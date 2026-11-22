"""Lossless, verified compaction of owned evidence; restore paths before old replay."""
import argparse,hashlib,json,math,os,stat,subprocess,tarfile,time
from pathlib import Path
from lp_billion_common import BASE,ROOT,put,load,ref,resolve,require
from lp_billion_portable import arrays

def safe(path):
    p=(BASE/path).resolve()
    require(p.is_relative_to(BASE) and not (BASE/path).is_symlink(),'owned regular path')
    return p

def entry(path,expected=None):
    p=safe(path);s=p.stat();require(stat.S_ISREG(s.st_mode),'regular compaction input')
    digest=expected or p.stem
    require(len(digest)==64 and all(c in '0123456789abcdef' for c in digest),'expected content hash')
    return dict(path=path,bytes=s.st_size,sha256=digest,device=s.st_dev,inode=s.st_ino,mtime_ns=s.st_mtime_ns)

def plan(kind,identity):
    require(not (BASE/'space-compaction'/identity).exists(),'fresh compaction plan')
    entries=[];protected=set()
    if kind=='sources':
        for p in BASE.glob('image-*/binding.json'):
            d=load(p)
            if d.get('source_manifest'):protected.add(d['source_manifest']['path'].split('/')[1])
        for d in (BASE/'sources').iterdir():
            if d.name.startswith(('operational-','gpu-control-')):protected.add(d.name)
        bindings=load(BASE/'gpu-pack-settled-checkpoint-v1.json')['numerical_bindings']
        for r in bindings:
            if r['namespace']=='evidence' and r['path'].startswith('sources/'):protected.add(r['path'].split('/')[1])
        for p in sorted((BASE/'sources').glob('*/manifest.json')):
            if p.parent.name in protected:continue
            for pair in load(p)['sources']:
                r=pair['retained'];q=BASE/r['path']
                if q.exists():
                    e=entry(r['path'],r['sha256']);require(e['bytes']==r['bytes'],'source bytes');entries.append(e)
    else:
        f=load(BASE/'gpu-control-1b-v1/freeze.json')
        for c in f['cells']:
            if (BASE/'resources'/(c['id']+'.reservation.json')).exists():continue
            for a in arrays(load(resolve(c['model']))):
                protected.update(x['sha256'] for x in a['chunks'])
        for p in sorted((BASE/'objects').glob('*.bin')):
            if p.stem not in protected and p.stat().st_size >= 8<<20:entries.append(entry(str(p.relative_to(BASE))))
    require(entries and len({e['path'] for e in entries})==len(entries),'nonempty unique planned paths')
    put(BASE/'space-compaction'/identity/'plan.json',dict(status='prospective',kind=kind,entries=entries,protected=sorted(protected),
        raw_bytes=sum(e['bytes'] for e in entries),source=ref(__file__),protocol=ref(ROOT/'docs/specifications/SPEC-0046-amendment-73.md')))
    print(dict(plan=identity,files=len(entries),raw_gib=sum(e['bytes'] for e in entries)/2**30),flush=True)

def verify_archive(archive,entries):
    expected={e['path']:e for e in entries};seen=set()
    p=subprocess.Popen(['zstd','-q','-d','-c',str(archive)],stdout=subprocess.PIPE)
    try:
        with tarfile.open(fileobj=p.stdout,mode='r|') as stream:
            for member in stream:
                require(member.isfile() and member.name in expected and member.name not in seen,'exact archive members')
                e=expected[member.name];require(member.size==e['bytes'],'archive member length')
                h=hashlib.sha256();file=stream.extractfile(member)
                while chunk:=file.read(1<<20):h.update(chunk)
                require(h.hexdigest()==e['sha256'],'archive member hash '+member.name);seen.add(member.name)
        require(p.wait()==0 and seen==set(expected),'complete verified archive')
    finally:
        p.stdout.close()
        if p.poll() is None:p.kill();p.wait()

def compact(plan_path):
    d=load(plan_path);resolve(d['source']);out=plan_path.parent;archive=out/'archive.tar.zst'
    require(not archive.exists() and not (out/'result.json').exists(),'fresh compaction execution')
    entries=d['entries'];before=sum(safe(e['path']).stat().st_blocks*512 for e in entries)
    with archive.open('xb') as sink:
        p=subprocess.Popen(['zstd','-q','-T2','-1','-c'],stdin=subprocess.PIPE,stdout=sink)
        try:
            with tarfile.open(fileobj=p.stdin,mode='w|',format=tarfile.PAX_FORMAT) as stream:
                for e in entries:
                    path=safe(e['path']);s=path.stat()
                    require((s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)==(e['device'],e['inode'],e['bytes'],e['mtime_ns']),'unchanged input before packing')
                    info=tarfile.TarInfo(e['path']);info.size=e['bytes'];info.mode=stat.S_IMODE(s.st_mode)
                    with path.open('rb') as file:stream.addfile(info,file)
            p.stdin.close();require(p.wait()==0,'complete compression');sink.flush();os.fsync(sink.fileno())
        finally:
            if not p.stdin.closed:p.stdin.close()
            if p.poll() is None:p.kill();p.wait()
    verify_archive(archive,entries)
    receipt=put(out/'verified.json',dict(status='all_members_verified',plan=ref(plan_path),archive=ref(archive),files=len(entries),bytes=sum(e['bytes'] for e in entries)))
    for e in entries:
        path=safe(e['path']);s=path.stat()
        require((s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)==(e['device'],e['inode'],e['bytes'],e['mtime_ns']),'unchanged input before unlink')
        path.unlink()
    # Remove only now-empty directories beneath archived source snapshots.
    if d['kind']=='sources':
        for root,dirs,files in os.walk(BASE/'sources',topdown=False):
            try:Path(root).rmdir()
            except OSError:pass
    after=archive.stat().st_blocks*512
    put(out/'result.json',dict(status='compacted_verified',verification=receipt,source=ref(__file__),files_compacted=len(entries),
        raw_bytes=sum(e['bytes'] for e in entries),archive_bytes=archive.stat().st_size,physical_bytes_released=before-after,
        restore='python3 tools/lp_billion_compact.py restore --plan '+str(plan_path),no_foreign_files_touched=True))
    print(dict(status='compacted',files=len(entries),released_gib=(before-after)/2**30,archive_gib=archive.stat().st_size/2**30),flush=True)

def restore(plan_path):
    d=load(plan_path);archive=resolve(load(plan_path.parent/'verified.json')['archive']);expected={e['path']:e for e in d['entries']}
    p=subprocess.Popen(['zstd','-q','-d','-c',str(archive)],stdout=subprocess.PIPE)
    try:
        with tarfile.open(fileobj=p.stdout,mode='r|') as stream:
            for member in stream:
                require(member.isfile() and member.name in expected,'owned restore member')
                e=expected[member.name];dest=safe(member.name);dest.parent.mkdir(parents=True,exist_ok=True)
                temporary=dest.with_name(dest.name+'.restore-pending');h=hashlib.sha256();file=stream.extractfile(member)
                with temporary.open('xb') as out:
                    while chunk:=file.read(1<<20):h.update(chunk);out.write(chunk)
                    out.flush();os.fsync(out.fileno())
                require(temporary.stat().st_size==e['bytes'] and h.hexdigest()==e['sha256'],'restored bytes verified')
                if dest.exists():
                    require(ref(dest)['sha256']==e['sha256'],'existing restore destination exact');temporary.unlink()
                else:temporary.chmod(member.mode);temporary.rename(dest)
        require(p.wait()==0,'complete restoration')
    finally:
        p.stdout.close()
        if p.poll() is None:p.kill();p.wait()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['plan','compact','restore']);p.add_argument('--kind',choices=['sources','cold']);p.add_argument('--id');p.add_argument('--plan',type=Path);a=p.parse_args()
    if a.action=='plan':plan(a.kind,a.id)
    elif a.action=='compact':compact(a.plan)
    else:restore(a.plan)
