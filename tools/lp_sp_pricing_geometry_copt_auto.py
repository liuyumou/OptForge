"""Additional prospective automatic-method COPT control on the same fresh inputs."""
import argparse
import json
from pathlib import Path
import sys
import time
import numpy as np
from scipy import sparse
from lp_sp_pricing_budget import ROOT,BASE,NS,put,binding
from lp_sp_pricing_baselines import PYTHON,images,audit
from lp_sp_pricing_gpu_opt_compare import read,verify
from lp_sp_pricing_geometry_experiment import validate,STUDY
from lp_billion_arrays import write
from lp_billion_owned_process import execute

AUTO=BASE/'geometry-copt-auto-v1'

def freeze():
    f=validate();AUTO.mkdir(exist_ok=False)
    put(AUTO/'freeze.json',dict(status='frozen',main_freeze=binding(STUDY/'freeze.json'),models=f['models'],
        native_seconds=30,process_seconds=45,source=binding(__file__),images=images(),
        configuration='automatic LP method with GPU disabled, original coefficients, common 1e-9 tolerances, four CPU threads',
        disclosure='Added as a stronger supplemental control after the primary roster was frozen and its first candidate timing was visible; candidate sources/configuration remain frozen.'))

def checked():
    f=read(AUTO/'freeze.json');verify(f['source']);verify(f['main_freeze']);validate()
    if images()!=f['images']:raise RuntimeError('vendor/checker image changed')
    return f

def child(model,out,seconds):
    from lp_billion_copt_run import read_model,ptr,installation
    from lp_billion_copt_diagnostic import DiagnosticNative,Journal,DurableClock,cooperative_solve
    journal=Journal(out/'phases.jsonl');clock=DurableClock(journal);api=None
    try:
        installed=installation();clock.enter('input_hash_validation');doc,data=read_model(model,BASE)
        clock.enter('library_environment');api=DiagnosticNative()
        defaults={k:api.get(k,True,True) for k in ['LpMethod','Presolve','Scaling','Dualize','Crossover']}
        params=dict(Threads=4,MemLimit=12000.,MatrixTol=0.,FeasTol=1e-9,DualTol=1e-9,GPUMode=0,Logging=1,LogToConsole=0)
        clock.enter('configuration');api.configure(params);api.call('SetLogFile',api.prob,str(out/'copt.log').encode())
        clock.enter('csr_to_csc');m,n=doc['rows'],doc['columns']
        csr=sparse.csr_matrix((data['values'],data['indices'],data['offsets']),shape=(m,n),copy=False)
        if not csr.has_canonical_format:raise ValueError('canonical CSR required')
        a=csr.tocsc(copy=True);c=np.zeros(n);c[data['objective_indices']]=data['objective_values']
        clock.enter('model_import');api.call('LoadProb',api.prob,n,m,-1,0.,ptr(c),ptr(a.indptr),None,ptr(a.indices),ptr(a.data),None,
            ptr(data['column_lower']),ptr(data['column_upper']),None,ptr(data['row_lower']),ptr(data['row_upper']),None,None)
        clock.enter('solve_configuration');api.configure(dict(TimeLimit=seconds))
        clock.enter('solve_call_opaque');start=time.monotonic_ns();code,interrupts=cooperative_solve(api,seconds,journal);native=time.monotonic_ns()-start
        clock.enter('endpoint_extraction');status=api.get('LpStatus',True);has=bool(api.get('HasLpSol',True));endpoint=None
        if has:
            x,y=np.empty(n),np.empty(m);api.call('GetLpSolution',api.prob,ptr(x),None,ptr(y),None);np.negative(y,out=y)
            if not np.isfinite(x).all() or not np.isfinite(y).all():raise ArithmeticError('nonfinite COPT endpoint')
            endpoint=dict(primal=write(BASE,x),dual=write(BASE,y))
        clock.enter('teardown');api.close();api=None
        put(out/'response.json',dict(status=status,has_solution=has,endpoint=endpoint,native_ns=native,parameters=params,
            automatic_defaults=defaults,solve_returncode=code,interrupts=interrupts,installation=installed,profile=clock.finish()))
    finally:
        if api is not None:api.close()
        journal.close()

def run():
    f=checked()
    for m in f['models']:
        out=AUTO/'runs'/m['name'];out.mkdir(parents=True,exist_ok=False)
        cmd=[str(PYTHON),'-B',__file__,'child','--model',m['model']['path'],'--output',str(out)]
        put(out/'started.json',dict(command=cmd,model=m['model']));proc=execute(cmd,out/'stdout',out/'stderr',f['process_seconds'],None)
        put(out/'process.json',proc);print(json.dumps(dict(model=m['name'],process=proc)),flush=True)
    put(AUTO/'completed.json',dict(status='all_cells_attempted'))

def audits():
    f=checked()
    if not (AUTO/'completed.json').exists():raise RuntimeError('incomplete automatic control')
    rows=[]
    for m in f['models']:
        out=AUTO/'runs'/m['name'];proc=read(out/'process.json');path=out/'response.json';d=read(path) if path.exists() else {}
        proof=audit('copt_scale_off',Path(m['model']['path']),Path(m['model']['path']),out);native=d.get('native_ns')
        rows.append(dict(id=m['name']+'-copt-auto',model=m['name'],lane='copt-auto',status=d.get('status','missing_response'),
            reason=None,route='COPT automatic CPU',timely=bool(native is not None and native<=30*NS and proc['returncode']==0 and not proc['timed_out']),
            strict_accepted=proof['accepted'],native_ns=native,process_ns=proc['elapsed_ns'],encoding_ns=m['encoding_ns'],audit_ns=proof['elapsed_ns'],
            complete_ns=m['encoding_ns']+proc['elapsed_ns']+proof['elapsed_ns'],response=binding(path) if path.exists() else None,
            audit=binding(out/'audit.json'),process=binding(out/'process.json')))
    put(AUTO/'audits.json',dict(status='all_endpoints_audited',rows=rows,freeze=binding(AUTO/'freeze.json')))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','run','child','audit']);p.add_argument('--model',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    if a.action=='freeze':freeze()
    elif a.action=='run':run()
    elif a.action=='child':checked();child(a.model,a.output,30)
    else:audits()
