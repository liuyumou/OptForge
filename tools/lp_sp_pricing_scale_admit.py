"""CPU-only certificate boundary/oracle admission; previous numerical kernels stay exact."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from lp_sp_pricing_budget import ROOT,BASE,put,binding
from lp_sp_pricing_gpu_opt_compare import read,verify
from lp_sp_pricing_geometry_experiment import admission as previous_admission

def sources():
    return [binding(ROOT/p) for p in ['research/lp-sp-pricing/python/sp_pricing/certificate_guard.py',
        'tools/lp_sp_pricing_scale_run.py','tools/lp_sp_pricing_scale_verify.py','tools/lp_sp_pricing_scale_admit.py',
        'tests/integration/test_lp_sp_pricing_scale.py']]

def run(identity):
    previous=previous_admission();out=BASE/identity;out.mkdir(exist_ok=False)
    subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests/integration','-p','test_lp_sp_pricing_scale.py','-v'],cwd=ROOT,check=True)
    put(out/'admission.json',dict(status='passed',tests=8,valid_random_models=128,invalid_random_proofs=384,
        previous_numerical_admission=previous,sources=sources(),arithmetic='independent Python unbounded integer full proof',
        hardening='validate unsigned values before narrowing; validate cached integers against original floating coefficients',
        historical_results='previous solver proposals were bounded signed integers; old source/results remain immutable'))

def validate():
    path=BASE/'scale-certificate-admit-v1/admission.json';d=read(path)
    if d['status']!='passed' or d['sources']!=sources():raise RuntimeError('certificate admission changed')
    verify(d['previous_numerical_admission']);previous_admission()
    if read(BASE/'resources/scale-certificate-admit-v1.settlement.json')['status']!='passed':raise RuntimeError('certificate supervision failed')
    return binding(path)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('identity');a=p.parse_args();run(a.identity)
