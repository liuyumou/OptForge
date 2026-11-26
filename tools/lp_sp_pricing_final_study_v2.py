"""Prospective final rectangular/tall holdouts and unchanged-path regressions."""
import argparse
import datetime as dt
from pathlib import Path
from unittest.mock import patch
from lp_sp_pricing_budget import ROOT,BASE,NS,binding,put,accounting
from lp_sp_pricing_baselines import PYTHON,images
from lp_sp_pricing_gpu_opt_compare import read,verify
from lp_sp_pricing_final_budget_v2 import allocation,CPU,GPU
from lp_sp_pricing_final_screened_admit import validate
from lp_sp_pricing_nontall_experiment import generate,SPECS as NON_TALL
from lp_sp_pricing_factor_experiment import SPECS as TALL
import lp_sp_pricing_recovery_parallel_experiment as common

STUDY=BASE/'final-evaluation-v2';DEV=BASE/'final-development-v2';ENVELOPE=BASE/'final-envelope-v2.json'
FOCUS=[NON_TALL[3]]+[dict(s,layout='band',shift=1) for s in TALL[:3]]+[dict(TALL[1],name='mixed-scaled-tall-4m',scaled=True,layout='band',shift=1)]
CONTROLS=[dict(NON_TALL[0],name='dense-wide-4m',m=1000,n=4000,degree=4000),NON_TALL[1],NON_TALL[2],NON_TALL[4],NON_TALL[6]]
SEEDS=[128101,128123,128149];CONTROL_SEEDS=[128201,128223,128249]

def sources():return [binding(__file__),binding(ROOT/'tools/lp_sp_pricing_final_driver_v2.py')]

def cell(model,lane,out):
    execute=common.previous.execute;commands=[]
    def command(cmd,*args,**kwargs):
        effective=list(cmd)
        if len(effective)>2:
            source=Path(effective[2]).name
            if source=='lp_sp_pricing_recovery_run_fast.py':
                effective[2]=str(ROOT/'tools'/('lp_sp_pricing_final_screened_run.py' if lane=='candidate' else 'lp_sp_pricing_rectangular_run.py'))
                if lane!='candidate':effective+=['--rho-multiplier','16']
            elif source=='lp_sp_pricing_recovery_endpoint_balanced.py':effective[2]=str(ROOT/'tools/lp_sp_pricing_final_endpoint.py')
            elif source=='lp_sp_pricing_factor_parallel_proof.py':effective[2]=str(ROOT/'tools/lp_sp_pricing_dual_fast_proof.py')
            commands.append(dict(command=effective,source=binding(effective[2])))
        return execute(effective,*args,**kwargs)
    with patch.object(common.previous,'execute',command):row=common.cell(model,lane,out,'cpu')
    put(out/'effective-commands.json',dict(commands=commands));row['effective_commands']=binding(out/'effective-commands.json');return row

def development():
    gate=validate();DEV.mkdir(exist_ok=False);models=[];rows=[]
    for i,spec in enumerate(FOCUS):
        model=generate(spec,128021+2*i,DEV/'models'/spec['name']);models.append(model)
        for lane in ('candidate-before','candidate'):rows.append(cell(model,lane,DEV/'runs'/f'{model["name"]}-{lane}'))
    put(DEV/'result.json',dict(status='all_10_slots_disposed',sources=sources(),admission=gate,models=models,rows=rows,
        prespecified_rule='All candidate endpoints timely and exactly certified; per-family complete new/before <=1.10. Common final postprocessor and independent proof are identical for before/new. Separate held-out inputs required; development measurements are not final comparisons.'))

def envelope():
    validate();allocation();cpu,gpu=accounting(BASE),accounting(BASE,True);d=read(DEV/'result.json')
    if d['sources']!=sources() or read(BASE/'resources/final-development-v2.settlement.json')['status']!='passed':raise RuntimeError('development supervision/source')
    for spec in FOCUS:
        rs={r['lane']:r for r in d['rows'] if r['family']==spec['name']};a,b=rs['candidate-before'],rs['candidate']
        if not all(r['accepted'] and r['timely'] for r in rs.values()) or b['complete_ns']>1.10*a['complete_ns']:raise RuntimeError('development preservation gate: '+spec['name'])
    if cpu['confirmation']+11040*NS>CPU['confirmation']*NS or gpu['confirmation']+540*NS>GPU['confirmation']*NS:raise RuntimeError('full final study reserve')
    if (dt.datetime.fromisoformat(allocation()['wall_deadline_utc'])-dt.datetime.now(dt.timezone.utc)).total_seconds()<3500:raise RuntimeError('final study/report wall envelope')
    put(ENVELOPE,dict(status='complete_reserve_fits',sources=sources(),cpu_phase_ns=cpu,gpu_phase_ns=gpu,full_cpu_seconds=11040,full_gpu_seconds=540,development=binding(DEV/'result.json'),
        settlements=[binding(p) for p in sorted((BASE/'resources').glob('*.settlement.json'))],
        scope='15 rectangular/tall models x before/new candidate and GPU/CPU COPT =60 attempts; 15 square/irregular/wide regression models x before/new=30 attempts. All sources, cases, native allowances and acceptance fixed before any holdout.'))

def freeze():
    gate=validate();e=read(ENVELOPE)
    if e['sources']!=sources():raise RuntimeError('final harness changed')
    verify(e['development'])
    for r in e['settlements']:verify(r)
    STUDY.mkdir(exist_ok=False);models=[];controls=[]
    for spec in FOCUS:
        for seed in SEEDS:models.append(generate(spec,seed,STUDY/'models'/f'{spec["name"]}-{seed}'))
    for spec in CONTROLS:
        for seed in CONTROL_SEEDS:controls.append(generate(spec,seed,STUDY/'models'/f'{spec["name"]}-{seed}'))
    put(STUDY/'freeze.json',dict(status='frozen',sources=sources(),admission=gate,envelope=binding(ENVELOPE),models=models,controls=controls,images=images(),wall_deadline_utc=allocation()['wall_deadline_utc'],
        native_seconds=60,process_seconds=90,reconstruction_seconds=90,proof_seconds=120,lanes=['candidate-before','candidate','copt-gpu-default','copt-auto'],
        unchanged_path_rule='All before/new explicit certificates identical where explicit; all exact certificates preserved, per-family median new/before complete <=1.10. Three fresh seeds per family.',
        complete_cost='Common original generation/encoding + cold solver process + raw 1e-9 audit + common endpoint construction + cold independent exact proof. Every prep/import/transfer/failed trial is included.'))

def frozen():
    validate();f=read(STUDY/'freeze.json')
    if f['sources']!=sources() or f['images']!=images():raise RuntimeError('frozen final sources/images changed')
    for k in ('admission','envelope'):verify(f[k])
    for m in f['models']+f['controls']:verify(m['model']);verify(m['construction_audit'])
    return f

def group(kind):
    f=frozen();rows=[]
    for i,model in enumerate(f['controls'] if kind=='control' else f['models']):
        lanes=['copt-auto'] if kind=='cpu' else (['candidate-before','candidate'] if kind=='control' else ['candidate-before','candidate','copt-gpu-default'])
        lanes=lanes[i%len(lanes):]+lanes[:i%len(lanes)]
        for lane in lanes:
            if (dt.datetime.fromisoformat(f['wall_deadline_utc'])-dt.datetime.now(dt.timezone.utc)).total_seconds()<500:raise TimeoutError('final report margin')
            rows.append(cell(model,lane,STUDY/'runs'/f'{model["name"]}-{model["seed"]}-{lane}'))
    put(STUDY/f'{kind}-group.json',dict(status='all_slots_disposed',rows=rows))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['development','envelope','freeze','group']);p.add_argument('--kind',choices=['gpu','cpu','control']);a=p.parse_args()
    if a.action=='group':group(a.kind)
    else:globals()[a.action]()
