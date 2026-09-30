"""Meter bounded GPUP-CONVERGENCE child CPU and preserve command receipts."""
import os
from pathlib import Path
import resource
import subprocess
import sys
import time
from lp_convergence_budget import protocol
from lp_protocol import ROOT, read_json, write_json


def main():
    value=protocol(); out=ROOT/value['acceptance_output'];out.mkdir(parents=True,exist_ok=True)
    name=sys.argv[1];command=sys.argv[2:]
    if not command or '/' in name:raise ValueError('receipt name and command required')
    used=sum(read_json(p)['cpu_seconds'] for p in out.glob('*.cpu.json'))
    if used>=value['cpu_cap_seconds']:raise ValueError('CPU budget exhausted')
    env=dict(os.environ,CARGO_BUILD_JOBS='4',PYTHONDONTWRITEBYTECODE='1')
    if Path('/tmp/ai-optimizer-cargo/bin').exists():env['PATH']='/tmp/ai-optimizer-cargo/bin:'+env['PATH']
    if Path('/tmp/ai-optimizer-rustup').exists():env['RUSTUP_HOME']='/tmp/ai-optimizer-rustup'
    start=time.monotonic();before=resource.getrusage(resource.RUSAGE_CHILDREN)
    with (out/(name+'.log')).open('x') as log:
        result=subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
    after=resource.getrusage(resource.RUSAGE_CHILDREN)
    receipt=dict(command=command,returncode=result.returncode,wall_seconds=time.monotonic()-start,cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime)
    write_json(out/(name+'.cpu.json'),receipt);print(receipt,flush=True)
    if used+receipt['cpu_seconds']>value['cpu_cap_seconds']:raise ValueError('CPU cap exceeded')
    raise SystemExit(result.returncode)


if __name__=='__main__':main()
