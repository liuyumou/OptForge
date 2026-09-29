"""SPEC-0019 frozen fresh scalar/bulk comparison; no historical worker is edited."""
import argparse
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
from benchmark_lp import prepare_execution, provenance, quiet_device, reference, telemetry
from benchmark_lp_copt import effective, is_gpu, verify_endpoint, cost_artifact
from lp_copt_adapter_budget import CONFIG, ledger_for, protocol, receipt
from lp_protocol import ROOT, checked_reference, digest, encoded, file_hash, ordered, read_json, write_json
from validate_artifacts import schema_snapshot, validator

SUFFIXES = dict(worker='.worker.json', stdout='.stdout', stderr='.stderr', endpoint='.endpoint.json',
                witness='.endpoint.witness.json', log='.endpoint.copt.log', cost='.cost.json',
                raw_cost='.raw-cost.json', cert_cost='.endpoint.cert-cost.json',
                observations='.endpoint.copt-observations.json', activity='.activity.json')


def jobs(value):
    instances = {i['id']: i for ref in value['manifests'] for i in read_json(checked_reference(ROOT, ref))['instances']}
    for kind, repeats, names in [('timing', 3, value['instances']), ('profile', 1, value['profile_instances'])]:
        for repetition in range(repeats):
            for name in names:
                for order, config in enumerate(ordered(value['configurations'], value['order_seed'], name, repetition)):
                    yield dict(id=f'{value["id"]}-{kind}-{name}-{repetition}-{config["id"]}', kind=kind, category=kind,
                               repetition=repetition, order=order, instance=instances[name], configuration=config)


def configuration_hash(value, job):
    solve, method, _ = effective(value, job)
    return digest(encoded(dict(configuration=job['configuration'], solve=solve, lp_settings=method)))


def command(value, job, binary, directory):
    key = job['id']; c = job['configuration']
    script = 'lp_copt_comparison.py' if c['adapter_id'] == 'copt-scalar-v1' else 'lp_copt_bulk.py'
    args = [str(ROOT / value['copt_python']), '-B', str(ROOT / 'tools' / script), '--model',
            str(checked_reference(ROOT, job['instance']['model'])), '--config', str(directory / (key + '.solve.json')),
            '--output', str(directory / (key + '.endpoint.json')), '--binary', str(binary), '--method', c['backend'],
            '--device', value['device'] if is_gpu(job) else 'cpu']
    if job['kind'] == 'profile': args += ['--cost-profile', str(directory / (key + '.raw-cost.json'))]
    return ['/usr/bin/env', 'COPT_HOME=' + value['copt_installation'], 'COPT_LICENSE_DIR=' + value['copt_installation'],
            'LD_LIBRARY_PATH=/usr/local/cuda/lib64', *([] if is_gpu(job) else ['CUDA_VISIBLE_DEVICES=']), *args]


def request_for(value, job, binary, directory):
    _, _, limits = effective(value, job)
    request = {k: limits[k] for k in ['solve_seconds', 'cleanup_seconds', 'host_rss_bytes', 'poll_ms', 'output_bytes']}
    request.update(command=command(value, job, binary, directory), directory=str(directory), prefix=job['id'])
    if is_gpu(job): request.update(schema_version=2, gpu_admission_seconds=3)
    return request


def validate_trial(data):
    validator('lp-copt-adapter-trial-v1.schema.json').validate(data)
    return data


def recover_intents(directory, attempted):
    for path in directory.glob('*.intent.json'):
        trial = read_json(path); dest = directory / (trial['id'] + '.trial.json')
        if trial['id'] in attempted and not dest.exists():
            trial.update(status='process_failure', error='interrupted coordinator; full reservation retained; no retry')
            write_json(dest, validate_trial(trial))


def run_trial(value, job, binary, directory, ledger, identity, protocol_hash):
    key = job['id']; gpu = is_gpu(job); c = job['configuration']; solve, method, limits = effective(value, job)
    activity = quiet_device(value['device']) if gpu else None
    if activity: write_json(directory / (key + '.activity.json'), activity)
    write_json(directory / (key + '.solve.json'), solve)
    request = request_for(value, job, binary, directory)
    request_path = directory / (key + '.request.json'); write_json(request_path, request)
    trial = dict(schema_version=1, id=key, campaign_sha256=protocol_hash, instance_id=job['instance']['id'],
                 model_sha256=job['instance']['model']['sha256'], config_id=c['id'], config_sha256=configuration_hash(value, job),
                 block=f'{job["kind"]}:{job["instance"]["id"]}:{job["repetition"]}', repetition=job['repetition'], order=job['order'],
                 mode=job['kind'], category=job['category'], adapter_id=c['adapter_id'], dependencies_sha256=value['dependencies']['sha256'],
                 requested_backend=c['backend'], executed_backend=None, status='process_failure', endpoint_class=None,
                 elapsed_ns=None, queue_ns=None, leased_ns=None, verification_ns=None, peak_rss_bytes=None,
                 memory_method='unavailable: worker not completed', limits=limits, provenance=identity,
                 error='unfinished trial intent', budget_authority_sha256=ledger.campaign_hash,
                 activity_wait_ns=activity['elapsed_ns'] if activity else None, solve=solve, lp_settings=method,
                 request_sha256=file_hash(request_path), **{k: None for k in SUFFIXES})
    trial['activity'] = reference(directory, directory / (key + '.activity.json'))
    write_json(directory / (key + '.intent.json'), validate_trial(trial))
    reservation = ledger.reserve(key, limits['solve_seconds'] + limits['cleanup_seconds'] + (4 if gpu else 1),
                                 resource='gpu' if gpu else 'cpu', phase=value['categories'][job['category']]['phase'])
    args = ['bash', str(ROOT / 'tools/gpu_job.sh'), value['device'], '--lp-study-request', str(request_path)] if gpu else [sys.executable, str(ROOT / 'tools/lp_supervise.py'), '--request', str(request_path)]
    worker = subprocess.Popen(args, pass_fds=(ledger.lock.fileno(),)); interrupted = False
    try: worker.wait(timeout=limits['solve_seconds'] + limits['cleanup_seconds'] + (310 if gpu else 10))
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        interrupted = True; worker.send_signal(signal.SIGTERM)
        try: worker.wait(timeout=3)
        except subprocess.TimeoutExpired: worker.kill(); worker.wait()
    path = directory / (key + '.worker.json'); info = read_json(path) if path.exists() else None
    charge = (info['leased_ns'] if gpu else info['elapsed_ns']) if info else reservation['reserved_ns']
    ledger.settle(reservation, charge)
    if info:
        trial.update(status=info['reason'] if worker.returncode == 0 else 'process_failure', error=None if worker.returncode == 0 else 'supervisor failed',
                     **{k: info[k] for k in ['elapsed_ns', 'queue_ns', 'leased_ns', 'peak_rss_bytes', 'memory_method']})
    else: trial['error'] = 'missing worker report; full reservation charged'
    for role, suffix in SUFFIXES.items(): trial[role] = reference(directory, directory / (key + suffix))
    started = time.monotonic_ns()
    if trial['endpoint']:
        try: trial['executed_backend'], trial['endpoint_class'] = verify_endpoint(value, job, directory, binary, identity)
        except Exception as error: trial.update(status='invalid_evidence', error=str(error)[:2000])
    elif trial['status'] == 'completed': trial.update(status='missing_evidence', error='no complete endpoint')
    trial['verification_ns'] = time.monotonic_ns() - started
    if job['kind'] == 'profile':
        try: trial['cost'] = cost_artifact(job, directory, trial, None)
        except Exception as error: trial.update(status='invalid_evidence', error=str(error)[:2000])
    write_json(directory / (key + '.trial.json'), validate_trial(trial)); write_json(directory / 'budget.json', receipt(ledger))
    print(key + ': ' + trial['status'] + '/' + str(trial['endpoint_class']), flush=True)
    if interrupted or info is None or charge > reservation['reserved_ns']: raise ValueError('uncertain worker retained; stop')


def freeze(value, binary):
    native = provenance(binary, value['device']); native['code_object_sha256'] = None
    gate = read_json(ROOT / 'target/lp-native-gate.json')
    if not gate.get('native') or gate['source_tree_sha256'] != native['source_tree_sha256'] or native['build_profile'] != 'release':
        raise ValueError('exact-source full native gate/release binary required')
    subprocess.run([str(ROOT / value['copt_python']), '-B', str(ROOT / 'tools/setup_copt_adapter.py'), '--identity'], check=True)
    dependency = checked_reference(ROOT, value['dependencies']); deps = read_json(dependency)
    native.update(copt_library_sha256=deps['files']['coptpy/libcopt_python.so'], copt_binding_sha256=deps['files']['coptpy/coptcore.so'])
    original = read_json(ROOT / 'benchmarks/configs/lp-precision-v4.json')
    if any(native[k] != original[k] for k in ['copt_library_sha256', 'copt_binding_sha256']): raise ValueError('COPT bytes differ')
    directory = ROOT / value['output']; prepare_execution(directory, native)
    for source, name in [(binary, 'optimizer'), (ROOT / value['baseline_output'] / 'optimizer', 'optimizer-baseline'),
                         (ROOT / value['baseline_output'] / 'source.tar', 'baseline-source.tar'), (dependency, 'dependencies.json')]:
        target = directory / name
        if target.exists() and file_hash(target) != file_hash(source): raise ValueError('frozen archive differs: ' + name)
        if not target.exists(): shutil.copy2(source, target)
    path = directory / 'campaign.json'
    if path.exists() and read_json(path) != value: raise ValueError('archived protocol differs')
    if not path.exists(): write_json(path, value)
    execution = read_json(directory / 'execution.json')
    return directory, {k: v for k, v in execution.items() if k != 'source_archive_sha256'}


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--dry-run', action='store_true'); p.add_argument('--prepare', action='store_true'); a = p.parse_args()
    value = protocol(); schedule = list(jobs(value))
    if len(schedule) != value['planned_attempts'] or len({j['id'] for j in schedule}) != len(schedule): raise ValueError('schedule differs')
    if a.dry_run: print('72 timings, 12 profiles; GPU caps 900/200/400; no added allowance'); return
    directory, identity = freeze(value, ROOT / 'target/release/optimizer')
    if a.prepare: return
    from lp_copt_adapter_accept import check_acceptance
    check_acceptance(value)
    with ledger_for(value) as ledger:
        recover_intents(directory, ledger.attempted()); exhausted = set()
        try:
            for job in schedule:
                if job['id'] in ledger.attempted() or (job['category'], is_gpu(job)) in exhausted: continue
                try: run_trial(value, job, directory / 'optimizer', directory, ledger, identity, file_hash(CONFIG))
                except ValueError as error:
                    if 'budget exhausted' not in str(error).lower(): raise
                    exhausted.add((job['category'], is_gpu(job))); print(str(error), flush=True)
        finally:
            shutil.copy2(ledger.path, directory / 'ledger.jsonl'); write_json(directory / 'budget.json', receipt(ledger))


if __name__ == '__main__': main()
