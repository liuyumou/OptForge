"""Diagnostic-only post-refusal capture; no per-sample tracing or relaxed limit."""
import faulthandler
import inspect
import os
from pathlib import Path
import signal
import time


def install(supervisor,prefix):
    owner=os.getpid();original_coordinator=supervisor.coordinator
    original_cleanup=supervisor.terminate_descendants
    stack=open(str(prefix)+'.failure-stack.txt','xb',buffering=0)

    def process_record(pid):
        fields={}
        for name in ('schedstat','wchan','syscall','status'):
            try:fields[name]=Path(f'/proc/{pid}/{name}').read_text()
            except OSError as error:fields[name]=dict(unavailable=repr(error))
        return dict(pid=pid,time_ns=time.monotonic_ns(),fields=fields)

    def coordinator(*args,**kwargs):
        faulthandler.register(signal.SIGUSR1,file=stack,all_threads=True,chain=False)
        supervisor.atomic_json(str(prefix)+'.coordinator-start.json',process_record(os.getpid()))
        try:return original_coordinator(*args,**kwargs)
        finally:faulthandler.unregister(signal.SIGUSR1)

    def cleanup(*args,**kwargs):
        frame=inspect.currentframe().f_back
        reason=frame.f_locals.get('reason')
        if os.getpid()==owner and frame.f_code.co_name=='run' and reason=='lost_coordinator_heartbeat':
            pid=frame.f_locals['pid'];record=process_record(pid)
            record.update(reason=reason,guardian_pid=owner,decision_already_refused=True,
                          requested_capture_sleep_seconds=.015,source=supervisor.__file__)
            try:
                os.kill(pid,signal.SIGUSR1)
                time.sleep(.015)
            except ProcessLookupError:record['signal_unavailable']=True
            record['after_capture']=process_record(pid)
            record['capture_finished_ns']=time.monotonic_ns()
            supervisor.atomic_json(str(prefix)+'.failure-capture.json',record)
        return original_cleanup(*args,**kwargs)

    supervisor.coordinator=coordinator
    supervisor.terminate_descendants=cleanup
