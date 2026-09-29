"""Frozen GPUP-ADAPTIVE-COST fresh-process comparison; historical protocols stay unchanged."""
import argparse
from pathlib import Path
import shutil
import signal
import subprocess
import time
from benchmark_lp import prepare_execution, provenance, quiet_device, reference, telemetry
from benchmark_lp_adaptive import code_images
from lp_adaptive_cost_budget import CONFIG, ledger_for, protocol, receipt
from lp_protocol import ROOT, checked_reference, digest, encoded, file_hash, ordered, read_json, write_json
from validate_artifacts import schema_snapshot, validator


def instances(value):
    return {i['id']: i for ref in value['manifests']
            for i in read_json(checked_reference(ROOT, ref))['instances']}


def jobs(value):
    models = instances(value)
    for mode, count, names in [('timing', value['timing_repetitions'], value['instances']),
                               ('profile', 1, value['profile_instances'])]:
        for repetition in range(count):
            for name in names:
                for policy in value['policies']:
                    configs = [c for c in value['configurations'] if c['policy_id'] == policy['id']]
                    for order, config in enumerate(ordered(configs, value['order_seed'], name + ':' + policy['id'], repetition)):
                        yield dict(id=f'{value["id"]}-{mode}-{name}-{repetition}-{config["id"]}',
                                   instance=models[name], configuration=config, repetition=repetition, order=order, mode=mode)


def configuration_hash(value, config):
    return digest(encoded(dict(configuration=config, solve=value['solve'], lp_settings=value['lp_settings'])))


def command(value, job, binary, directory):
    key = job['id']; config = job['configuration']
    args = [str(binary), 'lp-study', 'solve', '--model', str(checked_reference(ROOT, job['instance']['model'])),
            '--model-byte-limit', str(value['model_byte_limit']), '--config', str(directory / 'solve.json'),
            '--backend', config['backend'], '--lp-settings', str(directory / 'lp-settings.json'),
            '--lp-execution', str(directory / 'execution-settings.json'), '--lp-profile', str(job['mode'] == 'profile').lower(),
            '--lp-device-memory-bytes', str(value['limits']['device_buffer_bytes']), '--device', value['device'],
            '--lp-evidence', str(directory / (key + '.endpoint.json')), '--evidence-format', config['evidence_format']]
    args += ['--lp-adaptive', str(directory / (config['policy_id'] + '.adaptive.json'))]
    if job['mode'] == 'profile':
        args += ['--cost-profile', str(directory / (key + '.cost.json'))]
    return ['/usr/bin/env', 'AI_OPTIMIZER_CUDA_DIR=' + str(directory), *args]


def endpoint_shape(path, expected_format):
    data = read_json(path)
    if expected_format == 'compact-v1':
        validator('lp-compact-endpoint-v1.schema.json').validate(data)
        return data['endpoint']
    from lp_protocol import validate
    if 'format' in data:
        raise ValueError('compact endpoint supplied for a legacy request')
    return validate('endpoint', data)


def verify_endpoint(value, job, directory, binary, identity):
    path = directory / (job['id'] + '.endpoint.json')
    config = job['configuration']; endpoint = endpoint_shape(path, config['evidence_format'])
    record = endpoint['record']
    if endpoint['model_sha256'] != job['instance']['model']['sha256'] or endpoint['requested_backend'] != config['backend']:
        raise ValueError('model/requested backend differs')
    if record['options'] != value['solve']:
        raise ValueError('solve options differ')
    if record['backend'] != 'highs' and record.get('lp_settings') != value['lp_settings']:
        raise ValueError('LP settings differ')
    if endpoint.get('execution', {}).get('settings') != config['execution']:
        raise ValueError('execution settings differ')
    if record.get('lp_adaptive') != config['adaptive'] or endpoint.get('adaptive', {}).get('settings') != config['adaptive']:
        raise ValueError('adaptive policy differs')
    if record['schema_version'] != 5 or record.get('lp_precision') is not None:
        raise ValueError('adaptive record identity differs')
    code_hash = endpoint['execution']['code_object_sha256']
    if code_hash is not None and code_hash != identity['code_object_sha256']:
        raise ValueError('code identity differs')
    if record['backend'] == config['backend'] and code_hash != identity['code_object_sha256']:
        raise ValueError('successful device execution lacks code identity')
    result = subprocess.run([str(binary), 'lp-study', 'verify', '--model', str(checked_reference(ROOT, job['instance']['model'])),
                             '--model-byte-limit', str(value['model_byte_limit']), '--evidence', str(path)],
                            capture_output=True, text=True, timeout=value['verification_seconds'])
    if result.returncode:
        raise ValueError('independent verifier rejected evidence: ' + result.stderr[:1000])
    if json_summary(result.stdout) != endpoint['assessment']:
        raise ValueError('verifier assessment output differs')
    return endpoint


def json_summary(text):
    from lp_protocol import strict_loads
    return strict_loads(text)


def validate_trial(trial):
    validator('lp-adaptive-cost-trial-v1.schema.json').validate(trial)
    return trial


def run_trial(value, job, binary, directory, ledger, identity, protocol_hash):
    key = job['id']; config = job['configuration']; limits = value['limits']
    activity = quiet_device(value['device'])
    write_json(directory / (key + '.activity.json'), activity)
    request = {k: limits[k] for k in ['solve_seconds', 'cleanup_seconds', 'host_rss_bytes', 'poll_ms', 'output_bytes']}
    request.update(schema_version=2, gpu_admission_seconds=3, command=command(value, job, binary, directory), directory=str(directory), prefix=key)
    request_path = directory / (key + '.request.json')
    if request_path.exists():
        raise ValueError('existing unadmitted trial request; inspect retained intent before resuming')
    write_json(request_path, request)
    trial = dict(schema_version=1, id=key, campaign_sha256=protocol_hash, instance_id=job['instance']['id'],
                 model_sha256=job['instance']['model']['sha256'], config_id=config['id'], variant=config['variant'], policy_id=config['policy_id'], adaptive=config['adaptive'], evidence_format=config['evidence_format'],
                 config_sha256=configuration_hash(value, config), block=f'{job["instance"]["id"]}:{config["policy_id"]}:{job["repetition"]}',
                 repetition=job['repetition'], order=job['order'], mode=job['mode'], category=job['mode'],
                 requested_backend=config['backend'], executed_backend=None, status='process_failure', endpoint_class=None,
                 endpoint=None, worker=None, stdout=None, stderr=None, elapsed_ns=None, queue_ns=None, leased_ns=None,
                 verification_ns=None, peak_rss_bytes=None, memory_method='unavailable: worker not completed', limits=limits,
                 provenance={**identity, 'telemetry_before': telemetry(value['device']), 'schema_snapshot_sha256': schema_snapshot().sha256},
                 error='unfinished trial intent', budget_authority_sha256=ledger.campaign_hash,
                 activity_wait_ns=activity['elapsed_ns'], activity=reference(directory, directory / (key + '.activity.json')),
                 solve=value['solve'], lp_settings=value['lp_settings'], request_sha256=file_hash(request_path), cost=None)
    validate_trial(trial); write_json(directory / (key + '.intent.json'), trial)
    reservation = ledger.reserve(key, limits['solve_seconds'] + limits['cleanup_seconds'] + 4, phase=value['categories'][job['mode']]['phase'])
    worker = subprocess.Popen(['bash', str(ROOT / 'tools/gpu_job.sh'), value['device'], '--lp-study-request', str(request_path)],
                              pass_fds=(ledger.lock.fileno(),))
    interrupted = False
    try:
        worker.wait(timeout=limits['solve_seconds'] + limits['cleanup_seconds'] + 310)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        interrupted = True; worker.send_signal(signal.SIGTERM)
        try:
            worker.wait(timeout=3)
        except subprocess.TimeoutExpired:
            worker.kill(); worker.wait()
    worker_path = directory / (key + '.worker.json')
    info = read_json(worker_path) if worker_path.exists() else None
    charge = info['leased_ns'] if info else reservation['reserved_ns']
    ledger.settle(reservation, charge)
    if info:
        trial.update(status=info['reason'] if worker.returncode == 0 else 'process_failure',
                     elapsed_ns=info['elapsed_ns'], queue_ns=info['queue_ns'], leased_ns=info['leased_ns'],
                     peak_rss_bytes=info['peak_rss_bytes'], memory_method=info['memory_method'],
                     error=None if worker.returncode == 0 else 'supervisor failed')
    else:
        trial['error'] = 'missing worker report; full reservation charged'
    trial['worker'] = reference(directory, worker_path)
    for role in ['stdout', 'stderr', 'endpoint', 'cost']:
        trial[role] = reference(directory, directory / (key + ('.endpoint.json' if role == 'endpoint' else '.cost.json' if role == 'cost' else '.' + role)))
    start = time.monotonic_ns()
    if trial['endpoint']:
        try:
            endpoint = verify_both(value, job, directory, identity)
            trial.update(executed_backend=endpoint['record']['backend'], endpoint_class=endpoint['assessment']['classification'])
        except Exception as error:
            trial.update(status='invalid_evidence', error=str(error)[:2000])
    elif trial['status'] == 'completed':
        trial.update(status='missing_evidence', error='no complete endpoint')
    trial['verification_ns'] = time.monotonic_ns() - start
    trial['provenance']['telemetry_after'] = telemetry(value['device'])
    validate_trial(trial); write_json(directory / (key + '.trial.json'), trial)
    write_json(directory / 'budget.json', receipt(ledger))
    print(key + ': ' + trial['status'] + '/' + str(trial['endpoint_class']) + '; GPU ' + f'{charge / 1e9:.6f}s', flush=True)
    if interrupted or info is None or charge > reservation['reserved_ns']:
        raise ValueError('interrupted/uncertain worker retained; stop')


def recover_intents(directory, attempted):
    for path in directory.glob('*.intent.json'):
        trial = read_json(path); destination = directory / (trial['id'] + '.trial.json')
        if trial['id'] in attempted and not destination.exists():
            trial.update(status='process_failure', error='interrupted coordinator; reservation retained; no retry')
            validate_trial(trial); write_json(destination, trial)


def verify_both(value, job, directory, identity):
    endpoints = [verify_endpoint(value, job, directory, directory / name, identity)
                 for name in ['optimizer-baseline', 'optimizer']]
    if endpoints[0] != endpoints[1]:
        raise ValueError('independent verifiers disagree')
    return endpoints[0]


def freeze(value, binary):
    native = provenance(binary, value['device'])
    native.update(copt_library_sha256=None, copt_binding_sha256=None)
    gate = read_json(ROOT / 'target/lp-native-gate.json')
    if native['build_profile'] != 'release' or not gate.get('native') or gate['source_tree_sha256'] != native['source_tree_sha256']:
        raise ValueError('exact-source full native gate and release binary required')
    baseline_dir = ROOT / value['baseline_output']
    baseline = read_json(baseline_dir / 'execution.json')
    if baseline['revision'] != value['baseline_revision'] or baseline['dirty']:
        raise ValueError('baseline must be the frozen clean revision')
    if baseline['binary_sha256'] != file_hash(baseline_dir / 'optimizer') or baseline['source_archive_sha256'] != file_hash(baseline_dir / 'source.tar'):
        raise ValueError('baseline archive identity differs')
    for key in ['highs_library_sha256', 'rustc', 'cargo', 'cpu_affinity', 'device', 'build_profile']:
        if baseline[key] != native[key]:
            raise ValueError('baseline/repaired environment differs: ' + key)
    code = ROOT / 'target/native/cuda'; images = code_images(code)
    original = read_json(ROOT / 'benchmarks/configs/lp-precision-v4.json')
    if images['lp_pdhg_tuned.cubin'] != original['code_object_sha256'] or images['lp_pdhg_precision.cubin'] != original['precision_code_object_sha256']:
        raise ValueError('legacy code images changed')
    native['code_object_sha256'] = images['lp_pdhg_precision.cubin']
    if baseline['code_object_sha256'] != native['code_object_sha256']:
        raise ValueError('baseline code image differs')
    directory = ROOT / value['output']; prepare_execution(directory, native)
    copies = [(binary, 'optimizer'), (baseline_dir / 'optimizer', 'optimizer-baseline'),
              (baseline_dir / 'source.tar', 'baseline-source.tar'),
              *[(code / name, name) for name in images]]
    for source, name in copies:
        dest = directory / name
        if dest.exists() and file_hash(dest) != file_hash(source):
            raise ValueError('archived executable/source/image differs: ' + name)
        if not dest.exists():
            shutil.copy2(source, dest)
    # This is the collector's schema snapshot; each binary has its own source archive.
    identities = {name: {k: v for k, v in identity.items() if k in native}
                  for name, identity in [('baseline', baseline), ('repaired', native)]}
    for identity in identities.values():
        identity['schema_snapshot_sha256'] = schema_snapshot().sha256
    frozen = {'campaign.json': value, 'code-objects.json': images, 'solve.json': value['solve'],
              'lp-settings.json': value['lp_settings'], 'execution-settings.json': value['configurations'][0]['execution'],
              'baseline-execution.json': baseline, 'configuration-executions.json': identities,
              'budget-binding.json': dict(ledger_directory='artifacts/lp-campaign-ledgers/gpup-baseline-v1')}
    frozen.update({p['id'] + '.adaptive.json': p['adaptive'] for p in value['policies']})
    for name, data in frozen.items():
        path = directory / name
        if path.exists() and read_json(path) != data:
            raise ValueError('frozen input differs: ' + name)
        if not path.exists():
            write_json(path, data)
    return directory, identities


def check_acceptance(value, identities):
    directory = ROOT / value['acceptance_output']
    for name, command_args in [('regular', ['bash', 'tools/lp_adaptive_gpu_check.sh', 'regular']),
                               ('cli', ['python3', 'tools/lp_adaptive_cost_gpu_check.py']),
                               *[(s, ['bash', 'tools/lp_adaptive_gpu_check.sh', s]) for s in ['memcheck', 'racecheck', 'initcheck', 'synccheck']]]:
        key = value['id'] + '-accept-' + name
        source = read_json(directory / (key + '.source.json'))
        worker = read_json(directory / (key + '.worker.json'))
        request = directory / (key + '.request.json')
        if source['source_tree_sha256'] != identities['repaired']['source_tree_sha256'] or source['request_sha256'] != file_hash(request):
            raise ValueError('acceptance source/request differs')
        if read_json(request)['command'] != command_args or worker['reason'] != 'completed' or worker['returncode'] != 0:
            raise ValueError('matching device acceptance required: ' + name)
    cli = read_json(directory / 'cli-adaptive-cost.json')
    if cli['status'] != 'passed' or cli['binaries'] != {k: v['binary_sha256'] for k, v in identities.items()}:
        raise ValueError('matching CLI acceptance required')
    expected = {(c['instance'], c['configuration']) for c in value['acceptance_cases']}
    for name in ['pairs', 'replays']:
        if len(cli[name]) != len(expected) or {(r['instance'], r['configuration']) for r in cli[name]} != expected:
            raise ValueError('incomplete fixed-work/replay coverage')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol', type=Path, default=CONFIG)
    parser.add_argument('--binary', type=Path, default=ROOT / 'target/release/optimizer')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--prepare', action='store_true')
    args = parser.parse_args(); value = protocol(args.protocol); schedule = list(jobs(value))
    if len(schedule) != value['planned_attempts'] or len({j['id'] for j in schedule}) != len(schedule):
        raise ValueError('frozen host schedule differs')
    if args.dry_run:
        print('24 timings (864 seconds reservation), 8 profiles (288); 1000/300/500 category caps; no added allowance')
        return
    directory, identities = freeze(value, args.binary.resolve())
    if args.prepare:
        return
    check_acceptance(value, identities)
    with ledger_for(value) as ledger:
        recover_intents(directory, ledger.attempted())
        try:
            for job in schedule:
                if job['id'] in ledger.attempted():
                    continue
                variant = job['configuration']['variant']
                binary = directory / ('optimizer-baseline' if variant == 'baseline' else 'optimizer')
                try:
                    run_trial(value, job, binary, directory, ledger, identities[variant], file_hash(args.protocol))
                except ValueError as error:
                    if 'budget exhausted' not in str(error).lower():
                        raise
                    print(str(error), flush=True); break
        finally:
            shutil.copyfile(ledger.path, directory / 'ledger.jsonl')
            write_json(directory / 'budget.json', receipt(ledger))


if __name__ == '__main__':
    main()
