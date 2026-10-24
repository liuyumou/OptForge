"""Acknowledge a numerical worker's pre-admitted host allocation before exec."""
import argparse
import json
import os
import time
from pathlib import Path
from lp_cpu_admission import identity,atomic_json

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--memory-bytes',type=int,default=2<<30)
    p.add_argument('command',nargs=argparse.REMAINDER)
    a=p.parse_args();command=a.command[1:] if a.command[:1]==['--'] else a.command
    envelope=int(os.environ['LP_CPU_DECLARED_MEMORY_BYTES'])
    allowed=set(json.loads(os.environ['LP_CPU_ALLOWED_CPUS']))
    if not command or not 0<a.memory_bytes<=envelope or not os.sched_getaffinity(0)<=allowed:
        raise ValueError('unadmitted numerical worker allocation/affinity')
    record=dict(identity=identity(os.getpid()),host_bytes=a.memory_bytes,
                phase_sha256=os.environ['LP_CPU_PHASE_SHA256'],acknowledged_ns=time.monotonic_ns())
    directory=Path(os.environ['LP_CPU_ALLOCATION_DIR']);directory.mkdir(parents=True,exist_ok=True)
    target=directory/(str(record['identity']['pid'])+'-'+str(record['identity']['start_ticks'])+'.json')
    if target.exists():raise ValueError('duplicate numerical allocation acknowledgement')
    atomic_json(target,record)
    os.execvpe(command[0],command,os.environ)

if __name__=='__main__':main()
