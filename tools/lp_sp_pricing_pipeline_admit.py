"""Source-bound CPU admission; retained kernels and exact checker stay unchanged."""
import argparse
import unittest
from lp_sp_pricing_budget import ROOT,BASE,binding,put
from lp_sp_pricing_gpu_opt_compare import read,verify
from lp_sp_pricing_final_screened_admit import validate as previous
OUT=BASE/'pipeline-cpu-admit-v1'

def sources():return [binding(ROOT/p) for p in ('research/lp-sp-pricing/python/sp_pricing/dual_recovery_cached.py','tools/lp_sp_pricing_pipeline_run.py','tools/lp_sp_pricing_pipeline_admit.py','tests/integration/test_lp_sp_pricing_pipeline.py')]

def cpu():
    gate=previous();OUT.mkdir(exist_ok=False)
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT/'tests/integration'),'test_lp_sp_pricing_pipeline.py'))
    if not result.wasSuccessful() or result.testsRun!=7 or result.skipped:raise RuntimeError('pipeline CPU admission')
    report=ROOT/'docs/benchmarks/lp-sp-pricing-comprehensive.md';archive=OUT/'comprehensive-before.md';archive.write_bytes(report.read_bytes())
    put(OUT/'result.json',dict(status='passed',sources=sources(),previous=gate,tests=result.testsRun,old_report=binding(report),retained_report=binding(archive),scope='Bounded cached untrusted inverses and one correction worker; unchanged original-model independent proof and existing CUDA kernels.'))

def validate():
    previous();d=read(OUT/'result.json')
    if d['sources']!=sources() or read(BASE/'resources/pipeline-cpu-admit-v1.settlement.json')['status']!='passed':raise RuntimeError('pipeline CPU admission changed')
    for key in ('previous','retained_report'):verify(d[key])
    return binding(OUT/'result.json')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['cpu']);p.parse_args();cpu()
