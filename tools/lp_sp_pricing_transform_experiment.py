"""Fresh matched tall projection representation comparison, three seeds."""
import argparse
import datetime as dt
from pathlib import Path
import json
import time
from unittest.mock import patch
from lp_sp_pricing_budget import ROOT,BASE,NS,put,binding
from lp_sp_pricing_gpu_opt_compare import read,verify
from lp_sp_pricing_baselines import PYTHON,images,audit,copt
from lp_sp_pricing_scale_experiment import generate
from lp_sp_pricing_factor_experiment import SPECS,STUDY as PRIMARY,validate as primary
from lp_sp_pricing_transform_admit import validate as admission,sources
from lp_sp_pricing_factor_budget import allocation
from lp_billion_owned_process import execute

STUDY=BASE/'transform-evaluation-v1';SEEDS=[124401,124421,124439]
FOLLOWUP_SPECS=[*SPECS[:3],dict(name='mixed-scaled-tall-4m',m=8000,n=2000,degree=500,scaled=True,mixed=True),SPECS[3]]


def freeze():
    gate=admission();prior=primary();STUDY.mkdir(exist_ok=False);models=[]
    selection=read(BASE/'transform-selection-v1/result.json')
    if selection['status']!='selected' or read(BASE/'resources/transform-selection-v1.settlement.json')['status']!='passed':raise RuntimeError('selection admission')
    for seed in SEEDS:
        for spec in FOLLOWUP_SPECS:models.append(generate(spec,seed,STUDY/'models'/f"{spec['name']}-{seed}"))
    put(STUDY/'freeze.json',dict(status='frozen',admission=gate,primary=binding(PRIMARY/'freeze.json'),models=models,
        sources=sources()+[binding(ROOT/'tools'/name) for name in ('lp_sp_pricing_transform_endpoint.py','lp_sp_pricing_transform_experiment.py')],
        native_seconds=60,process_seconds=90,postprocess_seconds=90,proof_seconds=120,
        selection=binding(BASE/'transform-selection-v1/result.json'),rho_multiplier=selection['rho_multiplier'],representation=selection['representation'],
        lanes=['optimized','factor','copt-gpu-1e9'],images=images(),wall_deadline_utc=allocation()['wall_deadline_utc'],
        additional_control='Each row-scaled tall holdout also runs COPT GPU PDLP with installed default Scaling, the same Presolve=0 and PDLPTol=1e-9. This avoids relying solely on a scaling-disabled vendor control on scaled data.',
        disclosure='Prospective follow-up after first primary outcomes: precomputed GPU transform versus admitted triangular-solve GPU projection and matched COPT. Common direct implicit certificate policy for all three lanes. Fresh inputs only; primary cohort unchanged.',
        memory_tradeoff='Additional resident m*n FP64 operator replaces per-iteration triangular solves. No slack-space null basis is formed.'))


def validate():
    admission();primary();f=read(STUDY/'freeze.json')
    for item in f['sources']:verify(item)
    verify(f['primary'])
    verify(f['selection'])
    for model in f['models']:verify(model['model']);verify(model['construction_audit'])
    if f['images']!=images():raise RuntimeError('images')
    return f


def cell(model,lane,out,rho_multiplier=1,representation='transform'):
    out.mkdir(parents=True,exist_ok=False);path=Path(model['model']['path'])
    if lane in ('factor','optimized'):
        script='lp_sp_pricing_transform_run.py' if lane=='optimized' else 'lp_sp_pricing_factor_run.py'
        cmd=[str(PYTHON),'-B',str(ROOT/'tools'/script),str(path),str(out/'response.json'),'--seconds','60']
        if lane=='optimized':cmd+=['--rho-multiplier',str(rho_multiplier),'--representation',representation]
    elif lane=='copt-gpu-scaling-auto':cmd=[str(PYTHON),'-B',__file__,'vendor','--model',str(path),'--output',str(out)]
    else:cmd=[str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_factor_experiment.py'),'vendor','--lane',lane,'--model',str(path),'--output',str(out),'--seconds','60']
    put(out/'started.json',dict(command=cmd,lane=lane,model=model['model']))
    proc=execute(cmd,out/'stdout',out/'stderr',90,None);put(out/'process.json',proc)
    response=read(out/'response.json') if (out/'response.json').exists() else {};strict=audit('copt_scale_off',path,path,out)
    post=out/'postprocess';post.mkdir();postproc=proofproc=None;postdata={};proof=dict(accepted=False)
    start=time.perf_counter_ns()
    if response.get('endpoint'):
        cmd=[str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_transform_endpoint.py'),str(path),str(out/'response.json'),str(post/'response.json')]
        postproc=execute(cmd,post/'stdout',post/'stderr',90,None);put(post/'process.json',postproc)
        if (post/'response.json').exists():postdata=read(post/'response.json')
    post_ns=time.perf_counter_ns()-start;start=time.perf_counter_ns()
    if postdata.get('implicit_certificate') or postdata.get('certificate'):
        script='lp_sp_pricing_factor_parallel_proof.py' if postdata.get('implicit_certificate') else 'lp_sp_pricing_scale_verify.py'
        cmd=[str(PYTHON),'-B',str(ROOT/'tools'/script),str(path),str(post/'response.json'),str(post/'proof.json')]
        proofproc=execute(cmd,post/'proof-stdout',post/'proof-stderr',120,None);put(post/'proof-process.json',proofproc)
        if (post/'proof.json').exists():proof=read(post/'proof.json')
    proof_ns=time.perf_counter_ns()-start
    def passed(p):return bool(p and p['returncode']==0 and not p['timed_out'])
    native=response.get('solve_ns',response.get('native_ns'))
    row=dict(id=out.name,family=model['name'],seed=model['seed'],lane=lane,nonzeros=model['nonzeros'],status=response.get('status','missing_response'),
        timely=bool(passed(proc) and native is not None and native<=60*NS),accepted=bool(proof.get('accepted') and passed(postproc) and passed(proofproc)),
        raw_strict_accepted=strict['accepted'],native_ns=native,encoding_ns=model['encoding_ns'],process_ns=proc['elapsed_ns'],
        raw_audit_ns=strict['elapsed_ns'],postprocess_ns=post_ns,proof_ns=proof_ns,
        complete_ns=model['encoding_ns']+proc['elapsed_ns']+strict['elapsed_ns']+post_ns+proof_ns,
        response=binding(out/'response.json') if response else None,raw_audit=binding(out/'audit.json'),
        reconstructed=binding(post/'response.json') if postdata else None,proof=binding(post/'proof.json') if (post/'proof.json').exists() else None,
        process=binding(out/'process.json'),proposal=response.get('proposal'))
    if (out/'default-settings.json').exists():row['configuration_defaults']=binding(out/'default-settings.json')
    put(out/'result.json',row);print(json.dumps({k:row[k] for k in ('id','status','accepted','complete_ns')}),flush=True)
    return row


def run(group):
    f=validate();rows=[]
    width=len(FOLLOWUP_SPECS)
    for index,model in enumerate(f['models'][width*group:width*group+width]):
        shift=(group+index)%3;lanes=f['lanes'][shift:]+f['lanes'][:shift]
        if model['scaled']:lanes.append('copt-gpu-scaling-auto')
        for lane in lanes:
            left=(dt.datetime.fromisoformat(f['wall_deadline_utc'])-dt.datetime.now(dt.timezone.utc)).total_seconds()
            if left<600:raise TimeoutError('retain final reporting envelope')
            rows.append(cell(model,lane,STUDY/'runs'/f"{model['name']}-{model['seed']}-{lane}",f['rho_multiplier'],f['representation']))
    put(STUDY/f'group-{group}.json',dict(status='all_slots_disposed',rows=rows))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','run','vendor']);p.add_argument('--group',type=int)
    p.add_argument('--model',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    if a.action=='freeze':freeze()
    elif a.action=='run':run(a.group)
    else:
        import lp_billion_copt_diagnostic as diagnostic
        original=diagnostic.settings;configure=diagnostic.DiagnosticNative.configure;defaults={}
        def settings(variant,gpu,memory):
            result=original('instrumented',gpu,memory);result['PDLPTol']=1e-9;return result
        def record_defaults(self,parameters):
            configure(self,parameters)
            if 'GPUMode' in parameters:
                defaults.update({name:self.get(name,True,True) for name in ('Scaling','Presolve','Dualize','LpMethod')})
        with patch.object(diagnostic,'settings',settings),patch.object(diagnostic.DiagnosticNative,'configure',record_defaults):copt(a.model,a.output,60)
        put(a.output/'default-settings.json',defaults)
