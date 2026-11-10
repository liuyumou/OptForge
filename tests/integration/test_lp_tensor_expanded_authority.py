"""New ADR-0046 adapter checks; no retained checks or device work are run."""
import copy
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import lp_tensor_expanded_authority as a
from lp_gpup8_test_support import authority_tree


class ExpandedAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.root = self.enterContext(authority_tree())
        self.auth = a.authority()

    def event(self, i, kind, trial, ns):
        return dict(sequence=i, kind=kind, trial_id=trial, resource="gpu", phase="repeatability",
                    reservation_id=trial, reserved_ns=ns, charged_ns=0 if kind == "reserve" else ns)

    def test_historical_charge_included(self):
        auth = copy.deepcopy(self.auth)
        auth["prior_gpup8_gpu_ns"] = 2999 * a.NS
        with self.assertRaisesRegex(ValueError, "GPUP-8 exhausted"):
            a.gpu_admission(auth, [], "acceptance", "gpup-tensor-expanded-v1-acceptance-a", 2*a.NS)

    def test_phase_exhaustion_before_launch(self):
        with self.assertRaisesRegex(ValueError, "cohort phase exhausted"):
            a.gpu_admission(self.auth, [], "acceptance", "gpup-tensor-expanded-v1-acceptance-a", 451*a.NS)

    def test_pending_reservation_included(self):
        key="gpup-tensor-expanded-v1-acceptance-a"
        with self.assertRaisesRegex(ValueError, "cohort phase exhausted"):
            a.gpu_admission(self.auth,[self.event(0,"reserve",key,450*a.NS)],"acceptance",key+"b",a.NS)

    def test_duplicate_attempt(self):
        key="gpup-tensor-expanded-v1-acceptance-a"
        es=[self.event(0,"reserve",key,a.NS),self.event(1,"settle",key,a.NS)]
        with self.assertRaisesRegex(ValueError,"duplicate attempt"):
            a.gpu_admission(self.auth,es,"acceptance",key,a.NS)

    def test_existing_request_refuses(self):
        with self.assertRaisesRegex(ValueError,"duplicate attempt"):
            a.gpu_admission(self.auth,[],"acceptance","gpup-tensor-expanded-v1-acceptance-a",a.NS,True)

    def test_source_cache_mismatch(self):
        with self.assertRaisesRegex(ValueError,"source/cache mismatch"):
            a.checked(dict(path="tools/lp_expansion_oracle.py",sha256="0"*64))

    def test_stage_isolation(self):
        j=a.read(a.JOURNAL)
        j.update(active=None, stage_attempts={}, failed=False, scientific_closed=False)
        with self.assertRaisesRegex(ValueError,"stage exhausted"):
            a.stage_admission(j,"prototype",2001*a.NS)

    def test_failed_stage_closes_execution(self):
        j=a.read(a.JOURNAL);j["failed"]=True
        with self.assertRaisesRegex(ValueError,"closed"):
            a.stage_admission(j,"timings",6400*a.NS)

    def test_report_equivalence(self):
        r=dict(profiles_complete=True,working_families=True,forecast_pass=False,resource_pass=False,
               timings_certified=0,coverage_pass=False,adjusted_gain=False)
        self.assertEqual(a.report_view(r),dict(complete=False,criteria=r))
        r.update(forecast_pass=True,resource_pass=True,timings_certified=60,coverage_pass=True,adjusted_gain=True)
        self.assertTrue(a.report_view(r)["complete"])
        r["timings_certified"]=59
        self.assertFalse(a.report_view(r)["complete"])

    def test_exact_prefix_and_synthetic_preservation_guards(self):
        self.assertEqual(a.preserve(),17412)
        (self.root / "synthetic-prior-source.txt").write_text("changed")
        with self.assertRaisesRegex(ValueError, "source/cache mismatch"):
            a.preserve()

    def test_actual_historical_aggregate(self):
        phases, _, _, pending = a.aggregate(a.ledger_events())
        self.assertFalse(pending)
        self.assertEqual(sum(phases.values()),self.auth["prior_campaign_gpu_ns"])

    def test_conversion_boundary_counters(self):
        c=dict(penultimate_vectors=4,endpoint_vectors=4,decoded_coordinates=40)
        a.validate_conversion_counts(c,2,(3,7))
        c["decoded_coordinates"]=True
        with self.assertRaisesRegex(ValueError,"malformed"):
            a.validate_conversion_counts(c,2,(3,7))


if __name__ == "__main__":
    unittest.main()
