"""Diagnostic deadlines retain original-model and strict-tolerance contracts."""
import ctypes as ct
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from lp_billion_copt_diagnostic import Journal,DurableClock,settings,cooperative_solve

class DiagnosticContracts(unittest.TestCase):
    def test_all_variants_keep_original_coefficients_and_strict_tolerances(self):
        for name in ['instrumented','scale-off','dualize-off','scale-dual-off']:
            p=settings(name,True,48000.)
            self.assertEqual((p['MatrixTol'],p['FeasTol'],p['DualTol'],p['PDLPTol']),(0.,1e-9,1e-9,1e-12))
            self.assertEqual((p['Threads'],p['LpMethod'],p['GPUMode'],p['Crossover']),(4,6,1,0))
        for bad in [0.,float('inf'),120001.]:
            with self.assertRaises(ValueError):settings('instrumented',True,bad)
    def test_phase_journal_survives_before_response(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'phases.jsonl';j=Journal(p);c=DurableClock(j);c.enter('solve_call_opaque')
            rows=[json.loads(v) for v in p.read_text().splitlines()]
            self.assertEqual(rows[-1]['phase'],'solve_call_opaque')
            self.assertIn('installation_binding',rows[-1]['exclusive_ns'])
            result=c.finish();j.close()
            self.assertEqual(sum(result['exclusive_ns'].values()),result['total_ns'])
    def test_fast_return_cancels_deadline_before_handle_cleanup(self):
        self.exercise(False)
    def test_deadline_interrupts_only_owned_problem_and_joins(self):
        self.exercise(True)
    def exercise(self, slow):
        called=[]
        class Fn:
            def __call__(self,handle):called.append(handle);return 0
        class Lib:
            COPT_Interrupt=Fn()
            def COPT_SolveLp(self,handle):
                if slow:time.sleep(.03)
                return 0
        class Api:lib=Lib();prob=ct.c_void_p(42)
        with tempfile.TemporaryDirectory() as d:
            j=Journal(Path(d)/'events');code,events=cooperative_solve(Api(),.005 if slow else 10,j);j.close()
        self.assertEqual(code,0)
        self.assertEqual(len(events),int(slow))
        self.assertEqual([p.value for p in called],[42] if slow else [])

if __name__=='__main__':unittest.main()
