"""Exact-source device, structural, fixed-work and replay acceptance for ADR-0041."""
import os,re,subprocess,json
from lp_protocol import ROOT,read_json,write_json,checked_reference,file_hash
from benchmark_lp import reference,source_identity
from lp_quant_resident_budget import protocol,ledger_for,validate_command
from lp_quant_resident_admission import make_request
def project(v):
 if os.environ.get('AI_OPTIMIZER_GPU_LEASE')!='inherited' or os.environ.get('CUDA_VISIBLE_DEVICES')!=v['device']:raise ValueError('resident selected lease required')
 from benchmark_lp_quant_resident import instances
 study=ROOT/v['output'];identity=read_json(study/'execution.json');d=ROOT/v['acceptance_output']/'project';d.mkdir(parents=True,exist_ok=False);binary=study/'lp_precision_quant_resident'
 if source_identity()!=identity['source_tree_sha256']:raise ValueError('resident acceptance source changed')
 tests=read_json(study/'acceptance-binaries.json')
 for name in ['quant','resident']:
  test=checked_reference(ROOT,tests[name]);r=subprocess.run([str(test),'--test-threads','1','--nocapture'],capture_output=True,text=True,timeout=90,env=dict(os.environ,AI_OPTIMIZER_GPU='1'));(d/(name+'.stdout')).write_text(r.stdout);(d/(name+'.stderr')).write_text(r.stderr);print(r.stdout,flush=True);print(r.stderr,flush=True)
  if r.returncode or '3 passed; 0 failed' not in r.stdout or 'SKIP ' in r.stdout+r.stderr:raise ValueError('resident device suite failure '+name)
 models=instances(v);rows=[];result=dict(status='incomplete',source_tree_sha256=identity['source_tree_sha256'],rows=rows)
 roster=[(n,c,'ordinary') for n in v['acceptance_instances'] for c in v['configurations']]+[('gpup-development-irregular-2048',c,'structural') for c in v['configurations'][6:8]]
 try:
  for name,c,kind in roster:
   stem=name+'-'+c['id'];rp=d/(stem+'.request.json');ep=d/(stem+'.endpoint.json');model=checked_reference(ROOT,models[name]['model']);request=make_request(c,model,binary,identity['source_tree_sha256'],work=400,horizon=64,seconds=30);request['code_object_sha256']=identity['code_object_sha256'];write_json(rp,request)
   for action in ['solve','verify','replay']:
    r=subprocess.run([str(binary),action,str(model),str(rp),str(ep)],capture_output=True,text=True,timeout=30);(d/(stem+'.'+action+'.stdout')).write_text(r.stdout);(d/(stem+'.'+action+'.stderr')).write_text(r.stderr)
    if r.returncode:raise ValueError('resident acceptance '+action+' '+r.stderr[:2000])
   e=read_json(ep);core=e['outcome']['core']
   if core['stop']!='work_horizon' or core['iterations']!=64 or core['failure'] is not None or e['host_product_scans'] or e['product_vector_transfers'] or e['device_windows']!=e['outcome']['counts']['windows'] or e['state_uploads']!=e['device_windows']:raise ValueError('resident fixed-work/structure contract failed')
   rows.append(dict(instance=name,configuration=c['id'],kind=kind,endpoint=reference(ROOT,ep),replay=reference(ROOT,ep.with_name(ep.name+'.replay.json')),logical=core['iterations'],physical=core['physical'],device_windows=e['device_windows'],state_uploads=e['state_uploads']))
  result['status']='passed'
 finally:write_json(d/'acceptance.json',result)
 print('29 fixed-work endpoints and 29 bitwise same-device replays passed',flush=True)
def check_acceptance(v,identity):
 from lp_quant_resident_bridge import verify as source_bridge
 before=source_bridge();allowed_sources={identity['source_tree_sha256'],before}
 d=ROOT/v['acceptance_output'];found=set();events=[json.loads(x) for x in ledger_for(v).path.read_bytes().splitlines()]
 for source in d.glob('*.source.json'):
  key=source.name[:-len('.source.json')];s=read_json(source);r=read_json(d/(key+'.request.json'));w=read_json(d/(key+'.worker.json'));gate=s['gate'];validate_command(gate,s['command'])
  if s['source_tree_sha256'] not in allowed_sources or s['request_sha256']!=file_hash(d/(key+'.request.json')) or r['command'][2:]!=s['command'] or w['reason']!='completed' or w['returncode']!=0 or w['activity']['device']!=v['device']:raise ValueError('resident acceptance source/worker differs')
  transactions=[e for e in events if e['trial_id']==key]
  if len(transactions)!=2 or transactions[1]['charged_ns']!=w['leased_ns'] or w['leased_ns']>transactions[0]['reserved_ns']:raise ValueError('resident acceptance accounting differs')
  text=(d/(key+'.stdout')).read_text()+(d/(key+'.stderr')).read_text()
  if 'SKIP ' in text:raise ValueError('resident skipped GPU acceptance')
  if gate=='regular' and re.findall(r'test result: ok\. (\d+) passed; 0 failed;',text)!=['14','6','46']:raise ValueError('resident ordinary gate incomplete')
  if gate not in ['regular','project'] and not ('ERROR SUMMARY: 0 errors' in text or 'RACECHECK SUMMARY: 0 hazards' in text):raise ValueError('resident sanitizer receipt incomplete')
  found.add(gate)
 if found!={'regular','project','memcheck','racecheck','initcheck','synccheck'}:raise ValueError('resident acceptance gate missing')
 a=read_json(d/'project/acceptance.json')
 if a['status']!='passed' or a['source_tree_sha256'] not in allowed_sources or len(a['rows'])!=29:raise ValueError('resident project acceptance incomplete')
 for row in a['rows']:
  for key in ['endpoint','replay']:checked_reference(ROOT,row[key])
if __name__=='__main__':project(protocol())
