"""Versioned EOF-driven cold delivery; original formal cohort remains immutable."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
from lp_fp4_accel_common import ROOT,BASE,put,ref,load,require
from lp_fp4_accel_run import BINARY

LANES=('nativefast','gridfp4x2','auto')


def deliver(command,dest,log,timeout):
    start=time.monotonic_ns()
    # Pipes let communicate wait on EOF readiness instead of waitpid's 50 ms
    # timeout polling. Include process exit and all durable response/log writes.
    result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
    for path,payload in ((dest,result.stdout),(log,result.stderr)):
        with Path(path).open('xb') as stream:
            stream.write(payload);stream.flush();os.fsync(stream.fileno())
    elapsed=time.monotonic_ns()-start
    result.check_returncode();return elapsed


def check_transport():
    with tempfile.TemporaryDirectory() as tmp:
        p=Path(tmp)
        deliver(['python3','-c','import sys;sys.stdout.buffer.write(b"exact\\n");sys.stderr.buffer.write(b"log\\n")'],p/'out',p/'err',2)
        require((p/'out').read_bytes()==b'exact\n' and (p/'err').read_bytes()==b'log\n','delivery bytes')
        try:deliver(['python3','-c','import time;time.sleep(10)'],p/'timeout',p/'terr',.05)
        except subprocess.TimeoutExpired:pass
        else:raise ValueError('deadline ignored')
        require(not (p/'timeout').exists(),'timeout became completed output')
    print('EOF delivery bytes and deadline pass',flush=True)


def freeze(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    parent=load(BASE/'study-v1/manifest.json');require(load(BASE/'study-v1/result.json')['status']=='complete','parent incomplete')
    for r in [parent['image'],parent['binary'],*parent['sources']]:require(ref(ROOT/r['path'])==r,'changed numerical source')
    cells=[c for c in parent['cells'] if c['lifecycle']=='cold' and c['lane'] in LANES]
    put(out/'manifest.json',dict(kind='lp-fp4-accel-cold-eof-v1',parent=ref(BASE/'study-v1/manifest.json'),image=parent['image'],binary=parent['binary'],
        source=ref(Path(__file__)),cells=cells,settings=parent['settings'],models=parent['models'],lanes=LANES,
        protocol_change='EOF-driven process completion, exact response and log durable write; same numerical sources/settings/tiers and retention criteria; separate new cohort, no old cell retry',
        automatic_retry=False))
    print(dict(frozen=True,cells=len(cells)),flush=True)


def execute(out):
    out=Path(out);m=load(out/'manifest.json');parent=load(ROOT/m['parent']['path'])
    for r in [m['parent'],m['source'],m['image'],m['binary'],*parent['sources'],*m['models'].values()]:require(ref(ROOT/r['path'])==r,'changed frozen input')
    require(not (out/'STARTED.json').exists(),'cohort already started');put(out/'STARTED.json',dict(manifest=ref(out/'manifest.json')))
    rows=[]
    try:
        for cell in m['cells']:
            request=BASE/'study-v1'/(cell['id']+'.request.json');dest=out/(cell['id']+'.json')
            expected=dict(op='solve',lane=cell['lane'],tier=cell['tier'],**m['settings']);require(load(request)==expected,'request settings')
            ns=deliver([str(BINARY),'once',str(ROOT/m['image']['path']),str(ROOT/m['models'][cell['family']]['path']),str(request)],dest,out/(cell['id']+'.stderr'),35)
            r=load(dest);old=load(BASE/'study-v1'/(cell['id']+'.json'))
            require(r['endpoint']==old['endpoint'] and r['certificate']==old['certificate'] and r['physical']==old['physical'],'changed endpoint/work')
            require(sum(r['costs_ns'].values())==r['solve_ns'] and ns>=r['solve_ns'],'cost accounting')
            rows.append(dict(**cell,status=r['status'],certified=r['certified'],complete_ns=ns,gpu_us=r['gpu_us'],physical=r['physical'],solve_ns=r['solve_ns'],costs_ns=r['costs_ns'],result=ref(dest),original_endpoint_receipt=ref(BASE/'study-v1'/(cell['id']+'.json'))))
            if len(rows)%60==0:print(dict(completed=len(rows),planned=len(m['cells'])),flush=True)
    except Exception as e:
        put(out/'partial.json',dict(status='failed',error=str(e),rows=rows,failed_cell=cell,unexecuted=[c for c in m['cells'] if c['id'] not in {r['id'] for r in rows} and c['id']!=cell['id']]))
        raise
    put(out/'result.json',dict(status='complete',manifest=ref(out/'manifest.json'),rows=rows,all_endpoint_receipts_and_work_identical=True))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['test','freeze','run']);p.add_argument('--output');a=p.parse_args()
    if a.action=='test':check_transport()
    elif a.action=='freeze':freeze(Path(a.output))
    else:execute(Path(a.output))
