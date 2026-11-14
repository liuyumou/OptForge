"""Streamed portable original-byte verification and exact statistical replay."""
import argparse
import gzip
import hashlib
import io
import json
import re
import tarfile
from pathlib import Path
from lp_checker2_common import BASE,ROOT,PRIOR,load,put,ref,require
from lp_checker2_analysis import assess
from lp_mixed2_reuse_admit import numerical
from lp_mixed2_confirm2_analysis import PartReader,PartWriter

DATA=ROOT/'docs/benchmarks/data'
INDEX=DATA/'checker2-evidence-v1.json'
def digest(stream):
    h=hashlib.sha256();size=0
    while chunk:=stream.read(1<<20):h.update(chunk);size+=len(chunk)
    return h.hexdigest(),size

def trajectory(value):
    return hashlib.sha256(json.dumps(numerical(value),sort_keys=True,separators=(',',':')).encode()).hexdigest()

def publish():
    models=load(PRIOR/'models/manifest.json')
    paths=[p for p in BASE.rglob('*') if p.is_file() and not p.is_symlink()
           and p.suffix!='.lock' and not p.relative_to(BASE).parts[0].startswith('build-') and p.name!='executor'
           and p.relative_to(BASE).parts[0]!='vector-target' and p.name not in ['evidence-check.json']]
    paths += [ROOT/p['path'] for items in models['groups'].values() for p in items]+[PRIOR/'models/manifest.json']
    f=load(BASE/'freeze.json')
    for item in f['sources']+list(f['binaries'].values())+[f['image'],f['models']]+f['admissions']:
        require(ref(ROOT/item['path'])==item,'frozen publication binding differs')
    paths += [ROOT/p['path'] for p in f['sources']]
    entries=[];first={}
    for p in sorted(set(paths)):
        with p.open('rb') as stream:h,n=digest(stream)
        entry=dict(path=str(p.relative_to(ROOT)),sha256=h,bytes=n)
        if (h,n) in first:entry['link']=first[h,n]
        else:first[h,n]=entry['path']
        entries.append(entry)
    controls={}
    for p in sorted((BASE/'pilot-optimized').glob('*-r[0-9][0-9].json')):
        r=load(p);key='|'.join([r['model_sha256'],r['tier'],r['lane']]);value=trajectory(r)
        if key in controls:require(controls[key]==value,'inconsistent admitted trajectory')
        controls[key]=value
    manifest=dict(files=entries,controls=controls,protocol=f,freeze=ref(BASE/'freeze.json'),analysis=load(BASE/'analysis.json'),
                  exclusions='Executable files remain local; immutable binary digests and sources are retained. Archive verification requires no historical artifacts tree.')
    with PartWriter('checker2-evidence-v1') as out,gzip.GzipFile(fileobj=out,mode='wb',compresslevel=6,mtime=0) as zipped:
        with tarfile.open(fileobj=zipped,mode='w|',format=tarfile.PAX_FORMAT) as tar:
            raw=json.dumps(manifest,separators=(',',':')).encode();info=tarfile.TarInfo('manifest.json');info.size=len(raw);tar.addfile(info,io.BytesIO(raw))
            for entry in entries:
                info=tarfile.TarInfo(entry['path']);info.mode=0o644
                if 'link' in entry:info.type=tarfile.LNKTYPE;info.linkname=entry['link'];tar.addfile(info)
                else:
                    info.size=entry['bytes']
                    with (ROOT/entry['path']).open('rb') as stream:tar.addfile(info,stream)
    put(INDEX,dict(format='tar+gzip with exact-content hardlinks',files=len(entries),unique_files=len(first),**out.index(),manifest_sha256=hashlib.sha256(raw).hexdigest()))
    print(dict(files=len(entries),bytes=out.total),flush=True)

def verify(originals=False):
    index=load(INDEX);whole=hashlib.sha256();total=0
    for item in index['parts']:
        raw=(ROOT/item['path']).read_bytes();require(hashlib.sha256(raw).hexdigest()==item['sha256'] and len(raw)==item['bytes'],'archive part')
        whole.update(raw);total+=len(raw)
    require(whole.hexdigest()==index['sha256'] and total==index['bytes'],'archive sequence')
    seen={};small={};sessions={};response_refs={};responses=0;f=None;failures=[]
    base=str(BASE.relative_to(ROOT))
    with PartReader(index['parts']) as stream,tarfile.open(fileobj=stream,mode='r|gz') as tar:
        member=tar.next();require(member.name=='manifest.json','manifest first');raw=tar.extractfile(member).read()
        require(hashlib.sha256(raw).hexdigest()==index['manifest_sha256'],'manifest binding');manifest=json.loads(raw)
        roster={c['id']:c for c in manifest['protocol']['cells']}
        link_targets={e['link'] for e in manifest['files'] if 'link' in e}
        for entry in manifest['files']:
            member=tar.next();name=entry['path'];path=Path(name)
            require(member is not None and member.name==name and name not in seen and not path.is_absolute() and '..' not in path.parts,'archive path/order')
            wanted=(name==base+'/freeze.json' or name.startswith(base+'/confirmation/') and (name.endswith('.session.json') or re.search(r'-r\d\d\.json$',name))
                    or name.startswith(base+'/resources/confirmation-b') and name.endswith('.settlement.json'))
            if 'link' in entry:
                require(member.islnk() and member.linkname==entry['link'] and member.linkname in seen,'archive hardlink')
                got=seen[member.linkname];raw=small.get(member.linkname)
                require(not wanted or raw is not None,'linked metadata unavailable')
            else:
                require(member.isfile(),'archive member type')
                source=tar.extractfile(member)
                if wanted or entry['bytes']<8<<20:
                    raw=source.read();got=(hashlib.sha256(raw).hexdigest(),len(raw))
                    if name in link_targets:small[name]=raw
                else:raw=None;got=digest(source)
            require(got==(entry['sha256'],entry['bytes']),'archive bytes')
            if originals:
                with (ROOT/name).open('rb') as original:require(digest(original)==got,'original changed '+name)
            seen[name]=got
            if wanted:
                value=json.loads(raw)
                if name==base+'/freeze.json':f=value
                elif name.endswith('.settlement.json'):
                    if value['status']!='passed':failures.append(value)
                elif name.endswith('.session.json'):sessions[value['id']]=value
                else:
                    cell=roster[Path(name).name.rsplit('-r',1)[0]]
                    require(value['image_sha256']==manifest['protocol']['image']['sha256'] and value['checker_binary_sha256']==manifest['protocol']['binaries'][cell['variant']]['sha256'],'portable response binary/image binding')
                    key='|'.join([value['model_sha256'],value['tier'],value['lane']])
                    require(manifest['controls'].get(key)==trajectory(value),'archived numerical trajectory differs')
                    response_refs[name]=dict(path=name,sha256=got[0]);responses+=1
        require(tar.next() is None and len(seen)==index['files'],'archive coverage')
    require(f is not None and f==manifest['protocol'],'frozen protocol missing or altered')
    for item in f['sources']+[f['models']]+f['admissions']:
        require(item['path'] in seen and seen[item['path']][0]==item['sha256'],'portable frozen binding differs')
    missing=[c for c in f['cells'] if c['id'] not in sessions]
    linked=set()
    for session in sessions.values():
        require(len(session['records'])==f['count'] and session['count']==f['count'],'complete lifecycle count')
        for record in session['records']:
            require(response_refs.get(record['result']['path'])==record['result'],'response reference mismatch');linked.add(record['result']['path'])
    partial=[response_refs[p] for p in sorted(set(response_refs)-linked)]
    result=assess(f,sessions,missing,manifest['freeze'],partial,failures)
    require(result==manifest['analysis'],'portable statistical replay differs')
    return dict(status='passed',files=len(seen),responses=responses,sessions=len(sessions),scoped_passes=result['scoped_passes'],
                original_artifacts_required=False,archive=ref(INDEX))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['publish','verify','portable']);a=p.parse_args()
    if a.action=='publish':publish()
    else:
        result=verify(a.action=='verify');print(result,flush=True)
        if a.action=='verify':put(BASE/'evidence-check.json',result)
