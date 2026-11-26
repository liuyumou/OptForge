"""Frozen non-tall coverage; original candidate and certificate kernels unchanged."""
import argparse
import datetime as dt
import json
import platform
from pathlib import Path
import subprocess
import time
from unittest.mock import patch
import numpy as np
from scipy import sparse
import scipy
from lp_sp_pricing_budget import ROOT,BASE,NS,put,binding
from lp_sp_pricing_gpu_opt_compare import read,verify
from lp_sp_pricing_baselines import PYTHON,images,audit,copt
from lp_sp_pricing_geometry_copt_auto import child as copt_auto
from lp_sp_pricing_million import matrix
from lp_sp_pricing_transform_admit import validate as numerical_admission
from lp_sp_pricing_nontall_budget import allocation,APPROVAL
from lp_sp_pricing_factor_endpoint import prepare as original_prepare
from lp_sp_pricing_factor_range import build as adaptive_build
from lp_sp_pricing_geometry_run import load
from lp_billion_arrays import write,read as read_array
from lp_billion_owned_process import execute

STUDY=BASE/'nontall-evaluation-v1'
SEEDS=[125101,125123,125149]
SPECS=[
    dict(name='dense-wide-1m',m=500,n=2000,degree=2000,layout='band',shift=1,scaled=False,mixed=False),
    dict(name='sparse-wide-1m',m=2000,n=8000,degree=500,layout='band',shift=17,scaled=False,mixed=False),
    dict(name='mixed-square-1m',m=1000,n=1000,degree=1000,layout='band',shift=1,scaled=False,mixed=True),
    dict(name='mixed-rectangular-1p5m',m=1500,n=1000,degree=1000,layout='band',shift=1,scaled=False,mixed=True),
    dict(name='dense-square-4m',m=2000,n=2000,degree=2000,layout='band',shift=1,scaled=False,mixed=False),
    dict(name='banded-square-4m',m=16000,n=16000,degree=250,layout='band',shift=1,scaled=False,mixed=False),
    dict(name='irregular-square-1m',m=4000,n=4000,degree=250,layout='random',shift=1,scaled=False,mixed=False),
    dict(name='scaled-square-1m',m=8000,n=8000,degree=125,layout='band',shift=1,scaled=True,mixed=False)]


def arrays(spec,seed):
    m,n,d=spec['m'],spec['n'],spec['degree']
    if spec['layout']=='random':
        rng=np.random.default_rng(seed);indices=np.concatenate([np.sort(rng.choice(n,d,replace=False)) for _ in range(m)])
        values=rng.integers(1,32,size=m*d).astype(float)/16
        a=sparse.csr_matrix((values,indices,np.arange(m+1,dtype=np.int64)*d),shape=(m,n))
    else:a=matrix(m,n,d,seed,spec['shift'])
    rng=np.random.default_rng(seed+37);a.data*=2*rng.integers(0,2,size=a.nnz,dtype=np.int8)-1
    if spec['scaled']:a.data*=np.repeat(np.exp2(np.arange(m)%9-4),d)
    x=rng.integers(-8,9,size=n).astype(float)/8;y=rng.integers(1,8,size=m).astype(float)/(1<<(m-1).bit_length());slack=np.zeros(m)
    if spec['mixed']:
        inactive=np.arange(m)%5==0;y[inactive]=0;slack[inactive]=rng.integers(1,9,size=int(inactive.sum()))/8
    return a,np.asarray(a@x+slack),np.asarray(a.T@y).ravel(),x,y,slack


def generate(spec,seed,out):
    start=time.perf_counter_ns();a,b,c,x,y,slack=arrays(spec,seed);m,n=a.shape
    data=dict(column_ids=write(BASE,np.arange(n),'u32le'),row_ids=write(BASE,np.arange(m),'u32le'),
        column_lower=write(BASE,np.full(n,-np.inf)),column_upper=write(BASE,np.full(n,np.inf)),
        row_lower=write(BASE,np.full(m,-np.inf)),row_upper=write(BASE,b),offsets=write(BASE,a.indptr,'u64le'),
        indices=write(BASE,a.indices,'u32le'),values=write(BASE,a.data),objective_indices=write(BASE,np.arange(n),'u32le'),objective_values=write(BASE,c))
    out.mkdir(parents=True,exist_ok=False);path=out/'portable.json'
    put(path,dict(schema_version=1,model_id=f"{spec['name']}-{seed}",rows=m,columns=n,nonzeros=int(a.nnz),sense='maximize',offset=0.,arrays=data))
    encoding=time.perf_counter_ns()-start;construction=out/'construction';construction.mkdir()
    put(construction/'response.json',dict(endpoint=dict(primal=write(BASE,x),dual=write(BASE,-y))))
    if not audit('copt_scale_off',path,path,construction)['accepted']:raise ArithmeticError('construction audit')
    return dict(**spec,seed=seed,nonzeros=int(a.nnz),model=binding(path),encoding_ns=encoding,
        inactive_rows=int(np.count_nonzero(slack)),covered_columns=int(len(np.unique(a.indices))),construction_audit=binding(construction/'audit.json'))


def sources():
    return [binding(ROOT/'tools'/name) for name in ('lp_sp_pricing_nontall_experiment.py','lp_sp_pricing_nontall_budget.py','lp_sp_pricing_nontall_admin.py','lp_sp_pricing_nontall_driver.py',
        'lp_sp_pricing_transform_run.py','lp_sp_pricing_factor_endpoint.py','lp_sp_pricing_factor_range.py',
        'lp_sp_pricing_baselines.py','lp_sp_pricing_geometry_copt_auto.py','lp_sp_pricing_scale_verify.py')]+[binding(ROOT/'tests/integration/test_lp_sp_pricing_nontall.py')]


def freeze():
    gate=numerical_admission();alloc=allocation();test=BASE/'nontall-contracts-v1/result.json'
    if read(test)['status']!='passed' or read(BASE/'resources/nontall-contracts-v1.settlement.json')['status']!='passed':raise RuntimeError('non-tall harness admission')
    if read(test)['sources']!=sources():raise RuntimeError('tested harness changed')
    STUDY.mkdir(exist_ok=False);models=[]
    for spec in SPECS:
        for seed in SEEDS:models.append(generate(spec,seed,STUDY/'models'/f"{spec['name']}-{seed}"))
    put(STUDY/'freeze.json',dict(status='frozen',sources=sources(),admission=gate,contracts=binding(test),allocation=binding(APPROVAL),models=models,
        lanes=['candidate','copt-gpu-default','copt-auto'],native_seconds=60,process_seconds=90,postprocess_seconds=90,proof_seconds=120,
        images=images(),wall_deadline_utc=alloc['wall_deadline_utc'],hardware=dict(cpu=platform.processor(),platform=platform.platform(),numpy=np.__version__,scipy=scipy.__version__,
            cpuinfo=Path('/proc/cpuinfo').read_text().split('model name',1)[1].splitlines()[0].strip(' :\t'),cpu_slots=4,blas_threads=1),
        gpu_configuration='COPT PDLP GPU, PDLPTol=1e-9, Presolve=0 inherited instrumented setting, installed default Scaling and Dualize. CPU auto retains installed automatic defaults with GPUMode=0. Exact parameters and GPU startup evidence retained.',
        certificate_policy='Identical dyadic reconstruction then supported implicit dual correction, with adaptive dual exponent only on dual_base_range, CPU inverse proposals for every lane. Full independent exact check. Raw unchanged 1e-9 acceptance separately timed and reported.',
        scope='24 fresh models, 72 solver slots, three seeds per eight families. Rotated GPU/candidate order; CPU automatic controls in separate CPU-only groups, explicit order limitation. No cache flushing or repeated LP attempts.',
        limitation='Synthetic feasible bounded dyadic models, construction witnesses withheld. Wide primal reconstruction is limited; failure to reconstruct is not solver infeasibility. No candidate tuning or numerical code changes.'))
    print(json.dumps(dict(status='frozen',models=len(models),cells=3*len(models))),flush=True)


def validate():
    numerical_admission();allocation();f=read(STUDY/'freeze.json')
    for item in f['sources']:verify(item)
    verify(f['admission']);verify(f['contracts']);verify(f['allocation'])
    for model in f['models']:verify(model['model']);verify(model['construction_audit'])
    if images()!=f['images']:raise RuntimeError('retained images changed')
    return f


def endpoint(model,response,output):
    start=time.perf_counter_ns();original_prepare(model,response,output,gpu=False);result=read(output)
    # The base proposal remains immutable; the extension is prospectively
    # common to every lane and all its work is part of this cold process.
    if result.get('implicit_construction',{}).get('reason')=='dual_base_range':
        a,b,c,_,_=load(model);raw=read(response);x=read_array(BASE,raw['endpoint']['primal']);y=-read_array(BASE,raw['endpoint']['dual'])
        cert,detail=adaptive_build(a,b,c,x,y);result['adaptive_construction']=detail
        if cert:result.update(status='implicit_exact_proposal',implicit_certificate=dict(primal=write(BASE,cert['x']),dual_base=write(BASE,cert['y0']),basis=write(BASE,cert['basis'],'u32le'),inverse=write(BASE,cert['inverse'].ravel())))
        # Publish an additive second response; never overwrite the first one.
        result['preceding_proposal']=binding(output);result['elapsed_ns']=time.perf_counter_ns()-start;put(output.with_name('adaptive-response.json'),result)


def cell(model,lane,out):
    out.mkdir(parents=True,exist_ok=False);path=Path(model['model']['path'])
    if lane=='candidate':cmd=[str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_transform_run.py'),str(path),str(out/'response.json'),'--seconds','60','--rho-multiplier','16','--representation','factor']
    else:cmd=[str(PYTHON),'-B',__file__,'vendor','--lane',lane,'--model',str(path),'--output',str(out)]
    put(out/'started.json',dict(command=cmd,lane=lane,model=model['model']))
    proc=execute(cmd,out/'stdout',out/'stderr',90,None);put(out/'process.json',proc)
    response=read(out/'response.json') if (out/'response.json').exists() else {};strict=audit('copt_scale_off',path,path,out)
    post=out/'postprocess';post.mkdir();postproc=proofproc=None;postdata={};proof={};response_path=post/'response.json'
    start=time.perf_counter_ns()
    if response.get('endpoint'):
        postproc=execute([str(PYTHON),'-B',__file__,'endpoint','--model',str(path),'--response',str(out/'response.json'),'--output',str(response_path)],post/'stdout',post/'stderr',90,None);put(post/'process.json',postproc)
        if (post/'adaptive-response.json').exists():response_path=post/'adaptive-response.json'
        if response_path.exists():postdata=read(response_path)
    post_ns=time.perf_counter_ns()-start;start=time.perf_counter_ns()
    if postdata.get('certificate') or postdata.get('implicit_certificate'):
        script='lp_sp_pricing_factor_parallel_proof.py' if postdata.get('implicit_certificate') else 'lp_sp_pricing_scale_verify.py'
        proofproc=execute([str(PYTHON),'-B',str(ROOT/'tools'/script),str(path),str(response_path),str(post/'proof.json')],post/'proof-stdout',post/'proof-stderr',120,None);put(post/'proof-process.json',proofproc)
        if (post/'proof.json').exists():proof=read(post/'proof.json')
    proof_ns=time.perf_counter_ns()-start
    def passed(p):return bool(p and p['returncode']==0 and not p['timed_out'])
    native=response.get('solve_ns',response.get('native_ns'));raw_cost=model['encoding_ns']+proc['elapsed_ns']+strict['elapsed_ns']
    row=dict(id=out.name,family=model['name'],seed=model['seed'],lane=lane,rows=model['m'],columns=model['n'],nonzeros=model['nonzeros'],
        status=response.get('status','missing_response'),reason=response.get('reason'),route=response.get('route'),native_ns=native,
        timely=bool(passed(proc) and native is not None and native<=60*NS),raw_strict_accepted=strict['accepted'],
        accepted=bool(proof.get('accepted') and passed(postproc) and passed(proofproc)),certificate_kind=postdata.get('status'),
        encoding_ns=model['encoding_ns'],process_ns=proc['elapsed_ns'],raw_audit_ns=strict['elapsed_ns'],postprocess_ns=post_ns,proof_ns=proof_ns,
        raw_complete_ns=raw_cost,complete_ns=raw_cost+post_ns+proof_ns,
        response=binding(out/'response.json') if response else None,process=binding(out/'process.json'),raw_audit=binding(out/'audit.json'),
        reconstructed=binding(response_path) if postdata else None,proof=binding(post/'proof.json') if proof else None,
        proposal=response.get('proposal'),parameters=response.get('parameters'),gpu_confirmed=response.get('gpu_confirmed'),
        reconstruction_reason=postdata.get('adaptive_construction',postdata.get('implicit_construction',postdata.get('dyadic_reconstruction',{}))).get('reason'))
    if (out/'defaults.json').exists():row['defaults']=binding(out/'defaults.json')
    put(out/'result.json',row);print(json.dumps({k:row[k] for k in ('id','status','timely','raw_strict_accepted','accepted','complete_ns')}),flush=True);return row


def run(group,kind):
    f=validate();rows=[]
    for index,model in enumerate(f['models'][3*group:3*group+3]):
        lanes=['copt-auto'] if kind=='cpu' else (['candidate','copt-gpu-default'] if (group+index)%2==0 else ['copt-gpu-default','candidate'])
        for lane in lanes:
            if (dt.datetime.fromisoformat(f['wall_deadline_utc'])-dt.datetime.now(dt.timezone.utc)).total_seconds()<500:raise TimeoutError('final reporting envelope')
            rows.append(cell(model,lane,STUDY/'runs'/f"{model['name']}-{model['seed']}-{lane}"))
    put(STUDY/f'{kind}-group-{group}.json',dict(status='all_slots_disposed',rows=rows))


def vendor(lane,model,out):
    if lane=='copt-auto':return copt_auto(model,out,60)
    import lp_billion_copt_diagnostic as diagnostic
    original=diagnostic.settings;configure=diagnostic.DiagnosticNative.configure;defaults={}
    def settings(variant,gpu,memory):
        result=original('instrumented',gpu,memory);result['PDLPTol']=1e-9;return result
    def record(self,parameters):
        configure(self,parameters)
        if 'GPUMode' in parameters:defaults.update({name:self.get(name,True,True) for name in ('Scaling','Presolve','Dualize','LpMethod')})
    with patch.object(diagnostic,'settings',settings),patch.object(diagnostic.DiagnosticNative,'configure',record):copt(model,out,60)
    put(out/'defaults.json',defaults)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','run','vendor','endpoint']);p.add_argument('--group',type=int);p.add_argument('--kind',choices=['gpu','cpu']);p.add_argument('--lane');p.add_argument('--model',type=Path);p.add_argument('--response',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    if a.action=='freeze':freeze()
    elif a.action=='run':run(a.group,a.kind)
    elif a.action=='vendor':vendor(a.lane,a.model,a.output)
    else:endpoint(a.model,a.response,a.output)
