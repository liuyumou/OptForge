"""User-authorized removal of obsolete large objects, protecting unfinished checks."""
import argparse,json,os,stat
from pathlib import Path
from lp_billion_common import BASE,ROOT,load,put,ref,resolve,require
from lp_billion_portable import arrays

def protected():
    keep=set();f=load(BASE/'gpu-control-1b-v1/freeze.json')
    for c in f['cells']:
        attempted=(BASE/'resources'/(c['id']+'.reservation.json')).exists()
        response=BASE/c['id']/'response.json';audited=(BASE/(c['id']+'-full-audit')/'result.json').exists()
        if not attempted or (response.exists() and not audited):
            for a in arrays(load(resolve(c['model']))):keep.update(x['sha256'] for x in a['chunks'])
        if response.exists() and not audited:
            for a in arrays(load(response)):keep.update(x['sha256'] for x in a['chunks'])
    return keep

def plan(identity):
    keep=protected();entries=[]
    for p in sorted((BASE/'objects').glob('*.bin')):
        if p.stem in keep:continue
        s=p.lstat()
        if s.st_size<8<<20:continue
        require(stat.S_ISREG(s.st_mode) and len(p.stem)==64 and all(c in '0123456789abcdef' for c in p.stem),'owned content-addressed object')
        entries.append(dict(path=str(p.relative_to(BASE)),sha256=p.stem,bytes=s.st_size,device=s.st_dev,inode=s.st_ino,mtime_ns=s.st_mtime_ns))
    require(entries,'obsolete large objects available')
    put(BASE/'space-pruning'/identity/'plan.json',dict(status='prospective',entries=entries,protected=sorted(keep),raw_bytes=sum(e['bytes'] for e in entries),
        source=ref(__file__),protocol=ref(ROOT/'docs/specifications/SPEC-0046-amendment-75.md'),authorization='You can just delete the old large data and release the disk space.'))
    print(dict(plan=identity,files=len(entries),obsolete_gib=sum(e['bytes'] for e in entries)/2**30,protected_chunks=len(keep)),flush=True)

def execute(plan_path,identity):
    d=load(plan_path);resolve(d['source']);resolve(d['protocol']);require(d['authorization']=='You can just delete the old large data and release the disk space.','explicit deletion authority')
    for p in (BASE/'resources').glob('*.reservation.json'):
        if not p.with_name(p.name.replace('.reservation.','.settlement.')).exists():require(p.name==identity+'.reservation.json','no concurrent owned work')
    keep=protected();require(not any(e['sha256'] in keep for e in d['entries']),'all unfinished input/proof data protected')
    out=plan_path.parent;logical=physical=count=0
    with (out/'deleted.jsonl').open('x') as log:
        for e in d['entries']:
            p=BASE/e['path'];require(p.parent==BASE/'objects' and not p.is_symlink(),'owned flat object only')
            s=p.stat();require((s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)==(e['device'],e['inode'],e['bytes'],e['mtime_ns']),'unchanged object before deletion')
            p.unlink();logical+=s.st_size;physical+=s.st_blocks*512 if s.st_nlink==1 else 0;count+=1
            log.write(json.dumps(dict(path=e['path'],sha256=e['sha256'],bytes=e['bytes']))+'\n');log.flush()
        os.fsync(log.fileno())
    require(all((BASE/'objects'/(h+'.bin')).is_file() for h in keep),'every protected chunk remains')
    put(out/'result.json',dict(status='obsolete_large_objects_deleted',plan=ref(plan_path),deleted=ref(out/'deleted.jsonl'),files_deleted=count,
        logical_bytes_deleted=logical,allocated_bytes_released=physical,protected_chunks=len(keep),source=ref(__file__),
        retention_limit='Deleted raw chunks require regeneration for historical replay; timing, certificate and failure records remain.'))
    print(dict(status='deleted',files=count,released_gib=physical/2**30),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['plan','execute']);p.add_argument('--id',required=True);p.add_argument('--plan',type=Path);a=p.parse_args()
    plan(a.id) if a.action=='plan' else execute(a.plan,a.id)
