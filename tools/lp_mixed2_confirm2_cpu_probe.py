"""Fixed original CPU workload with before/after host observations."""
import argparse
import os
from pathlib import Path
import subprocess
import time
from lp_mixed2_confirm2_common import BASE, put, ref


def host():
    result=dict(monotonic_ns=time.monotonic_ns(),affinity=sorted(os.sched_getaffinity(0)))
    for name in ['cpu.max','cpu.stat','cpu.pressure','memory.current','memory.peak','memory.events']:
        path=Path('/sys/fs/cgroup')/name
        try:result[str(path)]=path.read_text()
        except OSError as error:result[str(path)]=repr(error)
    for name in ['/proc/stat','/proc/pressure/cpu','/proc/pressure/memory','/proc/self/timerslack_ns']:
        try:result[name]=Path(name).read_text()
        except OSError as error:result[name]=repr(error)
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('identity');a=p.parse_args()
    folder=BASE/a.identity;folder.mkdir(exist_ok=False)
    command=['cargo','test','-p','optimizer-experiment','--all-features','--locked','--offline','--lib']
    put(folder/'manifest.json',dict(command=command,source=ref(__file__),before=host(),
        limit_ns=1_000_000_000,previous_advisory_ns=100_000_000,scientific_timing=False,
        limitations='Shared-root cgroup and host counters are not exclusive task measurements.'))
    start=time.monotonic_ns();completed=subprocess.run(command)
    put(folder/'result.json',dict(status='passed' if completed.returncode==0 else 'failed',
        returncode=completed.returncode,elapsed_ns=time.monotonic_ns()-start,after=host()))
    raise SystemExit(completed.returncode)


if __name__=='__main__':main()
