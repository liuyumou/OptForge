"""Source-bound exact CPU optimization study with complete session accounting."""
import argparse
import hashlib
import json
import math
import random
import subprocess
import sys
from pathlib import Path
from lp_checker2_common import BASE, ROOT, BINARY as BASELINE_BINARY, IMAGE, PRIOR, load, put, ref, require
from lp_mixed2_confirm2_confirmation import FAMILIES, TIERS, environment_snapshot
from lp_mixed2_fp4_analysis import interval
from lp_mixed2_reuse_study import execute_session
from lp_mixed2_reuse_admit import numerical
import lp_mixed2_reuse_transport as transport

CANDIDATE=BASE/'build-v5/executor'
MODELS=PRIOR/'models/manifest.json'
VARIANTS={'baseline':BASELINE_BINARY,'candidate':CANDIDATE}

def run_cell(out, cell, count):
    transport.BINARY=VARIANTS[cell['variant']]
    image_digest=ref(IMAGE)['sha256'];binary_digest=ref(transport.BINARY)['sha256']
    row=execute_session(out,cell,load(MODELS),count=count)
    for record in row['records']:
        old=PRIOR/('scenario-v2-'+cell['family'])/(f"{cell['family']}-{cell['tier']}-{cell['lane']}-r{record['scenario']:02d}.json")
        response=load(ROOT/record['result']['path'])
        require(response['image_sha256']==image_digest and response['checker_binary_sha256']==binary_digest,'response executable/image binding')
        require(numerical(response)==numerical(load(old)), 'numerical trajectory differs')
    return row

def cells(blocks,seed):
    rng=random.Random(seed)
    pairs=[(f,t,l) for f in FAMILIES for t in TIERS for l in ['native','fp4x2']]
    orders={p:rng.sample([0]*(blocks//2)+[1]*(blocks//2),blocks) for p in pairs}
    result=[]
    for block in range(blocks):
        order=pairs.copy();rng.shuffle(order)
        for family,tier,lane in order:
            variants=['baseline','candidate']
            if orders[family,tier,lane][block]: variants.reverse()
            for position,variant in enumerate(variants):
                result.append(dict(id=f'b{block:02d}-{family}-{tier}-{lane}-{variant}',block=block,
                    family=family,tier=tier,lane=lane,variant=variant,position=position))
    return result

def admission(name,count):
    out=BASE/name;out.mkdir(exist_ok=False)
    manifest=dict(binaries={k:ref(v) for k,v in VARIANTS.items()},image=ref(IMAGE),models=ref(MODELS),
                  cells=cells(2,420075)[:32],count=count,environment=environment_snapshot(),scientific_confirmation=False)
    put(out/'manifest.json',manifest)
    rows=[run_cell(out,c,count) for c in manifest['cells']]
    put(out/'result.json',dict(status='passed',sessions=rows,exact_historical_comparisons=len(rows)*count,
                             environment=environment_snapshot()))

def bindings():
    paths=list((ROOT/'research/lp-mixed2-checker2/src').glob('*.rs'))+list((ROOT/'research/lp-mixed2-checker2').glob('Cargo.*'))
    paths+=list((ROOT/'tools').glob('lp_checker2*.py'))
    paths += [ROOT/'tools'/p for p in ['lp_mixed2_reuse_study.py','lp_mixed2_reuse_transport.py','lp_mixed2_reuse_admit.py',
              'lp_mixed2_reuse_place.py','lp_confirmation2_supervisor.py','lp_cpu_admission.py']]
    paths += list((ROOT/'crates').rglob('*.rs'))+list((ROOT/'crates').glob('*/Cargo.toml'))
    for directory in ['lp-fp4-checker','lp-fp4-accel','lp-tensor-expanded-device/cuda-sys']:
        paths += list((ROOT/'research'/directory/'src').glob('*.rs'))
        paths += list((ROOT/'research'/directory).glob('Cargo.*'))
    paths += [BASE/'selection-final.json',BASE/'cpu-vector-admission.json']
    paths += [ROOT/'research/lp-mixed2-checker2/README.md',ROOT/'research/lp-mixed2-checker2/deny.toml',ROOT/'tools/check_checker2_cpu.sh',ROOT/'tests/integration/test_lp_checker2.py']
    paths += [ROOT/'rust-toolchain.toml',ROOT/'Cargo.lock',ROOT/'Cargo.toml']
    paths += [ROOT/'docs/specifications/SPEC-0042-checker2.md', ROOT/'docs/decisions/ADR-0075-checker2.md']
    return [ref(p) for p in sorted(paths)]

def freeze():
    admissions=[]
    for name in ['cpu-optimized','native-optimized','device-optimized','smoke-optimized','pilot-optimized','serial-optimized']:
        path=BASE/'resources'/(name+'.settlement.json');s=load(path)
        require(s['status']=='passed' and not s['overrun'],'admission incomplete '+name)
        resource=load(ROOT/s['resource']['path']);require(resource['guardian_cleanup']['empty'] and resource['result']['cleanup']['empty'],'admission cleanup')
        admissions.append(ref(path))
    require(load(BASE/'analysis-admission.json')['status']=='passed','analysis admission')
    require(load(BASE/'cpu-optimized/result.json')['binary']==ref(CANDIDATE),'CPU admitted candidate differs')
    require(load(BASE/'device-admission-optimized.json')['binary']==ref(CANDIDATE),'device admitted candidate differs')
    admissions += [ref(BASE/p) for p in ['cpu-optimized/result.json','device-admission-optimized.json','smoke-optimized/result.json','pilot-optimized/result.json','serial-optimized/result.json','analysis-admission.json']]
    require(load(BASE/'smoke-optimized/result.json')['exact_historical_comparisons']==128,'smoke coverage')
    pilot=load(BASE/'pilot-optimized/result.json');require(pilot['exact_historical_comparisons']==1024,'pilot coverage')
    projected=sum(r['complete_session_ns'] for r in pilot['sessions'])/1e9*16
    require(projected*1.5 < min(8000,16*480),'cohort cannot fit CPU confirmation cap')
    ci=interval(list(range(16)),.05/32)
    put(BASE/'freeze.json',dict(blocks=16,count=32,seed=420075,cells=cells(16,420075),
        binaries={k:ref(v) for k,v in VARIANTS.items()},image=ref(IMAGE),models=ref(MODELS),sources=bindings(),admissions=admissions,
        block_seconds=480,projected_seconds=projected,statistics=dict(alpha=.05/32,endpoints=32,rank=ci['rank'],coverage=ci['coverage'],positive_blocks_needed=17-ci['rank'],sign_power={str(p):sum(math.comb(16,i)*p**i*(1-p)**(16-i) for i in range(17-ci['rank'],17)) for p in [.75,.8,.85,.9,.95]}),
        value=dict(ratio_lower=1.,saved_ms_lower=10.,provisional=1.10),no_retry=True,
        endpoint='complete 32-request session including preparation, outputs and teardown'))

def block(index):
    f=load(BASE/'freeze.json')
    for item in f['sources']+list(f['binaries'].values())+[f['image'],f['models']]+f['admissions']:
        require(ref(ROOT/item['path'])==item,'frozen identity changed')
    out=BASE/'confirmation'/f'b{index:02d}';out.mkdir(parents=True,exist_ok=False)
    rows=[];put(out/'environment-before.json',environment_snapshot())
    for cell in f['cells']:
        if cell['block']==index:rows.append(run_cell(out,cell,f['count']))
    put(out/'result.json',dict(status='passed',sessions=rows,environment=environment_snapshot()))

def run():
    f=load(BASE/'freeze.json')
    require(not list((BASE/'resources').glob('confirmation-b*.reservation.json')),'cohort already started')
    for index in range(f['blocks']):
        identity=f'confirmation-b{index:02d}'
        p=subprocess.run([sys.executable,'tools/lp_checker2_budget.py','--id',identity,'--phase','confirmation',
            '--seconds',str(f['block_seconds']),'--gpu','--',sys.executable,'tools/lp_mixed2_reuse_place.py',
            sys.executable,__file__,'block','--index',str(index)],cwd=ROOT)
        s=load(BASE/'resources'/(identity+'.settlement.json'));require(not s['overrun'],'overrun stops execution')
        r=load(ROOT/s['resource']['path']);require(r['guardian_cleanup']['empty'] and r['result']['cleanup']['empty'],'cleanup incomplete')
        require(p.returncode in (0,2),'unexpected launcher')
        print(dict(block=index+1,total=f['blocks'],status=s['status'],reason=r['result']['reason']),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['smoke','pilot','freeze','block','run']);p.add_argument('--index',type=int)
    a=p.parse_args()
    if a.command in ['smoke','pilot']:admission(a.command+'-optimized',4 if a.command=='smoke' else 32)
    elif a.command=='freeze':freeze()
    elif a.command=='block':block(a.index)
    else:run()
