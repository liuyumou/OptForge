"""Boundary dimensions and prepared-solve isolation, using real coupled work."""
import argparse,json
from pathlib import Path
import numpy as np
from lp_fp4_integrate_common import put,ref,require
from lp_fp4_integrate_model import model,prepare,reference,LANES
from lp_fp4_integrate_run import Service,Checker,run,BINARY
from lp_fp4_integrate_safety import refused

def checks(image,out):
 out=Path(out);out.mkdir(parents=True,exist_ok=False);rows=[]
 put(out/'manifest.json',dict(image=ref(image),binary=ref(BINARY)))
 for dimension in (32,128):
  doc,data=model('coupled-equality',dimension);path=out/f'model-{dimension}.json';put(path,doc)
  for f,k in LANES:
   service=Service(image,path,out/f'boundary-{dimension}-{f}-{k}.stderr')
   try:
    request=prepare(data,f,k);service.call('load',0,request=request);initial=service.call('export',0);p=dimension
    for generation,op in enumerate(('forward','transpose')):
     got=service.call(op,generation)['product'];vec=initial['raw'][2*p:3*p] if op=='forward' else initial['raw'][p:2*p]
     expected=(data['a'] if op=='forward' else data['a'].T)@np.array(vec)
     require(np.max(abs(np.array(got)-expected))<=1e-12,'boundary product');service.call('restore',generation)
    row=service.call('step',2,count=32,limit=1);result=service.call('export',2);expected=reference(data,initial['raw'],row['flags'][4],request['shift']);error=float(np.max(abs(np.array(result['raw'])-expected)))
    tolerance=1e-12 if f==64 else .4 if f==4 and k==2 else .02 if f==4 and k==4 else 2e-5
    require(error<=tolerance,'boundary recurrence');rows.append(dict(dimension=dimension,lane=[f,k],error=error,physical=row['flags'][4]))
   finally:service.close()
 doc,_=model('coupled-equality');path=out/'model.json';put(path,doc)
 service=Service(image,path,out/'prepared.stderr');checker=Checker(path,'certified-1e-7',out/'prepared-checker.stderr');hashes=[];counts=[]
 for index,lane in enumerate(((4,2),(64,1),(4,2))):
  r=run('coupled-equality',*lane,'certified-1e-7',image,out/f'prepared-{index}',diagnostic=False,session=service,checker_session=checker)
  require(r['certified'],'prepared certification');hashes.append(r['certificate']['endpoint']['sha256']);counts.append(r['physical_updates'])
 require(hashes[0]==hashes[2] and counts[0]==counts[2],'prepared solve leaked state')
 require(service.solve_id==3,'solve generation');refused(service,dict(op='export',generation=0,solve_id=2));checker.close()
 service=Service(image,path,out/'stale-finish.stderr');service.call('load',0,request=prepare(model('coupled-equality')[1],4,4));service.call('restore',0);refused(service,dict(op='finish',generation=0,solve_id=0))
 rows.append(dict(case='prepared-isolation',endpoint_identical=True,physical_counts=counts,stale_solve_refused=True))
 put(out/'result.json',dict(status='passed',rows=rows));print(json.dumps(dict(status='passed',cases=len(rows))))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--image',required=True);p.add_argument('--output',required=True);a=p.parse_args();checks(Path(a.image),a.output)
