"""Prospective unused GPU admission transfer after retained development I/O failure."""
import argparse
import datetime as dt
import json
import sys
import lp_sp_pricing_budget as original
from lp_sp_pricing_gpu_opt_compare import read,verify
from lp_sp_pricing_recovery_budget import CPU,DEADLINE,allocation as preceding
GPU=dict(reference=0,admission=4350,development=3250,confirmation=22400,billion=0,reporting=0)
APPROVAL=original.BASE/'rectangular-allocation-v1.json'

def allocation():
    preceding();d=read(APPROVAL)
    for k in ('source','previous','failure'):verify(d[k])
    if d['cpu']!=CPU or d['gpu']!=GPU:raise RuntimeError('rectangular allocation changed')
    return d

def approve():
    old=preceding();cpu,gpu=original.accounting(original.BASE),original.accounting(original.BASE,True)
    if sum(CPU.values())!=240000 or sum(GPU.values())!=30000 or any(cpu[p]>CPU[p]*original.NS or gpu[p]>GPU[p]*original.NS for p in CPU):raise RuntimeError('allocation does not fit')
    failure=original.BASE/'resources/rectangular-development-v1.settlement.json';r=read(failure)
    if r['status']!='refused' or not r['cleanup_empty'] or r['overrun'] or r['cpu_ns']!=600*original.NS or r['gpu_ns']!=150*original.NS:raise RuntimeError('original failure disposition')
    original.put(APPROVAL,dict(status='unused_phase_transfer_with_failure_retained',source=original.binding(__file__),previous=original.binding(original.BASE/'recovery-allocation-v1.json'),failure=original.binding(failure),
        cpu=CPU,gpu=GPU,wall_deadline_utc=DEADLINE,recorded_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
        authorization='Existing wide/mixed optimization authorization; transfer 150 unused GPU admission seconds to development without changing totals, physical limits, observations or two-hour deadline. Original failed baseline is never repeated and its full charge remains.'))

if __name__=='__main__':
    if sys.argv[1:]==['approve']:approve();raise SystemExit(0)
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--phase',choices=CPU,required=True);p.add_argument('--seconds',type=int,required=True);p.add_argument('--host-gib',type=int,default=32);p.add_argument('--gpu',action='store_true');p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args();d=allocation()
    if (dt.datetime.fromisoformat(d['wall_deadline_utc'])-dt.datetime.now(dt.timezone.utc)).total_seconds()<a.seconds+120:raise RuntimeError('reservation outside deadline')
    original.CPU.clear();original.CPU.update(CPU);original.GPU.clear();original.GPU.update(GPU)
    command=a.command[1:] if a.command[:1]==['--'] else a.command;result=original.run(a.id,a.phase,a.seconds,command,a.host_gib,gpu=a.gpu)
    print(json.dumps(result,sort_keys=True),flush=True);raise SystemExit(int(result['status']!='passed'))
