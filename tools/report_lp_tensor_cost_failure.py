"""CPU-only disposition of the retained ADR-0044 device correctness stop."""
import ast
import concurrent.futures
import hashlib
import json
import math
import re
import struct
import subprocess
from pathlib import Path

from lp_protocol import ROOT,read_json,checked_reference,file_hash,write_json
from lp_tensor_cost_common import protocol,instances
from benchmark_lp_tensor_cost import jobs,prepare_inputs
from lp_tensor_cost_accept import acceptance_jobs,acceptance_request
from report_lp_tensor_cost import archive,ledger,worker_bounds

def has_skip(text):
 return re.search(r'^\s*SKIP(?:\s|:)',text,re.MULTILINE) is not None

def ordered_bits(value):
 if not math.isfinite(value):raise ValueError('nonfinite comparison witness')
 bits=struct.unpack('>Q',struct.pack('>d',value))[0]
 return (~bits)&((1<<64)-1) if bits>>63 else bits|(1<<63)

def vector_differences(text):
 left,right=text.split('left: Outcome',1)[1].split('right: Outcome',1)
 rows=[]
 for name in ['primal','dual','scaled_primal','scaled_dual']:
  pattern=r'(?<![A-Za-z_])'+name+r': (\[[^\]]*\])'
  a=ast.literal_eval(re.search(pattern,left).group(1));b=ast.literal_eval(re.search(pattern,right).group(1))
  if len(a)!=len(b) or not a:raise ValueError('incomplete controller witness')
  rows.append(dict(vector=name,components=len(a),different=sum(ordered_bits(x)!=ordered_bits(y) for x,y in zip(a,b)),maximum_ulp_distance=max(abs(ordered_bits(x)-ordered_bits(y)) for x,y in zip(a,b)),maximum_absolute_difference=max(abs(x-y) for x,y in zip(a,b))))
 if not any(row['different'] for row in rows):raise ValueError('missing endpoint difference')
 return rows

def main():
 v=protocol();d=ROOT/v['output'];identity=archive(v,d)
 events,charges,cumulative=ledger(v,d/'ledger.jsonl');transactions={}
 for event in events:transactions.setdefault(event['trial_id'],[]).append(event)
 if read_json(d/'roster.json')!=list(jobs(v)):raise ValueError('frozen roster changed')
 study=[]
 for job in jobs(v):
  key=job['id'];expected,docs=prepare_inputs(v,job,d,identity)
  if read_json(d/(key+'.frozen.json'))!=expected or any(read_json(d/name)!=doc for name,doc in docs.items()):raise ValueError('prospective request changed')
  if transactions.get(key) or any((d/(key+suffix)).exists() for suffix in ['.request.json','.worker.json','.endpoint.json','.trial.json']):raise ValueError('unexpected study execution')
  study.append(dict(id=key,status='not_executed_device_correctness_failure'))
 acceptance=[];out=ROOT/v['acceptance_output']
 for gate,seconds in acceptance_jobs():
  key=v['id']+'-accept-'+gate;expected=acceptance_request(v,d,gate,seconds);tx=transactions.get(key,[])
  if read_json(d/(key+'.frozen.json'))!=expected:raise ValueError('frozen acceptance request changed')
  wp=out/(key+'.worker.json')
  if not wp.exists():
   if tx or (out/(key+'.request.json')).exists():raise ValueError('missing attempted acceptance worker')
   acceptance.append(dict(gate=gate,status='not_executed'));continue
  worker=read_json(wp);request=read_json(out/(key+'.request.json'));source=read_json(out/(key+'.source.json'))
  if request!=expected or source['request_sha256']!=file_hash(out/(key+'.request.json')) or source['source_tree_sha256']!=identity['source_tree_sha256'] or source['command']!=request['command'][2:]:raise ValueError('acceptance source binding')
  if len(tx)!=2 or tx[0]['reserved_ns']!=(seconds+6)*10**9 or tx[1]['charged_ns']!=worker['leased_ns']:raise ValueError('acceptance ledger binding')
  worker_bounds(worker,tx[0]['reserved_ns'],v['device'])
  if type(worker['returncode']) is not int:raise ValueError('invalid return code')
  text=(out/(key+'.stdout')).read_text()+(out/(key+'.stderr')).read_text()
  if has_skip(text):raise ValueError('skipped device acceptance')
  passed=worker['reason']=='completed' and worker['returncode']==0
  if gate=='regular' and (not passed or re.findall(r'test result: ok\. (\d+) passed; 0 failed;',text)!=['14','6','46']):raise ValueError('ordinary acceptance incomplete')
  if gate=='project' and (passed or '280 independent CPU/device pairs' not in text or 'tensor_controller_windows_match_cpu_and_charge_physical_work ... FAILED' not in text):raise ValueError('project stop does not match retained failure')
  acceptance.append(dict(gate=gate,status='passed' if passed else 'failed',leased_ns=worker['leased_ns'],returncode=worker['returncode']))
 if [row['gate'] for row in acceptance if row['status']=='failed']!=['project']:raise ValueError('unexpected gate disposition')
 cpu_tasks=[];cohorts=[]
 for cohort in ['cpu-admission','cpu-admission-v2']:
  directory=d.parent/cohort;admission=read_json(directory/'admission.json');binary=directory/'lp_precision_tensor_cost'
  if file_hash(binary)!=admission['executable_sha256']:raise ValueError('CPU executable changed')
  checked_reference(ROOT,admission['source_archive'])
  rows=[r for r in admission['rows'] if 'endpoint' in r]
  cohorts.append(dict(cohort=cohort,records=len(rows),source_tree_sha256=admission['source_tree_sha256']))
  cpu_tasks.extend((binary,row) for row in rows)
 models=instances(v)
 def verify(task):
  binary,row=task;ep=checked_reference(ROOT,row['endpoint']);rp=ep.parent/'request.json';model=checked_reference(ROOT,models[row['model']]['model'])
  for verifier in [binary,d/'lp_precision_tensor_cost']:
   command=['python3',str(ROOT/'tools/lp_tensor_cost_exec.py'),'--memory-bytes',str(1<<30),'--',str(verifier),'verify',str(model),str(rp),str(ep)]
   result=subprocess.run(command,capture_output=True,text=True,timeout=20)
   if result.returncode or result.stdout.strip()!='verified':raise ValueError('CPU endpoint verification failed: '+result.stderr[:1000])
  return row['endpoint']
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:verified=list(pool.map(verify,cpu_tasks))
 differences=vector_differences((out/'project/tensor.stderr').read_text())
 if 825114032275+sum(charges.values())>3000000000000:raise ValueError('GPUP-8 total ceiling exceeded')
 result=dict(identity='gpup-tensor-cost-device-refusal-report-v1',status='incomplete',reason='device_reference_reduction_order_mismatch',working_certified_tensor_families=False,certified_latency_gain=False,source_tree_sha256=identity['source_tree_sha256'],posthoc_reader_sha256=file_hash(Path(__file__)),acceptance=acceptance,study=study,planned_study_cells=76,executed_study_cells=0,certified_timings=0,profiles_executed=0,fixed_work_replay_pairs=0,product_pairs_passed=280,controller_case='Int8 at 64 logical updates / 66 physical updates / two audits',controller_vector_differences=differences,cpu_cohorts=cohorts,cpu_verified=len(verified),cpu_endpoints=verified,task_gpu_ns=sum(charges.values()),categories_ns=charges,gpup8_gpu_ns=825114032275+sum(charges.values()),gpup8_cap_ns=3000000000000,cumulative_gpu_ns=cumulative,cumulative_gpu_cap_ns=v['cumulative_gpu_ns'],ledger_events=len(events),ledger_sha256=file_hash(d/'ledger.jsonl'),historical_prefix_events=17362,historical_prefix_sha256=v['prior_ledger_sha256'],numerical_and_latency_criteria_changed=False,host_access=False,bootstrap_rerun=False,study_retry=False)
 dest=d.parent/'post-device-delivery/report-v1.json'
 if dest.exists():raise ValueError('immutable report already exists')
 write_json(dest,result)
 print(json.dumps({key:value for key,value in result.items() if key not in ['study','cpu_endpoints']},sort_keys=True))
 host=(ROOT/'crates/optimizer-lp/src/precision.rs').read_text().splitlines()
 for i,line in enumerate(host):
  if 'fn product(' in line:print('HOST_PRODUCT','\n'.join(str(k+1)+': '+host[k] for k in range(i,min(len(host),i+65))))

if __name__=='__main__':main()
