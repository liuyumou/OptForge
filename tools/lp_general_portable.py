"""Local portable evidence: exact bytes, compact Git receipt, independent replay.

Large matrices and response streams are retained in the local compressed bundle,
not committed to Git. The verifier runs from the extracted root and cannot resolve
its relative model/checker references through the original artifacts directory.
"""
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


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
    return h.hexdigest()


def archive_ref(path):
    # Archives can exceed the ordinary JSON-artifact size. Hash in bounded memory.
    return dict(path=str(path.resolve().relative_to(ROOT)),sha256=digest(path))


def archive(identity):
    out=BASE/'portable'/identity;out.mkdir(parents=True,exist_ok=False)
    active={p.name.removesuffix('.reservation.json') for p in (BASE/'resources').glob('*.reservation.json')
            if not p.with_name(p.name.replace('.reservation.json','.settlement.json')).exists()}
    files=[]
    for p in BASE.rglob('*'):
        if not p.is_file() or p.is_symlink():continue
        rel=p.relative_to(BASE)
        if rel.parts[0]=='portable' or p.name.endswith('.lock'):continue
        # The current packaging/replay reservation is still being written.
        if rel.parts[0]=='sources' and len(rel.parts)>1 and rel.parts[1] in active:continue
        if rel.parts[0]=='resources' and any(p.name.startswith(job+'.') for job in active):continue
        files.append(p)
    files += [ROOT/'artifacts/gpup-checker2-v1/build-v5/executor']
    files += list((ROOT/'tools').glob('lp_general*.py'))
    files += [ROOT/'tools/lp_general_env.sh']
    files += [ROOT/'tools'/n for n in ['lp_baseline_common.py','lp_baseline_contract.py','validate_artifacts.py']]
    files += [ROOT/'research/lp-general-lowbit'/n for n in ['Cargo.toml','Cargo.lock','README.md']]
    files += list((ROOT/'research/lp-general-lowbit/src').glob('*.rs'))
    files += list((ROOT/'research/lp-general-lowbit/tests').glob('*.rs'))
    files += [ROOT/'research/lp-general-lowbit/deny.toml']
    files += list((ROOT/'research/lp-general-lowbit/cuda').glob('*'))
    files += list((ROOT/'research/lp-general-lowbit/upstream').glob('*'))
    files += [ROOT/'docs/specifications/SPEC-0045-general-lowbit-lp.md',ROOT/'docs/decisions/ADR-0079-general-lowbit-lp.md']
    files += [ROOT/'docs/benchmarks/lp-general-lowbit.md',ROOT/'docs/benchmarks/lp-general-lowbit-results.json']
    public=load(BASE/'public-development-v1/manifest.json')
    for item in [public['distribution_license'],*[r['source'] for r in public['models']]]:
        path=ROOT/item['path'];require(ref(path)==item,'public source binding differs');files.append(path)
    manifest=[];parts=[];groups=[];group=[];size=0;cap=128<<20
    for p in sorted(set(files)):
        n=p.stat().st_size;require(n<=cap,'individual evidence file exceeds portable part domain')
        if group and size+n>cap:groups.append(group);group=[];size=0
        group.append(p);size+=n
    if group:groups.append(group)
    for i,group in enumerate(groups):
        archive_path=out/f'evidence-{i:03d}.tar.gz'
        with archive_path.open('xb') as raw,gzip.GzipFile(fileobj=raw,mode='wb',mtime=0,compresslevel=6) as compressed,tarfile.open(fileobj=compressed,mode='w|') as tar:
            for p in group:
                name=str(p.relative_to(ROOT));item=dict(path=name,sha256=digest(p),bytes=p.stat().st_size);manifest.append(item)
                info=tar.gettarinfo(str(p),arcname=name);info.uid=info.gid=0;info.uname=info.gname='';info.mtime=0
                with p.open('rb') as f:tar.addfile(info,f)
        require(archive_path.stat().st_size<512<<20,'portable part violates unchanged file limit')
        parts.append(dict(archive=archive_ref(archive_path),bytes=archive_path.stat().st_size))
        print(dict(part=i,files=len(group),bytes=archive_path.stat().st_size),flush=True)
    excluded=[]
    for p in sorted((BASE/'portable').rglob('*')):
        if p.is_file() and not p.is_relative_to(out):excluded.append(dict(file=archive_ref(p),bytes=p.stat().st_size))
    manifest_path=out/'EVIDENCE.json'
    put(manifest_path,dict(schema_version=2,files=manifest,excluded_prior_packaging_containers=excluded,
        exclusion_scope='prior packaging copies remain local; all underlying scientific files and settled failure receipts are included'))
    put(out/'receipt.json',dict(parts=parts,manifest=ref(manifest_path),files=len(manifest),raw_bytes=sum(r['bytes'] for r in manifest),compressed_bytes=sum(r['bytes'] for r in parts),
        scope='retained general-program inputs, responses, proofs, failures, source versions and serial checker; local bundle, not a Git blob'))
    print(dict(directory=str(out),parts=len(parts),files=len(manifest),bytes=sum(r['bytes'] for r in parts)),flush=True)


def replay(identity):
    out=BASE/'portable'/identity
    require(not any((out/name).exists() for name in ['replay.stdout','replay.stderr','replay.json']),
            'portable replay identity already used; retain prior attempt')
    receipt=load(out/'receipt.json');manifest_path=ROOT/receipt['manifest']['path']
    require(ref(manifest_path)==receipt['manifest'],'portable manifest differs')
    with tempfile.TemporaryDirectory(prefix='general-portable-',dir=ROOT/'artifacts') as temporary:
        root=Path(temporary)
        for part in receipt['parts']:
            archive_path=ROOT/part['archive']['path']
            require(archive_ref(archive_path)==part['archive'] and archive_path.stat().st_size==part['bytes'],'portable archive part differs')
            with tarfile.open(archive_path,'r:gz') as tar:tar.extractall(root,filter='data')
        manifest=load(manifest_path)
        for r in manifest['files']:
            p=root/r['path'];require(p.is_file() and p.stat().st_size==r['bytes'] and digest(p)==r['sha256'],'portable bytes differ '+r['path'])
        checker=root/'artifacts/gpup-checker2-v1/build-v5/executor';checker.chmod(checker.stat().st_mode|0o100)
        command=['python',str(root/'tools/lp_general_portable.py'),'_verify','--id',identity]
        p=subprocess.run(command,cwd=root,text=True,capture_output=True,env={**os.environ,'PYTHONPATH':str(root/'tools')})
        (out/'replay.stdout').write_text(p.stdout);(out/'replay.stderr').write_text(p.stderr)
        require(p.returncode==0,'portable independent replay failed')
        result=json.loads(p.stdout.splitlines()[-1]);put(out/'replay.json',dict(status='passed',receipt=ref(out/'receipt.json'),byte_files=len(manifest['files']),result=result,
            scope='extracted-root replay; no original artifacts reference resolution'))
        print(result,flush=True)


def verify(identity):
    from lp_general_device import serial
    from lp_general_public import parse
    out=BASE/'portable-replay';out.mkdir(parents=True,exist_ok=False)
    public=load(BASE/'public-development-v1/manifest.json')
    require(ref(ROOT/public['distribution_license']['path'])==public['distribution_license'],'public license differs')
    for item in public['models']:
        source=ROOT/item['source']['path'];require(ref(source)==item['source'],'public source differs')
        doc,names=parse(source)
        require(doc==load(ROOT/item['model']['path']) and names==item['names'],'portable public conversion differs')
    cells=assessments=0;missing=[];incomplete_responses=[]
    for campaign in ['development-pilot-v1','development-extended-v1']:
        frozen=load(BASE/campaign/'freeze.json')
        for cell in frozen['cells']:
            path=BASE/campaign/f'm{cell["model_index"]:02d}'/(cell['id']+'.cell.json')
            if not path.exists():
                missing.append(dict(campaign=campaign,id=cell['id']))
                raw=path.with_name(cell['id']+'.response.jsonl')
                if raw.exists():incomplete_responses.append(dict(campaign=campaign,id=cell['id'],response=ref(raw)))
                continue
            r=load(path)
            require(all(r[k]==v for k,v in cell.items()),'portable frozen cell differs')
            response=ROOT/r['response']['path'];require(ref(response)==r['response'],'portable response binding')
            if r['process_returncode']!=0:continue
            result=json.loads(response.read_text());require(sum(result['accepted'])==result['logical'] and sum(result['attempted'])==result['physical'],'portable work accounting')
            model=ROOT/cell['model']['path'];require(ref(model)==cell['model'],'portable model differs')
            for j,ep in enumerate([*result['assessments'],result]):
                serial(model,{**ep,'bound_proof':result.get('bound_proof',[])},cell['settings']['tolerance'],out,f'{campaign}-{cell["id"]}-{j}')
                assessments+=1
            cells+=1
    print(json.dumps(dict(status='passed',cells=cells,assessments=assessments,public_inputs=len(public['models']),missing=missing,
        incomplete_responses=incomplete_responses,root=str(ROOT),claim='retained numerical replay; missing supervision or cells are not repaired')),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['archive','replay','_verify']);p.add_argument('--id',required=True);a=p.parse_args()
    {'archive':archive,'replay':replay,'_verify':verify}[a.command](a.id)
