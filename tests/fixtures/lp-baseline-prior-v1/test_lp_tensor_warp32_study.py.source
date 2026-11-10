"""CPU-only admission, immutability and receipt guards for the isolated recovery."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from lp_protocol import ROOT, write_json
from lp_tensor_warp32_common import protocol, BASE, save_verification, read_verification, JointLedger
from benchmark_lp_tensor_warp32 import jobs, effective
from lp_tensor_warp32_accept import acceptance_jobs
from lp_tensor_warp32_screen import RULE, RESOURCE_RULE, integer
from lp_tensor_warp32_build import preserve
from report_lp_tensor_warp32 import gain, worker_bounds
import lp_tensor_cost_common as retained


class Warp32StudyTests(unittest.TestCase):
    def test_complete_roster_and_tighter_aggregate_caps(self):
        value = protocol()
        rows = list(jobs(value))
        self.assertEqual(len(rows), 76)
        self.assertEqual(len({r['id'] for r in rows}), 76)
        self.assertEqual(sum(effective(value, r)[2] + 6 for r in rows if r['kind'] == 'timing'), 990)
        self.assertEqual(sum(effective(value, r)[2] + 6 for r in rows if r['kind'] == 'profile'), 320)
        self.assertEqual(sum(seconds + 6 for _, seconds in acceptance_jobs()), 290)
        self.assertEqual(sum(r['seconds'] for r in value['categories'].values()), 790)
        self.assertEqual(value['categories']['timing']['seconds'], 300)
        self.assertEqual(value['categories']['profile']['seconds'], 200)

    def test_numerical_and_comparison_contract_is_exactly_inherited(self):
        old, new = retained.protocol(), protocol()
        for key in ['configurations', 'solve', 'lp_settings', 'timing_instances', 'profile_instances',
                    'timing_repetitions', 'order_seed', 'analysis', 'profile_work', 'acceptance_work']:
            self.assertEqual(old[key], new[key], key)
        self.assertEqual(RULE['threshold'], .9)
        self.assertEqual(RESOURCE_RULE['multiplier'], 1.25)
        self.assertEqual(gain([(2., 1.)] * 5)['multiplicity'], 6)
        self.assertIsNone(gain([(2., 1.)] * 4))
        self.assertIsNone(gain([(2., 1.)] * 5, False))

    def test_only_reference_product_body_changes(self):
        preserve()
        for path in (ROOT / 'cuda/lp_pdhg_tensor_warp32').iterdir():
            self.assertNotIn('atomicAdd(', path.read_text())

    def test_joint_cpu_guard_precedes_any_ledger_mutation(self):
        with tempfile.TemporaryDirectory(dir=BASE) as directory:
            value = protocol()
            ledger = JointLedger(Path(directory), value['budget_authority']['sha256'], value)
            with patch('lp_tensor_warp32_common.worker_remaining_ns', return_value=0):
                with self.assertRaises(ValueError):
                    ledger.reserve(value['id'] + '-timing-fixture', 22, phase='screening')
            self.assertFalse(ledger.path.exists())

    def test_receipt_rejects_changed_endpoint_request_and_executable(self):
        with tempfile.TemporaryDirectory(dir=BASE) as directory:
            d = Path(directory)
            paths = [d / name for name in ['model', 'request', 'endpoint', 'binary']]
            for path in paths:
                path.write_text('original')
            proof = d / 'verification.json'
            save_verification(proof, *paths, 'source', {'gap_closed': False}, 1)
            self.assertEqual(read_verification(proof, *paths, 'source')['assessment'], {'gap_closed': False})
            for path in paths:
                path.write_text('changed')
                with self.assertRaises(ValueError):
                    read_verification(proof, *paths, 'source')
                path.write_text('original')
            with self.assertRaises(ValueError):
                read_verification(proof, *paths, 'another-source')
            data = json.loads(proof.read_text())
            data['elapsed_ns'] = True
            write_json(proof, data)
            with self.assertRaises(ValueError):
                read_verification(proof, *paths, 'source')

    def test_physical_counter_types_and_bounds_refuse(self):
        for bad in [True, -1, 1.0, '1', None]:
            with self.assertRaises(ValueError):
                integer(bad)
        value = dict(elapsed_ns=1, leased_ns=2, peak_rss_bytes=1, queue_ns=0, activity=dict(device='device'))
        worker_bounds(value, 2, 'device')
        for field in ['elapsed_ns', 'leased_ns', 'peak_rss_bytes', 'queue_ns']:
            with self.assertRaises(ValueError):
                worker_bounds(dict(value, **{field: True}), 2, 'device')


if __name__ == '__main__':
    unittest.main()
