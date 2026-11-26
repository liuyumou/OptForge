"""Exact rational cross-checks for the implicit dual certificate."""
from fractions import Fraction as Q
from pathlib import Path
import sys
import unittest
import numpy as np
from scipy import sparse
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools')); sys.path.insert(0, str(ROOT/'research/lp-sp-pricing/python'))
from lp_sp_pricing_factor_proof import verify_arrays, build
from sp_pricing.implicit_certificate import inverse_bound, correction_bound
from sp_pricing.exact import Work, solve


class FactorCertificateTests(unittest.TestCase):
    def test_non_dyadic_exact_dual_is_proved_implicitly(self):
        a = sparse.csr_matrix([[3.]])
        y0 = np.array([np.rint((1/3)*2**48)/2**48])
        p = verify_arrays(a.indptr, a.indices, a.data, np.array([3.]), np.array([1.]),
                          np.array([1.]), y0, np.array([0], dtype=np.uint32), np.array([[1/3]]))
        self.assertTrue(p['accepted']); self.assertGreater(int(p['residual_numerator']), 0)
        self.assertEqual(Q(1)-Q(3)*Q(1, 3), 0)

    def test_64_inverse_enclosures_cover_exact_fraction_solves(self):
        for seed in range(64):
            rng = np.random.default_rng(123401+seed); n = 2+seed % 6
            b = rng.integers(-3, 4, size=(n, n)).astype(float)+np.eye(n)*32
            inverse = np.linalg.inv(b); p = inverse_bound(b, inverse)
            self.assertTrue(p['accepted'])
            rhs = rng.integers(-8, 9, size=n).tolist()
            exact = solve([[Q(float(v)) for v in row] for row in b], list(map(Q, rhs)), Work(seconds=5))
            self.assertIsNotNone(exact)
            self.assertLessEqual(max(map(abs, exact)), Q(correction_bound(p['inverse_norm_upper'], max(map(abs, rhs)))))

    def test_32_tall_certificates_match_explicit_exact_duals(self):
        for seed in range(32):
            rng = np.random.default_rng(123601+seed); n = 2+seed % 6
            a = sparse.csr_matrix(np.vstack([np.eye(n)*3, rng.integers(-3, 4, size=(n, n))]))
            x = np.ones(n); y = np.full(2*n, .125); b = a@x; c = np.asarray(a.T@y)
            y0 = y.copy(); y0[:n] += 2**-30
            basis = np.arange(n, dtype=np.uint32); inverse = np.eye(n)/3
            p = verify_arrays(a.indptr, a.indices, a.data, b, c, x, y0, basis, inverse)
            self.assertTrue(p['accepted'])
            residual = [Q(float(v))-sum(Q(float(a[i,j]))*Q(float(y0[i])) for i in range(2*n)) for j,v in enumerate(c)]
            corrected = [Q(float(y0[j]))+residual[j]/3 for j in range(n)]
            self.assertTrue(all(v >= 0 for v in corrected))

    def test_invalid_basis_inverse_primal_and_support_rejected(self):
        a = sparse.csr_matrix([[3.,0.],[0.,3.],[1.,1.]])
        b = np.array([3.,3.,3.]); c = np.ones(2); x = np.ones(2); y = np.rint(np.array([1/3,1/3,0.])*2**48)/2**48
        basis = np.array([0,1], dtype=np.uint32); inverse = np.eye(2)/3
        self.assertTrue(verify_arrays(a.indptr,a.indices,a.data,b,c,x,y,basis,inverse)['accepted'])
        cases = [(x+1,y,basis,inverse),(x,y+np.array([0,0,1.]),basis,inverse),
                 (x,y,np.array([0,2],dtype=np.uint32),inverse),(x,y,basis,np.eye(2)),
                 (x,y,np.array([0,0],dtype=np.uint32),inverse)]
        for xx,yy,bb,rr in cases:
            self.assertFalse(verify_arrays(a.indptr,a.indices,a.data,b,c,xx,yy,bb,rr)['accepted'])

    def test_insufficient_positive_margin_rejects_correction(self):
        a = sparse.csr_matrix([[1.]])
        p = verify_arrays(a.indptr,a.indices,a.data,np.array([0.]),np.array([-1.]),
                          np.array([0.]),np.array([.1]),np.array([0],dtype=np.uint32),np.array([[1.]]))
        self.assertFalse(p['accepted'])

    def test_singular_or_corrupt_inverse_is_inconclusive(self):
        self.assertFalse(inverse_bound(np.zeros((2,2)),np.eye(2))['accepted'])
        self.assertFalse(inverse_bound(np.eye(2),np.full((2,2),np.nan))['accepted'])
        self.assertFalse(inverse_bound(np.eye(2),np.ones((2,2)))['accepted'])


if __name__ == '__main__': unittest.main()
