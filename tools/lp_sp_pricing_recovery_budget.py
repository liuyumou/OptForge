"""Wide/mixed recovery follow-up, preserving cumulative ceilings and failures."""
import argparse
import datetime as dt
import json
import sys
import lp_sp_pricing_budget as original
from lp_sp_pricing_gpu_opt_compare import read,verify

APPROVAL=original.BASE/'recovery-allocation-v1.json'
CPU=dict(reference=18000,admission=26000,development=42000,confirmation=124000,billion=0,reporting=30000)
GPU=dict(reference=0,admission=4500,development=3100,confirmation=22400,billion=0,reporting=0)
DEADLINE='2026-11-26T06:40:24+00:00'

def allocation():
    d=read(APPROVAL)
    for key in ('source','original_wrapper','prior_checkpoint','prior_allocation'):verify(d[key])
    if d['cpu']!=CPU or d['gpu']!=GPU:raise RuntimeError('allocation changed')
    return d

def approve():
    prior=original.BASE/'nontall-report-v1/settled-checkpoint.json'
    if read(prior)['active_reservations']:raise RuntimeError('preceding study unsettled')
    cpu,gpu=original.accounting(original.BASE),original.accounting(original.BASE,True)
    if sum(CPU.values())!=240000 or sum(GPU.values())!=30000:raise RuntimeError('total cap changed')
    if any(cpu[p]>CPU[p]*original.NS or gpu[p]>GPU[p]*original.NS for p in CPU):raise RuntimeError('phase transfer below usage')
    original.put(APPROVAL,dict(status='prospectively_authorized_followup',cpu=CPU,gpu=GPU,
        authorization='User requests diagnosing/improving wide and mixed-active cases with GPU acceleration, fresh preparation/certification-inclusive COPT comparisons, and preservation of square/irregular performance. Transfer unused phase allowances within unchanged cumulative ceilings.',
        recorded_utc=dt.datetime.now(dt.timezone.utc).isoformat(),wall_deadline_utc=DEADLINE,
        source=original.binding(__file__),original_wrapper=original.binding(original.__file__),prior_checkpoint=original.binding(prior),
        prior_allocation=original.binding(original.BASE/'nontall-allocation-v1.json'),
        invariant='Existing numerical/resource sources, prior measurements and failed charges remain exact. Additive opt-in implementation and admission; no historical LP repetition. Four CPU slots and unchanged physical/ownership/idle controls.'))

if __name__=='__main__':
    if sys.argv[1:]==['approve']:approve();raise SystemExit(0)
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--phase',choices=CPU,required=True)
    p.add_argument('--seconds',type=int,required=True);p.add_argument('--host-gib',type=int,default=32);p.add_argument('--gpu',action='store_true');p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
    d=allocation();left=(dt.datetime.fromisoformat(d['wall_deadline_utc'])-dt.datetime.now(dt.timezone.utc)).total_seconds()
    if left<a.seconds+120:raise RuntimeError('reservation does not fit follow-up envelope')
    original.CPU.clear();original.CPU.update(CPU);original.GPU.clear();original.GPU.update(GPU)
    command=a.command[1:] if a.command[:1]==['--'] else a.command
    result=original.run(a.id,a.phase,a.seconds,command,a.host_gib,gpu=a.gpu)
    print(json.dumps(result,sort_keys=True),flush=True);raise SystemExit(int(result['status']!='passed'))
