"""Coverage-first selection and simultaneous held-out inference; CPU-only replay."""
import argparse
import math
import statistics
from lp_gpup9_common import BASE, ROOT, configs, load, put, ref, checked, require
from lp_gpup9_protocol import select
from lp_mixed2_fp4_analysis import interval


def rows(stage, verify=True):
    freeze=load(BASE/f'{stage}-freeze.json');found=[];missing=[];verified_models=set()
    for cell in freeze['cells']:
        path=BASE/stage/f"b{cell['block']:02d}"/(cell['id']+'.session.json')
        if not path.exists():missing.append(cell);continue
        row=load(path)
        from lp_gpup9_schema import validate_session
        validate_session(row)
        require(all(row[k]==v for k,v in cell.items()),'cell metadata mismatch')
        require(len(row['records'])==row['count'],'partial session')
        require(row['complete_session_ns']>=row['setup_ns']+row['teardown_ns']+sum(x['complete_ns'] for x in row['records']),'lifecycle partitions overlap')
        for index,record in enumerate(row['records']):
            require(record['index']==index and record['scenario']==(index%4 if cell['endpoint']=='prepared' else 0),'request order')
            if verify:
                r=load(checked(record['result']))
                model_key=(record['model']['path'],record['model']['sha256'])
                if model_key not in verified_models:
                    checked(record['model']);verified_models.add(model_key)
                for key in ['certified','physical','logical','attempted','gpu_us','costs_ns','final_lane']:
                    require(record[key]==r[key],'response summary differs')
                require(r['model_sha256']==record['model']['sha256'],'model identity')
                require(r['solve_ns']==sum(r['costs_ns'].values())<=record['solve_ns']<=record['complete_ns'],'solve costs')
        found.append(row)
    return freeze,found,missing


def useful(row):
    return all(r['certified'] for r in row['records']) and any(
        sum(v for k,v in r['attempted'].items() if k in ('34','36'))>0 for r in row['records'])


def paired(a,b,expected,alpha=.05/24):
    require(len(a)==len(b)<=expected,'invalid paired coverage')
    require(all(type(r['complete_session_ns']) is int and r['complete_session_ns']>0 for r in a+b),'invalid paired time')
    ratios=[x['complete_session_ns']/y['complete_session_ns'] for x,y in zip(a,b)]
    saved=[(x['complete_session_ns']-y['complete_session_ns'])/1e6 for x,y in zip(a,b)]
    complete=len(a)==len(b)==expected
    certified=all(all(r['certified'] for r in row['records']) for row in a+b)
    fp4=all(useful(row) for row in b)
    ri=interval(ratios,alpha) if ratios else None
    si=interval(saved,alpha) if saved else None
    passed=bool(complete and certified and fp4 and ri and ri['lower'] is not None and ri['lower']>1 and si['lower']>10)
    return dict(pairs=len(a),missing_pairs=expected-len(a),certified=certified,useful_fp4=fp4,
                ratio=ri,saved_ms=si,scoped_pass=passed,
                native_ms=statistics.median(x['complete_session_ns']/1e6 for x in a) if a else None,
                fp4_ms=statistics.median(x['complete_session_ns']/1e6 for x in b) if b else None)


def assess(f,rs,missing):
    roster={c['id']:c for c in f['cells']}
    require(len(roster)==len(f['cells']) and len({r['id'] for r in rs})==len(rs),'duplicate trial')
    require({r['id'] for r in rs}|{c['id'] for c in missing}==set(roster),'coverage roster')
    require(not ({r['id'] for r in rs}&{c['id'] for c in missing}),'overlapping coverage')
    for row in rs:require(all(row[k]==v for k,v in roster[row['id']].items()),'analysis cell differs')
    index={(r['family'],r['endpoint'],r['block'],f['configurations'][r['config']]['lane']):r for r in rs}
    comparisons=[]
    for family,endpoint in sorted({(c['family'],c['endpoint']) for c in f['cells']}):
        pairs=[]
        for block in range(f['blocks']):
            a=index.get((family,endpoint,block,'native'));b=index.get((family,endpoint,block,'fp4x2'))
            if a is not None and b is not None:pairs.append((a,b))
        result=dict(family=family,endpoint=endpoint,**paired([a for a,b in pairs],[b for a,b in pairs],f['blocks']))
        result['orders']={str(position):paired([a for a,b in pairs if a['position']==position],
            [b for a,b in pairs if a['position']==position],f['blocks']//2) for position in [0,1]}
        result['costs']={}
        for lane,items in [('native',[a for a,b in pairs]),('fp4x2',[b for a,b in pairs])]:
            result['costs'][lane]=dict(sessions=len(items),setup_ns=sum(x['setup_ns'] for x in items),
                teardown_ns=sum(x['teardown_ns'] for x in items),total_ns=sum(x['complete_session_ns'] for x in items),
                work=sorted({r['physical'] for x in items for r in x['records']}),
                recoveries=sum(len(r['recoveries']) for x in items for r in x['records']),
                partitions_ns={key:sum(r['costs_ns'].get(key,0) for x in items for r in x['records'])
                    for key in sorted({key for x in items for r in x['records'] for key in r['costs_ns']})})
        comparisons.append(result)
    k=interval(list(range(f['blocks'])),.05/24)['rank'];n=f['blocks']
    return dict(schema_version=1,kind='gpup9-analysis',planned=len(f['cells']),complete=len(rs),
        missing=missing,solves=sum(len(r['records']) for r in rs),
        certificates=sum(x['certified'] for r in rs for x in r['records']),comparisons=comparisons,
        status='incomplete' if missing else 'complete',rank=k,
        sign_power={str(p):sum(math.comb(n,i)*p**i*(1-p)**(n-i) for i in range(n-k+1,n+1)) for p in [.75,.8,.85,.9,.95]},
        public_adoption=False)


def screening_effects(f,rs):
    indexed={(r['family'],r['block'],r['config']):r['complete_session_ns'] for r in rs}
    effects=[]
    def cost(family,block,lane,window,scale):return indexed[(family,block,f'{lane}-w{window}-s{scale}')]
    for family in sorted({r['family'] for r in rs}):
        for block in range(f['blocks']):
            lane={f'w{w}-s{s}':cost(family,block,'native',w,s)/cost(family,block,'fp4x2',w,s) for w in [16,32] for s in [0,1]}
            window={f'{l}-s{s}':cost(family,block,l,32,s)/cost(family,block,l,16,s) for l in ['native','fp4x2'] for s in [0,1]}
            scaling={f'{l}-w{w}':cost(family,block,l,w,0)/cost(family,block,l,w,1) for l in ['native','fp4x2'] for w in [16,32]}
            effects.append(dict(family=family,block=block,precision=lane,window=window,scaling=scaling,
                precision_by_window={str(s):lane[f'w16-s{s}']/lane[f'w32-s{s}'] for s in [0,1]},
                precision_by_scaling={str(w):lane[f'w{w}-s1']/lane[f'w{w}-s0'] for w in [16,32]}))
    return dict(inferential=False,rows=effects)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['screening','validation','holdout']);a=p.parse_args()
    f,rs,missing=rows(a.stage)
    if a.stage=='holdout':put(BASE/'analysis.json',assess(f,rs,missing))
    else:
        require(not missing,'missing evidence stops selection')
        value=select(a.stage,rs,f['cells'],f['configurations'])
        value.update(freeze=ref(BASE/f'{a.stage}-freeze.json'),sessions=[ref(BASE/a.stage/f"b{r['block']:02d}"/(r['id']+'.session.json')) for r in rs])
        put(BASE/f'{a.stage}-selection.json',value)
        if a.stage=='screening':put(BASE/'screening-effects.json',screening_effects(f,rs))
        print(value['selected'],flush=True)
