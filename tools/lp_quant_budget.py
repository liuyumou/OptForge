"""ADR-0040 chained resource authority. Every historical ledger byte remains exact."""
import argparse,hashlib,json,subprocess,shutil
from pathlib import Path
from lp_protocol import ROOT,read_json,write_json,file_hash,checked_reference
from lp_copt_budget import ComparisonLedger,receipt
CONFIG=ROOT/'benchmarks/configs/lp-quant-v1.json'
PREFIX='dd5d7281a152d8fb56df373d913ac2dc7077aac9cf6ba2eb5f6e7781493ea52c'
def protocol(path=CONFIG):
 v=read_json(path)
 from validate_artifacts import validator
 validator("lp-quant-study-v1.schema.json").validate(v)
 if (v['id'],v['combined_cap_seconds'],v['additional_gpu_seconds'],v['cumulative_gpu_ns'],v['prior_events'],v['prior_gpu_ns'],v['prior_ledger_sha256'])!=('gpup-quant-v1',3600,3600,25202574545061,16816,19730939812844,PREFIX):raise ValueError('quant authority differs')
 if v['categories']!=dict(timing=dict(phase='screening',seconds=2300),profile=dict(phase='ablations',seconds=450),accept=dict(phase='repeatability',seconds=850)):raise ValueError('quant category authority differs')
 if v['phase_gpu_seconds']!=dict(baseline=1800,screening=11800,ablations=8100,repeatability=5300,finalists=9000) or v['total_gpu_seconds']!=28800:raise ValueError('quant phase authority differs')
 for r in [v['decision'],v['previous_protocol'],v['budget_authority'],v['cpu_admission'],v['cpu_source_bridge'],v['cpu_resource_bound'],*v['manifests']]:checked_reference(ROOT,r)
 a=read_json(checked_reference(ROOT,v['cpu_admission']))
 if a['status']!='passed' or a['gpu_seconds']!=0 or len(a['rows'])!=56:raise ValueError('quant CPU admission required')
 from lp_quant_cpu_bridge import verify
 verify()
 return v
def ledger_for(v,root=ROOT):
 if v!=protocol():raise ValueError('quant public authority differs')
 from lp_assess_budget import ledger_for as parent_ledger,protocol as parent_protocol
 old=parent_ledger(parent_protocol(),root);raw=old.path.read_bytes();prefix=b''.join(raw.splitlines(keepends=True)[:16816])
 if len(prefix.splitlines())!=16816 or hashlib.sha256(prefix).hexdigest()!=PREFIX or sum(json.loads(x)['charged_ns'] for x in prefix.splitlines() if json.loads(x)['resource']=='gpu')!=19730939812844:raise ValueError('quant historical prefix differs')
 return ComparisonLedger(old.path.parent,old.campaign_hash,v)
def validate_command(gate,command):
 if gate=='regular':valid=len(command)==5 and command[:2]==['bash',str(ROOT/'tools/lp_exec_regular_check.sh')] and len(set(command[2:]))==3 and all(Path(x).name.startswith('device-') for x in command[2:])
 elif gate=='project':valid=command==['python3',str(ROOT/'tools/lp_quant_accept.py')]
 else:valid=len(command)==4 and command[:2]==['bash',str(ROOT/'tools/lp_quant_gpu_check.sh')] and Path(command[2]).name.startswith('quant_device-') and command[3]==gate
 if not valid:raise ValueError('quant gate/command mismatch')
def main():
 p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--gate',required=True,choices=['regular','project','memcheck','racecheck','initcheck','synccheck']);p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args();command=a.command[1:] if a.command[:1]==['--'] else a.command
 seconds=180 if a.gate=='regular' else 240 if a.gate=='project' else 90
 validate_command(a.gate,command)
 v=protocol();from benchmark_lp_quant import freeze
 frozen,identity=freeze(v);directory=ROOT/v['acceptance_output'];directory.mkdir(parents=True,exist_ok=True)
 bound=[]
 for arg in command:
  path=Path(arg)
  if path.is_file() and path.open('rb').read(4)==b'\x7fELF':
   dest=frozen/(path.name+'-'+file_hash(path)[:16]);shutil.copy2(path,dest) if not dest.exists() else None
   if file_hash(dest)!=file_hash(path):raise ValueError('frozen acceptance binary differs')
   bound.append(str(dest))
  else:bound.append(arg)
 key=v['id']+'-accept-'+a.id
 with ledger_for(v) as ledger:
  if key in ledger.attempted():raise ValueError('acceptance cannot retry')
  request=dict(schema_version=2,gpu_admission_seconds=3,command=['/usr/bin/env','AI_OPTIMIZER_CUDA_DIR='+str(frozen),*bound],directory=str(directory),prefix=key,solve_seconds=seconds,cleanup_seconds=2,host_rss_bytes=8589934592,poll_ms=10,output_bytes=33554432)
  path=directory/(key+'.request.json')
  if path.exists():raise ValueError('acceptance request exists')
  write_json(path,request);write_json(directory/(key+'.source.json'),dict(source_tree_sha256=identity['source_tree_sha256'],request_sha256=file_hash(path),gate=a.gate,command=bound))
  reservation=ledger.reserve(key,seconds+6,phase='repeatability')
  child=subprocess.Popen(['bash',str(ROOT/'tools/gpu_job.sh'),v['device'],'--lp-study-request',str(path)],pass_fds=(ledger.lock.fileno(),))
  try:child.wait(timeout=seconds+310)
  finally:
   if child.poll() is None:
    child.terminate()
    try:child.wait(timeout=3)
    except subprocess.TimeoutExpired:child.kill();child.wait()
   info=read_json(directory/(key+'.worker.json')) if (directory/(key+'.worker.json')).exists() else None
   ledger.settle(reservation,info['leased_ns'] if info else reservation['reserved_ns']);write_json(directory/'budget.json',receipt(ledger));shutil.copy2(ledger.path,frozen/'ledger.jsonl')
  if child.returncode or info is None or info['reason']!='completed' or info['returncode']!=0:raise ValueError('acceptance failed; no retry')
if __name__=='__main__':main()
