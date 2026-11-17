"""COPT 8.0.6 external baseline on the same compact original model."""
import argparse
import json
import os
from pathlib import Path
import signal
import time
import numpy as np
from lp_general_common import DEVICE,ROOT,put,ref,require
from lp_general_scale_io import read,digest

PYTHON=ROOT/'artifacts/gpup-copt-adapter-env/venv/bin/python'

def run(model_path,output,method,tolerance,seconds,roundtrip=False):
    start=time.monotonic_ns();cost={}
    def mark(name,before):cost[name]=time.monotonic_ns()-before
    before=time.monotonic_ns()
    import coptpy as cp
    from scipy import sparse
    mark('bindings',before)
    installed=Path('/root/copt80')
    binding=Path(cp.__file__).parent
    for name,original in [('coptcore.so',installed/'lib/python/311/coptpy/coptcore.so'),('libcopt_python.so',installed/'lib/python/deps/libcopt_python.so')]:
        require(digest(binding/name)==digest(original),'COPT differs from authorized installation '+name)
    gpu=method in ['copt-gpu-pdlp','copt-gpu-tight']
    require(method in ['copt-cpu-auto','copt-gpu-pdlp','copt-gpu-tight'],'COPT method')
    if gpu:require(os.environ.get('AI_OPTIMIZER_GPU_LEASE')=='inherited' and os.environ.get('CUDA_VISIBLE_DEVICES')==DEVICE,'COPT pinned shared lease')
    before=time.monotonic_ns();data=read(model_path);model_hash=digest(model_path);mark('input',before)
    m,n=data['shape'];infinity=cp.COPT.INFINITY
    for key in ['values','objective_values','lower','upper','row_lower','row_upper']:
        a=data[key]
        require(not np.any(np.isfinite(a)&(np.abs(a)>=infinity)),'finite COPT sentinel collision '+key)
    def bounds(key):return np.clip(data[key],-infinity,infinity)
    before=time.monotonic_ns();env=cp.Envr();model=env.createModel('general-scale-baseline');mark('license_environment',before)
    lines=[]
    class Log(cp.LogCallback):
        def Display(self,message):lines.append(message)
    logger=Log();model.setLogCallback(logger)
    params=dict(Threads=4,TimeLimit=seconds,MemLimit=12000,MatrixTol=0.,FeasTol=tolerance,DualTol=tolerance,
                GPUMode=int(gpu),GPUDevice=0,LpMethod=6 if gpu else -1,Crossover=0 if gpu else 1)
    if gpu:params['PDLPTol']=1e-12 if method=='copt-gpu-tight' else tolerance
    for k,v in params.items():model.setParam(k,v)
    signal.signal(signal.SIGINT,lambda *_:model.interrupt())
    before=time.monotonic_ns()
    csr=sparse.csr_matrix((data['values'],data['indices'],data['pointers']),shape=(m,n));matrix=csr.tocsc()
    c=np.zeros(n);c[data['objective_indices']]=data['objective_values']
    model.loadMatrix(c,matrix,bounds('row_lower'),bounds('row_upper'),bounds('lower'),bounds('upper'))
    model.setObjSense(cp.COPT.MINIMIZE if data['sense']=='minimize' else cp.COPT.MAXIMIZE)
    model.setObjConst(data['offset']);mark('matrix_import',before)
    if roundtrip:
        a=model.getA().tocsr();a.sort_indices()
        require(np.array_equal(a.indptr,csr.indptr) and np.array_equal(a.indices,csr.indices) and np.array_equal(a.data.view('u8'),csr.data.view('u8')),'COPT exact sparse roundtrip')
        for key,objects,expected in [('LB',model.getVars(),bounds('lower')),('UB',model.getVars(),bounds('upper')),
                                     ('LB',model.getConstrs(),bounds('row_lower')),('UB',model.getConstrs(),bounds('row_upper')),('Obj',model.getVars(),c)]:
            require(np.array_equal(np.asarray(model.getInfo(key,objects)),expected),'COPT exact vector roundtrip '+key)
    del matrix,csr,c
    before=time.monotonic_ns();model.solveLP();mark('solve',before)
    before=time.monotonic_ns()
    status=int(model.getAttr('LpStatus'));has=bool(model.getAttr('HasLpSol'))
    x=list(model.getValues()) if has else None
    sign=1 if data['sense']=='minimize' else -1
    y=[sign*v for v in model.getDuals()] if has else None
    from lp_copt import gpu_started
    actual_gpu=gpu_started('\n'.join(lines))
    native={k:model.getAttr(k) for k in ['SimplexIter','BarrierIter','PDLPIter','SolvingTime','MemPeak']}
    mark('endpoint',before)
    result=dict(kind='general-scale-COPT-baseline',model_sha256=model_hash,requested=method,
        executed='copt-gpu-pdlp' if actual_gpu else ('copt-cpu-pdlp' if gpu else 'copt-cpu-auto'),
        gpu_confirmed=actual_gpu,copt_version='8.0.6',library=ref(binding/'libcopt_python.so'),binding=ref(binding/'coptcore.so'),
        parameters=params,status=status,optimal=status==cp.COPT.OPTIMAL,has_solution=has,primal=x,dual=y,native=native,cost_ns=cost,
        rows=m,columns=n,nonzeros=len(data['values']),roundtrip_checked=roundtrip,
        limitation='COPT stopping criteria and iteration counts differ; original-model checking is independent and all costs are retained.')
    output=Path(output);output.with_suffix('.copt.log').write_text('\n'.join(lines))
    before=time.monotonic_ns();del model,env;mark('teardown',before)
    result['elapsed_ns']=time.monotonic_ns()-start
    put(output,result)
    print(dict(method=method,executed=result['executed'],status=status,solve_ms=cost['solve']/1e6),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--method',choices=['copt-cpu-auto','copt-gpu-pdlp','copt-gpu-tight'],required=True);p.add_argument('--tolerance',type=float,default=1e-9)
    p.add_argument('--seconds',type=float,default=30);p.add_argument('--roundtrip',action='store_true');a=p.parse_args()
    require(a.tolerance in [1e-7,1e-9] and 0<a.seconds<=300,'baseline limits')
    run(a.model,a.output,a.method,a.tolerance,a.seconds,a.roundtrip)
