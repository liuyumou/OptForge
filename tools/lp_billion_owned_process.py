"""Bound a directly owned child before the outer reservation's cleanup margin."""
import subprocess,time
from pathlib import Path
from lp_billion_common import require

def stop_owned(p):
    if p.poll() is None:
        p.terminate()
        try:p.wait(timeout=5)
        except subprocess.TimeoutExpired:p.kill();p.wait(timeout=10)

def execute(command,stdout,stderr,seconds,input_text=None):
    require(seconds>0,'positive owned-child deadline')
    started=time.monotonic_ns();timed_out=False
    with Path(stdout).open('w') as out,Path(stderr).open('w') as err:
        p=subprocess.Popen(command,stdin=subprocess.PIPE if input_text is not None else subprocess.DEVNULL,stdout=out,stderr=err,text=True)
        # Popen retains ownership of this unreaped child PID. Signal only that
        # child, never a discovered GPU PID, unrelated process or shared group.
        try:
            p.communicate(input=input_text,timeout=seconds)
        except subprocess.TimeoutExpired:
            timed_out=True;stop_owned(p)
    return dict(returncode=p.returncode,timed_out=timed_out,pid=p.pid,elapsed_ns=time.monotonic_ns()-started)
