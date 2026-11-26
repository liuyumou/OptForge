"""Prospective two-hour factorized-geometry study; original guards unchanged."""
import argparse
import datetime as dt
import json
from pathlib import Path
import sys
import lp_sp_pricing_budget as original
from lp_sp_pricing_gpu_opt_compare import read, verify

APPROVAL = original.BASE/'factor-allocation-v1.json'
CPU = dict(reference=32000, admission=24000, development=30000, confirmation=124000, billion=0, reporting=30000)
GPU = dict(reference=0, admission=5000, development=3000, confirmation=22000, billion=0, reporting=0)
DEADLINE = '2026-11-26T03:53:22+00:00'


def approve():
    prior = original.BASE/'scale-report-v1/settled-checkpoint.json'
    if read(prior)['active_reservations']:
        raise RuntimeError('preceding study is unsettled')
    original.accounting(original.BASE); original.accounting(original.BASE, True)
    if sum(CPU.values()) != 240000 or sum(GPU.values()) != 30000:
        raise RuntimeError('total ceiling changed')
    original.put(APPROVAL, dict(status='prospectively_authorized_phase_transfer',
        authorization='User requests faster tall exact geometry with implicit/factorized representations and GPU acceleration, more eligible comparisons, in two hours.',
        recorded_utc=dt.datetime.now(dt.timezone.utc).isoformat(), wall_deadline_utc=DEADLINE,
        cpu=CPU, gpu=GPU, prior_checkpoint=original.binding(prior),
        prior_allocation=original.binding(original.BASE/'scale-allocation-v1.json'),
        source=original.binding(__file__), original_wrapper=original.binding(original.__file__),
        invariant='Original total 240000 CPU / 30000 GPU seconds; all charges, supervision, ownership, physical limits and idle checks remain. No historical scientific identity repeats.'))


def allocation():
    d = read(APPROVAL)
    for key in ('source', 'original_wrapper', 'prior_checkpoint', 'prior_allocation'):
        verify(d[key])
    if d['cpu'] != CPU or d['gpu'] != GPU:
        raise RuntimeError('allocation changed')
    return d


if __name__ == '__main__':
    if sys.argv[1:] == ['approve']:
        approve(); raise SystemExit(0)
    p = argparse.ArgumentParser(); p.add_argument('--id', required=True)
    p.add_argument('--phase', choices=CPU, required=True); p.add_argument('--seconds', type=int, required=True)
    p.add_argument('--host-gib', type=int, default=32); p.add_argument('--gpu', action='store_true')
    p.add_argument('command', nargs=argparse.REMAINDER); args = p.parse_args(); d = allocation()
    left = (dt.datetime.fromisoformat(d['wall_deadline_utc'])-dt.datetime.now(dt.timezone.utc)).total_seconds()
    if left < args.seconds+120:
        raise RuntimeError('complete reservation does not fit the two-hour envelope')
    original.CPU.clear(); original.CPU.update(CPU); original.GPU.clear(); original.GPU.update(GPU)
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    result = original.run(args.id, args.phase, args.seconds, command, args.host_gib, gpu=args.gpu)
    print(json.dumps(result, sort_keys=True), flush=True)
    raise SystemExit(int(result['status'] != 'passed'))
