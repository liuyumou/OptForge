"""Bound and retain CPU gate process-tree resources; never runs a GPU job itself."""
import argparse
import os
from pathlib import Path
import resource
import signal
import subprocess
import time
from lp_protocol import write_json
from lp_supervise import rss_tree

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args();command=a.command[1:] if a.command[:1]==['--'] else a.command
    if not command:raise ValueError('resource monitor needs a command')
    a.output.parent.mkdir(parents=True,exist_ok=True);start=time.monotonic_ns();before=resource.getrusage(resource.RUSAGE_CHILDREN);peak=0;reason='completed'
    with a.output.with_suffix('.log').open('wb') as stream:
        child=subprocess.Popen(command,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
        while child.poll() is None:
            peak=max(peak,rss_tree(child.pid))
            if peak>8<<30 or time.monotonic_ns()-start>21600*10**9:
                reason='resource_limit';os.killpg(child.pid,signal.SIGTERM)
                try:child.wait(timeout=3)
                except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
                break
            time.sleep(.05)
    after=resource.getrusage(resource.RUSAGE_CHILDREN)
    result=dict(command=command,returncode=child.returncode,reason=reason,elapsed_ns=time.monotonic_ns()-start,cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,peak_process_tree_rss_bytes=peak,max_child_rss_bytes=after.ru_maxrss*1024)
    write_json(a.output,result);print(result,flush=True)
    if child.returncode or reason!='completed':raise SystemExit(child.returncode or 1)
if __name__=='__main__':main()
