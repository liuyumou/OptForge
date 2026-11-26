"""Dense BLAS proposals preserve independently certified mathematical endpoints."""
from pathlib import Path
import sys
import unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'research/lp-sp-pricing/python'))
from lp_sp_pricing_nontall_experiment import arrays
from sp_pricing.primal_recovery import row_proposal as old
from sp_pricing.primal_recovery_fast import row_proposal
from sp_pricing.primal_recovery_balanced import build
from lp_sp_pricing_primal_proof import verify_arrays

class DensePrimal(unittest.TestCase):
    def test_dense_cpu_equivalence_and_independent_certificates(self):
        for m,n in ((3,11),(17,49),(32,128)):
            for seed in (126521,126523):
                a,b,c,_,_,_=arrays(dict(m=m,n=n,degree=n,layout='band',shift=1,scaled=False,mixed=True),seed)
                x,y,_=row_proposal(a,b,c);xp,yp,_=old(a,b,c)
                self.assertTrue(np.allclose(x,xp,atol=1e-11,rtol=1e-11));self.assertTrue(np.allclose(y,yp,atol=1e-11,rtol=1e-11))
                cert,_=build(a,b,c,x,y);self.assertIsNotNone(cert)
                self.assertTrue(verify_arrays(a.indptr,a.indices,a.data,b,c,cert['x0'],cert['y'],cert['columns'],cert['inverse'])['accepted'])

if __name__=='__main__':unittest.main()
