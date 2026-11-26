"""Sparse-wide basis coverage and unchanged dense/square construction."""
from pathlib import Path
import sys
import unittest
import numpy as np
from scipy import sparse
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'research/lp-sp-pricing/python'))
from sp_pricing.primal_recovery import row_proposal,build as old
from sp_pricing.primal_recovery_balanced import build
from lp_sp_pricing_primal_proof import verify_arrays
from lp_sp_pricing_nontall_experiment import arrays

class BalancedPrimal(unittest.TestCase):
    def test_sparse_wide_original_model_certificates(self):
        for seed in (126501,126503,126507):
            a,b,c,_,_,_=arrays(dict(m=32,n=128,degree=24,layout='band',shift=17,scaled=False,mixed=False),seed)
            x,y,_=row_proposal(a,b,c);cert,detail=build(a,b,c,x,y)
            self.assertIsNotNone(cert);self.assertTrue(verify_arrays(a.indptr,a.indices,a.data,b,c,cert['x0'],cert['y'],cert['columns'],cert['inverse'])['accepted'])
    def test_dense_and_square_outputs_unchanged(self):
        for m,n in ((8,8),(8,24)):
            a,b,c,_,_,_=arrays(dict(m=m,n=n,degree=n,layout='band',shift=1,scaled=False,mixed=True),126511)
            x,y,_=row_proposal(a,b,c);a0,_=old(a,b,c,x,y);a1,_=build(a,b,c,x,y)
            for name in ('x0','y','columns','inverse'):self.assertTrue(np.array_equal(a0[name],a1[name]))
    def test_rank_deficient_sparse_basis_is_not_accepted(self):
        a=sparse.csr_matrix(([1.,1.],([0,1],[0,0])),shape=(2,16));b=np.ones(2);c=np.zeros(16);c[0]=2
        cert,detail=build(a,b,c,np.zeros(16),np.ones(2));self.assertIsNone(cert)

if __name__=='__main__':unittest.main()
