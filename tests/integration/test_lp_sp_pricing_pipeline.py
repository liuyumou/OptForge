"""Cached proposals never replace independent exact authority; bounded overlap."""
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'research/lp-sp-pricing/python'))
from lp_sp_pricing_nontall_experiment import arrays
from lp_sp_pricing_factor_proof import verify_arrays
from sp_pricing.dual_recovery_cached import CachedCorrection,blas_threads
import lp_sp_pricing_pipeline_run as solver

class PipelineCorrection(unittest.TestCase):
    def case(self,scaled=True):return arrays(dict(m=48,n=12,degree=12,layout='band',shift=1,scaled=scaled,mixed=True),129003)
    def proof(self,a,b,c,k):return verify_arrays(a.indptr,a.indices,a.data,b,c,k['x'],k['y0'],k['basis'],k['inverse'])
    def test_cached_inverse_reuse_preserves_exact_proof(self):
        a,b,c,x,y,_=self.case();cache=CachedCorrection(a,b,c)
        first,d=cache.build(x,y+np.where(y>0,1e-12,0));self.assertIsNotNone(first);count=cache.builds
        for shift in (0.,1e-13,2e-13):
            k,d=cache.build(x,y+np.where(y>0,shift,0));self.assertTrue(self.proof(a,b,c,k)['accepted']);self.assertEqual(cache.builds,count);self.assertLessEqual(d['resident_inverses'],2)
        self.assertGreater(cache.hits,0)
    def test_inactive_cached_basis_is_not_reused(self):
        a,b,c,x,y,_=self.case();cache=CachedCorrection(a,b,c);k,_=cache.build(x,y)
        cache.cache=[(np.flatnonzero(y==0)[:1].repeat(a.shape[1]),np.eye(a.shape[1]))]
        count=cache.builds;k,d=cache.build(x,y);self.assertIsNotNone(k);self.assertGreater(cache.builds,count);self.assertTrue(self.proof(a,b,c,k)['accepted'])
    def test_nonfinite_and_tampered_data_rejected(self):
        a,b,c,x,y,_=self.case();cache=CachedCorrection(a,b,c);k,_=cache.build(x,np.full_like(y,np.nan));self.assertIsNone(k)
        k,_=cache.build(x,y);k['inverse'][:]=0;self.assertFalse(self.proof(a,b,c,k)['accepted'])
    def test_blas_limit_restores_installed_pools(self):
        with blas_threads(1) as outside:
            self.assertTrue(outside)
            with blas_threads(3) as inside:self.assertTrue(all(r['threads']==3 for r in inside))
            with blas_threads(1) as restored:self.assertEqual(outside,restored)
    def test_unscaled_dispatch_delegates_original_projection(self):
        a,b,c,x,y,_=self.case(False)
        with patch.object(solver,'OLD_PROJECTION',return_value='original') as old:
            self.assertEqual(solver.projection(a,b,c,17,True),'original');self.assertEqual(old.call_count,1)
    def test_cpu_dispatch_delegates_original_projection(self):
        a,b,c,x,y,_=self.case()
        with patch.object(solver,'OLD_PROJECTION',return_value='original') as old:self.assertEqual(solver.projection(a,b,c,17,False),'original');self.assertEqual(old.call_count,1)
    def test_single_worker_overlaps_and_certifies_snapshot(self):
        a,b,c,x,y,_=self.case();closed=[];build=CachedCorrection.build
        class State:
            def __init__(self,*args):self.scale=solver.original.equilibrate(a,b)[2]
            def advance(self,count):time.sleep(.001);return x+1e-7,(y+1e-9)/self.scale
            def close(self):closed.append(True)
        def delayed(cache,x,y):time.sleep(.03);return build(cache,x,y)
        with patch.object(solver,'GpuProjection',State),patch.object(CachedCorrection,'build',delayed):
            px,py,k,d=solver.projection(a,b,c,20,True,inverse_gpu=False,pipeline=True)
        self.assertEqual(closed,[True]);self.assertIsNotNone(k);self.assertTrue(self.proof(a,b,c,k)['accepted']);self.assertGreater(d['correction_projection_overlap_ns'],0);self.assertEqual(d['maximum_pending_corrections'],1);self.assertLessEqual(d['resident_inverses'],2);self.assertGreater(d['steps'],d['certificate_snapshot_step'])

if __name__=='__main__':unittest.main()
