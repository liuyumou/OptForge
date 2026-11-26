"""Bounded exit after observing a complete owned inventory cycle."""
import argparse
import os
from pathlib import Path
import subprocess
import time
from lp_sp_pricing_budget import ROOT,binding,put
from lp_sp_pricing_finish import still_same_process
from lp_sp_pricing_nontall_exit import process


def helpers(coordinator):
    raw=Path(f'/proc/{coordinator["pid"]}/task/{coordinator["pid"]}/children').read_text().split()
    items=[process(int(pid)) for pid in raw]
    return [v for v in items if v and v['ppid']==coordinator['pid'] and v['inventory']]


def finish(coordinator,seconds=15):
    start=time.monotonic_ns();deadline=time.monotonic()+seconds;seen={}
    while True:
        if not still_same_process(coordinator['pid'],coordinator['start_ticks']):raise RuntimeError('original coordinator disappeared')
        active=helpers(coordinator)
        for item in active:seen[(item['pid'],item['start_ticks'])]=item
        if seen and not active:break
        if time.monotonic()>=deadline:raise TimeoutError('no completed owned inventory cycle within exit allowance')
        time.sleep(.002)
    return dict(status='owned_inventory_cycle_completed',observed_helpers=list(seen.values()),elapsed_ns=time.monotonic_ns()-start,
        coordinator=coordinator,signals_sent=0,resource_observation_changes=0,source=binding(__file__))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--receipt',type=Path,required=True);p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
    coordinator=process(int(os.environ['LP_CPU_COORDINATOR_PID']))
    if coordinator is None:raise RuntimeError('coordinator identity unavailable')
    command=a.command[1:] if a.command[:1]==['--'] else a.command;code=subprocess.call(command,cwd=ROOT)
    result=finish(coordinator);result['command_returncode']=code;put(a.receipt,result);raise SystemExit(code)
