"""Frozen Tensor device differentials, endpoint/replay acceptance and receipts."""
import os,re,subprocess,json
from lp_protocol import ROOT,read_json,write_json,checked_reference,file_hash
from benchmark_lp import source_identity,reference
from lp_tensor_cost_common import protocol,instances,make_request,ledger_for

def project(v):
 if os.environ.get('AI_OPTIMIZER_GPU_LEASE')!='inherited' or os.environ.get('CUDA_VISIBLE_DEVICES')!=v['device']:raise ValueError('selected lease required')
 d=ROOT/v['output'];identity=read_json(d/'execution.json');out=ROOT/v['acceptance_output']/'project';out.mkdir(parents=True,exist_ok=False)
 tests=read_json(d/'acceptance-binaries.json');test=checked_reference(ROOT,tests['tensor-cost']);r=subprocess.run([str(test),'tensor_','--test-threads','1','--nocapture'],capture_output=True,text=True,timeout=100,env=dict(os.environ,AI_OPTIMIZER_GPU='1'));(out/'tensor.stdout').write_text(r.stdout);(out/'tensor.stderr').write_text(r.stderr);print(r.stdout,flush=True);print(r.stderr,flush=True)
 if r.returncode or '3 passed; 0 failed' not in r.stdout or 'SKIP ' in r.stdout+r.stderr:raise ValueError('Tensor device suite failure')
 # Actual-model fixed-work solves obey CPU admission, including refused candidates.
 admission=read_json(d/'cpu-admission.json');eligible={(r['model'],r['configuration']):r['eligible'] for r in admission['rows']};rows=[]
 for name in v['timing_instances']:
  for c in v['configurations']:
   if not eligible[(name,c['id'])]:rows.append(dict(instance=name,configuration=c['id'],status='cpu_admission_refusal'));continue
   model=checked_reference(ROOT,instances(v)[name]['model']);stem=name+'-'+c['id'];rp=out/(stem+'.request.json');ep=out/(stem+'.endpoint.json');request=make_request(c,model,d/'lp_precision_tensor_cost',identity['source_tree_sha256'],work=480,horizon=64);request['code_object_sha256']=identity['code_object_sha256'];write_json(rp,request)
   for action in ['solve','verify','replay']:
    from benchmark_lp_tensor_cost import numeric_command
    r=subprocess.run(numeric_command([str(d/'lp_precision_tensor_cost'),action,str(model),str(rp),str(ep)]),capture_output=True,text=True,timeout=40);(out/(stem+'.'+action+'.stdout')).write_text(r.stdout);(out/(stem+'.'+action+'.stderr')).write_text(r.stderr)
    if r.returncode:raise ValueError('Tensor endpoint '+action+' '+r.stderr[:2000])
   e=read_json(ep)
   if e['outcome']['core']['stop']!='work_horizon':raise ValueError('incomplete acceptance horizon')
   rows.append(dict(instance=name,configuration=c['id'],status='passed',endpoint=reference(ROOT,ep),replay=reference(ROOT,ep.with_name(ep.name+'.replay.json'))))
 write_json(out/'acceptance.json',dict(status='passed',source_tree_sha256=identity['source_tree_sha256'],rows=rows));print('Tensor device suites and admitted fixed-work/replay pairs pass',flush=True)

def check_acceptance(v,identity):
 d=ROOT/v['acceptance_output'];found=set();events=[json.loads(x) for x in ledger_for(v).path.read_bytes().splitlines()]
 for p in d.glob('*.source.json'):
  s=read_json(p);key=p.name[:-len('.source.json')];r=read_json(d/(key+'.request.json'));w=read_json(d/(key+'.worker.json'))
  if s['source_tree_sha256']!=identity['source_tree_sha256'] or file_hash(d/(key+'.request.json'))!=s['request_sha256'] or r['command'][2:]!=s['command'] or w['reason']!='completed' or w['returncode']!=0:raise ValueError('acceptance source/worker differs')
  tx=[e for e in events if e['trial_id']==key]
  if len(tx)!=2 or tx[1]['charged_ns']!=w['leased_ns'] or w['leased_ns']>tx[0]['reserved_ns']:raise ValueError('acceptance ledger differs')
  text=(d/(key+'.stdout')).read_text()+(d/(key+'.stderr')).read_text();gate=s['gate']
  if 'SKIP ' in text:raise ValueError('skipped device acceptance')
  if gate=='regular' and re.findall(r'test result: ok\. (\d+) passed; 0 failed;',text)!=['14','6','46']:raise ValueError('ordinary suite incomplete')
  if gate not in ['regular','project'] and not ('ERROR SUMMARY: 0 errors' in text or 'RACECHECK SUMMARY: 0 hazards' in text):raise ValueError('sanitizer receipt missing')
  found.add(gate)
 if found!={'regular','project','memcheck','racecheck','initcheck','synccheck'}:raise ValueError('acceptance gate missing')
 if read_json(d/'project/acceptance.json')['status']!='passed':raise ValueError('project acceptance missing')

def acceptance_jobs():
 return [('regular',60),('project',180),('memcheck',40),('racecheck',100),('initcheck',40),('synccheck',40)]

def acceptance_request(v,d,gate,seconds):
 from benchmark_lp_tensor_cost import numeric_command
 tests=read_json(d/'acceptance-binaries.json')
 if gate=='regular':command=['bash',str(ROOT/'tools/lp_exec_regular_check.sh'),*[str(checked_reference(ROOT,tests[k])) for k in ['optimizer-cuda','optimizer-schedule-examples','optimizer-lp-cuda']]]
 elif gate=='project':command=['python3',str(ROOT/'tools/lp_tensor_cost_accept.py')]
 else:command=['bash',str(ROOT/'tools/lp_tensor_cost_gpu_check.sh'),str(checked_reference(ROOT,tests['tensor-cost'])),gate]
 return dict(schema_version=2,gpu_admission_seconds=3,command=['/usr/bin/env','AI_OPTIMIZER_CUDA_DIR='+str(d),*numeric_command(command)],directory=str(ROOT/v['acceptance_output']),prefix=v['id']+'-accept-'+gate,solve_seconds=seconds,cleanup_seconds=2,host_rss_bytes=v['limits']['host_rss_bytes'],poll_ms=10,output_bytes=v['limits']['output_bytes'])

def run_acceptance(v,d,identity):
 from lp_tensor_cost_common import receipt
 import shutil
 out=ROOT/v['acceptance_output'];out.mkdir(parents=True,exist_ok=True)
 with ledger_for(v) as ledger:
  for gate,seconds in acceptance_jobs():
   key=v['id']+'-accept-'+gate
   if key in ledger.attempted() or (out/(key+'.request.json')).exists():raise ValueError('acceptance identity cannot retry')
   if source_identity()!=identity['source_tree_sha256']:raise ValueError('acceptance source changed')
   request=acceptance_request(v,d,gate,seconds)
   if request!=read_json(d/(key+'.frozen.json')):raise ValueError('acceptance request differs from freeze')
   path=out/(key+'.request.json');write_json(path,request)
   write_json(out/(key+'.source.json'),dict(source_tree_sha256=identity['source_tree_sha256'],request_sha256=file_hash(path),command=request['command'][2:],gate=gate))
   reservation=ledger.reserve(key,seconds+6,phase='repeatability')
   worker=subprocess.Popen(['bash',str(ROOT/'tools/gpu_job.sh'),v['device'],'--lp-study-request',str(path)],pass_fds=(ledger.lock.fileno(),))
   try:worker.wait(timeout=seconds+310)
   finally:
    if worker.poll() is None:worker.terminate();worker.wait(timeout=3)
    wp=out/(key+'.worker.json');info=read_json(wp) if wp.exists() else None
    charge=info['leased_ns'] if info else reservation['reserved_ns'];ledger.settle(reservation,charge)
    write_json(d/'budget.json',receipt(ledger));shutil.copy2(ledger.path,d/'ledger.jsonl')
   print(key+': '+str(info['reason'] if info else 'missing worker'),flush=True)
   if info is None or info['reason']!='completed' or info['returncode']!=0 or worker.returncode or charge>reservation['reserved_ns']:raise ValueError('device acceptance failed; retain identity and stop')
 check_acceptance(v,identity)
if __name__=='__main__':project(protocol())
