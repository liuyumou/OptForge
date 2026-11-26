"""Independent serial/parallel proof equivalence and malformed certificate checks."""
from pathlib import Path
import sys
import unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'research/lp-sp-pricing/python'))
from lp_sp_pricing_nontall_experiment import arrays
from sp_pricing.primal_recovery_fast import row_proposal
from sp_pricing.primal_recovery_balanced import build
from lp_sp_pricing_primal_proof import verify_arrays as serial
from lp_sp_pricing_primal_parallel_proof import verify_arrays as parallel

class ParallelPrimal(unittest.TestCase):
    def case(self,m,n):
        a,b,c,_,_,_=arrays(dict(m=m,n=n,degree=n,layout='band',shift=1,scaled=False,mixed=True),126601+m)
        x,y,_=row_proposal(a,b,c);cert,_=build(a,b,c,x,y)
        return a,b,c,cert
    def test_equivalent_exact_acceptance(self):
        for m,n in ((1,3),(7,7),(17,49)):
            a,b,c,k=self.case(m,n);args=(a.indptr,a.indices,a.data,b,c,k['x0'],k['y'],k['columns'],k['inverse'])
            one=serial(*args);many=parallel(*args,force_parallel=True)
            self.assertTrue(one['accepted']);self.assertTrue(many['accepted']);self.assertEqual(one['visited_nonzeros'],many['visited_nonzeros']);self.assertEqual(one['inverse_proof'],many['inverse_proof'])
    def test_both_reject_tampered_dual_and_basis(self):
        a,b,c,k=self.case(7,19)
        for dual,cols,inv in ((-k['y'],k['columns'],k['inverse']),(k['y']+1/1024,k['columns'],k['inverse']),(k['y'],k['columns'],np.zeros((7,7))),(k['y'],np.zeros(7,dtype=np.uint32),k['inverse'])):
            args=(a.indptr,a.indices,a.data,b,c,k['x0'],dual,cols,inv)
            self.assertFalse(serial(*args)['accepted']);self.assertFalse(parallel(*args,force_parallel=True)['accepted'])

if __name__=='__main__':unittest.main()
