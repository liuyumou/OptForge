"""Independent, short CPU-only bootstrap witnesses for ADR-0044 supervision."""
import json
import fcntl
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

TOOL = Path(__file__).with_name('lp_cpu_admission.py')


def invoke(directory, name, code, **kwargs):
    output = directory / (name + '.json')
    command = [sys.executable, str(TOOL), '--stage', 'implementation',
               '--reserve-cpu-seconds', '24', '--output', str(output),
               '--journal', str(directory / (name + '-journal.json')),
               '--lock', str(directory / 'test.lock'),
               '--declared-memory-bytes', str(128 << 20),
               '--', sys.executable, '-c', code]
    result = subprocess.run(command, capture_output=True, text=True, timeout=8)
    if kwargs.get('success', True):
        assert result.returncode == 0, (result.stdout, result.stderr)
        report = json.loads(output.read_text())
        assert report['status'] == 'passed', report
        assert report['result']['entry']['pid'] > 0
        assert report['result']['samples'] > 0
        assert report['guardian_cleanup']['empty']
        assert report['request']['affinity'] == sorted(os.sched_getaffinity(0))[:4]
        return report
    assert result.returncode != 0, result.stdout
    return json.loads(output.read_text())


def main():
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='gpup8-cpu-bootstrap-') as temp:
        directory = Path(temp)
        happy = invoke(directory, 'ready', 'import time; time.sleep(.03)')
        marker = directory/'orphan-ready'
        orphan = invoke(directory, 'orphan',
                        'import os,time\nfrom pathlib import Path\n'
                        'p=os.fork()\nif p:\n'
                        f' while not Path({str(marker)!r}).exists(): time.sleep(.001)\n'
                        ' os._exit(0)\n'
                        f'os.setsid()\nPath({str(marker)!r}).write_text(str(os.getpid()))\n'
                        'time.sleep(2)\n')
        assert orphan['result']['cleanup']['empty']
        assert not Path('/proc/'+marker.read_text()).exists()
        killed = invoke(directory, 'coordinator-kill',
                        'import os,signal,time; '
                        'os.kill(int(os.environ["LP_CPU_COORDINATOR_PID"]),signal.SIGKILL); time.sleep(2)',
                        success=False)
        assert killed['result']['reason'] in ('coordinator_lost', 'lost_coordinator_heartbeat')
        assert killed['guardian_cleanup']['empty']
        assert killed['charged_cpu_ns'] >= 24_000_000_000
        # A stale durable reservation may never be treated as a fresh budget.
        journal = directory / 'stale-journal.json'
        journal.write_text(json.dumps(dict(active=dict(reserved_cpu_ns=1), failed=False)))
        outcome = subprocess.run([sys.executable, str(TOOL), '--stage', 'implementation',
                                  '--reserve-cpu-seconds', '24', '--output', str(directory/'stale.json'),
                                  '--journal', str(journal), '--lock', str(directory/'test.lock'),
                                  '--', sys.executable, '-c', 'raise SystemExit(99)'],
                                 capture_output=True, text=True, timeout=2)
        assert outcome.returncode == 2 and 'stale_or_failed_reservation' in outcome.stdout
        assert not (directory/'stale.json.log').exists()
        with (directory/'test.lock').open('a+b') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            outcome = subprocess.run([sys.executable,str(TOOL),'--stage','implementation',
                                      '--reserve-cpu-seconds','24','--output',str(directory/'locked.json'),
                                      '--lock',str(directory/'test.lock'),'--',sys.executable,'-c','pass'],
                                     capture_output=True,text=True,timeout=2)
            assert outcome.returncode==2 and not (directory/'locked.json.log').exists()
        print(json.dumps(dict(identity='adr0044-independent-bootstrap-v1', status='passed',
                              witnesses=['entry/affinity/pidfd', 'subreaper/nested-session cleanup',
                                         'coordinator-death guardian cleanup', 'stale journal refusal',
                                         'competing coordinator lock refusal'],
                              elapsed_seconds=time.monotonic()-started,
                              gpu_seconds=0, host_access=False,
                              supervisor_sha256=happy['request']['source_sha256'])))


if __name__ == '__main__':
    main()
