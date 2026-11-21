"""A valid final witness after a deadline must not regrade the solver status."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from lp_billion_full_audit_v2 import certification_status
class FullAuditDeadlineContracts(unittest.TestCase):
    def test_late_valid_endpoint_retains_deadline(self):
        self.assertFalse(certification_status(dict(status='deadline',certified=False),True,True))
    def test_deadline_cannot_claim_in_time_certificate(self):
        with self.assertRaisesRegex(ValueError,'classification'):certification_status(dict(status='deadline',certified=True),True,True)
    def test_false_certificate_is_never_accepted(self):
        with self.assertRaisesRegex(ValueError,'classification'):certification_status(dict(status='certified',certified=True),True,False)
    def test_valid_in_time_and_external_vendor_certificates_remain_accepted(self):
        self.assertTrue(certification_status(dict(status='certified',certified=True),True,True));self.assertTrue(certification_status({},False,True))
if __name__=='__main__':unittest.main()
