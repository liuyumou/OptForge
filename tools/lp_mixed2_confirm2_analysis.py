"""Portable, fail-closed replay of complete changing-model session evidence."""
import argparse
from collections import defaultdict
import gzip
import hashlib
import json
import io
import os
import tarfile
from pathlib import Path
from statistics import median
from lp_mixed2_confirm2_common import BASE, ROOT, load, put, ref, require
from lp_mixed2_fp4_analysis import interval

DATA=ROOT/'docs/benchmarks/data'
ANALYSIS=DATA/'mixed2-confirm2-analysis-v1.json'
ARCHIVE=DATA/'mixed2-confirm2-records-v1.json'


from lp_mixed2_reuse_analysis import assess


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


class PartWriter(io.RawIOBase):
    """Bound each compressed artifact while retaining a whole-stream digest."""
    def __init__(self,prefix,directory=DATA,limit=48<<20):
        super().__init__()
        require(type(limit) is int and limit>0,'positive part limit')
        self.prefix=prefix;self.directory=directory;self.limit=limit
        self.current=None;self.part_bytes=0;self.total=0;self.parts=[]
        self.digest=hashlib.sha256()

    def writable(self):return True

    def finish_part(self):
        if self.current is not None:
            self.current.flush();os.fsync(self.current.fileno());self.current.close()
            self.parts.append(dict(**ref(self.path),bytes=self.part_bytes));self.current=None;self.part_bytes=0

    def write(self,raw):
        require(not self.closed,'write after close')
        size=len(raw);view=memoryview(raw);offset=0
        self.digest.update(view);self.total+=size
        while offset<size:
            if self.current is None:
                self.path=self.directory/f'{self.prefix}.part{len(self.parts):02d}'
                self.current=self.path.open('xb')
            n=min(size-offset,self.limit-self.part_bytes)
            self.current.write(view[offset:offset+n]);offset+=n;self.part_bytes+=n
            if self.part_bytes==self.limit:self.finish_part()
        return size

    def close(self):
        if not self.closed:self.finish_part()
        super().close()

    def index(self):
        require(self.closed,'unfinished archive')
        return dict(parts=self.parts,sha256=self.digest.hexdigest(),bytes=self.total)


def publish():
    f,ss,records,missing,failures=collect();result=assess(f,ss,DiskRecords(),missing,[r['block'] for r in failures])
    put(ANALYSIS,result)
    meta=dict(freeze=f,sessions=ss,missing_cells=missing,failures=failures,
              all_response_files=sorted(records))
    with PartWriter('mixed2-confirm2-records-v1') as dest, gzip.GzipFile(fileobj=dest,mode='wb',compresslevel=6,mtime=0) as zipped:
        with tarfile.open(fileobj=zipped,mode='w|') as tar:
            raw=json.dumps(meta,separators=(',',':')).encode();info=tarfile.TarInfo('metadata.json')
            info.size=len(raw);tar.addfile(info,io.BytesIO(raw))
            included=set()
            for session in ss:
                for rr in session['records']:
                    name=rr['result']['path'];tar.add(ROOT/name,arcname=name,recursive=False);included.add(name)
            for name in sorted(set(records)-included):tar.add(ROOT/name,arcname=name,recursive=False)
    put(ARCHIVE,dict(format='tar+gzip ordered responses',**dest.index()))
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
    print('MIXED2 confirmation portable replay passed',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['publish','verify']);a=p.parse_args()
    publish() if a.action=='publish' else verify()
