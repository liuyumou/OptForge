"""MIXED2 pilot attribution and independent guard contracts."""
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
from lp_mixed2_pilot_validate import union,profile,check_guard,rhs
from lp_mixed2_pilot_cpu import numerical_source,environment
from lp_mixed2_pilot_common import CPU_CAPS,GPU_CAPS

class Pilot(unittest.TestCase):
    def test_concurrent_intervals_are_not_summed(self):
        self.assertEqual(union([(0,10),(2,7),(9,15),(20,22)]),17)
        self.assertEqual(union([]),0)
        with self.assertRaises(ValueError):union([(5,2)])
    def test_profile_coverage_and_refusal(self):
        self.assertEqual(profile([])['matrix_union_ns'],0)
        with self.assertRaises(ValueError):profile([{'mixed2_device_profile':dict(count=1,done=1,outer_gpu_us=2,kernels=[],blocks=1)}])
    def test_rational_guard_detects_optimistic_bound(self):
        i=dict(rows=1,cols=2,a=[.1,-.2],x=[1.,2.],transpose=False)
        self.assertEqual(check_guard(i,[-.3],[1e-15])['outputs'],1)
        with self.assertRaises(ValueError):check_guard(i,[-.3],[0.])
    def test_transpose_padding_and_nonfinite(self):
        i=dict(rows=1,cols=2,a=[1.,-2.],x=[3.],transpose=True)
        check_guard(i,[3.,-6.,0.],[0.,0.,0.])
        with self.assertRaises(ValueError):check_guard(i,[3.,-6.,1.],[0.,0.,0.])
        with self.assertRaises(ValueError):check_guard(i,[3.,-6.],[float('inf'),0.])
    def test_exact_solver_and_independent_allocations(self):
        numerical_source();self.assertEqual(sum(CPU_CAPS.values()),48000);self.assertEqual(sum(GPU_CAPS.values()),2400)
        self.assertEqual(environment('profile')['GPUP_MIXED2_PILOT_VARIANT'],'profile')
        with self.assertRaises(ValueError):environment('auto')
    def test_operands_nonzero_and_generic(self):
        self.assertTrue(all(v!=0 for v in rhs(512)));self.assertEqual(rhs(512),rhs(512));self.assertGreater(len(set(rhs(512))),100)
