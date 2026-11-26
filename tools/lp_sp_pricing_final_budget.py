"""Final rectangular/tall study within the unchanged cumulative allocation."""
import argparse
import datetime as dt
import json
import sys
import lp_sp_pricing_budget as original
from lp_sp_pricing_gpu_opt_compare import read,verify
from lp_sp_pricing_rectangular_budget import allocation as preceding
CPU=dict(reference=16000,admission=28000,development=42000,confirmation=130000,billion=0,reporting=24000)
GPU=dict(reference=0,admission=4363,development=3176,confirmation=22461,billion=0,reporting=0)
DEADLINE='2026-11-26T08:01:11+00:00'
APPROVAL=original.BASE/'final-allocation-v1.json'

def allocation():
    preceding();d=read(APPROVAL)
    for k in ('source','previous','checkpoint'):verify(d[k])
    if d['cpu']!=CPU or d['gpu']!=GPU:raise RuntimeError('final allocation changed')
    return d

def approve():
    preceding();cpu,gpu=original.accounting(original.BASE),original.accounting(original.BASE,True)
    cp=dict(admission=1680,development=480,confirmation=11160,reporting=2400);gp=dict(admission=120,development=120,confirmation=570)
    if sum(CPU.values())!=240000 or sum(GPU.values())!=30000 or any(cpu[k]+cp.get(k,0)*original.NS>CPU[k]*original.NS or gpu[k]+gp.get(k,0)*original.NS>GPU[k]*original.NS for k in CPU):raise RuntimeError('complete prospective envelope does not fit')
    original.put(APPROVAL,dict(status='prospectively_authorized_final_followup',source=original.binding(__file__),previous=original.binding(original.BASE/'rectangular-allocation-v1.json'),checkpoint=original.binding(original.BASE/'recovery-report-v1/settled-checkpoint.json'),
        cpu=CPU,gpu=GPU,full_cpu_reserves=cp,full_gpu_reserves=gp,cpu_used_ns=cpu,gpu_used_ns=gpu,wall_deadline_utc=DEADLINE,recorded_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
        authorization='User requests final-version comprehensive report, rectangular and tall diagnosis/improvement, preservation of other cases and fresh complete-cost COPT comparisons. Reallocate unused phase allowances without changing cumulative totals; fresh two-hour envelope.',
        invariant='All prior numerical/resource sources and failures remain exact. Additive opt-in changes; no historical scientific replay. Four CPU slots, unchanged physical/ownership/idle checks. Dedicated new implicit-dual construction/proof processes may use four BLAS threads without simultaneous scan workers; other paths retain one thread.'))

if __name__=='__main__':
    if sys.argv[1:]==['approve']:approve();raise SystemExit(0)
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--phase',choices=CPU,required=True);p.add_argument('--seconds',type=int,required=True);p.add_argument('--host-gib',type=int,default=32);p.add_argument('--gpu',action='store_true');p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args();d=allocation()
    if (dt.datetime.fromisoformat(d['wall_deadline_utc'])-dt.datetime.now(dt.timezone.utc)).total_seconds()<a.seconds+120:raise RuntimeError('reservation outside deadline')
    original.CPU.clear();original.CPU.update(CPU);original.GPU.clear();original.GPU.update(GPU)
    command=a.command[1:] if a.command[:1]==['--'] else a.command;result=original.run(a.id,a.phase,a.seconds,command,a.host_gib,gpu=a.gpu)
    print(json.dumps(result,sort_keys=True),flush=True);raise SystemExit(int(result['status']!='passed'))
