"""Exact arithmetic equivalence, conservative rejection, and unchanged dispatch."""
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from scipy import sparse
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'research/lp-sp-pricing/python'))
from sp_pricing.geometry_fast import dyadic_integers as old_encoding
from sp_pricing.dual_recovery_fast import dyadic_integers,build
from lp_sp_pricing_dual_fast_proof import products,verify_arrays,canonical
from lp_sp_pricing_factor_proof import verify_arrays as serial
from lp_sp_pricing_nontall_experiment import arrays
import lp_sp_pricing_final_run as solver

class FinalRecovery(unittest.TestCase):
    def test_exponent_decoder_matches_exhaustive_oracle(self):
        rng=np.random.default_rng(128007)
        for exponent in (0,1,7,24,25,52,1074):
            for maximum in (8,2**20):
                a=np.ldexp(rng.integers(-maximum,maximum,size=67).astype(float),-exponent)
                old,new=old_encoding([a]),dyadic_integers([a])
                self.assertEqual(old is None,new is None)
                if old is not None:self.assertEqual(old[0],new[0]);self.assertTrue(np.array_equal(old[1][0],new[1][0]))
        for a in (np.array([0.,-0.,2**40]),np.array([np.inf]),np.array([np.nan]),np.array([2.**41]),np.array([np.nextafter(0.,1.)])):
            old,new=old_encoding([a]),dyadic_integers([a]);self.assertEqual(old is None,new is None)
            if old is not None:self.assertEqual(old[0],new[0]);self.assertTrue(np.array_equal(old[1][0],new[1][0]))
    def test_signed_limb_products_equal_unbounded_integer_oracle(self):
        rng=np.random.default_rng(128009);dense=rng.integers(-32,33,size=(47,29),dtype=np.int64)*(1<<34);a=sparse.csr_matrix(dense)
        for transpose in (False,True):
            matrix=dense.T if transpose else dense;v=rng.integers(-128,129,size=matrix.shape[1],dtype=np.int64)*(1<<43)
            result,limbs=products(a,v,transpose);expected=[sum(int(q)*int(x) for q,x in zip(row,v)) for row in matrix]
            self.assertEqual(result,expected);self.assertGreater(limbs,1)
    def case(self):
        a,b,c,x,y,_=arrays(dict(m=24,n=8,degree=8,layout='band',shift=1,scaled=False,mixed=True),128011)
        cert,_=build(a,b,c,x,y+np.where(y>0,1e-12,0));self.assertIsNotNone(cert)
        return a,b,c,cert
    def test_certificate_matches_arbitrary_integer_reference(self):
        a,b,c,k=self.case();args=(a.indptr,a.indices,a.data,b,c,k['x'],k['y0'],k['basis'],k['inverse']);one=serial(*args);fast=verify_arrays(*args)
        self.assertTrue(one['accepted']);self.assertTrue(fast['accepted']);self.assertEqual(one['residual_numerator'],fast['residual_numerator']);self.assertEqual(one['visited_nonzeros'],fast['visited_nonzeros'])
    def test_tampered_certificate_and_csr_rejected(self):
        a,b,c,k=self.case()
        for x,y,basis,inverse in ((k['x']+1,k['y0'],k['basis'],k['inverse']),(k['x'],-np.ones_like(k['y0']),k['basis'],k['inverse']),(k['x'],k['y0'],k['basis'],np.zeros_like(k['inverse'])),(k['x'],k['y0'],np.zeros_like(k['basis']),k['inverse'])):
            self.assertFalse(verify_arrays(a.indptr,a.indices,a.data,b,c,x,y,basis,inverse)['accepted'])
        indices=a.indices.copy();indices[2]=indices[1];self.assertFalse(verify_arrays(a.indptr,indices,a.data,b,c,k['x'],k['y0'],k['basis'],k['inverse'])['accepted'])
    def test_canonical_empty_rows_and_block_boundaries(self):
        self.assertEqual(canonical(np.array([0,0,2,2]),np.array([0,1]),2),(True,2))
        self.assertFalse(canonical(np.array([0,0,2,2]),np.array([1,0]),2)[0])
        indices=np.tile(np.arange(64),1025);offsets=np.arange(1026)*64
        self.assertEqual(canonical(offsets,indices,64),(True,len(indices)));indices[65537]=indices[65536];self.assertFalse(canonical(offsets,indices,64)[0])
    def test_balancing_preserves_original_exact_equations(self):
        a,b,c,x,y,_=arrays(dict(m=24,n=8,degree=8,layout='band',shift=1,scaled=True,mixed=True),128013)
        t,rhs,scale,info=solver.equilibrate(a,b);self.assertTrue(info['applied']);self.assertTrue(np.array_equal(t.data,a.data*np.repeat(scale,np.diff(a.indptr))))
        self.assertTrue(np.array_equal(rhs,b*scale));self.assertTrue(np.array_equal(t.T@(y/scale),a.T@y))
    def test_early_cpu_endpoint_independently_certifies(self):
        for m,n,scaled in ((36,24,False),(64,16,True)):
            a,b,c,_,_,_=arrays(dict(m=m,n=n,degree=n,layout='band',shift=1,scaled=scaled,mixed=True),128015)
            x,y,k,detail=solver.projection(a,b,c,20,False)
            if k is None:k,_=build(a,b,c,x,y)
            self.assertIsNotNone(k);proof=serial(a.indptr,a.indices,a.data,b,c,k['x'],k['y0'],k['basis'],k['inverse']);self.assertTrue(proof['accepted'])
    def test_other_shapes_delegate_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary:
            model=Path(temporary)/'model.json';out=Path(temporary)/'out'
            for m,n in ((16,16),(4,16),(8194,4097),(65536,4096)):
                model.write_text(json.dumps(dict(rows=m,columns=n)))
                with patch.object(solver.previous,'run',return_value='unchanged') as before:
                    self.assertEqual(solver.run(model,out,17,False,'cpu'),'unchanged');before.assert_called_once_with(model,out,17,False,'cpu',16)

if __name__=='__main__':unittest.main()
