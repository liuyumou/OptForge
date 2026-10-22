"""ADR-0041 allocation inside unchanged authority; exact historical prefix preserved."""
import argparse,hashlib,subprocess,shutil
from pathlib import Path
from lp_protocol import ROOT,read_json,write_json,file_hash,checked_reference
from lp_copt_budget import ComparisonLedger,receipt
from lp_quant_resident_common import numeric_sources
CONFIG=ROOT/'benchmarks/configs/lp-quant-resident-v1.json'
PREFIX='861c90d8d82a20ff9655173742db37a5047d315e8cc4c983e0d6b2e6fa09bb97'
def protocol(path=CONFIG):
 v=read_json(path)
 from validate_artifacts import validator
 validator('lp-quant-resident-study-v1.schema.json').validate(v)
 if (v['id'],v['combined_cap_seconds'],v['allocated_gpu_seconds'],v['additional_gpu_seconds'],v['cumulative_gpu_ns'],v['prior_events'],v['prior_gpu_ns'],v['prior_ledger_sha256'])!=('gpup-quant-resident-v1',3600,3600,0,25202574545061,17036,21113899268966,PREFIX):raise ValueError('resident allocation differs')
 parent=read_json(checked_reference(ROOT,v['previous_protocol']))
 if v['cumulative_gpu_ns']!=parent['cumulative_gpu_ns'] or v['phase_gpu_seconds']!=parent['phase_gpu_seconds'] or v['total_gpu_seconds']!=28800:raise ValueError('resident authority increase forbidden')
 if v['categories']!=dict(timing=dict(phase='screening',seconds=2300),profile=dict(phase='ablations',seconds=450),accept=dict(phase='repeatability',seconds=850)):raise ValueError('resident phase allocation differs')
 for ref in [v['decision'],v['budget_authority'],v['cpu_admission'],v['cpu_source_bridge'],v['oracle'],v['acceptance_source_bridge'],*v['manifests']]:checked_reference(ROOT,ref)
 a=read_json(checked_reference(ROOT,v['cpu_admission']));bridge=read_json(checked_reference(ROOT,v['cpu_source_bridge']));oracle=read_json(checked_reference(ROOT,v['oracle']))
 if a['status']!='passed' or a['gpu_seconds']!=0 or len(a['rows'])!=72 or len({(r['model'],r['configuration']) for r in a['rows']})!=72 or a['numerical_sources']!=numeric_sources():raise ValueError('resident exact CPU admission required')
 if bridge['status']!='passed' or not bridge['numerical_sources_identical'] or bridge['cpu_executable_sha256']!=a['executable_sha256'] or bridge['image_sha256']!=a['image_sha256'] or oracle['status']!='passed' or oracle['gpu_seconds']!=0:raise ValueError('resident admission/proof binding')
 return v
def ledger_for(v,root=ROOT):
 if v!=protocol():raise ValueError('resident public authority differs')
 from lp_quant_budget import ledger_for as parent_ledger,protocol as parent_protocol
 parent=parent_ledger(parent_protocol(),root);raw=parent.path.read_bytes();prefix=b''.join(raw.splitlines(keepends=True)[:17036])
 if len(prefix.splitlines())!=17036 or hashlib.sha256(prefix).hexdigest()!=PREFIX or sum(read_json_line['charged_ns'] for read_json_line in [__import__('json').loads(x) for x in prefix.splitlines()] if read_json_line['resource']=='gpu')!=21113899268966:raise ValueError('resident historical ledger differs')
 return ComparisonLedger(parent.path.parent,parent.campaign_hash,v)
def validate_command(gate,command):
 if gate=='regular':valid=len(command)==5 and command[:2]==['bash',str(ROOT/'tools/lp_exec_regular_check.sh')] and len(set(command[2:]))==3 and all(Path(x).name.startswith('device-') for x in command[2:])
 elif gate=='project':valid=command==['python3',str(ROOT/'tools/lp_quant_resident_accept.py')]
 else:valid=len(command)==4 and command[:2]==['bash',str(ROOT/'tools/lp_quant_resident_gpu_check.sh')] and Path(command[2]).name.startswith('quant_resident_device-') and command[3]==gate
 if not valid:raise ValueError('resident gate command differs')
def main():
 p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--gate',required=True,choices=['regular','project','memcheck','racecheck','initcheck','synccheck']);p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args();command=a.command[1:] if a.command[:1]==['--'] else a.command;validate_command(a.gate,command)
 v=protocol();from benchmark_lp_quant_resident import freeze
 frozen,identity=freeze(v);directory=ROOT/v['acceptance_output'];directory.mkdir(parents=True,exist_ok=True);key=v['id']+'-accept-'+a.id;seconds=180 if a.gate=='regular' else 240 if a.gate=='project' else 90
 bound=[]
 for arg in command:
  path=Path(arg)
  if path.is_file() and path.open('rb').read(4)==b'\x7fELF':
   dest=frozen/(path.name+'-'+file_hash(path)[:16]);shutil.copy2(path,dest) if not dest.exists() else None
   if file_hash(dest)!=file_hash(path):raise ValueError('resident frozen binary differs')
   bound.append(str(dest))
  else:bound.append(arg)
 with ledger_for(v) as ledger:
  if key in ledger.attempted():raise ValueError('resident acceptance cannot retry')
  request=dict(schema_version=2,gpu_admission_seconds=3,command=['/usr/bin/env','AI_OPTIMIZER_CUDA_DIR='+str(frozen),*bound],directory=str(directory),prefix=key,solve_seconds=seconds,cleanup_seconds=2,host_rss_bytes=8589934592,poll_ms=10,output_bytes=33554432)
  path=directory/(key+'.request.json')
  if path.exists():raise ValueError('resident acceptance identity exists')
  write_json(path,request);write_json(directory/(key+'.source.json'),dict(source_tree_sha256=identity['source_tree_sha256'],request_sha256=file_hash(path),gate=a.gate,command=bound))
  reservation=ledger.reserve(key,seconds+6,phase='repeatability');worker=subprocess.Popen(['bash',str(ROOT/'tools/gpu_job.sh'),v['device'],'--lp-study-request',str(path)],pass_fds=(ledger.lock.fileno(),))
  try:worker.wait(timeout=seconds+310)
  finally:
   if worker.poll() is None:
    worker.terminate()
    try:worker.wait(timeout=3)
    except subprocess.TimeoutExpired:worker.kill();worker.wait()
   info=read_json(directory/(key+'.worker.json')) if (directory/(key+'.worker.json')).exists() else None
   ledger.settle(reservation,info['leased_ns'] if info else reservation['reserved_ns']);write_json(directory/'budget.json',receipt(ledger));shutil.copy2(ledger.path,frozen/'ledger.jsonl')
  if worker.returncode or info is None or info['reason']!='completed' or info['returncode']!=0 or info['leased_ns']>reservation['reserved_ns']:raise ValueError('resident acceptance failed; attempt retained without retry')
if __name__=='__main__':main()
