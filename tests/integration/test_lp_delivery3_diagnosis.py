"""Timer-boundary and optimistic-cost contract regressions."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import lp_delivery3_diagnose as diagnosis


class DiagnosisContracts(unittest.TestCase):
    def record(self):
        return dict(costs_ns=dict(iteration=4000, checker=2000, coordination=1000),
                    solve_ns=7000, setup_ns=5000, complete_ns=15000, gpu_us=3.)

    def test_nested_event_and_cold_setup_are_not_double_counted(self):
        parts=diagnosis.components(self.record(), 'cold')
        self.assertAlmostEqual(sum(parts.values()), .015)
        self.assertEqual(parts['iteration_outside_event'], .001)
        self.assertEqual(parts['outside_solve_and_setup'], .003)

    def test_prepared_excludes_setup_already_paid(self):
        record=self.record();record['complete_ns']=10000
        parts=diagnosis.components(record,'prepared')
        self.assertEqual(parts['session_setup'],0)
        self.assertEqual(parts['outside_solve_and_setup'],.003)
        self.assertAlmostEqual(sum(parts.values()),.01)

    def test_intentional_refusal_has_no_iteration_timer(self):
        record=dict(costs_ns=dict(checker=2000),solve_ns=2000,setup_ns=1000,complete_ns=5000,gpu_us=0.)
        parts=diagnosis.components(record,'cold')
        self.assertEqual(parts['gpu_event'],0)
        self.assertAlmostEqual(sum(parts.values()),.005)

    def test_bad_timer_boundaries_refuse(self):
        for field,value in (('solve_ns',8000),('gpu_us',5.),('complete_ns',10000)):
            with self.subTest(field=field):
                record=self.record();record[field]=value
                with self.assertRaises(ValueError):diagnosis.components(record,'cold')

    def test_cost_bound_counts_added_work_and_cost(self):
        self.assertAlmostEqual(diagnosis.forecast(10,2),1.25)
        self.assertAlmostEqual(diagnosis.forecast(10,2,2),10/9)
        self.assertEqual(diagnosis.forecast(10,2,2,2),1)
        self.assertLess(diagnosis.forecast(10,2,2,2,1),1)
        with self.assertRaises(ValueError):diagnosis.forecast(10,11)

    def test_constant_association_is_unidentified(self):
        self.assertIsNone(diagnosis.correlation([1,1,1],[2,3,4]))
        self.assertAlmostEqual(diagnosis.correlation([1,2,3],[4,3,2]),-1)


if __name__=='__main__':unittest.main()
