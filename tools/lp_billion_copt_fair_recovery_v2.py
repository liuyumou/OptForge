"""Seal retained strict proofs without regrading refused audits; resume untouched LPs."""
import argparse
import json
import math
import time
from lp_billion_common import BASE, ROOT, NS, CPU_CAPS, GPU_CAPS, load, put, ref, resolve, require
from lp_billion_budget import accounting, run
from lp_billion_prepare_continue import job, completed
from lp_confirmation2_supervisor import same_process
from lp_billion_copt_fair_run import PYTHON
from lp_billion_copt_fair_policy import FAMILIES, timely, pair
from lp_billion_copt_fair_recovery import CELL, FAILED, REPAIR, MANIFEST, IDLE, GPU, prior_proofs, observation

CPU = 'operational-cpu-v32'
SEAL = 'copt-fair-tall-proof-seal-v1'
PLAN = BASE / 'copt-fair-untouched-tail-v2/plan.json'
PROTOCOL = ROOT / 'docs/specifications/SPEC-0046-amendment-84.md'


def identities(value):
    found = {}
    def collect(v):
        if isinstance(v, dict):
            if 'pid' in v and 'start_ticks' in v: found[(v['pid'], v['start_ticks'])] = v
            for child in v.values(): collect(child)
        elif isinstance(v, list):
            for child in v: collect(child)
    collect(value)
    return list(found.values())


def validate_seal(response, requests, first, second, stored, model_hash):
    _, mapping, endpoints = prior_proofs(response, requests, first, model_hash)
    require(len(second) == 1 and stored['results'] == first + second, 'exact retained supplemental proof output')
    require(stored['proof_mapping'] == mapping and stored['checks'] == 2 and stored['covered_endpoints'] == len(mapping), 'complete retained proof coverage')
    require(stored['final_check_ns'] is None and not stored['final_proof_timing_available'] and not stored['timing_eligible'], 'lost timing remains unavailable')
    from lp_billion_full_audit import validate
    from lp_billion_full_audit_v2 import certification_status
    accepted = validate(first + second, mapping, endpoints, model_hash, True)
    require(stored['strict_endpoint_accepted'] == accepted and stored['certified'] == certification_status(response, True, accepted), 'exact strict outcome')
    return accepted


def plan():
    require(not PLAN.exists(), 'fresh seal continuation plan')
    previous_path = BASE / 'copt-fair-untouched-tail-v1/plan.json'; previous = load(previous_path)
    resolve(previous['source']); resolve(previous['freeze'])
    failed = BASE / 'resources' / (REPAIR + '.settlement.json'); settlement = load(failed)
    require(settlement['status'] == 'refused' and settlement['cleanup_empty'] and not settlement['overrun'], 'retained supplemental finalization failure')
    owned = identities(load(resolve(settlement['resource']))) + load(resolve(previous['cleanup']))['identities']
    require(owned and not any(same_process(v) for v in owned), 'all retained owned identities gone')
    frozen = load(MANIFEST)
    todo = [c for c in frozen['cells'] if c['status'] == 'pending' and not (BASE / 'resources' / (c['id'] + '.reservation.json')).exists()]
    require([c['id'] for c in todo] == previous['never_started'], 'unchanged seven untouched LP cells')
    cpu, gpu = accounting()
    reserved = dict(admission=1200, development=4 * (sum(c['seconds'] for c in todo) + 1800),
                    reporting=4 * (60 + 480 + sum(c['audit_seconds'] for c in todo) + 600), cleanup=480)
    require(all(cpu[k] + v * NS <= CPU_CAPS[k] * NS for k, v in reserved.items()), 'complete remaining CPU reservation')
    require(gpu['admission'] + 120 * NS <= GPU_CAPS['admission'] * NS and gpu['development'] + sum(c['seconds'] for c in todo) * NS <= GPU_CAPS['development'] * NS, 'complete remaining GPU reservation')
    operational = BASE / 'operational-readmissions/v63.json'; require(not operational.exists(), 'fresh operational plan')
    put(operational, dict(status='prospective', cleanup_disposition=previous['cleanup'], admission_job=GPU, cpu_admission_job=CPU,
                          protocol=ref(PROTOCOL), previous_plan=previous['operational_plan'], availability_window_seconds=300))
    put(PLAN, dict(status='frozen_untouched_tail', source=ref(__file__), freeze=ref(MANIFEST), protocol=ref(PROTOCOL),
                   previous_plan=ref(previous_path), cleanup=previous['cleanup'], operational_plan=ref(operational),
                   failed_supplemental=ref(failed), retained_result=ref(BASE / REPAIR / 'result.json'),
                   never_started=previous['never_started'], cpu_reserve_seconds=reserved, proof_seal=SEAL,
                   final_proof_timing_excluded=True, lp_solves_repeated=False))
    print(dict(owned_identities_gone=len(owned), untouched=len(todo), reservations=reserved), flush=True)


def seal():
    started = time.monotonic_ns(); bound = load(PLAN); resolve(bound['source']); resolve(bound['freeze'])
    previous = load(resolve(bound['previous_plan'])); resolve(previous['source'])
    response = load(resolve(previous['response'])); requests = load(resolve(previous['retained_requests']))
    first = [json.loads(line) for line in resolve(previous['retained_proofs']).read_text().splitlines()]
    second_path = BASE / REPAIR / 'stdout.jsonl'; second = [json.loads(line) for line in second_path.read_text().splitlines()]
    stored = load(resolve(bound['retained_result'])); frozen = load(MANIFEST); cell = next(c for c in frozen['cells'] if c['id'] == CELL)
    require(stored['response'] == previous['response'] and stored['original_requests'] == previous['retained_requests']
            and stored['original_proofs'] == previous['retained_proofs'] and stored['original_audit'] == previous['failed_audit']
            and stored['plan'] == bound['previous_plan'] and stored['source'] == previous['source'], 'complete retained source and endpoint bindings')
    require(stored['checker'] == frozen['checker'] and stored['model'] == cell['model'], 'original checker and model identity')
    for item in [stored['checker'], stored['model'], stored['source']]: resolve(item)
    reservation = load(BASE / 'resources' / (REPAIR + '.reservation.json')); snapshot = load(resolve(reservation['source_manifest']))
    originals = [p for p in snapshot['sources'] if p['original'] == stored['source']]
    require(len(originals) == 1, 'original supplemental source snapshot'); resolve(originals[0]['retained'])
    accepted = validate_seal(response, requests, first, second, stored, cell['model']['sha256'])
    owned = identities(load(resolve(load(resolve(bound['failed_supplemental']))['resource']))) + load(resolve(bound['cleanup']))['identities']
    require(not any(same_process(v) for v in owned), 'all retained owned identities gone')
    out = BASE / SEAL; out.mkdir(exist_ok=False)
    result = dict(stored, status='passed', kind='read_only_retained_proof_seal', source=ref(__file__),
                  retained_completed_proofs=2, newly_completed_proofs=0, numerical_evaluations=0,
                  supplemental_result=bound['retained_result'], failed_supplemental=bound['failed_supplemental'],
                  supplemental_raw_proofs=ref(second_path), original_source_snapshot=originals[0], continuation_plan=ref(PLAN),
                  owned_identities_checked=len(owned), all_owned_identities_gone=True, seal_elapsed_ns=time.monotonic_ns() - started)
    put(out / 'result.json', result)
    print(dict(strict_endpoint_accepted=accepted, distinct_proofs=2, assessment_claims=len(stored['proof_mapping']), numerical_evaluations=0), flush=True)


def prune_tall():
    from lp_billion_portable import arrays
    require(completed(SEAL), 'complete supplemental strict proof coverage')
    frozen = load(MANIFEST); cells = [c for c in frozen['cells'] if c['family'] == 'tall']; documents = []
    for c in cells:
        if c['id'] != CELL: require(completed(c['id'] + '-full-audit'), 'complete paired COPT audit')
        documents += [resolve(c['model'])]
        for suffix in ['response.json', 'check-request.json']:
            p = BASE / c['id'] / suffix
            if p.exists(): documents.append(p)
        p = BASE / (c['id'] + '-full-audit') / 'requests.json'
        if p.exists(): documents.append(p)
    for p in [BASE / 'models-1b-tall-v1/result.json', BASE / 'copt-fair-regenerated-1b-tall-v1/result.json']:
        documents.append(resolve(load(p)['construction']))
    documents.append(BASE / REPAIR / 'requests.json'); chunks = {}
    for p in set(documents):
        for array in arrays(load(p)):
            for chunk in array['chunks']:
                sha, size = chunk['sha256'], chunk['bytes']
                require(len(sha) == 64 and all(c in '0123456789abcdef' for c in sha), 'owned content object')
                require(sha not in chunks or chunks[sha] == size, 'consistent content size'); chunks[sha] = size
    deleted = []; root = BASE / 'objects'
    output = BASE / 'copt-fair-prune-1b-tall-recovered-v1.json'; require(not output.exists(), 'fresh recovered-family cleanup')
    for sha, size in chunks.items():
        if size < 8 * (1 << 20): continue
        path = root / (sha + '.bin')
        if not path.exists(): continue
        require(not path.is_symlink() and path.resolve().parent == root.resolve() and path.stat().st_size == size, 'exact audited owned object')
        path.unlink(); deleted.append(dict(sha256=sha, bytes=size))
    put(output, dict(status='completed_audited_large_objects_deleted', deleted=deleted, released_bytes=sum(c['bytes'] for c in deleted),
                     manifest=ref(MANIFEST), supplemental_audit=ref(BASE / SEAL / 'result.json'), source=ref(__file__),
                     replay_requires_regeneration=True, small_results_and_failures_preserved=True))


def recovered_record(cell):
    require(completed(CELL) and completed(SEAL), 'settled solve and supplemental strict proof coverage')
    response_ref = ref(BASE / CELL / 'response.json'); response = load(resolve(response_ref)); measured = load(BASE / CELL / 'result.json')
    audit_ref = ref(BASE / SEAL / 'result.json'); proof = load(resolve(audit_ref))
    from lp_billion_full_report import validate_audit_binding
    validate_audit_binding(response_ref, cell['model'], ref(BASE / 'image-v1/executor'), response, proof, True)
    require(measured['response'] == response_ref and proof['original_audit'] == ref(BASE / 'resources' / (FAILED + '.settlement.json')), 'original solve and failed audit binding')
    from lp_billion_timing import process_ledger
    ledger = process_ledger(response, measured, 0); del ledger['exclusive_ns']['independent_final_check']
    require(sum(ledger['exclusive_ns'].values()) == ledger['total_ns'] == measured['fresh_process_ns'], 'observed process-only cost coverage')
    return dict(id=CELL, family=cell['family'], lane=cell['lane'], status=response['status'], capacity=cell['memory'],
                response=response_ref, settlement=ref(BASE / 'resources' / (CELL + '.settlement.json')),
                audit=audit_ref, audit_settlement=ref(BASE / 'resources' / (SEAL + '.settlement.json')),
                supplemental_failed_audit=ref(BASE / 'resources' / (REPAIR + '.settlement.json')),
                interrupted_audit=proof['original_audit'], supplemental_cleanup=ref(BASE / 'resources' / (FAILED + '.cleanup-disposition.json')),
                certified=proof['certified'], strict_endpoint_accepted=proof['strict_endpoint_accepted'], timing_eligible=False,
                timing_exclusion_reason='interrupted original audit did not retain cold final-proof timing',
                solver_returned_within_allowance=response['elapsed_ns'] <= cell['wall_seconds'] * NS,
                logical=response['logical'], physical=response['physical'], accepted=response['accepted'],
                accepted_product_work=response['accepted_product_work'], accepted_fp4_share=response['accepted_product_work'][1] / response['accepted_product_work'][3],
                solver_wall_ns=response['elapsed_ns'], original_input_validation_and_transpose_ns=response['input_ns'],
                solver_profile=response['solver_profile'], fresh_process_ns=measured['fresh_process_ns'], process_ns=measured['process_ns'],
                response_transport_ns=measured['response_transport_ns'], observed_process_cost_ledger=ledger,
                final_check_ns=None, offline_audit_ns=None, recovery_verification_ns=proof['recovery_verification_ns'])


def report():
    require((MANIFEST.parent / 'completed.json').exists(), 'complete original roster including recovered proof coverage')
    from lp_billion_full_report import record
    frozen = load(MANIFEST); rows = []
    for c in frozen['cells']:
        row = recovered_record(c) if c['id'] == CELL else record(c); row['timely_strict_certificate'] = False
        if row.get('response'):
            response = load(resolve(row['response'])); row['timely_strict_certificate'] = timely(row, response, c['wall_seconds'])
            row['requested_solver_wall_ns'] = int(c['wall_seconds'] * NS); row['requested_wall_exceeded'] = row['solver_wall_ns'] > row['requested_solver_wall_ns']
            row['iteration_safety_limit'] = 10000 if c['lane'] == 'fp4x2' else None
            row['iteration_limit_reached'] = response.get('logical', 0) >= 10000 if c['lane'] == 'fp4x2' else None
            if c['lane'] != 'fp4x2': row.update(phase_journal=response['phase_journal'], interrupts=response['interrupts'])
        rows.append(row)
    comparisons = [pair(next(r for r in rows if r['family'] == f and r['lane'] == 'fp4x2'), next(r for r in rows if r['family'] == f and r['lane'] == 'copt-gpu-pdlp')) for f in FAMILIES]
    path = BASE / 'copt-fair-results-v1.json'; require(not path.exists(), 'fresh complete recovered report')
    put(path, dict(status='all_fair_comparison_outcomes_retained', cells=rows, comparisons=comparisons, freeze=ref(MANIFEST),
                   source=ref(__file__), recovery=ref(PLAN), strict_original_tolerance=1e-9,
                   limitations=['One rotated pair per family; no broad superiority claim.',
                                'Tall project proof coverage is complete; original cold-proof timing is unavailable and excluded.',
                                'Every interruption, full failure charge, deadline and capacity refusal remains visible.']))
    from lp_billion_copt_fair_report import main
    main()


def execute():
    bound = load(PLAN); resolve(bound['source']); resolve(bound['freeze'])
    require(not (PLAN.parent / 'completed.json').exists(), 'never repeat completed continuation')
    command = load(BASE / 'resources/operational-cpu-v30.reservation.json')['command']
    job(CPU, 180, command, phase='admission')
    job(SEAL, 60, [str(PYTHON), '-B', str(ROOT / 'tools/lp_mixed2_reuse_place.py'), str(PYTHON), '-B', __file__, 'seal'], phase='reporting', host=8)
    job(IDLE, 480, [str(PYTHON), '-B', str(ROOT / 'tools/lp_mixed2_reuse_place.py'), str(PYTHON), '-B', __file__, 'observation'], phase='reporting', host=8)
    require(load(BASE / IDLE / 'result.json')['status'] == 'observed_idle', 'fresh complete idle window')
    from lp_billion_availability import observe, proof
    observe(GPU); proof(GPU)
    job(GPU, 120, ['python3', '-B', str(ROOT / 'tools/lp_billion_admit.py'), 'gpu', '--id', GPU, '--version', '2'], gpu=True)
    frozen = load(MANIFEST)
    for family in ['tall', 'coupled_blocks', 'ill_scaled', 'degenerate']:
        if family != 'tall':
            job('copt-fair-regenerate-1b-' + family + '-v1', 600, [str(PYTHON), '-B', str(ROOT / 'tools/lp_billion_copt_fair_run.py'), 'regenerate', '--scale', '1b', '--family', family], phase='development', host=32, disk=40)
        for index, cell in enumerate(frozen['cells']):
            if cell['family'] != family or cell['id'] not in bound['never_started']: continue
            require(not (BASE / 'resources' / (cell['id'] + '.reservation.json')).exists(), 'never repeat attempted LP solve')
            memory = cell['memory']; disk = cell.get('disk_gib', math.ceil(memory.get('endpoint_bytes_upper', 0) / (1 << 30)) + 1)
            s = run(cell['id'], 'development', cell['seconds'], True, [str(PYTHON), '-B', str(resolve(frozen['source'])), 'worker', '--manifest', str(MANIFEST), '--index', str(index)], memory['host_gib'], memory['device_gib'], disk)
            print(dict(cell=cell['id'], settlement=s), flush=True); require(s['cleanup_empty'] and not s['overrun'], 'cleanup or overrun stops tail')
            name = cell['id'] + '-full-audit'; require(not (BASE / 'resources' / (name + '.reservation.json')).exists(), 'fresh strict audit')
            s = run(name, 'reporting', cell['audit_seconds'], False, [str(PYTHON), '-B', str(resolve(frozen['audit'])), str(MANIFEST), str(index)], 64, 0, math.ceil(8 * load(resolve(cell['model_result']))['rows'] / (1 << 30)) + 1)
            print(dict(audit=name, settlement=s), flush=True); require(s['status'] == 'passed', 'full independent proof coverage')
        if family == 'tall':
            job('copt-fair-prune-1b-tall-recovered-v1', 30, [str(PYTHON), '-B', str(ROOT / 'tools/lp_mixed2_reuse_place.py'), str(PYTHON), '-B', __file__, 'prune_tall'], phase='cleanup', host=8)
        else:
            job('copt-fair-prune-1b-' + family + '-v1', 30, [str(PYTHON), '-B', str(ROOT / 'tools/lp_mixed2_reuse_place.py'), str(PYTHON), '-B', str(ROOT / 'tools/lp_billion_copt_fair_run.py'), 'cleanup', '--scale', '1b', '--family', family], phase='cleanup', host=8)
    put(MANIFEST.parent / 'completed.json', dict(status='all_admitted_cells_attempted_and_audited', freeze=ref(MANIFEST), recovery=ref(PLAN)))
    put(PLAN.parent / 'completed.json', dict(status='complete', plan=ref(PLAN)))
    job('copt-fair-complete-report-v1', 120, [str(PYTHON), '-B', str(ROOT / 'tools/lp_mixed2_reuse_place.py'), str(PYTHON), '-B', __file__, 'report'], phase='reporting', host=8)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['plan', 'seal', 'observation', 'execute', 'prune_tall', 'report'])
    args = parser.parse_args(); globals()[args.action]()
