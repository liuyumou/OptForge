"""Freeze once, then execute each complete paired block exactly once."""
import argparse
from pathlib import Path
import random
from lp_mixed2_fp4_common import BASE,BINARY,ROOT,load,put,ref,require
from lp_mixed2_fp4_study import execute_session

FREEZE=BASE/'confirmation-freeze.json'
TIERS=['certified-1e-7','certified-1e-9']

def bindings():
    paths=list((ROOT/'research/lp-mixed2-fp4/src').glob('*.rs'))+list((ROOT/'research/lp-mixed2-fp4/cuda').glob('*'))
    paths+=list((ROOT/'research/lp-mixed2-fp4').glob('Cargo.*'))
    paths+=[ROOT/'tools'/('lp_mixed2_fp4_'+x+'.py') for x in ('confirmation','study','transport','common','cpu','budget')]
    paths += [ROOT/'docs/specifications/SPEC-0038-mixed2-fp4.md',ROOT/'docs/decisions/ADR-0071-mixed2-fp4.md',ROOT/'tools/lp_cpu_admission.py']
    return [ref(p) for p in sorted(paths)]

def freeze():
    require(not FREEZE.exists(),'confirmation already frozen')
    require(load(BASE/'schedule-v1/result.json')['status']=='complete','audit pilot incomplete')
    require(load(BASE/'processes-v1/result.json')['status']=='passed','process admission incomplete')
    image=BASE/'build-v8/mixed.cubin';admissions=[]
    for name in ('device','memcheck','racecheck','initcheck','synccheck'):
        p=BASE/(name+'-v6' if name=='device' else name+'-v5')
        require(load(p/'result.json')['status']=='passed' and load(p/'manifest.json')['binary']==ref(BINARY) and load(p/'manifest.json')['image']==ref(image),'admission binding')
        admissions.extend([ref(p/'manifest.json'),ref(p/'result.json')])
    models=load(BASE/'models/manifest-v2.json');families=sorted(models['models']);rng=random.Random(380076);cells=[]
    # Each family has exactly 16 native-first and 16 FP4-first fresh sessions.
    orders={f:rng.sample([0]*16+[1]*16,32) for f in families}
    for block in range(32):
        fs=families.copy();rng.shuffle(fs)
        for f in fs:
            lanes=['native','fp4x2'];
            if orders[f][block]:lanes.reverse()
            for position,lane in enumerate(lanes):
                cells.append(dict(id=f'b{block:02d}-{f}-{lane}',block=block,family=f,lane=lane,position=position,settings=dict(window_max=32 if lane=='native' else 16,fixed_audit=True)))
    put(FREEZE,dict(schema_version=1,stage='frozen-confirmation',binary=ref(BINARY),image=ref(image),sources=bindings(),admissions=admissions,models=ref(BASE/'models/manifest-v2.json'),model_files=models['models'],cells=cells,blocks=32,seed=380076,repeats=3,tiers=TIERS,
        primary='within-block ratio of session medians of complete durable prepared solve time; all families and both tiers retained',
        intervals='exact binomial order-statistic median intervals; Bonferroni across 32 family/tier ratios and 32 paired absolute savings; pointwise GPU/session intervals descriptive',
        sample_size='32 fresh randomized paired blocks, exact 16/16 order balance; independent-session sampling unit, not 3 within-session repeats; first-16/32 sensitivity reported without stopping or exclusion; shared-device temporal independence remains an assumption',
        value='research scope only; report absolute savings, extra setup, six-solve measured session cost and forecast request-count break-even; 1.10 is provisional and not a diagnostic veto or adoption release',
        choice='x2 with 16-update original references removes the observed x2/32 extra audit on generic cases; native uses its cheaper 32 window. Both use fixed maximum-200 audits and cached initial observation. All final accuracy and recovery gates remain original-model.'))

def block(index):
    f=load(FREEZE);require(type(index) is int and 0<=index<f['blocks'],'block range')
    require(f['sources']==bindings() and f['binary']==ref(BINARY),'frozen implementation changed')
    for item in [f['image'],f['models'],*f['admissions'],*f['model_files'].values()]:require(ref(ROOT/item['path'])==item,'frozen input changed')
    out=BASE/f'confirmation-b{index:02d}';out.mkdir(exist_ok=False)
    put(out/'manifest.json',dict(freeze=ref(FREEZE),block=index))
    models=load(ROOT/f['models']['path']);rows=[]
    try:
        for cell in (c for c in f['cells'] if c['block']==index):rows.append(execute_session(out,cell,ROOT/f['image']['path'],models,f['tiers'],f['repeats']))
    except BaseException as e:put(out/'FAILED.json',dict(error=str(e),completed=len(rows)));raise
    put(out/'result.json',dict(status='complete',block=index,sessions=rows))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','block']);p.add_argument('--index',type=int);a=p.parse_args();freeze() if a.action=='freeze' else block(a.index)
