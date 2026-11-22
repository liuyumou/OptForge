"""Separate installed-COPT GPU PDLP variant with Presolve=0; original adapter retained.

GPU execution requires the inherited pinned lease and explicit admission evidence.
No license material is read or retained by this module.
"""
import argparse
import ctypes as ct
import hashlib
import math
import os
import time
from pathlib import Path
import numpy as np
from scipy import sparse
from lp_billion_arrays import CHUNK, DTYPES, write
from lp_billion_common import BASE, DEVICE, ROOT, put, load, ref, resolve, require, digest

INSTALL = Path('/root/copt80')
INF = 1e30
BLOCK = 1 << 20


def installation():
    return {name: dict(path=str(p), bytes=p.stat().st_size, sha256=digest(p))
            for name, p in [('library', INSTALL/'lib/libcopt.so'), ('header', INSTALL/'include/copt.h')]}


def read_array(root, spec, dtype, count):
    require(spec['dtype'] == dtype and type(spec['count']) is int and spec['count'] == count, 'array type/count')
    dt = DTYPES[dtype]
    require(sum(c['bytes'] for c in spec['chunks']) == count * dt.itemsize, 'array byte count')
    result = np.empty(count, dtype=dt)
    target = memoryview(result).cast('B')
    offset = 0
    for chunk in spec['chunks']:
        sha, size = chunk['sha256'], chunk['bytes']
        require(len(sha) == 64 and all(c in '0123456789abcdef' for c in sha)
                and type(size) is int and 0 < size <= CHUNK and size % dt.itemsize == 0, 'chunk domain')
        path = Path(root)/'objects'/(sha+'.bin')
        require(path.resolve().is_relative_to(Path(root).resolve()), 'chunk path')
        require(path.stat().st_size == size, 'chunk length')
        # One bounded chunk, copied into its final array; never concatenate all chunks.
        data = path.read_bytes()
        require(len(data) == size and hashlib.sha256(data).hexdigest() == sha, 'chunk digest')
        target[offset:offset+size] = data
        offset += size
    require(offset == target.nbytes, 'complete array coverage')
    return result


def finite(values, name, allow_infinity=False):
    for start in range(0, len(values), BLOCK):
        part = values[start:start+BLOCK]
        require(not np.any(np.isnan(part)), 'NaN '+name)
        require(allow_infinity or np.all(np.isfinite(part)), 'nonfinite '+name)
        require(not np.any(np.isfinite(part) & (np.abs(part) >= INF)), 'finite sentinel collision '+name)


def read_model(path, root=BASE):
    doc = load(path)
    m, n, z = (doc[k] for k in ['rows', 'columns', 'nonzeros'])
    require(doc['schema_version'] == 1 and all(type(v) is int and v >= 0 for v in [m,n,z])
            and max(m,n) <= 250_000_000 and z <= 1_000_000_000, 'model dimensions')
    require(doc['sense'] in ['minimize','maximize'] and math.isfinite(doc['offset']) and abs(doc['offset']) < INF, 'objective domain')
    fields = dict(column_ids=('u32le',n), row_ids=('u32le',m), column_lower=('f64le',n),
                  column_upper=('f64le',n), row_lower=('f64le',m), row_upper=('f64le',m),
                  offsets=('u64le',m+1), indices=('u32le',z), values=('f64le',z))
    k = doc['arrays']['objective_indices']['count']
    require(type(k) is int and 0 <= k <= n, 'objective count')
    fields.update(objective_indices=('u32le',k), objective_values=('f64le',k))
    require(set(fields) == set(doc['arrays']), 'original array fields')
    data = {key: read_array(root, doc['arrays'][key], *spec) for key,spec in fields.items()}
    for key in ['column_ids','row_ids','objective_indices']:
        a = data[key]
        require(np.all(a[1:] > a[:-1]), 'ordered identities '+key)
    require(k == 0 or data['objective_indices'][-1] < n, 'objective index domain')
    p = data['offsets']
    require(p[0] == 0 and p[-1] == z and np.all(p[1:] >= p[:-1]), 'CSR offsets')
    for start in range(0,z,BLOCK):
        require(np.all(data['indices'][start:start+BLOCK] < n), 'CSR column domain')
    for key in ['values','objective_values']:finite(data[key],key)
    for side in ['column','row']:
        lo, hi = data[side+'_lower'], data[side+'_upper']
        finite(lo, side+' lower', True); finite(hi, side+' upper', True)
        require(np.all(lo <= hi) and not np.any(np.isposinf(lo)) and not np.any(np.isneginf(hi)), 'bound orientation')
        np.clip(lo,-INF,INF,out=lo); np.clip(hi,-INF,INF,out=hi)
    data['offsets'] = p.astype(np.int32)
    data['indices'] = data['indices'].view(np.int32)
    return doc, data


class Clock:
    def __init__(self, first):
        self.origin = self.last = time.monotonic_ns()
        self.stage, self.cost = first, {}
    def enter(self, name):
        now = time.monotonic_ns()
        self.cost[self.stage] = self.cost.get(self.stage,0) + now-self.last
        self.last, self.stage = now, name
    def finish(self):
        self.enter('finished')
        return dict(schema_version=1, clock='monotonic_host_wall', total_ns=self.last-self.origin,
                    exclusive_ns=self.cost, timer_overhead_included=True, kernel_active_time=False)


class Native:
    def __init__(self):
        self.lib = ct.CDLL(str(INSTALL/'lib/libcopt.so'))
        self.env, self.prob = ct.c_void_p(), ct.c_void_p()
        P, I, D, S = ct.c_void_p, ct.c_int, ct.c_double, ct.c_char_p
        signatures = dict(CreateEnvWithPath=[S,ct.POINTER(P)], DeleteEnv=[ct.POINTER(P)],
            CreateProb=[P,ct.POINTER(P)], DeleteProb=[ct.POINTER(P)],
            LoadProb=[P,I,I,I,D,P,P,P,P,P,P,P,P,P,P,P,P,P],
            SetIntParam=[P,S,I], GetIntParam=[P,S,ct.POINTER(I)],
            SetDblParam=[P,S,D], GetDblParam=[P,S,ct.POINTER(D)],
            GetIntAttr=[P,S,ct.POINTER(I)], GetDblAttr=[P,S,ct.POINTER(D)],
            GetColInfo=[P,S,I,P,P], GetRowInfo=[P,S,I,P,P],
            GetCols=[P,I,P,P,P,P,P,I,ct.POINTER(I)],
            GetLpSolution=[P,P,P,P,P], SolveLp=[P], SetLogFile=[P,S])
        for name, signature in signatures.items():
            f = getattr(self.lib,'COPT_'+name); f.argtypes=signature; f.restype=I
        try:
            self.call('CreateEnvWithPath',str(INSTALL).encode(),ct.byref(self.env))
            self.call('CreateProb',self.env,ct.byref(self.prob))
        except BaseException:
            self.close(); raise
    def call(self, name, *args):
        code = getattr(self.lib,'COPT_'+name)(*args)
        require(code == 0, 'COPT '+name+' returned '+str(code))
    def get(self, name, integer=False, parameter=False):
        value = ct.c_int() if integer else ct.c_double()
        self.call(('GetInt' if integer else 'GetDbl')+('Param' if parameter else 'Attr'),self.prob,name.encode(),ct.byref(value))
        return value.value
    def configure(self, params):
        for name,value in params.items():
            integer = name in {'Threads','GPUMode','GPUDevice','LpMethod','Crossover','Presolve','Logging','LogToConsole'}
            require(integer or name in {'MemLimit','MatrixTol','FeasTol','DualTol','TimeLimit','PDLPTol'}, 'declared native parameter type '+name)
            self.call('SetIntParam' if integer else 'SetDblParam',self.prob,name.encode(),value)
            require(self.get(name,integer,True) == value, 'COPT parameter roundtrip '+name)
    def close(self):
        try:
            if self.prob:self.call('DeleteProb',ct.byref(self.prob))
        finally:
            if self.env:self.call('DeleteEnv',ct.byref(self.env))


def ptr(array):
    require(array.flags.c_contiguous, 'contiguous native array')
    return ct.c_void_p(array.ctypes.data)


def roundtrip(api, doc, data, matrix, objective):
    n,m,z = doc['columns'],doc['rows'],doc['nonzeros']
    require(z <= 1_000_000 and max(m,n) <= 100_000, 'roundtrip is bounded admission only')
    begins=np.empty(n,dtype=np.int32);counts=np.empty(n,dtype=np.int32)
    indices=np.empty(z,dtype=np.int32);values=np.empty(z,dtype=np.float64);required=ct.c_int()
    api.call('GetCols',api.prob,n,None,ptr(begins),ptr(counts),ptr(indices),ptr(values),z,ct.byref(required))
    require(required.value == z and np.array_equal(begins,matrix.indptr[:-1])
            and np.array_equal(counts,np.diff(matrix.indptr)) and np.array_equal(indices,matrix.indices)
            and np.array_equal(values.view('u8'),matrix.data.view('u8')), 'exact COPT sparse roundtrip')
    for side,count,names in [('Col',n,[('LB','column_lower'),('UB','column_upper'),('Obj',None)]),
                             ('Row',m,[('LB','row_lower'),('UB','row_upper')])]:
        for name,key in names:
            actual=np.empty(count,dtype=np.float64)
            api.call('Get'+side+'Info',api.prob,name.encode(),count,None,ptr(actual))
            expected=objective if key is None else data[key]
            require(np.array_equal(actual.view('u8'),expected.view('u8')), 'exact COPT '+side+' '+name)
    require(api.get('ObjSense',True) == (1 if doc['sense']=='minimize' else -1)
            and api.get('ObjConst') == doc['offset'], 'COPT objective sense/offset')


def solve(model_path, output, wall_seconds=30., check_roundtrip=False, gpu=False, memory_mb=12000., admission=False):
    require(gpu, 'this separately identified variant is GPU-only')
    require(0 < memory_mb <= 48000., 'bounded vendor soft memory allowance')
    if gpu:
        require(os.environ.get('AI_OPTIMIZER_GPU_LEASE')=='inherited' and os.environ.get('CUDA_VISIBLE_DEVICES')==DEVICE,'inherited pinned COPT GPU lease')
        require(load(BASE/'resources/operational-gpu-v17.settlement.json')['status']=='passed','fresh GPU operational admission')
    if not admission:
        gate=load(BASE/'copt-nopresolve-admission-v1/result.json')
        require(gate['status']=='passed' and gate['adapter']==ref(__file__) and gate['installation']==installation(),'current COPT CPU/GPU admission')
    require(math.isfinite(wall_seconds) and wall_seconds > 0, 'solver wall allowance')
    output = Path(output)
    require(not output.exists() and not output.with_suffix('.copt.log').exists(), 'fresh COPT cell')
    clock=Clock('installation_binding')
    binding=installation()
    clock.enter('input_hash_validation')
    doc,data=read_model(model_path);model_hash=digest(model_path)
    # Like the project executor, solver wall begins after original input loading.
    solver_started=time.monotonic_ns()
    clock.enter('library_environment')
    api=Native()
    try:
        clock.enter('configuration')
        params=dict(Threads=4,MemLimit=memory_mb,MatrixTol=0.,FeasTol=1e-9,DualTol=1e-9,
                    GPUMode=int(gpu),GPUDevice=0,LpMethod=6 if gpu else -1,Crossover=0 if gpu else 1,Presolve=0,Logging=1,LogToConsole=0)
        if gpu:params['PDLPTol']=1e-12
        api.configure(params)
        log=output.with_suffix('.copt.log')
        api.call('SetLogFile',api.prob,str(log).encode())
        clock.enter('csr_to_csc')
        m,n,z=doc['rows'],doc['columns'],doc['nonzeros']
        csr=sparse.csr_matrix((data['values'],data['indices'],data['offsets']),shape=(m,n),copy=False)
        require(csr.has_canonical_format, 'CSR duplicates or unordered row')
        matrix=csr.tocsc(copy=True)
        require(matrix.indices.dtype == np.int32 and matrix.indptr.dtype == np.int32, 'COPT 32-bit sparse indices')
        objective=np.zeros(n,dtype=np.float64)
        objective[data['objective_indices']]=data['objective_values']
        clock.enter('model_import')
        api.call('LoadProb',api.prob,n,m,1 if doc['sense']=='minimize' else -1,float(doc['offset']),
            ptr(objective),ptr(matrix.indptr),None,ptr(matrix.indices),ptr(matrix.data),None,
            ptr(data['column_lower']),ptr(data['column_upper']),None,
            ptr(data['row_lower']),ptr(data['row_upper']),None,None)
        clock.enter('import_roundtrip')
        if check_roundtrip:roundtrip(api,doc,data,matrix,objective)
        clock.enter('input_release')
        del csr,matrix,objective,data
        remaining=wall_seconds-(time.monotonic_ns()-solver_started)/1e9
        called=remaining > 0
        clock.enter('solve_configuration')
        if called:
            params['TimeLimit']=remaining
            api.configure({'TimeLimit':remaining})
        clock.enter('solve_call_opaque')
        solve_returncode=0
        if called:solve_returncode=api.lib.COPT_SolveLp(api.prob)
        require(solve_returncode in [0,1,9], 'unexpected COPT solve failure '+str(solve_returncode))
        clock.enter('endpoint_extraction')
        status=api.get('LpStatus',True);has=bool(api.get('HasLpSol',True))
        native={name:api.get(name,True) for name in ['SimplexIter','BarrierIter','PDLPIter']}
        native.update({name:api.get(name) for name in ['SolvingTime','MemPeak']})
        endpoint=None
        if has:
            x,y=np.empty(n,dtype=np.float64),np.empty(m,dtype=np.float64)
            api.call('GetLpSolution',api.prob,ptr(x),None,ptr(y),None)
            if doc['sense']=='maximize':np.negative(y,out=y)
            require(np.all(np.isfinite(x)) and np.all(np.isfinite(y)), 'finite vendor endpoint')
            clock.enter('endpoint_output')
            endpoint=dict(primal=write(BASE,x),dual=write(BASE,y))
            del x,y
        clock.enter('response_assembly')
        from lp_copt import gpu_started
        actual_gpu=gpu_started(log.read_text()) if log.exists() else False
        result=dict(schema_version=1,kind='billion-COPT-nopresolve-GPU-development',model_sha256=model_hash,
            requested='copt-gpu-pdlp' if gpu else 'copt-cpu-auto',executed='copt-gpu-pdlp' if actual_gpu else 'copt-cpu-pdlp' if gpu else 'copt-cpu-auto',copt_version='8.0.6',installation=binding,
            variant='gpu-pdlp-presolve0',parameters=params,status=status,optimal=status==1,has_solution=has,endpoint=endpoint,
            native=native,rows=m,columns=n,nonzeros=z,roundtrip_checked=check_roundtrip,
            common_solver_wall_seconds=wall_seconds,solve_called=called,
            deadline_before_solve=not called,internal_phase_costs='opaque',gpu_confirmed=actual_gpu,solve_returncode=solve_returncode,
            vendor_memory_limit_is_soft=True,adapter=ref(__file__),
            certified=None,certificate_policy='independent original-model 1e-9 check required')
    finally:
        clock.enter('teardown');api.close()
    clock.enter('finalization')
    result['gpu_confirmed']=gpu_started(log.read_text()) if log.exists() else False
    result['executed']='copt-gpu-pdlp' if result['gpu_confirmed'] else 'copt-cpu-pdlp' if gpu else 'copt-cpu-auto'
    result['solver_wall_ns']=time.monotonic_ns()-solver_started
    result['profile']=clock.finish()
    fields={l.split(':',1)[0]:l.split()[1] for l in Path('/proc/self/status').read_text().splitlines() if l.startswith(('VmRSS:','VmHWM:'))}
    result['host_memory']={k:int(v)*1024 for k,v in fields.items()}
    result['process_identity']={'pid':os.getpid(),'start_ticks':int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19])}
    require(sum(result['profile']['exclusive_ns'].values())==result['profile']['total_ns'], 'COPT exact timing coverage')
    put(output,result)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('model',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--wall-seconds',type=float,default=30.);p.add_argument('--roundtrip',action='store_true');p.add_argument('--gpu',action='store_true')
    p.add_argument('--memory-mb',type=float,default=12000.);p.add_argument('--admission',action='store_true')
    a=p.parse_args();r=solve(a.model,a.output,a.wall_seconds,a.roundtrip,a.gpu,a.memory_mb,a.admission)
    print(dict(status=r['status'],has_solution=r['has_solution'],profile_ns=r['profile']['total_ns']),flush=True)
