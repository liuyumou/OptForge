"""Fresh source-bound tall-factor comparisons and unchanged-route controls."""
import argparse
import datetime as dt
from pathlib import Path
import sys
import time
import json
from unittest.mock import patch
from lp_sp_pricing_budget import ROOT,BASE,put,binding,NS
from lp_sp_pricing_gpu_opt_compare import read,verify
from lp_sp_pricing_baselines import PYTHON,images,audit,copt
from lp_sp_pricing_geometry_copt_auto import child as copt_auto
from lp_sp_pricing_scale_experiment import generate
from lp_sp_pricing_factor_admit import validate as admission,sources
from lp_sp_pricing_factor_budget import allocation,APPROVAL
from lp_billion_owned_process import execute

STUDY=BASE/'factor-evaluation-v1'
SPECS=[dict(name='mixed-tall-1m',m=4000,n=1000,degree=250,scaled=False,mixed=True),
       dict(name='mixed-tall-4m',m=8000,n=2000,degree=500,scaled=False,mixed=True),
       dict(name='mixed-tall-16m',m=16000,n=4000,degree=1000,scaled=False,mixed=True),
       dict(name='dense-4m',m=2000,n=2000,degree=2000,scaled=False,mixed=False),
       dict(name='sparse-scaled-1m',m=8000,n=8000,degree=125,scaled=True,mixed=False)]
SEEDS=[123801,123821,123839]


def harness_sources():
    return sources()+[binding(ROOT/'tools'/name) for name in (
        'lp_sp_pricing_factor_run.py','lp_sp_pricing_factor_endpoint.py','lp_sp_pricing_factor_experiment.py',
        'lp_sp_pricing_scale_reconstruct.py','lp_sp_pricing_scale_verify.py','lp_sp_pricing_scale_experiment.py',
        'lp_sp_pricing_geometry_copt_auto.py','lp_sp_pricing_baselines.py')]


def freeze():
    gate=admission();alloc=allocation();STUDY.mkdir(exist_ok=False);models=[]
    for seed in SEEDS:
        for spec in SPECS:
            models.append(generate(spec,seed,STUDY/'models'/f"{spec['name']}-{seed}"))
    put(STUDY/'freeze.json',dict(status='frozen',admission=gate,allocation=binding(APPROVAL),sources=harness_sources(),
        models=models,lanes=['candidate','copt-gpu-1e9','copt-auto'],native_seconds=60,process_seconds=90,
        endpoint_process_seconds=90,independent_process_seconds=120,images=images(),
        wall_deadline_utc=alloc['wall_deadline_utc'],
        policy='Every returned endpoint receives identical dyadic then implicit reconstruction and cold independent proof. Raw strict 1e-9 audits remain separate. All preparation, construction, process startup, reconstruction and audits are charged.',
        controls='Previous candidate also runs on every fresh square model; candidate-cpu and inherited COPT GPU PDLPTol=1e-12 run on first-seed tall models. Rotated solver order; one timing per independent input; no cache flushing.',
        vendor_configuration='Primary GPU uses PDLPTol=1e-9, matching required raw audit tolerance; every accepted implicit certificate proves exact zero gap. All other inherited scale-off parameters unchanged. Automatic CPU control unchanged.',
        limitation='Synthetic dyadic inputs; tall exact-active primal reconstruction is restricted. Practical presolve, not completion of the paper algorithm.'))
    print(json.dumps(dict(status='frozen',models=len(models))),flush=True)


def validate():
    f=read(STUDY/'freeze.json');admission();allocation()
    for s in f['sources']:verify(s)
    verify(f['allocation'])
    if f['images']!=images():raise RuntimeError('images changed')
    for model in f['models']:verify(model['model']);verify(model['construction_audit'])
    return f


def cell(model,lane,out,seconds=60):
    out.mkdir(parents=True,exist_ok=False);path=Path(model['model']['path'])
    if lane in ('candidate','candidate-cpu','previous'):
        script='lp_sp_pricing_scale_run.py' if lane=='previous' else 'lp_sp_pricing_factor_run.py'
        cmd=[str(PYTHON),'-B',str(ROOT/'tools'/script),str(path),str(out/'response.json'),'--seconds',str(seconds)]
        if lane=='candidate-cpu':cmd.append('--cpu')
    else:cmd=[str(PYTHON),'-B',__file__,'vendor','--lane',lane,'--model',str(path),'--output',str(out),'--seconds',str(seconds)]
    put(out/'started.json',dict(command=cmd,model=model['model'],lane=lane))
    proc=execute(cmd,out/'stdout',out/'stderr',seconds+30,None);put(out/'process.json',proc)
    response=read(out/'response.json') if (out/'response.json').exists() else {}
    strict=audit('copt_scale_off',path,path,out)
    post=out/'postprocess';post.mkdir();postproc=None;proofproc=None;proof=dict(accepted=False,reason='no_endpoint');postdata={}
    post_start=time.perf_counter_ns()
    if response.get('endpoint'):
        cmd=[str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_factor_endpoint.py'),str(path),str(out/'response.json'),str(post/'response.json'),'--gpu']
        postproc=execute(cmd,post/'stdout',post/'stderr',90,None);put(post/'process.json',postproc)
        if (post/'response.json').exists():postdata=read(post/'response.json')
    post_ns=time.perf_counter_ns()-post_start
    proof_start=time.perf_counter_ns()
    if postdata.get('implicit_certificate') or postdata.get('certificate'):
        script='lp_sp_pricing_factor_proof.py' if postdata.get('implicit_certificate') else 'lp_sp_pricing_scale_verify.py'
        cmd=[str(PYTHON),'-B',str(ROOT/'tools'/script),str(path),str(post/'response.json'),str(post/'proof.json')]
        proofproc=execute(cmd,post/'proof-stdout',post/'proof-stderr',120,None);put(post/'proof-process.json',proofproc)
        if (post/'proof.json').exists():proof=read(post/'proof.json')
    proof_ns=time.perf_counter_ns()-proof_start
    def passed(p):return bool(p and p['returncode']==0 and not p['timed_out'])
    native=response.get('solve_ns',response.get('native_ns'));timely=passed(proc) and native is not None and native<=seconds*NS
    accepted=bool(proof.get('accepted') and passed(postproc) and passed(proofproc))
    row=dict(id=out.name,family=model['name'],seed=model['seed'],lane=lane,nonzeros=model['nonzeros'],
        status=response.get('status','missing_response'),route=response.get('route'),native_ns=native,timely=timely,
        raw_strict_accepted=strict['accepted'],accepted=accepted,certificate_kind=postdata.get('status'),
        encoding_ns=model['encoding_ns'],process_ns=proc['elapsed_ns'],raw_audit_ns=strict['elapsed_ns'],postprocess_ns=post_ns,proof_ns=proof_ns,
        complete_ns=model['encoding_ns']+proc['elapsed_ns']+strict['elapsed_ns']+post_ns+proof_ns,
        response=binding(out/'response.json') if response else None,raw_audit=binding(out/'audit.json'),
        reconstructed=binding(post/'response.json') if postdata else None,proof=binding(post/'proof.json') if (post/'proof.json').exists() else None,
        process=binding(out/'process.json'),proposal=response.get('proposal'),postprocess=postdata)
    put(out/'result.json',row);print(json.dumps({k:row[k] for k in ('id','status','accepted','raw_strict_accepted','complete_ns')}),flush=True)
    return row


def run(index):
    f=validate();model=f['models'][index];lanes=f['lanes'].copy()
    shift=index%3;lanes=lanes[shift:]+lanes[:shift]
    if model['m']==model['n']:lanes.append('previous')
    elif model['seed']==SEEDS[0]:lanes.extend(['candidate-cpu','previous','copt-gpu'])
    rows=[]
    for lane in lanes:
        left=(dt.datetime.fromisoformat(f['wall_deadline_utc'])-dt.datetime.now(dt.timezone.utc)).total_seconds()
        if left<600:raise TimeoutError('retain final reporting envelope')
        rows.append(cell(model,lane,STUDY/'runs'/f"{model['name']}-{model['seed']}-{lane}",f['native_seconds']))
    put(STUDY/f'group-{index}.json',dict(status='all_slots_disposed',rows=rows))


def develop():
    admission();out=BASE/'factor-development-v1';out.mkdir(exist_ok=False)
    spec=SPECS[1];model=generate(spec,123777,out/'model')
    put(out/'plan.json',dict(model=model,sources=harness_sources(),native_seconds=60))
    rows=[cell(model,lane,out/lane,60) for lane in ('candidate','copt-gpu')]
    put(out/'result.json',dict(rows=rows))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','run','vendor','develop'])
    p.add_argument('--index',type=int);p.add_argument('--lane');p.add_argument('--model',type=Path);p.add_argument('--output',type=Path)
    p.add_argument('--seconds',type=float,default=60);a=p.parse_args()
    if a.action=='freeze':freeze()
    elif a.action=='run':run(a.index)
    elif a.action=='develop':develop()
    elif a.lane=='copt-gpu':copt(a.model,a.output,a.seconds)
    elif a.lane=='copt-gpu-1e9':
        import lp_billion_copt_diagnostic as diagnostic
        original=diagnostic.settings
        def matched_settings(*args,**kwargs):
            parameters=original(*args,**kwargs);parameters['PDLPTol']=1e-9;return parameters
        with patch.object(diagnostic,'settings',matched_settings):copt(a.model,a.output,a.seconds)
    elif a.lane=='copt-auto':copt_auto(a.model,a.output,a.seconds)
    else:raise ValueError('lane')
