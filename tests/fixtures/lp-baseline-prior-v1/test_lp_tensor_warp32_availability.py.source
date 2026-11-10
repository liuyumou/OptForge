"""Reject source drift while retaining the approved availability-test bridge."""
import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from lp_protocol import ROOT, read_json
from lp_tensor_warp32_availability_bridge import (
    SOURCE, BRIDGE, MARKER, verify_test_only_change, verify_source_mapping, verify_cpu_sources,
)


class AvailabilitySourceBridgeTests(unittest.TestCase):
    def test_actual_admission_and_prior_driver_production_bytes_are_preserved(self):
        cpu = read_json(ROOT / 'docs/benchmarks/data/tensor-warp32/cpu-admission-v1.json')
        verify_cpu_sources(cpu)
        row = next(r for r in read_json(BRIDGE)['files'] if r['path'] == SOURCE)
        verify_test_only_change((ROOT / row['frozen_path']).read_bytes(), (ROOT / SOURCE).read_bytes())

    def test_production_mutation_and_missing_or_duplicate_boundaries_refuse(self):
        original = b'production' + MARKER + b'old tests}'
        verify_test_only_change(original, b'production' + MARKER + b'new tests}')
        for changed in [b'changed' + MARKER + b'new tests}', b'production', original + MARKER]:
            with self.assertRaises(ValueError):
                verify_test_only_change(original, changed)

    def test_changed_admission_hash_or_roster_refuses(self):
        cpu = read_json(ROOT / 'docs/benchmarks/data/tensor-warp32/cpu-admission-v1.json')
        bad = copy.deepcopy(cpu)
        bad['numerical_sources'][SOURCE] = '0' * 64
        with self.assertRaises(ValueError):
            verify_cpu_sources(bad)
        bad = copy.deepcopy(cpu)
        bad['numerical_sources'].pop(SOURCE)
        with self.assertRaises(ValueError):
            verify_cpu_sources(bad)

    def test_non_test_source_drift_refuses(self):
        with patch('lp_tensor_warp32_availability_bridge.file_hash', return_value='changed'):
            with self.assertRaises(ValueError):
                verify_source_mapping({'cuda/lp_pdhg_tuned/lp_pdhg_tuned.cu': 'original'})


if __name__ == '__main__':
    unittest.main()
