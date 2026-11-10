"""Frozen Tensor device differentials, endpoint/replay acceptance and receipts."""
import os,re,subprocess,json
from lp_protocol import ROOT,read_json,write_json,checked_reference,file_hash
from benchmark_lp import source_identity,reference
from lp_tensor_common import protocol,instances,make_request,ledger_for

def project(v):
 if os.environ.get('AI_OPTIMIZER_GPU_LEASE')!='inherited' or os.environ.get('CUDA_VISIBLE_DEVICES')!=v['device']:raise ValueError('selected lease required')
 d=ROOT/v['output'];identity=read_json(d/'execution.json');out=ROOT/v['acceptance_output']/'project';out.mkdir(parents=True,exist_ok=False)
 tests=read_json(d/'acceptance-binaries.json');test=checked_reference(ROOT,tests['tensor']);r=subprocess.run([str(test),'tensor_','--test-threads','1','--nocapture'],capture_output=True,text=True,timeout=100,env=dict(os.environ,AI_OPTIMIZER_GPU='1'));(out/'tensor.stdout').write_text(r.stdout);(out/'tensor.stderr').write_text(r.stderr);print(r.stdout,flush=True);print(r.stderr,flush=True)
 if r.returncode or '3 passed; 0 failed' not in r.stdout or 'SKIP ' in r.stdout+r.stderr:raise ValueError('Tensor device suite failure')
 # Actual-model fixed-work solves obey CPU admission, including refused candidates.
 admission=read_json(ROOT/'docs/benchmarks/data/tensor/cpu-admission.json');eligible={(r['model'],r['configuration']):r['eligible'] for r in admission['rows']};rows=[]
 for name in v['timing_instances']:
  for c in v['configurations']:
   if not eligible[(name,c['id'])]:rows.append(dict(instance=name,configuration=c['id'],status='cpu_admission_refusal'));continue
   model=checked_reference(ROOT,instances(v)[name]['model']);stem=name+'-'+c['id'];rp=out/(stem+'.request.json');ep=out/(stem+'.endpoint.json');request=make_request(c,model,d/'lp_precision_tensor',identity['source_tree_sha256'],work=480,horizon=64);request['code_object_sha256']=identity['code_object_sha256'];write_json(rp,request)
   for action in ['solve','verify','replay']:
    r=subprocess.run([str(d/'lp_precision_tensor'),action,str(model),str(rp),str(ep)],capture_output=True,text=True,timeout=40);(out/(stem+'.'+action+'.stdout')).write_text(r.stdout);(out/(stem+'.'+action+'.stderr')).write_text(r.stderr)
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
if __name__=='__main__':project(protocol())
