"""Stream and verify portable development evidence without extracting archive paths."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile
from lp_mixed2_reuse_common import BASE, ROOT, IMAGE, OLD, load, put, ref, require
from lp_mixed2_reuse_analysis import DATA, PartReader

INDEX = DATA/'mixed2-reuse-evidence-v1.json'
CHECK = DATA/'mixed2-reuse-evidence-check-v1.json'


def digest(stream):
    h=hashlib.sha256();size=0
    while block:=stream.read(1<<20):h.update(block);size+=len(block)
    return h.hexdigest(),size


def paths():
    selected=[]
    for p in BASE.rglob('*'):
        if not p.is_file() or p.is_symlink():continue
        rel=p.relative_to(BASE)
        if rel.parts[0] in ('resources','packaging-v1') or p.suffix=='.lock':continue
        if p.name=='records-v1.tar.gz':continue
        if rel.parts[0].startswith('confirmation-b') and re.search(r'-r\d\d\.json$',p.name):continue
        selected.append(p)
    # These retained executables are needed for independent original checking and
    # device replay; historical source/evidence archives remain exact dependencies.
    return sorted(set(selected+[IMAGE,OLD/'build-v10/executor']))


def publish():
    selected=paths();entries=[];first={}
    for p in selected:
        with p.open('rb') as f:sha,size=digest(f)
        entry=dict(path=str(p.relative_to(ROOT)),sha256=sha,bytes=size)
        key=(sha,size)
        if key in first:entry['link']=first[key]
        else:first[key]=entry['path']
        entries.append(entry)
    folder=BASE/'packaging-v1';folder.mkdir(exist_ok=False)
    manifest=dict(schema_version=1,files=entries,
                  excluded='Resource receipts are closed separately; confirmation responses are in the records archive.')
    put(folder/'manifest.json',manifest)
    archive=folder/'evidence.tar.gz'
    with archive.open('xb') as out,gzip.GzipFile(fileobj=out,mode='wb',compresslevel=6,mtime=0) as zipped:
        with tarfile.open(fileobj=zipped,mode='w|',format=tarfile.PAX_FORMAT) as tar:
            raw=json.dumps(manifest,separators=(',',':')).encode();info=tarfile.TarInfo('manifest.json')
            info.size=len(raw);tar.addfile(info,io.BytesIO(raw))
            for entry in entries:
                info=tarfile.TarInfo(entry['path']);info.mode=(ROOT/entry['path']).stat().st_mode & 0o777
                if 'link' in entry:
                    info.type=tarfile.LNKTYPE;info.linkname=entry['link'];tar.addfile(info)
                else:
                    info.size=entry['bytes']
                    with (ROOT/entry['path']).open('rb') as source:tar.addfile(info,source)
    parts=[];h=hashlib.sha256();total=0
    with archive.open('rb') as source:
        while chunk:=source.read(48<<20):
            p=DATA/f'mixed2-reuse-evidence-v1.part{len(parts):02d}'
            with p.open('xb') as out:out.write(chunk)
            parts.append(dict(**ref(p),bytes=len(chunk)));h.update(chunk);total+=len(chunk)
    put(INDEX,dict(format='tar+gzip with exact-content hardlinks',parts=parts,sha256=h.hexdigest(),bytes=total,
                   files=len(entries),unique_files=len(first),manifest_sha256=hashlib.sha256(raw).hexdigest()))
    print(dict(status='packaged',files=len(entries),unique_files=len(first),bytes=total),flush=True)


def verify(compare_originals=True):
    index=load(INDEX);h=hashlib.sha256();total=0
    for item in index['parts']:
        raw=(ROOT/item['path']).read_bytes()
        require(hashlib.sha256(raw).hexdigest()==item['sha256'] and len(raw)==item['bytes'],'evidence part')
        h.update(raw);total+=len(raw)
    require(h.hexdigest()==index['sha256'] and total==index['bytes'],'evidence sequence')
    seen={}
    with PartReader(index['parts']) as stream,tarfile.open(fileobj=stream,mode='r|gz') as tar:
        member=tar.next();require(member is not None and member.name=='manifest.json','evidence manifest')
        raw=tar.extractfile(member).read()
        require(hashlib.sha256(raw).hexdigest()==index['manifest_sha256'],'evidence manifest binding')
        manifest=json.loads(raw)
        for entry in manifest['files']:
            member=tar.next();name=entry['path'];p=Path(name)
            require(member is not None and member.name==name and name not in seen and
                    not p.is_absolute() and '..' not in p.parts,'evidence member path/order')
            if 'link' in entry:
                require(member.islnk() and member.linkname==entry['link'] and member.linkname in seen,
                        'evidence hardlink target')
                got=seen[member.linkname]
            else:
                require(member.isfile(),'evidence regular file')
                got=digest(tar.extractfile(member))
            require(got==(entry['sha256'],entry['bytes']),'evidence bytes')
            if compare_originals:
                with (ROOT/name).open('rb') as source:require(digest(source)==got,'original evidence changed: '+name)
            seen[name]=got
        require(tar.next() is None and len(seen)==index['files'],'evidence coverage')
    if compare_originals:
        put(CHECK,dict(status='passed',index=ref(INDEX),files=len(seen),original_bytes_exact=True))
    print(dict(status='verified',files=len(seen),originals_compared=compare_originals),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['publish','verify','portable']);a=p.parse_args()
    publish() if a.action=='publish' else verify(a.action=='verify')
