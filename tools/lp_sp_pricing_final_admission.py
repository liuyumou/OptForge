"""CPU arithmetic/host profiles and GPU continuation admission for final recovery."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import unittest
import numpy as np
from lp_sp_pricing_budget import ROOT,BASE,binding,put
from lp_sp_pricing_baselines import PYTHON
from lp_sp_pricing_gpu_opt_compare import read,verify
from lp_sp_pricing_gpu_opt_report import bindings
import lp_sp_pricing_rectangular_study_v2 as prior
from lp_sp_pricing_nontall_experiment import arrays
from lp_sp_pricing_geometry_run import load
from lp_billion_arrays import read as read_array,write
from lp_billion_owned_process import execute
from sp_pricing.dual_recovery_fast import build
from lp_sp_pricing_dual_fast_proof import verify_arrays
from lp_sp_pricing_final_run import projection
from sp_pricing.factor_projection import CpuProjection,GpuProjection

CPU=BASE/'final-cpu-admit-v1';GPU=BASE/'final-gpu-admit-v1'

def sources():return [binding(ROOT/p) for p in ('research/lp-sp-pricing/python/sp_pricing/dual_recovery_fast.py','tools/lp_sp_pricing_dual_fast_proof.py','tools/lp_sp_pricing_final_endpoint.py','tools/lp_sp_pricing_final_run.py','tools/lp_sp_pricing_final_admission.py','tests/integration/test_lp_sp_pricing_final.py')]

def profile(model,response,out,mode):
    from lp_sp_pricing_transform_endpoint import build as old
    a,b,c,_,_=load(model);raw=read(response);x=read_array(BASE,raw['endpoint']['primal']);y=-read_array(BASE,raw['endpoint']['dual']);start=time.perf_counter_ns();certificate,detail=(old(a,b,c,x,y,False) if mode=='old-build' else build(a,b,c,x,y))
    if certificate is None:raise ArithmeticError('profile failed construction')
    put(out,dict(status='constructed',elapsed_ns=time.perf_counter_ns()-start,detail=detail,implicit_certificate=dict(primal=write(BASE,certificate['x']),dual_base=write(BASE,certificate['y0']),basis=write(BASE,certificate['basis'],'u32le'),inverse=write(BASE,certificate['inverse'].ravel()))))

def cpu():
    prior.validate();CPU.mkdir(exist_ok=False);suite=unittest.defaultTestLoader.discover(str(ROOT/'tests/integration'),'test_lp_sp_pricing_final.py');tests=unittest.TextTestRunner(verbosity=2).run(suite)
    if not tests.wasSuccessful() or tests.testsRun!=8 or tests.skipped:raise RuntimeError('final arithmetic/dispatch admission')
    records=[]
    for family in ('mixed-tall-1m','mixed-tall-4m','mixed-tall-16m'):
        base=BASE/'transform-evaluation-v1/runs'/f'{family}-124401-optimized';response=base/'response.json';raw=read(response);model=Path(raw['model']['path']);certificate=base/'postprocess/response.json'
        for mode in ('old-build','new-build','old-check','new-check'):
            out=CPU/f'{family}-{mode}';out.mkdir()
            if mode.endswith('build'):
                if mode=='old-build':cmd=[str(PYTHON),'-B',__file__,'profile','--model',str(model),'--response',str(response),'--output',str(out/'result.json'),'--mode',mode]
                else:cmd=[str(PYTHON),'-B',str(ROOT/'tools/lp_sp_pricing_final_endpoint.py'),str(model),str(response),str(out/'result.json')]
            else:
                script='lp_sp_pricing_factor_parallel_proof.py' if mode=='old-check' else 'lp_sp_pricing_dual_fast_proof.py';cmd=[str(PYTHON),'-B',str(ROOT/'tools'/script),str(model),str(certificate),str(out/'result.json')]
            proc=execute(cmd,out/'stdout',out/'stderr',90,None);put(out/'process.json',proc)
            result=read(out/'result.json') if (out/'result.json').exists() else {}
            if proc['returncode'] or proc['timed_out'] or (mode.endswith('check') and not result.get('accepted')) or (mode.endswith('build') and not result.get('implicit_certificate')):raise RuntimeError('cold host profile failed '+family+' '+mode)
            records.append(dict(family=family,mode=mode,cold_process_ns=proc['elapsed_ns'],result=binding(out/'result.json'),model=binding(model),response=binding(response),certificate=binding(certificate)))
    archive=CPU/'comprehensive-before.md';archive.write_bytes((ROOT/'docs/benchmarks/lp-sp-pricing-comprehensive.md').read_bytes())
    put(CPU/'result.json',dict(status='passed',sources=sources(),tests=8,profiles=records,previous=prior.validate(),old_report=binding(ROOT/'docs/benchmarks/lp-sp-pricing-comprehensive.md'),retained_report=binding(archive),scope='CPU-only component rechecks of retained endpoints; no historical LP solves. Reports distinguish old CPU builder from historical GPU construction.'))

def cpu_valid():
    prior.validate();d=read(CPU/'result.json')
    if d['sources']!=sources() or read(BASE/'resources/final-cpu-admit-v1.settlement.json')['status']!='passed':raise RuntimeError('final CPU admission')
    for key in ('previous','retained_report'):verify(d[key])
    return binding(CPU/'result.json')

def gpu():
    gate=cpu_valid();GPU.mkdir(exist_ok=False);records=[]
    for m,n,scaled in ((96,64,False),(192,48,False),(192,48,True)):
        a,b,c,_,_,_=arrays(dict(m=m,n=n,degree=n,layout='band',shift=1,scaled=scaled,mixed=True),128031+m)
        cpu=CpuProjection(a,b,c,.001);gpu=GpuProjection(a,b,c,.001)
        try:
            for count in (1,7,31,61):
                xc,yc=cpu.advance(count);xg,yg=gpu.advance(count)
                if not np.allclose(xc,xg,rtol=1e-7,atol=2e-8) or not np.allclose(yc,yg,rtol=1e-7,atol=2e-8):raise ArithmeticError('retained GPU continuation differential')
                records.append(dict(kind='CPU_GPU_continuation',rows=m,columns=n,scaled=scaled,steps=count,passed=True))
        finally:cpu.close();gpu.close()
        x,y,k,detail=projection(a,b,c,20,True)
        if k is None:k,_=build(a,b,c,x,y)
        if k is None:raise ArithmeticError('GPU recovery missing certificate')
        proof=verify_arrays(a.indptr,a.indices,a.data,b,c,k['x'],k['y0'],k['basis'],k['inverse'])
        from lp_sp_pricing_factor_proof import verify_arrays as oracle
        check=oracle(a.indptr,a.indices,a.data,b,c,k['x'],k['y0'],k['basis'],k['inverse'])
        if not proof['accepted'] or not check['accepted'] or proof['residual_numerator']!=check['residual_numerator']:raise ArithmeticError('GPU endpoint independent exact proof')
        records.append(dict(kind='original_model_exact_recovery',rows=m,columns=n,scaled=scaled,proposal=detail,proof=proof,reference=check))
    put(GPU/'result.json',dict(status='passed',sources=sources(),cpu=gate,records=records,cuda_source_changes=False,retained_cuda_quality='Existing source-bound four-sanitizer admission remains exact; new code changes host scheduling, row transforms, construction and checking.'))

def validate():
    cpu_valid();d=read(GPU/'result.json')
    if d['sources']!=sources() or read(BASE/'resources/final-gpu-admit-v1.settlement.json')['status']!='passed':raise RuntimeError('final GPU admission')
    verify(d['cpu']);return binding(GPU/'result.json')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['cpu','gpu','profile']);p.add_argument('--model',type=Path);p.add_argument('--response',type=Path);p.add_argument('--output',type=Path);p.add_argument('--mode');a=p.parse_args()
    if a.action=='profile':profile(a.model,a.response,a.output,a.mode)
    else:globals()[a.action]()
