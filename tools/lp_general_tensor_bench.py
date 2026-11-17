"""Frozen, bounded, complete-cost development comparison; never retry a cell."""
import argparse
import json
import subprocess
import time
from pathlib import Path
from lp_general_common import BASE,ROOT,load,put,ref,require
from lp_general_budget import accounting
from lp_general_oracle import settings
from lp_general_device import serial


def freeze(identity,image,binary,threshold,limit,repeats,admission,ablation=False):
    admission=BASE/(admission+'.json');a=load(admission)
    require(a['status']=='passed' and a['binary']==ref(binary) and a['image']==ref(image),'current numerical admission required')
    out=BASE/identity;out.mkdir(parents=True,exist_ok=False)
    # All 22 original development models; no held-out instance is generated.
    require(1<=repeats<=4 and 1<=threshold<=1024 and 1<=limit<=1000000,"freeze domain")
    old=load(BASE/'development-extended-v1/freeze.json')
    models=[dict(model=next(c['model'] for c in old['cells'] if c['model_index']==i),family=next(c['family'] for c in old['cells'] if c['model_index']==i)) for i in range(max(c['model_index'] for c in old['cells'])+1)]
    cells=[]
    for i,model in enumerate(models):
        for rep in range(repeats):
            tiers=[1e-9] if ablation else [1e-7,1e-9]
            for ti,tol in enumerate(tiers):
                formats=['native','fp32','fp4x2','fp4x4','fp4x4-direct','fp4x4-expanded','fp4x4-w4'] if ablation else ['native','fp32','fp4x4']
                if (i+rep+ti)%2:formats.reverse()
                for fmt in formats:
                    cells.append(dict(id=f'm{i:02d}-r{rep}-t{ti}-{fmt}',model_index=i,repeat=rep,format=fmt,tolerance=tol,
                        request=dict(settings={**settings(fmt.split('-')[0]),'tolerance':tol,'iteration_limit':limit,'check_interval':500,'wall_ms':10000 if ablation else 30000},
                            tensor=dict(min_tile_nnz=threshold,control_interval=100,incremental=not fmt.endswith('-direct'),
                                compact_fragments=not fmt.endswith('-expanded'),tensor_warps=4 if fmt.endswith('-w4') else 1))))
    seconds=(120 if ablation else 240)*repeats;cpu,gpu=accounting()
    from lp_general_common import CPU_CAPS,GPU_CAPS,NS
    require(cpu['development']+len(models)*4*seconds*NS<=CPU_CAPS['development']*NS,'full CPU reservation unavailable')
    require(gpu['development']+len(models)*seconds*NS<=GPU_CAPS['development']*NS,'full GPU reservation unavailable')
    put(out/'freeze.json',dict(kind='tensor-general-development',ablation=ablation,admission=ref(admission),models=models,cells=cells,binary=ref(binary),image=ref(image),
        sources=[ref(ROOT/'tools/lp_general_tensor_bench.py')],seconds_per_job=seconds,repeats=repeats,
        claim='Exploratory matched development. No confirmation, population speedup or adoption pass.'))


def run(identity,index):
    root=BASE/identity;freeze=load(root/'freeze.json');out=root/f'm{index:02d}';out.mkdir(exist_ok=False)
    binary=ROOT/freeze['binary']['path'];image=ROOT/freeze['image']['path']
    require(ref(binary)==freeze['binary'] and ref(image)==freeze['image'],'frozen executable/image differs')
    for s in freeze['sources']:require(ref(ROOT/s['path'])==s,'frozen harness differs')
    entry=freeze['models'][index]
    # Existing manifests carry model/source/construction separately.
    model=ROOT/entry['model']['path'];require(ref(model)==entry['model'],'model differs')
    rows=[]
    for cell in [c for c in freeze['cells'] if c['model_index']==index]:
        started=time.monotonic_ns()
        p=subprocess.run([str(binary),'gpu-tensor',str(model),str(image)],input=json.dumps(cell['request'])+'\n',text=True,capture_output=True)
        complete=time.monotonic_ns()-started;name=cell['id']
        (out/(name+'.stdout.jsonl')).write_text(p.stdout);(out/(name+'.stderr')).write_text(p.stderr)
        require(p.returncode==0,'numerical process failed; cell remains failed '+name)
        result=json.loads(p.stdout);put(out/(name+'.response.json'),result)
        require(sum(result['attempted'])==result['physical'] and sum(result['accepted'])==result['logical'],'iteration accounting')
        independent=serial(model,dict(primal=result['primal'],dual=result['dual'],certificate=result['certificate'],bound_proof=result['bound_proof']),cell['request']['settings']['tolerance'],out,name)
        row=dict(cell=cell,response=ref(out/(name+'.response.json')),serial=independent,complete_ms=complete/1e6,
            certified=result['certified'],status=result['status'],physical=result['physical'],logical=result['logical'],
            accepted_product_work=result['accepted_product_work'],physical_product_work=result['physical_product_work'],tile_count=result['tile_count'],
            cost_ns=result['cost_ns'],nonzeros=result['nonzeros'])
        rows.append(row);put(out/f'partial-{len(rows):03d}.json',dict(rows=rows))
        print(dict(cell=name,status=result['status'],complete_ms=complete/1e6,logical=result['logical'],fp4=result['accepted_product_work'][1]),flush=True)
    put(out/'result.json',dict(status='passed',rows=rows))


def campaign(identity,indices=None):
    manifest=load(BASE/identity/'freeze.json');indices=range(len(manifest['models'])) if indices is None else indices
    for i in indices:
        name=f'{identity}-m{i:02d}';require(not (BASE/'resources'/(name+'.reservation.json')).exists(),'scientific cell already reserved')
        args=['python',str(ROOT/'tools/lp_general_budget.py'),'--id',name,'--phase','development','--seconds',str(manifest['seconds_per_job']),'--gpu','--',
              'python',str(ROOT/'tools/lp_mixed2_reuse_place.py'),'python',str(ROOT/'tools/lp_general_tensor_bench.py'),'run','--id',identity,'--index',str(i)]
        require(subprocess.run(args).returncode==0,'campaign stopped; no scientific retry')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','run','campaign']);p.add_argument('--id',required=True);p.add_argument('--image',type=Path);p.add_argument('--ablation',action='store_true');p.add_argument('--admission',default='tensor-admission-v1');p.add_argument('--binary',type=Path);p.add_argument('--threshold',type=int,default=128);p.add_argument('--limit',type=int,default=20000);p.add_argument('--repeats',type=int,default=1);p.add_argument('--index',type=int);p.add_argument('--indices');a=p.parse_args()
    if a.action=='freeze':freeze(a.id,a.image,a.binary,a.threshold,a.limit,a.repeats,a.admission,a.ablation)
    elif a.action=='run':run(a.id,a.index)
    else:campaign(a.id,None if a.indices is None else [int(i) for i in a.indices.split(',')])
