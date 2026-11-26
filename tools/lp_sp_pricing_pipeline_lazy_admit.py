"""Additive admission of lazy inverse caching and checked worker drain."""
import unittest
from lp_sp_pricing_budget import ROOT,BASE,binding,put
from lp_sp_pricing_gpu_opt_compare import read,verify
from lp_sp_pricing_pipeline_admit import validate as previous
OUT=BASE/'pipeline-lazy-cpu-v1'
def sources():return [binding(ROOT/p) for p in ('research/lp-sp-pricing/python/sp_pricing/dual_recovery_cached_lazy.py','tools/lp_sp_pricing_pipeline_lazy_run.py','tools/lp_sp_pricing_pipeline_lazy_admit.py','tests/integration/test_lp_sp_pricing_pipeline_lazy.py')]
def cpu():
    gate=previous();OUT.mkdir(exist_ok=False);r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT/'tests/integration'),'test_lp_sp_pricing_pipeline*.py'))
    if not r.wasSuccessful() or r.testsRun!=9 or r.skipped:raise RuntimeError('lazy pipeline admission')
    put(OUT/'result.json',dict(status='passed',sources=sources(),previous=gate,tests=r.testsRun,retained_development=binding(BASE/'pipeline-development-v1/result.json')))
def validate():
    previous();d=read(OUT/'result.json')
    if d['sources']!=sources() or read(BASE/'resources/pipeline-lazy-cpu-v1.settlement.json')['status']!='passed':raise RuntimeError('lazy pipeline source admission')
    for k in ('previous','retained_development'):verify(d[k])
    return binding(OUT/'result.json')
if __name__=='__main__':cpu()
