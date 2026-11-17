"""Local scale evidence delta with exact-byte restoration and serial replay."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
from lp_general_common import BASE,ROOT,load,put,require
from lp_general_portable import digest,archive_ref as ref
from lp_general_scale_evidence import read as read_response,KIND,CHUNK
from lp_general_oracle import settings

def verify_streams(paths):
    streams=0;raw_bytes=0;partial=[]
    for p in paths:
        if p.suffix not in ['.json','.jsonl']:continue
        with p.open('rb') as source:header=source.read(256)
        if KIND.encode() not in header:continue
        try:
            m=json.loads(p.read_text());require(m['kind']==KIND and 0<m['raw_bytes']<=4<<30,'stream manifest domain')
            h=hashlib.sha256();total=0
            for item in m['parts']:
                part=ROOT/item['path'];require(ref(part)==item,'stream chunk hash')
                with gzip.open(part,'rb') as z:data=z.read(CHUNK+1)
                require(len(data)<=CHUNK,'stream chunk bound');total+=len(data);h.update(data)
            require(total==m['raw_bytes'] and h.hexdigest()==m['raw_sha256'],'exact raw stream differs')
            streams+=1;raw_bytes+=total
        except (ValueError,EOFError,OSError) as error:
            sp=BASE/'resources'/(p.parent.parent.name+'-'+p.parent.name+'.settlement.json')
            require(sp.exists() and load(sp)['status']=='refused','invalid stream outside a retained failed group')
            partial.append(dict(path=str(p.relative_to(ROOT)),error=type(error).__name__))
    return dict(streams=streams,raw_bytes=raw_bytes,partial=partial)


def archive(identity):
    out=BASE/'portable'/identity;out.mkdir(parents=True,exist_ok=False)
    active={p.name.removesuffix('.reservation.json') for p in (BASE/'resources').glob('*.reservation.json')
            if not p.with_name(p.name.replace('.reservation.json','.settlement.json')).exists()}
    files=[];campaigns=[]
    for p in BASE.rglob('*'):
        if not p.is_file() or p.is_symlink() or p.name.endswith('.lock'):continue
        rel=p.relative_to(BASE)
        if rel.parts[0]=='portable':continue
        if rel.parts[0].startswith('scale-') or (rel.parts[0] in ['resources','sources'] and len(rel.parts)>1 and rel.parts[1].startswith('scale-')):
            if rel.parts[0]=='sources' and rel.parts[1] in active:continue
            if rel.parts[0]=='resources' and any(p.name.startswith(a+'.') for a in active):continue
            files.append(p)
    for p in sorted(BASE.glob('scale-*/freeze.json')):
        f=load(p)
        if f.get('mode') not in ['pilot','scale','broad','admission']:continue
        campaigns.append(p.parent.name)
        files += [ROOT/m['model']['path'] for m in f['models']]
        files += [ROOT/m['construction']['path'] for m in f['models'] if 'construction' in m]
        files += [ROOT/f[k]['path'] for k in ['binary','image','harness','baseline_worker']]
        files += [ROOT/c['binary']['path'] for c in f['cells'] if 'binary' in c]
    files += list((ROOT/'tools').glob('*.py'))
    files += list(BASE.glob('operational-readmission*.json'))
    files += list((ROOT/'docs/benchmarks').glob('lp-general-scale*'))
    files += [ROOT/p for p in ['AGENTS.md','docs/specifications/SPEC-0045-general-lowbit-lp.md',
        'docs/plans/lp-benchmark-scaling.md','docs/plans/gpu-lp-precision-roadmap.md','research/lp-general-lowbit/README.md']]
    prior=[];preserved={}
    for name in ['delivery-v2','tensor-delivery-v1','fast-delivery-v1','fast-overhead-delivery-v1']:
        p=BASE/'portable'/name/'EVIDENCE.json';prior.append(ref(p));files.append(p)
        for item in load(p)['files']:
            q=ROOT/item['path']
            if not q.is_relative_to(BASE) or item['path'] in preserved:continue
            require(q.stat().st_size==item['bytes'] and digest(q)==item['sha256'],'historical scientific bytes changed '+str(q))
            preserved[item['path']]=item['sha256']
    streams=verify_streams(sorted(set(files)))
    manifest=[];objects={}
    for p in sorted(set(files)):
        h=digest(p);n=p.stat().st_size
        manifest.append(dict(path=str(p.relative_to(ROOT)),sha256=h,bytes=n));objects.setdefault(h,p)
    # Mutable working paths may now hold a newer worker. Its frozen bytes must
    # still exist as a retained source object, independently of the latest copy.
    for name in campaigns:
        f=load(BASE/name/'freeze.json')
        for model in f['models']:
            for key in ['model','construction']:
                if key in model:require(ref(ROOT/model[key]['path'])==model[key],'frozen input differs '+name)
        for key in ['binary','image','harness','baseline_worker','evidence_worker']:
            if key in f:require(f[key]['sha256'] in objects,'missing frozen '+key+' for '+name)
    groups=[];group=[];size=0
    for h,p in sorted(objects.items()):
        n=p.stat().st_size
        require(n<=512<<20,'individual evidence file exceeds unchanged file ceiling')
        if group and size+n>128<<20:groups.append(group);group=[];size=0
        group.append((h,p));size+=n
    if group:groups.append(group)
    parts=[]
    for i,group in enumerate(groups):
        path=out/f'objects-{i:03d}.tar.gz'
        with path.open('xb') as raw,gzip.GzipFile(fileobj=raw,mode='wb',mtime=0,compresslevel=1) as z,tarfile.open(fileobj=z,mode='w|') as tar:
            for h,p in group:
                info=tar.gettarinfo(str(p),arcname='objects/'+h);info.uid=info.gid=0;info.uname=info.gname='';info.mtime=0
                with p.open('rb') as source:tar.addfile(info,source)
        require(path.stat().st_size<512<<20,'archive part ceiling');parts.append(dict(archive=ref(path),bytes=path.stat().st_size))
        print(dict(part=i,bytes=path.stat().st_size),flush=True)
    mp=out/'EVIDENCE.json';put(mp,dict(files=manifest,campaigns=campaigns,prior=prior,preserved_scientific_files=len(preserved)))
    put(out/'receipt.json',dict(manifest=ref(mp),parts=parts,files=len(manifest),unique_objects=len(objects),unique_bytes=sum(p.stat().st_size for p in objects.values()),
        logical_bytes=sum(r['bytes'] for r in manifest),compressed_bytes=sum(p['bytes'] for p in parts),prior_scientific_files_verified=len(preserved),raw_stream_validation=streams))


def replay(identity):
    out=BASE/'portable'/identity;r=load(out/'receipt.json');mp=ROOT/r['manifest']['path']
    require(ref(mp)==r['manifest'],'evidence manifest differs')
    require(not (out/'replay.stdout').exists(),'replay identity already used')
    with tempfile.TemporaryDirectory(prefix='scale-portable-',dir=ROOT/'artifacts') as temp:
        root=Path(temp);m=load(mp)
        for part in r['parts']:
            p=ROOT/part['archive']['path'];require(ref(p)==part['archive'],'archive hash differs')
            with tarfile.open(p,'r:gz') as tar:tar.extractall(root,filter='data')
        checked=set()
        for item in m['files']:
            source=root/'objects'/item['sha256'];require(source.stat().st_size==item['bytes'],'object length differs')
            if item['sha256'] not in checked:require(digest(source)==item['sha256'],'object hash differs');checked.add(item['sha256'])
            dest=root/item['path'];dest.parent.mkdir(parents=True,exist_ok=True);os.link(source,dest)
        put(root/'scale-campaigns.json',m['campaigns'])
        binary=root/'artifacts/gpup-general-v1/scale-image-v6/executor';binary.chmod(binary.stat().st_mode|0o100)
        p=subprocess.run(['python3',str(root/'tools/lp_general_scale_portable.py'),'_verify','--id',identity],cwd=root,text=True,capture_output=True,
                         env={**os.environ,'PYTHONPATH':str(root/'tools')})
        (out/'replay.stdout').write_text(p.stdout);(out/'replay.stderr').write_text(p.stderr)
        require(p.returncode==0,'extracted-root serial replay failed')
        result=json.loads(p.stdout.splitlines()[-1]);put(out/'replay.json',dict(status='passed',receipt=ref(out/'receipt.json'),byte_files=len(m['files']),result=result));print(result,flush=True)


def verify(identity,campaigns=None):
    binary=BASE/'scale-image-v6/executor';seen=set();assessments=0;cells=0;raw_only=0;missing=[];admissions=0;partial=[]
    baseline_admissions=0;baseline_expected={}
    identities=campaigns if campaigns is not None else load(ROOT/'scale-campaigns.json')
    excluded={p.parent.name for p in BASE.glob('scale-*/freeze.json')} - set(identities)
    streams=verify_streams(p for p in BASE.rglob('*') if p.is_file() and p.relative_to(BASE).parts[0] not in excluded|{'portable'})
    # Group by immutable model to reuse only original certificate geometry.
    groups={}
    for name in identities:
        f=load(BASE/name/'freeze.json')
        for c in f['cells']:
            path=BASE/name/f'm{c["model_index"]:02d}'/(c['id']+'.response.json')
            model=ROOT/f['models'][c['model_index']]['model']['path']
            if not path.exists():missing.append(dict(campaign=name,cell=c['id']));continue
            cell=path.with_name(path.name.replace('.response.json','.cell.json'))
            if not cell.exists():raw_only+=1;missing.append(dict(campaign=name,cell=c['id'],raw_retained=True))
            else:
                row=load(cell);require(ref(path)==row['response'],'completed response binding differs')
                for key in ['serial','audit']:
                    if row.get(key):require(ref(ROOT/row[key]['path'])==row[key],'independent stream binding differs')
            groups.setdefault(model,[]).append((path,c['tolerance'],cell if cell.exists() else None));cells+=1
    for directory in sorted(BASE.glob('scale-*')):
        if (directory/'freeze.json').exists():continue
        for p in sorted(directory.glob('*.response.json')):
            r=read_response(p);model=next((q for q in directory.glob('*.lpcsr') if digest(q)==r.get('model_sha256')),None)
            require(model is not None,'admission original input missing')
            groups.setdefault(model,[]).append((p,r['certificate']['tolerance'],None));admissions+=1
        for p in sorted(directory.glob('*.copt.json')):
            r=load(p);require(r['kind']=='general-scale-COPT-baseline','baseline admission type')
            model=next((q for q in directory.glob('*.lpcsr') if digest(q)==r['model_sha256']),None)
            require(model is not None,'baseline admission original input missing')
            tolerance=r['parameters']['FeasTol']
            if r['has_solution']:
                proof=load(p.with_name(p.name.replace('.copt.json','.serial.json')))
                baseline_expected[p]={k:proof[k] for k in ['accepted','feasible','objective','bound','gap_upper']}
                baseline_expected[p]['tolerance']=tolerance
            else:
                require(r['status']==8 and r['primal'] is None and r['dual'] is None,'baseline admission no-solution report')
            groups.setdefault(model,[]).append((p,tolerance,None));baseline_admissions+=1
    for model,items in groups.items():
        model_hash=digest(model)
        child=subprocess.Popen([str(binary),'assess-proven',str(model)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
        try:
            for path,tolerance,cell in items:
                try:r=read_response(path)
                except (ValueError,EOFError,OSError) as error:
                    require(cell is None,'completed cell has unreadable response')
                    settlement=BASE/'resources'/(path.parent.parent.name+'-'+path.parent.name+'.settlement.json')
                    require(settlement.exists() and load(settlement)['status']=='refused','unreadable response without a retained failed group')
                    partial.append(dict(path=str(path.relative_to(ROOT)),error=type(error).__name__));continue
                copt=r.get('kind')=='general-scale-COPT-baseline'
                require(r['model_sha256']==model_hash,'response original-model identity differs')
                if copt:
                    eps=[r] if r['has_solution'] else []
                else:
                    require(sum(r['accepted'])==r['logical'] and sum(r['attempted'])==r['physical'],'work ledger differs')
                    require(all(a<=b for a,b in zip(r['accepted_product_work'],r['physical_product_work'])),'accepted work exceeds physical')
                    eps=[*r['assessments'],r]
                for index,e in enumerate(eps):
                    request=dict(settings={**settings(),'tolerance':tolerance},primal=e['primal'],dual=e['dual'])
                    line=json.dumps(request,separators=(',',':'))+'\n'
                    key=hashlib.sha256((model_hash+line).encode()).hexdigest()
                    expected=load(cell)['certificate'] if copt and cell else baseline_expected.get(path) if copt else e['certificate']
                    # Include expected output in dedup key, so inconsistent saved
                    # certificates cannot hide behind an identical endpoint.
                    key+=hashlib.sha256(json.dumps(expected,sort_keys=True).encode()).hexdigest()
                    if key not in seen:
                        child.stdin.write(line);child.stdin.flush();answer=child.stdout.readline()
                        require(bool(answer),'serial checker ended early');observed=json.loads(answer)
                        if expected is not None:
                            canonical=lambda v:{k:x for k,x in v.items() if k not in ['model_sha256','bound_proof']}
                            require(canonical(observed)==canonical(expected),'serial certificate differs '+str(path))
                        seen.add(key)
                    assessments+=1
                del eps,r
            child.stdin.close();require(child.wait()==0,'serial checker process failed '+child.stderr.read())
        finally:
            if child.poll() is None:child.kill();child.wait()
        print(json.dumps(dict(model=model.name,assessments=assessments,distinct=len(seen))),flush=True)
    print(json.dumps(dict(status='passed',cells=cells,admission_responses=admissions,baseline_admission_responses=baseline_admissions,assessments=assessments,distinct_assessments=len(seen),raw_only=raw_only,partial_responses=partial,missing=missing,raw_stream_validation=streams,
        claim='Exact archived bytes and CPU original-model replay from extracted root. Raw-only checking does not repair missing historical supervision or cell receipts.')),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['archive','replay','_verify']);p.add_argument('--id',required=True);p.add_argument('--campaigns',nargs='+');a=p.parse_args()
    if a.action=='_verify':verify(a.id,a.campaigns)
    else:
        require(a.campaigns is None,'campaign filtering is admission-only')
        {'archive':archive,'replay':replay}[a.action](a.id)
