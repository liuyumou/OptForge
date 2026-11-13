"""Prospective audit-cost pilot on the admitted implementation."""
import argparse
from pathlib import Path
import random
from lp_mixed2_fp4_common import BASE,BINARY,ROOT,load,put,ref,require
from lp_mixed2_fp4_study import execute_session

def run(out):
    out=Path(out);out.mkdir(exist_ok=False);image=BASE/'build-v8/mixed.cubin'
    for name in ('device','memcheck','racecheck','initcheck','synccheck'):
        p=BASE/(name+'-v6' if name=='device' else name+'-v5')
        require(load(p/'result.json')['status']=='passed' and load(p/'manifest.json')['binary']==ref(BINARY) and load(p/'manifest.json')['image']==ref(image),'source-bound admission')
    models=load(BASE/'models/manifest-v2.json');rng=random.Random(380075);cells=[]
    for block in range(2):
        families=['dense-generic-512','dense-generic-1024','dense-generic-2048','dense-coupled-1024','dense-coupled-2048'];rng.shuffle(families)
        for family in families:
            cases=[(lane,fixed) for lane in ('native','fp4x2') for fixed in (False,True)];rng.shuffle(cases)
            for position,(lane,fixed) in enumerate(cases):
                cells.append(dict(id=f'b{block}-{family}-{lane}-fixed{int(fixed)}',block=block,family=family,lane=lane,position=position,settings=dict(window_max=32 if lane=='native' else 16,fixed_audit=fixed)))
    put(out/'manifest.json',dict(stage='exploratory-audit-cost',binary=ref(BINARY),image=ref(image),models=ref(BASE/'models/manifest-v2.json'),cells=cells,blocks=2,seed=380075,repeats=3,tiers=['certified-1e-9']))
    rows=[]
    try:
        for cell in cells:rows.append(execute_session(out,cell,image,models,['certified-1e-9'],3))
    except BaseException as e:put(out/'FAILED.json',dict(error=str(e),completed=len(rows)));raise
    put(out/'result.json',dict(status='complete',sessions=rows))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out');run(p.parse_args().out)
