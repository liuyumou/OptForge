"""Foreground bounded LP worker; optional ownership of the shared host GPU lease."""
import argparse
import ctypes
import fcntl
import math
import os
from pathlib import Path
import resource
import signal
import subprocess
import time
from lp_protocol import NS, read_json, write_json


def rss_tree(pid):
    """Conservatively sum RSS of the process tree; shared pages can be double counted."""
    pending=[pid]; seen=set(); total=0
    while pending:
        current=pending.pop()
        if current in seen: continue
        seen.add(current)
        try:
            for line in Path(f'/proc/{current}/status').read_text().splitlines():
                if line.startswith('VmRSS:'): total += int(line.split()[1])*1024
            pending.extend(map(int,Path(f'/proc/{current}/task/{current}/children').read_text().split()))
        except (FileNotFoundError, ProcessLookupError): pass
    return total


def enable_subreaper():
    """Adopt orphaned job descendants so cleanup can reap them before lease release."""
    libc = ctypes.CDLL(None, use_errno=True)
    # Linux PR_SET_CHILD_SUBREAPER; this is validation tooling, not a runtime FFI.
    if libc.prctl(36, 1, 0, 0, 0) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))


def reap_group(pgid):
    """The group was killed; wait for every adopted child to release its resources."""
    while True:
        try: os.waitpid(-pgid, 0)
        except ChildProcessError: return
        except InterruptedError: continue


def supervise(request, device=None):
    expected={'command','directory','prefix','solve_seconds','cleanup_seconds',
              'host_rss_bytes','poll_ms','output_bytes'}
    version = request.get('schema_version', 1)
    if version == 2:
        expected |= {'schema_version', 'gpu_admission_seconds'}
    elif version != 1:
        raise ValueError('unknown worker version')
    if set(request)!=expected: raise ValueError('invalid worker request fields')
    if not isinstance(request['command'],list) or not request['command'] or not all(isinstance(x,str) for x in request['command']):
        raise ValueError('invalid command')
    for key in expected-{'command','directory','prefix'}:
        if isinstance(request[key],bool) or not isinstance(request[key],(int,float)) or not math.isfinite(request[key]) or request[key]<=0: raise ValueError('invalid worker limit')
    if version == 2 and request['gpu_admission_seconds'] != 3:
        raise ValueError('unfrozen admission limit')
    directory=Path(request['directory']).resolve(); directory.mkdir(parents=True,exist_ok=True)
    prefix=request['prefix']
    if not prefix or Path(prefix).name!=prefix: raise ValueError('invalid worker prefix')
    enable_subreaper()
    cancelled=False
    def interrupt(*_):
        nonlocal cancelled
        cancelled=True
    old={s:signal.signal(s,interrupt) for s in [signal.SIGINT,signal.SIGTERM]}
    queued=time.monotonic_ns(); acquired=None; lock=None; child=None
    report={'schema_version':1,'returncode':None,'reason':None,'elapsed_ns':0,
            'queue_ns':0,'leased_ns':0,'peak_rss_bytes':0,'signal':None,'signal_events':[],
            'clock':'monotonic_ns','memory_method':'10ms aggregate process-tree VmRSS watchdog'}
    if version == 2:
        report.update(schema_version=2, activity=None)
    try:
        if device:
            if not device.startswith('GPU-'): raise ValueError('invalid device UUID')
            lock=open(os.environ.get('AI_OPTIMIZER_GPU_LOCK','/tmp/ai-optimizer-gpu.lock'),'a+b')
            while True:
                before=time.monotonic_ns()
                try:
                    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                    acquired=before; break
                except BlockingIOError:
                    if cancelled or time.monotonic_ns()-queued>=300*NS:
                        report['reason']='lease_cancelled' if cancelled else 'lease_timeout'
                        return report
                    time.sleep(0.01)
            report['queue_ns']=acquired-queued
        if device and version == 2:
            from lp_activity import ActivityPause, wait_quiet
            try:
                report['activity'] = wait_quiet(device, 3, lambda: cancelled)
            except ActivityPause as error:
                report.update(reason='activity_blocked', activity=error.report)
                return report
        if cancelled:
            report['reason']='cancelled_before_launch'; return report
        env={**os.environ,'OMP_NUM_THREADS':'1','LC_ALL':'C'}
        if device:
            env.update(CUDA_VISIBLE_DEVICES=device,AI_OPTIMIZER_GPU_LEASE='inherited')
        def limits():
            os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
            resource.setrlimit(resource.RLIMIT_FSIZE,(request['output_bytes'],request['output_bytes']))
            cpu=math.ceil(request['solve_seconds']+request['cleanup_seconds'])
            resource.setrlimit(resource.RLIMIT_CPU,(cpu,cpu+1))
        with (directory/(prefix+'.stdout')).open('wb') as stdout, (directory/(prefix+'.stderr')).open('wb') as stderr:
            started=time.monotonic_ns()
            child=subprocess.Popen(request['command'],cwd=Path(__file__).resolve().parents[1],
                stdout=stdout,stderr=stderr,start_new_session=True,env=env,preexec_fn=limits,
                pass_fds=(() if lock is None else (lock.fileno(),)))
            soft_deadline=started+round(request['solve_seconds']*NS)
            hard_deadline=soft_deadline+round(request['cleanup_seconds']*NS)
            signalled=None
            def send(signal_name, now):
                report['signal']=signal_name
                report['signal_events'].append({'signal':signal_name,'elapsed_ns':now-started})
                # Persist the interruption intent before sending it or escalating.
                write_json(directory/(prefix+'.worker.partial.json'),report)
                try: os.killpg(child.pid,getattr(signal,signal_name))
                except ProcessLookupError: pass
            while child.poll() is None:
                now=time.monotonic_ns()
                rss=rss_tree(child.pid); report['peak_rss_bytes']=max(report['peak_rss_bytes'],rss)
                reason='cancelled' if cancelled else ('memory_limit' if rss>request['host_rss_bytes'] else ('timeout' if now>=soft_deadline else None))
                if reason and signalled is None:
                    report['reason']=reason; signalled=now
                    hard_deadline=min(hard_deadline,now+round(request['cleanup_seconds']*NS))
                    send('SIGINT',now)
                if now>=hard_deadline and report['signal']!='SIGKILL':
                    send('SIGKILL',now)
                try: child.wait(timeout=request['poll_ms']/1000)
                except subprocess.TimeoutExpired: pass
            report['returncode']=child.wait()
            # A foreground command must not leave descendants holding the lease.
            try: os.killpg(child.pid,signal.SIGKILL)
            except ProcessLookupError: pass
            reap_group(child.pid)
            report['elapsed_ns']=time.monotonic_ns()-started
            if report['reason'] is None:
                report['reason']='completed' if child.returncode in (0,1,2,130) else 'process_failure'
            stdout.flush(); stderr.flush()
        return report
    finally:
        if child is not None and child.poll() is None:
            try: os.killpg(child.pid,signal.SIGKILL)
            except ProcessLookupError: pass
            child.wait()
            reap_group(child.pid)
        if lock is not None:
            fcntl.flock(lock,fcntl.LOCK_UN); lock.close()
            if acquired is not None: report['leased_ns']=time.monotonic_ns()-acquired
            else: report['queue_ns']=time.monotonic_ns()-queued
        for s,handler in old.items(): signal.signal(s,handler)
        write_json(directory/(prefix+'.worker.json'),report)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request',type=Path,required=True)
    parser.add_argument('--lease')
    args=parser.parse_args(); supervise(read_json(args.request),args.lease)
