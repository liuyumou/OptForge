"""Final bounded pipeline refinement; cumulative allocation stays unchanged."""
import argparse
import datetime as dt
import json
import sys
import lp_sp_pricing_budget as original
from lp_sp_pricing_pipeline_budget import allocation as preceding,CPU,DEADLINE
from lp_sp_pricing_gpu_opt_compare import read,verify
GPU=dict(reference=0,admission=4277,development=3436,confirmation=22287,billion=0,reporting=0)
APPROVAL=original.BASE/'pipeline-allocation-v2.json'

def allocation():
    preceding();d=read(APPROVAL)
    for k in ('source','previous','development'):verify(d[k])
    if d['cpu']!=CPU or d['gpu']!=GPU:raise RuntimeError('pipeline v2 allocation changed')
    return d

def approve():
    preceding();cpu,gpu=original.accounting(original.BASE),original.accounting(original.BASE,True);cp=dict(admission=960,development=480,confirmation=4080,reporting=2400);gp=dict(development=120,confirmation=120)
    if sum(GPU.values())!=30000 or any(cpu[k]+cp.get(k,0)*original.NS>CPU[k]*original.NS or gpu[k]+gp.get(k,0)*original.NS>GPU[k]*original.NS for k in CPU):raise RuntimeError('complete refined pipeline reserve')
    original.put(APPROVAL,dict(status='unused_phase_transfer_totals_unchanged',source=original.binding(__file__),previous=original.binding(original.BASE/'pipeline-allocation-v1.json'),development=original.binding(original.BASE/'pipeline-development-v1/result.json'),cpu=CPU,gpu=GPU,full_cpu_reserves=cp,full_gpu_reserves=gp,cpu_used_ns=cpu,gpu_used_ns=gpu,wall_deadline_utc=DEADLINE,
        authorization='Same scaled-tall acceleration request. Retain first development; reduce eager inverse work and check the latest snapshot before draining. Move three fresh unscaled GPU regression pairs into the final development reservation; untouched COPT holdout roster remains six models x four lanes, plus fifteen CPU regression pairs. No attempted input or identity repeats.'))

if __name__=='__main__':
    if sys.argv[1:]==['approve']:approve();raise SystemExit(0)
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--phase',choices=CPU,required=True);p.add_argument('--seconds',type=int,required=True);p.add_argument('--host-gib',type=int,default=32);p.add_argument('--gpu',action='store_true');p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args();d=allocation()
    if (dt.datetime.fromisoformat(d['wall_deadline_utc'])-dt.datetime.now(dt.timezone.utc)).total_seconds()<a.seconds+120:raise RuntimeError('wall envelope')
    original.CPU.clear();original.CPU.update(CPU);original.GPU.clear();original.GPU.update(GPU);cmd=a.command[1:] if a.command[:1]==['--'] else a.command
    r=original.run(a.id,a.phase,a.seconds,cmd,a.host_gib,gpu=a.gpu);print(json.dumps(r,sort_keys=True),flush=True);raise SystemExit(int(r['status']!='passed'))
