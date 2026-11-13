"""Corrected observer semantics and inherited live resource/cleanup contracts."""
import importlib.util
import inspect
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import lp_confirmation_supervisor as cpu
spec=importlib.util.spec_from_file_location('legacy_supervision_contracts',Path(__file__).with_name('test_lp_cpu_admission.py'))
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)


class CorrectedPortability(old.CpuAdmissionPortability):
    def setUp(self):
        change=patch.object(old,'cpu',cpu);change.start();self.addCleanup(change.stop)


class CorrectedLive(old.CpuAdmissionLive):
    def setUp(self):
        super().setUp()
        change=patch.object(old,'cpu',cpu);change.start();self.addCleanup(change.stop)

    def command(self,*args,**kwargs):
        command=super().command(*args,**kwargs)
        command[1]=str(ROOT/'tools/lp_confirmation_supervisor.py')
        return command

    def test_ready_handshake_and_resource_receipt(self):
        r=self.invoke('happy','import time; time.sleep(.04)')
        self.assertEqual(r['identity'],'cooperative_process_supervision_v3')
        self.assertGreater(r['guardian_observation']['heartbeats'],0)
        self.assertLessEqual(r['guardian_observation']['max_sample_gap_ns'],100000000)
        self.assertEqual(r['charged_cpu_ns'],4*(r['active_elapsed_ns']+1000000000))

    def test_coordinator_pause_remains_a_real_sampling_failure(self):
        r=self.invoke('pause','import os,signal,time; os.kill(int(os.environ["LP_CPU_COORDINATOR_PID"]),signal.SIGSTOP); time.sleep(.18)',success=False)
        self.assertEqual(r['result']['reason'],'lost_coordinator_heartbeat')
        self.assertTrue(r['guardian_cleanup']['empty'])

    def test_delayed_guardian_observes_healthy_queued_samples(self):
        # Inject real elapsed time at the guardian's first loop observation. The
        # coordinator runs normally; no timestamp is fabricated or advanced.
        request=dict(stage='implementation',reserve_cpu_seconds=24,output=str(self.directory/'lag.json'),
            log=str(self.directory/'lag.log'),journal=str(self.directory/'journal.json'),lock=str(self.directory/'lock'),
            slots=4,declared_memory_bytes=64<<20,rss_stop_bytes=6<<30,address_space_bytes=0,sources=[],
            bootstrap=False,show_log=False,max_gap_ns=100000000,command=[sys.executable,'-c','import time;time.sleep(.6)'])
        runner=self.directory/'runner.py';request_path=self.directory/'request.json'
        request_path.write_text(json.dumps(request))
        runner.write_text('''import sys,os,time,inspect,json
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import lp_confirmation_supervisor as cpu
owner=os.getpid();clock=time.monotonic_ns;paused=False
def delayed():
 global paused
 frame=inspect.currentframe().f_back
 if not paused and os.getpid()==owner and frame.f_code.co_name=='run' and 'previous_observation' in frame.f_locals:
  paused=True;time.sleep(.18)
 return clock()
cpu.time.monotonic_ns=delayed
r=cpu.run(json.loads(Path(sys.argv[2]).read_text()))
assert paused
print(r['status'])
''')
        p=subprocess.run([sys.executable,str(runner),str(ROOT/'tools'),str(request_path)],capture_output=True,text=True,timeout=8)
        self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(p.stdout.strip(),'passed')
        r=json.loads((self.directory/'lag.json').read_text())
        self.assertGreaterEqual(r['guardian_observation']['max_loop_gap_ns'],180000000)
        self.assertLessEqual(r['result']['max_sample_gap_ns'],100000000)

    def timed_scan(self,name,delay,guardian_pause=0):
        request=dict(stage='implementation',reserve_cpu_seconds=24,output=str(self.directory/(name+'.json')),
            log=str(self.directory/(name+'.log')),journal=str(self.directory/'journal.json'),lock=str(self.directory/'lock'),
            slots=4,declared_memory_bytes=64<<20,rss_stop_bytes=6<<30,address_space_bytes=0,sources=[],
            bootstrap=False,show_log=False,max_gap_ns=100000000,command=[sys.executable,'-c','import time;time.sleep(.4)'])
        runner=self.directory/(name+'.py');request_path=self.directory/(name+'-request.json')
        request_path.write_text(json.dumps(request))
        runner.write_text('''import sys,os,time,inspect,json
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import lp_confirmation_supervisor as cpu
owner=os.getpid();clock=time.monotonic_ns;original=cpu.snapshot;paused=False
def delayed_scan(*a,**k):
 if inspect.currentframe().f_back.f_code.co_name=='coordinator':time.sleep(float(sys.argv[3]))
 return original(*a,**k)
def delayed_clock():
 global paused
 frame=inspect.currentframe().f_back
 if not paused and os.getpid()==owner and frame.f_code.co_name=='run' and 'previous_observation' in frame.f_locals:
  paused=True;time.sleep(float(sys.argv[4]))
 return clock()
cpu.snapshot=delayed_scan;cpu.time.monotonic_ns=delayed_clock
cpu.run(json.loads(Path(sys.argv[2]).read_text()))
''')
        result=subprocess.run([sys.executable,str(runner),str(ROOT/'tools'),str(request_path),str(delay),str(guardian_pause)],
                              capture_output=True,text=True,timeout=8)
        self.assertEqual(result.returncode,0,result.stderr)
        return json.loads((self.directory/(name+'.json')).read_text())

    def test_two_valid_long_scans_do_not_create_false_staleness(self):
        r=self.timed_scan('valid-scans',.060)
        self.assertEqual(r['status'],'passed',r['result'])
        self.assertGreaterEqual(r['result']['max_sample_work_ns'],60000000)
        self.assertLessEqual(r['result']['max_sample_gap_ns'],100000000)

    def test_overlong_scan_refuses_even_when_guardian_is_delayed(self):
        r=self.timed_scan('overlong-scan',.150,.180)
        self.assertEqual(r['status'],'refused')
        self.assertEqual(r['result']['reason'],'sample_duration')
        self.assertTrue(r['guardian_cleanup']['empty'])


class HeartbeatCadence(unittest.TestCase):
    def watch(self):
        x=cpu.Heartbeats(100,1000);x.entry();return x

    def test_queued_old_messages_never_extend_freshness(self):
        x=self.watch();x.sample(1010,2000);x.sample(1020,2001)
        self.assertFalse(x.fresh(2001))

    def test_continuous_queue_can_outlive_observer_pause(self):
        x=self.watch()
        for t in range(1010,1401,10):x.sample(t,1401)
        self.assertTrue(x.fresh(1401));self.assertEqual(x.max_sample_gap,10)
        self.assertGreater(x.max_delivery_lag,100)

    def test_genuine_sample_gap_is_not_hidden_by_queued_delivery(self):
        x=self.watch();x.sample(1010,2000)
        with self.assertRaisesRegex(cpu.AdmissionError,'heartbeat_sample_gap'):x.sample(1111,2001)

    def test_duplicate_reversed_future_boolean_and_missing_timestamps_refuse(self):
        for sent in [1010,1009,2002,True,None,1.5]:
            x=self.watch();x.sample(1010,2000)
            with self.assertRaises(cpu.AdmissionError):x.sample(sent,2001)

    def test_entry_is_required_and_cannot_repeat(self):
        x=cpu.Heartbeats(100,1000)
        with self.assertRaises(cpu.AdmissionError):x.sample(1010,1020)
        x.entry()
        with self.assertRaises(cpu.AdmissionError):x.entry()

    def test_queued_sample_before_guardian_initialization_is_valid(self):
        x=cpu.Heartbeats(100,1100,1000);x.entry();x.sample(1050,1101)
        self.assertTrue(x.fresh(1101))
        y=cpu.Heartbeats(100,1100,1000);y.entry()
        with self.assertRaises(cpu.AdmissionError):y.sample(999,1101)


if __name__=='__main__':unittest.main()
