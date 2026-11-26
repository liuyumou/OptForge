"""Independent exact acceptance contracts for the lean GPU candidate."""
from fractions import Fraction as Q
import ctypes as C
from pathlib import Path
import random
import sys
import unittest
from unittest.mock import patch
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'research/lp-sp-pricing/python'))
from sp_pricing.exact import Work, Limit
from sp_pricing.geometry import LabelOracle
from sp_pricing.gpu import accept_proposal
from sp_pricing.native_proof import NativeProof, LIBRARY
from sp_pricing import gpu_lean


class PilotControlTests(unittest.TestCase):
    def run_pilot(self,accepted):
        advances=[];checks=[]
        class Engine:
            preparation_ns=0;digest='mock'
            def __init__(self,*args):pass
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def begin(self,slots,*args):self.width=len(slots)
            def active(self,flags):self.flags=flags
            def advance(self,steps):
                advances.append(steps)
                return dict(x=[[0.]]*self.width,dual=[[0.,0.]]*self.width,width=self.width,
                    elapsed_ns=0,device_iteration_ms=0,steps=steps,mode='fp64')
        class Checker:
            preparation_ns=0
            def __init__(self,*args):pass
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def labels(self,*args):
                checks.append(args[0]);return dict(established={0:1} if accepted else {})
        oracle=SimpleNamespace(r=1,n=1,b=[[0,1]],h=1,epsilon=Q(1,1024),work=Work(seconds=30))
        with patch.object(gpu_lean,'LeanBatch',Engine),patch.object(gpu_lean,'NativeProof',Checker):
            labels,proofs,metadata=gpu_lean.propose_labels(oracle,'unused',64,steps=1000)
        return labels,metadata,advances,checks

    def test_unproductive_pilot_hands_off_without_spending_remaining_steps(self):
        labels,metadata,advances,checks=self.run_pilot(False)
        self.assertEqual(labels,{})
        self.assertEqual(advances,[64,192])
        self.assertEqual(metadata['exact_cpu_handoff'],'no_exact_label_after_pilot')

    def test_exact_label_prunes_companion_and_remaining_stages(self):
        labels,metadata,advances,checks=self.run_pilot(True)
        self.assertEqual(labels,{0:1})
        self.assertEqual(advances,[64])
        self.assertEqual(checks,[0])


@unittest.skipUnless(LIBRARY.exists(),'native proof library not built')
class NativeProposalTests(unittest.TestCase):
    def test_native_matches_independent_python_full_proof(self):
        rng=random.Random(72841)
        for case in range(12):
            r,s=1+case%4,2*(2+case%5)
            b=[[Q(rng.randrange(-8,9),1<<rng.randrange(5)) for _ in range(s)] for _ in range(r)]
            oracle=LabelOracle(b,Q(7,3),Q(1,1024),Work(max_operations=10000000,seconds=30))
            with NativeProof(oracle) as checker:
                for trial in range(8):
                    x=[rng.randrange(-64,65)/8 for _ in range(r)]
                    u=[rng.randrange(-32,33)/16 for _ in range(s)]
                    target=trial%(s//2)
                    old=accept_proposal(oracle,target,x,u);new=checker.check(target,x,u,full_dual=True)
                    for key in ['x','witness','dual','dual_upper','established','accepted']:
                        self.assertEqual(old[key],new[key],(case,trial,key))
                    compact=checker.labels(target,x,u)
                    self.assertEqual(old['established'],compact['established'])

    def test_primal_exit_omits_only_unneeded_dual_work(self):
        oracle=LabelOracle([[0,1,0,0]],1,Q(1,1024),Work(seconds=30))
        with NativeProof(oracle) as checker:
            positive=checker.check(0,[1.0],[0.0]*4)
            self.assertEqual(positive['established'],{0:1})
            self.assertIsNone(positive['dual_upper'])
            self.assertEqual(oracle.witness(positive['x']),positive['witness'])
            negative=checker.check(1,[0.0],[0.0]*4)
            self.assertEqual(negative['dual_upper'],0)
            self.assertEqual(negative['established'],{1:-1})
            self.assertFalse(checker.check(0,[float('nan')],[0.0]*4)['accepted'])

    def test_bounds_dimensions_and_lifetime_fail_closed(self):
        oracle=LabelOracle([[0,1]],1,Q(1,1024),Work(seconds=30))
        with NativeProof(oracle) as checker:
            for target,x,u in [(1,[0.],[0.,0.]),(0,[],[0.,0.]),(0,[0.],[])]:
                with self.assertRaises(ValueError):checker.check(target,x,u)
            oracle.work.max_operations=oracle.work.operations
            with self.assertRaises(Limit):checker.check(0,[1.],[0.,0.])
        with self.assertRaises(ValueError):checker.check(0,[1.],[0.,0.])

    def test_native_abi_rejects_bad_shape_and_zero_denominator(self):
        oracle=LabelOracle([[0,1]],1,Q(1,1024),Work(seconds=30))
        with NativeProof(oracle) as checker:
            out=C.c_void_p();bad=(C.c_char_p*2)(b'1/0',b'1')
            self.assertEqual(checker.lib.sp_proof_create(1,2,bad,b'1',b'1/1024',16384,0,C.byref(out)),4)
            self.assertFalse(out)
            self.assertEqual(checker.lib.sp_proof_create(2147483647,2,bad,b'1',b'1/1024',16384,0,C.byref(out)),4)
            self.assertFalse(out)

    def test_large_common_denominator_uses_exact_general_fallback(self):
        oracle=LabelOracle([[0,Q(1,2**70),0,Q(1,3**45)]],8,Q(1,1024),Work(max_bits=256,seconds=30))
        with NativeProof(oracle) as checker:
            x,u=[0.1],[0.0,0.25,0.0,-0.125]
            expected=accept_proposal(oracle,0,x,u);actual=checker.check(0,x,u,full_dual=True)
            for key in ['x','witness','dual_upper','established']:self.assertEqual(expected[key],actual[key])
            self.assertEqual(actual['integer_products'],0)
            self.assertEqual(expected['established'],checker.labels(0,x,u)['established'])

    def test_opposite_witness_requires_the_dimension_dependent_separation_bound(self):
        b=[[Q(int(j==2*i+(i%2))) for j in range(34)] for i in range(17)]
        x=[1.]+[0.]*16;u=[1.]+[0.]*33
        for eps,expected in [(Q(1,1024),False),(Q(1,1024*17),True)]:
            oracle=LabelOracle(b,4,eps,Work(max_operations=10000000,seconds=30))
            self.assertEqual(oracle.broadcast_negative,expected)
            with NativeProof(oracle) as checker:
                proof=checker.labels(0,x,u)
                self.assertEqual(proof['accepted'],expected)


if __name__=='__main__':unittest.main()
