"""User-authorized prospective phase transfer for the two-hour scale campaign.

The original wrapper, supervisor, admission sources and historical receipts remain
unchanged. Only phase allocations change; the original total ceilings are kept.
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path
import lp_sp_pricing_budget as original
from lp_sp_pricing_gpu_opt_compare import read,verify

APPROVAL=original.BASE/'scale-allocation-v1.json'
CPU=dict(original.CPU,confirmation=84000,billion=36000)
GPU=dict(original.GPU,confirmation=17000,billion=3000)
DEADLINE='2026-11-26T02:12:58+00:00'

def approve():
    old=original.BASE/'geometry-report-v1/settled-checkpoint.json';d=read(old)
    if d['active_reservations']:raise RuntimeError('unsettled preceding campaign')
    if sum(CPU.values())!=sum(original.CPU.values()) or sum(GPU.values())!=sum(original.GPU.values()):raise RuntimeError('total allocation changed')
    original.accounting(original.BASE);original.accounting(original.BASE,True)
    original.put(APPROVAL,dict(status='prospectively_authorized_phase_transfer',
        authorization='User: You can use more time budget as needed. But I hope the experiments can end in 2 hours.',
        recorded_utc=dt.datetime.now(dt.timezone.utc).isoformat(),wall_deadline_utc=DEADLINE,
        cpu=CPU,gpu=GPU,previous_cpu=dict(original.CPU),previous_gpu=dict(original.GPU),
        prior_checkpoint=original.binding(old),source=original.binding(__file__),
        original_wrapper=original.binding(Path(original.__file__)),
        invariant='240000 CPU / 30000 GPU seconds total; all prior charges, physical limits, ownership, idle and cleanup guards unchanged'))

def allocation():
    d=read(APPROVAL);verify(d['source']);verify(d['original_wrapper']);verify(d['prior_checkpoint'])
    if d['cpu']!=CPU or d['gpu']!=GPU:raise RuntimeError('allocation mismatch')
    return d

def run(args):
    d=allocation();now=dt.datetime.now(dt.timezone.utc);deadline=dt.datetime.fromisoformat(d['wall_deadline_utc'])
    if (deadline-now).total_seconds()<args.seconds+120:raise RuntimeError('two-hour campaign envelope: insufficient complete reservation and settlement time')
    original.CPU.clear();original.CPU.update(CPU);original.GPU.clear();original.GPU.update(GPU)
    command=args.command[1:] if args.command[:1]==['--'] else args.command
    result=original.run(args.id,args.phase,args.seconds,command,args.host_gib,gpu=args.gpu)
    print(json.dumps(result,sort_keys=True),flush=True);return result['status']!='passed'

if __name__=='__main__':
    if sys.argv[1:]==['approve']:approve();raise SystemExit(0)
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--phase',choices=CPU,required=True)
    p.add_argument('--seconds',type=int,required=True);p.add_argument('--host-gib',type=int,default=32);p.add_argument('--gpu',action='store_true')
    p.add_argument('command',nargs=argparse.REMAINDER);raise SystemExit(int(run(p.parse_args())))
