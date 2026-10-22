"""ADR-0039 bounded allocation; preserve the exact inherited campaign ledger."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from lp_copt_budget import ComparisonLedger,receipt
from lp_protocol import ROOT,checked_reference,file_hash,read_json,write_json
from validate_artifacts import validator
CONFIG=ROOT/'benchmarks/configs/lp-assess-v1.json'
PREFIX='e83d07792fb0775fc26d8d2cca8a2411f59fcbc94f742cafd8f6b844ffb60535'

def protocol(path=CONFIG):
    v=read_json(path);validator('lp-assess-study-v1.schema.json').validate(v)
    for ref in [v['decision'],v['previous_protocol'],v['budget_authority'],v['cpu_admission'],*v['manifests']]:checked_reference(ROOT,ref)
    if v['id']!='gpup-assess-v1' or v['combined_cap_seconds']!=2300 or v['additional_gpu_seconds']!=0 or v['cumulative_gpu_ns']!=21602574545061 or v['prior_events']!=16684 or v['prior_gpu_ns']!=19207265220123 or v['prior_ledger_sha256']!=PREFIX:raise ValueError('assessment resource authority differs')
    if v['categories']!=dict(timing=dict(phase='screening',seconds=1300),profile=dict(phase='ablations',seconds=450),accept=dict(phase='repeatability',seconds=550)):raise ValueError('assessment phase authority differs')
    admission=read_json(checked_reference(ROOT,v['cpu_admission']))
    if admission['status']!='passed' or admission['gpu_seconds']!=0 or len(admission['rows'])!=16:raise ValueError('CPU common-trajectory admission required')
    return v

def ledger_for(v,root=ROOT):
    validator('lp-assess-study-v1.schema.json').validate(v)
    if v!=protocol():raise ValueError('assessment public authority differs')
    from lp_refine_budget import protocol as parent_protocol,ledger_for as parent_ledger
    inherited=parent_ledger(parent_protocol(),root)
    raw=inherited.path.read_bytes();prefix=b''.join(raw.splitlines(keepends=True)[:16684])
    if len(prefix.splitlines())!=16684 or hashlib.sha256(prefix).hexdigest()!=PREFIX or sum(json.loads(x)['charged_ns'] for x in prefix.splitlines() if json.loads(x)['resource']=='gpu')!=19207265220123:raise ValueError('assessment historical prefix differs')
    return ComparisonLedger(inherited.path.parent,inherited.campaign_hash,v)

def validate_command(gate,command):
    if gate=='regular':
        valid=len(command)==5 and command[:2]==['bash',str(ROOT/'tools/lp_exec_regular_check.sh')] and len(set(command[2:]))==3 and all(Path(p).name.startswith('device-') for p in command[2:])
    elif gate=='project':valid=command==['python3',str(ROOT/'tools/lp_assess_accept.py'),'project']
    else:valid=len(command)==4 and command[:2]==['bash',str(ROOT/'tools/lp_assess_gpu_check.sh')] and Path(command[2]).name.startswith('assess_device-') and command[3]==gate
    if not valid:raise ValueError('assessment gate/command mismatch')

def main():
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--gate',required=True,choices=['regular','project','memcheck','racecheck','initcheck','synccheck']);p.add_argument('--seconds',type=int,required=True);p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
    v=protocol();command=a.command[1:] if a.command[:1]==['--'] else a.command;validate_command(a.gate,command)
    if a.seconds!=(120 if a.gate in ['regular','project'] else 60):raise ValueError('assessment gate reservation differs')
    from benchmark_lp_assess import freeze
    frozen,identity=freeze(v);directory=ROOT/v['acceptance_output'];directory.mkdir(parents=True,exist_ok=True)
    bound=[]
    for arg in command:
        path=Path(arg)
        if path.is_file() and path.open('rb').read(4)==b'\x7fELF':
            dest=frozen/(path.name+'-'+file_hash(path)[:16])
            if not dest.exists():shutil.copy2(path,dest)
            bound.append(str(dest))
        else:bound.append(arg)
    key=v['id']+'-accept-'+a.id
    with ledger_for(v) as ledger:
        if key in ledger.attempted():raise ValueError('assessment acceptance cannot retry')
        request=dict(schema_version=2,gpu_admission_seconds=3,command=['/usr/bin/env','AI_OPTIMIZER_CUDA_DIR='+str(frozen),*bound],directory=str(directory),prefix=key,solve_seconds=a.seconds,cleanup_seconds=2,host_rss_bytes=8589934592,poll_ms=10,output_bytes=33554432)
        path=directory/(key+'.request.json')
        if path.exists():raise ValueError('assessment acceptance identity exists')
        write_json(path,request);write_json(directory/(key+'.source.json'),dict(source_tree_sha256=identity['source_tree_sha256'],request_sha256=file_hash(path),gate=a.gate,binaries=[dict(path=str(Path(x).relative_to(ROOT)),sha256=file_hash(Path(x))) for x in bound if Path(x).is_file() and Path(x).open('rb').read(4)==b'\x7fELF']))
        reservation=ledger.reserve(key,a.seconds+6,phase='repeatability')
        worker=subprocess.Popen(['bash',str(ROOT/'tools/gpu_job.sh'),v['device'],'--lp-study-request',str(path)],pass_fds=(ledger.lock.fileno(),))
        interrupted=False
        try:worker.wait(timeout=a.seconds+310)
        except (subprocess.TimeoutExpired,KeyboardInterrupt):
            interrupted=True;worker.terminate()
            try:worker.wait(timeout=3)
            except subprocess.TimeoutExpired:worker.kill();worker.wait()
        finally:
            result_path=directory/(key+'.worker.json');info=read_json(result_path) if result_path.exists() else None
            ledger.settle(reservation,info['leased_ns'] if info else reservation['reserved_ns']);write_json(directory/'budget.json',receipt(ledger));shutil.copy2(ledger.path,frozen/'ledger.jsonl')
        if interrupted or worker.returncode or info is None or info['reason']!='completed' or info['returncode']!=0:raise ValueError('assessment acceptance failed; retained without retry')
if __name__=='__main__':main()
