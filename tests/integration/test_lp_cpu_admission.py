"""Portability regressions; real supervisor acceptance remains separately gated."""
import importlib.util
import os
from pathlib import Path
import json
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('lp_cpu_admission', ROOT/'tools/lp_cpu_admission.py')
cpu = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cpu)


class CpuAdmissionPortability(unittest.TestCase):
    def test_large_result_uses_bound_durable_file_and_small_control_packet(self):
        with tempfile.TemporaryDirectory() as directory:
            request = dict(output=str(Path(directory)/'phase.json'))
            result = dict(reason='completed', observed_processes=[dict(pid=i, detail='x'*80) for i in range(1600)])
            self.assertGreater(len(json.dumps(result)),65536)
            left,right = socket.socketpair(socket.AF_UNIX,socket.SOCK_SEQPACKET)
            try:
                cpu.publish_result(left,request,result)
                message=cpu.receive(right)
                self.assertNotIn('result',message)
                self.assertEqual(cpu.load_result(request,message),result)
            finally:
                left.close();right.close()

    def test_truncated_control_packet_refuses_explicitly(self):
        left,right=socket.socketpair(socket.AF_UNIX,socket.SOCK_SEQPACKET)
        try:
            left.send(b'x'*70000)
            with self.assertRaisesRegex(cpu.AdmissionError,'ipc_control_frame_truncated'):
                cpu.receive(right)
        finally:
            left.close();right.close()

    def test_changed_result_cannot_pass_its_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            request=dict(output=str(Path(directory)/'phase.json'))
            result=dict(reason='completed')
            with patch.object(cpu,'send') as sent:
                cpu.publish_result(None,request,result)
            message=sent.call_args.args[1]
            Path(request['output']+'.coordinator-result.json').write_text('{}')
            with self.assertRaisesRegex(cpu.AdmissionError,'coordinator_result_binding_invalid'):
                cpu.load_result(request,message)

    def test_result_size_is_strict_and_bounded(self):
        for size in [True,0,-1,(8<<20)+1]:
            with self.assertRaisesRegex(cpu.AdmissionError,'coordinator_result_size_invalid'):
                cpu.load_result(dict(output='unused'),dict(result_bytes=size))

    def test_python_wrapper_when_available(self):
        with patch.object(os, 'pidfd_open', create=True, return_value=91) as opened:
            self.assertEqual(cpu.pidfd_open(123), 91)
            opened.assert_called_once_with(123)

    def test_missing_python_wrapper_uses_existing_container_syscall(self):
        with patch.object(os, 'pidfd_open', None, create=True), \
             patch.object(cpu.platform, 'machine', return_value='x86_64'), \
             patch.object(cpu.ctypes, 'CDLL') as library, \
             patch.object(os, 'set_inheritable') as cloexec:
            library.return_value.syscall.return_value = 92
            self.assertEqual(cpu.pidfd_open(123), 92)
            cloexec.assert_called_once_with(92, False)

    def test_unknown_architecture_refuses_instead_of_guessing(self):
        with patch.object(os, 'pidfd_open', None, create=True), \
             patch.object(cpu.platform, 'machine', return_value='unsupported'), \
             patch.object(cpu.ctypes, 'CDLL') as library:
            with self.assertRaises(cpu.AdmissionError):
                cpu.pidfd_open(123)
            library.assert_not_called()

    def test_kernel_policy_failure_is_not_bypassed(self):
        with patch.object(os, 'pidfd_open', None, create=True), \
             patch.object(cpu.platform, 'machine', return_value='x86_64'), \
             patch.object(cpu.ctypes, 'CDLL') as library, \
             patch.object(cpu.ctypes, 'get_errno', return_value=1):
            library.return_value.syscall.return_value = -1
            with self.assertRaises(PermissionError):
                cpu.pidfd_open(123)


class CpuAdmissionLive(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='gpup8-supervisor-test-')
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def command(self, name, code, extra=()):
        return [sys.executable, str(ROOT/'tools/lp_cpu_admission.py'),
                '--stage', 'implementation', '--reserve-cpu-seconds', '24',
                '--output', str(self.directory/(name+'.json')),
                '--journal', str(self.directory/'journal.json'),
                '--lock', str(self.directory/'lock'),
                '--declared-memory-bytes', str(64 << 20), *extra,
                '--', sys.executable, '-c', code]

    def invoke(self, name, code, extra=(), success=True):
        result = subprocess.run(self.command(name,code,extra),capture_output=True,text=True,timeout=8)
        self.assertEqual(result.returncode,0 if success else 2,(result.stdout,result.stderr))
        path=self.directory/(name+'.json')
        return json.loads(path.read_text()) if path.exists() else json.loads(result.stdout)

    def test_ready_handshake_and_resource_receipt(self):
        r=self.invoke('happy','import time; time.sleep(.04)')
        self.assertEqual(r['identity'],'cooperative_process_supervision_v1')
        self.assertTrue(r['result']['entry']['start_ticks']>0)
        self.assertTrue(r['result']['samples']>0)
        self.assertFalse(r['hard_memory_enclosure'])
        self.assertEqual(r['charged_cpu_ns'],4*(r['active_elapsed_ns']+1_000_000_000))

    def test_build_admission_contention_has_no_second_launch(self):
        first=subprocess.Popen(self.command('build','import time; time.sleep(.4)'),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            until=time.monotonic()+2
            while not (self.directory/'journal.json').exists() and time.monotonic()<until:time.sleep(.005)
            r=self.invoke('admission','raise SystemExit(99)',success=False)
            self.assertEqual(r['status'],'refused_before_launch')
            self.assertFalse((self.directory/'admission.json.log').exists())
            out,err=first.communicate(timeout=3)
            self.assertEqual(first.returncode,0,(out,err))
        finally:
            if first.poll() is None:first.kill();first.wait()

    def test_nested_sessions_from_thread_are_reaped(self):
        marker=self.directory/'nested.pid'
        code=('import os,time,threading,subprocess,sys\nfrom pathlib import Path\n'
              'def launch():\n'
              f' subprocess.Popen([sys.executable,"-c","import os,time; from pathlib import Path; Path({str(marker)!r}).write_text(str(os.getpid())); time.sleep(60)"],start_new_session=True)\n'
              't=threading.Thread(target=launch);t.start();t.join()\n'
              f'while not Path({str(marker)!r}).exists():time.sleep(.001)\n')
        r=self.invoke('nested',code)
        self.assertTrue(r['result']['cleanup']['empty'])
        self.assertFalse(Path('/proc/'+marker.read_text()).exists())

    def test_coordinator_sigkill_is_observed_by_guardian(self):
        r=self.invoke('coord-kill','import os,signal,time; os.kill(int(os.environ["LP_CPU_COORDINATOR_PID"]),signal.SIGKILL); time.sleep(2)',success=False)
        self.assertIn(r['result']['reason'],('coordinator_lost','lost_coordinator_heartbeat'))
        self.assertTrue(r['guardian_cleanup']['empty'])
        self.assertGreaterEqual(r['charged_cpu_ns'],24_000_000_000)

    def test_guardian_sigkill_is_observed_by_coordinator(self):
        marker=self.directory/'worker.pid'
        code=('import os,signal,time\nfrom pathlib import Path\n'
              f'Path({str(marker)!r}).write_text(str(os.getpid()))\n'
              'os.kill(int(os.environ["LP_CPU_GUARDIAN_PID"]),signal.SIGKILL)\ntime.sleep(3)')
        result=subprocess.run(self.command('guardian-kill',code),capture_output=True,text=True,timeout=8)
        self.assertEqual(result.returncode,-signal.SIGKILL)
        emergency=self.directory/'guardian-kill.json.coordinator-failure.json'
        until=time.monotonic()+2
        while not emergency.exists() and time.monotonic()<until:time.sleep(.005)
        self.assertTrue(emergency.exists())
        record=json.loads(emergency.read_text())
        self.assertEqual(record['reason'],'guardian_lost')
        self.assertTrue(record['cleanup']['empty'])
        self.assertFalse(Path('/proc/'+marker.read_text()).exists())
        r=self.invoke('stale-after-kill','pass',success=False)
        self.assertIn('stale_or_failed_reservation',r['reason'])

    def test_sampling_stall_triggers_independent_watchdog(self):
        r=self.invoke('stalled','import os,signal,time; os.kill(int(os.environ["LP_CPU_COORDINATOR_PID"]),signal.SIGSTOP); time.sleep(2)',success=False)
        self.assertEqual(r['result']['reason'],'lost_coordinator_heartbeat')
        self.assertTrue(r['guardian_cleanup']['empty'])

    def test_small_fixture_memory_threshold_does_not_oom_container(self):
        r=self.invoke('memory','import time; allocation=bytearray(300<<20); time.sleep(2)',
                      ['--rss-stop-bytes',str(256<<20)],success=False)
        self.assertEqual(r['result']['reason'],'sampled_rss_limit')
        self.assertTrue(r['guardian_cleanup']['empty'])

    def test_sigterm_cancellation_reaps_family(self):
        r=self.invoke('term','import os,signal,time; os.kill(int(os.environ["LP_CPU_GUARDIAN_PID"]),signal.SIGTERM); time.sleep(2)',success=False)
        self.assertEqual(r['result']['reason'],'cancelled')
        self.assertTrue(r['guardian_cleanup']['empty'])

    def test_sequential_stages_do_not_reset_spent_budget(self):
        journal=cpu.initial_journal();journal['stages']['implementation']['cap_cpu_ns']=26_000_000_000
        (self.directory/'journal.json').write_text(json.dumps(journal))
        self.invoke('one','pass')
        r=self.invoke('two','raise SystemExit(99)',success=False)
        self.assertEqual(r['reason'],'stage_reservation_exhausted')
        self.assertFalse((self.directory/'two.json.log').exists())

    def test_excess_work_slots_refuse_before_exec(self):
        r=self.invoke('slots','raise SystemExit(99)',['--slots','5'],success=False)
        self.assertEqual(r['reason'],'invalid_work_slots')

    def test_memory_reservation_refuses_before_exec(self):
        r=self.invoke('envelope','raise SystemExit(99)',['--declared-memory-bytes',str(6<<30)],success=False)
        self.assertEqual(r['reason'],'memory_envelope_refused')

    def test_failed_exec_is_durable_and_cannot_restart(self):
        r=self.invoke('exec-fail','raise SystemExit(17)',success=False)
        self.assertEqual(r['result']['reason'],'command_failed')
        r=self.invoke('after-fail','pass',success=False)
        self.assertEqual(r['reason'],'stale_or_failed_reservation')

    def test_affinity_violation_is_detected_within_outer_mask(self):
        allowed=sorted(os.sched_getaffinity(0))
        self.assertGreaterEqual(len(allowed),4)
        child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(2)'])
        try:
            os.sched_setaffinity(child.pid,{allowed[2]})
            with self.assertRaises(cpu.AdmissionError):cpu.snapshot(child.pid,set(allowed[:2]))
        finally:
            child.kill();child.wait()

    def test_unreadable_live_telemetry_is_not_silently_ignored(self):
        with patch.object(cpu.Path,'read_text',side_effect=PermissionError('denied')):
            with self.assertRaises(PermissionError):cpu.snapshot(os.getpid(),os.sched_getaffinity(0))

    def test_pid_reuse_does_not_match_old_identity(self):
        item=cpu.identity(os.getpid());item['start_ticks']+=1
        self.assertFalse(cpu.same_process(item))

    def test_receipt_write_failure_cannot_commit_replacement(self):
        path=self.directory/'receipt.json'
        with patch.object(cpu.os,'replace',side_effect=OSError('interrupted rename')):
            with self.assertRaises(OSError):cpu.atomic_json(path,{'pass':True})
        self.assertFalse(path.exists())

    def test_numerical_allocation_checkpoint_precedes_exec(self):
        wrapper=str(ROOT/'tools/lp_tensor_cost_exec.py')
        code=f'import os,sys; os.execv(sys.executable,[sys.executable,{wrapper!r},"--memory-bytes",str(64<<20),"--",sys.executable,"-c","import time;time.sleep(.05)"])'
        r=self.invoke('allocation',code)
        self.assertEqual(r['result']['peak_active_numerical_allocations'],1)
        self.assertEqual(len(r['result']['allocation_acknowledgements']),1)

    def test_oversized_numerical_allocation_refuses_before_target(self):
        wrapper=str(ROOT/'tools/lp_tensor_cost_exec.py')
        code=f'import os,sys; os.execv(sys.executable,[sys.executable,{wrapper!r},"--memory-bytes",str(1<<30),"--",sys.executable,"-c","raise SystemExit(99)"])'
        r=self.invoke('allocation-refused',code,success=False)
        self.assertEqual(r['result']['reason'],'command_failed')


if __name__ == '__main__':
    unittest.main()
