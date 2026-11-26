"""Frozen two-seed 4M–16M-NNZ campaign with independent full certificates."""
import argparse
import datetime as dt
import json
from pathlib import Path
import sys
import time
import numpy as np
from lp_sp_pricing_budget import ROOT,BASE,NS,put,binding
from lp_sp_pricing_gpu_opt_compare import read,verify
from lp_sp_pricing_baselines import PYTHON,images,audit,copt
from lp_sp_pricing_geometry_copt_auto import child as copt_auto
from lp_sp_pricing_scale_admit import validate as admission,sources as certificate_sources
from lp_sp_pricing_geometry_admit import sources as geometry_sources
from lp_sp_pricing_scale_budget import allocation,APPROVAL
from lp_sp_pricing_million import matrix
from lp_billion_arrays import write
from lp_billion_owned_process import execute

STUDY=BASE/'scale-evaluation-v1'
SPECS=[dict(name='dense-4m',m=2000,n=2000,degree=2000,scaled=False,mixed=False),
       dict(name='dense-16m',m=4000,n=4000,degree=4000,scaled=False,mixed=False),
       dict(name='sparse-4m',m=16000,n=16000,degree=250,scaled=False,mixed=False),
       dict(name='sparse-scaled-10m',m=40000,n=40000,degree=250,scaled=True,mixed=False),
       dict(name='mixed-tall-4m',m=8000,n=2000,degree=500,scaled=False,mixed=True)]
SEEDS=[122301,122357]

def generate(spec,seed,out):
    start=time.perf_counter_ns();m,n=spec['m'],spec['n'];a=matrix(m,n,spec['degree'],seed,1)
    rng=np.random.default_rng(seed+37);a.data*=2*rng.integers(0,2,size=a.nnz,dtype=np.int8)-1
    if spec['scaled']:a.data*=np.repeat(np.exp2(np.arange(m)%9-4),spec['degree'])
    x=rng.integers(-8,9,size=n).astype(float)/8;y=rng.integers(1,8,size=m).astype(float)/(1<<(m-1).bit_length())
    slack=np.zeros(m)
    if spec['mixed']:
        inactive=np.arange(m)%5==0;y[inactive]=0;slack[inactive]=rng.integers(1,9,size=int(inactive.sum()))/8
    b=a@x+slack;c=np.asarray(a.T@y).ravel()
    arrays=dict(column_ids=write(BASE,np.arange(n),'u32le'),row_ids=write(BASE,np.arange(m),'u32le'),
        column_lower=write(BASE,np.full(n,-np.inf)),column_upper=write(BASE,np.full(n,np.inf)),
        row_lower=write(BASE,np.full(m,-np.inf)),row_upper=write(BASE,b),offsets=write(BASE,a.indptr,'u64le'),
        indices=write(BASE,a.indices,'u32le'),values=write(BASE,a.data),objective_indices=write(BASE,np.arange(n),'u32le'),objective_values=write(BASE,c))
    out.mkdir(parents=True,exist_ok=False);path=out/'portable.json'
    put(path,dict(schema_version=1,model_id=f"{spec['name']}-{seed}",rows=m,columns=n,nonzeros=int(a.nnz),sense='maximize',offset=0.,arrays=arrays))
    encoding=time.perf_counter_ns()-start;construction=out/'construction';construction.mkdir()
    put(construction/'response.json',dict(endpoint=dict(primal=write(BASE,x),dual=write(BASE,-y))))
    proof=audit('copt_scale_off',path,path,construction)
    if not proof['accepted']:raise RuntimeError('construction strict original-model proof failed')
    return dict(**spec,seed=seed,nonzeros=int(a.nnz),model=binding(path),encoding_ns=encoding,
        inactive_rows=int(np.count_nonzero(slack)),construction_audit=binding(construction/'audit.json'))

def freeze():
    gate=admission();allocation();STUDY.mkdir(exist_ok=False);models=[];cells=[]
    for repetition,seed in enumerate(SEEDS):
        for i,spec in enumerate(SPECS):
            model=generate(spec,seed,STUDY/'models'/f"{spec['name']}-{seed}");index=len(models);models.append(model)
            lanes=['candidate','copt-gpu'] if (i+repetition)%2==0 else ['copt-gpu','candidate']
            for lane in lanes+['copt-auto']:
                cells.append(dict(id=f"{spec['name']}-{seed}-{lane}",model_index=index,family=spec['name'],seed=seed,lane=lane,group=repetition))
    paths=[Path(__file__),ROOT/'tools/lp_sp_pricing_scale_budget.py',ROOT/'tools/lp_sp_pricing_geometry_copt_auto.py',ROOT/'tools/lp_sp_pricing_baselines.py']
    put(STUDY/'freeze.json',dict(status='frozen',admission=gate,allocation=binding(APPROVAL),models=models,cells=cells,
        native_seconds=120,process_seconds=150,gpu_group_reservation_seconds=1560,auto_group_reservation_seconds=810,
        independent_audit_process_seconds=240,wall_deadline_utc=allocation()['wall_deadline_utc'],
        sources=certificate_sources()+geometry_sources()+[binding(p) for p in paths],images=images(),
        scope='two independent seeds per family, one cold timing per solver/input; no repeated historical identity',
        limitations=['synthetic dyadic matrices and certificates','eight square all-active and two mixed-active tall models',
            'candidate presolve remains optional and does not prove completion of the pricing algorithm',
            'single cold timing per independent input; no cache flushing; CPU-auto groups run separately from GPU groups']))
    print(json.dumps(dict(status='frozen',models=len(models),cells=len(cells),nonzeros=sum(m['nonzeros'] for m in models))),flush=True)

def validate():
    f=read(STUDY/'freeze.json');admission();allocation()
    for s in f['sources']:verify(s)
    verify(f['allocation'])
    for model in f['models']:verify(model['model']);verify(model['construction_audit'])
    if f['images']!=images():raise RuntimeError('baseline/checker image changed')
    return f

def run(group,kind):
    f=validate();selected=[c for c in f['cells'] if c['group']==group and ((c['lane']=='copt-auto')==(kind=='auto'))]
    for cell in selected:
        model=f['models'][cell['model_index']];out=STUDY/'runs'/cell['id'];out.mkdir(parents=True,exist_ok=False)
        # Keep at least ten minutes for all audits and reporting. A cell that
        # cannot fit is explicitly unattempted, never silently omitted/retried.
        left=(dt.datetime.fromisoformat(f['wall_deadline_utc'])-dt.datetime.now(dt.timezone.utc)).total_seconds()
        if left<f['process_seconds']+600:
            put(out/'unattempted.json',dict(reason='campaign_wall_envelope',remaining_seconds=left));continue
        if cell['lane']=='candidate':cmd=[str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_scale_run.py'),model['model']['path'],str(out/'response.json'),'--seconds',str(f['native_seconds'])]
        else:cmd=[str(PYTHON),'-B',__file__,'vendor','--lane',cell['lane'],'--model',model['model']['path'],'--output',str(out)]
        put(out/'started.json',dict(command=cmd,cell=cell,model=model['model']))
        proc=execute(cmd,out/'stdout',out/'stderr',f['process_seconds'],None);put(out/'process.json',proc)
        print(json.dumps(dict(cell=cell['id'],process=proc)),flush=True)
    put(STUDY/f'{kind}-group-{group}-completed.json',dict(status='all_slots_disposed'))

def vendor(lane,model,out):
    f=validate()
    if lane=='copt-gpu':copt(model,out,f['native_seconds'])
    elif lane=='copt-auto':copt_auto(model,out,f['native_seconds'])
    else:raise ValueError('vendor lane')

def audits(group):
    f=validate()
    for kind in ('gpu','auto'):
        if not (STUDY/f'{kind}-group-{group}-completed.json').exists():raise RuntimeError('unfinished solver group')
    rows=[]
    for cell in [c for c in f['cells'] if c['group']==group]:
        model=f['models'][cell['model_index']];out=STUDY/'runs'/cell['id']
        if (out/'unattempted.json').exists():
            rows.append(dict(**cell,status='unattempted_wall_budget',strict_accepted=False,independent_exact_accepted=False,timely=False));continue
        proc=read(out/'process.json');path=out/'response.json';response=read(path) if path.exists() else {}
        strict=audit('copt_scale_off',Path(model['model']['path']),Path(model['model']['path']),out)
        independent_start=time.perf_counter_ns();proof_path=out/'independent-exact.json';exact={};audit_proc=None
        if path.exists() and (response.get('certificate') or response.get('endpoint')):
            cmd=[str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_scale_verify.py'),model['model']['path'],str(path),str(proof_path),'--seconds','210']
            audit_proc=execute(cmd,out/'independent-stdout',out/'independent-stderr',f['independent_audit_process_seconds'],None)
            put(out/'independent-process.json',audit_proc)
            if audit_proc['returncode']==0 and not audit_proc['timed_out'] and proof_path.exists():exact=read(proof_path)
            else:exact=dict(accepted=False,reason='independent_audit_process_failed')
        else:exact=dict(accepted=False,reason='no_endpoint');put(proof_path,exact)
        independent_ns=time.perf_counter_ns()-independent_start;native=response.get('solve_ns',response.get('native_ns'))
        timely=bool(proc['returncode']==0 and not proc['timed_out'] and native is not None and native<=f['native_seconds']*NS)
        if response.get('audit',{}).get('accepted') and not exact.get('accepted'):raise ArithmeticError('native accepted candidate not independently exact')
        if exact.get('accepted') and not strict['accepted']:raise ArithmeticError('exact endpoint not accepted by unchanged strict checker')
        row=dict(**cell,model=f"{model['name']}-{model['seed']}",nonzeros=model['nonzeros'],status=response.get('status','missing_response'),
            reason=response.get('reason'),route=response.get('route'),timely=timely,strict_accepted=strict['accepted'],independent_exact_accepted=bool(exact.get('accepted')),
            native_ns=native,process_ns=proc['elapsed_ns'],encoding_ns=model['encoding_ns'],strict_audit_ns=strict['elapsed_ns'],independent_audit_ns=independent_ns,
            complete_ns=model['encoding_ns']+proc['elapsed_ns']+strict['elapsed_ns']+independent_ns,
            operational_complete_ns=model['encoding_ns']+proc['elapsed_ns']+strict['elapsed_ns'],
            response=binding(path) if path.exists() else None,strict_audit=binding(out/'audit.json'),
            independent_proof=binding(proof_path) if proof_path.exists() else None,process=binding(out/'process.json'))
        rows.append(row);print(json.dumps({k:row[k] for k in ['id','status','strict_accepted','independent_exact_accepted','complete_ns']}),flush=True)
    put(STUDY/f'audits-group-{group}.json',dict(status='all_group_endpoints_checked',rows=rows))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','run','vendor','audit']);p.add_argument('--group',type=int,choices=[0,1]);p.add_argument('--kind',choices=['gpu','auto'])
    p.add_argument('--lane');p.add_argument('--model',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    if a.action=='freeze':freeze()
    elif a.action=='run':run(a.group,a.kind)
    elif a.action=='vendor':vendor(a.lane,a.model,a.output)
    else:audits(a.group)
