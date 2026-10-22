"""ADR-0037 allocation within the unchanged cumulative campaign ceiling."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from lp_copt_budget import ComparisonLedger,receipt
from lp_protocol import ROOT,checked_reference,file_hash,read_json,write_json
from validate_artifacts import validator
CONFIG=ROOT/'benchmarks/configs/lp-refine-v2.json'
PREFIX='900bbaed980f273db069819028e48ee8c896024e4492ade21382199b78ae8e6e'

def protocol(path=CONFIG):
    value=read_json(path);validator('lp-refine-study-v2.schema.json').validate(value)
    for ref in [value['decision'],value['previous_protocol'],value['budget_authority'],*value['manifests']]:checked_reference(ROOT,ref)
    parent=read_json(checked_reference(ROOT,value['previous_protocol']))
    validator('lp-refine-study-v1.schema.json').validate(parent)
    checked_reference(ROOT,parent['decision'])
    return value

def ledger_for(value,root=ROOT):
    validator('lp-refine-study-v2.schema.json').validate(value)
    # Public authority is checked before any historical/private artifact access.
    if value!=protocol():raise ValueError('refine public authority differs')
    from lp_exec_budget import protocol as parent_protocol,ledger_for as parent_ledger
    inherited=parent_ledger(parent_protocol(),root)
    raw=inherited.path.read_bytes();prefix=b''.join(raw.splitlines(keepends=True)[:16454])
    if len(prefix.splitlines())!=16454 or hashlib.sha256(prefix).hexdigest()!=PREFIX:raise ValueError('refine historical prefix differs')
    if sum(json.loads(x)['charged_ns'] for x in prefix.splitlines() if json.loads(x)['resource']=='gpu')!=17665672031998:raise ValueError('refine previous consumption differs')
    return ComparisonLedger(inherited.path.parent,inherited.campaign_hash,value)

def validate_command(gate,command):
    if gate=='regular':
        valid=len(command)==5 and command[0]=='bash' and Path(command[1]).resolve()==ROOT/'tools/lp_exec_regular_check.sh' and all(Path(p).name.startswith('device-') for p in command[2:])
    elif gate=='project':
        valid=command==['python3',str(ROOT/'tools/lp_refine_accept.py'),'project']
    else:
        valid=len(command)==4 and command[0]=='bash' and Path(command[1]).resolve()==ROOT/'tools/lp_refine_gpu_check.sh' and Path(command[2]).name.startswith('refine_device-') and command[3]==('regular' if gate=='oracle' else gate)
    if not valid:raise ValueError('refine acceptance command/gate mismatch')

def main():
    a=argparse.ArgumentParser();a.add_argument('--id',required=True);a.add_argument('--gate',required=True,choices=['regular','oracle','project','memcheck','racecheck','initcheck','synccheck']);a.add_argument('--seconds',type=int,required=True);a.add_argument('command',nargs=argparse.REMAINDER);args=a.parse_args()
    value=protocol();command=args.command[1:] if args.command[:1]==['--'] else args.command
    validate_command(args.gate,command)
    if not 0<args.seconds<=120:raise ValueError('refine acceptance duration')
    from benchmark_lp_refine import freeze
    frozen,identity=freeze(value)
    gate=read_json(ROOT/'target/lp-native-gate.json')
    if gate['source_tree_sha256']!=identity['source_tree_sha256']:raise ValueError('exact source native gate required')
    # Every test binary is frozen before reservation. The project runner uses the
    # already frozen research executable and images from the study directory.
    import shutil
    directory=ROOT/value['acceptance_output'];directory.mkdir(parents=True,exist_ok=True)
    bound=[]
    for arg in command:
        path=Path(arg)
        if path.is_file() and path.open('rb').read(4)==b'\x7fELF':
            dest=frozen/(path.name+'-'+file_hash(path)[:16]);
            if not dest.exists():shutil.copy2(path,dest)
            bound.append(str(dest))
        else:bound.append(arg)
    key=value['id']+'-accept-'+args.id
    with ledger_for(value) as ledger:
        if key in ledger.attempted():raise ValueError('acceptance identity cannot retry')
        request=dict(schema_version=2,gpu_admission_seconds=3,command=['/usr/bin/env','AI_OPTIMIZER_CUDA_DIR='+str(frozen),*bound],directory=str(directory),prefix=key,solve_seconds=args.seconds,cleanup_seconds=2,host_rss_bytes=8589934592,poll_ms=10,output_bytes=33554432)
        path=directory/(key+'.request.json')
        if path.exists():raise ValueError('acceptance request already exists')
        write_json(path,request);write_json(directory/(key+'.source.json'),dict(source_tree_sha256=identity['source_tree_sha256'],request_sha256=file_hash(path),gate=args.gate))
        reservation=ledger.reserve(key,args.seconds+6,phase='repeatability')
        worker=subprocess.Popen(['bash',str(ROOT/'tools/gpu_job.sh'),value['device'],'--lp-study-request',str(path)],pass_fds=(ledger.lock.fileno(),))
        interrupted=False
        try:worker.wait(timeout=args.seconds+310)
        except (subprocess.TimeoutExpired,KeyboardInterrupt):
            interrupted=True;worker.terminate()
            try:worker.wait(timeout=3)
            except subprocess.TimeoutExpired:worker.kill();worker.wait()
        finally:
            receipt_path=directory/(key+'.worker.json');info=read_json(receipt_path) if receipt_path.exists() else None
            charged=info['leased_ns'] if info else reservation['reserved_ns'];ledger.settle(reservation,charged)
            write_json(directory/'budget.json',receipt(ledger))
        if interrupted or worker.returncode or info is None or info['reason']!='completed' or info['returncode']!=0:raise ValueError('refine acceptance failed; retained without retry')

if __name__=='__main__':main()
