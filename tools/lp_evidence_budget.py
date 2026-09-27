"""ADR-0027: bounded evidence study on the unchanged campaign authority."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from lp_copt_budget import ComparisonLedger, receipt
from lp_protocol import ROOT, NS, checked_reference, file_hash, read_json, write_json
from validate_artifacts import validator

CONFIG = ROOT / 'benchmarks/configs/lp-evidence-v1.json'


def protocol(path=CONFIG):
    value = read_json(path)
    validator('lp-evidence-study-v1.schema.json').validate(value)
    for ref in [value['budget_authority'], value['previous_protocol'], value['decision'], *value['manifests']]:
        checked_reference(ROOT, ref)
    return value


def ledger_for(value, root=ROOT):
    """Verify the complete authority chain without depending on historical outputs."""
    base_path = checked_reference(root, value['budget_authority'])
    base = read_json(base_path)
    parent = read_json(checked_reference(root, value['previous_protocol']))
    checked_reference(root, value['decision'])
    checked_reference(root, parent['decision'])
    adaptive = read_json(checked_reference(root, parent['previous_protocol']))
    checked_reference(root, adaptive['decision'])
    throughput = read_json(checked_reference(root, adaptive['previous_protocol']))
    checked_reference(root, throughput['decision'])
    source = read_json(checked_reference(root, throughput['source_campaign']))
    for item in [parent, adaptive, source]:
        if item['budget_authority'] != value['budget_authority']:
            raise ValueError('evidence authority chain differs')
    if throughput['cumulative_ceiling_ns'] != source['cumulative_gpu_ns'] + throughput['additional_gpu_seconds'] * NS:
        raise ValueError('invalid throughput authority')
    if adaptive['cumulative_gpu_ns'] != throughput['cumulative_ceiling_ns'] + adaptive['additional_gpu_seconds'] * NS:
        raise ValueError('invalid adaptive authority')
    if parent['cumulative_gpu_ns'] != adaptive['cumulative_gpu_ns'] + parent['additional_gpu_seconds'] * NS:
        raise ValueError('invalid COPT authority')
    if value['additional_gpu_seconds'] != 0 or value['cumulative_gpu_ns'] != parent['cumulative_gpu_ns']:
        raise ValueError('compact evidence grants no new allowance')
    if value['phase_gpu_seconds'] != base['phase_gpu_seconds'] or value['total_gpu_seconds'] != base['total_gpu_seconds']:
        raise ValueError('campaign/phase caps changed')
    expected = {'timing': ('ablations', 900), 'accept': ('repeatability', 300)}
    if set(value['categories']) != set(expected):
        raise ValueError('evidence categories differ')
    for name, (phase, cap) in expected.items():
        rule = value['categories'][name]
        if rule['phase'] != phase or type(rule['seconds']) is not int or not 0 < rule['seconds'] <= cap:
            raise ValueError('evidence category authority differs')
    if not 0 < value['combined_cap_seconds'] <= 1200 or not 0 < value['cpu_cap_seconds'] <= 14400:
        raise ValueError('evidence combined/CPU cap differs')
    directory = root / 'artifacts/lp-campaign-ledgers' / base['id']
    data = (directory / 'ledger.jsonl').read_bytes()
    prefix = b''.join(data.splitlines(keepends=True)[:value['prior_events']])
    if len(prefix.splitlines()) != value['prior_events'] or not prefix.endswith(b'\n') or hashlib.sha256(prefix).hexdigest() != value['prior_ledger_sha256']:
        raise ValueError('evidence historical prefix changed')
    if sum(json.loads(line)['charged_ns'] for line in prefix.splitlines() if json.loads(line)['resource'] == 'gpu') != value['prior_gpu_ns']:
        raise ValueError('evidence prior consumption differs')
    if read_json(directory / 'output.json') != dict(campaign_sha256=file_hash(base_path), output_path=str(root / 'artifacts/gpup-baseline-v1')):
        raise ValueError('original output binding changed')
    return ComparisonLedger(directory, file_hash(base_path), value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--id', required=True)
    parser.add_argument('--seconds', type=int, required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    value = protocol()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command or args.seconds <= 0:
        raise ValueError('positive duration and foreground command required')
    from benchmark_lp import source_identity
    gate = read_json(ROOT / 'target/lp-native-gate.json')
    if not gate.get('native') or gate['source_tree_sha256'] != source_identity():
        raise ValueError('exact-source full native gate required')
    directory = ROOT / value['acceptance_output']
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
        print(result, flush=True)
        if interrupted or not result or worker.returncode or result['reason'] != 'completed' or result['returncode'] != 0 or result['leased_ns'] > reservation['reserved_ns']:
            raise SystemExit(1)


if __name__ == '__main__':
    main()
