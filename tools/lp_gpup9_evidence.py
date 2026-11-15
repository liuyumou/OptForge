"""Portable exact-byte observation replay and historical preservation for GPUP-9."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile
from lp_gpup9_common import BASE, ROOT, load, put, ref, require
from lp_gpup9_analysis import assess, screening_effects
from lp_gpup9_protocol import select

ARCHIVE=ROOT/'docs/benchmarks/data/gpup9-v1.zip'


def historical():
    require(not (BASE/'historical.json').exists(),'history snapshot already exists')
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    names=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
    put(BASE/'historical.json',dict(revision=revision,files=[ref(ROOT/n) for n in names if n]))


def preserve():
    history=load(BASE/'historical.json');exceptions=['AGENTS.md','state/active-task.md','state/backlog.yaml',
        'docs/plans/gpu-lp-precision-roadmap.md','README.md','CHANGELOG.md','docs/index.md']
    unchanged=0;appended=[]
    for item in history['files']:
        path=ROOT/item['path']
        if item['path'] in exceptions:
            old=subprocess.check_output(['git','show',history['revision']+':'+item['path']],cwd=ROOT)
            current=path.read_bytes()
            if item['path']=='state/backlog.yaml':
                # Only the current task and routing line may change.
                def rest(raw):
                    text=raw.decode();start=text.index('  - id: GPUP-9\n');end=text.index('  - id: GPUP-10\n',start)
                    return [line for line in (text[:start]+text[end:]).splitlines()
                            if not line.startswith(('next_ready_task:', '# Current GPUP-9'))]
                require(rest(old)==rest(current),'unrelated backlog changed')
            else:
                body=old.split(b'\n',1)[1]
                require(body in current,'historical navigation text changed '+item['path'])
            appended.append(item['path'])
        else:require(ref(path)==item,'historical bytes changed '+item['path']);unchanged+=1
    return dict(status='passed',unchanged_files=unchanged,navigation=appended,baseline=history['revision'])


def pack():
    paths={}
    # Exact responses, trial intentions/failures, sources and receipts. Large original
    # model bytes are reproducible from the frozen generator; their hashes stay bound.
    for path in sorted(BASE.rglob('*')):
        if not path.is_file() or path.suffix not in ['.json','.log','.py','.sh','.rs','.toml','.lock','.md']:continue
        if any(part.startswith('models') for part in path.relative_to(BASE).parts) and path.name!='manifest.json':continue
        if path.name in ['budget.lock','cpu.lock']:continue
        paths[str(path.relative_to(ROOT))]=path
    implementation=load(BASE/'implementation-v5.json') if (BASE/'implementation-v5.json').exists() else load(BASE/'design-v2.json')
    for item in implementation['source']:
        paths[item['path']]=ROOT/item['path']
    value=dict(schema_version=1,kind='gpup9-portable-evidence',files=sorted(paths),
        limits='Original model bytes are generator-reproducible, not embedded; offline replay verifies observations/selection/statistics, not fresh serial certificates.')
    ARCHIVE.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(ARCHIVE,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        archive.writestr('manifest.json',json.dumps(value,sort_keys=True))
        for name,path in sorted(paths.items()):archive.write(path,name)
    print(dict(archive=str(ARCHIVE),files=len(paths),bytes=ARCHIVE.stat().st_size),flush=True)


def replay(path=ARCHIVE):
    archive=zipfile.ZipFile(path)
    bundle=json.loads(archive.read('manifest.json'));raw=set(bundle['files'])
    require(bundle['kind']=='gpup9-portable-evidence' and bundle['schema_version']==1,'archive schema')
    require(len(raw)==len(bundle['files']) and set(archive.namelist())==raw|{'manifest.json'},'portable archive inventory')
    def read(relative):return json.loads(archive.read('artifacts/gpup9-v1/'+relative))
    def bind(item):
        require(item['path'] in raw,'portable file missing '+item['path'])
        require(hashlib.sha256(archive.read(item['path'])).hexdigest()==item['sha256'],'portable bytes changed')
    design=read('design-v2.json')
    implementation=read('implementation-v5.json') if 'artifacts/gpup9-v1/implementation-v5.json' in raw else design
    for source in implementation['source']:bind(source)
    total=0
    for stage in ['screening','validation','holdout']:
        freeze_key=f'artifacts/gpup9-v1/{stage}-freeze.json'
        if freeze_key not in raw:continue
        f=read(stage+'-freeze.json');bind(f['design']);bind(f['implementation']);rs=[];missing=[]
        for cell in f['cells']:
            name=f"{stage}/b{cell['block']:02d}/{cell['id']}.session.json"
            if 'artifacts/gpup9-v1/'+name not in raw:missing.append(cell);continue
            r=read(name)
            from lp_gpup9_schema import validate_session
            validate_session(r)
            require(all(r[k]==v for k,v in cell.items()),'portable cell differs')
            require(r['count']==len(r['records']),'portable request coverage')
            require(r['complete_session_ns']>=r['setup_ns']+r['teardown_ns']+sum(x['complete_ns'] for x in r['records']),'portable cost partition')
            cfg=f['configurations'][r['config']]
            for record in r['records']:
                bind(record['result']);response=json.loads(archive.read(record['result']['path']))
                require(response['model_sha256']==record['model']['sha256'],'portable model ownership')
                require(response['image_sha256']==design['image']['sha256'] and response['checker_binary_sha256']==design['binary']['sha256'],'portable executable binding')
                require(response['lane']==cfg['lane'] and response['window_max']==cfg['window_max'],'portable config binding')
                for key in ['certified','physical','logical','attempted','gpu_us','costs_ns','final_lane']:
                    require(record[key]==response[key],'portable response summary')
                total+=1
            rs.append(r)
        if stage=='holdout':require(assess(f,rs,missing)==read('analysis.json'),'portable analysis differs')
        elif not missing and f'artifacts/gpup9-v1/{stage}-selection.json' in raw:
            expected=read(stage+'-selection.json');actual=select(stage,rs,f['cells'],f['configurations'])
            require(all(expected[k]==v for k,v in actual.items()),'portable selection differs')
            if stage=='screening':require(screening_effects(f,rs)==read('screening-effects.json'),'portable interactions differ')
    return dict(status='passed',verified_solve_responses=total,files=len(raw),artifact=str(path))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['historical','preserve','pack','replay']);p.add_argument('--archive',type=Path,default=ARCHIVE);a=p.parse_args()
    if a.action=='historical':historical()
    elif a.action=='preserve':put(BASE/'preservation.json',preserve())
    elif a.action=='pack':pack()
    else:print(replay(a.archive),flush=True)
