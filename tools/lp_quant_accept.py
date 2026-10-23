"""Source-bound device tests and fixed-work/replay acceptance for ADR-0040."""
import os,json,re,subprocess
from lp_protocol import ROOT,read_json,write_json,checked_reference,file_hash
from benchmark_lp import reference
from benchmark_lp_quant import instances
from lp_quant_budget import protocol,ledger_for,validate_command

def project(v):
 if os.environ.get('AI_OPTIMIZER_GPU_LEASE')!='inherited' or os.environ.get('CUDA_VISIBLE_DEVICES')!=v['device']:raise ValueError('selected shared host lease required')
 study=ROOT/v['output'];d=ROOT/v['acceptance_output']/'project';d.mkdir(parents=True,exist_ok=False);identity=read_json(study/'execution.json');binary=study/'lp_precision_quant';test=checked_reference(ROOT,read_json(study/'acceptance-binaries.json')['quant'])
 r=subprocess.run([str(test),'--test-threads','1','--nocapture'],capture_output=True,text=True,timeout=90,env=dict(os.environ,AI_OPTIMIZER_GPU='1'));(d/'device.stdout').write_text(r.stdout);(d/'device.stderr').write_text(r.stderr);print(r.stdout,flush=True);print(r.stderr,flush=True)
 if r.returncode or '3 passed; 0 failed' not in r.stdout or 'SKIP ' in r.stdout+r.stderr:raise ValueError('quant device differential failure')
 models=instances(v);rows=[];result=dict(status='incomplete',source_tree_sha256=identity['source_tree_sha256'],executable_sha256=file_hash(binary),rows=rows)
 try:
  for name in v['acceptance_instances']:
   for c in v['configurations'][:6]:
    stem=name+'-'+c['id'];rp=d/(stem+'.request.json');ep=d/(stem+'.endpoint.json');model=checked_reference(ROOT,models[name]['model']);request=dict(schema_version=1,identity='lp-quant-v1',settings=c['settings'],model_sha256=file_hash(model),source_tree_sha256=identity['source_tree_sha256'],executable_sha256=file_hash(binary),code_object_sha256=identity['code_object_sha256'],device=v['device'],options=dict(v['solve'],iteration_limit=400,time_limit_ms=30000),method=dict(v['lp_settings'],iteration_limit=400),diagnostic=True,device_buffer_bytes=1<<30);write_json(rp,request)
    for action in ['solve','verify','replay']:
     r=subprocess.run([str(binary),action,str(model),str(rp),str(ep)],capture_output=True,text=True,timeout=30);(d/(stem+'.'+action+'.stdout')).write_text(r.stdout);(d/(stem+'.'+action+'.stderr')).write_text(r.stderr)
     if r.returncode:raise ValueError('quant acceptance '+action+' '+r.stderr[:1200])
    e=read_json(ep)
    if e['outcome']['stop']!='iteration_limit' or e['outcome']['physical']<399:raise ValueError('quant fixed-work horizon incomplete')
    rows.append(dict(instance=name,configuration=c['id'],endpoint=reference(ROOT,ep),replay=reference(ROOT,ep.with_name(ep.name+'.replay.json'))))
  result['status']='passed'
 finally:write_json(d/'acceptance.json',result)
 print('18 fixed-work endpoints and 18 bitwise same-device replays passed',flush=True)
def check_acceptance(v,identity):
 d=ROOT/v['acceptance_output'];found=set();events=[json.loads(x) for x in ledger_for(v).path.read_bytes().splitlines()]
 for source in d.glob('*.source.json'):
  key=source.name[:-len('.source.json')];s=read_json(source);r=read_json(d/(key+'.request.json'));w=read_json(d/(key+'.worker.json'));gate=s['gate'];validate_command(gate,s['command'])
  if s['source_tree_sha256']!=identity['source_tree_sha256'] or s['request_sha256']!=file_hash(d/(key+'.request.json')) or r['command'][2:]!=s['command'] or w['reason']!='completed' or w['returncode']!=0 or w['activity']['device']!=v['device']:raise ValueError('quant acceptance source/worker mismatch')
  transactions=[e for e in events if e['trial_id']==key]
  if len(transactions)!=2 or transactions[1]['charged_ns']!=w['leased_ns'] or w['leased_ns']>transactions[0]['reserved_ns']:raise ValueError('quant acceptance accounting')
  text=(d/(key+'.stdout')).read_text()+(d/(key+'.stderr')).read_text()
  if 'SKIP ' in text:raise ValueError('quant skipped device coverage')
  if gate=='regular' and re.findall(r'test result: ok\. (\d+) passed; 0 failed;',text)!=['14','6','46']:raise ValueError('ordinary gate incomplete')
  if gate not in ['regular','project'] and not ('ERROR SUMMARY: 0 errors' in text or 'RACECHECK SUMMARY: 0 hazards' in text):raise ValueError('sanitizer receipt incomplete')
  found.add(gate)
 if found!={'regular','project','memcheck','racecheck','initcheck','synccheck'}:raise ValueError('quant acceptance gates missing '+str(found))
 a=read_json(d/'project/acceptance.json')
 if a['status']!='passed' or a['source_tree_sha256']!=identity['source_tree_sha256'] or len(a['rows'])!=18:raise ValueError('quant project coverage incomplete')
 for row in a['rows']:
  for key in ['endpoint','replay']:checked_reference(ROOT,row[key])
if __name__=='__main__':project(protocol())
