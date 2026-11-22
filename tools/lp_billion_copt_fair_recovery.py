"""Complete retained proof coverage, then execute only untouched frozen LP cells."""
import argparse
import json
import math
import select
import subprocess
import time
from lp_billion_common import BASE, ROOT, NS, CPU_CAPS, GPU_CAPS, load, put, ref, resolve, require
from lp_billion_budget import accounting, run
from lp_billion_prepare_continue import job, completed
from lp_confirmation2_supervisor import same_process
from lp_billion_copt_fair_run import PYTHON, AUDIT
from lp_billion_copt_fair_policy import FAMILIES, timely, pair

CELL = 'copt-fair-1b-v1-tall-project'
FAILED = CELL + '-full-audit'
REPAIR = 'copt-fair-tall-audit-completion-v1'
CPU, GPU = 'operational-cpu-v31', 'operational-gpu-v25'
MANIFEST = BASE / 'copt-fair-1b-v1/freeze.json'
PLAN = BASE / 'copt-fair-untouched-tail-v1/plan.json'
PROTOCOL = ROOT / 'docs/specifications/SPEC-0046-amendment-83.md'
IDLE = 'copt-fair-tail-idle-v1'


def prior_proofs(response, retained_requests, retained_proofs, model_hash):
    from lp_billion_full_audit import requests
    queries, mapping, endpoints = requests(response, True)
    require(retained_requests == dict(requests=queries, mapping=mapping), 'exact interrupted request binding')
    require(len(queries) == 2 and len(retained_proofs) == 1, 'one completed and one missing distinct proof')
    for index, endpoint in zip(mapping, endpoints):
        if index >= len(retained_proofs): continue
        proof = retained_proofs[index]
        require(proof['model_sha256'] == model_hash and proof['tolerance'] == 1e-9, 'retained original-model proof')
        require(all(proof[k] == v for k, v in endpoint['certificate'].items()), 'retained proof matches exact assessment')
    return queries, mapping, endpoints


def plan():
    require(not PLAN.exists(), 'fresh untouched-tail plan')
    receipt = BASE / 'resources' / (FAILED + '.settlement.json'); settled = load(receipt)
    require(settled['status'] == 'refused' and not settled['cleanup_empty'] and not settled['overrun'], 'exact non-overrun audit failure')
    resource = load(resolve(settled['resource'])); journal = BASE / 'resources' / (FAILED + '.cpu-journal.json')
    identities = {}
    def collect(value):
        if isinstance(value, dict):
            if 'pid' in value and 'start_ticks' in value: identities[(value['pid'], value['start_ticks'])] = value
            for child in value.values(): collect(child)
        elif isinstance(value, list):
            for child in value: collect(child)
    collect(resource); collect(load(journal))
    require(identities and not any(same_process(v) for v in identities.values()), 'all exact owned identities gone')
    disposition = BASE / 'resources' / (FAILED + '.cleanup-disposition.json')
    require(not disposition.exists(), 'fresh additive cleanup proof')
    put(disposition, dict(status='cleanup_verified', settlement=ref(receipt), resource=settled['resource'], journal=ref(journal),
                         identities=list(identities.values()), signals_sent=False, admission_job=GPU, cpu_admission_job=CPU,
                         protocol=ref(PROTOCOL), source=ref(__file__)))
    operational = BASE / 'operational-readmissions/v62.json'
    require(not operational.exists(), 'fresh operational plan')
    put(operational, dict(status='prospective', cleanup_disposition=ref(disposition), admission_job=GPU, cpu_admission_job=CPU,
                          protocol=ref(PROTOCOL), previous_plan=ref(BASE / 'operational-readmissions/v61.json'), availability_window_seconds=300))
    frozen = load(MANIFEST)
    todo = [c for c in frozen['cells'] if c['status'] == 'pending' and not (BASE / 'resources' / (c['id'] + '.reservation.json')).exists()]
    require([(c['family'], c['lane']) for c in todo] == [('tall', 'copt-gpu-pdlp'), ('coupled_blocks', 'copt-gpu-pdlp'),
            ('coupled_blocks', 'fp4x2'), ('ill_scaled', 'fp4x2'), ('ill_scaled', 'copt-gpu-pdlp'),
            ('degenerate', 'copt-gpu-pdlp'), ('degenerate', 'fp4x2')], 'exact seven untouched frozen cells')
    cpu, gpu = accounting()
    reservations = dict(admission=4 * (180 + 120), development=4 * (sum(c['seconds'] for c in todo) + 3 * 600),
                        reporting=4 * (600 + 480 + sum(c['audit_seconds'] for c in todo) + 600), cleanup=4 * 4 * 30)
    require(all(cpu[k] + v * NS <= CPU_CAPS[k] * NS for k, v in reservations.items()), 'whole remaining CPU reservation')
    require(gpu['admission'] + 120 * NS <= GPU_CAPS['admission'] * NS and
            gpu['development'] + sum(c['seconds'] for c in todo) * NS <= GPU_CAPS['development'] * NS, 'whole remaining GPU reservation')
    put(PLAN, dict(status='frozen_untouched_tail', freeze=ref(MANIFEST), source=ref(__file__), protocol=ref(PROTOCOL),
                   cleanup=ref(disposition), operational_plan=ref(operational), never_started=[c['id'] for c in todo],
                   failed_audit=ref(receipt), retained_requests=ref(BASE / FAILED / 'requests.json'),
                   retained_proofs=ref(BASE / FAILED / 'stdout.jsonl'), response=ref(BASE / CELL / 'response.json'),
                   cpu_reserve_seconds=reservations, supplemental_audit=REPAIR, audit_host_gib=64,
                   final_proof_timing_excluded=True, lp_solves_repeated=False))
    print(dict(identities_gone=len(identities), untouched=len(todo), reservations=reservations), flush=True)


def audit():
    bound = load(PLAN); resolve(bound['source']); resolve(bound['freeze'])
    response = load(resolve(bound['response'])); retained = [json.loads(line) for line in resolve(bound['retained_proofs']).read_text().splitlines()]
    frozen = load(MANIFEST); cell = next(c for c in frozen['cells'] if c['id'] == CELL)
    queries, mapping, endpoints = prior_proofs(response, load(resolve(bound['retained_requests'])), retained, cell['model']['sha256'])
    out = BASE / REPAIR; out.mkdir(exist_ok=False)
    put(out / 'requests.json', dict(requests=queries[1:], original_indices=[1], original_requests=bound['retained_requests']))
    checker = resolve(frozen['checker']); model = resolve(cell['model']); start = time.monotonic_ns()
    from lp_billion_owned_process import stop_owned
    with (out / 'stderr').open('w') as err, (out / 'stdout.jsonl').open('w') as raw:
        child = subprocess.Popen([str(checker), 'assess', str(model), str(BASE)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=err, text=True)
        try:
            child.stdin.write(json.dumps(queries[1], allow_nan=False) + '\n'); child.stdin.flush()
            require(select.select([child.stdout], [], [], 540)[0], 'supplemental proof deadline')
            line = child.stdout.readline(); require(bool(line), 'supplemental checker returned a proof')
            raw.write(line); raw.flush(); proof = json.loads(line)
            child.stdin.close()
            require(child.wait(timeout=10) == 0 and child.stdout.read() == '', 'supplemental checker completed')
        finally:
            stop_owned(child); child.stdout.close()
            if not child.stdin.closed: child.stdin.close()
    elapsed = time.monotonic_ns() - start
    from lp_billion_full_audit import validate
    from lp_billion_full_audit_v2 import certification_status
    results = retained + [proof]
    accepted = validate(results, mapping, endpoints, cell['model']['sha256'], True)
    certified = certification_status(response, True, accepted)
    put(out / 'result.json', dict(status='passed', response=bound['response'], model=cell['model'], checker=ref(checker),
                                  certified=certified, strict_endpoint_accepted=accepted, checks=len(results), covered_endpoints=len(mapping),
                                  proof_mapping=mapping, results=results, retained_completed_proofs=1, newly_completed_proofs=1,
                                  recovery_verification_ns=elapsed, final_check_ns=None, offline_audit_ns=None,
                                  original_audit=bound['failed_audit'], original_requests=bound['retained_requests'],
                                  original_proofs=bound['retained_proofs'], plan=ref(PLAN), source=ref(__file__),
                                  final_proof_timing_available=False, timing_eligible=False, lp_solves_repeated=False))
    print(dict(certified=certified, completed_proof_coverage=len(results), recovery_seconds=elapsed / NS), flush=True)


def observation():
    from lp_billion_availability import stable, idle
    from lp_billion_idle import Nvml
    out = BASE / IDLE; out.mkdir(exist_ok=False); samples = []; start = time.monotonic(); ready = False; sensor = Nvml()
    try:
        for i in range(8):
            target = start + i * 60
            while time.monotonic() < target: time.sleep(min(1, target - time.monotonic()))
            sample = sensor.sample(); path = BASE / 'availability' / GPU / (str(sample['start_ns']) + '.json'); put(path, sample); samples.append(ref(path))
            ready = stable([load(resolve(p)) for p in samples], time.monotonic_ns())
            print(dict(sample=i, idle=idle(sample), used_gib=sample['used'] / 2**30, ready=ready), flush=True)
            if ready: break
        put(out / 'result.json', dict(status='observed_idle' if ready else 'idle_gate_not_met', samples=samples, source=ref(__file__)))
    finally: sensor.close()


def prune_tall():
    from lp_billion_portable import arrays
    require(completed(REPAIR), 'complete supplemental strict proof coverage')
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
                     manifest=ref(MANIFEST), supplemental_audit=ref(BASE / REPAIR / 'result.json'), source=ref(__file__),
                     replay_requires_regeneration=True, small_results_and_failures_preserved=True))


def recovered_record(cell):
    require(completed(CELL) and completed(REPAIR), 'settled solve and supplemental strict proof coverage')
    response_ref = ref(BASE / CELL / 'response.json'); response = load(resolve(response_ref)); measured = load(BASE / CELL / 'result.json')
    audit_ref = ref(BASE / REPAIR / 'result.json'); proof = load(resolve(audit_ref))
    from lp_billion_full_report import validate_audit_binding
    validate_audit_binding(response_ref, cell['model'], ref(BASE / 'image-v1/executor'), response, proof, True)
    require(measured['response'] == response_ref and proof['original_audit'] == ref(BASE / 'resources' / (FAILED + '.settlement.json')), 'original solve and failed audit binding')
    from lp_billion_timing import process_ledger
    ledger = process_ledger(response, measured, 0); del ledger['exclusive_ns']['independent_final_check']
    require(sum(ledger['exclusive_ns'].values()) == ledger['total_ns'] == measured['fresh_process_ns'], 'observed process-only cost coverage')
    return dict(id=CELL, family=cell['family'], lane=cell['lane'], status=response['status'], capacity=cell['memory'],
                response=response_ref, settlement=ref(BASE / 'resources' / (CELL + '.settlement.json')),
                audit=audit_ref, audit_settlement=ref(BASE / 'resources' / (REPAIR + '.settlement.json')),
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
    job(REPAIR, 600, [str(PYTHON), '-B', __file__, 'audit'], phase='reporting', host=64)
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
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['plan', 'audit', 'observation', 'execute', 'prune_tall', 'report'])
    args = parser.parse_args(); globals()[args.action]()
