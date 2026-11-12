"""Actual service transactions plus explicitly injected recovery-policy events."""
import argparse,json
from pathlib import Path
from lp_fp4_integrate_common import put,require,ref,ROOT
from lp_fp4_integrate_model import model,prepare
from lp_fp4_integrate_run import Service,run,BINARY

def refused(service,command):
 service.proc.stdin.write(json.dumps(command)+'\n');service.proc.stdin.flush()
 require(service.proc.stdout.readline()=='','expected service refusal')
 service.proc.stdin.close();code=service.proc.wait(timeout=10);service.log.close();require(code!=0,'refusal exit')

def checks(image,out):
 out=Path(out);out.mkdir(parents=True,exist_ok=False);rows=[]
 put(out/'manifest.json',dict(image=ref(image),binary=ref(BINARY),kind='safety',fault_injection=True))
 for label,kwargs in [('cancel-before',dict(cancel_after=0)),('cancel-audit',dict(cancel_after=200)),('deadline',dict(wall_seconds=0))]:
  r=run('coupled-equality',4,8,'certified-1e-7',image,out/label,**kwargs)
  require(not r['certified'] and r['status'] in ('cancelled','deadline'),'stop status')
  rows.append(dict(case=label,status=r['status'],physical=r['physical_updates'],result=ref(out/label/'result.json')))
 doc,data=model('coupled-equality');path=out/'model.json';put(path,doc)
 for label in ('stale-generation','physical-budget','nonfinite-input','local-budget','queued-cancel'):
  service=Service(image,path,out/(label+'.stderr'));request=prepare(data,4,8,max_updates=1 if label=='physical-budget' else 600)
  if label=='nonfinite-input':
   request['initial'][0]=1e300;refused(service,dict(op='load',generation=0,request=request));rows.append(dict(case=label,refused=True));continue
  service.call('load',0,request=request);initial=service.call('export',0)
  if label in ('stale-generation','physical-budget'):
   refused(service,dict(op='step',generation=1 if label=='stale-generation' else 0,count=2,limit=1));rows.append(dict(case=label,refused=True));continue
  if label=='local-budget':
   row=service.call('step',0,count=32,limit=1e-30);require(3 in row['flags'][:4],'local guard not exercised')
   service.call('restore',0);restored=service.call('export',1)
   require(restored['raw']==initial['raw'] and restored['codes']==initial['codes'],'guard rollback')
   service.close();rows.append(dict(case=label,physical=row['flags'][4],rollback_exact=True));continue
  # Queue cancellation while the step response is still outstanding. The service
  # submits only the one bounded numerical window, then restores before replying.
  for command in (dict(op='step',generation=0,count=32,limit=1),dict(op='cancel',generation=0)):
   service.proc.stdin.write(json.dumps(command)+'\n')
  service.proc.stdin.flush();step=service.read();cancel=service.read();require(cancel['cancelled'] and 0<step['flags'][4]<=32,'queued cancel boundary')
  restored=service.call('export',1);require(restored['raw']==initial['raw'] and restored['codes']==initial['codes'],'cancel rollback')
  refused(service,dict(op='step',generation=1,count=1,limit=1));rows.append(dict(case=label,physical=step['flags'][4],rollback_exact=True,terminal=True))
 # A rejected candidate load must preserve the old generation/checkpoint so
 # the native load can recover without re-running or refunding any update.
 service=Service(image,path,out/'atomic-conversion.stderr')
 try:
  request=prepare(data,4,2);service.call('load',0,request=request);original=service.call('export',0)
  service.call('step',0,count=8,limit=1);service.call('restore',0)
  promoted=prepare(data,4,4,raw=original['raw']);promoted['codes'][0]=8
  refused_load=service.call('load',1,request=promoted);require(refused_load.get('conversion_failure'),'corrupt conversion accepted')
  retained=service.call('export',1);require(retained['raw']==original['raw'] and retained['codes']==original['codes'],'conversion destroyed checkpoint')
  native=prepare(data,64,1,raw=original['raw']);require(service.call('load',1,request=native)['loaded'],'native recovery refused')
  row=service.call('step',1,count=1,limit=1);require(row['physical_updates']>=2,'conversion refunded work')
  rows.append(dict(case='actual-conversion-failure',checkpoint_exact=True,native_recovery=True,physical=row['physical_updates']))
 finally:service.close()
 # Exact low pair component straddles the local comparison resolution near -1.
 doc,data=model('irregular-tail-33');doc['objective']['terms']=[];data['c'][:]=0;path=out/'projection-model.json';put(path,doc)
 request=prepare(data,4,8);p=len(request['initial'])//5
 for v in (0,2,3):request['initial'][v*p:v*p+33]=[-1+2**-45]*33
 for v in (1,4):request['initial'][v*p:v*p+33]=[0.]*33
 service=Service(image,path,out/'projection.stderr')
 try:
  service.call('load',0,request=request);row=service.call('step',0,count=1,limit=1);require(5 in row['flags'][:4],'projection ambiguity not exercised');service.call('restore',0);rows.append(dict(case='ambiguous-projection',physical=row['flags'][4],flags=row['flags']))
 finally:service.close()
 for reason in ('residual_growth','stagnation','conversion_failure'):
  r=run('coupled-equality',4,8,'certified-1e-7',image,out/reason,diagnostic=False,inject=reason)
  require(any(e.get('reason')==reason for e in r['events']),'recovery reason not exercised')
  require(r['certified'],'native recovery did not certify')
  rows.append(dict(case=reason,injected_policy_event=True,certified=True,result=ref(out/reason/'result.json')))
 r=run('infinite-bound-refusal',4,8,'certified-1e-9',image,out/'checker-refusal')
 require(not r['certified'],'infinite bound falsely certified');rows.append(dict(case='checker-bound-refusal',certified=False,result=ref(out/'checker-refusal/result.json')))
 put(out/'result.json',dict(status='passed',rows=rows));print(json.dumps(dict(status='passed',cases=len(rows))))

def main():
 p=argparse.ArgumentParser();p.add_argument('--image',required=True);p.add_argument('--output',required=True);a=p.parse_args();checks(Path(a.image),Path(a.output))
if __name__=='__main__':main()
