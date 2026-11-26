"""Remaining final study reserves after measured scaled-tall regression."""
import argparse
import datetime as dt
import json
import sys
import lp_sp_pricing_budget as original
from lp_sp_pricing_final_budget import CPU,DEADLINE,allocation as preceding
from lp_sp_pricing_gpu_opt_compare import read,verify
GPU=dict(reference=0,admission=4277,development=3274,confirmation=22449,billion=0,reporting=0)
APPROVAL=original.BASE/'final-allocation-v2.json'

def allocation():
    preceding();d=read(APPROVAL)
    for k in ('source','previous','retained_development'):verify(d[k])
    if d['cpu']!=CPU or d['gpu']!=GPU:raise RuntimeError('v2 allocation changed')
    return d

def approve():
    preceding();cpu,gpu=original.accounting(original.BASE),original.accounting(original.BASE,True)
    cp=dict(admission=480,development=480,confirmation=11040,reporting=2400);gp=dict(development=120,confirmation=540)
    if sum(GPU.values())!=30000 or any(cpu[k]+cp.get(k,0)*original.NS>CPU[k]*original.NS or gpu[k]+gp.get(k,0)*original.NS>GPU[k]*original.NS for k in CPU):raise RuntimeError('v2 complete reserves do not fit')
    original.put(APPROVAL,dict(status='unused_phase_transfer_totals_unchanged',source=original.binding(__file__),previous=original.binding(original.BASE/'final-allocation-v1.json'),retained_development=original.binding(original.BASE/'final-development-v1/result.json'),
        cpu=CPU,gpu=GPU,full_cpu_reserves=cp,full_gpu_reserves=gp,cpu_used_ns=cpu,gpu_used_ns=gpu,wall_deadline_utc=DEADLINE,
        authorization='Existing request for improved rectangular/tall performance and preserved other cases. Reallocate unused admission allowance; use the measured development costs to reserve 540 seconds for untouched GPU holdouts. Preserve the scaled-tall regression and all other preceding outcomes.'))

if __name__=='__main__':
    if sys.argv[1:]==['approve']:approve();raise SystemExit(0)
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--phase',choices=CPU,required=True);p.add_argument('--seconds',type=int,required=True);p.add_argument('--host-gib',type=int,default=32);p.add_argument('--gpu',action='store_true');p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args();d=allocation()
    if (dt.datetime.fromisoformat(d['wall_deadline_utc'])-dt.datetime.now(dt.timezone.utc)).total_seconds()<a.seconds+120:raise RuntimeError('reservation outside deadline')
    original.CPU.clear();original.CPU.update(CPU);original.GPU.clear();original.GPU.update(GPU);cmd=a.command[1:] if a.command[:1]==['--'] else a.command
    r=original.run(a.id,a.phase,a.seconds,cmd,a.host_gib,gpu=a.gpu);print(json.dumps(r,sort_keys=True),flush=True);raise SystemExit(int(r['status']!='passed'))
