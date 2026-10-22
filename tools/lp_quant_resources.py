"""Bound and retain CPU gate process-tree resources; never runs a GPU job itself."""
import argparse
import os
from pathlib import Path
import resource
import signal
import subprocess
import time
from lp_protocol import write_json
from benchmark_lp import source_identity

def process_tree(pid):
    pending=[pid];seen=set();rss=0;ticks=0
    while pending:
        current=pending.pop()
        if current in seen:continue
        seen.add(current)
        try:
            directory=Path('/proc')/str(current)
            for line in (directory/'status').read_text().splitlines():
                if line.startswith('VmRSS:'):rss+=int(line.split()[1])*1024
            stat=(directory/'stat').read_text().split(') ',1)[1].split()
            ticks+=sum(int(stat[i]) for i in [11,12,13,14])
            # Children spawned by worker threads are attached to that task,
            # rather than necessarily to the process's main thread.
            for task in (directory/'task').iterdir():
                try:pending.extend(map(int,(task/'children').read_text().split()))
                except (FileNotFoundError,ProcessLookupError):pass
        except (FileNotFoundError,ProcessLookupError):pass
    return rss,ticks/os.sysconf('SC_CLK_TCK')

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args();command=a.command[1:] if a.command[:1]==['--'] else a.command
    if not command:raise ValueError('resource monitor needs a command')
    a.output.parent.mkdir(parents=True,exist_ok=True);source_before=source_identity();start=time.monotonic_ns();before=resource.getrusage(resource.RUSAGE_CHILDREN);peak=0;reason='completed'
    with a.output.with_suffix('.log').open('wb') as stream:
        child=subprocess.Popen(command,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
        while child.poll() is None:
            rss,cpu=process_tree(child.pid);peak=max(peak,rss)
            if peak>8<<30 or cpu>21600 or time.monotonic_ns()-start>21600*10**9:
                reason='resource_limit';os.killpg(child.pid,signal.SIGTERM)
                try:child.wait(timeout=3)
                except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
                break
            time.sleep(.05)
    after=resource.getrusage(resource.RUSAGE_CHILDREN)
    result=dict(command=command,returncode=child.returncode,reason=reason,elapsed_ns=time.monotonic_ns()-start,cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,peak_process_tree_rss_bytes=peak,max_child_rss_bytes=after.ru_maxrss*1024)
    result.update(source_before=source_before,source_after=source_identity(),rss_method="all thread child lists plus per-process VmRSS")
    if result["source_before"]!=result["source_after"]:result["reason"]="source_changed"
    write_json(a.output,result);print(result,flush=True)
    if child.returncode or result['reason']!='completed':raise SystemExit(child.returncode or 1)
if __name__=='__main__':main()
