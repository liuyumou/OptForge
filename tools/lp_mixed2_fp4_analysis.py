"""CPU-only replay of all frozen cells, complete costs and exact median intervals."""
import argparse
from collections import defaultdict
import gzip
import hashlib
import json
import math
from pathlib import Path
from statistics import median
from lp_mixed2_fp4_common import BASE,ROOT,load,put,ref,require

DATA=ROOT/'docs/benchmarks/data'
ANALYSIS=DATA/'mixed2-fp4-analysis-v1.json'
ARCHIVE=DATA/'mixed2-fp4-records-v1.json'
RAW_ARCHIVE=DATA/'mixed2-fp4-records-v1.json.gz'

def interval(values,alpha=.05):
    require(len(values)>0 and all(math.isfinite(x) for x in values),'invalid interval input')
    n=len(values);ordered=sorted(values);k=0
    for candidate in range(1,n//2+1):
        tail=2*sum(math.comb(n,i) for i in range(candidate))/2**n
        if tail<=alpha:k=candidate
    return dict(median=median(values),lower=ordered[k-1] if k else None,upper=ordered[n-k] if k else None,rank=k,n=n,coverage=(1-2*sum(math.comb(n,i) for i in range(k))/2**n) if k else 1.,values=values)

def assess(freeze,sessions,records,completion=None):
    expected={c['id']:c for c in freeze['cells']};require(len(expected)==len(freeze['cells']),'duplicate frozen cell')
    require(len({s['id'] for s in sessions})==len(sessions),'duplicate session')
    missing=sorted(set(expected)-{s['id'] for s in sessions})
    if completion is None:require(not missing and len(sessions)==len(expected),'missing session')
    else:
        require(completion['status']=='incomplete' and completion['missing_cells']==missing,'incomplete roster mismatch')
        require(all(expected[k]['block'] in completion['failed_blocks'] for k in missing),'missing cell outside failed block')
        require(completion['failed_blocks'] and all(r['settlement']['status']=='refused' for r in completion['failures']),'failure evidence missing')
    indexed={};certificates=refusals=0;recoveries=defaultdict(int);unique=set();audits=0
    for s in sessions:
        c=expected[s['id']];require(all(s[k]==v for k,v in c.items()),'cell changed')
        require(s['complete_session_ns']>=s['setup_ns']+s['teardown_ns']+sum(r['complete_ns'] for r in s['records']),'session boundary')
        require(sorted((r['tier'],r['repeat']) for r in s['records'])==sorted((t,i) for t in freeze['tiers'] for i in range(freeze['repeats'])),'solve roster')
        physical_total=0
        for solve_id,rr in enumerate(s['records']):
            item=rr['result'];raw=records[item['path']];require(hashlib.sha256(raw).hexdigest()==item['sha256'],'result binding');r=json.loads(raw)
            physical_total+=r['physical']
            require(r['solve_id']==solve_id and r['physical_total']==physical_total,'session identity/work')
            require(rr['costs_ns']==r['costs_ns'] and rr['certified']==r['certified'] and rr['final_lane']==r['final_lane'],'summary differs from original response')
            require(r['lane']==s['lane'] and r['tier']==rr['tier'] and r['fixed_audit'] and r['window_max']==s['settings']['window_max'],'solve config')
            require(r['image_sha256']==freeze['image']['sha256'],'image differs')
            require(r['certificate']['model_sha256']==freeze['model_files'][s['family']]['sha256'],'original-model binding')
            require(r['certified']==(s['family']!='infinite-bound-refusal') and r['certificate']['accepted']==r['certified'],'final certificate')
            require(rr['complete_ns']>=r['solve_ns']==sum(r['costs_ns'].values()),'complete timing partition')
            require(r['physical']==sum(r['attempted'].values())==rr['physical'] and r['logical']==rr['logical'] and r['gpu_us']==rr['gpu_us'],'work binding')
            require(sum(e['step']['done'] for e in r['events'] if e['kind']=='window')==r['physical'],'window work')
            certificates+=int(r['certified']);refusals+=int(not r['certified']);audits+=len(r['audits'])
            for e in r['events']:
                if e['kind']=='recovery':recoveries[e['reason']]+=1
            unique.add((s['family'],r['tier'],json.dumps(r['endpoint'],sort_keys=True,separators=(',',':'))))
        for tier in freeze['tiers']:
            rs=[r for r in s['records'] if r['tier']==tier]
            indexed[s['block'],s['family'],tier,s['lane']]=dict(complete_ms=median(r['complete_ns'] for r in rs)/1e6,gpu_ms=median(r['gpu_us'] for r in rs)/1000,setup_ms=s['setup_ns']/1e6,teardown_ms=s['teardown_ns']/1e6,session_ms=s['complete_session_ns']/1e6,work=sorted(set(r['physical'] for r in rs)),costs_ms={k:median(r['costs_ns'].get(k,0) for r in rs)/1e6 for k in set().union(*(r['costs_ns'] for r in rs))},order=s['position'])
    families=sorted(freeze['model_files']);out=[];multiplicity=2*len(families)*len(freeze['tiers'])
    for family in families:
        for tier in freeze['tiers']:
            blocks=[b for b in range(freeze['blocks']) if (b,family,tier,'native') in indexed and (b,family,tier,'fp4x2') in indexed]
            require(blocks,'no paired sessions')
            ns=[indexed[b,family,tier,'native'] for b in blocks];fs=[indexed[b,family,tier,'fp4x2'] for b in blocks]
            ratios=[n['complete_ms']/f['complete_ms'] for n,f in zip(ns,fs)];savings=[n['complete_ms']-f['complete_ms'] for n,f in zip(ns,fs)]
            fixed=[f['setup_ms']+f['teardown_ms']-n['setup_ms']-n['teardown_ms'] for n,f in zip(ns,fs)]
            ratio=interval(ratios,.05/multiplicity);saving=interval(savings,.05/multiplicity)
            out.append(dict(family=family,tier=tier,paired_blocks=blocks,native_ms=median(n['complete_ms'] for n in ns),fp4_ms=median(f['complete_ms'] for f in fs),speedup=ratio,saved_ms=saving,native_gpu_ms=median(n['gpu_ms'] for n in ns),fp4_gpu_ms=median(f['gpu_ms'] for f in fs),gpu_speedup=interval([n['gpu_ms']/f['gpu_ms'] if f['gpu_ms'] else 1. for n,f in zip(ns,fs)]),native_work=sorted(set(v for n in ns for v in n['work'])),fp4_work=sorted(set(v for f in fs for v in f['work'])),extra_lifecycle_ms=median(fixed),forecast_break_even_solves=math.ceil(max(0,median(fixed))/median(savings)) if median(savings)>0 else None,six_solve_session_speedup=interval([n['session_ms']/f['session_ms'] for n,f in zip(ns,fs)]),native_setup_ms=median(n['setup_ms'] for n in ns),fp4_setup_ms=median(f['setup_ms'] for f in fs),native_costs_ms={k:median(n['costs_ms'].get(k,0) for n in ns) for k in set().union(*(n['costs_ms'] for n in ns))},fp4_costs_ms={k:median(f['costs_ms'].get(k,0) for f in fs) for k in set().union(*(f['costs_ms'] for f in fs))},first_16_speedup=interval(ratios[:16],.05/multiplicity),order_speedup={str(order):median(ratios[i] for i,n in enumerate(ns) if n['order']==order) for order in (0,1)}))
    completed_solves=certificates+refusals
    partial=[] if completion is None else completion['partial_responses']
    for item in partial:
        raw=records[item['result']['path']];require(hashlib.sha256(raw).hexdigest()==item['result']['sha256'],'partial response binding');r=json.loads(raw);c=expected[item['cell']]
        require(item['cell'] in missing and r['lane']==c['lane'] and r['tier']==item['tier'],'partial identity')
        require(r['image_sha256']==freeze['image']['sha256'] and r['model_sha256']==freeze['model_files'][c['family']]['sha256'],'partial source/model')
        require(r['certificate']['accepted']==r['certified']==(c['family']!='infinite-bound-refusal'),'partial certificate')
        require(r['physical']==sum(r['attempted'].values()) and r['solve_ns']==sum(r['costs_ns'].values()),'partial work/cost')
        certificates+=int(r['certified']);refusals+=int(not r['certified']);audits+=len(r['audits'])
        unique.add((c['family'],r['tier'],json.dumps(r['endpoint'],sort_keys=True,separators=(',',':'))))
        for e in r['events']:
            if e['kind']=='recovery':recoveries[e['reason']]+=1
    return dict(schema_version=1,status='incomplete-confirmation' if completion else 'complete',planned_sessions=len(expected),sessions=len(sessions),incomplete_sessions=len(missing),partial_session_responses=len(partial),completed_session_solves=completed_solves,solves=certificates+refusals,certificates=certificates,refusals=refusals,unique_endpoints=len(unique),audits=audits,recoveries=dict(recoveries),simultaneous_comparisons=multiplicity,completion=completion,rows=out)

def collect():
    f=load(BASE/'confirmation-freeze.json');sessions=[];records={};failures=[];failed=[]
    for i in range(f['blocks']):
        directory=BASE/f'confirmation-b{i:02d}';settlement=load(BASE/'resources'/f'confirmation-b{i}.settlement.json')
        if settlement['status']=='passed':
            d=load(directory/'result.json');require(d['status']=='complete','block incomplete');sessions+=d['sessions']
        else:
            failed.append(i);failures.append(dict(block=i,settlement=settlement,resource=load(ROOT/settlement['resource']['path'])))
            sessions += [load(p) for p in sorted(directory.glob('*.session.json'))]
    referenced=set()
    for session in sessions:
        for r in session['records']:
            p=r['result']['path'];records[p]=(ROOT/p).read_bytes();referenced.add(p)
    partial=[]
    for c in f['cells']:
        if c['block'] not in failed:continue
        for tier in f['tiers']:
            for repeat in range(f['repeats']):
                path=BASE/f"confirmation-b{c['block']:02d}"/(c['id']+f'-{tier}-{repeat}.json')
                key=str(path.relative_to(ROOT))
                if path.exists() and key not in referenced:
                    records[key]=path.read_bytes();partial.append(dict(cell=c['id'],family=c['family'],tier=tier,repeat=repeat,result=ref(path)))
    completion=dict(status='incomplete',failed_blocks=failed,failures=failures,missing_cells=sorted({c['id'] for c in f['cells']}-{s['id'] for s in sessions}),partial_responses=partial,interpretation='No scientific retry. All available paired complete sessions are descriptive; planned confirmation/retention fails coverage. Orphan durable responses retain certificates but lack completed lifecycle cost.') if failed else None
    return f,sessions,records,completion

def publish():
    f,s,r,c=collect();a=assess(f,s,r,c);put(ANALYSIS,a)
    # Preserve exact original response bytes, so every recorded SHA remains verifiable.
    raw=json.dumps(dict(freeze=f,sessions=s,completion=c,records={k:v.decode() for k,v in r.items()}),separators=(',',':'),allow_nan=False).encode()
    write_parts(gzip.compress(raw,mtime=0))
    print(dict(sessions=a['sessions'],solves=a['solves'],certificates=a['certificates'],refusals=a['refusals'],archive=ref(ARCHIVE)),flush=True)


def write_parts(blob):
    parts=[]
    for i,start in enumerate(range(0,len(blob),48<<20)):
        path=DATA/f'mixed2-fp4-records-v1.part{i:02d}'
        with path.open('xb') as out:out.write(blob[start:start+(48<<20)])
        parts.append(dict(**ref(path),bytes=path.stat().st_size))
    put(ARCHIVE,dict(format='concatenated-gzip-v1',sha256=hashlib.sha256(blob).hexdigest(),bytes=len(blob),parts=parts))

def archive_files():
    return [ARCHIVE]+[ROOT/r['path'] for r in load(ARCHIVE)['parts']]

def read_archive():
    index=load(ARCHIVE);require(index['format']=='concatenated-gzip-v1','archive format');pieces=[]
    for item in index['parts']:
        path=(ROOT/item['path']).resolve();require(path.is_relative_to(ROOT),'archive path escape');raw=path.read_bytes()
        require(len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256'],'archive part changed');pieces.append(raw)
    blob=b''.join(pieces);require(len(blob)==index['bytes'] and hashlib.sha256(blob).hexdigest()==index['sha256'],'archive sequence changed')
    return json.loads(gzip.decompress(blob))

def pack_existing():
    blob=RAW_ARCHIVE.read_bytes();write_parts(blob)
    dest=BASE/'packaging-v1'/RAW_ARCHIVE.name;dest.parent.mkdir(exist_ok=True);RAW_ARCHIVE.rename(dest)
    put(BASE/'packaging-v1/manifest.json',dict(original_path=str(RAW_ARCHIVE.relative_to(ROOT)),original_gzip=ref(dest),portable_index=ref(ARCHIVE),exact_gzip_bytes=True))
    verify()

def verify():
    d=read_archive();actual=assess(d['freeze'],d['sessions'],{k:v.encode() for k,v in d['records'].items()},d.get('completion'));require(actual==load(ANALYSIS),'portable replay differs');print(dict(status='passed',sessions=actual['sessions'],solves=actual['solves']))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['publish','verify','pack']);a=p.parse_args();publish() if a.action=='publish' else pack_existing() if a.action=='pack' else verify()
