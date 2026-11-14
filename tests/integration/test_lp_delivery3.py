"""Prospective decision boundary, exact numerical preservation and pipe failure guards."""
import copy
import io
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from lp_delivery3_cpu import numerical_source, environment
from lp_delivery3_stats import interval, classify, summarize
from lp_delivery3_transport import Service
from lp_delivery3_budget import admission_open
from lp_fp4_accel_model import FAMILIES
from lp_delivery3_common import LANES, TIERS, TARGETS


def cohort():
    return [dict(block=block,family=family,lane=lane,tier=tier,lifecycle=lifecycle,role=role,
        complete_ns=20_000_000 if role=='control' or family not in TARGETS else 14_000_000,
        certified=family!='infinite-bound-refusal')
        for block in range(32) for family in FAMILIES for lane in LANES for tier in TIERS
        for lifecycle in ('cold','prepared') for role in ('control','candidate')]

class Delivery3Guards(unittest.TestCase):
    def test_state_machine_and_explicit_variant(self):
        self.assertTrue(numerical_source()['unchanged'])
        for mode in ('control','batch','overlap','combined'):
            env=environment(mode,True)
            self.assertEqual(env['GPUP_DELIVERY3_VARIANT'],mode)
            self.assertEqual(env['GPUP_DELIVERY3_PROFILE'],'1')
            self.assertNotIn('GPUP_CHECKER_ORIGINAL',env)
        with self.assertRaises(ValueError):environment('auto')

    def test_exact_simultaneous_rank_and_unbounded_small_sample(self):
        ci=interval(list(range(32)));self.assertEqual(ci['ranks'],[6,27]);self.assertEqual((ci['lower'],ci['upper']),(5,26))
        self.assertLessEqual(sum(math.comb(32,i) for i in range(6))*40*96,2**32)
        self.assertGreater(sum(math.comb(32,i) for i in range(7))*40*96,2**32)
        self.assertIsNone(interval([1,2,3])['lower'])
        self.assertEqual(classify(interval([2]*3),1.1,True),'inconclusive')
        for bad in ([],[float('nan')],[float('inf')]):
            with self.assertRaises(ValueError):interval(bad)

    def test_thresholds_ties_and_inconclusive(self):
        self.assertEqual(classify(interval([1.1]*32),1.1,True),'supported')
        self.assertEqual(classify(interval([1.0]*32),1.1,True),'insufficient-benefit')
        self.assertEqual(classify(interval([0.0]*32),0.0,False),'supported')
        self.assertEqual(classify(interval([-.1]*16+[.1]*16),0.0,False),'inconclusive')
        self.assertEqual(classify(interval([.1]*32),0.0,False),'material-regression')

    def test_target_benefit_and_small_families_are_separate(self):
        decisions=summarize(cohort(),FAMILIES)
        self.assertEqual(len(decisions),8)
        self.assertTrue(all(d['decision']=='supported' for d in decisions))
        self.assertEqual(sum(1+len(d['guards']) for d in decisions),96)

    def test_material_regression_and_missing_cells_cannot_hide(self):
        rows=cohort()
        for row in rows:
            if row['role']=='candidate' and row['family']=='coupled-equality':row['complete_ns']=21_000_000
        self.assertTrue(all(d['decision']=='material-regression' for d in summarize(rows,FAMILIES)))
        with self.assertRaises(ValueError):summarize(rows[:-1],FAMILIES)
        rows[-1]=copy.deepcopy(rows[0])
        with self.assertRaises(ValueError):summarize(rows,FAMILIES)

    def test_certification_or_refusal_change_vetoes_retention(self):
        rows=cohort()
        for row in rows:
            if row['role']=='candidate' and row['family']=='dense-generic-512':row['certified']=False
        self.assertTrue(all(d['decision']=='correctness-or-coverage-failure' for d in summarize(rows,FAMILIES)))
        rows=cohort()
        for row in rows:
            if row['family']=='infinite-bound-refusal':row['certified']=True
        self.assertTrue(all(d['decision']=='correctness-or-coverage-failure' for d in summarize(rows,FAMILIES)))

    def test_truncated_pipe_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            service=Service.__new__(Service);service.buffer=bytearray();service.log_path=Path(temp)/'stderr'
            service.proc=subprocess.Popen([sys.executable,'-c','import sys; sys.stdout.write("partial")'],stdout=subprocess.PIPE)
            try:
                with self.assertRaises(RuntimeError):service.line(3)
                self.assertEqual(Path(str(service.log_path)+'.stdout.partial').read_bytes(),b'partial')
            finally:service.proc.wait();service.proc.stdout.close()

    def test_short_writes_complete_the_frame(self):
        class Short(io.BytesIO):
            def write(self,data):return super().write(data[:3])
        writer=Short();service=Service.__new__(Service);service.proc=types.SimpleNamespace(stdin=writer)
        service.write({'op':'solve','value':-0.0})
        self.assertEqual(writer.getvalue(),b'{"op":"solve","value":-0.0}\n')

    def test_closed_allocation_is_not_reused(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);(base/'CLOSED.json').write_text('{}')
            with self.assertRaises(ValueError):admission_open(base)

if __name__=='__main__':unittest.main()
