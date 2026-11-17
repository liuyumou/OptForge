"""Prospective matched fixed-work and broad single-solve fast-proposal studies."""
import argparse
import json
import subprocess
import time
from pathlib import Path
from lp_general_common import BASE,ROOT,load,put,ref,require,CPU_CAPS,GPU_CAPS,NS
from lp_general_budget import accounting
from lp_general_device import serial
from lp_general_oracle import settings


def freeze(identity,admission,pilot,precision,schedule='combined',include_fp4x1=False):
    a=load(BASE/(admission+'.json'));require(a['status']=='passed','current admission required')
    for key in ['image','binary']:require(ref(ROOT/a[key]['path'])==a[key],'admitted file differs')
    root=BASE/identity;root.mkdir(exist_ok=False)
    old=load(BASE/'tensor-ablation-v1/freeze.json');models=old['models']
    indices=[3,9,11,13,18,21] if pilot else list(range(len(models)))
    cells=[]
    for index in indices:
        for repeat in range(2 if pilot else 1):
            for ti,tol in enumerate([1e-9] if pilot else [1e-7,1e-9]):
                formats=['old-native','old-fp4x4','native','fp32','fp4x1','fp4x2','fp4x4','fp4x2-unfused','fp4x2-split'] if pilot else ['native','fp32',precision]
                if include_fp4x1 and not pilot and precision!='fp4x1':formats.insert(2,'fp4x1')
                if (index+repeat+ti)%2:formats.reverse()
                for fmt in formats:
                    old_lane=fmt.startswith('old-');actual=fmt.removeprefix('old-').removesuffix('-unfused').removesuffix('-split')
                    cells.append(dict(id=f'm{index:02d}-r{repeat}-t{ti}-{fmt}',model_index=index,format=fmt,tolerance=tol,
                        command='gpu-tensor' if old_lane else 'gpu-fast',binary=old['binary'] if old_lane else a['binary'],image=old['image'] if old_lane else a['image'],
                        request=dict(settings={**settings(actual),'tolerance':tol,'iteration_limit':500 if pilot else 20000,'check_interval':500,'wall_ms':10000 if pilot else 30000},
                            tensor=dict(min_tile_nnz=128,control_interval=100),fast=dict(fused_encode=not fmt.endswith('-unfused'),combined=not fmt.endswith('-split') if pilot else schedule=='combined'))))
    seconds=120 if pilot else (300 if include_fp4x1 else 240);cpu,gpu=accounting()
    require(cpu['development']+len(indices)*4*seconds*NS<=CPU_CAPS['development']*NS,'whole CPU reservation unavailable')
    require(gpu['development']+len(indices)*seconds*NS<=GPU_CAPS['development']*NS,'whole GPU reservation unavailable')
    put(root/'freeze.json',dict(kind='fast-proposal-development',pilot=pilot,admission=ref(BASE/(admission+'.json')),models=models,indices=indices,cells=cells,
        seconds_per_job=seconds,harness=ref(__file__),claim='Descriptive development; no confirmation or adoption test.'))


def run(identity,index):
    root=BASE/identity;f=load(root/'freeze.json');require(ref(__file__)==f['harness'],'frozen harness differs')
    out=root/f'm{index:02d}';out.mkdir(exist_ok=False);modelref=f['models'][index]['model'];model=ROOT/modelref['path'];require(ref(model)==modelref,'model changed')
    rows=[]
    for c in [x for x in f['cells'] if x['model_index']==index]:
        for key in ['binary','image']:require(ref(ROOT/c[key]['path'])==c[key],'frozen execution source changed')
        command=[str(ROOT/c['binary']['path']),c['command'],str(model),str(ROOT/c['image']['path'])]
        before=time.monotonic_ns();p=subprocess.run(command,input=json.dumps(c['request'])+'\n',text=True,capture_output=True);elapsed=time.monotonic_ns()-before
        name=c['id'];(out/(name+'.stdout.jsonl')).write_text(p.stdout);(out/(name+'.stderr')).write_text(p.stderr)
        require(p.returncode==0,'execution failed; no scientific retry '+name)
        r=json.loads(p.stdout);put(out/(name+'.response.json'),r)
        require(sum(r['accepted'])==r['logical'] and sum(r['attempted'])==r['physical'],'iteration accounting')
        independent=serial(model,dict(primal=r['primal'],dual=r['dual'],certificate=r['certificate'],bound_proof=r['bound_proof']),c['tolerance'],out,name)
        row=dict(cell=c,response=ref(out/(name+'.response.json')),serial=independent,complete_ms=elapsed/1e6,
            certified=r['certified'],status=r['status'],physical=r['physical'],logical=r['logical'],accepted_product_work=r['accepted_product_work'],
            physical_product_work=r['physical_product_work'],tile_count=r['tile_count'],cost_ns=r['cost_ns'],nonzeros=r['nonzeros'],selected_initial_format=r['selected_initial_format'],
            reference_product_nnz=r['reference_product_nnz'],recoveries=r['recoveries'],fast_lanes=r.get('initial_fast_lanes'))
        rows.append(row);put(out/f'partial-{len(rows):03d}.json',dict(rows=rows))
        print(dict(cell=name,status=r['status'],complete_ms=round(elapsed/1e6,3),execution_ms=round(r['cost_ns']['execution']/1e6,3),logical=r['logical'],fp4=r['accepted_product_work'][1]),flush=True)
    put(out/'result.json',dict(status='passed',rows=rows))


def campaign(identity):
    f=load(BASE/identity/'freeze.json')
    for index in f['indices']:
        job=f'{identity}-m{index:02d}'
        require(not (BASE/'resources'/(job+'.reservation.json')).exists(),'cell already reserved')
        command=['python',str(ROOT/'tools/lp_general_budget.py'),'--id',job,'--phase','development','--seconds',str(f['seconds_per_job']),'--gpu','--',
                 'python',str(ROOT/'tools/lp_mixed2_reuse_place.py'),'python',str(ROOT/'tools/lp_general_fast_bench.py'),'run','--id',identity,'--index',str(index)]
        require(subprocess.run(command).returncode==0,'campaign stopped; no retry')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','run','campaign']);p.add_argument('--id',required=True);p.add_argument('--admission');p.add_argument('--pilot',action='store_true');p.add_argument('--include-fp4x1',action='store_true');p.add_argument('--precision',choices=['fp4x1','fp4x2','fp4x3','fp4x4'],default='fp4x2');p.add_argument('--schedule',choices=['combined','split'],default='combined');p.add_argument('--index',type=int);a=p.parse_args()
    if a.action=='freeze':freeze(a.id,a.admission,a.pilot,a.precision,a.schedule,a.include_fp4x1)
    elif a.action=='run':run(a.id,a.index)
    else:campaign(a.id)
