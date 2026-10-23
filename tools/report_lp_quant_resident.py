"""Independent append-only accounting and endpoint report for ADR-0041."""
import argparse,hashlib,json,tarfile,subprocess,statistics
from pathlib import Path
from collections import Counter
from lp_protocol import ROOT,read_json,write_json,file_hash,checked_reference,validate
from lp_quant_resident_budget import protocol,CONFIG,PREFIX
from benchmark_lp_quant_resident import jobs,effective,prepare_inputs,verify_endpoint,refs,micro_jobs
from benchmark_lp_adaptive_cost import endpoint_shape
from lp_quant_resident_accept import check_acceptance
from report_lp_setup import paired_ratios
def ledger(v,path):
 raw=path.read_bytes();lines=raw.splitlines(keepends=True)
 if not raw.endswith(b'\n') or hashlib.sha256(b''.join(lines[:17036])).hexdigest()!=PREFIX:raise ValueError('quant historical prefix differs')
 events=[json.loads(x) for x in lines];pending={};seen=set();phases=Counter();charges=Counter()
 for n,e in enumerate(events):
  validate('ledger',e)
  if e['sequence']!=n or e['campaign_sha256']!=v['budget_authority']['sha256']:raise ValueError('ledger sequence/identity')
  key=e['reservation_id']
  if e['kind']=='reserve':
   if key in seen or e['charged_ns']!=0:raise ValueError('duplicate reservation')
   pending[key]=e;seen.add(key)
  else:
   previous=pending.pop(key,None)
   if previous is None or any(previous[k]!=e[k] for k in ['trial_id','resource','phase','reserved_ns']):raise ValueError('unmatched settlement')
   if e['kind']=='recover' and e['charged_ns']!=e['reserved_ns']:raise ValueError('undercharged recovery')
  if e['resource']=='gpu':
   phases[e['phase']]+=e['charged_ns']
   for c in v['categories']:
    if e['trial_id'].startswith(v['id']+'-'+c+'-'):charges[c]+=e['charged_ns']
 if pending or sum(phases.values())>min(v['cumulative_gpu_ns'],28800*10**9) or any(phases[k]>cap*10**9 for k,cap in v['phase_gpu_seconds'].items()) or any(charges[k]>cap['seconds']*10**9 for k,cap in v['categories'].items()) or sum(charges.values())>3600*10**9:raise ValueError('unsettled/exceeded resource contract')
 return events,dict(charges),sum(phases.values())
def archive(v,d):
 identity=read_json(d/'execution.json')
 if read_json(d/'campaign.json')!=v:raise ValueError('frozen campaign differs')
 for name,key in [('source.tar','source_archive_sha256'),('optimizer','binary_sha256'),('lp_precision_quant_resident','exec_binary_sha256')]:
  if file_hash(d/name)!=identity[key]:raise ValueError('frozen archive binding '+name)
 for name,sha in read_json(d/'code-objects.json').items():
  if file_hash(d/name)!=sha:raise ValueError('frozen image inventory '+name)
 digest=hashlib.sha256()
 with tarfile.open(d/'source.tar') as source:
  members=source.getmembers();names=[m.name for m in members]
  if names!=sorted(set(names)) or any(not m.isfile() or Path(m.name).is_absolute() or '..' in Path(m.name).parts for m in members):raise ValueError('source archive layout')
  for m in members:digest.update(m.name.encode()+b'\0'+source.extractfile(m).read()+b'\0')
 if digest.hexdigest()!=identity['source_tree_sha256']:raise ValueError('frozen source digest')
 gate=read_json(d/'native-gate.json')
 if not gate['native'] or gate['source_tree_sha256']!=identity['source_tree_sha256']:raise ValueError('frozen native gate')
 return identity

def tile_counts(model):
 doc=read_json(model);variables=doc['variables'];constraints=doc['constraints']
 if [v['id'] for v in variables]!=sorted(v['id'] for v in variables) or [r['id'] for r in constraints]!=sorted(r['id'] for r in constraints):raise ValueError('noncanonical frozen model order')
 columns={v['id']:i for i,v in enumerate(variables)};counts=Counter()
 for i,row in enumerate(constraints):
  ids=[t['variable_id'] for t in row['terms']]
  if len(ids)!=len(set(ids)):raise ValueError('duplicate frozen coefficients')
  for t in row['terms']:
   if t['coefficient']!=0:counts[(i//32,columns[t['variable_id']]//32)]+=1
 return [counts[k] for k in sorted(counts)]

def successful_solve(e,backend):
 if 'outcome' in e:return e['executor']=='gpu' and e['outcome']['core']['stop']=='certified' and e['outcome']['core']['failure'] is None
 return e['record']['backend']==backend and e['record']['termination']=='optimal'

def profile_complete(e,work,verified=True):
 if not verified or e.get('executor')!='gpu' or not e['request']['diagnostic'] or e['request']['horizon']!=work:return False
 o=e['outcome'];c=o['core']
 return o['horizon']==work and c['stop']=='work_horizon' and c['iterations']==work and c['failure'] is None and o['counts']['uncertain']==0

def profile_eligible(e,work,verified,trial,worker):
 return bool(verified and trial and trial['status']=='completed' and worker and worker['reason']=='completed' and worker['returncode']==0 and profile_complete(e,work,verified))

def verify_cpu_cohorts():
 rows=[]
 for cohort in ['cpu-admission','final-admission','accepted-admission']:
  d=ROOT/'artifacts/gpup-quant-resident-v1'/cohort;a=read_json(d/'admission.json');binary=d/'lp_precision_quant_resident'
  if file_hash(binary)!=a['executable_sha256']:raise ValueError('CPU cohort executable changed')
  checked_reference(ROOT,a['source_archive'])
  for row in a['rows']:
   if 'endpoint' not in row:continue
   ep=checked_reference(ROOT,row['endpoint']);rp=ep.parent/'request.json';request=read_json(rp)
   from benchmark_lp_quant_resident import instances
   model=checked_reference(ROOT,instances(protocol())[row['model']]['model'])
   if request['source_tree_sha256']!=a['source_tree_sha256'] or request['executable_sha256']!=a['executable_sha256']:raise ValueError('CPU cohort request binding')
   r=subprocess.run([str(binary),'verify',str(model),str(rp),str(ep)],capture_output=True,text=True,timeout=120)
   if r.returncode or r.stdout.strip()!='verified':raise ValueError('retained CPU endpoint rejected '+r.stderr[:1000])
  rows.append(dict(cohort=cohort,verified=sum('endpoint' in r for r in a['rows']),executable_sha256=a['executable_sha256']))
 return rows

def report():
 v=protocol();d=ROOT/v['output'];identity=archive(v,d);check_acceptance(v,identity);events,charges,cumulative=ledger(v,d/'ledger.jsonl');rows=[];timings={};counts_cache={};profiles=[]
 admission=read_json(checked_reference(ROOT,v['cpu_admission']));eligibility={(r['model'],r['configuration']):r['eligible'] for r in admission['rows']}
 for j in jobs(v):
  key=j['id'];name=j['instance']['id'];config=j['configuration']['id'];path=d/(key+'.trial.json');row=dict(id=key,instance=name,configuration=config,kind=j['kind'],repetition=j['repetition'],status='unexecuted',verified=False,certified=False)
  if not path.exists():
   if any(e['trial_id']==key for e in events):raise ValueError('attempted identity lacks trial')
   rows.append(row);continue
  t=read_json(path)
  if t['job']!=j or t['id']!=key:raise ValueError('trial roster differs')
  if t['status']=='cpu_admission_refusal':
   if eligibility[(name,config)] or t['charged_ns'] or any(e['trial_id']==key for e in events):raise ValueError('incorrect CPU refusal')
   row['status']=t['status'];rows.append(row);continue
  request=read_json(d/(key+'.request.json'));expected,docs=prepare_inputs(v,j,d,identity)
  if request!=expected or t['campaign_sha256']!=file_hash(CONFIG) or t['source_tree_sha256']!=identity['source_tree_sha256'] or t['request_sha256']!=file_hash(d/(key+'.request.json')) or t['artifacts']!=refs(d,key):raise ValueError('trial request/source/artifact binding')
  for filename,data in docs.items():
   if read_json(d/filename)!=data:raise ValueError('frozen request differs')
  tx=[e for e in events if e['trial_id']==key]
  if len(tx)!=2 or tx[0]['kind']!='reserve' or tx[1]['kind'] not in ['settle','recover'] or any(e['reserved_ns']!=(effective(v,j)[2]+6)*10**9 or e['phase']!=v['categories'][j['category']]['phase'] for e in tx):raise ValueError('trial reservation differs')
  w=read_json(d/(key+'.worker.json')) if t['artifacts']['worker'] else None;charge=tx[1]['charged_ns']
  if charge!=t.get('charged_ns',charge) or charge!=(w['leased_ns'] if w and tx[1]['kind']=='settle' else tx[0]['reserved_ns']):raise ValueError('trial charge differs')
  if w and (w['activity']['device']!=v['device'] or charge>tx[0]['reserved_ns']):raise ValueError('worker device/charge')
  a=e=None;error=None
  if t['artifacts']['endpoint']:
   try:
    a=verify_endpoint(v,j,d,identity);e=read_json(d/(key+'.endpoint.json')) if j['kind']=='profile' or j['configuration']['backend']=='lp-quant-resident-v1' else endpoint_shape(d/(key+'.endpoint.json'),'compact-v1')
   except Exception as exc:
    if t['assessment'] is not None:raise
    error=str(exc)
  if a!=t['assessment'] and not(t['status']=='interrupted' and t['assessment'] is None):raise ValueError('retained assessment differs')
  good=bool(a and a['gap_closed'] and e and successful_solve(e,j['configuration']['backend']) and t['status']=='completed' and w and w['reason']=='completed' and w['returncode']==0)
  row.update(status=t['status'],verified=a is not None,certified=good,assessment=a,verification_error=error,elapsed_ns=None if w is None else w['elapsed_ns'],charged_ns=charge)
  if e and 'outcome' in e:
   o=e['outcome'];core=o['core'];counts=counts_cache.get(name)
   if counts is None:counts=tile_counts(checked_reference(ROOT,j['instance']['model']));counts_cache[name]=counts
   if len(counts)!=len(core['promotion']['mask']):raise ValueError('promotion canonical tile count')
   promoted=sum(c for c,m in zip(counts,core['promotion']['mask']) if m)
   row.update(termination=core['stop'],failure=core['failure'],physical=core['physical'],logical=core['iterations'],work=core['work'],counts=o['counts'],first_certified_iteration=o['first_certified_iteration'],promoted_coefficients=promoted,promoted_fraction=promoted/max(1,sum(counts)),promotion={k:core['promotion'][k] for k in ['generation','transitions','native']},phases_ns=e['phases_ns'],launches=e['launches'],upload_bytes=e['upload_bytes'],readback_bytes=e['readback_bytes'],device_peak_bytes=e['device_peak_bytes'],device_windows=e['device_windows'],state_uploads=e['state_uploads'],host_product_scans=e['host_product_scans'],product_vector_transfers=e['product_vector_transfers'])
  if j['kind']=='profile':profiles.append(dict(id=key,configuration=config,verified=a is not None,eligible=bool(e and profile_eligible(e,v['profile_work'],a is not None,t,w)),physical=None if e is None else e['outcome']['core']['physical'],logical=None if e is None else e['outcome']['core']['iterations']))
  if j['kind']=='timing' and good:timings[(name,config,j['repetition'])]=w['elapsed_ns']
  rows.append(row)
 for j in jobs(v):
  if j['kind']=='profile' and not any(p['id']==j['id'] for p in profiles):profiles.append(dict(id=j['id'],configuration=j['configuration']['id'],verified=False,eligible=False,reason=next(r['status'] for r in rows if r['id']==j['id'])))
 comparisons=[]
 contrasts=[(c['id'],control) for c in v['configurations'][:6] for control in ['resident-matched-fp64','tuned-fp64']]+[('resident-matched-fp64','resident-bridge-fp64'),('resident-bridge-fp64','tuned-fp64'),('resident-matched-fp64','tuned-fp64')]
 for name in v['timing_instances']:
  for candidate,control in contrasts:
   pairs=[(timings[(name,control,r)],timings[(name,candidate,r)]) for r in range(3) if (name,control,r) in timings and (name,candidate,r) in timings]
   comparisons.append(dict(instance=name,configuration=candidate,control=control,pairs=len(pairs),uncertainty=None if not pairs else paired_ratios(pairs,seed=v['analysis']['seed'],resamples=v['analysis']['resamples'])))
 micro=[]
 from lp_quant_resident_micro import verify_available
 for j in micro_jobs(v):
  key=j['id'];path=d/(key+'.trial.json');t=read_json(path) if path.exists() else None
  if t:
   tx=[e for e in events if e['trial_id']==key];w=read_json(d/(key+'.worker.json'))
   if len(tx)!=2 or tx[0]['reserved_ns']!=36*10**9 or tx[1]['charged_ns']!=t['charged_ns'] or t['charged_ns']!=w['leased_ns'] or w['activity']['device']!=v['device'] or t['source_tree_sha256']!=identity['source_tree_sha256'] or t['request_sha256']!=file_hash(d/(key+'.request.json')):raise ValueError('micro accounting/identity differs')
  verified=verify_available(v,d,j['mode']);entries=[]
  for r in verified:
   ep=d/'micro'/(j['mode']+'-'+r['configuration']+'.endpoint.json');e=read_json(ep)
   if e['request']!=read_json(ep.with_name(ep.name.replace('.endpoint.','.request.'))) or e['request']['request']['source_tree_sha256']!=identity['source_tree_sha256']:raise ValueError('micro request differs')
   entries.append(dict(configuration=r['configuration'],elapsed_ns=e['elapsed_ns'],rows=e['rows'],counters=e['counters']))
  micro.append(dict(mode=j['mode'],status='unexecuted' if t is None else t['status'],verified=len(entries),entries=entries))
 # Every acceptance endpoint and its independent replay are reverified on CPU.
 a=read_json(ROOT/v['acceptance_output']/'project/acceptance.json');models=__import__('benchmark_lp_quant_resident').instances(v);accept_verified=0
 for row in a['rows']:
  ep=checked_reference(ROOT,row['endpoint']);rp=ep.with_name(ep.name.replace('.endpoint.','.request.'));model=checked_reference(ROOT,models[row['instance']]['model'])
  for endpoint in [ep,checked_reference(ROOT,row['replay'])]:
   r=subprocess.run([str(d/'lp_precision_quant_resident'),'verify',str(model),str(rp),str(endpoint)],capture_output=True,text=True,timeout=120)
   if r.returncode or r.stdout.strip()!='verified':raise ValueError('acceptance endpoint rejected '+r.stderr[:1000])
   accept_verified+=1
 return dict(identity='gpup-quant-resident-report-v1',source_tree_sha256=identity['source_tree_sha256'],cpu_admission=v['cpu_admission'],planned_attempts=120,planned_timings=108,attempts=sum(r['status'] not in ['unexecuted','cpu_admission_refusal'] for r in rows)+sum(m['status']!='unexecuted' for m in micro),cpu_refusals=sum(r['status']=='cpu_admission_refusal' for r in rows),verified=sum(r['verified'] for r in rows),acceptance_endpoints_verified=accept_verified,cpu_cohorts=verify_cpu_cohorts(),certified_timings=sum(r['kind']=='timing' and r['certified'] for r in rows),profiles=profiles,micro=micro,comparisons=comparisons,rows=rows,categories_ns=charges,task_gpu_ns=sum(charges.values()),cumulative_gpu_ns=cumulative,ledger_events=len(events),ledger_sha256=file_hash(d/'ledger.jsonl'))

def main():
 from lp_quant_report_output import report_output
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args();output=report_output(a.output)
 r=report();write_json(output,r)
 print({k:r[k] for k in ['attempts','cpu_refusals','verified','certified_timings','task_gpu_ns','cumulative_gpu_ns','ledger_events','ledger_sha256']})
if __name__=='__main__':main()

