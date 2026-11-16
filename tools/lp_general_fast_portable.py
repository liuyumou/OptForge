"""Content-addressed local evidence: repeated source snapshots occupy one object."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
from lp_general_common import BASE,ROOT,load,put,ref,require
from lp_general_portable import digest,archive_ref


def archive(identity):
    out=BASE/'portable'/identity;out.mkdir(parents=True,exist_ok=False);files=[];campaigns=[]
    active={p.name.removesuffix('.reservation.json') for p in (BASE/'resources').glob('*.reservation.json') if not p.with_name(p.name.replace('.reservation.json','.settlement.json')).exists()}
    for p in BASE.rglob('*'):
        if not p.is_file() or p.is_symlink() or p.name.endswith('.lock'):continue
        rel=p.relative_to(BASE)
        if rel.parts[0]=='portable':continue
        if rel.parts[0].startswith('fast-') or (rel.parts[0] in ['resources','sources'] and len(rel.parts)>1 and rel.parts[1].startswith('fast-')):
            if rel.parts[0]=='sources' and rel.parts[1] in active:continue
            if rel.parts[0]=='resources' and any(p.name.startswith(a+'.') for a in active):continue
            files.append(p)
    for p in sorted(BASE.glob('fast-*/freeze.json')):
        f=load(p)
        if f.get('kind')=='fast-proposal-development':
            campaigns.append(p.parent.name)
            files += [ROOT/m['model']['path'] for m in f['models']]
            files += [ROOT/c[k]['path'] for c in f['cells'] for k in ['binary','image']]
    files += list((ROOT/'tools').glob('*.py'))+[ROOT/'artifacts/gpup-checker2-v1/build-v5/executor']
    files += [ROOT/p for p in ['docs/benchmarks/lp-general-fast.md','docs/benchmarks/lp-general-fast-results.json','docs/benchmarks/lp-general-fast-profile-results.json','docs/specifications/SPEC-0045-general-lowbit-lp.md','docs/decisions/ADR-0079-general-lowbit-lp.md','research/lp-general-lowbit/README.md']]
    public=BASE/'public-development-v1/manifest.json';pub=load(public);files += [public,ROOT/pub['distribution_license']['path']]
    files += [ROOT/m[k]['path'] for m in pub['models'] for k in ['source','model']]
    prior=[];preserved={}
    for name in ['delivery-v2','tensor-delivery-v1']:
        mp=BASE/'portable'/name/'EVIDENCE.json';prior.append(ref(mp));files.append(mp)
        for item in load(mp)['files']:
            p=ROOT/item['path']
            if not p.is_relative_to(BASE) or item['path'] in preserved:continue
            require(p.stat().st_size==item['bytes'] and digest(p)==item['sha256'],'historical bytes changed '+str(p));preserved[item['path']]=item['sha256']
    diagnosis=ROOT/'docs/benchmarks/lp-general-tensor-diagnosis-results.json'
    files.append(diagnosis)
    diagnosis_items=load(diagnosis)['artifact_files']
    for item in diagnosis_items:
        require(ref(ROOT/item['path'])==item,'historical diagnostic bytes changed '+item['path'])
    manifest=[];objects={}
    for p in sorted(set(files)):
        h=digest(p);n=p.stat().st_size;manifest.append(dict(path=str(p.relative_to(ROOT)),sha256=h,bytes=n));objects.setdefault(h,p)
    groups=[];group=[];size=0
    for h,p in sorted(objects.items()):
        n=p.stat().st_size
        if group and size+n>128<<20:groups.append(group);group=[];size=0
        group.append((h,p));size+=n
    if group:groups.append(group)
    parts=[]
    for i,group in enumerate(groups):
        path=out/f'objects-{i:03d}.tar.gz'
        with path.open('xb') as raw,gzip.GzipFile(fileobj=raw,mode='wb',mtime=0,compresslevel=4) as z,tarfile.open(fileobj=z,mode='w|') as tar:
            for h,p in group:
                info=tar.gettarinfo(str(p),arcname='objects/'+h);info.uid=info.gid=0;info.uname=info.gname='';info.mtime=0
                with p.open('rb') as source:tar.addfile(info,source)
        require(path.stat().st_size<512<<20,'part limit');parts.append(dict(archive=archive_ref(path),bytes=path.stat().st_size))
        print(dict(part=i,objects=len(group),bytes=path.stat().st_size),flush=True)
    mp=out/'EVIDENCE.json';put(mp,dict(files=manifest,campaigns=campaigns,prior=prior,preserved_scientific_files=len(preserved),unique_objects=len(objects),unique_bytes=sum(p.stat().st_size for p in objects.values())))
    put(out/'receipt.json',dict(manifest=ref(mp),parts=parts,files=len(manifest),logical_bytes=sum(r['bytes'] for r in manifest),unique_objects=len(objects),unique_bytes=sum(p.stat().st_size for p in objects.values()),compressed_bytes=sum(p['bytes'] for p in parts),prior_scientific_files_verified=len(preserved),prior_diagnostic_files_verified=len(diagnosis_items)))


def replay(identity):
    out=BASE/'portable'/identity;receipt=load(out/'receipt.json');mp=ROOT/receipt['manifest']['path'];require(ref(mp)==receipt['manifest'],'manifest differs')
    require(not (out/'replay.stdout').exists(),'no replay retry')
    with tempfile.TemporaryDirectory(prefix='fast-portable-',dir=ROOT/'artifacts') as temp:
        root=Path(temp);m=load(mp)
        for part in receipt['parts']:
            p=ROOT/part['archive']['path'];require(archive_ref(p)==part['archive'],'archive differs')
            with tarfile.open(p,'r:gz') as tar:tar.extractall(root,filter='data')
        verified_objects=set()
        for item in m['files']:
            source=root/'objects'/item['sha256']
            require(source.stat().st_size==item['bytes'],'object size differs')
            if item['sha256'] not in verified_objects:
                require(digest(source)==item['sha256'],'object differs');verified_objects.add(item['sha256'])
            dest=root/item['path'];dest.parent.mkdir(parents=True,exist_ok=True);os.link(source,dest)
        put(root/'campaigns.json',m['campaigns']);checker=root/'artifacts/gpup-checker2-v1/build-v5/executor';checker.chmod(checker.stat().st_mode|0o100)
        p=subprocess.run(['python',str(root/'tools/lp_general_fast_portable.py'),'_verify','--id',identity],cwd=root,text=True,capture_output=True,env={**os.environ,'PYTHONPATH':str(root/'tools')})
        (out/'replay.stdout').write_text(p.stdout);(out/'replay.stderr').write_text(p.stderr);require(p.returncode==0,'portable replay failed')
        result=json.loads(p.stdout.splitlines()[-1]);put(out/'replay.json',dict(status='passed',receipt=ref(out/'receipt.json'),byte_files=len(m['files']),result=result));print(result,flush=True)


def verify(identity):
    from lp_general_device import serial
    from lp_general_fast import expected
    from lp_general_public import parse
    out=BASE/'fast-portable-replay';out.mkdir(exist_ok=False);checked={};model_hashes={};assessments=0;cells=0;probes=0;products=0;admission_solves=0;missing=[]
    def check(model,r,tol):
        nonlocal assessments
        require(r['certified']==(r['status']=='certified' and r['certificate']['accepted']),'certificate/status authority differs')
        if model not in model_hashes:model_hashes[model]=digest(model)
        for ep in [*r['assessments'],r]:
            certificate=ep['certificate'];proof=r.get('bound_proof',[]);result={k:certificate[k] for k in ['accepted','feasible','objective','bound','gap_upper']}
            key=hashlib.sha256(json.dumps([model_hashes[model],tol,ep['primal'],certificate.get('certificate_dual',ep['dual']),proof,result],sort_keys=True,separators=(',',':')).encode()).hexdigest()
            if key not in checked:checked[key]=serial(model,{**ep,'bound_proof':proof},tol,out,str(len(checked)))
            assessments+=1
        require(sum(r['accepted'])==r['logical'] and sum(r['attempted'])==r['physical'],'iteration ledger')
        require(all(a<=b for a,b in zip(r['accepted_product_work'],r['physical_product_work'])),'work ledger')
    for name in load(ROOT/'campaigns.json'):
        f=load(BASE/name/'freeze.json')
        for c in f['cells']:
            raw=BASE/name/f'm{c["model_index"]:02d}'/(c['id']+'.stdout.jsonl')
            if not raw.exists():missing.append(dict(campaign=name,id=c['id']));continue
            r=load(raw);model=ROOT/f['models'][c['model_index']]['model']['path'];check(model,r,c['tolerance']);cells+=1
            if f['pilot']:require(r['physical']==500,'fixed-work pilot differs')
    for directory in sorted(BASE.glob('fast-*/invocations')):
        for p in sorted(directory.glob('*.json')):
            command=load(p);args=command['argv'];mode=next((s for s in args if s in ['gpu-fast','gpu-fast-probe']),None)
            if mode is None or command['returncode']!=0:continue
            stdout=p.with_suffix('.stdout').read_text();responses=[json.loads(s) for s in stdout.splitlines() if s.startswith('{')];require(len(responses)==1,'raw response')
            r=responses[0];request=load(p.with_suffix('.input.jsonl'))
            if mode=='gpu-fast-probe':
                oracle=expected(r,request,r['lanes'][int(request['transpose'])]);require(r['proposal_values']==oracle and r['enclosed'] is False,'independent proposal replay');probes+=1;products+=len(oracle)
            else:
                original=args[args.index(mode)+1];model=ROOT/'artifacts'/original.split('/artifacts/',1)[1];check(model,r,request['settings']['tolerance']);admission_solves+=1
    public=load(BASE/'public-development-v1/manifest.json')
    for item in public['models']:
        source=ROOT/item['source']['path'];require(ref(source)==item['source'],'public source');doc,names=parse(source);require(doc==load(ROOT/item['model']['path']) and names==item['names'],'public parse')
    print(json.dumps(dict(status='passed',cells=cells,admission_solves=admission_solves,assessments=assessments,distinct_assessments=len(checked),probes=probes,product_outputs=products,missing=missing,root=str(ROOT),claim='Extracted-root byte and independent arithmetic/certificate replay. Identical offline witnesses deduplicated; no solver answer reuse or missingness repair.')),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['archive','replay','_verify']);p.add_argument('--id',required=True);a=p.parse_args();{'archive':archive,'replay':replay,'_verify':verify}[a.action](a.id)
