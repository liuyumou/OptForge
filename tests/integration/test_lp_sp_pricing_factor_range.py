"""Adaptive range proposals retain independent exact acceptance."""
from pathlib import Path
import sys
import unittest
import numpy as np
from scipy import sparse
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
from lp_sp_pricing_factor_range import build
from lp_sp_pricing_factor_proof import verify_arrays


class AdaptiveRangeTests(unittest.TestCase):
    def test_large_positive_nullspace_duals(self):
        a=sparse.csr_matrix([[1.],[-1.]]);b=np.array([1.,-1.]);c=x=np.array([1.])
        for magnitude in (32.,2.**12,2.**24,2.**40):
            cert,detail=build(a,b,c,x,np.array([magnitude+1,magnitude]))
            self.assertIsNotNone(cert);self.assertLess(detail['dual_base_exponent'],48)
            self.assertTrue(verify_arrays(a.indptr,a.indices,a.data,b,c,cert['x'],cert['y0'],cert['basis'],cert['inverse'])['accepted'])

    def test_large_base_for_non_dyadic_exact_dual(self):
        a=sparse.csr_matrix([[3.]]);b=np.array([3.]);c=x=np.array([1.])
        cert,detail=build(a,b,c,x,np.array([100000.]))
        self.assertIsNotNone(cert)
        self.assertTrue(verify_arrays(a.indptr,a.indices,a.data,b,c,cert['x'],cert['y0'],cert['basis'],cert['inverse'])['accepted'])

    def test_invalid_and_extreme_inputs_remain_inconclusive(self):
        a=sparse.csr_matrix([[1.]]);b=c=x=np.array([1.])
        for y in (np.array([-1.]),np.array([np.inf]),np.array([2.**54])):
            self.assertIsNone(build(a,b,c,x,y)[0])
        self.assertIsNone(build(a,b,c,x+1,np.array([100.]))[0])


if __name__=='__main__':unittest.main()
