"""Independent exact oracles for rigorous interval proposal acceptance."""
import ctypes as C
from fractions import Fraction as Q
import math
from pathlib import Path
import random
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'research/lp-sp-pricing/python'))
from sp_pricing.exact import Work,Limit
from sp_pricing.geometry import LabelOracle
from sp_pricing.gpu import accept_proposal
from sp_pricing.gpu_wave import enclosure,PackedBasis,IntervalProof,PROOF_LIBRARY


class Enclosures(unittest.TestCase):
    def test_original_rational_is_inside_binary64_bounds(self):
        rng=random.Random(17431)
        values=[Q(0),Q(1,3),Q(-1,7),Q(1,2**1074),Q(1,2**1100),Q(-1,2**1100),Q(2**1023)]
        values+=[Q(rng.randrange(-10**12,10**12),rng.randrange(1,10**10)) for _ in range(500)]
        for value in values:
            low,high=enclosure(value)
            self.assertLessEqual(Q(low),value);self.assertGreaterEqual(Q(high),value)


@unittest.skipUnless(PROOF_LIBRARY.exists(),'interval proof library not built')
class IntervalChecks(unittest.TestCase):
    def compare(self,b,h,eps,x,u,target=0):
        oracle=LabelOracle(b,h,eps,Work(max_operations=100000000,seconds=30))
        expected=accept_proposal(oracle,target,x,u).get('established',{})
        with IntervalProof(oracle,PackedBasis(oracle)) as checker:
            actual,stats=checker.batch([2*target+1],[1],(C.c_double*len(x))(*x),(C.c_double*len(u))(*u),{})
        self.assertEqual(actual,expected)
        return stats

    def test_random_dyadic_and_non_dyadic_proposals_match_exact_oracle(self):
        rng=random.Random(99172)
        for case in range(72):
            r=1+case%5;n=1+case%7
            b=[[Q(rng.randrange(-20,21),rng.choice([1,2,4,7,11])) for _ in range(2*n)] for _ in range(r)]
            x=[rng.randrange(-40,41)/8 for _ in range(r)]
            u=[rng.randrange(-20,21)/16 for _ in range(2*n)]
            self.compare(b,Q(7,3),Q(1,1024*n),x,u,case%n)

    def test_threshold_equality_uses_gmp_instead_of_guessing(self):
        stats=self.compare([[0,1]],4,Q(1,1024),[.25],[0.,0.])
        self.assertEqual(stats['gmp_fallbacks'],1)

    def test_easy_primal_and_dual_are_decided_without_gmp(self):
        for b,x,u in [([[0,1]],[1.],[0.,0.]),([[0,0]],[0.],[0.,0.])]:
            stats=self.compare(b,4,Q(1,1024),x,u)
            self.assertEqual(stats['gmp_fallbacks'],0)

    def test_cancellation_subnormal_and_box_clipping(self):
        cases=[([[0,Q(1,2**1074)]],1,[1.],[0.,0.]),
               ([[0,Q(1,3)]],Q(1,3),[1.],[0.,0.]),
               ([[0,2**40],[0,-2**40],[0,1]],4,[1.,1.,.25],[0.,1.])]
        for b,h,x,u in cases:self.compare(b,h,Q(1,1024),x,u)

    def test_nonfinite_proposal_does_not_establish_a_label(self):
        self.compare([[0,1]],4,Q(1,1024),[math.nan],[0.,0.])
        self.compare([[0,1]],4,Q(1,1024),[1.],[math.inf,0.])

    def test_nondefault_rounding_mode_falls_back_to_exact(self):
        oracle=LabelOracle([[0,1]],4,Q(1,1024),Work(seconds=30))
        checker=IntervalProof(oracle,PackedBasis(oracle));libm=C.CDLL('libm.so.6')
        previous=libm.fegetround()
        try:
            self.assertEqual(libm.fesetround(0x400),0)
            labels,stats=checker.batch([1],[1],(C.c_double*1)(1.),(C.c_double*2)(0.,0.),{})
            self.assertEqual(labels,{0:1});self.assertEqual(stats['gmp_fallbacks'],1)
        finally:libm.fesetround(previous);checker.close()

    def test_lifetime_dimensions_and_operation_cap(self):
        oracle=LabelOracle([[0,1]],4,Q(1,1024),Work(seconds=30))
        checker=IntervalProof(oracle,PackedBasis(oracle))
        for slots,active,x,u,known in [([2],[1],[0.],[0.,0.],{}),([1],[],[0.],[0.,0.],{}),
            ([1],[1],[],[0.,0.],{}),([1],[1],[0.],[0.,0.],{2:1})]:
            with self.assertRaises(ValueError):checker.batch(slots,active,(C.c_double*len(x))(*x),(C.c_double*len(u))(*u),known)
        oracle.work.max_operations=oracle.work.operations
        with self.assertRaises(Limit):checker.batch([1],[1],(C.c_double*1)(1.),(C.c_double*2)(0.,0.),{})
        checker.close()
        with self.assertRaises(ValueError):checker.batch([1],[1],(C.c_double*1)(1.),(C.c_double*2)(0.,0.),{})


if __name__=='__main__':unittest.main()
