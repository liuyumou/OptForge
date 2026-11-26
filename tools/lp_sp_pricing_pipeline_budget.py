"""Scaled-tall followup using only the unused cumulative allocation."""
import argparse
import datetime as dt
import json
import sys
import lp_sp_pricing_budget as original
from lp_sp_pricing_final_budget_v2 import allocation as preceding,CPU
from lp_sp_pricing_gpu_opt_compare import read,verify
GPU=dict(reference=0,admission=4277,development=3366,confirmation=22357,billion=0,reporting=0)
DEADLINE='2026-11-26T09:01:24+00:00'
APPROVAL=original.BASE/'pipeline-allocation-v1.json'

def allocation():
    preceding();d=read(APPROVAL)
    for key in ('source','previous','checkpoint'):verify(d[key])
    if d['cpu']!=CPU or d['gpu']!=GPU:raise RuntimeError('pipeline allocation changed')
    return d

def approve():
    preceding();cpu,gpu=original.accounting(original.BASE),original.accounting(original.BASE,True)
    cp=dict(admission=960,development=480,confirmation=4360,reporting=2400);gp=dict(development=120,confirmation=190)
    if sum(CPU.values())!=240000 or sum(GPU.values())!=30000 or any(cpu[k]+cp.get(k,0)*original.NS>CPU[k]*original.NS or gpu[k]+gp.get(k,0)*original.NS>GPU[k]*original.NS for k in CPU):raise RuntimeError('complete pipeline reserve does not fit')
    original.put(APPROVAL,dict(status='prospectively_authorized_scaled_tall_followup',source=original.binding(__file__),previous=original.binding(original.BASE/'final-allocation-v2.json'),checkpoint=original.binding(original.BASE/'final-comprehensive-report-v1/settled-checkpoint.json'),cpu=CPU,gpu=GPU,full_cpu_reserves=cp,full_gpu_reserves=gp,cpu_used_ns=cpu,gpu_used_ns=gpu,wall_deadline_utc=DEADLINE,
        authorization='User requests faster scaled-tall correction checks with GPU acceleration/pipelining, preservation of other cases, and fresh preparation/certification-inclusive COPT comparisons. Transfer unused phase allowance; cumulative totals unchanged; fresh two-hour envelope.',
        invariant='Existing sources, kernels, independent acceptance and all historical attempts/charges remain exact. New opt-in source versions and fresh inputs only. Four CPU slots; one GPU projection thread plus at most three BLAS threads in a bounded single correction worker. Existing resource, ownership, storage and 30-second idle guards unchanged.'))

if __name__=='__main__':
    if sys.argv[1:]==['approve']:approve();raise SystemExit(0)
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--phase',choices=CPU,required=True);p.add_argument('--seconds',type=int,required=True);p.add_argument('--host-gib',type=int,default=32);p.add_argument('--gpu',action='store_true');p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args();d=allocation()
    if (dt.datetime.fromisoformat(d['wall_deadline_utc'])-dt.datetime.now(dt.timezone.utc)).total_seconds()<a.seconds+120:raise RuntimeError('outside wall envelope')
    original.CPU.clear();original.CPU.update(CPU);original.GPU.clear();original.GPU.update(GPU);cmd=a.command[1:] if a.command[:1]==['--'] else a.command
    r=original.run(a.id,a.phase,a.seconds,cmd,a.host_gib,gpu=a.gpu);print(json.dumps(r,sort_keys=True),flush=True);raise SystemExit(int(r['status']!='passed'))
