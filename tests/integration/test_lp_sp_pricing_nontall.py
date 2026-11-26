"""Non-tall benchmark generation checked against an independent exact oracle."""
from fractions import Fraction
from pathlib import Path
import sys
import unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
from lp_sp_pricing_nontall_experiment import arrays,SPECS,SEEDS
from lp_sp_pricing_scale_verify import verify_arrays


class NonTallProtocol(unittest.TestCase):
    def test_small_all_shapes_have_exact_original_witnesses(self):
        for m,n in ((8,8),(12,8),(4,16)):
            for layout in ('band','random'):
                for mixed in (False,True):
                    for scaled in (False,True):
                        spec=dict(m=m,n=n,degree=min(n,5),layout=layout,shift=3,scaled=scaled,mixed=mixed)
                        a,b,c,x,y,slack=arrays(spec,125001)
                        proof=verify_arrays(a.indptr,a.indices,a.data,b,c,list(map(Fraction,x)),list(map(Fraction,y)))
                        self.assertTrue(proof['accepted']);self.assertEqual(proof['visited_nonzeros'],m*spec['degree'])
                        self.assertTrue(a.has_canonical_format);self.assertTrue(np.all(y[slack>0]==0))
    def test_seed_reproducibility_and_irregular_variation(self):
        spec=dict(m=20,n=20,degree=7,layout='random',shift=1,scaled=False,mixed=True)
        a=arrays(spec,1);b=arrays(spec,1);c=arrays(spec,2)
        self.assertTrue(np.array_equal(a[0].indices,b[0].indices));self.assertTrue(np.array_equal(a[0].data,b[0].data));self.assertFalse(np.array_equal(a[0].indices,c[0].indices))
    def test_frozen_roster_covers_non_tall_dispatch_gaps(self):
        self.assertEqual(len(SPECS)*len(SEEDS)*3,72);self.assertEqual(len({s['name'] for s in SPECS}),8)
        self.assertTrue(all(s['m']<2*s['n'] for s in SPECS));self.assertEqual(sum(s['m']<s['n'] for s in SPECS),2)
        self.assertTrue(any(s['layout']=='random' for s in SPECS));self.assertTrue(any(s['mixed'] and s['m']==s['n'] for s in SPECS))


if __name__=='__main__':unittest.main()
