"""Frozen eight-block prepared attribution and fixed-operand product cohorts."""
import argparse
import json
import os
from pathlib import Path
import random
import subprocess
import time
from lp_mixed2_pilot_common import ROOT,BASE,BINARY,IMAGE,TARGETS,load,put,ref,require
from lp_mixed2_pilot_device import prior,product,matrix_input
from lp_mixed2_pilot_transport import Service
from lp_mixed2_pilot_validate import profile,exact_solve,check_guard
from lp_delivery2_study import PARENT
STUDY=BASE/'study-v1'


def freeze():
    STUDY.mkdir(parents=True,exist_ok=False);m=load(PARENT/'manifest.json')
    admissions=[BASE/'cpu-v1/result.json',BASE/'device-v1/result.json']+[BASE/(s+('-v2' if s=='memcheck' else '-v1')+'/result.json') for s in ('memcheck','racecheck','initcheck','synccheck')]
    for p in admissions:require(load(p)['status']=='passed','missing admission '+str(p))
    require(load(BASE/'resources/cpu-native-v1.settlement.json')['status']=='passed','full native gate')
    for p in admissions[1:]:require(load(p.parent/'manifest.json')['image']==ref(IMAGE),'admitted image changed')
    rng=random.Random(370070);orders={f:rng.sample([0]*4+[1]*4,8) for f in m['models']}
    sessions=[];products=[];rproduct=random.Random(370071)
    for block in range(8):
        families=list(m['models']);rng.shuffle(families)
        for family in families:
            variants=('control','profile') if orders[family][block]==0 else ('profile','control')
            for position,variant in enumerate(variants):sessions.append(dict(id=f'b{block}-{family}-{variant}',block=block,family=family,variant=variant,position=position,original=prior(family)))
        pairs=[(f,t) for f in (*TARGETS,'irregular-tail-33') for t in (False,True)];rproduct.shuffle(pairs)
        for family,tr in pairs:
            modes=['fp64','fp32','guard'];rproduct.shuffle(modes)
            for mode in modes:products.append(dict(id=f'b{block}-{family}-t{int(tr)}-{mode}',block=block,family=family,transpose=tr,mode=mode))
    inputs={}
    for family in (*TARGETS,'irregular-tail-33'):
        for tr in (False,True):
            p=STUDY/f'{family}-t{int(tr)}.json';put(p,dict(**matrix_input(ROOT/m['models'][family]['path'],tr),count=128));inputs[family+f'-t{int(tr)}']=ref(p)
    sources=[ref(p) for p in sorted((ROOT/'research/lp-mixed2-pilot').rglob('*')) if p.is_file() and 'target' not in p.parts]
    sources += [ref(p) for p in sorted((ROOT/'tools').glob('lp_mixed2_pilot*.py')) if not p.name.endswith(('_analysis.py','_report.py'))]
    sources += m['sources']
    sources += [ref(ROOT/'docs/specifications/SPEC-0037-mixed2-pilot.md'),ref(ROOT/'docs/decisions/ADR-0070-mixed2-pilot.md')]
    put(STUDY/'manifest.json',dict(binary=ref(BINARY),image=ref(IMAGE),models=m['models'],settings=m['settings'],sources=sources,admissions=[ref(p) for p in admissions],inputs=inputs,sessions=sessions,products=products,seed=370070,product_seed=370071,blocks=8,solves_per_session=3,automatic_retry=False))
    print(dict(frozen_sessions=len(sessions),solves=3*len(sessions),product_cells=len(products)),flush=True)


def execute(block):
    m=load(STUDY/'manifest.json');require(block in range(8),'invalid block')
    for binding in [m['binary'],m['image'],*m['models'].values(),*m['sources'],*m['inputs'].values(),*m['admissions']]:require(ref(ROOT/binding['path'])==binding,'frozen source/input changed')
    out=STUDY/f'block-{block}';out.mkdir(exist_ok=False);put(out/'STARTED.json',dict(manifest=ref(STUDY/'manifest.json'),block=block))
    rows=[];products=[];active=None
    try:
        for cell in [c for c in m['sessions'] if c['block']==block]:
            active=cell;start=time.monotonic_ns();log=out/(cell['id']+'.log')
            service=Service(IMAGE,ROOT/m['models'][cell['family']]['path'],log,variant=cell['variant'])
            ready=time.monotonic_ns()-start
            try:
                prep_start=time.monotonic_ns();prep=service.call('prepare',lane='nativefast');prepare_ns=time.monotonic_ns()-prep_start
                setup_ns=time.monotonic_ns()-start;records=[]
                for i in range(3):
                    dest=out/(cell['id']+f'-s{i}.json')
                    result,elapsed=service.solve_to_file(dest,lane='nativefast',tier='certified-1e-9',**m['settings'])
                    exact_solve(result,load(ROOT/cell['original']['path']),m['binary'],m['image'])
                    require(elapsed>=result['solve_ns'],'complete boundary')
                    records.append(dict(index=i,complete_ns=elapsed,result=ref(dest)))
            finally:
                end=time.monotonic_ns();service.close();teardown_ns=time.monotonic_ns()-end
            lines=[json.loads(v) for v in log.read_text().splitlines()];attribution=profile(lines)
            row=dict(**cell,setup_ns=setup_ns,ready_ns=ready,prepare_ns=prepare_ns,prepare=prep,teardown_ns=teardown_ns,complete_session_ns=time.monotonic_ns()-start,records=records,profile=attribution,profile_log=ref(log))
            rows.append(row);put(out/(cell['id']+'.session.json'),row)
        grouped={}
        for cell in [c for c in m['products'] if c['block']==block]:
            active=cell;inp=load(ROOT/m['inputs'][cell['family']+f"-t{int(cell['transpose'])}"]['path'])
            result=product(dict(**inp,mode=cell['mode']),out,cell['id']);row=dict(**cell,**result);products.append(row)
            grouped.setdefault((cell['family'],cell['transpose']),{})[cell['mode']]=row
        guards=[]
        for (family,tr),group in grouped.items():
            inp=load(ROOT/group['fp32']['input']['path']);check=check_guard(inp,group['fp32']['value']['values'],group['guard']['value']['values'])
            guards.append(dict(family=family,transpose=tr,**check))
    except BaseException as e:
        put(out/'FAILED.json',dict(error=str(e),active=active,sessions=rows,products=products));raise
    put(out/'result.json',dict(status='complete',block=block,sessions=rows,products=products,guards=guards))
    print(dict(block=block,sessions=len(rows),solves=sum(len(r['records']) for r in rows),products=len(products)),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','run']);p.add_argument('--block',type=int);a=p.parse_args();freeze() if a.action=='freeze' else execute(a.block)
