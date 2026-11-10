"""Source-only counterexamples for retained Tensor latency attribution."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from diagnose_lp_tensor_latency import control_path, exclusive_subtree


class TensorLatencyDiagnosis(unittest.TestCase):
    def test_overlapping_envelopes_are_not_added_to_exclusive_scopes(self):
        phases = {"solve_loop": 100, "original_model_assessments": 40,
                  "cost/solve": 10, "cost/solve/audit": 20,
                  "cost/solve/audit/arithmetic": 30, "cost/solve/auditor": 99}
        self.assertEqual(exclusive_subtree(phases, "cost/solve/audit"), 50)
        with self.assertRaises(ValueError):
            exclusive_subtree(phases, "solve_loop")

    def test_research_tuned_profile_cannot_be_treated_as_unchanged_timing(self):
        wrapper = {"outcome": {}, "request": {"layout": "original_tuned"}}
        self.assertEqual(control_path("profile", wrapper), "research_wrapper_original_tuned")
        with self.assertRaises(ValueError):
            control_path("timing", wrapper)
        actual = {"format": "lp-compact-v1", "endpoint": {"record": {"backend": "cuda-lp-tuned"}}}
        self.assertEqual(control_path("timing", actual), "unchanged_cuda_lp_tuned")

    def test_other_backends_cannot_supply_tuned_control_evidence(self):
        with self.assertRaises(ValueError):
            control_path("timing", {"format": "lp-compact-v1", "endpoint": {"record": {"backend": "host-lp"}}})
