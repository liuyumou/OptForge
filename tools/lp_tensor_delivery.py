"""CPU-only final acceptance, preserved-source and resource receipt for GPUP-8."""
import hashlib,json,tarfile
from pathlib import Path
from lp_protocol import ROOT,read_json,write_json,file_hash,checked_reference
from lp_tensor_common import BASE,protocol,numeric_sources
from benchmark_lp import reference

def main():
 v=protocol();d=ROOT/v['output'];r=read_json(BASE/'report.json')
 if read_json(ROOT/'docs/benchmarks/data/tensor/report.json')!=r:raise ValueError('report copy differs')
 identity=read_json(d/'execution.json');cpu=read_json(d/'cpu-admission.json')
 if numeric_sources()!=cpu['numerical_sources']:raise ValueError('measured numerical sources changed')
 if len(r['rows'])!=72 or len(r['micro'])!=3 or r['cpu_verified']!=96 or r['acceptance_verified']!=8 or r['verified']!=24 or r['certified_timings']!=20 or r['cpu_admission_refusals']!=48:raise ValueError('verification coverage differs')
 if r['status']!='incomplete' or r['working_families'] or r['certified_latency_gain']:raise ValueError('unmet completion gates were promoted')
 raw=(ROOT/'artifacts/lp-campaign-ledgers/gpup-baseline-v1/ledger.jsonl').read_bytes()
 if hashlib.sha256(raw).hexdigest()!=r['ledger_sha256'] or hashlib.sha256(b''.join(raw.splitlines(keepends=True)[:17132])).hexdigest()!=v['prior_ledger_sha256'] or len(raw.splitlines())!=r['ledger_events']:raise ValueError('ledger changed after independent verification')
 final=read_json(BASE/'final-native-resources.json')
 if final['returncode'] or final['reason']!='completed' or final['source_before']!=final['source_after']:raise ValueError('final native gate incomplete or source unstable')
 resource_rows=[];total=0.;peak=0
 for path in sorted(BASE.glob('*resources.json')):
  row=read_json(path);total+=row['cpu_seconds'];peak=max(peak,row['peak_process_tree_rss_bytes']);resource_rows.append(reference(ROOT,path))
 upper=total+6000+1000
 artifact_bytes=sum(p.stat().st_size for p in BASE.rglob('*') if p.is_file())
 if upper>21600 or peak>8<<30 or artifact_bytes>32<<30:raise ValueError('task CPU/RSS/artifact resource bound exceeded')
 # Bind every measured cohort and retained failure; the inventory excludes
 # this derived receipt and final gate logs that were still open while measured.
 measured=['cpu-admission','accepted-admission','final-admission','device-fix-admission','study','study-v2','study-v3','acceptance','acceptance-v2','proofs','initial-proof','proof-before-device-fix']
 files={str(p.relative_to(ROOT)):file_hash(p) for name in measured for p in sorted((BASE/name).rglob('*')) if p.is_file()}
 inventory=BASE/'retained-inventory.json';write_json(inventory,dict(identity='gpup-tensor-retained-inventory-v1',files=files))
 old=ROOT/'artifacts/gpup-tensor-v1/acceptance/gpup-tensor-v1-accept-project-v1.worker.json';failure=read_json(old)
 result=dict(identity='gpup-tensor-delivery-v1',acceptance_status='passed',task_status='incomplete',completion_unmet=['useful_tensor_certified_nontrivial_solve','certified_total_latency_gain'],gpu_verification_seconds=0,task_gpu_ns=r['task_gpu_ns'],cumulative_gpu_ns=r['cumulative_gpu_ns'],ledger_events=r['ledger_events'],ledger_sha256=r['ledger_sha256'],historical_prefix_events=17132,historical_prefix_sha256=v['prior_ledger_sha256'],report=reference(ROOT,ROOT/'docs/benchmarks/data/tensor/report.json'),measured_source_tree_sha256=identity['source_tree_sha256'],native_gate_source_tree_sha256=final['source_after'],numerical_sources_identical=True,lp_records_verified=128,cpu_cohorts=r['cpu_cohorts'],study_verified=24,acceptance_replay_verified=8,cpu_verified=96,failed_device_gate=reference(ROOT,old),failed_device_gate_gpu_ns=failure['leased_ns'],native_acceptance=reference(ROOT,BASE/'final-native-resources.json'),retained_inventory=reference(ROOT,inventory),resource_receipts=resource_rows,measured_cpu_seconds=total,preparation_coordination_allowance_seconds=6000,delivery_cpu_reserve_seconds=1000,accounted_cpu_upper_seconds=upper,cpu_cap_seconds=21600,peak_process_tree_rss_bytes=peak,artifact_bytes=artifact_bytes,artifact_cap_bytes=32<<30)
 write_json(ROOT/'docs/benchmarks/data/tensor/acceptance.json',result);print({k:result[k] for k in ['acceptance_status','task_status','lp_records_verified','task_gpu_ns','accounted_cpu_upper_seconds','artifact_bytes']})
if __name__=='__main__':main()
