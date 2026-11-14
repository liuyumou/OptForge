"""Immutable factorial cohorts and 32 independently restarted confirmation blocks."""
import argparse
import itertools
import json
import os
from pathlib import Path
import random
import statistics
import subprocess
import time
from lp_delivery3_common import ROOT, BASE, BINARY, VARIANTS, LANES, TIERS, load, put, ref, require
from lp_delivery3_cpu import environment, numerical_source
from lp_delivery3_transport import Service, deliver
from lp_delivery2_study import matches

PARENT=ROOT/'artifacts/gpup-fp4-accel-v1/study-v1'
DIAGNOSTIC=('dense-generic-512','coupled-equality','fixed-active-bounds','irregular-tail-33')
SEED=340067


def snapshot():
    rows={}
    commands={'device':['nvidia-smi','--query-gpu=uuid,temperature.gpu,clocks.sm,clocks.mem,utilization.gpu,memory.used,power.draw','--format=csv,noheader,nounits'],
              'processes':['nvidia-smi','--query-compute-apps=gpu_uuid,pid,process_name,used_memory','--format=csv,noheader,nounits']}
    for name,command in commands.items():
        result=subprocess.run(command,capture_output=True,text=True,timeout=10)
        rows[name]=dict(returncode=result.returncode,stdout=result.stdout,stderr=result.stderr)
    rows.update(monotonic_ns=time.monotonic_ns(),wall_time_ns=time.time_ns(),load_average=list(os.getloadavg()),affinity=sorted(os.sched_getaffinity(0)))
    return rows


def sources():
    paths=list((ROOT/'research/lp-delivery3/src').glob('*.rs'))+list((ROOT/'research/lp-delivery3').glob('Cargo.*'))
    paths += [ROOT/'tools'/('lp_delivery3_'+name+'.py') for name in ('study','stats','transport','cpu','common','analysis','budget')]
    paths += [ROOT/'docs/specifications/SPEC-0034-delivery3.md',ROOT/'docs/decisions/ADR-0067-delivery3.md',ROOT/'docs/plans/lp-delivery3.md']
    paths += list((ROOT/'research/lp-fp4-checker/src').glob('*.rs'))
    paths += [BASE/'run-cohort.py']
    return [ref(p) for p in sorted(paths)]


def freeze(directory, kind):
    require(kind in ('profile','diagnostic','confirmation'),'cohort kind')
    out=Path(directory);out.mkdir(parents=True,exist_ok=False)
    for identity in ('cpu-acceptance-v1','native-gate-v1','device-acceptance-v1'):
        require(load(BASE/'resources'/f'{identity}.settlement.json')['status']=='passed','missing admission: '+identity)
    require(load(BASE/'device-v1/result.json')['status']=='passed','device admission')
    cpu=load(BASE/'cpu-v1/manifest.json');require(cpu['binary']==ref(BINARY),'CPU-admitted executable changed')
    parent=load(PARENT/'manifest.json')
    for source in parent['sources']:require(ref(ROOT/source['path'])==source,'historical source changed')
    numerical_source()
    selection=None
    if kind=='confirmation':
        selection=load(BASE/'selection-v1.json')
        require(selection['status']=='frozen' and selection['binary']==ref(BINARY),'candidate selection missing')
        for key in ('profile','diagnostic'):
            require(selection[key]==ref(BASE/(key+'-v1')/'result.json'),'diagnostic evidence changed')
        families=list(parent['models']);blocks=32
    else:families=list(DIAGNOSTIC);blocks=2 if kind=='profile' else 4
    rng=random.Random(SEED+{'profile':0,'diagnostic':1,'confirmation':2}[kind]);cells=[]
    for block in range(blocks):
        strata=list(itertools.product(families,LANES,TIERS,('cold','prepared')));rng.shuffle(strata)
        for family,lane,tier,lifecycle in strata:
            if kind=='confirmation':
                # Each stratum receives each pair order exactly sixteen times.
                parity=(sum((i+1)*ord(c) for i,c in enumerate(f'{family}/{lane}/{tier}/{lifecycle}'))+block)%2
                roles=['control','candidate'] if parity==0 else ['candidate','control']
                variants=[('control' if role=='control' else selection['candidates'][lifecycle]) for role in roles]
            else:
                order=list(VARIANTS)
                random.Random(f'{SEED}:{family}:{lane}:{tier}:{lifecycle}').shuffle(order)
                # Two profile blocks reverse order; four diagnostic blocks form
                # a balanced Latin schedule, with each variant in each position.
                variants=(order if block==0 else order[::-1]) if kind=='profile' else [order[(i+block)%4] for i in (0,1,3,2)]
                roles=variants
            old=next(c for c in parent['cells'] if c['family']==family and c['lane']==lane and c['tier']==tier and c['lifecycle']==lifecycle and c['repetition']==0)
            original=ref(PARENT/(old['id']+'.json'))
            for role,variant in zip(roles,variants):
                ident=f'b{block:02d}-{family}-{lane}-{tier}-{lifecycle}-{role}'
                cells.append(dict(id=ident,block=block,family=family,lane=lane,tier=tier,lifecycle=lifecycle,role=role,variant=variant,original_result=original))
    expected={'profile':256,'diagnostic':512,'confirmation':6144}[kind]
    require(len(cells)==expected and len({c['id'] for c in cells})==expected,'cohort count or identity')
    manifest=dict(kind=kind,seed=SEED+{'profile':0,'diagnostic':1,'confirmation':2}[kind],blocks=blocks,cells=cells,profile=kind=='profile',prepared_solves=3,
        image=parent['image'],models={f:parent['models'][f] for f in families},settings=parent['settings'],binary=ref(BINARY),sources=sources(),parent=ref(PARENT/'manifest.json'),
        admissions={name:ref(BASE/name/'result.json') for name in ('cpu-v1','device-v1')},selection=ref(BASE/'selection-v1.json') if selection else None,
        metrics=96,median_ranks=[6,27],automatic_retry=False)
    put(out/'manifest.json',manifest)
    print(dict(kind=kind,blocks=blocks,cells=len(cells)),flush=True)


def validate_manifest(manifest):
    bindings=[manifest['binary'],manifest['image'],manifest['parent'],*manifest['models'].values(),*manifest['sources'],*manifest['admissions'].values()]
    if manifest['selection']:bindings.append(manifest['selection'])
    for binding in bindings:require(ref(ROOT/binding['path'])==binding,'frozen input changed: '+binding['path'])
    for binding in load(ROOT/manifest['parent']['path'])['sources']:require(ref(ROOT/binding['path'])==binding,'historical numerical source changed')


def run_cell(out,cell,manifest):
    variant=cell['variant'];profile=manifest['profile'];model=ROOT/manifest['models'][cell['family']]['path'];image=ROOT/manifest['image']['path']
    require(ref(ROOT/cell['original_result']['path'])==cell['original_result'],'historical cell changed')
    original=load(ROOT/cell['original_result']['path']);records=[];service=None;start=time.monotonic_ns();setup=None;teardown=None
    if cell['lifecycle']=='cold':
        request=out/(cell['id']+'.request.json');put(request,dict(op='solve',lane=cell['lane'],tier=cell['tier'],**manifest['settings']))
        dest=out/(cell['id']+'.solve0.json');log=out/(cell['id']+'.stderr')
        # deliver() inherits only this explicitly set, validated process policy.
        env=environment(variant,profile)
        for name in ('GPUP_DELIVERY2_CONTROL','GPUP_CHECKER_ORIGINAL'):os.environ.pop(name,None)
        os.environ['GPUP_DELIVERY3_VARIANT']=env['GPUP_DELIVERY3_VARIANT'];os.environ['GPUP_DELIVERY3_PROFILE']=env['GPUP_DELIVERY3_PROFILE']
        elapsed=deliver([str(BINARY),'once',str(image),str(model),str(request)],dest,log,35)
        value=load(dest);matches(value,original,manifest['binary'])
        records.append(dict(complete_ns=elapsed,result=ref(dest),solve_ns=value['solve_ns'],costs_ns=value['costs_ns'],setup_ns=value['setup_ns'],gpu_us=value['gpu_us'],physical=value['physical'],certified=value['certified'],status=value['status']))
    else:
        setup_begin=time.monotonic_ns()
        service=Service(image,model,out/(cell['id']+'.stderr'),variant=variant,profile=profile)
        try:
            ready_ns=time.monotonic_ns()-setup_begin
            prepared=service.call('prepare',lane=cell['lane'])
            setup=dict(ready_ns=ready_ns,total_ns=time.monotonic_ns()-setup_begin,ready=service.ready,prepared=prepared)
            for solve in range(manifest['prepared_solves']):
                dest=out/(cell['id']+f'.solve{solve}.json')
                value,elapsed=service.solve_to_file(dest,lane=cell['lane'],tier=cell['tier'],**manifest['settings'])
                matches(value,original,manifest['binary'])
                require(elapsed>=value['solve_ns'],'complete solve boundary')
                records.append(dict(complete_ns=elapsed,result=ref(dest),solve_ns=value['solve_ns'],costs_ns=value['costs_ns'],setup_ns=value['setup_ns'],gpu_us=value['gpu_us'],physical=value['physical'],certified=value['certified'],status=value['status'],delivery=service.last_delivery))
        finally:
            ended=time.monotonic_ns();service.close();teardown=time.monotonic_ns()-ended
    elapsed=time.monotonic_ns()-start
    require(len(records)==(3 if cell['lifecycle']=='prepared' else 1),'fresh solve count')
    require(all(r['certified']==(cell['family']!='infinite-bound-refusal') for r in records),'certificate coverage')
    row=dict(**cell,complete_ns=statistics.median(r['complete_ns'] for r in records),certified=all(r['certified'] for r in records),
        records=records,setup=setup,teardown_ns=teardown,batch_with_analysis_ns=elapsed)
    put(out/(cell['id']+'.cell.json'),row)
    return row


def execute_block(directory,block):
    directory=Path(directory);manifest=load(directory/'manifest.json');validate_manifest(manifest)
    require(0<=block<manifest['blocks'],'unknown block')
    out=directory/f'block-{block:02d}';out.mkdir(exist_ok=False)
    put(out/'STARTED.json',dict(manifest=ref(directory/'manifest.json'),block=block,environment=snapshot()))
    rows=[];cell=None
    try:
        for cell in [c for c in manifest['cells'] if c['block']==block]:
            rows.append(run_cell(out,cell,manifest))
            if len(rows)%32==0:print(dict(block=block,completed=len(rows)),flush=True)
    except BaseException as error:
        put(out/'partial.json',dict(status='failed',error=repr(error),failed_cell=cell,rows=rows,unexecuted=[c['id'] for c in manifest['cells'] if c['block']==block and c['id'] not in {r['id'] for r in rows} and c!=cell]))
        raise
    put(out/'result.json',dict(status='complete',rows=rows,environment=snapshot()))
    print(dict(block=block,completed=len(rows)),flush=True)


def collect(directory):
    directory=Path(directory);manifest=load(directory/'manifest.json');validate_manifest(manifest);rows=[];blocks=[]
    for block in range(manifest['blocks']):
        path=directory/f'block-{block:02d}'/'result.json';r=load(path)
        require(r['status']=='complete','incomplete block');rows+=r['rows'];blocks.append(ref(path))
    require(len(rows)==len(manifest['cells']) and {r['id'] for r in rows}=={c['id'] for c in manifest['cells']},'incomplete cohort')
    put(directory/'result.json',dict(status='complete',manifest=ref(directory/'manifest.json'),rows=rows,blocks=blocks))
    print(dict(cells=len(rows),solves=sum(len(r['records']) for r in rows)),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','block','collect']);p.add_argument('directory');p.add_argument('--kind',choices=['profile','diagnostic','confirmation']);p.add_argument('--block',type=int);a=p.parse_args()
    if a.action=='freeze':freeze(a.directory,a.kind)
    elif a.action=='block':execute_block(a.directory,a.block)
    else:collect(a.directory)
