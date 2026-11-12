"""Verify all final receipts and replay unique endpoints in fresh checker processes."""
import argparse,json,subprocess
from fractions import Fraction
from pathlib import Path
from lp_fp4_integrate_common import ROOT,BASE,put,ref,load,require
from lp_fp4_integrate_run import BINARY
from lp_fp4_recovery_contract import digest

def replay(out):
 out=Path(out);out.mkdir(parents=True,exist_ok=False);unique={};cells=[]
 for grid in ('diagnostic-v1','performance-v1'):
  summary=load(BASE/grid/'result.json');require(summary['complete'],'partial grid')
  for row in summary['rows']:
   result_path=ROOT/row['result']['path'];require(ref(result_path)==row['result'],'cell mutated');r=load(result_path)
   require(sum(r['costs_ns'].values())==r['cold_wall_ns'],'phase accounting gap')
   require(0<=r['logical_updates']<=r['physical_updates']<= (600 if grid=='diagnostic-v1' else 10000),'physical accounting')
   checkpoint=load(ROOT/r['final_checkpoint']['path']);require(ref(ROOT/r['model']['path'])==r['model'],'original model changed')
   controller=checkpoint['controller'];device=checkpoint['device'];require(controller['logical']==device['logical'],'checkpoint logical state')
   require(float(Fraction(*controller['residual_ratio']))==checkpoint['representation']['last_audit']['rho'],'checkpoint residual differs')
   require(device['generation']<=controller['generation'],'checkpoint generation')
   for binding in (r['certificate']['endpoint'],r['certificate']['certificate']):require(ref(ROOT/binding['path'])==binding,'certificate evidence changed')
   certificate=load(ROOT/r['certificate']['certificate']['path']);require(certificate['accepted']==r['certified'],'certification label')
   require(load(ROOT/r['certificate']['endpoint']['path'])==checkpoint['terminal_export']['endpoint'],'certificate endpoint differs')
   key=digest(dict(model=certificate['model_sha256'],endpoint=certificate['endpoint_sha256'],tier=r['tier']))
   if key not in unique:
    path=out/(key+'.json');subprocess.run([str(BINARY),'check',str(ROOT/r['model']['path']),str(ROOT/r['certificate']['endpoint']['path']),r['tier'],str(path)],check=True,timeout=15)
    require(load(path)==certificate,'independent replay differs');unique[key]=ref(path)
   cells.append(dict(grid=grid,id=row['id'],replay=unique[key]))
 put(out/'result.json',dict(status='passed',cells=cells,unique_endpoints=len(unique),final_binary=ref(BINARY)))
 print(json.dumps(dict(status='passed',cells=len(cells),unique_endpoints=len(unique))))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();replay(a.output)
