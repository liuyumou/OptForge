"""Independent frozen-source, endpoint and append-only ledger report for GPUP-7."""
import argparse,hashlib,json,tarfile
from pathlib import Path
from collections import Counter
from lp_protocol import ROOT,read_json,write_json,file_hash,checked_reference,validate
from lp_quant_budget import protocol,CONFIG,PREFIX
from benchmark_lp_quant import jobs,effective,prepare_inputs,verify_endpoint,refs
from benchmark_lp_adaptive_cost import endpoint_shape
from lp_quant_accept import check_acceptance
from report_lp_setup import paired_ratios

def ledger(v,path):
 raw=path.read_bytes();lines=raw.splitlines(keepends=True)
 if not raw.endswith(b'\n') or hashlib.sha256(b''.join(lines[:16816])).hexdigest()!=PREFIX:raise ValueError('quant historical prefix differs')
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
 for name,key in [('source.tar','source_archive_sha256'),('optimizer','binary_sha256'),('lp_precision_quant','exec_binary_sha256')]:
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

def successful_solve(endpoint,requested_backend):
 if 'outcome' in endpoint:return endpoint['executor']=='gpu' and endpoint['outcome']['stop']=='certified'
 return endpoint['record']['backend']==requested_backend and endpoint['record']['termination']=='optimal'

def profile_complete(endpoint,work):
 if 'outcome' in endpoint:
  o=endpoint['outcome'];return endpoint['executor']=='gpu' and o['stop']=='iteration_limit' and o['physical']==work and o['failure'] is None
 d=endpoint['diagnostics'];c=endpoint.get('control',{})
 return d['profile'] and d['iterations']==work and c.get('physical_iterations')==work and c.get('logical_iterations')==work and endpoint['record']['termination'] in ['optimal','iteration_limit']

def profile_eligible(endpoint,work,verified,trial,worker):
 return bool(verified and trial and trial['status']=='completed' and worker and worker['reason']=='completed' and worker['returncode']==0 and profile_complete(endpoint,work))

def report():
 v=protocol();d=ROOT/v['output'];identity=archive(v,d);check_acceptance(v,identity);events,charges,cumulative=ledger(v,d/'ledger.jsonl');rows=[];timings={};profiles=[];counts_cache={}
 admission=read_json(checked_reference(ROOT,v['cpu_admission']));eligibility={(r['model'],r['configuration']):r['eligible'] for r in admission['rows']}
 for j in jobs(v):
  key=j['id'];path=d/(key+'.trial.json');name=j['instance']['id'];config=j['configuration']['id'];row=dict(id=key,instance=name,configuration=config,kind=j['kind'],repetition=j['repetition'],status='unexecuted',verified=False,certified=False)
  if not path.exists():
   if any(e['trial_id']==key for e in events):raise ValueError('attempted identity lacks trial')
   rows.append(row);continue
  t=read_json(path)
  if t['job']!=j or t['id']!=key:raise ValueError('trial roster differs')
  if t['status']=='cpu_admission_refusal':
   if j['configuration']['backend']!='lp-quant-v1' or eligibility[(name,config)] or any(e['trial_id']==key for e in events):raise ValueError('incorrect CPU refusal')
   row['status']=t['status'];rows.append(row);continue
  request=read_json(d/(key+'.request.json'));expected,docs=prepare_inputs(v,j,d,identity)
  if request!=expected or t['campaign_sha256']!=file_hash(CONFIG) or t['source_tree_sha256']!=identity['source_tree_sha256'] or t['request_sha256']!=file_hash(d/(key+'.request.json')) or t['artifacts']!=refs(d,key):raise ValueError('trial request/source/artifact binding')
  for filename,data in docs.items():
   if read_json(d/filename)!=data:raise ValueError('frozen request differs')
  transactions=[e for e in events if e['trial_id']==key]
  if len(transactions)!=2 or transactions[0]['kind']!='reserve' or transactions[1]['kind'] not in ['settle','recover'] or any(e['reserved_ns']!=(effective(v,j)[2]+6)*10**9 or e['phase']!=v['categories'][j['category']]['phase'] for e in transactions):raise ValueError('trial reservation differs')
  w=read_json(d/(key+'.worker.json')) if t['artifacts']['worker'] else None;charge=transactions[1]['charged_ns']
  if charge!=t.get('charged_ns',charge) or charge!=(w['leased_ns'] if w and transactions[1]['kind']=='settle' else transactions[0]['reserved_ns']):raise ValueError('trial charge differs')
  if w and (w['activity']['device']!=v['device'] or charge>transactions[0]['reserved_ns']):raise ValueError('worker device/charge')
  a=None;e=None;verification_error=None
  if t['artifacts']['endpoint']:
   try:a=verify_endpoint(v,j,d,identity);e=read_json(d/(key+'.endpoint.json')) if j['configuration']['backend']=='lp-quant-v1' else endpoint_shape(d/(key+'.endpoint.json'),'compact-v1')
   except Exception as error:
    if t['assessment'] is not None:raise
    verification_error=str(error)
  if a!=t['assessment'] and not(t['status']=='interrupted' and t['assessment'] is None):raise ValueError('retained assessment differs')
  successful=e is not None and successful_solve(e,j['configuration']['backend'])
  good=bool(a and a['gap_closed'] and successful and t['status']=='completed' and w and w['reason']=='completed' and w['returncode']==0)
  row.update(status=t['status'],verified=a is not None,certified=good,assessment=a,verification_error=verification_error,elapsed_ns=None if w is None else w['elapsed_ns'],charged_ns=charge)
  if e and 'outcome' in e:
   o=e['outcome'];counts=counts_cache.get(name)
   if counts is None:counts=tile_counts(checked_reference(ROOT,j['instance']['model']));counts_cache[name]=counts
   if len(counts)!=len(o['promotion']['mask']):raise ValueError('promotion canonical tile count')
   promoted=sum(c for c,m in zip(counts,o['promotion']['mask']) if m)
   row.update(termination=o['stop'],failure=o['failure'],physical=o['physical'],iterations=o['iterations'],work=o['work'],promoted_tiles=sum(1 for x in o['promotion']['mask'] if x),promoted_coefficients=promoted,promoted_fraction=promoted/max(1,sum(counts)),promotion={k:o['promotion'][k] for k in ['generation','transitions','native']},phases_ns=e['phases_ns'],launches=e['launches'],upload_bytes=e['upload_bytes'],readback_bytes=e['readback_bytes'])
   if j['kind']=='profile':profiles.append(dict(id=key,configuration=config,eligible=a is not None and profile_complete(e,v['profile_work']),physical=o['physical'],logical=o['iterations'],low_products=o['work']['low_products'],high_products=o['work']['high_products'],phases_ns=e['phases_ns']))
  if j['kind']=='timing' and good:timings[(name,config,j['repetition'])]=w['elapsed_ns']
  rows.append(row)
 # Keep every diagnostic cell visible, including missing and early-success horizons.
 profiles=[]
 for j in jobs(v):
  if j['kind']!='profile':continue
  row=next(r for r in rows if r['id']==j['id']);entry=dict(id=j['id'],configuration=j['configuration']['id'],verified=row['verified'],eligible=False,reason='missing_or_unverified_endpoint')
  if row['verified']:
   path=d/(j['id']+'.endpoint.json');e=read_json(path) if j['configuration']['backend']=='lp-quant-v1' else endpoint_shape(path,'compact-v1');trial=read_json(d/(j['id']+'.trial.json'));worker=read_json(d/(j['id']+'.worker.json')) if trial['artifacts']['worker'] else None;eligible=profile_eligible(e,v['profile_work'],row['verified'],trial,worker);o=e.get('outcome');c=e.get('control',{})
   entry.update(eligible=eligible,reason=None if eligible else 'incomplete_horizon',physical=o['physical'] if o else c.get('physical_iterations'),logical=o['iterations'] if o else c.get('logical_iterations'))
  profiles.append(entry)
 comparisons=[]
 for name in v['timing_instances']:
  for c in v['configurations'][:6]:
   for control in ['matched-fp64','tuned-fp64']:
    pairs=[(timings[(name,control,r)],timings[(name,c['id'],r)]) for r in range(3) if (name,control,r) in timings and (name,c['id'],r) in timings]
    comparisons.append(dict(instance=name,configuration=c['id'],control=control,pairs=len(pairs),uncertainty=None if not pairs else paired_ratios(pairs,seed=v['analysis']['seed'],resamples=v['analysis']['resamples'])))
 from lp_quant_review import verify as source_review
 source_review()
 return dict(source_review=dict(path='docs/benchmarks/data/quant/cpu-review-source.json',sha256=file_hash(ROOT/'docs/benchmarks/data/quant/cpu-review-source.json')),identity='gpup-quant-report-v1',source_tree_sha256=identity['source_tree_sha256'],cpu_admission=v['cpu_admission'],planned_attempts=104,attempts=sum(r['status'] not in ['unexecuted','cpu_admission_refusal'] for r in rows),verified=sum(r['verified'] for r in rows),certified_timings=sum(r['kind']=='timing' and r['certified'] for r in rows),profiles=profiles,comparisons=comparisons,rows=rows,categories_ns=charges,task_gpu_ns=sum(charges.values()),cumulative_gpu_ns=cumulative,ledger_events=len(events),ledger_sha256=file_hash(d/'ledger.jsonl'))
def main():
 from lp_quant_report_output import report_output
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args();output=report_output(a.output,kind='quant')
 r=report();write_json(output,r)
 lines=['# Bounded matrix quantization: GPUP-7','', 'Status: bounded research evaluation under accepted ADR-0040. No supported preset.','',f"Retained {r['attempts']} of {r['planned_attempts']} planned attempts; independently verified {r['verified']} endpoints and certified {r['certified_timings']}/96 timing cells.",'','| Configuration | Verified timings | Certified timings |','| --- | ---: | ---: |']
 for c in protocol()['configurations']:
  cells=[x for x in r['rows'] if x['kind']=='timing' and x['configuration']==c['id']];lines.append(f"| {c['id']} | {sum(x['verified'] for x in cells)} / 12 | {sum(x['certified'] for x in cells)} / 12 |")
 lines+=['','All candidates retain FP64 masters and fresh original-model host certification at','1e-9. Local 1e-7 product/audit budgets grant no final-accuracy authority.','Original-unit guards, metadata scans, host FP64 updates, transfers, audits and','sticky promotion/replay are included in fresh-process latency. Low work and','promoted masks remain explicit in the [machine-readable report](data/quant/report.json).','A solve that succeeds after native promotion is not evidence of a low-precision','convergence or throughput benefit. Initial host-only successes are also separate.','','The eight-model CPU admission and independent integer/Fraction format/product','oracle precede device execution; numerical refusals remain in','[CPU admission](data/quant/cpu-admission.json). Failed, interrupted and missing','endpoints remain unsuccessful timings. Partial profiles cannot enter comparisons.','All eight diagnostic cells remain visible. None reaches its complete requested',
 '2000 charged-update horizon: seven paths time out; tuned FP64 certifies early',
 'at 1400 updates. No full-horizon profile comparison follows. CPU-only reader',
 'review excludes incomplete horizons and CPU fallback from GPU timing claims,',
 'with unchanged numerical results and charges. The original report is retained.',
 'The fixed comparison includes uniform/selective binary16, CUDA E4M3/E5M2,','matched FP64 with the same conservative step/audits and unchanged tuned FP64.','','Full pinned-native, ordinary device, new product/controller differentials,','18 fixed-work endpoint/replay pairs and four scoped sanitizers precede the study.','Exact sources, executable/image identities, raw outputs and all outcomes are','retained under artifacts/gpup-quant-v1; historical evidence remains separate.','',f"Task GPU charge: {r['task_gpu_ns']/1e9:.9f} / 3600 seconds.",f"Cumulative charge: {r['cumulative_gpu_ns']/1e9:.9f} / 25202.574545061 seconds.",f"Ledger: {r['ledger_events']} events, SHA-256",r['ledger_sha256']+'.','', 'No vector FP16/FP8 quantization, Tensor Core or combined-policy conclusion follows.','GPUP-8 needs its own conditional admission contract; unused allowance reserves nothing.']
 markdown=report_output(output.with_suffix('.md'));markdown.write_text('\n'.join(lines)+'\n');print({k:r[k] for k in ['attempts','verified','certified_timings','task_gpu_ns','cumulative_gpu_ns','ledger_events','ledger_sha256']})
if __name__=='__main__':main()
