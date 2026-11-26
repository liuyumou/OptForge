"""Additive CPU admission for screened correction; original GPU kernel stays exact."""
import argparse
import unittest
from lp_sp_pricing_budget import ROOT,BASE,binding,put
from lp_sp_pricing_gpu_opt_compare import read,verify
from lp_sp_pricing_final_admission import validate as previous
OUT=BASE/'final-screened-cpu-v1'

def sources():return [binding(ROOT/p) for p in ('research/lp-sp-pricing/python/sp_pricing/dual_recovery_screened.py','tools/lp_sp_pricing_final_screened_run.py','tools/lp_sp_pricing_final_screened_admit.py','tests/integration/test_lp_sp_pricing_final_screened.py')]

def cpu():
    gate=previous();OUT.mkdir(exist_ok=False);suite=unittest.defaultTestLoader.discover(str(ROOT/'tests/integration'),'test_lp_sp_pricing_final*.py');r=unittest.TextTestRunner(verbosity=2).run(suite)
    if not r.wasSuccessful() or r.testsRun!=10 or r.skipped:raise RuntimeError('screened recovery admission')
    put(OUT/'result.json',dict(status='passed',sources=sources(),previous=gate,tests=r.testsRun,retained_development=binding(BASE/'final-development-v1/result.json'),
        numerical_scope='Only early candidate correction construction: reject proposed negative corrections before constructing inverse. Final acceptance/checker and all CUDA sources unchanged. Regression development remains exact.'))

def validate():
    previous();d=read(OUT/'result.json')
    if d['sources']!=sources() or read(BASE/'resources/final-screened-cpu-v1.settlement.json')['status']!='passed':raise RuntimeError('screened CPU admission')
    for key in ('previous','retained_development'):verify(d[key])
    return binding(OUT/'result.json')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['cpu']);p.parse_args();cpu()
