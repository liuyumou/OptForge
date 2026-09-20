"""Causal-diagnostic scope, exact representation arithmetic and immutable history."""
from pathlib import Path
import struct
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from diagnose_lp_precision import jobs,label,work_limit,CONFIG
from analyze_lp_precision_diagnosis import quantization_rows, iteration_execution, counter_status, short_eligible
from lp_protocol import Ledger,read_json
from report_lp_precision import use_historical_snapshot

class PrecisionDiagnosisTests(unittest.TestCase):
    def test_frozen_diagnostics_have_equal_proposals_and_explicit_physical_cost(self):
        value=read_json(CONFIG);schedule=list(jobs(value))
        self.assertEqual(len(schedule),213)
        self.assertEqual(len({label(j) for j in schedule}),213)
        self.assertEqual([sum(j[0]==k for j in schedule) for k in ['short','trace','counter']],[196,14,3])
        self.assertTrue(all(work_limit(j[2])==(206 if 'correction32' in j[2]['id'] else 200) for j in schedule))
        self.assertEqual(schedule,list(jobs(value)))
    def test_exact_row_diagnostic_distinguishes_the_original_operator(self):
        a=1/3;b=struct.unpack('f',struct.pack('f',a))[0]
        model=dict(variables=[dict(id=0)],constraints=[dict(id=0,lower=dict(kind='negative_infinity'),upper=dict(kind='finite',value=a))])
        op=dict(row_scale=[0.5],column_scale=[2.0],entries=[[0,0,a,a,b]])
        endpoint=dict(record=dict(candidate=dict(values=[dict(variable_id=0,value=1.0)]),validation=dict(constraints=[dict(constraint_id=0,upper=dict(allowance=1e-9))])))
        row=quantization_rows(model,op,endpoint)[0]
        self.assertEqual(row['matrix_shift'],b-a)
        self.assertFalse(row['checks'][0]['original_rejected'])
        self.assertTrue(row['checks'][0]['represented_rejected'])
    def test_later_settled_jobs_do_not_rewrite_historical_spending(self):
        with tempfile.TemporaryDirectory() as tmp:
            with Ledger(Path(tmp),'a'*64) as ledger:
                r=ledger.reserve('original',1);ledger.settle(r,123)
                snapshot=ledger.path.read_bytes()
                r=ledger.reserve('later',1);ledger.settle(r,456)
                active=ledger.path.read_bytes()
                self.assertEqual(ledger.totals(),579)
                use_historical_snapshot(ledger,snapshot,active)
                self.assertEqual(ledger.totals(),123)
                self.assertEqual(ledger.path.read_bytes(),active)
                with self.assertRaises(ValueError):use_historical_snapshot(ledger,snapshot[:-1],active)
                with self.assertRaises(ValueError):use_historical_snapshot(ledger,snapshot,b'changed\n'+active)

    def test_phase_boundaries_and_counter_permission_are_not_misreported(self):
        self.assertEqual(iteration_execution(dict(kernels_and_synchronization=20,
            working_upload=3, readback=4, fp64_correction=9, device_context=100)),27)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'metrics.csv'
            path.write_text('==ERROR== ERR_NVGPUCTRPERM\n')
            result=counter_status(path)
            self.assertFalse(result['available'])
            self.assertEqual(result['status'],'permission_denied')
            path.write_text('==PROF== Connected; no metrics\n')
            self.assertFalse(counter_status(path)['available'])

    def test_deliberate_work_limit_is_timed_but_failure_is_retained(self):
        row=dict(kind='short',equal_work=True,verified=True,termination='iteration_limit',
                 worker=dict(reason='completed',returncode=1))
        self.assertTrue(short_eligible(row))
        row['termination']='numerical_failure'
        self.assertFalse(short_eligible(row))
        row['termination']='iteration_limit';row['worker']['reason']='timeout'
        self.assertFalse(short_eligible(row))
