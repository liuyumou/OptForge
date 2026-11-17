"""Stream, verify and replay split GPUP-9 evidence without the original artifacts."""
import argparse
import hashlib
import bisect
import io
import json
import re
from pathlib import Path
import shutil
import zipfile
import tempfile
from contextlib import contextmanager

from lp_baseline_common import ROOT, load, put, ref, require
from lp_gpup9_common import BASE, CPU_CAPS, GPU_CAPS

INDEX = ROOT/'docs/benchmarks/data/gpup9-evidence-v1.json'
CHUNK = 48 << 20


def accepted_work(response):
    """Replay logical-update truncation; rejected FP4 attempts are not useful work."""
    segments=[];logical=0
    def truncate(target):
        nonlocal logical
        require(type(target) is int and 0<=target<=logical,'invalid logical rollback')
        while logical>target:
            lane,count=segments.pop();keep=max(0,count-(logical-target))
            logical-=count-keep
            if keep:segments.append((lane,keep))
    attempted={}
    for event in response['events']:
        if event['kind']=='window':
            count=event['step']['done'];lane=event['lane']
            require(type(count) is int and count>0 and lane in [32,34,36],'invalid executed work')
            require(event['logical']==logical+count,'logical window count differs')
            segments.append((lane,count));logical+=count
            attempted[str(lane)]=attempted.get(str(lane),0)+count
        elif event['kind']=='recovery':truncate(event['logical'])
    require(attempted==response['attempted'] and sum(attempted.values())==response['physical'],'attempted work differs')
    truncate(response['logical'])
    result={str(lane):0 for lane in [32,34,36]}
    for lane,count in segments:result[str(lane)]+=count
    require(sum(result.values())==response['logical'],'accepted work differs')
    return result



def verify_closure(value, index_path=INDEX):
    """Recompute the closed allocation from exact embedded administrative receipts."""
    require(value['schema_version']==1 and value['kind']=='gpup9-closure','closure schema')
    require(value['archive']==ref(index_path),'closure archive binding')
    raw=value['raw'];closed=value['closed']
    def bound(item):
        body=raw[item['path']].encode()
        require(hashlib.sha256(body).hexdigest()==item['sha256'],'closure receipt changed')
        return json.loads(body)
    require(json.loads(raw['artifacts/gpup9-v1/CLOSED.json'])==closed,'closed record differs')
    require(closed['status']=='closed' and closed['scientific_status']=='complete' and closed['cleanup_empty'],'closure incomplete')
    require(not any(closed[k] for k in ['public_defaults_changed','prep3_opened','publication']),'unexpected scope change')
    cpu={k:0 for k in CPU_CAPS};gpu={k:0 for k in GPU_CAPS}
    cpu['implementation']=512*10**9;cpu['cleanup']=128*10**9
    require(closed['administration_cpu_seconds']==dict(preparation=512,closing=128),'administrative charges')
    expected={p for p in raw if p.endswith('.reservation.json')}
    require({r['reservation']['path'] for r in closed['resources']}==expected and len(closed['resources'])==len(expected),'reservation coverage')
    failed=[]
    for entry in closed['resources']:
        reservation=bound(entry['reservation']);settlement=bound(entry['settlement']);resource=bound(entry['resource'])
        require(settlement['resource']==entry['resource'] and not settlement['overrun'],'settlement binding/overrun')
        require(reservation['phase']==settlement['phase'] and reservation['gpu']==settlement['gpu'],'settlement scope')
        require(resource['guardian_cleanup']['empty'] and resource['result']['cleanup']['empty'],'closure cleanup')
        require(all(type(settlement[k]) is int and settlement[k]>=0 for k in ['cpu_ns','gpu_ns']),'invalid charges')
        require(settlement['cpu_ns']<=reservation['cpu_ns'] and settlement['gpu_ns']<=reservation['gpu_ns'],'reservation overrun')
        if settlement['status']!='passed':
            failed.append(entry)
            require(settlement['cpu_ns']>=reservation['cpu_ns'] and settlement['gpu_ns']>=reservation['gpu_ns'],'failed reservation undercharged')
        else:require(resource['status']=='passed','successful settlement lacks success')
        cpu[reservation['phase']]+=settlement['cpu_ns']
        if reservation['gpu']:gpu[reservation['phase']]+=settlement['gpu_ns']
        else:require(settlement['gpu_ns']==0,'CPU-only GPU charge')
    require(failed==closed['failed'],'failed receipt coverage')
    require(cpu==closed['cpu_phases_ns'] and gpu==closed['gpu_phases_ns'],'phase accounting differs')
    require(sum(cpu.values())==closed['cpu_ns'] and sum(gpu.values())==closed['gpu_ns'],'total accounting differs')
    require(all(cpu[k]<=v*10**9 for k,v in CPU_CAPS.items()) and all(gpu[k]<=v*10**9 for k,v in GPU_CAPS.items()),'phase ceiling')
    require(closed['cpu_ceiling_seconds']==sum(CPU_CAPS.values()) and closed['gpu_ceiling_seconds']==sum(GPU_CAPS.values()),'allocation ceiling')
    published=json.loads(raw['artifacts/gpup9-v1/published-files.json'])
    available={item['sha256'] for item in published['entries'].values()}
    for sha,body in value['late_source_bytes'].items():
        require(hashlib.sha256(body.encode()).hexdigest()==sha,'late source changed');available.add(sha)
    for path,body in raw.items():
        if '/sources/' in path and path.endswith('/manifest.json'):
            require(all(r['sha256'] in available for r in json.loads(body)['sources']),'late source bytes missing')
    for key in ['historical','portable','analysis']:
        item=closed[key]
        if item['path'] in raw:bound(item)
        else:require(published['entries'][item['path']]['sha256']==item['sha256'],'closed evidence binding')
    return dict(status='passed',reservations=len(expected),failed=len(failed),cpu_ns=closed['cpu_ns'],gpu_ns=closed['gpu_ns'])


def digest(stream):
    h=hashlib.sha256();size=0
    while block:=stream.read(1<<20):h.update(block);size+=len(block)
    return h.hexdigest(),size



class PartWriter:
    """Nonseekable ZIP sink; no temporary file grows beyond one admitted part."""
    def __init__(self,index_path=INDEX,chunk=CHUNK,root=None):
        self.root=ROOT if root is None else Path(root)
        self.index_path=Path(index_path);self.chunk=chunk;self.total=0;self.whole=hashlib.sha256();self.parts=[];self.output=None;self.part_size=0;self.part_hash=None
    def tell(self):return self.total
    def seek(self,*args):raise io.UnsupportedOperation('split sink is not seekable')
    def flush(self):
        if self.output:self.output.flush()
    def finish_part(self):
        if self.output:
            self.output.close();self.parts.append(dict(path=str(self.path.relative_to(self.root)),sha256=self.part_hash.hexdigest(),bytes=self.part_size));self.output=None
    def write(self,data):
        original=len(data);data=memoryview(data)
        while data:
            if self.output is None:
                self.path=self.index_path.with_name(self.index_path.stem+f'.part{len(self.parts):02d}')
                self.output=self.path.open('xb');self.part_size=0;self.part_hash=hashlib.sha256()
            piece=data[:self.chunk-self.part_size];self.output.write(piece);self.part_hash.update(piece);self.whole.update(piece)
            self.part_size+=len(piece);self.total+=len(piece);data=data[len(piece):]
            if self.part_size==self.chunk:self.finish_part()
        return original
    def finish(self):
        self.finish_part();return dict(parts=self.parts,bytes=self.total,sha256=self.whole.hexdigest())


class PartReader(io.RawIOBase):
    """Seek across immutable parts without reconstructing an oversized file."""
    def __init__(self,index,root=ROOT):
        super().__init__();self.root=Path(root);self.parts=index['parts'];self.ends=[];self.position=0;self.open_index=None;self.source=None
        total=0
        for part in self.parts:total+=part['bytes'];self.ends.append(total)
        self.total=total
    def __str__(self):return 'gpup9-split-evidence'
    def readable(self):return True
    def seekable(self):return True
    def tell(self):return self.position
    def seek(self,offset,whence=0):
        if whence==0:position=offset
        elif whence==1:position=self.position+offset
        elif whence==2:position=self.total+offset
        else:raise ValueError('invalid seek origin')
        if position<0:raise ValueError('negative seek')
        self.position=position;return position
    def read(self,size=-1):
        if size is None or size<0:size=max(0,self.total-self.position)
        size=min(size,max(0,self.total-self.position));chunks=[]
        while size:
            number=bisect.bisect_right(self.ends,self.position)
            if self.open_index!=number:
                if self.source:self.source.close()
                self.source=(self.root/self.parts[number]['path']).open('rb');self.open_index=number
            start=0 if number==0 else self.ends[number-1]
            self.source.seek(self.position-start);data=self.source.read(min(size,self.ends[number]-self.position))
            require(data,'truncated split archive');chunks.append(data);self.position+=len(data);size-=len(data)
        return b''.join(chunks)
    def close(self):
        if self.source:self.source.close()
        super().close()


class CountingWriter:
    """ZIP offsets count input bytes, independent of compressed output offsets."""
    def __init__(self,output):self.output=output;self.total=0
    def tell(self):return self.total
    def seek(self,*args):raise io.UnsupportedOperation('compression stream is not seekable')
    def write(self,data):
        self.output.write(data);self.total+=len(data);return len(data)
    def flush(self):self.output.flush()


def model_bindings(manifest, archive):
    """Omitted input hashes must agree with the retained generator manifests."""
    omitted=manifest.get('reproducible_models',{})
    entries=manifest['entries'];bound={}
    available={v['sha256'] for v in entries.values()}
    for name,item in omitted.items():
        path=Path(name)
        require(not path.is_absolute() and '..' not in path.parts and
            re.fullmatch(r'artifacts/gpup9-v1/models(?:-v2)?/[^/]+/[^/]+\.json',name), 'invalid omitted model path')
        require(name not in entries and set(item)=={'sha256','bytes'} and type(item['bytes']) is int and item['bytes']>0 and
            re.fullmatch('[0-9a-f]{64}',item['sha256']), 'invalid omitted model metadata')
    for name in entries:
        if re.fullmatch(r'artifacts/gpup9-v1/models(?:-v2)?/[^/]+/manifest\.json',name):
            value=json.loads(archive.read(name))
            require(value['generator']['sha256'] in available,'model generator source missing')
            require(entries[value['design']['path']]['sha256']==value['design']['sha256'],'model design binding differs')
            for group in value['groups'].values():
                for item in group['models']:
                    source=entries.get(item['path'],omitted.get(item['path']))
                    require(source and source['sha256']==item['sha256'],'model catalog differs')
                    bound[item['path']]=item['sha256']
    return bound


def publish():
    import zstandard
    pending=[p.name.removesuffix('.reservation.json') for p in (BASE/'resources').glob('*.reservation.json')
             if not p.with_name(p.name.replace('.reservation.json','.settlement.json')).exists()]
    paths={};omitted={}
    for path in sorted(BASE.rglob('*')):
        if not path.is_file() or path.is_symlink() or path.suffix not in ['.json','.log','.py','.sh','.rs','.toml','.lock','.md']:continue
        relative=path.relative_to(BASE)
        if relative.parts[0].startswith('portable-gpup9-'):continue
        if path.name in ['budget.lock','cpu.lock'] or path==BASE/'published-files.json':continue
        if path.parent==BASE/'resources' and any(path.name.startswith(p+'.') for p in pending):continue
        name=str(path.relative_to(ROOT))
        if relative.parts[0] in ['models','models-v2'] and path.name!='manifest.json':
            with path.open('rb') as source:sha,size=digest(source)
            omitted[name]=dict(sha256=sha,bytes=size)
        else:paths[name]=path
    implementation=load(BASE/'implementation-v5.json')
    for item in implementation['source']:
        require(ref(ROOT/item['path'])==item,'frozen implementation changed')
        paths[item['path']]=ROOT/item['path']
    for path in [Path(__file__).resolve(),ROOT/'tools/gpup9-evidence-requirements.txt']:
        paths[str(path.relative_to(ROOT))]=path
    entries={}
    for name,path in sorted(paths.items()):
        with path.open('rb') as source:sha,size=digest(source)
        entries[name]=dict(sha256=sha,bytes=size)
    manifest=dict(schema_version=1,kind='gpup9-portable-evidence',files=sorted(paths),entries=entries,
        reproducible_models=omitted,pending_administration=pending,
        limits='Responses, source versions and settled receipts embedded exactly. Generated model bytes remain local; generator versions, seeds and original byte hashes are retained. Replay checks observations and model bindings, not fresh certificates or regenerated model bytes. In-flight administration is published at closure.')
    sink=PartWriter()
    parameters=zstandard.ZstdCompressionParameters.from_level(6,window_log=25,threads=0)
    try:
        with zstandard.ZstdCompressor(compression_params=parameters).stream_writer(sink,closefd=False) as compressed:
            counter=CountingWriter(compressed)
            with zipfile.ZipFile(counter,'w',compression=zipfile.ZIP_STORED,allowZip64=True) as archive:
                archive.writestr('manifest.json',json.dumps(manifest,sort_keys=True,separators=(',',':')))
                for name,path in sorted(paths.items()):
                    info=zipfile.ZipInfo(name);info.compress_type=zipfile.ZIP_STORED;info.external_attr=0o100644<<16
                    with path.open('rb') as source,archive.open(info,'w',force_zip64=True) as dest:
                        shutil.copyfileobj(source,dest,1<<20)
            zip_bytes=counter.tell()
        value=sink.finish()
    finally:sink.finish_part()
    put(INDEX,dict(schema_version=1,kind='gpup9-split-zstd-zip-v1',**value,zip_bytes=zip_bytes,files=len(paths),pending_administration=pending))
    put(BASE/'published-files.json',dict(index=ref(INDEX),entries=entries,reproducible_models=omitted,pending_administration=pending))
    print(dict(files=len(paths),parts=len(value['parts']),bytes=value['bytes'],zip_bytes=zip_bytes,omitted_models=len(omitted),pending=pending),flush=True)


@contextmanager
def zip_payload(index,root=ROOT):
    """Decode to bounded temporary parts; cleanup also covers failed replay."""
    with PartReader(index,root) as compressed:
        if index['kind']=='gpup9-split-zip-v1':
            yield compressed
            return
        import zstandard
        with tempfile.TemporaryDirectory(prefix='gpup9-replay-') as directory:
            temporary=Path(directory);sink=PartWriter(temporary/'payload.json',root=temporary)
            try:
                with zstandard.ZstdDecompressor(max_window_size=1<<26).stream_reader(compressed,closefd=False) as source:
                    while data:=source.read(1<<20):
                        require(sink.total+len(data)<=index['zip_bytes'],'expanded archive exceeds declared size')
                        sink.write(data)
                expanded=sink.finish()
                require(expanded['bytes']==index['zip_bytes'],'expanded archive size differs')
                with PartReader(expanded,temporary) as payload:yield payload
            finally:sink.finish_part()


def verify_index(index,root=ROOT):
    fields={'schema_version','kind','parts','bytes','sha256','files','pending_administration'}
    if index.get('kind')=='gpup9-split-zstd-zip-v1':
        fields.add('zip_bytes')
        require(type(index.get('zip_bytes')) is int and 0<index['zip_bytes']<=32<<30,'expanded size limit')
    require(set(index)==fields,'index fields')
    require(index['schema_version']==1 and index['kind'] in ['gpup9-split-zip-v1','gpup9-split-zstd-zip-v1'],'index version')
    require(type(index['bytes']) is int and index['bytes']>0 and index['parts'],'empty archive')
    require(type(index['files']) is int and index['files']>0,'invalid file count')
    require(len({p['path'] for p in index['parts']})==len(index['parts']),'duplicate archive part')
    for part in index['parts']:
        require(set(part)=={'path','sha256','bytes'} and type(part['bytes']) is int and 0<part['bytes']<=CHUNK,'part fields/size')
        path=Path(part['path'])
        require(not path.is_absolute() and '..' not in path.parts,'part path escape')
        require((root/path).resolve().is_relative_to(root.resolve()/'docs/benchmarks/data'),'part outside evidence directory')


def replay(index_path=INDEX):
    index=load(index_path);verify_index(index,ROOT)
    whole=hashlib.sha256();total=0
    for part in index['parts']:
        h=hashlib.sha256();size=0
        with (ROOT/part['path']).open('rb') as source:
            while data:=source.read(1<<20):h.update(data);whole.update(data);size+=len(data)
        require(size==part['bytes'] and h.hexdigest()==part['sha256'],'part bytes changed');total+=size
    require(total==index['bytes'] and whole.hexdigest()==index['sha256'],'archive sequence changed')
    with zip_payload(index,ROOT) as payload:
        with zipfile.ZipFile(payload) as archive:
            manifest=json.loads(archive.read('manifest.json'));names=manifest['files']
            require(len(archive.namelist())==len(set(archive.namelist())),'duplicate ZIP member')
            require(len(names)==len(set(names))==index['files'],'archive file inventory')
            require(set(archive.namelist())==set(names)|{'manifest.json'},'archive extra/missing files')
            require(set(manifest['entries'])==set(names),'archive entry bindings')
            accepted={};fp4=0;native_promotions=set();bound_models=set()
            models=model_bindings(manifest,archive)
            for name in names:
                path=Path(name)
                require(not path.is_absolute() and '..' not in path.parts,'archive path escape')
                entry=manifest['entries'][name]
                require(set(entry)=={'sha256','bytes'} and type(entry['bytes']) is int and entry['bytes']>=0,'invalid embedded file metadata')
                with archive.open(name) as source:sha,size=digest(source)
                require(manifest['entries'][name]==dict(sha256=sha,bytes=size),'embedded bytes changed '+name)
                if re.fullmatch(r'artifacts/gpup9-v1/(screening|validation|holdout)/b\d{2}/.*\.session\.json',name):
                    row=json.loads(archive.read(name))
                    for record in row['records']:
                        model=record['model'];key=(model['path'],model['sha256'])
                        if key not in bound_models:
                            require(models.get(model['path'])==model['sha256'],'original model binding differs')
                            bound_models.add(key)
                if re.fullmatch(r'artifacts/gpup9-v1/(screening|validation|holdout)/b\d{2}/.*-r\d{2}\.json',name):
                    response=json.loads(archive.read(name));work=accepted_work(response);accepted[name]=work
                    if response['lane']=='fp4x2':
                        fp4+=1
                        if work['34']+work['36']==0:native_promotions.add((name,sha))
            if accepted:
                proof=json.loads(archive.read('artifacts/gpup9-v1/accepted-work.json'))
                require(proof['status']=='passed' and proof['accepted']==accepted and proof['fp4_responses']==fp4,'accepted-work replay differs')
                require({(r['path'],r['sha256']) for r in proof['all_native_promotions']}==native_promotions,'native promotion coverage differs')
                freeze=json.loads(archive.read('artifacts/gpup9-v1/holdout-freeze.json'))
                analysis=json.loads(archive.read('artifacts/gpup9-v1/analysis.json'))
                passes={(r['family'],r['endpoint']) for r in analysis['comparisons'] if r['scoped_pass']}
                for cell in freeze['cells']:
                    if (cell['family'],cell['endpoint']) in passes and freeze['configurations'][cell['config']]['lane']=='fp4x2':
                        row=json.loads(archive.read(f"artifacts/gpup9-v1/holdout/b{cell['block']:02d}/{cell['id']}.session.json"))
                        require(any(accepted[r['result']['path']]['34']+accepted[r['result']['path']]['36']>0 for r in row['records']),'held-out pass lacks accepted FP4 work')
        payload.seek(0)
        # ZipFile accepts the seekable part reader directly; no extraction or
        # oversized temporary reconstruction is required by the frozen reader.
        from lp_gpup9_evidence import replay as frozen_replay
        value=frozen_replay(payload)
    return dict(status='passed',exact_files=index['files'],bytes=total,observation_replay=value)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['publish','replay','closure']);p.add_argument('--index',type=Path,default=INDEX);a=p.parse_args()
    if a.action=='publish':publish()
    elif a.action=='replay':print(json.dumps(replay(a.index),sort_keys=True),flush=True)
    else:print(json.dumps(verify_closure(load(a.index.with_name('gpup9-closure-v1.json')),a.index),sort_keys=True),flush=True)
