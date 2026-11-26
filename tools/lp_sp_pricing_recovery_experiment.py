"""Fresh recovery holdouts and unchanged-path regression controls."""
import argparse
import datetime as dt
import json
from pathlib import Path
import time
from lp_sp_pricing_budget import ROOT,BASE,NS,binding,put,accounting
from lp_sp_pricing_baselines import PYTHON,audit,images
from lp_sp_pricing_gpu_opt_compare import read,verify
from lp_sp_pricing_nontall_experiment import SPECS as OLD_SPECS,generate
from lp_sp_pricing_recovery_admit import validate
from lp_sp_pricing_recovery_budget import allocation,CPU,GPU
from lp_billion_owned_process import execute

STUDY=BASE/'recovery-evaluation-v1';DEV=BASE/'recovery-development-v1';ENVELOPE=BASE/'recovery-envelope-v1.json'
SPECS=[OLD_SPECS[0],dict(OLD_SPECS[0],name='dense-wide-4m',m=1000,n=4000,degree=4000),OLD_SPECS[1],OLD_SPECS[2],OLD_SPECS[3]]
CONTROLS=[OLD_SPECS[4],OLD_SPECS[6]];SEEDS=[126101,126123,126149];CONTROL_SEEDS=[126201,126223,126249]

def cell(model,lane,out,backend='auto'):
    out.mkdir(parents=True,exist_ok=False);path=Path(model['model']['path'])
    if lane=='old':cmd=[str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_transform_run.py'),str(path),str(out/'response.json'),'--seconds','60','--rho-multiplier','16','--representation','factor']
    elif lane.startswith('candidate'):
        cmd=[str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_recovery_run.py'),str(path),str(out/'response.json'),'--seconds','60','--wide-backend',backend]
    else:cmd=[str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_nontall_experiment.py'),'vendor','--lane',lane,'--model',str(path),'--output',str(out)]
    put(out/'started.json',dict(command=cmd,lane=lane,model=model['model']))
    proc=execute(cmd,out/'stdout',out/'stderr',90,None);put(out/'process.json',proc)
    raw=read(out/'response.json') if (out/'response.json').exists() else {};strict=audit('copt_scale_off',path,path,out)
    post=out/'postprocess';post.mkdir();postproc=proofproc=None;data={};proof={};start=time.perf_counter_ns()
    if raw.get('endpoint'):
        postproc=execute([str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_recovery_endpoint.py'),str(path),str(out/'response.json'),str(post/'response.json')],post/'stdout',post/'stderr',90,None);put(post/'process.json',postproc)
        if (post/'response.json').exists():data=read(post/'response.json')
    post_ns=time.perf_counter_ns()-start;start=time.perf_counter_ns()
    if data.get('certificate') or data.get('implicit_certificate') or data.get('implicit_primal_certificate'):
        script='lp_sp_pricing_primal_proof.py' if data.get('implicit_primal_certificate') else ('lp_sp_pricing_factor_parallel_proof.py' if data.get('implicit_certificate') else 'lp_sp_pricing_scale_verify.py')
        proofproc=execute([str(PYTHON),'-B',str(ROOT/'tools'/script),str(path),str(post/'response.json'),str(post/'proof.json')],post/'proof-stdout',post/'proof-stderr',120,None);put(post/'proof-process.json',proofproc)
        if (post/'proof.json').exists():proof=read(post/'proof.json')
    proof_ns=time.perf_counter_ns()-start
    passed=lambda p:bool(p and p['returncode']==0 and not p['timed_out'])
    native=raw.get('solve_ns',raw.get('native_ns'));raw_cost=model['encoding_ns']+proc['elapsed_ns']+strict['elapsed_ns']
    row=dict(id=out.name,family=model['name'],seed=model['seed'],lane=lane,backend=backend,rows=model['m'],columns=model['n'],nonzeros=model['nonzeros'],
        status=raw.get('status','missing_response'),reason=raw.get('reason'),route=raw.get('route'),native_ns=native,
        timely=bool(passed(proc) and native is not None and native<=60*NS),raw_strict_accepted=strict['accepted'],
        accepted=bool(proof.get('accepted') and passed(postproc) and passed(proofproc)),certificate_kind=data.get('status'),
        encoding_ns=model['encoding_ns'],process_ns=proc['elapsed_ns'],raw_audit_ns=strict['elapsed_ns'],postprocess_ns=post_ns,proof_ns=proof_ns,raw_complete_ns=raw_cost,complete_ns=raw_cost+post_ns+proof_ns,
        response=binding(out/'response.json') if raw else None,process=binding(out/'process.json'),raw_audit=binding(out/'audit.json'),
        reconstructed=binding(post/'response.json') if data else None,proof=binding(post/'proof.json') if proof else None,
        proposal=raw.get('proposal'),parameters=raw.get('parameters'),gpu_confirmed=raw.get('gpu_confirmed'),
        reconstruction_reason=data.get('implicit_primal_construction',data.get('adaptive_construction',data.get('implicit_construction',data.get('dyadic_reconstruction',{})))).get('reason'))
    if (out/'defaults.json').exists():row['defaults']=binding(out/'defaults.json')
    put(out/'result.json',row);print(json.dumps({k:row[k] for k in ('id','status','timely','accepted','complete_ns','reconstruction_reason')}),flush=True);return row

def development():
    validate();DEV.mkdir(exist_ok=False);rows=[];models=[]
    for i,spec in enumerate((SPECS[0],SPECS[2],SPECS[3],SPECS[4])):
        model=generate(spec,126001+2*i,DEV/'models'/spec['name']);models.append(model)
        for lane,backend in ([('candidate-cpu','cpu'),('candidate-gpu','gpu')] if i<2 else [('candidate','auto')]):
            rows.append(cell(model,lane,DEV/'runs'/f"{spec['name']}-{lane}",backend))
    put(DEV/'result.json',dict(status='all_slots_disposed',models=models,rows=rows,sources=sources()))

def sources():
    return [binding(ROOT/'tools'/name) for name in ('lp_sp_pricing_recovery_experiment.py','lp_sp_pricing_recovery_driver.py','lp_sp_pricing_recovery_budget.py')]

def envelope():
    validate();a=allocation();cpu,gpu=accounting(BASE),accounting(BASE,True)
    if cpu['confirmation']+12720*NS>CPU['confirmation']*NS or gpu['confirmation']+1020*NS>GPU['confirmation']*NS:raise RuntimeError('full holdout reserve does not fit')
    if (dt.datetime.fromisoformat(a['wall_deadline_utc'])-dt.datetime.now(dt.timezone.utc)).total_seconds()<3600:raise RuntimeError('holdout/report envelope')
    if read(BASE/'resources/recovery-development-v1.settlement.json')['status']!='passed':raise RuntimeError('development supervision')
    development=read(DEV/'result.json')
    if development['sources']!=sources():raise RuntimeError('development harness changed')
    if not all(r['accepted'] and r['timely'] for r in development['rows']):raise RuntimeError('development capability gap')
    # A single development pair is a policy choice, not a performance claim.
    selected={}
    for name in ('dense-wide-1m','sparse-wide-1m'):
        rs={r['lane']:r for r in development['rows'] if r['family']==name}
        selected[name]='gpu' if rs['candidate-gpu']['complete_ns']<.9*rs['candidate-cpu']['complete_ns'] else 'cpu'
    selected['dense-wide-4m']=selected['dense-wide-1m']
    put(ENVELOPE,dict(status='complete_reserve_fits_before_launch',source=binding(__file__),cpu_phase_ns=cpu,gpu_phase_ns=gpu,
        full_reserves=dict(cpu_seconds=12720,gpu_seconds=1020),backend=selected,development=binding(DEV/'result.json'),
        rule='Use GPU wide proposals only when cold complete development cost improves at least ten percent. Validate on separate holdouts; all development alternatives retained.',
        settlements=[binding(p) for p in sorted((BASE/'resources').glob('*.settlement.json'))]))

def freeze():
    gate=validate();a=allocation();e=read(ENVELOPE);verify(e['source']);verify(e['development'])
    for item in e['settlements']:verify(item)
    STUDY.mkdir(exist_ok=False);models=[];controls=[]
    for spec in SPECS:
        for seed in SEEDS:models.append(generate(spec,seed,STUDY/'models'/f"{spec['name']}-{seed}"))
    for spec in CONTROLS:
        for seed in CONTROL_SEEDS:controls.append(generate(spec,seed,STUDY/'models'/f"{spec['name']}-{seed}"))
    put(STUDY/'freeze.json',dict(status='frozen',sources=sources(),admission=gate,envelope=binding(ENVELOPE),backend=e['backend'],
        models=models,controls=controls,images=images(),wall_deadline_utc=a['wall_deadline_utc'],native_seconds=60,process_seconds=90,reconstruction_seconds=90,proof_seconds=120,
        lanes=['candidate','copt-gpu-default','copt-auto'],control_lanes=['old','candidate'],
        scope='15 focus models x 3 lanes plus six square/irregular models x old/new lanes. One cold run per seed, rotated order. All preparation and cold common certification included.',
        certificate_policy='Existing common dyadic/implicit-dual reconstruction, then additive full-row implicit primal recovery; same postprocessor and full independent CPU proof for every lane.',
        regression_rule='No lost exact certificates; all explicit square/irregular certificates identical; per-family median new/old complete time <=1.10. Three observations describe regression evidence, not a hard performance guarantee.'))

def frozen():
    validate();f=read(STUDY/'freeze.json')
    if f['sources']!=sources() or f['images']!=images():raise RuntimeError('frozen harness/images changed')
    for key in ('admission','envelope'):verify(f[key])
    for m in f['models']+f['controls']:verify(m['model']);verify(m['construction_audit'])
    return f

def group(index,kind):
    f=frozen();rows=[];models=(f['controls'] if kind=='control' else f['models'])[3*index:3*index+3]
    for i,model in enumerate(models):
        lanes=['copt-auto'] if kind=='cpu' else (['old','candidate'] if kind=='control' else ['candidate','copt-gpu-default'])
        if kind!='cpu' and (i+index)%2:lanes=lanes[::-1]
        for lane in lanes:
            if (dt.datetime.fromisoformat(f['wall_deadline_utc'])-dt.datetime.now(dt.timezone.utc)).total_seconds()<500:raise TimeoutError('report envelope')
            rows.append(cell(model,lane,STUDY/'runs'/f"{model['name']}-{model['seed']}-{lane}",f['backend'].get(model['name'],'auto')))
    put(STUDY/f'{kind}-group-{index}.json',dict(status='all_slots_disposed',rows=rows))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['development','envelope','freeze','group']);p.add_argument('--index',type=int);p.add_argument('--kind',choices=['gpu','cpu','control']);a=p.parse_args()
    if a.action=='development':development()
    elif a.action=='envelope':envelope()
    elif a.action=='freeze':freeze()
    else:group(a.index,a.kind)
