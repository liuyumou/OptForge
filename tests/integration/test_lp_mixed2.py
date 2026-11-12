"""MIXED2 cost boundary, coverage, independent enclosure and allocation guards."""
import copy
import math
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from lp_mixed2_cost import forecast, validate, summarize, scenarios, TARGETS, METRICS
from lp_mixed2_oracle import check
from lp_mixed2_budget import admission_open, accounting
from lp_mixed2_common import NS, CPU_CAPS, GPU_CAPS
from lp_fp4_accel_model import FAMILIES
from lp_delivery4_stats import interval


def cohort(lifecycle='cold'):
    rows=[]
    for b in range(32):
        for f in FAMILIES:
            certified=f!='infinite-bound-refusal'
            rec=dict(certified=certified,complete_ns=10_000_000,costs_ns={'iteration':4_000_000 if certified else 0,'checker':1_000_000},
                     gpu_us=3000. if certified else 0.,physical=200 if certified else 0,setup_ns=1_000_000,solve_ns=5_000_000 if certified else 1_000_000)
            rows.append(dict(block=b,family=f,lane='nativefast',tier='certified-1e-9',role='candidate',lifecycle=lifecycle,
                variant='candidate' if lifecycle=='cold' else 'batch',certified=certified,complete_ns=rec['complete_ns'],
                records=[copy.deepcopy(rec) for _ in range(1 if lifecycle=='cold' else 3)],setup={'total_ns':1_000_000},teardown_ns=100_000))
    return rows


class Mixed2Contract(unittest.TestCase):
    def test_complete_cost_formula_and_impossible_target(self):
        self.assertEqual(forecast(100,2,None,1,0),98)
        self.assertEqual(forecast(100,20,2,1.25,3),95.5)
        self.assertLess(100/forecast(100,2,None,1,0),1.1)

    def test_bad_forecast_inputs_refuse(self):
        for values in ((0,0,2,1,0),(10,10,2,1,0),(10,-1,2,1,0),(10,1,0,1,0),(10,1,2,.5,0),(10,1,2,1,-1),(math.inf,1,2,1,0),(10,1,math.nan,1,0)):
            with self.assertRaises(ValueError):forecast(*values)

    def test_frozen_scenarios_and_exact_uncertainty(self):
        self.assertEqual(len(list(scenarios())),145)
        ci=interval(list(range(32)),metrics=METRICS);k=ci['ranks'][0]
        self.assertLessEqual(sum(math.comb(32,i) for i in range(k))*40*METRICS,2**32)
        self.assertGreater(sum(math.comb(32,i) for i in range(k+1))*40*METRICS,2**32)
        self.assertEqual(len(set(s['id'] for s in scenarios())),145)

    def test_coverage_duplicates_and_refusals_cannot_disappear(self):
        rows=cohort();validate(rows,FAMILIES,'cold')
        with self.assertRaises(ValueError):validate(rows[:-1],FAMILIES,'cold')
        with self.assertRaises(ValueError):validate(rows+[rows[0]],FAMILIES,'cold')
        for row in rows:
            if row['family']=='infinite-bound-refusal':row['records'][0]['certified']=True
        with self.assertRaises(ValueError):validate(rows,FAMILIES,'cold')

    def test_bad_timer_boundaries_and_zero_work_refuse(self):
        for field,value in (('gpu_us',100_000.),('physical',0),('complete_ns',-1),('setup_ns',10_000_000)):
            rows=cohort();rows[0]['records'][0][field]=value
            with self.assertRaises(ValueError):validate(rows,FAMILIES,'cold')
        rows=cohort();rows[0]['records'][0]['costs_ns']['checker']=-1
        with self.assertRaises(ValueError):validate(rows,FAMILIES,'cold')

    def test_regression_guard_vetoes_a_good_dense_forecast(self):
        rows=cohort();s=dict(fraction=1.,speed=2.,work=1.,overhead_ms=0.)
        self.assertTrue(summarize(rows,FAMILIES,'cold',s)['conditional_all_cost_rules_supported'])
        for row in rows:
            if row['family'] not in TARGETS:row['records'][0]['gpu_us']=0.
        s['overhead_ms']=.3
        decision=summarize(rows,FAMILIES,'cold',s)
        self.assertEqual(decision['benefit']['decision'],'supported')
        self.assertFalse(decision['conditional_all_cost_rules_supported'])
        self.assertTrue(any(g['decision']=='material-regression' for g in decision['guards']))

    def test_prepared_transforms_each_solve_before_median(self):
        rows=cohort('prepared')
        for row in rows:
            if row['certified']:
                for rec,t,g in zip(row['records'],(9_000_000,10_000_000,11_000_000),(0.,3000.,0.)):
                    rec['complete_ns']=t;rec['gpu_us']=g
        value=summarize(rows,FAMILIES,'prepared',dict(fraction=1.,speed=None,work=1.,overhead_ms=0.))
        # median(9,7,11)=9; subtracting marginal medians would incorrectly yield 10.
        self.assertAlmostEqual(value['benefit']['median'],10/9)

    def test_oracle_rejects_plausible_but_wrong_product(self):
        req=dict(matrix=dict(rows=1,cols=1,offsets=[0,1],columns=[0],values=[1.]),x=[2.],transpose=False)
        p=dict(values=[2.],error_bounds=[0.],representation_bounds=[0.],rounding_bounds=[0.])
        self.assertEqual(check(req,dict(status='enclosed',product=p)),1)
        p['values']=[2.000001]
        with self.assertRaises(ValueError):check(req,dict(status='enclosed',product=p))

    def test_closed_or_unsettled_allocation_refuses(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);(base/'CLOSED.json').write_text('{}')
            with self.assertRaises(ValueError):admission_open(base)
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);(base/'resources').mkdir();(base/'resources/job.reservation.json').write_text('{}')
            with self.assertRaises(ValueError):admission_open(base)

    def test_independent_cpu_allocation(self):
        self.assertEqual(sum(CPU_CAPS.values()),16000);self.assertEqual(GPU_CAPS,{})
        with tempfile.TemporaryDirectory() as temp:
            cpu,gpu=accounting(Path(temp));self.assertEqual(sum(cpu.values()),512*NS);self.assertEqual(gpu,{})

if __name__=='__main__':unittest.main()
