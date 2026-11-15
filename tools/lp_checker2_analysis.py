"""Paired complete-cost analysis retaining missing cells and all unfavorable results."""
import argparse
import statistics
from lp_checker2_common import BASE, ROOT, load, put, ref, require
from lp_mixed2_fp4_analysis import interval

def summarize(pairs, expected=16):
    ratios=[a['complete_session_ns']/b['complete_session_ns'] for a,b in pairs]
    saved=[(a['complete_session_ns']-b['complete_session_ns'])/1e6 for a,b in pairs]
    if not pairs:return dict(complete_pairs=0,missing_pairs=expected,scoped_pass=False,provisional_pass=False)
    r=interval(ratios,.05/32);s=interval(saved,.05/32)
    complete=len(pairs)==expected
    return dict(complete_pairs=len(pairs),missing_pairs=expected-len(pairs),speedup=r,saved_ms=s,
                scoped_pass=complete and r['lower'] is not None and r['lower']>1 and s['lower'] is not None and s['lower']>10,
                provisional_pass=complete and r['lower'] is not None and r['lower']>=1.10 and s['lower'] is not None and s['lower']>10,
                baseline_session_ms=statistics.median(a['complete_session_ns']/1e6 for a,b in pairs),
                candidate_session_ms=statistics.median(b['complete_session_ns']/1e6 for a,b in pairs))

def analyze():
    f=load(BASE/'freeze.json');rows={};missing=[]
    for cell in f['cells']:
        path=BASE/'confirmation'/f"b{cell['block']:02d}"/(cell['id']+'.session.json')
        if path.exists():
            r=load(path);require(r['count']==f['count'] and len(r['records'])==f['count'],'partial session receipt')
            for record in r['records']:require(ref(ROOT/record['result']['path'])==record['result'],'response bytes changed')
            rows[cell['id']]=r
        else:missing.append(cell)
    complete_paths={record['result']['path'] for row in rows.values() for record in row['records']}
    partial=[ref(p) for p in sorted((BASE/'confirmation').glob('b*/*-r[0-9][0-9].json'))
             if str(p.relative_to(ROOT)) not in complete_paths]
    failures=[load(p) for p in sorted((BASE/'resources').glob('confirmation-b*.settlement.json')) if load(p)['status']!='passed']
    return assess(f,rows,missing,ref(BASE/'freeze.json'),partial,failures)

def assess(f,rows,missing,freeze_ref,partial,failures):
    roster={c['id']:c for c in f['cells']}
    require(set(rows)<=set(roster),'unexpected session')
    require({c['id'] for c in missing}==set(roster)-set(rows),'missing-cell ledger differs')
    for identity,row in rows.items():
        require(all(row[k]==v for k,v in roster[identity].items()),'session metadata differs from freeze')
        require(row['count']==f['count']==len(row['records']),'session count')
        require(row['complete_session_ns']>0 and row['setup_ns']>=0 and row['teardown_ns']>=0,'invalid lifecycle time')
        require(row['setup_ns']+row['teardown_ns']+sum(r['complete_ns'] for r in row['records'])<=row['complete_session_ns'],'overlapping lifecycle partitions')
        for i,record in enumerate(row['records']):
            require(record['index']==i and record['scenario']==i%4 and record['complete_ns']>0,'request order/time differs')
    keys=sorted({(c['family'],c['tier'],c['lane']) for c in f['cells']});results=[]
    for family,tier,lane in keys:
        pairs=[]
        for block in range(f['blocks']):
            prefix=f'b{block:02d}-{family}-{tier}-{lane}-'
            if prefix+'baseline' in rows and prefix+'candidate' in rows:pairs.append((rows[prefix+'baseline'],rows[prefix+'candidate']))
        result=dict(family=family,tier=tier,lane=lane,**summarize(pairs,f['blocks']))
        result['order_sensitivity']={str(first):summarize([(a,b) for a,b in pairs if a['position']==first],f['blocks']//2) for first in [0,1]}
        result['partitions']={}
        for index,variant in enumerate(['baseline','candidate']):
            sessions=[p[index] for p in pairs]
            if not sessions:continue
            totals={key:sum(s[key] for s in sessions) for key in ['setup_ns','teardown_ns','complete_session_ns']}
            for session in sessions:
                for record in session['records']:
                    for key,value in record['costs_ns'].items():totals[key]=totals.get(key,0)+value
                    totals['gpu_ns']=totals.get('gpu_ns',0)+record['gpu_us']*1000
            result['partitions'][variant]=dict(session_count=len(sessions),totals_ns=totals,
                setup_median_ms=statistics.median(s['setup_ns']/1e6 for s in sessions),
                checker_median_ms=statistics.median(sum(r['costs_ns'].get('checker',0) for r in s['records'])/1e6 for s in sessions))
        results.append(result)
    lanes=[]
    for family,tier in sorted({(c['family'],c['tier']) for c in f['cells']}):
        for variant in ['baseline','candidate']:
            values=[]
            for block in range(f['blocks']):
                prefix=f'b{block:02d}-{family}-{tier}-'
                native=rows.get(prefix+'native-'+variant);fp4=rows.get(prefix+'fp4x2-'+variant)
                if native is not None and fp4 is not None:
                    values.append(native['complete_session_ns']/fp4['complete_session_ns'])
            lanes.append(dict(family=family,tier=tier,variant=variant,complete_pairs=len(values),
                median=statistics.median(values) if values else None,values=values,
                inferential_claim=False,scope='descriptive FP4/native contrast; primary inference compares implementations within each lane'))
    return dict(schema_version=1,freeze=freeze_ref,complete_sessions=len(rows),planned_sessions=len(f['cells']),
        complete_solves=sum(len(r['records']) for r in rows.values()),missing=missing,partial_responses=partial,failed_blocks=failures,comparisons=results,descriptive_lane_ratios=lanes,
        scoped_passes=sum(r['scoped_pass'] for r in results),provisional_passes=sum(r['provisional_pass'] for r in results),
        limitations=['constructed cyclic model streams','shared device and temporal independence assumption',
                     'intervals condition on complete pairs when coverage is missing','no public/default adoption'])
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args();value=analyze()
    path=BASE/'analysis.json'
    if a.verify:require(load(path)==value,'analysis differs')
    else:put(path,value)
    print({k:value[k] for k in ['complete_sessions','complete_solves','scoped_passes','provisional_passes']})
