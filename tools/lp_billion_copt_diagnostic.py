"""Source-bound COPT startup diagnostics with durable phases and cooperative deadlines.

The historical adapters, original models and independent 1e-9 checker are unchanged.
Each invocation owns one problem and records all overhead, including interruption.
"""
import argparse
import ctypes as ct
import json
import math
import os
import threading
import time
from pathlib import Path
import numpy as np
from scipy import sparse
from lp_billion_common import BASE, DEVICE, load, put, ref, require
from lp_billion_arrays import write
from lp_billion_copt_run import Native, Clock, installation, read_model, ptr, roundtrip

VARIANTS = {
    'instrumented': dict(Presolve=0),
    'scale-off': dict(Presolve=0, Scaling=0),
    'dualize-off': dict(Presolve=0, Dualize=0),
    'scale-dual-off': dict(Presolve=0, Scaling=0, Dualize=0),
}


class Journal:
    def __init__(self, path):
        self.stream = Path(path).open('x')
        self.lock = threading.Lock()
    def record(self, event, **values):
        with self.lock:
            self.stream.write(json.dumps(dict(event=event, monotonic_ns=time.monotonic_ns(), **values), allow_nan=False)+'\n')
            self.stream.flush()
            os.fsync(self.stream.fileno())
    def close(self):
        self.stream.close()


class DurableClock(Clock):
    def __init__(self, journal):
        super().__init__('installation_binding')
        self.journal = journal
        journal.record('phase', phase=self.stage, exclusive_ns={})
    def enter(self, name):
        super().enter(name)
        self.journal.record('phase', phase=name, exclusive_ns=dict(self.cost))


def settings(variant, gpu, memory_mb):
    require(variant in VARIANTS, 'named diagnostic configuration')
    require(math.isfinite(memory_mb) and 0 < memory_mb <= 120000, 'vendor soft cap within physical host reservation')
    return dict(Threads=4, MemLimit=memory_mb, MatrixTol=0., FeasTol=1e-9, DualTol=1e-9,
                GPUMode=int(gpu), GPUDevice=0, LpMethod=6, Crossover=0,
                PDLPTol=1e-12, Logging=1, LogToConsole=0, **VARIANTS[variant])


class DiagnosticNative(Native):
    def configure(self, params):
        extra = {k:v for k,v in params.items() if k in {'Presolve','Scaling','Dualize'}}
        super().configure({k:v for k,v in params.items() if k not in extra})
        for key, value in extra.items():
            self.call('SetIntParam', self.prob, key.encode(), value)
            require(self.get(key, True, True)==value, 'diagnostic parameter roundtrip '+key)


def cooperative_solve(api, remaining, journal):
    """Interrupt only this live COPT problem; join before its handle can be freed."""
    done = threading.Event()
    events = []
    function = api.lib.COPT_Interrupt
    function.argtypes = [ct.c_void_p]
    function.restype = ct.c_int
    def deadline():
        if not done.wait(remaining):
            journal.record('interrupt_requested')
            code = function(api.prob)
            events.append(dict(returncode=code, monotonic_ns=time.monotonic_ns()))
            journal.record('interrupt_returned', returncode=code)
    watcher = threading.Thread(target=deadline, name='owned-copt-deadline', daemon=True)
    watcher.start()
    try:
        return api.lib.COPT_SolveLp(api.prob), events
    finally:
        done.set()
        watcher.join()


def solve(model, output, variant, wall, gpu=True, memory_mb=48000., check_roundtrip=False):
    require(math.isfinite(wall) and wall>0, 'positive solver wall allowance')
    if gpu:
        require(os.environ.get('AI_OPTIMIZER_GPU_LEASE')=='inherited' and os.environ.get('CUDA_VISIBLE_DEVICES')==DEVICE,
                'inherited pinned GPU lease')
    output=Path(output)
    require(not output.exists(), 'fresh diagnostic response')
    journal=Journal(output.with_suffix('.phases.jsonl'))
    clock=DurableClock(journal)
    api=None
    try:
        binding=installation()
        clock.enter('input_hash_validation')
        doc, data=read_model(model)
        model_ref=ref(model)
        solver_started=time.monotonic_ns()
        clock.enter('library_environment')
        api=DiagnosticNative()
        clock.enter('configuration')
        params=settings(variant,gpu,memory_mb)
        api.configure(params)
        log=output.with_suffix('.copt.log')
        api.call('SetLogFile',api.prob,str(log).encode())
        clock.enter('csr_to_csc')
        m,n,z=(doc[k] for k in ('rows','columns','nonzeros'))
        csr=sparse.csr_matrix((data['values'],data['indices'],data['offsets']),shape=(m,n),copy=False)
        require(csr.has_canonical_format,'canonical original CSR')
        matrix=csr.tocsc(copy=True)
        require(matrix.indices.dtype==np.int32 and matrix.indptr.dtype==np.int32,'32-bit COPT positions')
        objective=np.zeros(n,dtype=np.float64)
        objective[data['objective_indices']]=data['objective_values']
        clock.enter('model_import')
        api.call('LoadProb',api.prob,n,m,1 if doc['sense']=='minimize' else -1,float(doc['offset']),
                 ptr(objective),ptr(matrix.indptr),None,ptr(matrix.indices),ptr(matrix.data),None,
                 ptr(data['column_lower']),ptr(data['column_upper']),None,ptr(data['row_lower']),ptr(data['row_upper']),None,None)
        clock.enter('import_roundtrip')
        if check_roundtrip:roundtrip(api,doc,data,matrix,objective)
        clock.enter('input_release')
        del csr,matrix,objective,data
        remaining=wall-(time.monotonic_ns()-solver_started)/1e9
        called=remaining>0
        clock.enter('solve_configuration')
        if called:
            params['TimeLimit']=remaining
            api.configure({'TimeLimit':remaining})
        clock.enter('solve_call_opaque')
        code,interrupts=cooperative_solve(api,max(1e-9,wall-(time.monotonic_ns()-solver_started)/1e9),journal) if called else (0,[])
        solve_returned=time.monotonic_ns()
        journal.record('solve_returned',returncode=code,solver_elapsed_ns=solve_returned-solver_started)
        require(code in [0,1,9], 'unexpected COPT return code '+str(code))
        clock.enter('endpoint_extraction')
        status=api.get('LpStatus',True)
        has=bool(api.get('HasLpSol',True))
        native={name:api.get(name,True) for name in ['SimplexIter','BarrierIter','PDLPIter']}
        native.update({name:api.get(name) for name in ['SolvingTime','MemPeak']})
        endpoint=None
        if has:
            x,y=np.empty(n),np.empty(m)
            api.call('GetLpSolution',api.prob,ptr(x),None,ptr(y),None)
            if doc['sense']=='maximize':np.negative(y,out=y)
            require(np.all(np.isfinite(x)) and np.all(np.isfinite(y)), 'finite COPT endpoint')
            clock.enter('endpoint_output')
            endpoint=dict(primal=write(BASE,x),dual=write(BASE,y))
            del x,y
        clock.enter('response_assembly')
        result=dict(schema_version=1,kind='billion-COPT-startup-diagnostic',model_sha256=model_ref['sha256'],
                    requested='copt-gpu-pdlp' if gpu else 'copt-cpu-pdlp',copt_version='8.0.6',installation=binding,
                    parameters=params,variant=variant,status=status,optimal=status==1,has_solution=has,endpoint=endpoint,
                    native=native,rows=m,columns=n,nonzeros=z,roundtrip_checked=check_roundtrip,
                    common_solver_wall_seconds=wall,solve_called=called,deadline_before_solve=not called,
                    solve_returncode=code,solve_returned_ns=solve_returned-solver_started,interrupts=interrupts,
                    returned_before_deadline=solve_returned-solver_started<=int(wall*1e9),
                    internal_phase_costs='opaque',vendor_memory_limit_is_soft=True,adapter=ref(__file__),
                    input_adapter=ref(Path(__file__).with_name('lp_billion_copt_run.py')),
                    certified=None,certificate_policy='independent original-model 1e-9 check required; late endpoints cannot win deadline comparisons')
        clock.enter('teardown')
        api.close();api=None
        clock.enter('finalization')
        from lp_copt import gpu_started
        result['gpu_confirmed']=gpu_started(log.read_text()) if log.exists() else False
        result['executed']='copt-gpu-pdlp' if result['gpu_confirmed'] else 'copt-cpu-pdlp'
        result['solver_wall_ns']=time.monotonic_ns()-solver_started
        result['profile']=clock.finish()
        result['phase_journal']=ref(output.with_suffix('.phases.jsonl'))
        result['host_memory']={l.split(':',1)[0]:int(l.split()[1])*1024 for l in Path('/proc/self/status').read_text().splitlines() if l.startswith(('VmRSS:','VmHWM:'))}
        require(sum(result['profile']['exclusive_ns'].values())==result['profile']['total_ns'],'exact complete profile')
        put(output,result)
        return result
    except BaseException as error:
        journal.record('adapter_error',type=type(error).__name__,message=str(error),phase=clock.stage)
        raise
    finally:
        if api is not None:
            journal.record('exception_teardown_begin')
            api.close()
        journal.close()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('model',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--variant',choices=VARIANTS,default='instrumented');p.add_argument('--wall',type=float,default=60.)
    p.add_argument('--memory-mb',type=float,default=48000.);p.add_argument('--cpu',action='store_true');p.add_argument('--roundtrip',action='store_true')
    a=p.parse_args();r=solve(a.model,a.output,a.variant,a.wall,not a.cpu,a.memory_mb,a.roundtrip)
    print(dict(status=r['status'],has_solution=r['has_solution'],iterations=r['native']['PDLPIter'],solver_seconds=r['solver_wall_ns']/1e9),flush=True)
