"""Bootstrap refusal counterexamples, with no host cgroup mutation or workload."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from lp_tensor_cost_preflight import REQUIRED_CONTROLS, assess, control_snapshot, create_receipt


def controls():
    value = {name: dict(exists=True, writable=True, value='') for name in REQUIRED_CONTROLS}
    for name, text in {'cpu.max': '400000 100000', 'cpuset.cpus.effective': '0-3',
                       'memory.max': str(8 << 30), 'memory.swap.max': '0',
                       'cpu.stat': 'usage_usec 0\nuser_usec 0\nsystem_usec 0',
                       'memory.peak': '0', 'memory.events': 'max 0\noom 0\noom_kill 0'}.items():
        value[name]['value'] = text
    return value


class TensorCostPreflight(unittest.TestCase):
    def test_writable_files_cannot_override_read_only_mount_or_foreign_root(self):
        for read_only, explicit in [(True, True), (False, False)]:
            result = assess(controls(), read_only, explicit)
            self.assertEqual(result['status'], 'cpu_admission_refusal')
            self.assertFalse(result['preparation_admitted'])

    def test_capability_alone_never_admits_a_workload(self):
        result = assess(controls(), False, True)
        self.assertEqual(result['status'], 'capability_ready_not_admitted')
        self.assertFalse(result['preparation_admitted'])
        self.assertFalse(result['device_admitted'])
        self.assertFalse(result['cpu_coordinator_failure_tests_passed'])

    def test_loose_malformed_or_unlimited_limits_refuse(self):
        for name, text in [('cpu.max', '9000000 100000'), ('cpu.max', 'max 100000'),
                           ('cpu.max', '0 100000'), ('cpuset.cpus.effective', '0-95'),
                           ('cpuset.cpus.effective', '3-0'), ('memory.max', str(200 << 30)),
                           ('memory.max', 'max'), ('memory.swap.max', '1')]:
            bad = controls()
            bad[name]['value'] = text
            self.assertEqual(assess(bad, False, True)['status'], 'cpu_admission_refusal')

    def test_missing_aggregate_accounting_or_oom_refuses(self):
        for name, text in [('cpu.stat', ''), ('cpu.stat', 'usage_usec -1'),
                           ('memory.peak', ''), ('memory.events', 'max 0\noom 1\noom_kill 0')]:
            bad = controls()
            bad[name]['value'] = text
            self.assertIn('aggregate_cpu_memory_accounting_not_ready', assess(bad, False, True)['reasons'])
        bad = controls()
        del bad['memory.peak']
        self.assertIn('missing_control:memory.peak', assess(bad, False, True)['reasons'])

    def test_membership_and_kill_permissions_are_required(self):
        for name in ['cgroup.procs', 'cgroup.freeze', 'cgroup.kill']:
            bad = controls()
            bad[name]['writable'] = False
            self.assertIn('control_not_delegated:' + name, assess(bad, False, True)['reasons'])

    def test_snapshot_does_not_read_write_only_kill_control(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in REQUIRED_CONTROLS:
                (root / name).write_text('0')
            read = Path.read_text
            def checked_read(path, *args, **kwargs):
                if path.name == 'cgroup.kill':
                    raise AssertionError('write-only control read')
                return read(path, *args, **kwargs)
            with patch.object(Path, 'read_text', checked_read):
                snapshot = control_snapshot(root)
            self.assertTrue(snapshot['cgroup.kill']['exists'])
            self.assertNotIn('value', snapshot['cgroup.kill'])

    def test_prior_refusal_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'refusal.json'
            result = assess(controls(), True, False)
            create_receipt(path, result)
            original = path.read_bytes()
            with self.assertRaises(FileExistsError):
                create_receipt(path, assess(controls(), False, True))
            self.assertEqual(path.read_bytes(), original)
