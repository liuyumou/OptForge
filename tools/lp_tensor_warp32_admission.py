"""Eight-model CPU layout/error/window admission; no CUDA context or lease."""
import concurrent.futures,json,shutil,subprocess,time,collections
from benchmark_lp import reference,source_identity
from lp_protocol import ROOT,read_json,write_json,file_hash,checked_reference
from lp_tensor_warp32_common import protocol,instances,make_request,numeric_sources,BASE,IMAGE,DATA,save_verification
from lp_quant_resident_common import freeze_cpu

def main():
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument("--cohort",default="cpu-admission");args=parser.parse_args()
 v=protocol();models=instances(v);names=read_json(ROOT/'benchmarks/configs/lp-exec-v1.json')['timing_instances'];out=BASE/args.cohort;out.mkdir(parents=True,exist_ok=False)
 binary=out/'lp_precision_tensor_cost';shutil.copy2(ROOT/'target/release/examples/lp_precision_tensor_cost',binary)
 identity=freeze_cpu(out,binary,IMAGE,v['device']);sources=numeric_sources();layouts={}
 for name in names:
  m=read_json(checked_reference(ROOT,models[name]['model']));tiles=collections.Counter((r//32,t['variable_id']//32) for r,c in enumerate(m['constraints']) for t in c['terms'] if t['coefficient']!=0)
  layouts[name]=dict(selected_tiles=sum(n>=512 for n in tiles.values()),nonzeros=sum(tiles.values()),selected_nonzeros=sum(n for n in tiles.values() if n>=512))
 def one(task):
  name,c=task;d=out/(name+'-'+c['id']);d.mkdir();model=checked_reference(ROOT,models[name]['model']);row=dict(model=name,configuration=c['id'],eligible=False,layout=layouts[name])
  if not layouts[name]['selected_tiles'] and c['layout'] in ['int8','fp16','bf16','simt']:return dict(row,status='layout_refusal')
  request=make_request(c,model,binary,identity['source_tree_sha256'],work=480,horizon=400);write_json(d/'request.json',request)
  r=subprocess.run(['python3',str(ROOT/'tools/lp_tensor_cost_exec.py'),'--memory-bytes',str(1<<30),'--',str(binary),'trace-cpu',str(model),str(d/'request.json'),str(d/'endpoint.json')],capture_output=True,text=True,timeout=1200);(d/'stdout').write_text(r.stdout);(d/'stderr').write_text(r.stderr)
  if r.returncode:
   if 'panicked' in r.stderr:raise ValueError(r.stderr)
   return dict(row,status='preparation_refusal',error=r.stderr[-2000:])
  started=time.monotonic_ns()
  check=subprocess.run(['python3',str(ROOT/'tools/lp_tensor_cost_exec.py'),'--memory-bytes',str(1<<30),'--',str(binary),'verify',str(model),str(d/'request.json'),str(d/'endpoint.json')],capture_output=True,text=True,timeout=1200);(d/'verify.stdout').write_text(check.stdout);(d/'verify.stderr').write_text(check.stderr)
  if check.returncode or check.stdout.strip()!='verified':raise ValueError(check.stderr)
  save_verification(d/'verification.json',model,d/'request.json',d/'endpoint.json',binary,identity['source_tree_sha256'],read_json(d/'endpoint.json')['assessment'],time.monotonic_ns()-started)
  e=read_json(d/'endpoint.json');o=e['outcome'];core=o['core'];useful=o['counts']['useful_windows']>0
  eligible=core['stop']=='work_horizon' and (c['layout'] in ['segmented','original_tuned'] or useful)
  row.update(status=core['stop'],eligible=eligible,useful_low=useful,iterations=core['iterations'],physical=core['physical'],counts=o['counts'],endpoint=reference(ROOT,d/'endpoint.json'));print(name,c['id'],core['stop'],'useful',useful,flush=True);return row
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(one,[(n,c) for n in names for c in v['configurations']]))
 if sources!=numeric_sources():raise ValueError('numerical sources changed during admission')
 result=dict(status='passed',gpu_seconds=0,rows=rows,source_tree_sha256=identity['source_tree_sha256'],numerical_sources=sources,executable_sha256=file_hash(binary),image_sha256=file_hash(IMAGE),source_archive=reference(ROOT,out/'source.tar'))
 write_json(out/'admission.json',result);write_json(DATA/(args.cohort+'.json'),result)
 required={(name,c['id']) for name in v['timing_instances'] for c in v['configurations']}
 admitted={(r['model'],r['configuration']) for r in rows if r['eligible'] and r.get('iterations')==400}
 if not required<=admitted:raise ValueError('cost continuation lacks complete useful 400-update dense trajectories: '+repr(sorted(required-admitted)))
 print('48 cells retained; eligible',sum(r['eligible'] for r in rows),flush=True)
if __name__=='__main__':main()
