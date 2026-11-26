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
from lp_sp_pricing_pipeline_budget import allocation,CPU,GPU
from lp_sp_pricing_pipeline_admit import validate
from lp_sp_pricing_nontall_experiment import generate,arrays
from lp_sp_pricing_final_study_v2 import FOCUS as PREVIOUS_FOCUS,CONTROLS
from sp_pricing.factor_projection import CpuProjection,GpuProjection,inverse_proposal
from sp_pricing.implicit_certificate import inverse_bound
import lp_sp_pricing_recovery_parallel_experiment as common

STUDY=BASE/'pipeline-evaluation-v1';DEV=BASE/'pipeline-development-v1';ENVELOPE=BASE/'pipeline-envelope-v1.json'
FOCUS=[dict(PREVIOUS_FOCUS[1],name='mixed-scaled-tall-1m',scaled=True),PREVIOUS_FOCUS[-1]]
GPU_CONTROLS=[PREVIOUS_FOCUS[i] for i in (0,2,3)]
CONFIG={'candidate-cpu-pipeline':['--inverse-backend','cpu'],'candidate-gpu-sync':['--inverse-backend','gpu','--synchronous'],'candidate-gpu-pipeline':['--inverse-backend','gpu']}
SEEDS=[129101,129123,129149];CONTROL_SEEDS=[129201,129223,129249]

def sources():return [binding(__file__),binding(ROOT/'tools/lp_sp_pricing_pipeline_driver.py')]

def cell(model,lane,out,configuration=None):
    execute=common.previous.execute;commands=[]
    def command(cmd,*args,**kwargs):
        effective=list(cmd)
        if len(effective)>2:
            name=Path(effective[2]).name
            if name=='lp_sp_pricing_recovery_run_fast.py':
                effective[2]=str(ROOT/'tools'/('lp_sp_pricing_final_screened_run.py' if lane=='candidate-before' else 'lp_sp_pricing_pipeline_run.py'))
                if lane!='candidate-before':effective+=CONFIG.get(lane,configuration or [])
            elif name=='lp_sp_pricing_recovery_endpoint_balanced.py':effective[2]=str(ROOT/'tools/lp_sp_pricing_final_endpoint.py')
            elif name=='lp_sp_pricing_factor_parallel_proof.py':effective[2]=str(ROOT/'tools/lp_sp_pricing_dual_fast_proof.py')
            commands.append(dict(command=effective,source=binding(effective[2])))
        return execute(effective,*args,**kwargs)
    with patch.object(common.previous,'execute',command):row=common.cell(model,lane,out,'cpu')
    put(out/'effective-commands.json',dict(commands=commands));row['effective_commands']=binding(out/'effective-commands.json');return row

def gpu_quality():
    records=[]
    for m,n in ((96,32),(192,64),(288,96)):
        a,b,c,x,y,_=arrays(dict(m=m,n=n,degree=n,layout='band',shift=1,scaled=True,mixed=True),129031+n)
        cpu=CpuProjection(a,b,c,.001);gpu=GpuProjection(a,b,c,.001)
        matrix=np.asarray(a[:n].toarray().T);matrix+=np.eye(n)*128
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                for steps in (1,7,31,61):
                    future=pool.submit(inverse_proposal,matrix,True);xg,yg=gpu.advance(steps);xc,yc=cpu.advance(steps);inverse=future.result();proof=inverse_bound(matrix,inverse)
                    if not proof['accepted'] or not np.allclose(xc,xg,rtol=1e-7,atol=2e-8) or not np.allclose(yc,yg,rtol=1e-7,atol=2e-8):raise ArithmeticError('concurrent retained CUDA differential')
                    records.append(dict(rows=m,columns=n,steps=steps,passed=True,inverse_proof=proof))
        finally:gpu.close();cpu.close()
    return records

def development():
    gate=validate();DEV.mkdir(exist_ok=False);quality=gpu_quality();put(DEV/'quality.json',dict(status='passed',records=quality,admission=gate,sources=sources(),cuda_source_changes=False,checker_changes=False))
    models=[];rows=[]
    for i,spec in enumerate(FOCUS):
        model=generate(spec,129051+2*i,DEV/'models'/spec['name']);models.append(model)
        for lane in ['candidate-before']+list(CONFIG):rows.append(cell(model,lane,DEV/'runs'/f'{model["name"]}-{lane}'))
    put(DEV/'result.json',dict(status='all_8_slots_disposed',models=models,rows=rows,sources=sources(),quality=binding(DEV/'quality.json'),
        selection_rule='Every selected lane must certify both models timely and cost <=1.05 of the reference per model. Choose lowest sum of complete costs; require at least 5% total improvement over CPU pipeline to select GPU. Same final endpoint constructor and cold independent checker. No development model repeats in holdouts.'))

def selected():
    validate();d=read(DEV/'result.json')
    if d['sources']!=sources() or read(BASE/'resources/pipeline-development-v1.settlement.json')['status']!='passed':raise RuntimeError('development source/supervision')
    verify(d['quality']);eligible={}
    for lane in CONFIG:
        ratios=[];costs=[]
        for spec in FOCUS:
            rs={r['lane']:r for r in d['rows'] if r['family']==spec['name']};a,b=rs['candidate-before'],rs[lane]
            if not all(r['accepted'] and r['timely'] for r in (a,b)) or b['complete_ns']>1.05*a['complete_ns']:break
            ratios.append(b['complete_ns']/a['complete_ns']);costs.append(b['complete_ns'])
        else:eligible[lane]=sum(costs)
    if not eligible:raise RuntimeError('no admissible cached correction configuration')
    best=min(eligible,key=eligible.get);cpu=eligible.get('candidate-cpu-pipeline')
    if cpu is not None and eligible[best]>.95*cpu:best='candidate-cpu-pipeline'
    return dict(lane=best,arguments=CONFIG[best],complete_cost_sums_ns=eligible)

def envelope():
    choice=selected();allocation();cpu,gpu=accounting(BASE),accounting(BASE,True)
    if cpu['confirmation']+4360*NS>CPU['confirmation']*NS or gpu['confirmation']+190*NS>GPU['confirmation']*NS:raise RuntimeError('full holdout reserve')
    put(ENVELOPE,dict(status='complete_reserve_fits',sources=sources(),choice=choice,development=binding(DEV/'result.json'),cpu_phase_ns=cpu,gpu_phase_ns=gpu,full_cpu_seconds=4360,full_gpu_seconds=190,settlements=[binding(p) for p in sorted((BASE/'resources').glob('*.settlement.json'))]))

def freeze():
    gate=validate();choice=selected();e=read(ENVELOPE)
    if e['sources']!=sources() or e['choice']!=choice:raise RuntimeError('prospective envelope changed')
    for item in e['settlements']:verify(item)
    STUDY.mkdir(exist_ok=False);models=[];controls=[];gpu_controls=[]
    for spec in FOCUS:
        for seed in SEEDS:models.append(generate(spec,seed,STUDY/'models'/f'{spec["name"]}-{seed}'))
    for spec in CONTROLS:
        for seed in CONTROL_SEEDS:controls.append(generate(spec,seed,STUDY/'models'/f'{spec["name"]}-{seed}'))
    for spec in GPU_CONTROLS:gpu_controls.append(generate(spec,129301,STUDY/'models'/f'{spec["name"]}-129301'))
    put(STUDY/'freeze.json',dict(status='frozen',sources=sources(),admission=gate,envelope=binding(ENVELOPE),choice=choice,models=models,controls=controls,gpu_controls=gpu_controls,images=images(),wall_deadline_utc=allocation()['wall_deadline_utc'],native_seconds=60,process_seconds=90,reconstruction_seconds=90,proof_seconds=120,
        roster='60 fresh attempts on 24 models: six scaled-tall models x before/new/GPU-COPT/CPU-COPT; fifteen CPU regression models x before/new; three GPU regression models x before/new.',
        unchanged_path_rule='All exact certificates preserved; identical explicit certificates where present; median current/reference complete <=1.10 per family. Unscaled GPU paths must retain step counts and endpoints.',
        complete_cost='Common original generation/encoding + cold solver process + raw 1e-9 audit + common endpoint construction + cold independent exact proof, including cached preparation, failed checks, speculative GPU work and worker drain.'))

def frozen():
    validate();f=read(STUDY/'freeze.json')
    if f['sources']!=sources() or f['images']!=images():raise RuntimeError('pipeline sources/images changed')
    for key in ('admission','envelope'):verify(f[key])
    for m in f['models']+f['controls']+f['gpu_controls']:verify(m['model']);verify(m['construction_audit'])
    return f

def group(kind):
    f=frozen();rows=[]
    for i,model in enumerate(f['controls'] if kind=='control' else f['models']):
        lanes=['copt-auto'] if kind=='cpu' else (['candidate-before','candidate'] if kind=='control' else ['candidate-before','candidate','copt-gpu-default']);lanes=lanes[i%len(lanes):]+lanes[:i%len(lanes)]
        for lane in lanes:rows.append(cell(model,lane,STUDY/'runs'/f'{model["name"]}-{model["seed"]}-{lane}',f['choice']['arguments']))
    if kind=='gpu':
        for i,model in enumerate(f['gpu_controls']):
            lanes=['candidate-before','candidate'] if i%2==0 else ['candidate','candidate-before']
            for lane in lanes:rows.append(cell(model,lane,STUDY/'runs'/f'{model["name"]}-{model["seed"]}-{lane}',f['choice']['arguments']))
    put(STUDY/f'{kind}-group.json',dict(status='all_slots_disposed',rows=rows))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['development','envelope','freeze','group']);p.add_argument('--kind',choices=['gpu','cpu','control']);a=p.parse_args();group(a.kind) if a.action=='group' else globals()[a.action]()
