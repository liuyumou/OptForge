"""Versioned development and prospectively frozen complete-cost paired studies."""
import argparse
import json
from pathlib import Path
import random
import statistics
import time
from lp_mixed2_fp4_common import ROOT,BASE,BINARY,load,put,ref,require
from lp_mixed2_fp4_transport import Service


def execute_session(out,cell,image,models,tiers,repeats):
    started=time.monotonic_ns();name=cell['family'];lane=cell['lane'];records=[]
    s=Service(image,ROOT/models['models'][name]['path'],out/(cell['id']+'.log'))
    ready=time.monotonic_ns()-started
    try:
        before=time.monotonic_ns();s.call('prepare',lane=lane);prepare=time.monotonic_ns()-before
        setup=time.monotonic_ns()-started
        for tier in tiers:
            for i in range(repeats):
                dest=out/(cell['id']+f'-{tier}-{i}.json')
                r,elapsed=s.solve_to_file(dest,lane=lane,tier=tier,**{**models['settings'],**cell.get('settings',{})})
                require(r['certified']==(name!='infinite-bound-refusal'),'certificate outcome differs')
                require(r['physical']==sum(r['attempted'].values()) and elapsed>=r['solve_ns'],'physical/complete cost')
                records.append(dict(tier=tier,repeat=i,complete_ns=elapsed,result=ref(dest),physical=r['physical'],logical=r['logical'],gpu_us=r['gpu_us'],final_lane=r['final_lane'],costs_ns=r['costs_ns'],certified=r['certified'],recoveries=[e for e in r['events'] if e['kind']=='recovery']))
    finally:
        end=time.monotonic_ns();s.close();teardown=time.monotonic_ns()-end
    row=dict(**cell,ready_ns=ready,prepare_ns=prepare,setup_ns=setup,teardown_ns=teardown,complete_session_ns=time.monotonic_ns()-started,records=records)
    put(out/(cell['id']+'.session.json'),row)
    print(dict(family=name,lane=lane,median_ms=statistics.median(x['complete_ns'] for x in records)/1e6,gpu_ms=statistics.median(x['gpu_us'] for x in records)/1000,physical=sorted(set(x['physical'] for x in records)),final_lanes=sorted(set(x['final_lane'] for x in records)),setup_ms=setup/1e6),flush=True)
    return row


def development(out,image,admission,blocks=3,sanitizer_version="v1"):
    out=Path(out);out.mkdir(exist_ok=False);image=Path(image)
    models=load(BASE/'models/manifest.json');admission=Path(admission)
    require(load(admission/'result.json')['status']=='passed','device admission')
    require(load(admission/'manifest.json')['binary']==ref(BINARY) and load(admission/'manifest.json')['image']==ref(image),'admitted executable/image')
    for name in ('memcheck','racecheck','initcheck','synccheck'):
        p=BASE/(name+'-'+sanitizer_version);require(load(p/'result.json')['status']=='passed' and load(p/'manifest.json')['image']==ref(image),'four-sanitizer admission')
    families=('dense-generic-128','dense-generic-256','dense-generic-512','dense-generic-1024','dense-generic-2048','irregular-tail-33')
    rng=random.Random(380071);cells=[]
    for block in range(blocks):
        fs=list(families);rng.shuffle(fs)
        for f in fs:
            lanes=['native','fp4x2','fp4x4'];rng.shuffle(lanes)
            for position,lane in enumerate(lanes):cells.append(dict(id=f'b{block}-{f}-{lane}',block=block,family=f,lane=lane,position=position))
    put(out/'manifest.json',dict(stage='exploratory-development',binary=ref(BINARY),image=ref(image),models=ref(BASE/'models/manifest.json'),cells=cells,blocks=blocks,seed=380071,admission=ref(admission/'result.json'),repeats=3,tiers=['certified-1e-9']))
    rows=[]
    try:
        for cell in cells:rows.append(execute_session(out,cell,image,models,['certified-1e-9'],3))
    except BaseException as e:put(out/'FAILED.json',dict(error=str(e),completed=len(rows)));raise
    put(out/'result.json',dict(status='complete',sessions=rows))

def windows(out,image,admission,sanitizer_version):
    out=Path(out);out.mkdir(exist_ok=False);image=Path(image);admission=Path(admission)
    require(load(admission/'result.json')['status']=='passed' and load(admission/'manifest.json')['image']==ref(image) and load(admission/'manifest.json')['binary']==ref(BINARY),'window admission')
    for name in ('memcheck','racecheck','initcheck','synccheck'):
        p=BASE/(name+'-'+sanitizer_version);require(load(p/'result.json')['status']=='passed' and load(p/'manifest.json')['image']==ref(image),'window sanitizer admission')
    models=load(BASE/'models/manifest-v2.json');rng=random.Random(380074);cells=[]
    for block in range(2):
        families=['dense-generic-512','dense-generic-1024','dense-generic-2048','dense-coupled-1024','dense-coupled-2048'];rng.shuffle(families)
        for family in families:
            cases=[(lane,window) for lane in ('native','fp4x2','fp4x4') for window in (8,16,32)];rng.shuffle(cases)
            for position,(lane,window) in enumerate(cases):cells.append(dict(id=f'b{block}-{family}-{lane}-w{window}',block=block,family=family,lane=lane,position=position,settings=dict(window_max=window)))
    put(out/'manifest.json',dict(stage='exploratory-window-and-larger-coupling',binary=ref(BINARY),image=ref(image),models=ref(BASE/'models/manifest-v2.json'),cells=cells,blocks=2,seed=380074,repeats=3,tiers=['certified-1e-9']))
    rows=[]
    try:
        for cell in cells:rows.append(execute_session(out,cell,image,models,['certified-1e-9'],3))
    except BaseException as e:put(out/'FAILED.json',dict(error=str(e),completed=len(rows)));raise
    put(out/'result.json',dict(status='complete',sessions=rows))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out');p.add_argument('--image',required=True);p.add_argument('--admission',required=True);p.add_argument('--blocks',type=int,default=3);p.add_argument('--windows',action='store_true');p.add_argument('--sanitizer-version',default='v1');a=p.parse_args();windows(a.out,a.image,a.admission,a.sanitizer_version) if a.windows else development(a.out,a.image,a.admission,a.blocks,a.sanitizer_version)
