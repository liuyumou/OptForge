"""Lazy inverse construction and current-snapshot drain retain exact checks."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'research/lp-sp-pricing/python'))
from lp_sp_pricing_nontall_experiment import arrays
from lp_sp_pricing_factor_proof import verify_arrays
from sp_pricing.dual_recovery_cached_lazy import CachedCorrection
import lp_sp_pricing_pipeline_lazy_run as solver

class LazyCorrection(unittest.TestCase):
    def case(self):return arrays(dict(m=48,n=12,degree=12,layout='band',shift=1,scaled=True,mixed=True),129071)
    def test_only_one_inverse_is_constructed_and_reused(self):
        a,b,c,x,y,_=self.case();cache=CachedCorrection(a,b,c)
        for _ in range(3):
            k,d=cache.build(x,y);self.assertEqual(cache.builds,1);self.assertEqual(len(cache.cache),1);self.assertTrue(verify_arrays(a.indptr,a.indices,a.data,b,c,k['x'],k['y0'],k['basis'],k['inverse'])['accepted'])
    def test_failed_old_snapshot_is_rechecked_at_drain(self):
        a,b,c,x,y,_=self.case();calls=[];build=CachedCorrection.build
        class State:
            def __init__(self,*args):self.scale=solver.original.equilibrate(a,b)[2]
            def advance(self,count):return x,y/self.scale
            def close(self):pass
        def fail_first(cache,x,y):
            calls.append(True)
            return (None,dict(reason='stale_snapshot_test')) if len(calls)==1 else build(cache,x,y)
        with patch.object(solver,'GpuProjection',State),patch.object(CachedCorrection,'build',fail_first):
            _,_,k,d=solver.projection(a,b,c,20,True,inverse_gpu=False,pipeline=True)
        self.assertIsNotNone(k);self.assertEqual(len(calls),2);self.assertFalse(d['early_trials'][0]['accepted']);self.assertTrue(d['early_trials'][1]['accepted']);self.assertTrue(verify_arrays(a.indptr,a.indices,a.data,b,c,k['x'],k['y0'],k['basis'],k['inverse'])['accepted'])

if __name__=='__main__':unittest.main()
