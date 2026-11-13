"""Portable, fail-closed replay of complete changing-model session evidence."""
import argparse
from collections import defaultdict
import gzip
import hashlib
import json
import io
import tarfile
from pathlib import Path
from statistics import median
from lp_mixed2_reuse_common import BASE, ROOT, load, put, ref, require
from lp_mixed2_fp4_analysis import interval

DATA=ROOT/'docs/benchmarks/data'
ANALYSIS=DATA/'mixed2-reuse-analysis-v1.json'
ARCHIVE=DATA/'mixed2-reuse-records-v1.json'


def assess(freeze, sessions, records, missing, failed_blocks=()):
    expected={c['id']:c for c in freeze['cells']}
    require(len(expected)==len(freeze['cells']),'duplicate planned cell')
    require(len({s['id'] for s in sessions})==len(sessions),'duplicate observed cell')
    require(sorted(set(expected)-{s['id'] for s in sessions})==missing,'missing-cell ledger')
    require(len(set(failed_blocks))==len(failed_blocks) and all(0<=b<freeze['blocks'] for b in failed_blocks),'failed-block ledger')
    coverage_ok=not missing and not failed_blocks
    indexed={};certificates=physical=0;recoveries=defaultdict(int);unique=set()
    for s in sessions:
        require(s['id'] in expected,'unexpected session')
        require(all(s[k]==v for k,v in expected[s['id']].items()),'cell differs')
        require(s['count']==freeze['count']==len(s['records']),'incomplete solve roster')
        require(s['complete_session_ns']>=s['setup_ns']+s['teardown_ns']+
                sum(r['complete_ns'] for r in s['records']),'session cost partition')
        total=0
        for i, rr in enumerate(s['records']):
            require(rr['index']==i and rr['scenario']==i%4,'scenario order')
            item=rr['result'];raw=records[item['path']]
            require(hashlib.sha256(raw).hexdigest()==item['sha256'],'response binding')
            r=json.loads(raw);model=freeze['groups'][s['family']][i%4]
            total+=r['physical'];physical+=r['physical']
            require(r['solve_id']==i and r['physical_total']==total,'session work identity')
            require(r['model_sha256']==r['endpoint']['model_sha256']==
                    r['certificate']['model_sha256']==model['sha256'],'original scenario authority')
            require(r['image_sha256']==freeze['image']['sha256'],'device image binding')
            require(r['checker_binary_sha256']==freeze['binary']['sha256'],'checker binary binding')
            require(r['lane']==s['lane'] and r['tier']==s['tier'] and r['fixed_audit'] and
                    r['window_max']==(32 if s['lane']=='native' else 16),'solve configuration')
            require(r['certified'] and r['certificate']['accepted'],'missing certificate')
            require(r['physical']==sum(r['attempted'].values())==rr['physical'] and
                    r['logical']==rr['logical'] and r['gpu_us']==rr['gpu_us'],'work summary')
            require(r['solve_ns']==sum(r['costs_ns'].values()) and rr['costs_ns']==r['costs_ns'] and
                    rr['solve_ns']>=r['solve_ns'] and
                    rr['complete_ns']>=rr['switch_ns']+rr['solve_ns'],'solve cost partition')
            require(sum(e['step']['done'] for e in r['events'] if e['kind']=='window')==r['physical'],
                    'physical window accounting')
            for event in r['events']:
                if event['kind']=='recovery':recoveries[event['reason']]+=1
            unique.add((model['sha256'],s['tier'],json.dumps(r['endpoint'],sort_keys=True)))
            certificates+=1
        indexed[s['block'],s['family'],s['tier'],s['lane']]=s
    rows=[];alpha=freeze['statistics']['alpha']
    pairs=sorted({(c['family'],c['tier']) for c in freeze['cells']})
    for family,tier in pairs:
        blocks=[b for b in range(freeze['blocks']) if
                all((b,family,tier,lane) in indexed for lane in ['native','fp4x2'])]
        if not blocks:
            rows.append(dict(family=family,tier=tier,status='no-complete-pairs'));continue
        ns=[indexed[b,family,tier,'native'] for b in blocks]
        fs=[indexed[b,family,tier,'fp4x2'] for b in blocks]
        ratios=[n['complete_session_ns']/f['complete_session_ns'] for n,f in zip(ns,fs)]
        savings=[(n['complete_session_ns']-f['complete_session_ns'])/1e6 for n,f in zip(ns,fs)]
        ratio=interval(ratios,alpha);saving=interval(savings,alpha)
        useful=coverage_ok and ratio['lower'] is not None and ratio['lower']>1 and saving['lower']>10
        summaries={}
        for lane,ss in [('native',ns),('fp4x2',fs)]:
            summaries[lane]=dict(session_ms=median(s['complete_session_ns']/1e6 for s in ss),
                setup_ms=median(s['setup_ns']/1e6 for s in ss),teardown_ms=median(s['teardown_ns']/1e6 for s in ss),
                request_ms=median(median(r['complete_ns']/1e6 for r in s['records']) for s in ss),
                switch_ms=median(median(r['switch_ns']/1e6 for r in s['records']) for s in ss),
                gpu_ms=median(median(r['gpu_us']/1000 for r in s['records']) for s in ss),
                work=sorted({r['physical'] for s in ss for r in s['records']}),
                costs_ms={k:median(median(r['costs_ns'].get(k,0)/1e6 for r in s['records']) for s in ss)
                          for k in set().union(*(r['costs_ns'] for s in ss for r in s['records']))})
        for lane,ss in [('native',ns),('fp4x2',fs)]:
            parts=dict(setup=sum(s['setup_ns'] for s in ss),teardown=sum(s['teardown_ns'] for s in ss),
                       switch=sum(r['switch_ns'] for s in ss for r in s['records']))
            for key in set().union(*(r['costs_ns'] for s in ss for r in s['records'])):
                parts['solver/'+key]=sum(r['costs_ns'].get(key,0) for s in ss for r in s['records'])
            total=sum(s['complete_session_ns'] for s in ss)
            require(sum(parts.values())<=total,'aggregate complete-cost partition')
            parts['delivery_and_bookkeeping']=total-sum(parts.values())
            summaries[lane]['aggregate_cost_ns']=parts
            summaries[lane]['aggregate_session_ns']=total
        rows.append(dict(family=family,tier=tier,blocks=blocks,speedup=ratio,saved_ms=saving,
            useful_scoped_gain=useful,provisional_110_lower_pass=coverage_ok and ratio['lower'] is not None and ratio['lower']>1.1,
            summaries=summaries,first_16=interval(ratios[:16],alpha),
            order_medians={str(p):median(ratios[i] for i,n in enumerate(ns) if n['position']==p)
                           for p in [0,1] if any(n['position']==p for n in ns)}))
    return dict(schema_version=1,status='complete-confirmation' if coverage_ok else 'incomplete-confirmation',
                sessions=len(sessions),planned_sessions=len(expected),solves=certificates,certificates=certificates,
                physical_updates=physical,unique_endpoints=len(unique),recoveries=dict(recoveries),
                missing_cells=missing,failed_blocks=list(failed_blocks),rows=rows,production_adoption=False)


def collect():
    freeze=load(BASE/'confirmation-freeze.json');sessions=[];records={};failures=[]
    for b in range(freeze['blocks']):
        folder=BASE/f'confirmation-b{b:02d}'
        settlement=load(BASE/'resources'/f'confirmation-b{b:02d}.settlement.json')
        if settlement['status']!='passed':failures.append(dict(block=b,settlement=settlement))
        if (folder/'result.json').exists():
            ss=load(folder/'result.json')['sessions']
        else:
            require(settlement['status']=='refused','missing block without refusal')
            ss=[load(p) for p in sorted(folder.glob('*.session.json'))]
        sessions.extend(ss)
        # Partial files are retained separately and never count as a completed
        # lifecycle. Keep every response, including ones lacking a session receipt.
        for p in folder.glob('*-r[0-9][0-9].json'):
            records[str(p.relative_to(ROOT))]=p
    missing=sorted({c['id'] for c in freeze['cells']}-{s['id'] for s in sessions})
    return freeze,sessions,records,missing,failures


class DiskRecords:
    def __getitem__(self, name):
        return (ROOT/name).read_bytes()


class PartReader(io.RawIOBase):
    def __init__(self, parts):
        self.parts=iter(parts);self.current=None
    def readable(self):return True
    def readinto(self, target):
        while True:
            if self.current is None:
                item=next(self.parts,None)
                if item is None:return 0
                self.current=(ROOT/item['path']).open('rb')
            n=self.current.readinto(target)
            if n:return n
            self.current.close();self.current=None
    def close(self):
        if self.current:self.current.close()
        super().close()


class TarRecords:
    def __init__(self, archive):self.archive=archive
    def __getitem__(self, name):
        member=self.archive.next()
        require(member is not None and member.name==name,'portable response order')
        return self.archive.extractfile(member).read()


def publish():
    f,ss,records,missing,failures=collect();result=assess(f,ss,DiskRecords(),missing,[r['block'] for r in failures])
    put(ANALYSIS,result)
    meta=dict(freeze=f,sessions=ss,missing_cells=missing,failures=failures,
              all_response_files=sorted(records))
    target=BASE/'records-v1.tar.gz'
    with target.open('xb') as dest, gzip.GzipFile(fileobj=dest,mode='wb',mtime=0) as zipped:
        with tarfile.open(fileobj=zipped,mode='w|') as tar:
            raw=json.dumps(meta,separators=(',',':')).encode();info=tarfile.TarInfo('metadata.json')
            info.size=len(raw);tar.addfile(info,io.BytesIO(raw))
            included=set()
            for session in ss:
                for rr in session['records']:
                    name=rr['result']['path'];tar.add(ROOT/name,arcname=name,recursive=False);included.add(name)
            for name in sorted(set(records)-included):tar.add(ROOT/name,arcname=name,recursive=False)
    parts=[];digest=hashlib.sha256();size=0
    with target.open('rb') as stream:
        i=0
        while chunk:=stream.read(48<<20):
            p=DATA/f'mixed2-reuse-records-v1.part{i:02d}'
            with p.open('xb') as dest:dest.write(chunk)
            parts.append(ref(p));digest.update(chunk);size+=len(chunk);i+=1
    put(ARCHIVE,dict(format='tar+gzip ordered responses',parts=parts,sha256=digest.hexdigest(),bytes=size))
    print(dict(status=result['status'],sessions=len(ss),solves=result['solves']),flush=True)


def verify():
    index=load(ARCHIVE);digest=hashlib.sha256();size=0
    for item in index['parts']:
        raw=(ROOT/item['path']).read_bytes()
        require(hashlib.sha256(raw).hexdigest()==item['sha256'],'archive part binding')
        digest.update(raw);size+=len(raw)
    require(digest.hexdigest()==index['sha256'] and size==index['bytes'],'archive binding')
    with PartReader(index['parts']) as parts, tarfile.open(fileobj=parts,mode='r|gz') as tar:
        member=tar.next();require(member.name=='metadata.json','archive metadata')
        d=json.load(tar.extractfile(member))
        require(assess(d['freeze'],d['sessions'],TarRecords(tar),d['missing_cells'],[r['block'] for r in d['failures']])==load(ANALYSIS),'portable arithmetic replay')
    print('MIXED2 reuse portable replay passed',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['publish','verify']);a=p.parse_args()
    publish() if a.action=='publish' else verify()
