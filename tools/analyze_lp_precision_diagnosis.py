"""Read-only analysis of ADR-0020 diagnostics and preserved GPUP-5 evidence."""
import argparse
from collections import defaultdict
from fractions import Fraction as F
import json
from pathlib import Path
import sqlite3
import statistics
import subprocess
from diagnose_lp_precision import OUTPUT, HISTORY, PRIOR_NS, PRIOR_EVENTS, CAP_NS, CONFIG, jobs, label, work_limit, check_prefix
from lp_protocol import ROOT, NS, file_hash, read_json, write_json, Ledger, strict_loads, validate, checked_reference
from lp_report import paired_ratio


def quantization_rows(model, operator, endpoint):
    """Exact row activities; represented feasibility is a diagnostic, never a certificate."""
    primal = {v['variable_id']: F(v['value']) for v in endpoint['record']['candidate']['values']}
    ids = [v['id'] for v in sorted(model['variables'], key=lambda v: v['id'])]
    x = [primal[v] for v in ids]
    rows = sorted(model['constraints'], key=lambda r: r['id'])
    dr = list(map(F, operator['row_scale']))
    dc = list(map(F, operator['column_scale']))
    activity = [[F(0), F(0), F(0)] for _ in rows]
    for row, col, original, scaled, represented in operator['entries']:
        activity[row][0] += F(original) * x[col]
        activity[row][1] += F(scaled) * x[col] / (dr[row] * dc[col])
        activity[row][2] += F(represented) * x[col] / (dr[row] * dc[col])
    observed = {r['constraint_id']: r for r in endpoint['record']['validation']['constraints']}
    output = []
    for row, (original, scaled, represented) in zip(rows, activity):
        checks = []
        for side in ['lower', 'upper']:
            bound = row[side]
            if bound['kind'] != 'finite':
                continue
            exact = F(bound['value'])
            def violation(a):
                return max(F(0), exact-a if side == 'lower' else a-exact)
            allowance = observed[row['id']][side]['allowance']
            checks.append(dict(side=side, original_violation=float(violation(original)),
                               scaled_fp64_violation=float(violation(scaled)),
                               represented_violation=float(violation(represented)), allowance=allowance,
                               original_rejected=violation(original) > F(allowance),
                               represented_rejected=violation(represented) > F(allowance)))
        output.append(dict(row_id=row['id'], original_activity=float(original),
                           scaled_fp64_activity=float(scaled), represented_activity=float(represented),
                           matrix_shift=float(represented-original), checks=checks))
    return output


def cpu(directory):
    directory.mkdir(parents=True, exist_ok=True)
    manifest = read_json(ROOT / 'benchmarks/manifests/lp-development-v1.json')
    binary = ROOT / 'target/release/examples/lp_precision_diagnose'
    output = []
    for instance in manifest['instances']:
        model_path = ROOT / instance['model']['path']
        model = read_json(model_path)
        source = HISTORY / f'gpup5-fp32-v1-timing-{instance["id"]}-0-storage-fp32.endpoint.json'
        result = subprocess.run([str(binary), str(model_path), str(source)], capture_output=True, check=True, timeout=30)
        operator = strict_loads(result.stdout)
        if operator['model_sha256'] != instance['model']['sha256']:
            raise ValueError('operator model identity differs')
        write_json(directory / (instance['id'] + '.operator.json'), operator)
        for config in read_json(CONFIG)['configurations']:
            if 'precision' not in config:
                continue
            path = HISTORY / f'gpup5-fp32-v1-timing-{instance["id"]}-0-{config["id"]}.endpoint.json'
            endpoint = read_json(path)
            if endpoint['record']['candidate'] is None:
                continue
            rows = quantization_rows(model, operator, endpoint)
            checks = [b for row in rows for b in row['checks']]
            detail = dict(instance=instance['id'], config=config['id'], endpoint_sha256=file_hash(path),
                          endpoint_class=endpoint['assessment']['classification'], rows=rows)
            write_json(directory / (instance['id'] + '.' + config['id'] + '.rows.json'), detail)
            output.append({k: v for k, v in detail.items() if k != 'rows'} | dict(
                original_rejected_bounds=sum(b['original_rejected'] for b in checks),
                represented_rejected_bounds=sum(b['represented_rejected'] for b in checks),
                max_original_violation=max((b['original_violation'] for b in checks), default=0),
                max_represented_violation=max((b['represented_violation'] for b in checks), default=0),
                max_original_over_allowance=max((b['original_violation']/b['allowance'] for b in checks if b['allowance'] > 0), default=0),
                max_matrix_shift=max((abs(r['matrix_shift']) for r in rows), default=0)))
        print(instance['id'], 'representation checked', flush=True)
    write_json(directory / 'representation-summary.json', dict(kind='exact_rational_diagnostic_not_certificate',
               export_binary_sha256=file_hash(binary), rows=output))
    print(len(output), 'archived endpoint representation diagnostics')


def trace(path, expected_launches):
    connection = sqlite3.connect('file:' + str(path) + '?mode=ro', uri=True)
    try:
        apis = connection.execute('select s.value,count(*),sum(a.end-a.start) from CUPTI_ACTIVITY_KIND_RUNTIME a join StringIds s on s.id=a.nameId group by s.value').fetchall()
        kernels = connection.execute('select s.value,count(*),sum(k.end-k.start),min(k.end-k.start),max(k.end-k.start),k.gridX,k.blockX,k.registersPerThread from CUPTI_ACTIVITY_KIND_KERNEL k join StringIds s on s.id=k.shortName group by s.value').fetchall()
        count, busy, span = connection.execute('select count(*),sum(end-start),max(end)-min(start) from CUPTI_ACTIVITY_KIND_KERNEL').fetchone()
        copies = connection.execute('select copyKind,count(*),sum(bytes),sum(end-start) from CUPTI_ACTIVITY_KIND_MEMCPY group by copyKind').fetchall()
    finally:
        connection.close()
    if count != expected_launches or next((r[1] for r in apis if r[0] == 'cuLaunchKernel'), 0) != count:
        raise ValueError('CUDA trace/endpoint launch counts differ')
    return dict(launches=count, kernel_busy_ns=busy, kernel_span_ns=span,
                gap_fraction=1-busy/span, apis=apis, kernels=kernels, copies=copies,
                copy_ns=sum(r[3] for r in copies))


def iteration_execution(phases):
    # Tuned records dynamic uploads/readbacks outside its kernel phase; precision
    # includes them inside advance. Compare the same envelope, excluding correction.
    return sum(phases.get(k, 0) for k in ['kernels_and_synchronization',
                                        'working_allocation', 'working_upload', 'readback'])


def short_eligible(row):
    # Deliberately limiting a diagnostic solve normally returns CLI exit 1.
    expected = {'optimal': 0, 'iteration_limit': 1}.get(row['termination'])
    return (row['kind'] == 'short' and row['equal_work'] and row['verified']
            and row['worker']['reason'] == 'completed' and expected is not None
            and row['worker']['returncode'] == expected)


def counter_status(path):
    raw = path.read_text()
    return dict(available=False, status='permission_denied' if 'ERR_NVGPUCTRPERM' in raw
                else 'unavailable_or_unparsed', raw_sha256=file_hash(path))


def analyze(directory):
    protocol = read_json(directory / 'diagnostic-protocol.json')
    value = read_json(CONFIG)
    schedule = list(jobs(value))
    if protocol['jobs'] != json.loads(json.dumps(schedule)) or protocol['source_campaign_sha256'] != file_hash(CONFIG):
        raise ValueError('diagnostic schedule/provenance changed')
    if protocol['history_index_sha256'] != file_hash(HISTORY / 'artifact-index.json'):
        raise ValueError('historical artifact index changed')
    for item in read_json(HISTORY / 'artifact-index.json'):
        if file_hash(HISTORY / item['path']) != item['sha256']:
            raise ValueError('historical artifact changed: ' + item['path'])
    check_prefix(directory / 'ledger.jsonl')
    events = [strict_loads(line) for line in (directory / 'ledger.jsonl').read_bytes().splitlines()]
    authority = checked_reference(ROOT, value['budget_authority'])
    canonical = ROOT / 'artifacts/lp-campaign-ledgers' / read_json(authority)['id'] / 'ledger.jsonl'
    snapshot = (directory / 'ledger.jsonl').read_bytes()
    if not snapshot.endswith(b'\n') or not canonical.read_bytes().startswith(snapshot):
        raise ValueError('diagnostic ledger is not an intact canonical prefix')
    ledger = Ledger(directory, file_hash(authority))
    for index, event in enumerate(events):
        validate('ledger', event)
        if event['sequence'] != index or event['campaign_sha256'] != file_hash(authority):
            raise ValueError('diagnostic ledger identity/sequence mismatch')
    ledger.events = events
    if ledger.pending() or ledger.totals()-PRIOR_NS > CAP_NS:
        raise ValueError('unsettled/excess diagnostic budget')
    groups = defaultdict(list)
    rows = []
    missing = []
    for job in schedule:
        key = label(job)
        path = directory / (key + '.result.json')
        if not path.exists():
            missing.append(key)
            continue
        result = read_json(path)
        kind, name, config, repetition = job
        if (result['id'], result['kind'], result['instance'], result['config'], result['repetition']) != (
                'gpup5-diagnosis-v1-' + key, kind, name, config, repetition):
            raise ValueError('diagnostic result differs from frozen job')
        model = ROOT / f'artifacts/lp-inputs-v1/gpup-development-{name}.json'
        if result['model_sha256'] != file_hash(model):
            raise ValueError('diagnostic model changed')
        expected_solve = {**value['solve'], 'iteration_limit': work_limit(config)}
        expected_method = {**value['lp_settings'], 'iteration_limit': work_limit(config)}
        if result['solve'] != expected_solve or result['method'] != expected_method:
            raise ValueError('diagnostic method/solve settings changed')
        charges = [e['charged_ns'] for e in events[PRIOR_EVENTS:] if e['trial_id'] == result['id'] and e['kind'] == 'settle']
        if charges != [result['charged_ns']]:
            raise ValueError('diagnostic charge mismatch')
        row = dict(label=key, kind=kind, instance=name, config=config['id'], repetition=repetition,
                   worker=result['worker'], verified=result['endpoint_verified'])
        if kind == 'counter':
            row['counter'] = counter_status(directory / (key + '.ncu.csv'))
        endpoint_path = directory / (key + '.endpoint.json')
        if result['endpoint_verified'] and not endpoint_path.exists():
            raise ValueError('verified diagnostic endpoint is missing')
        if endpoint_path.exists():
            if not result['endpoint_verified'] or file_hash(endpoint_path) != result['endpoint_sha256']:
                raise ValueError('altered/unverified endpoint')
            endpoint = validate('endpoint', read_json(endpoint_path))
            if endpoint['record']['options'] != result['solve'] or endpoint['record']['lp_settings'] != result['method']:
                raise ValueError('recorded short limits differ')
            identity = value['precision_code_object_sha256'] if 'precision' in config else value['code_object_sha256']
            if endpoint['execution']['settings'] != config['execution'] or endpoint['execution']['code_object_sha256'] != identity:
                raise ValueError('diagnostic execution/code object differs')
            if endpoint['record']['backend'] != 'cuda-lp-tuned' or endpoint['model_sha256'] != result['model_sha256']:
                raise ValueError('diagnostic endpoint backend/model differs')
            precision = endpoint.get('precision')
            if (precision or {}).get('settings') != job[2].get('precision'):
                raise ValueError('recorded precision differs')
            control = endpoint['control']
            proposed = precision['proposed_steps'] if precision else control['logical_iterations']
            row.update(termination=endpoint['record']['termination'], endpoint_class=endpoint['assessment']['classification'], proposed=proposed,
                       physical=control['physical_iterations'], execution=endpoint['execution'],
                       precision=precision, phases_ns=endpoint['diagnostics']['phases_ns'],
                       equal_work=proposed == 200 and control['physical_iterations'] == work_limit(job[2]))
            row['iteration_execution_ns'] = iteration_execution(row['phases_ns'])
            row['execution_and_correction_ns'] = row['iteration_execution_ns'] + row['phases_ns'].get('fp64_correction', 0)
            if job[0] == 'trace':
                row['trace'] = trace(directory / (key + '.sqlite'), endpoint['diagnostics']['kernel_launches'])
            if short_eligible(row):
                groups[job[1], job[2]['id']].append(row)
        rows.append(row)
    grouped = []
    for (instance, config), observed in groups.items():
        phases = {k for r in observed for k in r['phases_ns']}
        times = [r['phases_ns']['kernels_and_synchronization'] for r in observed]
        grouped.append(dict(instance=instance, config=config, repetitions=len(observed),
                            median_process_ns=statistics.median(r['worker']['elapsed_ns'] for r in observed),
                            median_iteration_execution_ns=statistics.median(r['iteration_execution_ns'] for r in observed),
                            median_execution_and_correction_ns=statistics.median(r['execution_and_correction_ns'] for r in observed),
                            median_kernel_phase_ns=statistics.median(times), min_kernel_phase_ns=min(times), max_kernel_phase_ns=max(times),
                            median_phases_ns={k:statistics.median(r['phases_ns'].get(k,0) for r in observed) for k in phases}))
    ratios = []
    for (instance, config), observed in groups.items():
        baseline = {r['repetition']:r for r in groups.get((instance, 'precision-fp64'), [])}
        pairs = [(baseline[r['repetition']]['iteration_execution_ns'], r['iteration_execution_ns'])
                 for r in observed if r['repetition'] in baseline]
        ratios.append(dict(instance=instance, candidate=config, reference='precision-fp64',
                           scope='iteration_execution_excluding_correction',
                           statistics=paired_ratio(pairs, value['analysis']['seed'], value['analysis']['resamples'])))
    summary = dict(schema_version=1, kind='diagnosis_not_baseline', planned=len(schedule), observed=len(rows), missing=missing,
                   groups=grouped, paired_ratios=ratios, jobs=rows, additional_gpu_ns=ledger.totals()-PRIOR_NS,
                   cumulative_gpu_ns=ledger.totals(), ledger_sha256=file_hash(directory / 'ledger.jsonl'))
    write_json(directory / 'diagnosis.json', summary)
    write_json(directory / 'artifact-hashes.json', {p.name:file_hash(p) for p in sorted(directory.iterdir())
                                                   if p.is_file() and p.name != 'artifact-hashes.json'})
    print(len(rows), 'retained diagnostics;', len(missing), 'missing;', (ledger.totals()-PRIOR_NS)/NS, 'additional GPU seconds')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cpu', action='store_true')
    parser.add_argument('--directory', type=Path, default=OUTPUT)
    args = parser.parse_args()
    (cpu if args.cpu else analyze)(args.directory)
