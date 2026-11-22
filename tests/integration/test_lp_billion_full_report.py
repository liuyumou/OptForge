import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from lp_billion_full_report import validate_audit_binding,vendor_ledger,vendor_timing_eligible
class FullReportContracts(unittest.TestCase):
    def audit(self):
        source={'sha256':'response'};model={'sha256':'original'};checker={'sha256':'checker'}
        response=dict(status='deadline',certified=False)
        audit=dict(response=source,model=model,checker=checker,status='passed',certified=False,strict_endpoint_accepted=True,
                   results=[dict(model_sha256='original',tolerance=1e-9,accepted=True)])
        return source,model,checker,response,audit,True
    def test_late_valid_endpoint_keeps_original_deadline(self):validate_audit_binding(*self.audit())
    def test_wrong_response_model_or_checker_binding_is_rejected(self):
        for key in ['response','model','checker']:
            args=list(copy.deepcopy(self.audit()));args[4][key]={'sha256':'another'}
            with self.assertRaises(ValueError):validate_audit_binding(*args)
    def test_looser_tolerance_or_wrong_model_in_any_proof_is_rejected(self):
        for bad in [dict(model_sha256='another',tolerance=1e-9,accepted=False),dict(model_sha256='original',tolerance=1e-8,accepted=False)]:
            args=list(copy.deepcopy(self.audit()));args[4]['results'].append(bad)
            with self.assertRaises(ValueError):validate_audit_binding(*args)
    def test_vendor_outer_cost_is_derived_without_cached_ledger(self):
        r=dict(profile=dict(total_ns=70,exclusive_ns=dict(input=20,solve=50)))
        m=dict(process_ns=100,response_transport_ns=5,fresh_process_ns=105)
        got=vendor_ledger(r,m,40);self.assertEqual(got['total_ns'],145)
        self.assertEqual(got['exclusive_ns']['process_imports_serialization_cleanup'],30)
        self.assertEqual(sum(got['exclusive_ns'].values()),145)
    def test_inconsistent_cached_vendor_ledger_is_rejected(self):
        r=dict(profile=dict(total_ns=70,exclusive_ns=dict(input=20,solve=50)))
        m=dict(process_ns=100,response_transport_ns=5,fresh_process_ns=105,process_cost_ledger=dict(exclusive_ns={}))
        with self.assertRaises(ValueError):vendor_ledger(r,m,40)
    def test_failed_or_unattempted_vendor_call_is_not_a_performance_result(self):
        for called,code in [(False,0),(True,1),(True,9)]:
            self.assertFalse(vendor_timing_eligible(dict(solve_called=called,solve_returncode=code)))
        self.assertTrue(vendor_timing_eligible(dict(solve_called=True,solve_returncode=0)))
if __name__=='__main__':unittest.main()
