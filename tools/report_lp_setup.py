"""Independently verify every retained GPUP-SETUP attempt and report coverage."""
import argparse
from collections import Counter
from pathlib import Path
import statistics
import time
from benchmark_lp_setup import check_setup, command, configuration_hash, jobs, validate_trial, verify_both, check_acceptance
from lp_setup_budget import CONFIG, protocol
from lp_generate import Random
from lp_protocol import ROOT, checked_reference, file_hash, read_json, write_json
from lp_report import percentile, successful
from report_lp_copt import check_worker, numerical_digest


def paired_ratios(pairs, seed=17002, resamples=10000):
    if not pairs:
        return None
    if any(a <= 0 or b <= 0 for a, b in pairs):
        raise ValueError('non-positive paired latency')
    rng = Random(seed)
    ratio = lambda rows: statistics.median(a / b for a, b in rows)
    estimates = [ratio([pairs[rng.integer(len(pairs))] for _ in pairs]) for _ in range(resamples)]
    return dict(paired_repetitions=len(pairs), ratio=ratio(pairs), ci95=[percentile(estimates, .025), percentile(estimates, .975)])


def timing_eligible(trial, worker, endpoint):
    return bool(successful(trial) and worker and worker['reason'] == 'completed' and worker['returncode'] == 0
                and endpoint['record']['termination'] == 'optimal')


def check_identity(value, job, trial, request, directory, binary, protocol_hash):
    config = job['configuration']
    expected = dict(id=job['id'], campaign_sha256=protocol_hash, model_sha256=job['instance']['model']['sha256'],
                    instance_id=job['instance']['id'], config_id=config['id'], variant=config['variant'], policy_id=config['policy_id'], adaptive=config['adaptive'], cuda_context=config['cuda_context'], evidence_format=config['evidence_format'],
                    config_sha256=configuration_hash(value, config), requested_backend=config['backend'],
                    repetition=job['repetition'], order=job['order'], block=f'{job["instance"]["id"]}:{config["policy_id"]}:{job["repetition"]}',
                    mode=job['mode'], category=job['mode'], limits=value['limits'], solve=value['solve'], lp_settings=value['lp_settings'],
                    budget_authority_sha256=value['budget_authority']['sha256'])
    if any(trial[k] != val for k, val in expected.items()):
        raise ValueError('trial schedule/format/configuration identity differs')
    request_expected = {k: value['limits'][k] for k in ['solve_seconds', 'cleanup_seconds', 'host_rss_bytes', 'poll_ms', 'output_bytes']}
    request_expected.update(schema_version=2, gpu_admission_seconds=3, command=command(value, job, binary, directory), directory=str(directory), prefix=job['id'])
    if request != request_expected:
        raise ValueError('worker request differs from frozen format/limits/command')



def check_trial_artifacts(directory, trial):
    suffixes = dict(worker='.worker.json', stdout='.stdout', stderr='.stderr',
                    endpoint='.endpoint.json', activity='.activity.json',
                    cost='.cost.json', setup='.setup.json')
    for role, suffix in suffixes.items():
        ref = trial[role]
        if ref:
            if ref['path'] != trial['id'] + suffix:
                raise ValueError('trial artifact path differs: ' + role)
            checked_reference(directory, ref)


def checked_ledger(path, value):
    from lp_protocol import Ledger
    if not path.is_file() or (path.read_bytes() and not path.read_bytes().endswith(b'\n')):
        raise ValueError('missing/torn ledger; reporting cannot repair it')
    ledger = Ledger(path.parent, value['budget_authority']['sha256'], value['phase_gpu_seconds'],
                    cumulative_ns=value['cumulative_gpu_ns'])
    ledger._load()
    if ledger.pending():
        raise ValueError('unsettled ledger; reporting cannot recover it')
    return ledger.events


def report(directory, value, protocol_path):
    started = time.monotonic_ns(); binary = directory / 'optimizer'
    if read_json(directory / 'campaign.json') != value:
        raise ValueError('archived protocol differs')
    identities = read_json(directory / 'configuration-executions.json'); execution = read_json(directory / 'execution.json')
    if file_hash(binary) != execution['binary_sha256']:
        raise ValueError('archived verifier binary changed')
    if file_hash(directory / 'source.tar') != execution['source_archive_sha256']:
        raise ValueError('archived source changed')
    from validate_artifacts import schema_snapshot
    if schema_snapshot().sha256 != execution['schema_snapshot_sha256']:
        raise ValueError('use the archived source/schema snapshot for this report')
    images = read_json(directory / 'code-objects.json')
    for name, expected in images.items():
        if file_hash(directory / name) != expected:
            raise ValueError('archived code image changed')
    baseline = read_json(directory / 'baseline-execution.json')
    if baseline['revision'] != value['baseline_revision'] or baseline['source_archive_sha256'] != file_hash(directory / 'baseline-source.tar'):
        raise ValueError('baseline source identity differs')
    if file_hash(directory / 'optimizer-baseline') != baseline['binary_sha256']:
        raise ValueError('baseline binary changed')
    for variant, source in [('baseline', baseline), ('repaired', execution)]:
        for field, expected in identities[variant].items():
            if field not in ('telemetry_before', 'telemetry_after', 'schema_snapshot_sha256') and source[field] != expected:
                raise ValueError('configuration execution archive differs')
    original = read_json(directory / 'original-execution.json')
    if original['revision'] != value['baseline_revision'] or original['dirty'] or original['binary_sha256'] != file_hash(directory / 'optimizer-original') or original['source_archive_sha256'] != file_hash(directory / 'original-source.tar'):
        raise ValueError('original clean baseline changed')
    checked_reference(directory, read_json(directory / 'control-attribution-binding.json'))
    check_acceptance(value, identities)
    schedule = list(jobs(value)); expected_ids = {j['id'] for j in schedule}
    paths = list(directory.glob('*.trial.json'))
    trials = {read_json(p)['id']: validate_trial(read_json(p)) for p in paths}
    if len(trials) != len(paths) or not set(trials) <= expected_ids:
        raise ValueError('duplicate/unplanned attempt')
    rows = []; verified = {}; certified = {}
    for job in schedule:
        key = job['id']; trial = trials.get(key)
        row = dict(id=key, instance_id=job['instance']['id'], variant=job['configuration']['variant'], policy_id=job['configuration']['policy_id'], mode=job['mode'],
                   repetition=job['repetition'], attempted=trial is not None, verified=False, certified=False,
                   status='unattempted', classification=None, elapsed_ns=None, leased_ns=None, endpoint_bytes=None,
                   stdout_bytes=None, partial_bytes=None, worker_returncode=None, error=None)
        rows.append(row)
        if trial is None:
            continue
        request_path = directory / (key + '.request.json')
        if file_hash(request_path) != trial['request_sha256']:
            raise ValueError('request hash differs')
        producer = directory / ('optimizer-baseline' if job['configuration']['variant'] == 'baseline' else 'optimizer')
        check_identity(value, job, trial, read_json(request_path), directory, producer, file_hash(protocol_path))
        identity = identities[job['configuration']['variant']]
        for field, val in identity.items():
            if field not in ('telemetry_before', 'telemetry_after') and trial['provenance'].get(field) != val:
                raise ValueError('execution provenance differs: ' + field)
        if trial['provenance']['schema_snapshot_sha256'] != execution['schema_snapshot_sha256']:
            raise ValueError('schema snapshot identity differs')
        check_trial_artifacts(directory, trial)
        worker = read_json(checked_reference(directory, trial['worker'])) if trial['worker'] else None
        if worker:
            check_worker(trial, worker)
            row['worker_returncode'] = worker['returncode']
        row.update(status=trial['status'], classification=trial['endpoint_class'], elapsed_ns=trial['elapsed_ns'],
                   leased_ns=trial['leased_ns'], error=trial['error'])
        for role in ['endpoint', 'stdout']:
            if trial[role]:
                row[role + '_bytes'] = checked_reference(directory, trial[role]).stat().st_size
        partial = directory / (key + '.endpoint.partial')
        if partial.exists():
            row['partial_bytes'] = partial.stat().st_size
        if trial['endpoint']:
            verify_start = time.monotonic_ns()
            try:
                if trial['setup'] is None: raise ValueError('missing bound setup receipt')
                endpoint = verify_both(value, job, directory, identity)
                check_setup(directory / (key + '.setup.json'), directory / (key + '.endpoint.json'), job['configuration']['cuda_context'], value['device'])
            except Exception as error:
                if trial['status'] != 'invalid_evidence':
                    raise
                row['error'] = 'independent rejection: ' + str(error)[:2000]
                continue
            if trial['status'] == 'invalid_evidence':
                raise ValueError('historically invalid endpoint unexpectedly verifies')
            if (endpoint['record']['backend'], endpoint['assessment']['classification']) != (trial['executed_backend'], trial['endpoint_class']):
                raise ValueError('independent endpoint classification differs from trial')
            verified[key] = dict(endpoint_sha256=trial['endpoint']['sha256'], verification_ns=time.monotonic_ns() - verify_start,
                                 numerical_sha256=numerical_digest(endpoint), termination=endpoint['record']['termination'],
                                 adaptive=endpoint.get('adaptive'), control=endpoint.get('control'), execution=endpoint.get('execution'))
            row['verified'] = True
            row['certified'] = job['mode'] == 'timing' and timing_eligible(trial, worker, endpoint)
            if row['certified']:
                certified[key] = trial
    groups = []; ratios = []; equivalence = []; profiles = []
    for policy in value['policies']:
        policy_id = policy['id']
        for name in value['instances']:
            selected = [r for r in rows if r['instance_id'] == name and r['policy_id'] == policy_id and r['mode'] == 'timing']
            for variant in ['baseline', 'repaired']:
                items = [r for r in selected if r['variant'] == variant]; good = [r for r in items if r['certified']]
                groups.append(dict(instance_id=name, policy_id=policy_id, variant=variant, planned=len(items),
                    attempted=sum(r['attempted'] for r in items), verified=sum(r['verified'] for r in items), certified=len(good),
                    certified_median_ns=statistics.median(r['elapsed_ns'] for r in good) if good else None,
                    outcomes=dict(Counter(r['status'] + '/' + str(r['classification']) for r in items))))
            left = {r['repetition']: r for r in selected if r['variant'] == 'baseline'}
            right = {r['repetition']: r for r in selected if r['variant'] == 'repaired'}
            pairs = [(left[r]['elapsed_ns'], right[r]['elapsed_ns']) for r in left if left[r]['certified'] and right[r]['certified']]
            ratios.append(dict(instance_id=name, policy_id=policy_id, comparison='baseline/repaired',
                statistics=paired_ratios(pairs, value['analysis']['seed'], value['analysis']['resamples'])))
        for mode, names, repetitions in [('timing', value['instances'], range(value['timing_repetitions'])), ('profile', value['profile_instances'], range(1))]:
            for name in names:
                for repetition in repetitions:
                    keys = [f'{value["id"]}-{mode}-{name}-{repetition}-{v}-{policy_id}' for v in ['baseline', 'repaired']]
                    equal = verified[keys[0]]['numerical_sha256'] == verified[keys[1]]['numerical_sha256'] if all(k in verified for k in keys) else None
                    equivalence.append(dict(mode=mode, instance_id=name, policy_id=policy_id, repetition=repetition, equal=equal))
    from lp_cost import validate_profile
    for job in schedule:
        if job['mode'] != 'profile':
            continue
        trial = trials.get(job['id']); raw = None
        if trial and trial['cost']:
            raw = read_json(checked_reference(directory, trial['cost'])); validate_profile(raw)
            if trial['elapsed_ns'] is None or raw['elapsed_ns'] > trial['elapsed_ns']:
                raise ValueError('profile exceeds process envelope')
        names = SETUP_SCOPES
        scopes = None if raw is None else {name: dict(calls=sum(s['calls'] for s in raw['scopes'] if s['path'][-1] == name),
                      inclusive_ns=sum(s['inclusive_ns'] for s in raw['scopes'] if s['path'][-1] == name),
                      exclusive_ns=sum(s['exclusive_ns'] for s in raw['scopes'] if s['path'][-1] == name)) for name in names}
        profiles.append(dict(id=job['id'], instance_id=job['instance']['id'], variant=job['configuration']['variant'], policy_id=job['configuration']['policy_id'],
                             scopes=scopes, counters=raw['counters'] if raw else None, work=verified.get(job['id']), unavailable=raw['unavailable'] if raw else ['missing profile'],
                             peak_rss_bytes=trial['peak_rss_bytes'] if trial else None,
                             process_ns=trial['elapsed_ns'] if trial else None,
                             residual_ns=trial['elapsed_ns'] - sum(r['exclusive_ns'] for r in raw['scopes']) if raw and trial else None))
    # Read-only accounting: reporting never repairs or appends to the campaign ledger.
    ledger_path = directory / 'ledger.jsonl'; ledger = checked_ledger(ledger_path, value)
    if len(ledger) < value['prior_events']:
        raise ValueError('ledger prefix missing')
    import hashlib
    prefix = b''.join(ledger_path.read_bytes().splitlines(keepends=True)[:value['prior_events']])
    if hashlib.sha256(prefix).hexdigest() != value['prior_ledger_sha256']:
        raise ValueError('historical ledger prefix changed')
    reserve = {e['trial_id']: e for e in ledger if e['kind'] == 'reserve'}
    settled = {e['trial_id']: e for e in ledger if e['kind'] in ('settle', 'recover')}
    admitted = [e['trial_id'] for e in ledger if e['kind'] == 'reserve' and any(e['trial_id'].startswith(value['id'] + '-' + k + '-') for k in ['timing', 'profile'])]
    if len(admitted) != len(set(admitted)) or set(admitted) != set(trials):
        raise ValueError('timing attempt coverage differs from ledger')
    for key, trial in trials.items():
        if key not in reserve or key not in settled:
            raise ValueError('trial lacks durable accounting')
        if reserve[key]['reserved_ns'] != 36 * 10**9 or reserve[key]['phase'] != value['categories'][trial['category']]['phase']:
            raise ValueError('trial reservation differs')
        if trial['leased_ns'] is not None and settled[key]['charged_ns'] != trial['leased_ns']:
            raise ValueError('worker lease charge differs')
    cumulative = sum(e['charged_ns'] for e in ledger if e['resource'] == 'gpu')
    phase = {name: sum(e['charged_ns'] for e in ledger if e['resource'] == 'gpu' and e['phase'] == name) for name in value['phase_gpu_seconds']}
    categories = {name: sum(e['charged_ns'] for e in ledger if e['resource'] == 'gpu' and e['trial_id'].startswith(value['id'] + '-' + name + '-')) for name in value['categories']}
    if cumulative > value['cumulative_gpu_ns'] or any(phase[k] > cap * 10**9 for k, cap in value['phase_gpu_seconds'].items()):
        raise ValueError('campaign/phase cap exceeded')
    if any(categories[k] > rule['seconds'] * 10**9 for k, rule in value['categories'].items()) or sum(categories.values()) > value['combined_cap_seconds'] * 10**9:
        raise ValueError('slice cap exceeded')
    budget = read_json(directory / 'budget.json')
    if budget['categories_ns'] != categories or budget['cumulative_ns'] != cumulative or budget['ledger_sha256'] != file_hash(ledger_path) or budget['events'] != len(ledger):
        raise ValueError('budget receipt differs from ledger')
    return dict(schema_version=1, id=value['id'], planned=len(schedule), attempted=len(trials), verified=len(verified),
                certified=len(certified), rows=rows, groups=groups, ratios=ratios, verification=verified,
                profiles=profiles, equivalence=equivalence, budget=dict(budget, phases_ns=phase, ceiling_ns=value['cumulative_gpu_ns']),
                analysis_elapsed_ns=time.monotonic_ns() - started,
                limitations=['Three development repetitions; no preset or universal speed claim.',
                             'Verification does not promote timeouts, work limits or numerical rejection.',
                             'All historical COPT attempts and coverage gaps remain unchanged.',
                             'Historical tuned_cases racecheck and large-session gaps remain open.'])


SETUP_SCOPES = ['device_discovery', 'device_context', 'driver_library_load', 'driver_symbol_resolution',
    'driver_initialization', 'device_lookup', 'context_create_api', 'context_identity_check',
    'code_image_read', 'code_image_hash', 'module_load', 'module_image_preparation', 'module_load_api',
    'kernel_lookup', 'stream_creation', 'device_allocation', 'device_free', 'stream_teardown',
    'module_unload', 'context_teardown', 'primary_preconditions', 'primary_symbol_resolution', 'primary_retain_api',
    'primary_make_current', 'primary_detach_api', 'primary_release_api', 'primary_cleanup_check']


def control_attribution(directory, value):
    from lp_cost import validate_profile
    profiles = []
    for job in jobs(value):
        if job['mode'] != 'profile' or job['configuration']['variant'] != 'baseline': continue
        key = job['id']; trial = validate_trial(read_json(directory / (key + '.trial.json')))
        if trial['status'] != 'completed': raise ValueError('control profile did not complete: ' + key)
        check_trial_artifacts(directory, trial)
        verify_both(value, job, directory, trial['provenance'])
        check_setup(directory / (key + '.setup.json'), directory / (key + '.endpoint.json'), 'user', value['device'])
        raw = read_json(checked_reference(directory, trial['cost'])); validate_profile(raw)
        phases = {name: sum(r['exclusive_ns'] for r in raw['scopes'] if r['path'][-1] == name) for name in SETUP_SCOPES}
        lifecycle = phases['context_create_api'] + phases['context_teardown']
        wall = trial['elapsed_ns']; setup = sum(phases.values())
        profiles.append(dict(id=key, trial_sha256=file_hash(directory / (key + '.trial.json')), phases_ns=phases,
            process_ns=wall, lifecycle_ns=lifecycle, setup_ns=setup, lifecycle_fraction=lifecycle / wall,
            ideal_lifecycle_elimination_bound=wall / (wall - lifecycle)))
    if len(profiles) != 4: raise ValueError('four prior profiles required')
    result = dict(status='passed', profiles=profiles, control_execution_sha256=file_hash(directory / 'baseline-execution.json'),
                  note='Historical user-context attribution, completed before implementing the primary candidate; zero lifecycle cost is only an upper-bound assumption.')
    path = directory / 'control-attribution.json'
    if path.exists() and read_json(path) != result: raise ValueError('control attribution is immutable')
    if not path.exists(): write_json(path, result)
    print(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol', type=Path, default=CONFIG)
    parser.add_argument('--control-attribution', action='store_true')
    args = parser.parse_args(); value = protocol(args.protocol); directory = ROOT / value['output']
    if args.control_attribution:
        control_attribution(directory, value); return
    result = report(directory, value, args.protocol)
    write_json(directory / 'report.json', result)
    print(f'{result["attempted"]}/{result["planned"]} attempts; {result["verified"]} verified; {result["certified"]} certified timings')


if __name__ == '__main__':
    main()
