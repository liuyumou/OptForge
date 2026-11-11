"""Fresh coupled device differential/transaction checks, never an old qualification retry."""
import argparse,json,subprocess,time
from pathlib import Path
import numpy as np
from lp_fp4_integrate_common import BASE,ROOT,put,ref,require
from lp_fp4_integrate_model import model,prepare,reference,LANES
from lp_fp4_integrate_run import Service,BINARY

def checks(image,out,sanitizer=None):
 out=Path(out);out.mkdir(parents=True,exist_ok=False);rows=[]
 put(out/'manifest.json',dict(image=ref(image),binary=ref(BINARY),source=ref(ROOT/'research/lp-fp4-integrate/cuda/integrate.cu'),sanitizer=sanitizer,lanes=LANES,families=['coupled-equality','irregular-tail-33','dense-rich-65']))
 for family in ('coupled-equality','irregular-tail-33','dense-rich-65'):
  doc,d=model(family);path=out/(family+'.json');put(path,doc)
  for f,k in LANES:
   label=f'{family}-{f}-{k}';service=Service(image,path,out/(label+'.stderr'))
   try:
    request=prepare(d,f,k,max_updates=600);service.call('load',0,request=request);initial=service.call('export',0);p=len(initial['raw'])//5;n=len(d['c'])
    for op in ('transpose','forward'):
     got=service.call(op,0)['product'];vector=initial['raw'][p:2*p] if op=='transpose' else initial['raw'][2*p:3*p]
     expected=(d['a'].T if op=='transpose' else d['a'])@np.asarray(vector[:n])
     error=float(np.max(np.abs(np.asarray(got[:n])-expected)))
     # Dyadic fixture products fit the admitted component representation exactly.
     tolerance=1e-12 if family!='dense-rich-65' or f==64 or (f==4 and k>=4) else .05
     require(error<=tolerance,f'product mismatch {label}/{op}: {error}')
     restored=service.call('restore',0);generation=restored['generation'];require(generation==1,'restore generation')
     # Each next restore increments generation; use a new service below for step checks.
     rows.append(dict(case=label+'/'+op,error=error,tolerance=tolerance))
     break
   finally:service.close()
   # A second independent service exercises the other orientation and 1/8/32 updates.
   service=Service(image,path,out/(label+'-steps.stderr'))
   try:
    service.call('load',0,request=request);initial=service.call('export',0);generation=0
    got=service.call('forward',generation)['product'];expected=d['a']@np.asarray(initial['raw'][2*p:2*p+n]);error=float(np.max(abs(np.asarray(got[:n])-expected)))
    tolerance=1e-12 if family!='dense-rich-65' or f==64 or (f==4 and k>=4) else .05
    require(error<=tolerance,f'forward mismatch {label}: {error}');rows.append(dict(case=label+'/forward',error=error,tolerance=tolerance))
    service.call('restore',generation);generation+=1
    for steps in (1,8,32):
     row=service.call('step',generation,count=steps,limit=1.0)
     require(row['flags'][4]>0,'missing actual work')
     result=service.call('export',generation);expected=reference(d,initial['raw'],row['flags'][4],request['shift'])
     error=float(np.max(abs(np.asarray(result['raw'])-expected)))
     tolerance=1e-12 if f==64 else .4 if f==4 and k==2 else .02 if f==4 and k==4 else 2e-5
     require(error<=tolerance,f'trajectory mismatch {label}/{steps}: {error}')
     require(result['raw'][3*p:]==initial['raw'][3*p:],'anchors changed')
     service.call('restore',generation);generation+=1;restored=service.call('export',generation)
     require(restored['raw']==initial['raw'] and restored['codes']==initial['codes'] and restored['exponents']==initial['exponents'],'checkpoint mismatch')
     rows.append(dict(case=f'{label}/{steps}',error=error,tolerance=tolerance,physical=row['flags'][4],rollback_exact=True))
   finally:service.close()
 put(out/'result.json',dict(status='passed',rows=rows,certificate=False));print(json.dumps(dict(status='passed',cases=len(rows))))

def main():
 p=argparse.ArgumentParser();p.add_argument('--image',required=True);p.add_argument('--output',required=True);a=p.parse_args();checks(Path(a.image),Path(a.output))
if __name__=='__main__':main()
