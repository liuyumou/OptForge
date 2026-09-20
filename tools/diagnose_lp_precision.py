"""Frozen ADR-0020 equal-update and CUDA-profiler diagnostics; never baseline trials."""
import argparse
import json
import shutil
import subprocess
from pathlib import Path
from benchmark_lp import prepare_execution, provenance, quiet_device, telemetry
from benchmark_lp_precision import CONFIG
from lp_protocol import ROOT, NS, Ledger, checked_reference, file_hash, ordered, read_json, validate, write_json

OUTPUT = ROOT / 'artifacts/gpup5-diagnosis-v1'
HISTORY = ROOT / 'artifacts/gpup5-fp32-v1'
PRIOR_NS = 1324210639253
PRIOR_EVENTS = 2862
PRIOR_HASH = '66d8c2b0ee24ce050ee051c6dbea2184361abe2c2fc4a57b8ee202c001479ff0'
CAP_NS = 300 * NS
NSYS = Path('/opt/nvidia/nsight-compute/2025.3.0/host/target-linux-x64/nsys')
NCU = Path('/opt/nvidia/nsight-compute/2025.3.0/ncu')
NAMES = ['small-4', 'irregular-256', 'irregular-2048', 'dense_block-1024']


def jobs(value):
    modes = [c for c in value['configurations'] if c['backend'] == 'cuda-lp-tuned']
    for name in NAMES:
        for repetition in range(7):
            for config in ordered(modes, value['order_seed'], name, repetition):
                yield 'short', name, config, repetition
    for name in ['small-4', 'irregular-2048']:
        for config in modes:
            yield 'trace', name, config, 0
    for config in modes:
        if config['id'] in ['precision-fp64', 'products-fp32', 'accumulation-fp32']:
            yield 'counter', 'irregular-2048', config, 0


def work_limit(config):
    return 206 if config.get('precision', {}).get('correction_interval') == 32 else 200


def label(job):
    kind, name, config, repetition = job
    return f'{kind}-{name}-{config["id"]}-{repetition}'


def check_prefix(path):
    import hashlib
    prefix = b''.join(path.read_bytes().splitlines(keepends=True)[:PRIOR_EVENTS])
    if hashlib.sha256(prefix).hexdigest() != PRIOR_HASH:
        raise ValueError('GPUP-5 ledger history changed')


def run_job(value, job, binary, directory, ledger):
    kind, name, config, repetition = job
    key = label(job)
    identity = 'gpup5-diagnosis-v1-' + key
    seconds = 30 if kind == 'counter' else 10
    reservation_seconds = seconds + 6
    if ledger.totals() - PRIOR_NS + reservation_seconds * NS > CAP_NS:
        raise ValueError('diagnostic cap reached; incomplete evidence retained')
    activity = quiet_device(value['device'])
    before = telemetry(value['device'])
    model = ROOT / f'artifacts/lp-inputs-v1/gpup-development-{name}.json'
    evidence = directory / (key + '.endpoint.json')
    solve = {**value['solve'], 'iteration_limit': work_limit(config)}
    method = {**value['lp_settings'], 'iteration_limit': work_limit(config)}
    for suffix, data in [('solve', solve), ('method', method), ('execution', config['execution'])]:
        write_json(directory / (key + '.' + suffix + '.json'), data)
    command = [str(binary), 'solve', '--backend', 'cuda-lp-tuned', '--device', value['device'],
               '--model', str(model), '--config', str(directory / (key + '.solve.json')),
               '--lp-settings', str(directory / (key + '.method.json')),
               '--lp-execution', str(directory / (key + '.execution.json')),
               '--lp-evidence', str(evidence), '--lp-profile', 'true',
               '--lp-device-memory-bytes', str(value['limits']['device_buffer_bytes'])]
    if 'precision' in config:
        path = directory / (key + '.precision.json')
        write_json(path, config['precision'])
        command += ['--lp-precision', str(path)]
    if kind == 'trace':
        command = [str(NSYS), 'profile', '--trace=cuda', '--sample=none', '--cpuctxsw=none',
                   '--cuda-event-trace=false', '--stats=false', '--force-overwrite=false',
                   '--export=sqlite', '--output=' + str(directory / key)] + command
    if kind == 'counter':
        command = [str(NCU), '--clock-control', 'none', '--cache-control', 'none', '--kernel-name', 'regex:precision_spmv', '--launch-skip', '20',
                   '--launch-count', '2', '--section', 'SpeedOfLight', '--section', 'LaunchStats',
                   '--section', 'ComputeWorkloadAnalysis', '--section', 'MemoryWorkloadAnalysis',
                   '--csv', '--page', 'raw', '--log-file', str(directory / (key + '.ncu.csv'))] + command
    request = dict(schema_version=2, gpu_admission_seconds=3, command=command,
                   directory=str(directory), prefix=key, solve_seconds=seconds, cleanup_seconds=2,
                   host_rss_bytes=value['limits']['host_rss_bytes'], poll_ms=10,
                   output_bytes=value['limits']['output_bytes'])
    request_path = directory / (key + '.request.json')
    write_json(request_path, request)
    intent = dict(id=identity, kind=kind, instance=name, config=config, repetition=repetition,
                  model_sha256=file_hash(model), solve=solve, method=method, command=command,
                  activity=activity, telemetry_before=before)
    write_json(directory / (key + '.intent.json'), intent)
    reservation = ledger.reserve(identity, reservation_seconds, phase='screening')
    worker = subprocess.Popen(['bash', str(ROOT / 'tools/gpu_job.sh'), value['device'],
                               '--lp-study-request', str(request_path)], pass_fds=(ledger.lock.fileno(),))
    try:
        worker.wait(timeout=seconds + 310)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        worker.terminate()
        try:
            worker.wait(timeout=3)
        except subprocess.TimeoutExpired:
            worker.kill()
            worker.wait()
    worker_path = directory / (key + '.worker.json')
    info = read_json(worker_path) if worker_path.is_file() else None
    charge = info['leased_ns'] if info else reservation['reserved_ns']
    ledger.settle(reservation, charge)
    result = dict(**intent, worker=info, charged_ns=charge, endpoint_verified=False,
                  cumulative_gpu_ns=ledger.totals(), telemetry_after=telemetry(value['device']))
    if evidence.exists():
        endpoint = validate('endpoint', read_json(evidence))
        verification = subprocess.run([str(binary), 'lp-study', 'verify', '--model', str(model),
                                       '--evidence', str(evidence)], capture_output=True, text=True, timeout=12)
        result.update(endpoint_verified=verification.returncode == 0,
                      endpoint_sha256=file_hash(evidence), assessment=endpoint['assessment'],
                      verification_error=verification.stderr[:2000])
        if endpoint['record']['backend'] != 'cuda-lp-tuned':
            result['endpoint_verified'] = False
            result['verification_error'] = 'unexpected fallback'
    write_json(directory / (key + '.result.json'), result)
    print(f'{key}: {info and info["reason"]}; verified={result["endpoint_verified"]}; '
          f'diagnostic GPU {(ledger.totals()-PRIOR_NS)/NS:.6f}s', flush=True)
    if info is None or charge > reservation['reserved_ns']:
        raise ValueError('uncertain/overrun job retained; stop')
    if info['reason'] == 'activity_blocked':
        raise ValueError('activity appeared under lease; diagnostic paused')
    if kind != 'counter' and not result['endpoint_verified']:
        raise ValueError('missing/invalid diagnostic endpoint retained; stop')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gpu', action='store_true')
    args = parser.parse_args()
    value = read_json(CONFIG)
    schedule = list(jobs(value))
    if not args.gpu:
        print(len(schedule), 'diagnostic jobs; 300 GPU-second cap inside existing allowance')
        return
    binary = ROOT / 'target/release/optimizer'
    base = provenance(binary, value['device'])
    receipt = read_json(ROOT / 'target/lp-native-gate.json')
    if not receipt['native'] or receipt['source_tree_sha256'] != base['source_tree_sha256']:
        raise ValueError('full native gate required on exact diagnostic source')
    for filename, key in [('lp_pdhg_tuned.cubin', 'code_object_sha256'),
                          ('lp_pdhg_precision.cubin', 'precision_code_object_sha256')]:
        if file_hash(ROOT / 'target/native/cuda' / filename) != value[key]:
            raise ValueError('original provisioned code object changed')
    old = read_json(HISTORY / 'artifact-index.json')
    for item in old:
        if file_hash(HISTORY / item['path']) != item['sha256']:
            raise ValueError('archived GPUP-5 artifact changed: ' + item['path'])
    protocol = dict(schema_version=1, kind='diagnosis_not_baseline', id='gpup5-diagnosis-v1',
                    adr_sha256=file_hash(ROOT / 'docs/decisions/ADR-0020-fp32-latency-diagnosis.md'),
                    source_campaign_sha256=file_hash(CONFIG), prior_gpu_ns=PRIOR_NS, cap_ns=CAP_NS,
                    cumulative_ceiling_ns=value['cumulative_gpu_ns'], jobs=schedule,
                    history_index_sha256=file_hash(HISTORY / 'artifact-index.json'),
                    profiler={p.name: dict(path=str(p), sha256=file_hash(p), version=subprocess.check_output(
                        [str(p), '--version'], text=True).strip()) for p in [NSYS, NCU]})
    authority = checked_reference(ROOT, value['budget_authority'])
    ledger_directory = ROOT / 'artifacts/lp-campaign-ledgers' / read_json(authority)['id']
    check_prefix(ledger_directory / 'ledger.jsonl')
    with Ledger(ledger_directory, file_hash(authority), value['phase_gpu_seconds'],
                cumulative_ns=value['cumulative_gpu_ns']) as ledger:
        if read_json(ledger_directory / 'output.json')['output_path'] != str(ROOT / 'artifacts/gpup-baseline-v1'):
            raise ValueError('original output binding changed')
        prepare_execution(OUTPUT, base)
        frozen = OUTPUT / 'diagnostic-protocol.json'
        if frozen.exists() and read_json(frozen) != json.loads(json.dumps(protocol)):
            raise ValueError('diagnostic protocol differs across resume')
        write_json(frozen, protocol)
        for source in [binary, ROOT / 'target/native/cuda/lp_pdhg_precision.cubin',
                       ROOT / 'target/native/cuda/lp_pdhg_tuned.cubin']:
            destination = OUTPUT / source.name
            if destination.exists() and file_hash(destination) != file_hash(source):
                raise ValueError('archived executable identity differs')
            if not destination.exists():
                shutil.copy2(source, destination)
        try:
            for job in schedule:
                if 'gpup5-diagnosis-v1-' + label(job) not in ledger.attempted():
                    run_job(value, job, binary, OUTPUT, ledger)
        finally:
            shutil.copyfile(ledger.path, OUTPUT / 'ledger.jsonl')
    write_json(OUTPUT / 'artifact-hashes.json', {p.name: file_hash(p) for p in sorted(OUTPUT.iterdir())
                                                if p.is_file() and p.name != 'artifact-hashes.json'})


if __name__ == '__main__':
    main()
