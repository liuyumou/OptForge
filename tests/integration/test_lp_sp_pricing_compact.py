"""Exact storage, implicit geometry and lazy-fallback contracts (CPU only)."""
from fractions import Fraction as Q
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'research/lp-sp-pricing/python'))
sys.path.insert(0,str(ROOT/'tools'))
from sp_pricing.compact_basis import Rows,Storage,NullRows,PairedRows,TileSource,product,sparse_rref
from sp_pricing.compact_geometry import CompactCalibration,CompactOracle
from sp_pricing.compact_gpu import TileProof,exact_labels
from sp_pricing.compact_solver import CompactSolver
from sp_pricing.exact import Work,Limit,rref,nullspace
from sp_pricing.geometry import paired_space,LabelOracle
from sp_pricing.calibration import DirectCalibration
from sp_pricing.native_proof import NativeProof


def dense(matrix):return [[matrix.row(i).get(j,Q(0)) for j in range(matrix.s)] for i in range(matrix.r)]
def work():return Work(seconds=90,max_operations=100000000)


class CompactGeometryTests(unittest.TestCase):
    def test_sparse_rref_and_implicit_nullspace_match_exact(self):
        for seed in range(12):
            rng=np.random.default_rng(seed);a=rng.integers(-2,3,size=(4,7)).tolist()
            if seed%2:a[-1]=a[0][:]
            source=Rows.dense(a);reduced,p=sparse_rref(source.rows,7,work(),Storage())
            expected,pivots=rref(a,work())
            self.assertEqual(p,pivots);self.assertEqual(dense(reduced),expected[:len(p)])
            self.assertEqual(dense(NullRows(reduced,p)),nullspace(a,work(),7))
            self.assertEqual(dense(PairedRows(reduced,p)),paired_space(a,work(),7))

    def test_factor_products_and_storage_scale_with_factors(self):
        source=Rows([{i:Q(1)} for i in range(4000)],8000)
        paired=PairedRows(source,list(range(4000)))
        self.assertEqual(paired.stored_entries,4000)
        self.assertEqual(paired.r*paired.s,128000000)
        x=[Q(1)]*paired.r
        y=product(paired,x,True)
        self.assertEqual(sum(y),8000)
        self.assertEqual(sum(len(paired.row(i)) for i in range(paired.r)),8000)

    def test_sparse_calibration_matches_original_half_integral_prices(self):
        reduced,p=sparse_rref(Rows.dense([[1,2,0,1],[0,1,1,-1]]).rows,4,work(),Storage())
        factor=PairedRows(reduced,p);reference=dense(factor)
        for prices in [[0]*4,[Q(1,2),Q(-1,2),2,-1]]:
            old=DirectCalibration(reference,work()).query(prices)
            new=CompactCalibration(factor,work()).query(prices)
            self.assertEqual(dense(new['basis']),old['basis'])
            for key in ['H','epsilon','entry_error','displacement_bound','pivots','demand_bound']:
                self.assertEqual(new[key],old[key],key)

    def test_lazy_fallback_is_never_built_for_resolved_gpu_labels(self):
        matrix=Rows.dense([[0,1,0,0],[0,0,1,0]])
        oracle=CompactOracle(matrix,4,Q(1,65536),work(),isotropic_error=0)
        with patch('sp_pricing.compact_gpu.proposals',return_value=({0:1,1:-1},{'test':True})):
            labels,_=oracle.labels(gpu={})
        self.assertEqual(labels,[1,-1]);self.assertIsNone(oracle._a)
        self.assertEqual(oracle.fallback_constructions,0)

    def test_lazy_cpu_fallback_matches_existing_oracle(self):
        b=[[0,1,0,0],[0,0,1,0]]
        new=CompactOracle(Rows.dense(b),4,Q(1,65536),work(),isotropic_error=0)
        old=LabelOracle(b,4,Q(1,65536),work(),isotropic_error=0)
        self.assertEqual(new.labels()[0],old.labels()[0]);self.assertEqual(new.fallback_constructions,1)
        self.assertEqual(new.a,old.a);self.assertEqual(new.rhs,old.rhs)

    def test_large_fallback_refuses_before_allocating(self):
        oracle=CompactOracle(Rows([{i:Q(1)} for i in range(1000)],2000),4,Q(1,65536),work())
        with self.assertRaisesRegex(Limit,'tableau_limit'):oracle.fallback()
        self.assertIsNone(oracle._a)

    def test_tile_cache_is_bounded_and_does_not_materialize_nullspace(self):
        rows=Rows([{i:Q(1)} for i in range(100)],200)
        source=TileSource(PairedRows(rows,list(range(100))),8,16,cache_bytes=6144)
        for key in source.descriptors:
            tile=source.tile(key);self.assertFalse(tile.flags.writeable)
        self.assertLessEqual(source.peak_bytes,6144)
        self.assertEqual(source.nnz,200)

    def test_sparse_storage_failure_and_original_certificates(self):
        with self.assertRaisesRegex(Limit,'storage_limit'):
            sparse_rref(Rows.dense([[1,2,3],[0,1,2]]).rows,3,work(),Storage(entries=2))
        from lp_sp_pricing_verify import verify
        models=[dict(A=[[1],[-1]],b=[2,0],c=[1]),dict(A=[[1],[-1]],b=[0,-1],c=[1]),
                dict(A=[[-1]],b=[0],c=[1])]
        for model in models:
            solver=CompactSolver(work=work(),extra_experts=0,max_queries=64,market_backend='flow')
            result=solver.solve(model)
            self.assertTrue(verify(model,result)['accepted'])


class StreamProofTests(unittest.TestCase):
    def test_sparse_tiles_match_exact_and_reject_closed_checker(self):
        oracle=CompactOracle(Rows([{2*i+1:Q(1)} for i in range(20)],80),4,Q(1,65536),work())
        source=TileSource(oracle.matrix,8,16,cache_bytes=4096)
        x=np.zeros((2,20));x[0,0]=.5;x[1,7]=.25;u=np.zeros((2,80))
        with TileProof(oracle,source) as checker:
            found,stats=checker.batch([1,15],x,u)
            expected=exact_labels(oracle,0,x[0],u[0]);expected.update(exact_labels(oracle,7,x[1],u[1]))
            self.assertEqual(found,expected);self.assertLessEqual(stats['sparse_check_cache_peak'],4096)
        with self.assertRaises(ValueError):checker.batch([1,15],x,u)

    def test_tiled_intervals_and_exact_fallback_match_gmp(self):
        rng=np.random.default_rng(77)
        for case in range(8):
            b=[[Q(int(x),8) for x in row] for row in rng.integers(-4,5,size=(9,12))]
            compact=CompactOracle(Rows.dense(b),4,Q(1,65536),work())
            old=LabelOracle(b,4,Q(1,65536),work())
            old.broadcast_negative=False
            source=TileSource(compact.matrix,4,4,cache_bytes=0)
            x=rng.integers(-4,5,size=(3,9)).astype(float)/8
            u=rng.integers(-4,5,size=(3,12)).astype(float)/16
            slots=[1,5,9];reference={}
            with NativeProof(old) as gmp,TileProof(compact,source) as check:
                for i,s in enumerate(slots):reference.update(gmp.labels(s//2,x[i].tolist(),u[i].tolist())['established'])
                labels,_=check.batch(slots,x,u)
            for i,value in labels.items():self.assertEqual(reference[i],value)

    def test_threshold_clipping_and_nonfinite_proposals(self):
        oracle=CompactOracle(Rows.dense([[0,1]]),4,Q(1,65536),work(),isotropic_error=0)
        source=TileSource(oracle.matrix,1,1,cache_bytes=0)
        with TileProof(oracle,source) as checker:
            labels,stats=checker.batch([1],np.array([[.25]]),np.array([[0.,0.]]))
            self.assertEqual(labels,{0:1});self.assertEqual(stats['exact_fallbacks'],1)
            labels,_=checker.batch([1],np.array([[8.]]),np.array([[0.,0.]]))
            self.assertEqual(labels,{0:1})
            labels,_=checker.batch([1],np.array([[np.nan]]),np.array([[0.,0.]]))
            self.assertEqual(labels,{})


if __name__=='__main__':unittest.main()
