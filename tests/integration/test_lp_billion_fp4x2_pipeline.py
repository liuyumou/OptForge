"""Source-only checks for CPU-only jobs and idempotent future GPU configuration."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
import lp_billion_fp4x2_pipeline as subject
import lp_billion_fp4x2_evaluate as evaluator


class PipelineHarness(unittest.TestCase):
    def test_repeated_configuration_does_not_duplicate_gpu_variants(self):
        original=(evaluator.QUALITY,evaluator.IMAGE,evaluator.FLAGS)
        try:
            first=subject.configured_evaluator().FLAGS
            second=subject.configured_evaluator().FLAGS
            self.assertEqual(first,second)
            self.assertEqual(len(first),5)
            self.assertEqual(len(set(first)),5)
            self.assertIn('host_state_reuse',first)
        finally:
            evaluator.QUALITY,evaluator.IMAGE,evaluator.FLAGS=original

    def test_cpu_job_refuses_a_gpu_reservation_before_output(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(subject,'BASE',Path(tmp)), patch.object(subject,'load',return_value=dict(gpu=True,command=['job'])):
            with self.assertRaisesRegex(ValueError,'CPU-only'):
                subject.directory('job')
            self.assertFalse((Path(tmp)/'job').exists())

    def test_job_identity_cannot_borrow_another_reservation(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(subject,'BASE',Path(tmp)), patch.object(subject,'load',return_value=dict(gpu=False,command=['someone-else'])):
            with self.assertRaisesRegex(ValueError,'matching'):
                subject.directory('job')
            self.assertFalse((Path(tmp)/'job').exists())


if __name__=='__main__':unittest.main()
