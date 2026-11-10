"""Independent CPU verification and strict completion gate for ADR-0043."""
import argparse,hashlib,json,tarfile,subprocess,statistics,random,concurrent.futures
from pathlib import Path
from collections import Counter
from lp_protocol import ROOT,read_json,write_json,file_hash,checked_reference,validate
from lp_tensor_residual_common import protocol,CONFIG,BASE,instances
from benchmark_lp_tensor_residual import jobs,effective,prepare_inputs,verify_endpoint,refs,micro_jobs
from benchmark_lp_adaptive_cost import endpoint_shape
from lp_tensor_residual_accept import check_acceptance
PREFIX='5af7782a384ac73226f339d98d0b33e320518053c1accdf67c1339db36d0e0f1'
def ledger(v,path):
 raw=path.read_bytes();lines=raw.splitlines(keepends=True)
 if not raw.endswith(b'\n') or hashlib.sha256(b''.join(lines[:17200])).hexdigest()!=PREFIX:raise ValueError('quant historical prefix differs')
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
 if pending or sum(phases.values())>min(v['cumulative_gpu_ns'],28800*10**9) or any(phases[k]>cap*10**9 for k,cap in v['phase_gpu_seconds'].items()) or any(charges[k]>cap['seconds']*10**9 for k,cap in v['categories'].items()) or sum(charges.values())>2665*10**9:raise ValueError('unsettled/exceeded resource contract')
 return events,dict(charges),sum(phases.values())
def archive(v,d):
 identity=read_json(d/'execution.json')
 if read_json(d/'campaign.json')!=v:raise ValueError('frozen campaign differs')
 for name,key in [('source.tar','source_archive_sha256'),('optimizer','binary_sha256'),('lp_precision_tensor_residual','exec_binary_sha256')]:
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


def profile_eligible(e,work,verified,trial,worker):
 return bool(verified and trial and trial['status']=='completed' and worker and worker['reason']=='completed' and worker['returncode']==0 and e.get('executor')=='gpu' and e['request']['diagnostic'] and e['request']['horizon']==work and e['outcome']['core']['iterations']==work and e['outcome']['core']['stop']=='work_horizon' and e['outcome']['core']['failure'] is None and e['outcome']['counts']['uncertain']==0)

def useful_tensor(e):
 if e.get('executor')!='gpu' or 'outcome' not in e:return False
 o=e['outcome'];c=o['counts'];return o['core']['stop']=='certified' and o['core']['failure'] is None and c['useful_windows']>0 and c['mma_instructions']>0 and c['accepted_nonzero_t']>0 and c['accepted_nonzero_f']>0

def worker_bounds(worker,reserved,device):
 for key in ['elapsed_ns','leased_ns','peak_rss_bytes','queue_ns']:
  if type(worker[key]) is not int or worker[key]<0:raise ValueError('worker physical counter type/range')
 if worker['elapsed_ns']>worker['leased_ns'] or worker['leased_ns']>reserved or worker['peak_rss_bytes']>8<<30 or worker['activity']['device']!=device:raise ValueError('worker physical accounting differs')


def gain(pairs,coverage_equal=True):
 if len(pairs)!=5 or not coverage_equal:return None
 if any(a<=0 or b<=0 for a,b in pairs):raise ValueError('invalid latency')
 rng=random.Random(17002);ratios=[]
 for _ in range(10000):
  sampled=[pairs[rng.randrange(5)] for _ in range(5)];ratios.append(statistics.median(a for a,b in sampled)/statistics.median(b for a,b in sampled))
 ratios.sort();tail=.05/6/2;lo=ratios[int(tail*len(ratios))];hi=ratios[min(len(ratios)-1,int((1-tail)*len(ratios)))];ratio=statistics.median(a for a,b in pairs)/statistics.median(b for a,b in pairs)
 return dict(speedup=ratio,interval=[lo,hi],confidence=1-.05/6,multiplicity=6,gain=lo>1)

def report_output(path):
 path=Path(path);allowed=[BASE.resolve(),(ROOT/'docs/benchmarks/data/tensor-residual').resolve()]
 if not any(path.parent.resolve().is_relative_to(root) for root in allowed) or path.is_symlink() or path.exists() and path.stat().st_nlink!=1:raise ValueError('protected report output')
 if path.exists():raise ValueError('report already exists; retain it and choose a new version')
 return path

def report():
 v=protocol();d=ROOT/v['output'];identity=archive(v,d);check_acceptance(v,identity);events,charges,cumulative=ledger(v,d/'ledger.jsonl');rows=[];timings={};profiles=[]
 admission=read_json(d/'cpu-admission.json');eligible={(r['model'],r['configuration']):r['eligible'] for r in admission['rows']}
 transactions={}
 for event in events:transactions.setdefault(event['trial_id'],[]).append(event)
 for j in jobs(v):
  key=j['id'];trial=read_json(d/(key+'.trial.json'));row=dict(id=key,model=j['instance']['id'],configuration=j['configuration']['id'],kind=j['kind'],repetition=j['repetition'],status=trial['status'],verified=False,certified=False)
  tx=transactions.get(key,[])
  if trial['status']=='cpu_admission_refusal':
   if eligible[(j['instance']['id'],j['configuration']['id'])] or tx or (d/(key+'.endpoint.json')).exists() or (d/(key+'.worker.json')).exists():raise ValueError('refusal identity has execution or was eligible')
  else:
   expected,docs=prepare_inputs(v,j,d,identity)
   if read_json(d/(key+'.request.json'))!=expected or any(read_json(d/name)!=doc for name,doc in docs.items()):raise ValueError('frozen worker request differs')
   worker_doc=read_json(d/(key+'.worker.json'));worker_bounds(worker_doc,tx[0]['reserved_ns'] if tx else 0,v['device'])
   if len(tx)!=2 or tx[0]['reserved_ns']!=(effective(v,j)[2]+6)*10**9 or tx[1]['charged_ns']!=trial['charged_ns'] or trial['charged_ns']!=worker_doc['leased_ns'] or worker_doc['activity']['device']!=v['device'] or trial['source_tree_sha256']!=identity['source_tree_sha256']:raise ValueError('trial/worker ledger binding differs')
  ep=d/(key+'.endpoint.json');worker=read_json(d/(key+'.worker.json')) if (d/(key+'.worker.json')).exists() else None
  if ep.exists():
   assessment=verify_endpoint(v,j,d,identity);raw=read_json(ep);e=raw if 'outcome' in raw else endpoint_shape(ep,'compact-v1');row['verified']=True
   complete=trial['status']=='completed' and worker is not None and worker['reason']=='completed' and worker['returncode']==0
   numerical=(e['executor']=='gpu' and e['outcome']['core']['stop']=='certified' and e['outcome']['core']['failure'] is None) if 'outcome' in e else e['record']['backend']=='cuda-lp-tuned' and e['record']['termination']=='optimal'
   row['certified']=bool(j['kind']=='timing' and complete and assessment['gap_closed'] and numerical)
   if j['configuration']['id'] in ['int8-tensor','fp16-tensor','bf16-tensor'] and not useful_tensor(e):row['certified']=False
   if row['certified']:
    seconds=worker['elapsed_ns']/1e9;row['seconds']=seconds;timings[(row['model'],row['configuration'],j['repetition'])]=seconds
   if 'outcome' in e:
    row['useful_windows']=e['outcome']['counts']['useful_windows'];row['mma_instructions']=e['outcome']['counts']['mma_instructions']
    if j['kind']=='profile':row['profile_complete']=profile_eligible(e,2000,True,trial,worker);profiles.append(row)
  rows.append(row)
 comparisons=[]
 for c in v['configurations'][:3]:
  coverage_equal=all(sum((n,c['id'],r) in timings for r in range(5))>=sum((n,'tuned-fp64',r) in timings for r in range(5)) for n in v['timing_instances'])
  for n in v['timing_instances']:
   pairs=[(timings[(n,'tuned-fp64',r)],timings[(n,c['id'],r)]) for r in range(5) if (n,'tuned-fp64',r) in timings and (n,c['id'],r) in timings]
   comparisons.append(dict(model=n,configuration=c['id'],paired=len(pairs),coverage_equal=coverage_equal,result=gain(pairs,coverage_equal)))
 cpu=[];cpu_cohorts=[];cpu_tasks=[]
 for cohort in ['cpu-admission']:
  directory=BASE/cohort;admission=read_json(directory/'admission.json');binary=directory/'lp_precision_tensor_residual'
  if file_hash(binary)!=admission['executable_sha256']:raise ValueError('CPU binary binding')
  archive_path=checked_reference(ROOT,admission['source_archive']);digest=hashlib.sha256()
  with tarfile.open(archive_path) as source:
   members=source.getmembers();names=[m.name for m in members]
   if names!=sorted(set(names)) or any(not m.isfile() or Path(m.name).is_absolute() or '..' in Path(m.name).parts for m in members):raise ValueError('CPU source layout')
   for m in members:digest.update(m.name.encode()+b'\0'+source.extractfile(m).read()+b'\0')
  if digest.hexdigest()!=admission['source_tree_sha256']:raise ValueError('CPU source identity')
  present=[r for r in admission['rows'] if 'endpoint' in r]
  cpu_cohorts.append(dict(cohort=cohort,verified=len(present),source_tree_sha256=admission['source_tree_sha256'],executable_sha256=admission['executable_sha256'],image_sha256=admission['image_sha256'],source_archive=admission['source_archive']))
  for row in present:cpu_tasks.append((binary,row))
 def verify_cpu(task):
  binary,row=task;ep=checked_reference(ROOT,row['endpoint']);rp=ep.parent/'request.json';model=checked_reference(ROOT,instances(v)[row['model']]['model'])
  for verifier in [binary,d/'lp_precision_tensor_residual']:
   r=subprocess.run([str(verifier),'verify',str(model),str(rp),str(ep)],capture_output=True,text=True,timeout=120)
   if r.returncode or r.stdout.strip()!='verified':raise ValueError('retained CPU endpoint rejected '+r.stderr[:1000])
  return row['endpoint']
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:cpu=list(pool.map(verify_cpu,cpu_tasks))
 acceptance=read_json(ROOT/v['acceptance_output']/'project/acceptance.json');acceptance_endpoints=[]
 for row in acceptance['rows']:
  if row['status']!='passed':continue
  ep=checked_reference(ROOT,row['endpoint']);rp=ep.parent/(row['instance']+'-'+row['configuration']+'.request.json');model=checked_reference(ROOT,instances(v)[row['instance']]['model'])
  for kind in ['endpoint','replay']:
   endpoint=checked_reference(ROOT,row[kind]);r=subprocess.run([str(d/'lp_precision_tensor_residual'),'verify',str(model),str(rp),str(endpoint)],capture_output=True,text=True,timeout=120)
   if r.returncode or r.stdout.strip()!='verified':raise ValueError('retained device acceptance endpoint rejected '+r.stderr[:1000])
   acceptance_endpoints.append(row[kind])
 diagnostics=[];test=checked_reference(ROOT,read_json(d/'acceptance-binaries.json')['tensor-residual'])
 for job in micro_jobs(v):
  key=job['id'];trial=read_json(d/(key+'.trial.json'));worker=read_json(d/(key+'.worker.json'));request=read_json(d/(key+'.request.json'));tx=transactions.get(key,[])
  expected=['/usr/bin/env','AI_OPTIMIZER_CUDA_DIR='+str(d),'AI_OPTIMIZER_GPU=1',str(test),'tensor_products_match_exact_cpu_in_both_orientations','--nocapture','--test-threads','1']
  if request['command']!=expected or len(tx)!=2 or tx[0]['reserved_ns']!=35*10**9 or tx[1]['charged_ns']!=trial['charged_ns'] or trial['charged_ns']!=worker['leased_ns']:raise ValueError('diagnostic binding differs')
  worker_bounds(worker,tx[0]['reserved_ns'],v['device']);text=(d/(key+'.stdout')).read_text()+(d/(key+'.stderr')).read_text()
  if trial['status']!='completed' or worker['reason']!='completed' or worker['returncode']!=0 or '280 independent CPU/device pairs' not in text or '1 passed; 0 failed' not in text or 'SKIP ' in text:raise ValueError('diagnostic receipt incomplete')
  diagnostics.append(trial)

 useful={r['configuration'] for r in rows if r['certified'] and r.get('useful_windows',0)>0 and r.get('mma_instructions',0)>0}
 working='int8-tensor' in useful and bool(useful&{'fp16-tensor','bf16-tensor'});winning=any(c['result'] and c['result']['gain'] for c in comparisons)
 return dict(identity='gpup-tensor-residual-report-v1',status='complete' if working and winning else 'incomplete',working_families=working,certified_latency_gain=winning,planned_study_cells=75,rows=rows,comparisons=comparisons,profiles=profiles,cpu_verified=len(cpu),cpu_cohorts=cpu_cohorts,acceptance_verified=len(acceptance_endpoints),acceptance_endpoints=acceptance_endpoints,verified=sum(r['verified'] for r in rows),certified_timings=sum(r['certified'] for r in rows),cpu_admission_refusals=sum(r['status']=='cpu_admission_refusal' for r in rows),micro=diagnostics,source_tree_sha256=identity['source_tree_sha256'],task_gpu_ns=sum(charges.values()),categories_ns=charges,cumulative_gpu_ns=cumulative,ledger_events=len(events),ledger_sha256=file_hash(d/'ledger.jsonl'))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=BASE/'report.json');a=p.parse_args();out=report_output(a.output);result=report();out.parent.mkdir(parents=True,exist_ok=True)
 with out.open('x') as stream:json.dump(result,stream,sort_keys=True,indent=2);stream.write('\n')
 print({k:v for k,v in result.items() if k not in ['rows','comparisons','profiles','micro']})
