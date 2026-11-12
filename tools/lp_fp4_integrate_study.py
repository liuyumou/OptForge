"""Frozen 96-cell integration grid and separately labeled cold/prepared solves."""
import argparse,json,random,subprocess,sys,time
from pathlib import Path
from lp_fp4_integrate_common import BASE,ROOT,put,ref,require,load
from lp_fp4_integrate_model import model,FAMILIES,LANES
from lp_fp4_integrate_run import run,Service,Checker,BINARY
TIERS=('certified-1e-7','certified-1e-9')

def freeze(image,out,kind,admission):
 admission=Path(admission);accepted=load(admission);require(accepted['status']=='passed','admission refused');require(accepted['image']==ref(image) and accepted['binary']==ref(BINARY),'unadmitted executable')
 for binding in accepted['sources']:require(ref(ROOT/binding['path'])==binding,'admitted source changed')
 out=Path(out);out.mkdir(parents=True,exist_ok=False)
 sources=list((ROOT/'research/lp-fp4-integrate/src').glob('*.rs'))+list((ROOT/'research/lp-fp4-integrate/cuda').glob('*'))+list((ROOT/'tools').glob('*fp4_integrate*.py'))
 models=[]
 for family in FAMILIES:
  path=out/(family+'.model.json');put(path,model(family)[0]);models.append(ref(path))
 cells=[dict(family=f,lane=list(l),tier=t,rep=r,lifecycle=life) for f in FAMILIES for t in TIERS for r in range(1 if kind=='diagnostic' else 3) for life in (['diagnostic'] if kind=='diagnostic' else ['cold','prepared']) for l in LANES]
 random.Random(30962026).shuffle(cells)
 # Group prepared work only by immutable model/tier, preserving random lane order.
 for i,c in enumerate(cells):c['id']=f'cell-{i:04d}'
 manifest=dict(schema_version=1,admission=ref(admission),kind=kind,cells=cells,updates=600 if kind=='diagnostic' else 10000,models=models,sources=[ref(p) for p in sorted(sources)],binary=ref(BINARY),image=ref(image),repetitions=1 if kind=='diagnostic' else 3,seed=30962026,deadline_seconds=30,retention=dict(cold_geomean_min=1.10,no_model_median_regression=True,no_coverage_loss=True),status='frozen-before-execution')
 put(out/'manifest.json',manifest);put(out/'freeze-receipt.json',dict(manifest=ref(out/'manifest.json')));print(ref(out/'manifest.json'))
 return manifest

def execute(manifest_path):
 manifest_path=Path(manifest_path);spec=load(manifest_path);out=manifest_path.parent;require(ref(manifest_path)==load(out/'freeze-receipt.json')['manifest'],'frozen manifest changed');require(ref(ROOT/spec['admission']['path'])==spec['admission'],'admission changed');image=ROOT/spec['image']['path']
 for binding in spec['sources']+[spec['binary'],spec['image']]+spec['models']:require(ref(ROOT/binding['path'])==binding,'frozen source changed')
 rows=[];sessions={};startup=[]
 try:
  for cell in spec['cells']:
   directory=out/cell['id'];kwargs={};outer=time.monotonic_ns();mode=cell['lifecycle']
   if mode=='prepared':
    key=(cell['family'],cell['tier'])
    if key not in sessions:
     begin=time.monotonic_ns();path=out/(cell['family']+'.model.json')
     service=Service(image,path,out/(cell['family']+'-'+cell['tier']+'.stderr'))
     checker=Checker(path,cell['tier'],out/(cell['family']+'-'+cell['tier']+'-checker.stderr'))
     sessions[key]=(service,checker);startup.append(dict(family=key[0],tier=key[1],setup_ns=time.monotonic_ns()-begin))
    kwargs=dict(session=sessions[key][0],checker_session=sessions[key][1]);outer=time.monotonic_ns()
   if mode=='cold':
    with (out/(cell['id']+'.stdout')).open('xb') as stdout,(out/(cell['id']+'.stderr')).open('xb') as stderr:
     result=subprocess.run([sys.executable,'-B',str(ROOT/'tools/lp_fp4_integrate_run.py'),'--image',str(image),'--output',str(directory),'--family',cell['family'],'--format',str(cell['lane'][0]),'--components',str(cell['lane'][1]),'--tier',cell['tier'],'--updates',str(spec['updates']),'--solve'],stdout=stdout,stderr=stderr,timeout=40)
    require(result.returncode==0,'cold cell transport failed; no automatic retry')
    r=load(directory/'result.json')
   else:r=run(cell['family'],*cell['lane'],cell['tier'],image,directory,updates=spec['updates'],diagnostic=mode=='diagnostic',**kwargs)
   elapsed=time.monotonic_ns()-outer
   rows.append(dict(**cell,result=ref(directory/'result.json'),certified=r['certified'],physical=r['physical_updates'],fp4=r['fp4_updates'],outer_ns=elapsed,controller_ns=r['cold_wall_ns'],gpu_us=r['gpu_us'],costs_ns=r['costs_ns'],status=r['status']))
   put(out/(cell['id']+'.receipt.json'),rows[-1])
   print(json.dumps(dict(completed=len(rows),total=len(spec['cells']),cell=cell['id'],certified=r['certified'],physical=r['physical_updates'])),flush=True)
 finally:
  for service,checker in sessions.values():service.close();checker.close()
 put(out/'result.json',dict(manifest=ref(manifest_path),rows=rows,prepared_startup=startup,complete=len(rows)==len(spec['cells'])))

def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','run']);p.add_argument('--image');p.add_argument('--output');p.add_argument('--kind',choices=['diagnostic','performance']);p.add_argument('--manifest');p.add_argument('--admission');a=p.parse_args()
 if a.action=='freeze':freeze(Path(a.image),Path(a.output),a.kind,a.admission)
 else:execute(a.manifest)
if __name__=='__main__':main()
