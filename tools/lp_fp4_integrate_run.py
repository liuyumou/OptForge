"""SPEC-0030 persistent GPU service, operational recovery, independent certificates."""
import argparse,dataclasses,hashlib,json,math,os,subprocess,time
from pathlib import Path
import numpy as np
import lp_fp4_recovery_contract as policy
from lp_fp4_integrate_common import BASE,ROOT,put,ref,require,load
from lp_fp4_integrate_model import model,prepare,observation
from lp_fp4_integrate_policy import admitted_policy, POLICY_SHA256
BINARY=ROOT/'research/lp-fp4-integrate/target/release/lp-fp4-integrate'

class Service:
 def __init__(self,image,model_path,log):
  self.log=Path(log).open('xb');prefix=[]
  if os.environ.get('AI_OPTIMIZER_SANITIZER'):
   tool=os.environ['AI_OPTIMIZER_SANITIZER'];require(tool in ('memcheck','racecheck','initcheck','synccheck'),'sanitizer name')
   prefix=['/usr/local/cuda/bin/compute-sanitizer','--tool',tool,'--error-exitcode','86','--log-file',str(log)+'.sanitizer']
  self.proc=subprocess.Popen(prefix+[str(BINARY),'serve',str(image),str(model_path)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,text=True,bufsize=1)
  self.ready=self.read();self.solve_id=0;self.generation=0
 def read(self):
  line=self.proc.stdout.readline()
  if not line:raise RuntimeError(f'GPU service exited {self.proc.poll()}')
  return json.loads(line)
 def call(self,op,generation,**fields):
  self.proc.stdin.write(json.dumps(dict(op=op,generation=generation,solve_id=self.solve_id,**fields),allow_nan=False,separators=(',',':'))+'\n');self.proc.stdin.flush();result=self.read();self.generation=result.get('generation',self.generation);return result
 def finish(self):
  result=self.call('finish',self.generation);require(result['finished'],'finish refused');self.solve_id=result['solve_id'];self.generation=0;return result
 def close(self):
  if self.proc.stdin and not self.proc.stdin.closed:self.proc.stdin.close()
  try:code=self.proc.wait(timeout=10)
  except subprocess.TimeoutExpired:self.proc.kill();self.proc.wait();raise
  self.log.close();require(code==0,'service exit')

class Checker:
 def __init__(self,model_path,tier,log):
  self.log=Path(log).open('xb')
  self.proc=subprocess.Popen([str(BINARY),'check-service',str(model_path),tier],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,text=True,bufsize=1,env={**os.environ,'CUDA_VISIBLE_DEVICES':''})
  self.image=ref(BINARY)['sha256'];ready=json.loads(self.proc.stdout.readline())
  require(ready['checker_binary_sha256']==self.image,'independent checker binding')
 def assess(self,endpoint):
  self.proc.stdin.write(json.dumps(endpoint,allow_nan=False,separators=(',',':'))+'\n');self.proc.stdin.flush()
  line=self.proc.stdout.readline();require(bool(line),'independent checker exited')
  return json.loads(line)
 def close(self):
  self.proc.stdin.close()
  try:code=self.proc.wait(timeout=10)
  except subprocess.TimeoutExpired:self.proc.kill();self.proc.wait();raise
  self.log.close();require(code==0,'checker exit')

def state_hash(snapshot):
 return policy.digest({k:snapshot[k] for k in ('raw','codes','exponents','generation','logical')})

def certify(model_path,endpoint,tier,directory,label,checker=None):
 candidate=directory/(label+'-endpoint.json');certificate=directory/(label+'-certificate.json')
 put(candidate,endpoint)
 if checker is None:
  subprocess.run([str(BINARY),'check',str(model_path),str(candidate),tier,str(certificate)],check=True,timeout=15)
  result=load(certificate)
 else:
  result=checker.assess(endpoint);put(certificate,result)
 require(result['model_sha256']==ref(model_path)['sha256'] and result['tier']==tier,'certificate binding')
 require(result['checker_binary_sha256']==(checker.image if checker else ref(BINARY)['sha256']),'checker image binding')
 return result,dict(endpoint=ref(candidate),certificate=ref(certificate))

def run(family,bits,components,tier,image,directory,updates=600,diagnostic=True,cancel_after=None,inject=None,wall_seconds=30,session=None,checker_session=None):
 directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
 entered=time.monotonic_ns();admitted_policy();doc,data=model(family);model_path=directory/'model.json';put(model_path,doc)
 costs=dict.fromkeys(policy.PHASES,0);events=[];audits=[];physical=0;generation=0;logical=0;gpu_us=0.;attempted={};loads=0
 current=(bits,components);max_updates=updates;mode='fp4' if bits!=64 else 'native';start=time.monotonic_ns()
 request=prepare(data,*current,max_updates=max_updates);costs['prepare']+=time.monotonic_ns()-start
 start=time.monotonic_ns();service=session or Service(image,model_path,directory/'service.stderr');require(service.ready['model_sha256']==ref(model_path)['sha256'],'reused model differs');costs['transport']+=time.monotonic_ns()-start
 checker=checker_session;last_checked_endpoint=None
 try:
  start=time.monotonic_ns();service.call('load',generation,request=request);checkpoint=service.call('export',generation);service.call('save',generation);costs['transport']+=time.monotonic_ns()-start
  initial_checkpoint=state_hash(checkpoint);start=time.monotonic_ns();obs=observation(data,checkpoint['raw']);costs['audit']+=time.monotonic_ns()-start
  state=policy.Monitor(model=ref(model_path)['sha256'],policy=POLICY_SHA256,tier=tier,checkpoint=state_hash(checkpoint),generation=generation,components=components if bits!=64 else 8,residual=obs['rho'])
  audit_logical=0;stop='limit';certificate=None;last_binding=None;last_export=checkpoint
  def recovery(reason):
   nonlocal generation,current,checkpoint,state,logical,audit_logical,mode,loads,request,obs
   old=current;plan=policy.recover(state,reason) if current[0]==4 else dict(action='native_restore',target_components=None)
   start=time.monotonic_ns();result=service.call('restore',generation);generation=result['generation'];restored=service.call('export',generation);costs['rollback']+=time.monotonic_ns()-start
   require(restored['raw']==checkpoint['raw'] and restored['codes']==checkpoint['codes'] and restored['exponents']==checkpoint['exponents'],'rollback bytes differ')
   start=time.monotonic_ns();obs=observation(data,restored['raw']);costs['audit']+=time.monotonic_ns()-start
   logical=state.iteration;audit_logical=logical;target=plan['target_components'];current=(4,target) if target else (64,1);mode='fp4' if target else 'native'
   start=time.monotonic_ns();request=prepare(data,*current,raw=restored['raw'],iteration=logical,max_updates=max_updates);costs['prepare']+=time.monotonic_ns()-start
   start=time.monotonic_ns();conversion=service.call('load',generation,request=request);costs['conversion']+=time.monotonic_ns()-start;loads+=1
   if not conversion['loaded']:
    require(current[0]!=64,'native conversion failed')
    events.append(dict(reason='conversion_failure',from_lane=list(old),to_lane=[64,1],physical=physical,logical=logical,generation=generation,restored_exact=True))
    current=(64,1);target=None;mode='native'
    start=time.monotonic_ns();request=prepare(data,*current,raw=restored['raw'],iteration=logical,max_updates=max_updates);costs['prepare']+=time.monotonic_ns()-start
    start=time.monotonic_ns();conversion=service.call('load',generation,request=request);costs['conversion']+=time.monotonic_ns()-start;loads+=1
    require(conversion['loaded'],'native conversion failed')
   start=time.monotonic_ns();converted=service.call('export',generation);costs['conversion']+=time.monotonic_ns()-start
   require(converted['raw']==restored['raw'],'promotion changed represented state')
   checkpoint=converted;state=dataclasses.replace(state,generation=generation,components=target or state.components,checkpoint=state_hash(checkpoint),stalls=0)
   events.append(dict(reason=reason,from_lane=list(old),to_lane=list(current),physical=physical,logical=logical,generation=generation,restored_exact=True))
  while physical<max_updates:
   deadline=time.monotonic_ns()-entered>=wall_seconds*1e9
   if deadline or (cancel_after is not None and physical>=cancel_after):
    start=time.monotonic_ns();service.call('restore',generation);generation+=1;last_export=service.call('export',generation);costs['rollback']+=time.monotonic_ns()-start;stop='deadline' if deadline else 'cancelled';logical=state.iteration;break
   count=min(32,200-(logical-audit_logical),max_updates-physical)
   if cancel_after is not None:count=min(count,max(1,cancel_after-physical))
   if count:
    allowance=float(policy.local_allowance(obs['rho'],tier))*obs['scale'];start=time.monotonic_ns()
    row=service.call('step',generation,count=count,limit=allowance);wall=time.monotonic_ns()-start
    costs['iteration' if mode=='fp4' else 'native_recovery' if bits!=64 else 'iteration']+=wall
    done=row['flags'][4];require(done>0,'no physical progress');physical+=done;logical=row['logical'];gpu_us+=row['gpu_us'];attempted[str(current)]=attempted.get(str(current),0)+done
    flags=row['flags'][:4];events.append(dict(kind='window',lane=list(current),physical=physical,logical=logical,count=done,gpu_us=row['gpu_us'],local_terms=row['local_terms'],flags=flags))
    fault=('projection_ambiguous' if 5 in flags else 'nonfinite' if 1 in flags or 2 in flags else 'local_budget') if any(flags) else None
    if inject and physical>=32 and loads==0:fault=inject
    if fault and mode=='fp4':recovery(fault);continue
    if fault:stop='numerical_failure';break
   if logical-audit_logical>=200 or physical==max_updates:
    start=time.monotonic_ns();export=service.call('export',generation);costs['export']+=time.monotonic_ns()-start;last_export=export
    start=time.monotonic_ns();obs=observation(data,export['raw']);costs['audit']+=time.monotonic_ns()-start
    start=time.monotonic_ns()
    if checker is None:checker=Checker(model_path,tier,directory/'checker.stderr')
    certificate,last_binding=certify(model_path,export['endpoint'],tier,directory,f'audit-{physical}',checker);last_checked_endpoint=export['endpoint'];costs['checker']+=time.monotonic_ns()-start
    audits.append(dict(physical=physical,logical=logical,observation=obs,certificate=last_binding['certificate'],accepted=certificate['accepted'],elapsed_ns=time.monotonic_ns()-entered))
    if certificate['accepted'] and not diagnostic:stop='certified';break
    action='adopt'
    if mode=='fp4':
     decision=policy.audit(state,generation=generation,iteration=logical,candidate=certificate['endpoint_sha256'],candidate_checkpoint=state_hash(export),residual=obs['rho'])
     action=decision['action']
     if action!='adopt':recovery(decision['reason']);continue
     state=decision['state']
    else:state=dataclasses.replace(state,iteration=logical,residual=obs['rho'],checkpoint=state_hash(export),generation=generation)
    checkpoint=export;audit_logical=logical;start=time.monotonic_ns();service.call('save',generation);costs['transport']+=time.monotonic_ns()-start
  # Always independently assess the actual exported endpoint after cancellation/recovery.
  start=time.monotonic_ns();last_export=service.call('export',generation);costs['export']+=time.monotonic_ns()-start
  if stop in ('cancelled','deadline','numerical_failure'):last_export['endpoint']['transport']={'cancelled':'cancelled','deadline':'limit','numerical_failure':'error'}[stop]
  start=time.monotonic_ns()
  if last_export['endpoint']!=last_checked_endpoint:
   if checker is None:checker=Checker(model_path,tier,directory/'checker.stderr')
   certificate,last_binding=certify(model_path,last_export['endpoint'],tier,directory,'final',checker)
  else:events.append(dict(kind='reuse_identical_final_certificate',binding=last_binding))
  costs['checker']+=time.monotonic_ns()-start
  final_checkpoint=dict(device=checkpoint,terminal_export=last_export,controller=dict(logical=state.iteration,checked_iteration=state.iteration,generation=generation,precision=list(current),residual_ratio=[state.residual.numerator,state.residual.denominator],stalls=state.stalls,policy=state.policy),original_model=ref(model_path),settings=dict(shift=request['shift'],tier=tier,max_updates=max_updates,wall_seconds=wall_seconds),operator_sha256=policy.digest(dict(codes=request['codes'],exponents=request['exponents'])),representation=dict(format=current[0],components=current[1],exponent_range=[-48,48],term_semantics='operational-estimates-not-proved-enclosures',last_audit=observation(data,checkpoint['raw']),window_terms=[e for e in events if e.get('kind')=='window']),physical_updates_outside_rollback=physical)
  put(directory/'checkpoint.json',final_checkpoint)
 finally:
  start=time.monotonic_ns();service.close() if session is None else service.finish();costs['transport']+=time.monotonic_ns()-start
  if checker is not None and checker_session is None:
   start=time.monotonic_ns();checker.close();costs['checker']+=time.monotonic_ns()-start
 elapsed=time.monotonic_ns()-entered
 coordination_ns=elapsed-sum(costs.values());require(coordination_ns>=0,'overlapping phase costs');costs['transport']+=coordination_ns
 result=dict(lifecycle='prepared' if session else 'cold',status=stop,family=family,lane=[bits,components],tier=tier,diagnostic=diagnostic,physical_updates=physical,logical_updates=logical,fp4_updates=sum(v for k,v in attempted.items() if k.startswith('(4,')),attempted_updates=attempted,gpu_us=gpu_us,certified=certificate['accepted'],certificate=last_binding,costs_ns=costs,cold_wall_ns=elapsed,coordination_within_transport_ns=coordination_ns,audits=audits,events=events,initial_checkpoint_sha256=initial_checkpoint,final_checkpoint=ref(directory/'checkpoint.json'),model=ref(model_path),binary=ref(BINARY),image=ref(image))
 put(directory/'result.json',result);return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--image',required=True);p.add_argument('--output',required=True);p.add_argument('--family',default='coupled-equality');p.add_argument('--format',type=int,default=4);p.add_argument('--components',type=int,default=2);p.add_argument('--tier',default='certified-1e-7');p.add_argument('--updates',type=int,default=600);p.add_argument('--solve',action='store_true');a=p.parse_args()
 r=run(a.family,a.format,a.components,a.tier,Path(a.image),Path(a.output),a.updates,not a.solve)
 print(json.dumps({k:r[k] for k in ('status','certified','physical_updates','fp4_updates','gpu_us','cold_wall_ns')}))
if __name__=='__main__':main()
