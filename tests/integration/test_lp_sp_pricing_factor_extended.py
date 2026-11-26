"""Independent exact-product bounds and precomputed projection algebra."""
from fractions import Fraction as Q
from pathlib import Path
import sys
import unittest
import numpy as np
from scipy import linalg
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'research/lp-sp-pricing/python'))
from lp_sp_pricing_factor_admit import fixture
from sp_pricing.implicit_certificate import inverse_bound
from sp_pricing.factor_projection import CpuProjection
from lp_sp_pricing_transform_endpoint import build
from lp_sp_pricing_factor_proof import verify_arrays as serial
from lp_sp_pricing_factor_parallel_proof import verify_arrays as parallel


class ExtendedFactorTests(unittest.TestCase):
    def test_parallel_integer_proof_matches_serial_with_corruptions(self):
        for seed in range(16):
            a,b,c,x,y=fixture(4+seed%5,124601+seed);certificate,_=build(a,b,c,x,y+1e-9)
            self.assertIsNotNone(certificate)
            args=[a.indptr,a.indices,a.data,b,c,certificate['x'],certificate['y0'],certificate['basis'],certificate['inverse']]
            p=parallel(*args,force_parallel=True);s=serial(*args)
            self.assertTrue(p['accepted']);self.assertEqual(p['residual_numerator'],s['residual_numerator'])
            self.assertEqual(p['inverse_proof'],s['inverse_proof']);self.assertEqual(p['visited_nonzeros'],a.nnz)
            corrupt=[*args];corrupt[8]=np.zeros_like(corrupt[8])
            self.assertFalse(parallel(*corrupt,force_parallel=True)['accepted'])
            corrupt=[*args];corrupt[6]=-np.ones(len(b))/8
            self.assertFalse(parallel(*corrupt,force_parallel=True)['accepted'])
            corrupt=[*args];corrupt[5]=x+100
            self.assertEqual(parallel(*corrupt,force_parallel=True)['accepted'],serial(*corrupt)['accepted'])

    def test_parallel_partition_rejects_malformed_offsets(self):
        a,b,c,x,y=fixture(7,124777);certificate,_=build(a,b,c,x,y);offsets=a.indptr.copy();offsets[2]=offsets[3]+1
        self.assertFalse(parallel(offsets,a.indices,a.data,b,c,x,certificate['y0'],certificate['basis'],certificate['inverse'],force_parallel=True)['accepted'])

    def test_inverse_residual_bound_contains_exact_rational_product(self):
        for seed in range(96):
            rng=np.random.default_rng(124001+seed);n=2+seed%6
            b=(rng.integers(-4,5,size=(n,n))+np.eye(n)*24)*2.**(seed%13-6)
            r=np.linalg.inv(b);proof=inverse_bound(b,r);self.assertTrue(proof['accepted'])
            exact=max(sum(abs(Q(int(i==j))-sum(Q(float(r[i,k]))*Q(float(b[k,j])) for k in range(n))) for j in range(n)) for i in range(n))
            self.assertLessEqual(exact,Q(proof['error_upper']))

    def test_precomputed_projection_matches_cholesky_iterations(self):
        for n in (7,17,33,65):
            a,b,c,_,_=fixture(n,124201+n);dense=a.toarray();factor=linalg.cho_factor(dense.T@dense,lower=True)
            transform=linalg.cho_solve(factor,dense.T).T;constant=linalg.cho_solve(factor,c)/.01
            cpu=CpuProjection(a,b,c,.01);u=np.zeros(len(b));s=np.maximum(b,0.)
            for k in range(40):
                x=transform.T@(b-s-u)+constant;v=1.6*(dense@x)+.6*(s-b)
                s=np.maximum(0.,b-v-u);u+=v+s-b
                xc,yc=cpu.advance(1)
                np.testing.assert_allclose(x,xc,rtol=2e-10,atol=2e-10)
                np.testing.assert_allclose(.01*u,yc,rtol=2e-10,atol=2e-10)


if __name__=='__main__':unittest.main()
