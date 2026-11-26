"""Asynchronous scans must not block samples or turn missing evidence into success."""
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
import lp_billion_storage as s
import lp_billion_idle as idle


def record(start=0, end=0, size=1):
    return dict(started_ns=start, completed_ns=end, value=dict(bytes=size, files=1))


class Child:
    def __init__(self):
        self.returncode = None
        self.stdout, self.stderr = '', ''
        self.killed = False

    def poll(self):
        return self.returncode

    def communicate(self, timeout):
        if self.returncode is None:
            raise AssertionError('sample blocked waiting for scanner')
        return self.stdout, self.stderr

    def kill(self):
        self.killed, self.returncode = True, -9


class StorageContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.trace = Path(self.temp.name) / 'storage.jsonl'
        self.now = 0
        self.child = Child()
        self.spawn = Mock(return_value=self.child)
        self.monitor = s.DiskMonitor(record(), self.trace, clock=lambda: self.now,
                                     command=['owned-fixture'], spawn=self.spawn)
        self.addCleanup(self.monitor.close)

    def start(self):
        self.now = 5*s.NS
        self.monitor.tick()
        self.spawn.assert_called_once()

    def test_slow_scan_does_not_wait_or_launch_duplicate_scanners(self):
        self.start()
        for seconds in range(6, 64):
            self.now = seconds*s.NS
            self.monitor.tick()
        self.spawn.assert_called_once()
        self.child.returncode = 0
        self.child.stdout = json.dumps(record(6*s.NS, 63*s.NS, 19))
        self.monitor.tick()
        self.assertEqual(self.monitor.last['value']['bytes'], 19)
        self.monitor.close()
        with patch.object(s, 'observation', return_value=record()) as final:
            s.final_check(self.trace)
            final.assert_called_once()

    def test_scan_timeout_fails_and_owned_child_is_reaped(self):
        self.start()
        self.now = 65*s.NS
        with self.assertRaisesRegex(ValueError, 'scan timeout'):
            self.monitor.tick()
        self.monitor.close()
        self.assertTrue(self.child.killed)
        with patch.object(s, 'observation') as final:
            with self.assertRaisesRegex(ValueError, 'monitor failed'):
                s.final_check(self.trace)
            final.assert_not_called()

    def test_stale_initial_count_refuses_before_spawn(self):
        self.now = 90*s.NS
        with self.assertRaisesRegex(ValueError, 'observation stale'):
            self.monitor.tick()
        self.spawn.assert_not_called()

    def test_bad_scanner_results_never_refresh_freshness(self):
        for status, stdout, stderr in [
            (2, '', ''), (0, '{}', ''), (0, 'not-json', ''),
            (0, json.dumps(record(5*s.NS, 6*s.NS, s.DISK_LIMIT+1)), ''),
            (0, json.dumps(record(5*s.NS, 8*s.NS)), ''),
            (0, json.dumps(record(5*s.NS, 6*s.NS)), 'warning'),
        ]:
            with self.subTest(status=status, stdout=stdout):
                child = Child()
                monitor = s.DiskMonitor(record(), self.trace, clock=lambda: self.now,
                                        command=['fixture'], spawn=lambda *a, **k: child)
                self.now = 5*s.NS
                monitor.tick()
                child.returncode, child.stdout, child.stderr = status, stdout, stderr
                self.now = 7*s.NS
                with self.assertRaises((ValueError, json.JSONDecodeError)):
                    monitor.tick()
                self.assertEqual(monitor.last, record())
                monitor.close()

    def test_cleanup_stops_scanner_and_never_restarts(self):
        self.start()
        self.monitor.close()
        self.assertTrue(self.child.killed)
        self.now = 1000*s.NS
        self.monitor.tick()
        self.spawn.assert_called_once()

    def test_completed_failure_at_cleanup_is_not_lost(self):
        self.start()
        self.child.returncode = 2
        self.monitor.close()
        with self.assertRaisesRegex(ValueError, 'monitor failed'):
            s.final_check(self.trace)

    def test_final_inventory_is_mandatory_and_can_refuse_a_successful_process(self):
        with self.assertRaises(FileNotFoundError):
            s.final_check(self.trace)
        self.trace.write_text(json.dumps(dict(event='closed', error=None))+'\n')
        with patch.object(s, 'observation', side_effect=subprocess.TimeoutExpired('owned', 60)):
            with self.assertRaises(subprocess.TimeoutExpired):
                s.final_check(self.trace)
        with patch.object(s, 'observation', return_value=record(size=s.DISK_LIMIT+1)):
            with self.assertRaisesRegex(ValueError, 'disk ceiling'):
                s.final_check(self.trace)

    def test_final_storage_failure_keeps_full_charge_and_actual_cleanup(self):
        from lp_billion_budget import settlement
        report = dict(status='passed', charged_cpu_ns=4*s.NS,
                      guardian_cleanup=dict(empty=True), result=dict(cleanup=dict(empty=True)))
        passed = settlement('admission', True, 120, 2*s.NS, 0, report, {})
        failed = settlement('admission', True, 120, 2*s.NS, 0, report, {}, 'final scan timeout')
        self.assertEqual(passed['status'], 'passed')
        self.assertEqual(failed['status'], 'refused')
        self.assertEqual((failed['cpu_ns'], failed['gpu_ns']), (480*s.NS, 120*s.NS))
        self.assertTrue(failed['cleanup_empty'])
        self.assertFalse(failed['overrun'])

    def test_legacy_synchronous_policy_is_unchanged(self):
        supervisor = SimpleNamespace(snapshot=lambda *a, **k: {'processes': []})
        with patch.object(idle, 'disk_bytes', return_value=1) as scan:
            idle.install(supervisor, dict(output=str(self.trace), billion_gpu=False))
            supervisor.snapshot()
            scan.assert_called_once()

    def test_cleanup_still_runs_when_storage_close_fails(self):
        cleanup = Mock(return_value=dict(empty=True))
        supervisor = SimpleNamespace(snapshot=lambda *a, **k: {'processes': []},
                                     terminate_descendants=cleanup)
        with patch.object(s.DiskMonitor, 'close', side_effect=OSError('trace unavailable')):
            idle.install(supervisor, dict(output=str(self.trace), billion_gpu=False,
                                          storage_policy=s.POLICY, storage_initial=record()))
            with self.assertRaises(OSError):
                supervisor.terminate_descendants('owned-root')
            cleanup.assert_called_once_with('owned-root')

    def test_real_slow_child_allows_repeated_samples(self):
        now = time.monotonic_ns()
        code = ('import json,time; start=time.monotonic_ns(); time.sleep(1.2); '
                'print(json.dumps(dict(started_ns=start, completed_ns=time.monotonic_ns(), '
                'value=dict(bytes=1,files=1))))')
        monitor = s.DiskMonitor(record(now-5*s.NS, now-5*s.NS), self.trace,
                                command=[sys.executable, '-B', '-c', code])
        self.addCleanup(monitor.close)
        samples = 0
        pending_samples = 0
        deadline = time.monotonic()+5
        while time.monotonic() < deadline:
            before = time.monotonic()
            monitor.tick()
            self.assertLess(time.monotonic()-before, .5)
            samples += 1
            if monitor.process is not None:
                pending_samples += 1
            elif samples > 1:
                break
            time.sleep(.01)
        self.assertGreater(pending_samples, 5)
        self.assertIsNone(monitor.process)


if __name__ == '__main__':
    unittest.main()
