"""Diagnostic large Python fixture preparation with bounded parent telemetry."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time
from lp_mixed2_reuse_common import BASE, OLD, ROOT, load, put


def monitor(path, parent):
    ids=[int(os.environ[k]) for k in ('LP_CPU_COORDINATOR_PID','LP_CPU_GUARDIAN_PID')]+[parent]
    with path.open('x', buffering=1) as f:
        while os.getppid()==parent:
            row=dict(time_ns=time.monotonic_ns(),processes={})
            try:
                children=list(map(int,Path(f'/proc/{parent}/task/{parent}/children').read_text().split()))
            except OSError:children=[]
            for pid in sorted(set(ids+children)-{os.getpid()}):
                d={}
                for key in ('schedstat','wchan','stat','syscall'):
                    try:d[key]=Path(f'/proc/{pid}/{key}').read_text().strip()
                    except OSError as e:d[key]=type(e).__name__
                row['processes'][pid]=d
            for name in ['cpu.stat','memory.events']:
                try:row[name]=Path('/sys/fs/cgroup',name).read_text().strip()
                except OSError:row[name]='unavailable'
            f.write(json.dumps(row)+'\n');time.sleep(.01)


def run(out, pin):
    out.mkdir(exist_ok=False)
    cpus=json.loads(os.environ['LP_CPU_ALLOWED_CPUS'])
    if pin:
        for key in ('LP_CPU_COORDINATOR_PID','LP_CPU_GUARDIAN_PID'):
            os.sched_setaffinity(int(os.environ[key]),{cpus[-1]})
    os.sched_setaffinity(0,set(cpus[:3]))
    parent=os.getpid();child=os.fork()
    if child==0:
        try:monitor(out/'parent-telemetry.jsonl',parent)
        finally:os._exit(0)
    rows=[]
    try:
        source=ROOT/load(OLD/'models/manifest-v2.json')['models']['dense-generic-2048']['path']
        for i in range(3):
            started=time.monotonic_ns()
            with source.open() as f:doc=json.load(f)
            doc['model_id']=f'host-probe-{i}'
            dest=out/f'model-{i}.json'
            with dest.open('x') as f:json.dump(doc,f,separators=(',',':'))
            p=subprocess.run([str(OLD/'build-v10/executor'),'check-service',str(dest)],input=b'',capture_output=True,check=True,timeout=90)
            rows.append(dict(index=i,elapsed_ns=time.monotonic_ns()-started,ready=json.loads(p.stdout)['ready']))
            del doc
        put(out/'result.json',dict(status='passed',pinned_control=pin,rows=rows))
    finally:
        os.kill(child,signal.SIGTERM);os.waitpid(child,0)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);p.add_argument('--pin-control',action='store_true')
    a=p.parse_args();run(a.out,a.pin_control)
