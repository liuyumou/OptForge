"""Frozen complete-cost comparison; no automatic retry of any formal cell."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
from lp_fp4_accel_common import ROOT,BASE,DEVICE,put,ref,require,load
from lp_fp4_accel_model import FAMILIES,model
from lp_fp4_accel_run import Service,BINARY,compact

LANES=('native','nativefast','fp4x4','gridfp4x2','gridfp4x4','auto')
TIERS=('certified-1e-7','certified-1e-9')


def freeze(image,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False);models={}
    for family in FAMILIES:
        p=out/(family+'.model.json');compact(p,model(family)[0]);models[family]=ref(p)
    sources=list((ROOT/'research/lp-fp4-accel/src').glob('*.rs'))+list((ROOT/'research/lp-fp4-accel/cuda').glob('*'))
    sources+=list((ROOT/'tools').glob('*fp4_accel*.py'))+list((ROOT/'research/lp-fp4-accel').glob('Cargo.*'))
    for directory in ('crates/optimizer-core','crates/optimizer-lp','crates/optimizer-experiment','research/lp-tensor-expanded-device/cuda-sys'):
        sources += [p for p in (ROOT/directory).rglob('*.rs') if 'target' not in p.relative_to(ROOT).parts]+list((ROOT/directory).glob('Cargo.toml'))
    sources += list((ROOT/'tools').glob('lp_*.py'))
    admission=load(BASE/'admission.json');require(admission['status']=='passed','admission required')
    for binding in admission['receipts']:require(ref(ROOT/binding['path'])==binding,'changed admission receipt')
    require(admission['binary']==ref(BINARY) and admission['image']==ref(image),'admission image mismatch')
    cells=[]
    for lifecycle in ('cold','prepared'):
        for f,family in enumerate(FAMILIES):
            for rep in range(5):
                for t in range(2):
                    tier=TIERS[(t+rep)%2]
                    for j in range(len(LANES)):
                        lane=LANES[(j+rep+f)%len(LANES)]
                        cells.append(dict(id=f'{lifecycle}-{family}-{rep}-{tier}-{lane}',lifecycle=lifecycle,family=family,repetition=rep,tier=tier,lane=lane))
    put(out/'manifest.json',dict(kind='lp-fp4-accel-formal-v1',device=DEVICE,
        device_metadata=subprocess.check_output(['nvidia-smi','-i',DEVICE,'--query-gpu=uuid,name,driver_version,memory.total','--format=csv,noheader'],text=True).strip(),
        cuda_compiler=subprocess.check_output(['/usr/local/cuda/bin/nvcc','--version'],text=True),
        image=ref(image),binary=ref(BINARY),
        sources=[ref(p) for p in sorted(set(sources))],admission=ref(BASE/'admission.json'),models=models,cells=cells,settings=dict(max_updates=10000,wall_ms=30000,audit_max=200),
        complete_cost='cold: process spawn through exit and durable native response; prepared: request through durable response; original input files frozen before timing',
        preparation='shared prepared model/context/checker and all lane buffers charged separately per family; cold cells include their actual selected preparation',
        retention=dict(reference='nativefast',cold_geomean=1.10,no_certified_model_regression=True,no_coverage_loss=True),automatic_retry=False))
    print(dict(frozen=True,cells=len(cells)),flush=True)


def execute(out):
    out=Path(out);m=load(out/'manifest.json');require(not (out/'STARTED.json').exists(),'formal cohort already started')
    for r in [m['image'],m['binary'],*m['sources'],*m['models'].values()]:require(ref(ROOT/r['path'])==r,'changed frozen input: '+r['path'])
    put(out/'STARTED.json',dict(manifest=ref(out/'manifest.json')))
    rows=[];setups=[];image=ROOT/m['image']['path'];service=None;family=None
    try:
        for cell in m['cells']:
            dest=out/(cell['id']+'.json');path=ROOT/m['models'][cell['family']]['path'];settings=dict(lane=cell['lane'],tier=cell['tier'],**m['settings'])
            if cell['lifecycle']=='cold':
                request=out/(cell['id']+'.request.json');compact(request,dict(op='solve',**settings))
                start=time.monotonic_ns()
                with dest.open('xb') as output,(out/(cell['id']+'.stderr')).open('xb') as err:
                    p=subprocess.run([str(BINARY),'once',str(image),str(path),str(request)],stdout=output,stderr=err,timeout=35)
                    output.flush();os.fsync(output.fileno())
                elapsed=time.monotonic_ns()-start;p.check_returncode();r=load(dest)
            else:
                if family!=cell['family']:
                    if service is not None:service.close()
                    family=cell['family'];start=time.monotonic_ns();service=Service(image,path,out/(family+'.prepared.stderr'));ready=time.monotonic_ns()-start
                    prep=[]
                    for lane in LANES:
                        mark=time.monotonic_ns();reply=service.call('prepare',lane=lane);prep.append(dict(lane=lane,actual=reply['prepared'],ns=time.monotonic_ns()-mark))
                    setups.append(dict(family=family,ready_ns=ready,prepare=prep,total_ns=time.monotonic_ns()-start))
                r,elapsed=service.solve_to_file(dest,**settings)
            require(sum(r['costs_ns'].values())==r['solve_ns'],'overlapping phase costs')
            require(sum(r['attempted'].values())==r['physical'],'physical ledger')
            rows.append(dict(**cell,status=r['status'],certified=r['certified'],physical=r['physical'],logical=r['logical'],
                final_lane=r['final_lane'],attempted=r['attempted'],gpu_us=r['gpu_us'],complete_ns=elapsed,solve_ns=r['solve_ns'],costs_ns=r['costs_ns'],
                recovery=[e for e in r['events'] if e['kind']!='window'],result=ref(dest)))
            if len(rows)%60==0:print(dict(completed=len(rows),planned=len(m['cells'])),flush=True)
    except Exception as e:
        put(out/'partial.json',dict(status='failed',error=str(e),rows=rows,setups=setups,failed_cell=cell,partial_output=ref(dest) if dest.exists() else None,unexecuted=[c for c in m['cells'] if c['id'] not in {r['id'] for r in rows} and c['id']!=cell['id']]))
        raise
    finally:
        if service is not None:service.close()
    put(out/'result.json',dict(status='complete',manifest=ref(out/'manifest.json'),rows=rows,setups=setups));print(dict(completed=len(rows)),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','run']);p.add_argument('--image');p.add_argument('--output',required=True);a=p.parse_args()
    if a.action=='freeze':freeze(Path(a.image),Path(a.output))
    else:execute(Path(a.output))
