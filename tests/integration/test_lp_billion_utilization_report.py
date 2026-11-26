"""Source-only regression tests for offline attribution and rollback exclusions."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from lp_billion_timing import PHASES
from lp_billion_utilization_report import inspect_row, summarize


def response():
    phases = dict.fromkeys(PHASES, 0)
    phases.update(device_advance=100, strict_certificate=300, checkpoint=20)
    entries = dict.fromkeys(PHASES, 0)
    entries['strict_certificate'] = 2
    endpoint = {'primal': {'sha256': 'a'}, 'dual': {'sha256': 'b'}}
    certificate = {'accepted': False, 'tolerance': 1e-9, 'bound': 0.0}
    return dict(status='limit', logical=100, elapsed_ns=420,
        endpoint=endpoint, certificate=certificate,
        assessments=[dict(endpoint=copy.deepcopy(endpoint),
                          certificate=copy.deepcopy(certificate))],
        solver_profile=dict(schema_version=1, clock='monotonic_host_wall',
            timer_overhead_included=True, kernel_active_time=False,
            exclusive_ns=phases, phase_entries=entries, total_ns=420))


class UtilizationReport(unittest.TestCase):
    def test_duplicate_does_not_invent_duration_or_utilization(self):
        result = summarize(response())
        self.assertTrue(result['duplicate_final_assessment_candidate'])
        self.assertIsNone(result['duplicate_duration_ns'])
        self.assertIsNone(result['utilization_percent'])
        self.assertIsNone(result['kernel_active_time_ns'])

    def test_rollback_changes_endpoint_even_with_same_logical_counter(self):
        data = response()
        data['status'] = 'deadline'
        data['endpoint']['primal']['sha256'] = 'rolled-back'
        self.assertFalse(summarize(data)['duplicate_final_assessment_candidate'])

    def test_changed_dual_or_certificate_prevents_candidate(self):
        data = response()
        data['endpoint']['dual']['sha256'] = 'other-dual'
        self.assertFalse(summarize(data)['duplicate_final_assessment_candidate'])
        data = response()
        data['certificate']['bound'] = 1.0
        self.assertFalse(summarize(data)['duplicate_final_assessment_candidate'])

    def test_certified_reuse_is_already_implemented(self):
        data = response()
        data['status'] = 'certified'
        data['solver_profile']['phase_entries']['strict_certificate'] = 1
        self.assertFalse(summarize(data)['duplicate_final_assessment_candidate'])

    def test_no_last_assessment_or_no_extra_call(self):
        data = response()
        data['assessments'] = []
        self.assertFalse(summarize(data)['duplicate_final_assessment_candidate'])
        data = response()
        data['solver_profile']['phase_entries']['strict_certificate'] = 1
        self.assertFalse(summarize(data)['duplicate_final_assessment_candidate'])

    def test_corrupt_phase_coverage_and_kernel_claim_refuse(self):
        for key, value in [('total_ns', 419), ('kernel_active_time', True)]:
            data = response()
            data['solver_profile'][key] = value
            with self.assertRaises(ValueError):
                summarize(data)

    def test_missing_and_vendor_outcomes_remain_unattributed(self):
        def forbidden(_):
            self.fail('missing response must not be opened')
        row = dict(family='wide', lane='fp4x2', status='missing_response')
        self.assertEqual(inspect_row(row, 'test', forbidden)['phase_attribution'],
                         'unavailable')
        row.update(lane='copt', response={'path': 'vendor'})
        self.assertEqual(inspect_row(row, 'test', lambda _: {})['phase_attribution'],
                         'opaque_vendor_solve')


if __name__ == '__main__':
    unittest.main()
