"""Portable delta evidence for actual Tensor Core development; old bundles stay exact."""
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
from lp_general_tensor_analyze import CAMPAIGNS

def archive(identity):
    out=BASE/'portable'/identity;out.mkdir(parents=True,exist_ok=False)
    active={p.name.removesuffix('.reservation.json') for p in (BASE/'resources').glob('*.reservation.json') if not p.with_name(p.name.replace('.reservation.json','.settlement.json')).exists()}
    files=[]
    for p in BASE.rglob('*'):
        if not p.is_file() or p.is_symlink() or p.name.endswith('.lock'):continue
        rel=p.relative_to(BASE)
        if rel.parts[0]=='portable':continue
        if rel.parts[0].startswith('tensor-') or rel.parts[0].startswith('operational-readmission') or (rel.parts[0] in ('sources','resources') and len(rel.parts)>1 and rel.parts[1].startswith('tensor-')):
            if rel.parts[0]=='sources' and len(rel.parts)>1 and rel.parts[1] in active:continue
            if rel.parts[0]=='resources' and any(p.name.startswith(x+'.') for x in active):continue
            files.append(p)
    for name in CAMPAIGNS:
        f=load(BASE/name/'freeze.json')
        files += [ROOT/r['model']['path'] for r in f['models']]
    public=BASE/'public-development-v1/manifest.json';files.append(public);pub=load(public)
    files += [ROOT/pub['distribution_license']['path']]+[ROOT/r['source']['path'] for r in pub['models']]+[ROOT/r['model']['path'] for r in pub['models']]
    files += list((ROOT/'tools').glob('*.py'))
    files += [ROOT/'artifacts/gpup-checker2-v1/build-v5/executor']
    files += list((ROOT/'research/lp-general-lowbit/src').glob('*.rs'))+list((ROOT/'research/lp-general-lowbit/cuda').glob('*'))+list((ROOT/'research/lp-general-lowbit/tests').glob('*.rs'))
    files += [ROOT/'docs/specifications/SPEC-0045-general-lowbit-lp.md',ROOT/'docs/decisions/ADR-0079-general-lowbit-lp.md']
    # Bind and verify all pre-existing scientific bytes; mutable working sources/navigation are excluded explicitly.
    old=BASE/'portable/delivery-v2/EVIDENCE.json';prior=load(old);preserved=0
    for r in prior['files']:
        p=ROOT/r['path']
        if not p.is_relative_to(BASE):continue
        require(p.stat().st_size==r['bytes'] and digest(p)==r['sha256'],'historical scientific bytes changed '+r['path']);preserved+=1
    files += [old,BASE/'portable/delivery-v2/receipt.json',BASE/'portable/delivery-v2/replay.json']
    manifest=[];parts=[];groups=[];group=[];size=0
    for p in sorted(set(files)):
        n=p.stat().st_size
        if group and size+n>128<<20:groups.append(group);group=[];size=0
        group.append(p);size+=n
    if group:groups.append(group)
    for i,group in enumerate(groups):
        path=out/f'evidence-{i:03d}.tar.gz'
        with path.open('xb') as raw,gzip.GzipFile(fileobj=raw,mode='wb',mtime=0,compresslevel=4) as compressed,tarfile.open(fileobj=compressed,mode='w|') as tar:
            for p in group:
                name=str(p.relative_to(ROOT));manifest.append(dict(path=name,sha256=digest(p),bytes=p.stat().st_size))
                info=tar.gettarinfo(str(p),arcname=name);info.uid=info.gid=0;info.uname=info.gname='';info.mtime=0
                with p.open('rb') as source:tar.addfile(info,source)
        require(path.stat().st_size<512<<20,'compressed part exceeds file limit')
        parts.append(dict(archive=archive_ref(path),bytes=path.stat().st_size));print(dict(part=i,files=len(group),bytes=path.stat().st_size),flush=True)
    mp=out/'EVIDENCE.json';put(mp,dict(schema_version=1,files=manifest,prior_scientific_manifest=ref(old),prior_scientific_files_verified=preserved,scope='Tensor continuation delta, including failed candidates and raw scientific responses; original bundle remains separate.'))
    put(out/'receipt.json',dict(parts=parts,manifest=ref(mp),files=len(manifest),raw_bytes=sum(x['bytes'] for x in manifest),compressed_bytes=sum(x['bytes'] for x in parts),prior_scientific_files_verified=preserved))

def replay(identity):
    out=BASE/'portable'/identity;receipt=load(out/'receipt.json');manifest=ROOT/receipt['manifest']['path'];require(ref(manifest)==receipt['manifest'],'manifest differs')
    require(not (out/'replay.json').exists() and not (out/'replay.stdout').exists(),'replay attempt already exists')
    with tempfile.TemporaryDirectory(prefix='tensor-portable-',dir=ROOT/'artifacts') as temporary:
        root=Path(temporary)
        for part in receipt['parts']:
            path=ROOT/part['archive']['path'];require(archive_ref(path)==part['archive'] and path.stat().st_size==part['bytes'],'archive differs')
            with tarfile.open(path,'r:gz') as tar:tar.extractall(root,filter='data')
        items=load(manifest)['files']
        for item in items:
            p=root/item['path'];require(p.is_file() and p.stat().st_size==item['bytes'] and digest(p)==item['sha256'],'extracted bytes differ')
        checker=root/'artifacts/gpup-checker2-v1/build-v5/executor';checker.chmod(checker.stat().st_mode|0o100)
        p=subprocess.run(['python',str(root/'tools/lp_general_tensor_portable.py'),'_verify','--id',identity],cwd=root,text=True,capture_output=True,env={**os.environ,'PYTHONPATH':str(root/'tools')})
        (out/'replay.stdout').write_text(p.stdout);(out/'replay.stderr').write_text(p.stderr);require(p.returncode==0,'portable independent replay failed')
        result=json.loads(p.stdout.splitlines()[-1]);put(out/'replay.json',dict(status='passed',receipt=ref(out/'receipt.json'),byte_files=len(items),result=result,scope='extracted-root replay without original artifacts reference resolution; missingness remains'))
        print(result,flush=True)

def verify(identity):
    from lp_general_device import serial
    from lp_general_public import parse
    out=BASE/'tensor-portable-replay';out.mkdir(exist_ok=False);cells=assessments=0;missing=[];per_campaign={};checked={}
    public=load(BASE/'public-development-v1/manifest.json')
    require(ref(ROOT/public['distribution_license']['path'])==public['distribution_license'],'public license differs')
    for item in public['models']:
        source=ROOT/item['source']['path'];require(ref(source)==item['source'],'public source differs');doc,names=parse(source);require(doc==load(ROOT/item['model']['path']) and names==item['names'],'public conversion differs')
    for name in CAMPAIGNS:
        frozen=load(BASE/name/'freeze.json');count=0
        for c in frozen['cells']:
            raw=BASE/name/f'm{c["model_index"]:02d}'/(c['id']+'.stdout.jsonl')
            if not raw.exists():missing.append(dict(campaign=name,id=c['id']));continue
            r=json.loads(raw.read_text());require(sum(r['accepted'])==r['logical'] and sum(r['attempted'])==r['physical'],'work differs')
            require(all(a<=b for a,b in zip(r['accepted_product_work'],r['physical_product_work'])),'accepted exceeds physical work')
            modelref=frozen['models'][c['model_index']]['model'];model=ROOT/modelref['path'];require(ref(model)==modelref,'model differs')
            for j,ep in enumerate([*r['assessments'],r]):
                tol=c['request']['settings']['tolerance'];certificate=ep['certificate'];proof=r.get('bound_proof',[])
                expected={k:certificate[k] for k in ['accepted','feasible','objective','bound','gap_upper']}
                key=hashlib.sha256(json.dumps([modelref['sha256'],tol,ep['primal'],certificate.get('certificate_dual',ep['dual']),proof,expected],sort_keys=True,separators=(',',':')).encode()).hexdigest()
                if key not in checked:
                    checked[key]=serial(model,{**ep,'bound_proof':proof},tol,out,f'{name}-{c["id"]}-{j}')
                assessments+=1
            cells+=1;count+=1
        per_campaign[name]=count
    print(json.dumps(dict(status='passed',cells=cells,assessments=assessments,distinct_serial_assessments=len(checked),per_campaign=per_campaign,missing=missing,public_inputs=len(public['models']),root=str(ROOT),claim='Every retained scientific final/intermediate assessment is matched to an independent original serial check. Offline identical-witness/tier/proof/result deduplication only; no solver memoization or missingness repair.')),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['archive','replay','_verify']);p.add_argument('--id',required=True);a=p.parse_args();{'archive':archive,'replay':replay,'_verify':verify}[a.action](a.id)
