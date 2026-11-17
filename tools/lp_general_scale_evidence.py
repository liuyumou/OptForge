"""Exact response bytes in bounded local chunks; no giant tracked trajectory file."""
import gzip
import hashlib
import json
from pathlib import Path
from lp_general_common import ROOT,put,load,ref,require

CHUNK=64<<20
KIND='general-scale-response-chunks-v1'

def save(path,text,threshold=32<<20,chunk_bytes=CHUNK):
    path=Path(path);data=text.encode()
    if len(data)<=threshold:
        with path.open('xb') as f:f.write(data)
        return
    require(0<chunk_bytes<=CHUNK and len(data)<=4<<30,'response evidence bounds')
    parts=[]
    for i,start in enumerate(range(0,len(data),chunk_bytes)):
        p=path.with_suffix(f'.part-{i:03d}.gz')
        with p.open('xb') as raw,gzip.GzipFile(fileobj=raw,mode='wb',mtime=0,compresslevel=1) as compressed:
            compressed.write(data[start:start+chunk_bytes])
        parts.append(ref(p))
    put(path,dict(kind=KIND,raw_sha256=hashlib.sha256(data).hexdigest(),raw_bytes=len(data),parts=parts))

def read(path):
    path=Path(path);require(path.stat().st_size<=4<<30,'response file bound')
    with path.open() as f:item=json.load(f)
    if not isinstance(item,dict) or item.get('kind')!=KIND:return item
    require(0<item['raw_bytes']<=4<<30 and 0<len(item['parts'])<=4096,'chunk manifest bounds')
    pieces=[];count=0;digest=hashlib.sha256()
    for r in item['parts']:
        p=ROOT/r['path'];require(ref(p)==r,'response chunk hash')
        with gzip.open(p,'rb') as z:data=z.read(CHUNK+1)
        require(len(data)<=CHUNK,'response chunk inflated bound');count+=len(data)
        require(count<=item['raw_bytes'],'response excess bytes');digest.update(data);pieces.append(data)
    require(count==item['raw_bytes'] and digest.hexdigest()==item['raw_sha256'],'response byte identity')
    return json.loads(b''.join(pieces))
