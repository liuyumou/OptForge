"""CPU-only delivery receipt; keep task completion distinct from software gates."""
import argparse
import hashlib
from pathlib import Path
from benchmark_lp import reference
from lp_protocol import ROOT,read_json,write_json,file_hash,checked_reference
from lp_tensor_residual_common import BASE,protocol,numeric_sources

def main():
 p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');args=p.parse_args()
 v=protocol();r=read_json(BASE/'report.json');old=read_json(ROOT/'docs/benchmarks/data/tensor/acceptance.json')
 if read_json(ROOT/'docs/benchmarks/data/tensor-residual/report.json')!=r:raise ValueError('separate report copy differs')
 if (r['certified_timings'],r['verified'],r['cpu_verified'],r['acceptance_verified'],len(r['profiles']),len(r['micro']))!=(60,72,24,24,12,3):raise ValueError('endpoint coverage differs')
 if r['status']!='incomplete' or not r['working_families'] or r['certified_latency_gain']:raise ValueError('completion gates differ')
 if any(c['paired']!=5 or not c['coverage_equal'] or c['result'] is None or c['result']['interval'][1]>=1 for c in r['comparisons']):raise ValueError('gain comparisons differ')
 d=ROOT/v['output'];cpu=read_json(d/'cpu-admission.json')
 if numeric_sources()!=cpu['numerical_sources']:raise ValueError('measured numerical sources changed')
 tensor=[]
 for row in r['rows']:
  if row['kind']!='timing' or row['configuration'] not in ['int8-tensor','fp16-tensor','bf16-tensor']:continue
  e=read_json(d/(row['id']+'.endpoint.json'));o=e['outcome']
  if o['core']['stop']!='certified' or o['core']['iterations']!=2200 or o['core']['promotion']['native'] or o['counts']['useful_windows']!=66:raise ValueError('useful Tensor solve differs')
  tensor.append(row['id'])
 if len(tensor)!=30 or any(not row['profile_complete'] for row in r['profiles']):raise ValueError('Tensor/profile horizon coverage differs')
 ledger=ROOT/'artifacts/lp-campaign-ledgers/gpup-baseline-v1/ledger.jsonl';raw=ledger.read_bytes();lines=raw.splitlines(keepends=True)
 if len(lines)!=r['ledger_events'] or file_hash(ledger)!=r['ledger_sha256']:raise ValueError('final ledger differs')
 for n,want in [(17200,v['prior_ledger_sha256']),(17132,old['historical_prefix_sha256'])]:
  if hashlib.sha256(b''.join(lines[:n])).hexdigest()!=want:raise ValueError('historical ledger prefix differs')
 combined=r['task_gpu_ns']+old['task_gpu_ns']
 if combined>3000*10**9:raise ValueError('original task allocation exceeded')
 previous=read_json(ROOT/'docs/benchmarks/data/tensor/report.json')
 for c,cap in [('timing',1600),('profile',550),('accept',850)]:
  if r['categories_ns'][c]+previous['categories_ns'][c]>cap*10**9:raise ValueError('original task phase allocation exceeded')
 preservation=read_json(BASE/'historical-preservation.json')
 if preservation['status']!='passed' or preservation['verified_historical_files']!=1272:raise ValueError('historical inventory proof missing')
 result=dict(identity='gpup-tensor-residual-delivery-v1',software_acceptance_status='pending_final_native_gate',task_status='incomplete',completion_unmet=['certified_total_latency_gain','initial_cpu_concurrency_not_certified'],resource_acceptance_status='initial_cpu_concurrency_not_certified',cpu_concurrency_limitation=reference(ROOT,ROOT/'docs/benchmarks/data/tensor-residual/cpu-concurrency-limitation.json'),working_families=True,certified_latency_gain=False,gpu_verification_seconds=0,continuation_gpu_ns=r['task_gpu_ns'],combined_gpup8_gpu_ns=combined,cumulative_gpu_ns=r['cumulative_gpu_ns'],categories_ns=r['categories_ns'],ledger_events=r['ledger_events'],ledger_sha256=r['ledger_sha256'],historical_prefix_events=17200,historical_prefix_sha256=v['prior_ledger_sha256'],lp_records_verified=120,cpu_records_verified=24,study_records_verified=72,acceptance_replay_records_verified=24,certified_timings=60,useful_tensor_timings=30,complete_profiles=12,report=reference(ROOT,ROOT/'docs/benchmarks/data/tensor-residual/report.json'),historical_preservation=reference(ROOT,BASE/'historical-preservation.json'),measured_source_tree_sha256=r['source_tree_sha256'],numerical_sources_identical=True)
 if not args.prepare:
  final=read_json(BASE/'final-native-v2-resources.json')
  if final['returncode'] or final['reason']!='completed' or final['source_before']!=final['source_after']:raise ValueError('final native gate incomplete/source unstable')
  history=read_json(BASE/'historical-reverification.json')
  if history['status']!='passed' or history['lp_records_verified']!=128 or not history['unchanged_report']:raise ValueError('historical endpoint re-verification missing')
  rows=[];measured=0.;peak=0
  for path in sorted(BASE.glob('*resources.json')):
   row=read_json(path);measured+=row['cpu_seconds'];peak=max(peak,row['peak_process_tree_rss_bytes']);rows.append(reference(ROOT,path))
  # Single-threaded CPU admission traces dominate their one host verification.
  # Two trace wall windows plus 600 seconds cover raw preparation, compilation,
  # exact oracles, portability, admission verification and coordination.
  trace_wall=sum(read_json(p)['phases_ns']['execute_total']/1e9 for p in (BASE/'cpu-admission').glob('*/endpoint.json'))
  preparation_upper=2*trace_wall+600
  # Conservatively account eight CPU-seconds per leased wall second, including
  # worker/driver/watchdog activity and unmonitored solve coordination/checks.
  worker_upper=8*r['task_gpu_ns']/1e9
  upper=measured+preparation_upper+worker_upper+500
  artifact_bytes=sum(p.stat().st_size for p in BASE.rglob('*') if p.is_file())
  combined_artifacts=artifact_bytes+old['artifact_bytes']
  if upper>10000 or upper+old['accounted_cpu_upper_seconds']>21600 or peak>8<<30 or combined_artifacts>32<<30:raise ValueError('CPU/RSS/artifact cap exceeded')
  portability=read_json(BASE/'source-only-portability-final.json')
  if portability['status']!='passed' or portability['passed_tests']!=39 or not portability['study_artifacts_absent'] or not portability['native_dependencies_absent']:raise ValueError('source-only portability missing')
  files={str(p.relative_to(ROOT)):file_hash(p) for name in ['cpu-admission','study-v1','acceptance-v1','proofs','build'] for p in sorted((BASE/name).rglob('*')) if p.is_file()}
  inventory=BASE/'retained-inventory.json';write_json(inventory,dict(identity='gpup-tensor-residual-retained-inventory-v1',files=files))
  result.update(software_acceptance_status='passed',historical_lp_records_freshly_verified=128,total_gpup8_lp_records_verified=248,historical_reverification=reference(ROOT,BASE/'historical-reverification.json'),native_acceptance=reference(ROOT,BASE/'final-native-v2-resources.json'),native_gate_source_tree_sha256=final['source_after'],resource_receipts=rows,measured_cpu_seconds=measured,cpu_trace_wall_seconds=trace_wall,preparation_coordination_upper_seconds=preparation_upper,worker_coordination_cpu_upper_seconds=worker_upper,delivery_cpu_reserve_seconds=500,accounted_cpu_upper_seconds=upper,combined_gpup8_cpu_upper_seconds=upper+old['accounted_cpu_upper_seconds'],cpu_cap_seconds=10000,combined_cpu_cap_seconds=21600,monitored_peak_process_tree_rss_bytes=peak,rss_sampling_scope='monitored jobs; aggregate initial admission/build overlap not sampled',artifact_bytes=artifact_bytes,combined_gpup8_artifact_bytes=combined_artifacts,artifact_cap_bytes=32<<30,source_only_portability=reference(ROOT,BASE/'source-only-portability-final.json'),retained_inventory=reference(ROOT,inventory))
 write_json(ROOT/'docs/benchmarks/data/tensor-residual/acceptance.json',result)
 print({k:result[k] for k in ['software_acceptance_status','task_status','lp_records_verified','continuation_gpu_ns','combined_gpup8_gpu_ns']})
if __name__=='__main__':main()
