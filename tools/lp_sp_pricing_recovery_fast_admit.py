"""Additive CPU dense proposal admission; preserve admitted GPU and proof sources."""
import argparse
import subprocess
import sys
from lp_sp_pricing_budget import ROOT,BASE,binding,put
from lp_sp_pricing_gpu_opt_compare import read,verify
from lp_sp_pricing_recovery_balanced_admit import validate as previous

def sources():
    return [binding(ROOT/p) for p in ('research/lp-sp-pricing/python/sp_pricing/primal_recovery_fast.py',
        'tools/lp_sp_pricing_recovery_run_fast.py','tools/lp_sp_pricing_recovery_fast_admit.py','tests/integration/test_lp_sp_pricing_primal_fast.py')]

def cpu():
    prior=previous();out=BASE/'recovery-fast-cpu-v1';out.mkdir(exist_ok=False)
    subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests/integration','-p','test_lp_sp_pricing_primal*.py','-v'],cwd=ROOT,check=True)
    put(out/'result.json',dict(status='passed',sources=sources(),previous=prior,tests=12))

def validate():
    previous();path=BASE/'recovery-fast-cpu-v1/result.json';d=read(path)
    if d['sources']!=sources() or read(BASE/'resources/recovery-fast-cpu-v1.settlement.json')['status']!='passed':raise RuntimeError('dense CPU admission')
    verify(d['previous']);return binding(path)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['cpu']);p.parse_args();cpu()
