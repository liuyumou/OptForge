"""Final bounded pipeline refinement; cumulative allocation stays unchanged."""
import argparse
import datetime as dt
import json
import sys
import lp_sp_pricing_budget as original
from lp_sp_pricing_pipeline_budget_v2 import allocation as preceding,CPU,DEADLINE
from lp_sp_pricing_gpu_opt_compare import read,verify
GPU=dict(reference=0,admission=4277,development=3416,confirmation=22307,billion=0,reporting=0)
APPROVAL=original.BASE/'pipeline-allocation-v3.json'

def allocation():
    preceding();d=read(APPROVAL)
    for k in ('source','previous','development','freeze'):verify(d[k])
    if d['cpu']!=CPU or d['gpu']!=GPU:raise RuntimeError('pipeline v2 allocation changed')
    return d

def approve():
    preceding();cpu,gpu=original.accounting(original.BASE),original.accounting(original.BASE,True);cp=dict(confirmation=4160,reporting=2400);gp=dict(confirmation=140)
    if sum(GPU.values())!=30000 or any(cpu[k]+cp.get(k,0)*original.NS>CPU[k]*original.NS or gpu[k]+gp.get(k,0)*original.NS>GPU[k]*original.NS for k in CPU):raise RuntimeError('padded untouched holdout reserve')
    original.put(APPROVAL,dict(status='untouched_holdout_outer_reserve_padding',source=original.binding(__file__),previous=original.binding(original.BASE/'pipeline-allocation-v2.json'),development=original.binding(original.BASE/'pipeline-development-v2/result.json'),freeze=original.binding(original.BASE/'pipeline-evaluation-v2/freeze.json'),cpu=CPU,gpu=GPU,full_cpu_reserves=cp,full_gpu_reserves=gp,cpu_used_ns=cpu,gpu_used_ns=gpu,wall_deadline_utc=DEADLINE,
        authorization='Same user request and cumulative totals. Before any holdout runs, transfer 20 unused development GPU seconds to confirmation and reserve 140 seconds for the untouched 18-slot GPU group, including its unchanged 30-second idle proof. Every model, native allowance, selected configuration, acceptance rule and prior charge stays exact. The original driver remains unstarted.'))

if __name__=='__main__':
    if sys.argv[1:]==['approve']:approve();raise SystemExit(0)
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--phase',choices=CPU,required=True);p.add_argument('--seconds',type=int,required=True);p.add_argument('--host-gib',type=int,default=32);p.add_argument('--gpu',action='store_true');p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args();d=allocation()
    if (dt.datetime.fromisoformat(d['wall_deadline_utc'])-dt.datetime.now(dt.timezone.utc)).total_seconds()<a.seconds+120:raise RuntimeError('wall envelope')
    original.CPU.clear();original.CPU.update(CPU);original.GPU.clear();original.GPU.update(GPU);cmd=a.command[1:] if a.command[:1]==['--'] else a.command
    r=original.run(a.id,a.phase,a.seconds,cmd,a.host_gib,gpu=a.gpu);print(json.dumps(r,sort_keys=True),flush=True);raise SystemExit(int(r['status']!='passed'))
