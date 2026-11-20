"""Bounded CPU preparation memory diagnostics; no CUDA contexts or LP solves."""
import argparse
import json
import math
import shutil
import subprocess
import sys
import time
from pathlib import Path
from lp_billion_common import BASE,ROOT,put,load,ref,resolve,require
from lp_billion_prepare_continue import job,completed
from lp_billion_memory_bounds import bounded_capacity

BUILD='bounded-memory-diagnostic-v1'
COHORT='bounded-memory-cpu-v1'
SOURCE=ROOT/'research/lp-billion-lowbit/diagnostics/memory.rs'
PYTHON=ROOT/'artifacts/gpup-copt-adapter-env/venv/bin/python'


def command(out,name,args):
    r=subprocess.run(list(map(str,args)),text=True,capture_output=True)
    (out/(name+'.stdout')).write_text(r.stdout);(out/(name+'.stderr')).write_text(r.stderr)
    if r.returncode:print(r.stdout[-2000:]+r.stderr[-4000:],flush=True)
    require(r.returncode==0,'bounded memory '+name)
    return r.stdout


def build():
    out=BASE/BUILD;out.mkdir(exist_ok=False)
    require(load(BASE/'resources/bounded-memory-quality-v1.settlement.json')['status']=='passed','CPU quality')
    before=load(BASE/'image-v8/binding.json')
    original=next(s for s in load(resolve(before['source_manifest']))['sources']
                  if s['original']['path']=='research/lp-billion-lowbit/src/tensor_prepare.rs')
    require(resolve(original['retained']).read_bytes()==(ROOT/'research/lp-billion-lowbit/src/tensor_prepare_reference.rs').read_bytes(),'retained v8 reference exact')
    command(out,'format',['rustfmt','--edition','2024','--check',SOURCE])
    command(out,'library',['cargo','build','--manifest-path','research/lp-billion-lowbit/Cargo.toml','--release','--offline','--lib','--jobs','1'])
    deps=BASE/'target/release/deps';libraries={}
    for name in ['lp_billion_lowbit','serde_json','sha2']:
        paths=list(deps.glob('lib'+name+'-*.rlib'));require(len(paths)==1,'unambiguous library '+name)
        target=out/('lib'+name+'.rlib');shutil.copyfile(paths[0],target);libraries[name]=ref(target)
    args=['rustc','--edition','2024','-C','opt-level=3','-C','debuginfo=0']
    for name,item in libraries.items():args+=['--extern',name+'='+str(resolve(item))]
    exe=out/'memory';args+=['-L','dependency='+str(deps),SOURCE,'-o',exe]
    command(out,'compile',args)
    request=out/'smoke-request.json';put(request,load(BASE/'ladder-64m-v4/freeze.json')['cells'][0]['request'])
    smokes=[]
    for family in ['dense','irregular']:
        rows=[]
        for impl in ['reference','candidate']:
            text=command(out,family+'-'+impl,[exe,BASE/('memory-gpu-v1/'+family+'.arrays.json'),BASE,request,impl])
            rows.append(json.loads(text))
        require(rows[0]['packed_sha256']==rows[1]['packed_sha256'] and rows[0]['packed_bytes']==rows[1]['packed_bytes'],'exact diagnostic smoke')
        smokes.append(dict(family=family,packed_sha256=rows[0]['packed_sha256'],exact=True))
    put(out/'result.json',dict(status='passed',source=ref(SOURCE),executable=ref(exe),libraries=libraries,
        smokes=smokes,reference_source=ref(ROOT/'research/lp-billion-lowbit/src/tensor_prepare_reference.rs'),
        retained_reference=original['retained'],image=ref(BASE/'image-v9/binding.json')))


def freeze():
    out=BASE/COHORT;out.mkdir(exist_ok=False)
    cells=[]
    for scale in ['64m','256m']:
        previous=load(BASE/f'ladder-{scale}-v4/freeze.json')['cells']
        if scale=='256m':previous=[c for c in previous if load(resolve(c['model_result']))['family']=='coupled_blocks']
        for i,c in enumerate(previous):
            model=load(resolve(c['model_result']))
            for impl in (['reference','candidate'] if i%2==0 else ['candidate','reference']):
                cells.append(dict(id=f'{COHORT}-{scale}-{i}-{impl}',family=model['family'],scale=scale,implementation=impl,
                    model=c['model'],model_result=c['model_result'],request=c['request'],seconds=240 if scale=='64m' else 480,
                    host_gib=20 if scale=='64m' else 32,disk_gib=1,status='pending',cuda=False,lp_solve=False))
    model_path=BASE/'models-1b-coupled_blocks-v1/result.json';model=load(model_path);bound=bounded_capacity(model,'fp4x2')
    cells.append(dict(id=COHORT+'-1b-candidate',family='coupled_blocks',scale='1b',implementation='candidate',
        model=model['model'],model_result=ref(model_path),request=cells[0]['request'],seconds=1800,
        host_gib=bound['CPU_preparation_host_gib'],disk_gib=1,status='pending',cuda=False,lp_solve=False,memory_bound=bound))
    from lp_billion_budget import accounting
    from lp_billion_common import CPU_CAPS,NS
    cpu,_=accounting();require(cpu['development']+4*sum(c['seconds'] for c in cells)*NS<=CPU_CAPS['development']*NS,'whole CPU diagnostic allocation')
    put(out/'freeze.json',dict(status='frozen_CPU_diagnostics_only',cells=cells,build=ref(BASE/BUILD/'result.json'),
        protocol=ref(ROOT/'docs/specifications/SPEC-0046-amendment-36.md'),source=ref(__file__),
        actual_1b_LP_solve=False,claim='Separate-process CPU preparation and packed-byte comparisons; no solve-time or GPU-admission claim.'))


def worker(index):
    freeze_path=BASE/COHORT/'freeze.json';f=load(freeze_path);cell=f['cells'][index]
    built=load(resolve(f['build']));exe=resolve(built['executable']);model=resolve(cell['model'])
    out=BASE/cell['id'];out.mkdir(exist_ok=False);request=out/'request.json';put(request,cell['request'])
    start=time.monotonic_ns();text=command(out,'preparation',[exe,model,BASE,request,cell['implementation']]);elapsed=time.monotonic_ns()-start
    r=json.loads(text);m=load(resolve(cell['model_result']))
    require(r['status']=='passed' and r['model_sha256']==cell['model']['sha256'] and r['nonzeros']==m['nonzeros'] and
            r['tile_count']==m['canonical_tiles'] and not r['lp_solve_executed'] and not r['cuda_context_created'],'complete original CPU preparation')
    if cell['implementation']=='candidate':
        bounds=bounded_capacity(m,'fp4x2');require(r['packed_bytes']<=bounds['packed_bytes_upper'],'actual final storage within derived bound')
    put(out/'result.json',dict(status='passed',raw=ref(out/'preparation.stdout'),freeze=ref(freeze_path),process_ns=elapsed))
    print(dict(cell=cell['id'],packing_seconds=r['packing_ns']/1e9,hwm_gib=r['after_drop']['hwm_bytes']/2**30),flush=True)


def plans():
    built=load(BASE/BUILD/'result.json')
    jobs=[c['id'] for c in load(BASE/COHORT/'freeze.json')['cells']]
    for version,old in [(17,15),(18,16)]:
        path=BASE/f'operational-readmissions/v{version}.json'
        require(not path.exists(),'fresh operational plan')
        plan=load(BASE/f'operational-readmissions/v{old}.json')
        plan.update(protocol=ref(ROOT/'docs/specifications/SPEC-0046-amendment-36.md'),cpu_admission_job='operational-cpu-v16',
            admission_job='operational-gpu-v16',supersedes_never_started=['operational-gpu-v15'],cpu_only_jobs=jobs,
            cpu_only_sources=[ref(SOURCE),ref(__file__),ref(ROOT/'tools/lp_billion_memory_bounds.py'),built['executable'],*built['libraries'].values()])
        put(path,plan)


def execute():
    f=load(BASE/COHORT/'freeze.json')
    for i,c in enumerate(f['cells']):
        if completed(c['id']):continue
        available=int(next(l for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')).split()[1])*1024
        if available<(c['host_gib']+4)*2**30:
            put(BASE/COHORT/(c['id']+'.capacity-refusal.json'),dict(status='never_started_capacity_refusal',host_available_bytes=available,
                host_required_bytes=(c['host_gib']+4)*2**30,cell=c['id']))
            print(dict(cell=c['id'],status='capacity_refusal'),flush=True);continue
        job(c['id'],c['seconds'],['python3','-B',__file__,'worker','--index',str(i)],phase='development',host=c['host_gib'],disk=1)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['build','freeze','plans','execute','worker']);p.add_argument('--index',type=int);a=p.parse_args()
    if a.action=='worker':worker(a.index)
    else:globals()[a.action]()
