"""Slow durable I/O must not fabricate samples or extend admitted work time."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import lp_confirmation2_supervisor as cpu


class ObservedFinalization(unittest.TestCase):
    def run_case(self, mode):
        with tempfile.TemporaryDirectory(prefix='lp-finalization-', dir=os.environ.get('LP_FINALIZATION_TEST_DIR')) as directory:
            out = Path(directory)
            journal = dict(identity='test', prior_cpu_ns=0, ceiling_cpu_ns=48_000_000_000, active=None,
                           failed=False, runs=[], stages={'implementation': dict(cap_cpu_ns=48_000_000_000, charged_cpu_ns=0)})
            (out / 'journal.json').write_text(json.dumps(journal))
            command = 'import time; time.sleep(.05)'
            if mode == 'stalled_sampler':
                command = 'import os,signal,time;os.kill(int(os.environ["LP_CPU_COORDINATOR_PID"]),signal.SIGSTOP);time.sleep(3)'
            request = dict(stage='implementation', reserve_cpu_seconds=48, output=str(out / 'result.json'),
                           log=str(out / 'log'), journal=str(out / 'journal.json'), lock=str(out / 'lock'),
                           slots=4, declared_memory_bytes=64 << 20, rss_stop_bytes=6 << 30, address_space_bytes=0,
                           sources=[], bootstrap=False, show_log=False, max_gap_ns=1_000_000_000,
                           observed_finalization=True, receipt_finalization_seconds=3, publication_wall_seconds=2,
                           command=[sys.executable, '-c', command])
            (out / 'request.json').write_text(json.dumps(request))
            runner = out / 'runner.py'
            runner.write_text('''import sys,os,time,json,inspect
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import lp_confirmation2_supervisor as cpu
request=json.loads(Path(sys.argv[2]).read_text());mode=sys.argv[3];owner=os.getpid()
write=cpu.atomic_json;scan=cpu.snapshot
def delayed_write(path,value):
 if str(path).endswith('.coordinator-result.json'):
  if mode in ['slow_publication','slow_scan']:time.sleep(1.2)
  if mode=='publication_timeout':time.sleep(3)
 if str(path)==request['output'] and os.getpid()==owner and mode=='slow_receipt':time.sleep(1.2)
 return write(path,value)
def delayed_scan(*a,**k):
 if mode=='slow_scan' and inspect.currentframe().f_back.f_code.co_name=='sample':time.sleep(1.1)
 return scan(*a,**k)
cpu.atomic_json=delayed_write;cpu.snapshot=delayed_scan
cpu.run(request)
''')
            result = subprocess.run([sys.executable, str(runner), str(ROOT / 'tools'), str(out / 'request.json'), mode],
                                    text=True, capture_output=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads((out / 'result.json').read_text())

    def test_slow_publication_keeps_real_resource_sampling(self):
        result = self.run_case('slow_publication')
        self.assertEqual(result['status'], 'passed', result['result'])
        samples = result['result']['finalization_observation']
        self.assertGreater(samples['samples'], 10)
        self.assertLessEqual(samples['max_sample_gap_ns'], 1_000_000_000)
        self.assertLessEqual(samples['max_sample_work_ns'], 1_000_000_000)
        self.assertTrue(result['guardian_cleanup']['empty'])

    def test_receipt_reserve_covers_normal_slow_fsync(self):
        result = self.run_case('slow_receipt')
        self.assertEqual(result['status'], 'passed', result['result'])
        self.assertEqual(result['finalization_wall_reserve_ns'], 3_000_000_000)
        self.assertEqual(result['charged_cpu_ns'], 4 * (result['active_elapsed_ns'] + 3_000_000_000))
        self.assertLessEqual(result['charged_cpu_ns'], 48_000_000_000)

    def test_post_command_overlong_resource_sample_still_fails(self):
        self.assertEqual(self.run_case('slow_scan')['status'], 'refused')

    def test_stopped_coordinator_still_fails(self):
        result = self.run_case('stalled_sampler')
        self.assertEqual(result['status'], 'refused')
        self.assertEqual(result['result']['reason'], 'lost_coordinator_heartbeat')

    def test_publication_deadline_remains_bounded(self):
        self.assertEqual(self.run_case('publication_timeout')['status'], 'refused')

    def test_invalid_receipt_and_publication_limits_fail_before_launch(self):
        for bad in [True, 0, 11, 1.5]:
            with self.assertRaises(cpu.AdmissionError): cpu.run(dict(max_gap_ns=1_000_000_000, receipt_finalization_seconds=bad))
        with self.assertRaises(cpu.AdmissionError):
            cpu.run(dict(max_gap_ns=1_000_000_000, observed_finalization=True, publication_wall_seconds=31))


if __name__ == '__main__': unittest.main()
