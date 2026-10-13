"""ADR-0035 explicit task, cumulative and phase budget authority."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from lp_copt_budget import ComparisonLedger, receipt
from lp_protocol import ROOT, NS, checked_reference, file_hash, read_json, write_json
from validate_artifacts import validator
CONFIG = ROOT / 'benchmarks/configs/lp-exec-v1.json'

def protocol(path=CONFIG):
    value=read_json(path)
    validator('lp-exec-study-v1.schema.json').validate(value)
    for ref in [value['budget_authority'],value['previous_protocol'],value['decision'],*value['manifests']]:checked_reference(ROOT,ref)
    return value

def ledger_for(value,root=ROOT):
    from lp_convergence_budget import ledger_for as parent_ledger
    parent=read_json(checked_reference(root,value['previous_protocol']))
    checked_reference(root,value['decision'])
    if value['budget_authority']!=parent['budget_authority'] or value['additional_gpu_seconds']!=3600 or value['cumulative_gpu_ns']!=parent['cumulative_gpu_ns']+3600*NS:raise ValueError('exec cumulative authority differs')
    if value['phase_gpu_seconds']!=dict(baseline=1800,screening=9500,ablations=7650,repeatability=4450,finalists=9000) or value['total_gpu_seconds']!=28800:raise ValueError('exec phase authority differs')
    expected=dict(timing=dict(phase='screening',seconds=2300),profile=dict(phase='ablations',seconds=450),accept=dict(phase='repeatability',seconds=850))
    if value['categories']!=expected or value['combined_cap_seconds']!=3600 or value['cpu_cap_seconds']!=21600:raise ValueError('exec task authority differs')
    if value['prior_events']!=16134 or value['prior_gpu_ns']!=17115274617853 or value['prior_ledger_sha256']!='60649d29992d21508e60aa60f3e334e9ac18fe3254525ec38cc0eef298e84823':raise ValueError('exec parent identity differs')
    # Reject malformed authority before requiring private historical artifacts.
    # Admitted work still must verify the complete preserved campaign prefix.
    inherited=parent_ledger(parent,root)
    data=inherited.path.read_bytes();prefix=b''.join(data.splitlines(keepends=True)[:16134])
    if len(prefix.splitlines())!=16134 or not prefix.endswith(b'\n') or hashlib.sha256(prefix).hexdigest()!=value['prior_ledger_sha256']:raise ValueError('exec historical prefix changed')
    if sum(json.loads(line)['charged_ns'] for line in prefix.splitlines() if json.loads(line)['resource']=='gpu')!=value['prior_gpu_ns']:raise ValueError('exec prior consumption differs')
    return ComparisonLedger(inherited.path.parent,inherited.campaign_hash,value)

def validate_gate_command(gate,command):
    if gate=='regular':
        valid=len(command)==5 and command[0]=='bash' and Path(command[1]).resolve()==ROOT/'tools/lp_exec_regular_check.sh' and len(set(command[2:]))==3 and all(Path(p).name.startswith('device-') for p in command[2:])
    elif gate=='project':
        valid=len(command)==5 and command[0]=='python3' and Path(command[1]).resolve()==ROOT/'tools/lp_exec_accept.py' and command[2:4]==['project','--binary'] and Path(command[4]).name.startswith('lp_precision_exec')
    else:
        valid=len(command)==4 and command[0]=='bash' and Path(command[1]).resolve()==ROOT/'tools/lp_exec_gpu_check.sh' and Path(command[2]).name.startswith('exec_device-') and command[3]==('regular' if gate=='oracle' else gate)
    if not valid:raise ValueError('acceptance gate/command binding differs')
    return True

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--id', required=True)
    parser.add_argument('--gate', required=True, choices=['regular','oracle','memcheck','racecheck','initcheck','synccheck','project'])
    parser.add_argument('--seconds', type=int, required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    value = protocol()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command or args.seconds <= 0:
        raise ValueError('positive duration and foreground command required')
    validate_gate_command(args.gate,command)
    from benchmark_lp import source_identity
    gate = read_json(ROOT / 'target/lp-native-gate.json')
    if not gate.get('native') or gate['source_tree_sha256'] != source_identity():
        raise ValueError('exact-source full native gate required')
    directory = ROOT / value['acceptance_output']
    # Freeze every acceptance source, image and ELF before it can be overwritten.
    import shutil
    from benchmark_lp import prepare_execution, provenance, reference
    archive = directory / 'sources' / gate['source_tree_sha256']
    base = provenance(ROOT / 'target/release/optimizer', value['device'])
    prepare_execution(archive, base)
    images = archive / 'images'; images.mkdir(exist_ok=True)
    for source in (ROOT / 'target/native/cuda').glob('*.cubin'):
        dest=images/source.name
        if dest.exists() and file_hash(dest)!=file_hash(source):raise ValueError('acceptance image changed under source identity')
        if not dest.exists():shutil.copy2(source,dest)
    frozen=[]
    for argument in command:
        path=Path(argument)
        if path.is_file() and path.open('rb').read(4)==b'\x7fELF':
            dest=archive/(path.name+'-'+file_hash(path)[:16])
            if not dest.exists():shutil.copy2(path,dest)
            frozen.append(str(dest))
        else:frozen.append(argument)
    command=['/usr/bin/env','AI_OPTIMIZER_CUDA_DIR='+str(images),'AI_OPTIMIZER_EXEC_ACCEPT_KEY='+value['id']+'-accept-'+args.id,*frozen]
    key = value['id'] + '-accept-' + args.id
    with ledger_for(value) as ledger:
        if key in ledger.attempted():
            raise ValueError('acceptance identity already attempted')
        directory.mkdir(parents=True, exist_ok=True)
        request = dict(schema_version=2, gpu_admission_seconds=3, command=command,
                       directory=str(directory), prefix=key, solve_seconds=args.seconds,
                       cleanup_seconds=2, host_rss_bytes=8589934592, poll_ms=10, output_bytes=33554432)
        path = directory / (key + '.request.json')
        if path.exists():
            raise ValueError('existing acceptance request')
        write_json(path, request)
        write_json(directory / (key + '.source.json'), dict(source_tree_sha256=gate['source_tree_sha256'], request_sha256=file_hash(path)))
        reservation = ledger.reserve(key, args.seconds + 6, phase='repeatability')
        worker = subprocess.Popen(['bash', str(ROOT / 'tools/gpu_job.sh'), value['device'], '--lp-study-request', str(path)], pass_fds=(ledger.lock.fileno(),))
        interrupted = False
        try:
            worker.wait(timeout=args.seconds + 310)
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            interrupted = True
            worker.terminate()
            try:
                worker.wait(timeout=3)
            except subprocess.TimeoutExpired:
                worker.kill(); worker.wait()
        report = directory / (key + '.worker.json')
        result = read_json(report) if report.exists() else None
        ledger.settle(reservation, result['leased_ns'] if result else reservation['reserved_ns'])
        write_json(directory / 'budget.json', receipt(ledger))
        status='passed' if not interrupted and result and worker.returncode==0 and result['reason']=='completed' and result['returncode']==0 and result['leased_ns']<=reservation['reserved_ns'] else 'failed'
        record=dict(gate=args.gate,status=status,source_tree_sha256=gate['source_tree_sha256'],image_sha256=file_hash(images/'lp_pdhg_exec.cubin'),request=reference(ROOT,path),worker=reference(ROOT,report),command=command,project=reference(ROOT,directory/(key+'.project.json')),stdout=reference(ROOT,directory/(key+'.stdout')),stderr=reference(ROOT,directory/(key+'.stderr')),images={p.name:reference(ROOT,p) for p in sorted(images.glob('*.cubin'))},binaries=[reference(ROOT,Path(p)) for p in frozen if Path(p).is_file() and Path(p).read_bytes()[:4]==b'\x7fELF'])
        write_json(directory/(key+'.gate.json'),record)
        print(result, flush=True)
        if interrupted or not result or worker.returncode or result['reason'] != 'completed' or result['returncode'] != 0 or result['leased_ns'] > reservation['reserved_ns']:
            raise SystemExit(1)


if __name__ == '__main__':
    main()
