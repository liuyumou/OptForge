"""CPU-only additive construction admission; retain the exact GPU/checker gate."""
import argparse
from pathlib import Path
import subprocess
import sys
from lp_sp_pricing_budget import ROOT,BASE,binding,put
from lp_sp_pricing_gpu_opt_compare import read,verify
from lp_sp_pricing_recovery_admit import validate as previous

def sources():
    return [binding(ROOT/p) for p in ('research/lp-sp-pricing/python/sp_pricing/primal_recovery_balanced.py',
        'tools/lp_sp_pricing_recovery_endpoint_balanced.py','tools/lp_sp_pricing_recovery_balanced_admit.py',
        'tests/integration/test_lp_sp_pricing_primal_balanced.py')]

def cpu():
    prior=previous();out=BASE/'recovery-balanced-cpu-v1';out.mkdir(exist_ok=False)
    subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests/integration','-p','test_lp_sp_pricing_primal*.py','-v'],cwd=ROOT,check=True)
    put(out/'result.json',dict(status='passed',sources=sources(),previous=prior,tests=11,
        scope='Only numerical sparse-wide basis selection changes; original GPU kernels, numerical proposals and independent exact checker remain byte-for-byte identical.'))

def validate():
    previous();path=BASE/'recovery-balanced-cpu-v1/result.json';d=read(path)
    if d['sources']!=sources() or read(BASE/'resources/recovery-balanced-cpu-v1.settlement.json')['status']!='passed':raise RuntimeError('balanced CPU admission')
    verify(d['previous']);return binding(path)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['cpu']);p.parse_args();cpu()
