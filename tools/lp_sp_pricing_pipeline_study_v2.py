"""Prospective cached-correction development, fresh COPT pairs and regressions."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
from pathlib import Path
import statistics
from unittest.mock import patch
import numpy as np
from lp_sp_pricing_budget import ROOT,BASE,NS,binding,put,accounting
from lp_sp_pricing_baselines import PYTHON,images
from lp_sp_pricing_gpu_opt_compare import read,verify
from lp_sp_pricing_pipeline_budget_v2 import allocation,CPU,GPU
from lp_sp_pricing_pipeline_lazy_admit import validate
from lp_sp_pricing_nontall_experiment import generate,arrays
from lp_sp_pricing_final_study_v2 import FOCUS as PREVIOUS_FOCUS,CONTROLS
from sp_pricing.factor_projection import CpuProjection,GpuProjection,inverse_proposal
from sp_pricing.implicit_certificate import inverse_bound
import lp_sp_pricing_recovery_parallel_experiment as common

STUDY=BASE/'pipeline-evaluation-v2';DEV=BASE/'pipeline-development-v2';ENVELOPE=BASE/'pipeline-envelope-v2.json'
FOCUS=[dict(PREVIOUS_FOCUS[1],name='mixed-scaled-tall-1m',scaled=True),PREVIOUS_FOCUS[-1]]
GPU_CONTROLS=[PREVIOUS_FOCUS[i] for i in (0,2,3)]
CONFIG={'candidate-cpu-pipeline':['--inverse-backend','cpu'],'candidate-gpu-pipeline':['--inverse-backend','gpu']}
SEEDS=[129101,129123,129149];CONTROL_SEEDS=[129201,129223,129249]

def sources():return [binding(__file__),binding(ROOT/'tools/lp_sp_pricing_pipeline_driver_v2.py')]

def cell(model,lane,out,configuration=None):
    execute=common.previous.execute;commands=[]
    def command(cmd,*args,**kwargs):
        effective=list(cmd)
        if len(effective)>2:
            name=Path(effective[2]).name
            if name=='lp_sp_pricing_recovery_run_fast.py':
                effective[2]=str(ROOT/'tools'/('lp_sp_pricing_final_screened_run.py' if lane=='candidate-before' else 'lp_sp_pricing_pipeline_lazy_run.py'))
                if lane!='candidate-before':effective+=CONFIG.get(lane,configuration or [])
            elif name=='lp_sp_pricing_recovery_endpoint_balanced.py':effective[2]=str(ROOT/'tools/lp_sp_pricing_final_endpoint.py')
            elif name=='lp_sp_pricing_factor_parallel_proof.py':effective[2]=str(ROOT/'tools/lp_sp_pricing_dual_fast_proof.py')
            commands.append(dict(command=effective,source=binding(effective[2])))
        return execute(effective,*args,**kwargs)
    with patch.object(common.previous,'execute',command):row=common.cell(model,lane,out,'cpu')
    put(out/'effective-commands.json',dict(commands=commands));row['effective_commands']=binding(out/'effective-commands.json');return row

def choose(rows):
    eligible={}
    for lane in CONFIG:
        costs=[]
        for spec in FOCUS:
            rs={r['lane']:r for r in rows if r['family']==spec['name']};a,b=rs['candidate-before'],rs[lane]
            if not all(r['accepted'] and r['timely'] for r in (a,b)) or b['complete_ns']>1.05*a['complete_ns']:break
            costs.append(b['complete_ns'])
        else:eligible[lane]=sum(costs)
    if not eligible:raise RuntimeError('no admissible lazy correction configuration')
    best=min(eligible,key=eligible.get);cpu=eligible.get('candidate-cpu-pipeline')
    if cpu is not None and eligible[best]>.95*cpu:best='candidate-cpu-pipeline'
    return dict(lane=best,arguments=CONFIG[best],complete_cost_sums_ns=eligible)

def development():
    gate=validate();DEV.mkdir(exist_ok=False);quality=BASE/'pipeline-development-v1/quality.json'
    if read(quality)['status']!='passed':raise RuntimeError('retained concurrent GPU differential')
    models=[];rows=[];controls=[];regression=[]
    for i,spec in enumerate(FOCUS):
        model=generate(spec,129075+2*i,DEV/'models'/spec['name']);models.append(model)
        for lane in ['candidate-before']+list(CONFIG):rows.append(cell(model,lane,DEV/'runs'/f'{model["name"]}-{lane}'))
    choice=choose(rows)
    for spec in GPU_CONTROLS:
        model=generate(spec,129081,DEV/'models'/spec['name']);controls.append(model)
        for lane in ('candidate-before','candidate'):regression.append(cell(model,lane,DEV/'runs'/f'{model["name"]}-{lane}',choice['arguments']))
    put(DEV/'result.json',dict(status='all_12_slots_disposed',models=models,rows=rows,regression_models=controls,regression_rows=regression,sources=sources(),admission=gate,quality=binding(quality),choice=choice,
        selection_rule='All selected focus endpoints timely/exact and <=1.05 reference complete cost per model. Minimize sum; require at least 5% improvement over CPU pipeline to select GPU. Three fresh unscaled GPU regression pairs: same endpoint/steps and <=1.10 complete cost. Previous development and every outcome retained.'))

def selected():
    validate();d=read(DEV/'result.json')
    if d['sources']!=sources() or read(BASE/'resources/pipeline-development-v2.settlement.json')['status']!='passed':raise RuntimeError('refined development source/supervision')
    verify(d['quality']);choice=choose(d['rows'])
    if choice!=d['choice']:raise RuntimeError('configuration choice changed')
    for spec in GPU_CONTROLS:
        rs={r['lane']:r for r in d['regression_rows'] if r['family']==spec['name']};a,b=rs['candidate-before'],rs['candidate']
        ar,br=read(a['response']['path']),read(b['response']['path'])
        if not all(r['accepted'] and r['timely'] for r in (a,b)) or b['complete_ns']>1.10*a['complete_ns'] or ar['endpoint']!=br['endpoint'] or ar['proposal']['steps']!=br['proposal']['steps']:raise RuntimeError('unscaled GPU regression')
    return choice

def envelope():
    choice=selected();allocation();cpu,gpu=accounting(BASE),accounting(BASE,True)
    if cpu['confirmation']+4080*NS>CPU['confirmation']*NS or gpu['confirmation']+120*NS>GPU['confirmation']*NS:raise RuntimeError('full holdout reserve')
    put(ENVELOPE,dict(status='complete_reserve_fits',sources=sources(),choice=choice,development=binding(DEV/'result.json'),cpu_phase_ns=cpu,gpu_phase_ns=gpu,full_cpu_seconds=4080,full_gpu_seconds=120,settlements=[binding(p) for p in sorted((BASE/'resources').glob('*.settlement.json'))]))

def freeze():
    gate=validate();choice=selected();e=read(ENVELOPE)
    if e['sources']!=sources() or e['choice']!=choice:raise RuntimeError('prospective envelope changed')
    for item in e['settlements']:verify(item)
    STUDY.mkdir(exist_ok=False);models=[];controls=[]
    for spec in FOCUS:
        for seed in SEEDS:models.append(generate(spec,seed,STUDY/'models'/f'{spec["name"]}-{seed}'))
    for spec in CONTROLS:
        for seed in CONTROL_SEEDS:controls.append(generate(spec,seed,STUDY/'models'/f'{spec["name"]}-{seed}'))
    put(STUDY/'freeze.json',dict(status='frozen',sources=sources(),admission=gate,envelope=binding(ENVELOPE),choice=choice,models=models,controls=controls,gpu_regressions=binding(DEV/'result.json'),images=images(),wall_deadline_utc=allocation()['wall_deadline_utc'],native_seconds=60,process_seconds=90,reconstruction_seconds=90,proof_seconds=120,
        roster='54 fresh holdout attempts on 21 models: six scaled-tall models x before/new/GPU-COPT/CPU-COPT; fifteen CPU regression models x before/new. Six separate fresh GPU regression attempts on three models are retained from the frozen development protocol.',
        unchanged_path_rule='All exact certificates preserved; identical explicit certificates where present; median current/reference complete <=1.10 per family. Unscaled GPU paths must retain step counts and endpoints.',
        complete_cost='Common original generation/encoding + cold solver process + raw 1e-9 audit + common endpoint construction + cold independent exact proof, including cached preparation, failed checks, speculative GPU work and worker drain.'))

def frozen():
    validate();f=read(STUDY/'freeze.json')
    if f['sources']!=sources() or f['images']!=images():raise RuntimeError('pipeline sources/images changed')
    for key in ('admission','envelope'):verify(f[key])
    for m in f['models']+f['controls']:verify(m['model']);verify(m['construction_audit'])
    return f

def group(kind):
    f=frozen();rows=[]
    for i,model in enumerate(f['controls'] if kind=='control' else f['models']):
        lanes=['copt-auto'] if kind=='cpu' else (['candidate-before','candidate'] if kind=='control' else ['candidate-before','candidate','copt-gpu-default']);lanes=lanes[i%len(lanes):]+lanes[:i%len(lanes)]
        for lane in lanes:rows.append(cell(model,lane,STUDY/'runs'/f'{model["name"]}-{model["seed"]}-{lane}',f['choice']['arguments']))
    put(STUDY/f'{kind}-group.json',dict(status='all_slots_disposed',rows=rows))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['development','envelope','freeze','group']);p.add_argument('--kind',choices=['gpu','cpu','control']);a=p.parse_args();group(a.kind) if a.action=='group' else globals()[a.action]()
