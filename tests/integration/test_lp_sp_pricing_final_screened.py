"""Conservative correction screening retains independent exact authority."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'research/lp-sp-pricing/python'))
from lp_sp_pricing_nontall_experiment import arrays
from lp_sp_pricing_factor_proof import verify_arrays
from sp_pricing.dual_recovery_screened import build
import sp_pricing.dual_recovery_screened as subject

class ScreenedRecovery(unittest.TestCase):
    def test_valid_recovery_matches_arbitrary_integer_proof(self):
        for scaled in (False,True):
            a,b,c,x,y,_=arrays(dict(m=24,n=8,degree=8,layout='band',shift=1,scaled=scaled,mixed=True),128051)
            k,d=build(a,b,c,x,y+np.where(y>0,1e-12,0));self.assertIsNotNone(k)
            self.assertEqual(d['numerical_dual_refinement_steps'],2);self.assertTrue(verify_arrays(a.indptr,a.indices,a.data,b,c,k['x'],k['y0'],k['basis'],k['inverse'])['accepted'])
    def test_failed_screen_never_constructs_full_inverse(self):
        a,b,c,x,y,_=arrays(dict(m=24,n=8,degree=8,layout='band',shift=1,scaled=False,mixed=True),128053);shapes=[]
        def impossible(factor,rhs,**kwargs):
            shapes.append(np.shape(rhs));return np.full_like(rhs,-1e6)
        with patch.object(subject.linalg,'lu_solve',side_effect=impossible):certificate,detail=build(a,b,c,x,y)
        self.assertIsNone(certificate);self.assertTrue(shapes);self.assertTrue(all(shape==(8,) for shape in shapes));self.assertTrue(all(not q['inverse_constructed'] for q in detail['attempts']))

if __name__=='__main__':unittest.main()
