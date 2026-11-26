"""Let an owned supervisor inventory helper finish naturally before command exit.

No signals, synthetic heartbeats, sampling changes or resource exceptions.
The bounded wait is outside solver timing and inside its original reservation.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
from lp_sp_pricing_budget import ROOT,binding,put
from lp_sp_pricing_finish import still_same_process

GUARD=ROOT/'tools/lp_sp_pricing_guard.py'


def inventory_command(argv):
    return len(argv)>=4 and argv[-2:]==[str(GUARD),'inventory'] and argv[-3]=='-B'


def process(pid):
    try:
        fields=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()
        argv=[v.decode() for v in Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0') if v]
        return dict(pid=pid,start_ticks=int(fields[19]),ppid=int(fields[1]),state=fields[0],inventory=inventory_command(argv))
    except (FileNotFoundError,ProcessLookupError):return None


def finish(coordinator,seconds=15):
    start=time.monotonic_ns();deadline=time.monotonic()+seconds;seen={};idle_since=None
    while True:
        if not still_same_process(coordinator['pid'],coordinator['start_ticks']):raise RuntimeError('original coordinator disappeared')
        children=Path(f'/proc/{coordinator["pid"]}/task/{coordinator["pid"]}/children').read_text().split();active=[]
        for raw in children:
            item=process(int(raw))
            if item and item['ppid']==coordinator['pid'] and item['inventory']:
                seen[(item['pid'],item['start_ticks'])]=item;active.append(item)
        if active:idle_since=None
        elif idle_since is None:idle_since=time.monotonic()
        elif time.monotonic()-idle_since>=.1:break
        if time.monotonic()>=deadline:raise TimeoutError('owned inventory did not finish within exit allowance')
        time.sleep(.01)
    return dict(status='owned_inventory_quiescent',observed_helpers=list(seen.values()),elapsed_ns=time.monotonic_ns()-start,
        coordinator=coordinator,signals_sent=0,resource_observation_changes=0,source=binding(__file__))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--receipt',type=Path,required=True);p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
    coordinator=process(int(os.environ['LP_CPU_COORDINATOR_PID']))
    if coordinator is None:raise RuntimeError('coordinator identity unavailable')
    command=a.command[1:] if a.command[:1]==['--'] else a.command;code=subprocess.call(command,cwd=ROOT)
    result=finish(coordinator);result['command_returncode']=code;put(a.receipt,result);raise SystemExit(code)
