"""Prospective larger allowances and complete audit reserves for untouched LPs."""
import argparse
import copy
import math
import time
from lp_billion_common import BASE, ROOT, NS, CPU_CAPS, GPU_CAPS, DISK_LIMIT, disk_bytes, load, put, ref, resolve, require
from lp_billion_budget import accounting, run
from lp_billion_prepare_continue import completed, job
from lp_billion_readmission import CPU, GPU
from lp_billion_copt_fair_policy import FAMILIES, timely, pair
from lp_billion_copt_fair_run import PYTHON
from lp_billion_copt_fair_recovery_v2 import CELL, SEAL, recovered_record, prune_tall

ORIGINAL = BASE / 'copt-fair-1b-v1/freeze.json'
MANIFEST = BASE / 'copt-fair-budgeted-v1/freeze.json'
PROTOCOL = ROOT / 'docs/specifications/SPEC-0046-amendment-85.md'
CONTRACTS = 'copt-fair-budgeted-contracts-v2'
SOLVER_SECONDS, OUTER_SECONDS = 2100, 2700


def resized(cell):
    value = copy.deepcopy(cell)
    require(value['status'] == 'pending', 'only admitted untouched LP cells')
    value.update(seconds=OUTER_SECONDS, wall_seconds=float(SOLVER_SECONDS), common_solver_wall_seconds=SOLVER_SECONDS,
                 audit_host_gib=64, audit_seconds=900 if value['lane'] == 'copt-gpu-pdlp' else
                 dict(coupled_blocks=2800, ill_scaled=4600, degenerate=4600)[value['family']])
    if value['lane'] == 'fp4x2':
        require(value['request']['settings']['iteration_limit'] == 10000 and value['request']['settings']['tolerance'] == 1e-9,
                'unchanged project iteration and strict certificate criteria')
        value['request']['settings']['wall_ms'] = SOLVER_SECONDS * 1000
    return value


def worksheet(cells):
    require(len(cells) == 7 and all(c['seconds'] == 2700 and c['wall_seconds'] == 2100 for c in cells), 'seven prospectively bounded solves')
    audits = sum(c['audit_seconds'] for c in cells)
    require(audits == 15600, 'complete strict final/intermediate proof allowance')
    return dict(cpu=dict(admission=2400, development=4 * (sum(c['seconds'] for c in cells) + 3 * 600),
                         reporting=70000, cleanup=4 * 4 * 45), gpu=dict(admission=180, development=sum(c['seconds'] for c in cells)),
                audit_wall_seconds=audits, audit_cpu_seconds=4 * audits,
                reporting_components_cpu=dict(audits=4 * audits, idle_window=1920, report=720, verification=1920,
                                              additional_contingency=70000 - 4 * audits - 1920 - 720 - 1920))


def admit_envelope(cells):
    plan = worksheet(cells); cpu, gpu = accounting()
    require(all(cpu[k] + seconds * NS <= CPU_CAPS[k] * NS for k, seconds in plan['cpu'].items()), 'whole remaining CPU envelope')
    require(all(gpu[k] + seconds * NS <= GPU_CAPS[k] * NS for k, seconds in plan['gpu'].items()), 'whole remaining GPU envelope')
    return dict(plan, remaining_after_cpu_seconds={k: CPU_CAPS[k] - cpu[k] / NS - v for k, v in plan['cpu'].items()},
                remaining_after_gpu_seconds={k: GPU_CAPS[k] - gpu[k] / NS - v for k, v in plan['gpu'].items()})


def budgeted_pair(project, vendor):
    compared = pair(project, vendor)
    compared['same_requested_allowances'] = (project['requested_solver_wall_ns'], project['outer_reservation_seconds']) == (vendor['requested_solver_wall_ns'], vendor['outer_reservation_seconds'])
    if not compared['same_requested_allowances']: compared['copt_over_project_complete_ratio'] = None
    return compared


def freeze():
    require(completed(CPU) and completed(CONTRACTS) and completed(SEAL), 'fresh supervision/contracts and retained proof seal')
    require(not MANIFEST.exists(), 'fresh prospective effective manifest')
    original = load(ORIGINAL); previous = load(BASE / 'copt-fair-untouched-tail-v2/plan.json'); resolve(previous['source'])
    untouched = [c['id'] for c in original['cells'] if c['status'] == 'pending' and not (BASE / 'resources' / (c['id'] + '.reservation.json')).exists()]
    require(untouched == previous['never_started'] and len(untouched) == 7, 'exact seven never-attempted cells')
    effective = copy.deepcopy(original)
    effective['cells'] = [resized(c) if c['id'] in untouched else copy.deepcopy(c) for c in original['cells']]
    revised = [c for c in effective['cells'] if c['id'] in untouched]; envelope = admit_envelope(revised)
    for old, new in zip(original['cells'], effective['cells']):
        if old['id'] not in untouched: require(old == new, 'every historical outcome and refusal unchanged')
        else:
            require(new['model'] == old['model'] and new['memory'] == old['memory'], 'unchanged original input and solve memory bound')
            if old['lane'] == 'fp4x2':
                expected = copy.deepcopy(old['request']); expected['settings']['wall_ms'] = 2100000
                require(new['request'] == expected, 'only native wall allowance changes in the numerical request')
    for family in ['tall', 'coupled_blocks', 'ill_scaled', 'degenerate']:
        active = [c for c in revised if c['family'] == family]
        endpoint = sum(c.get('disk_gib', math.ceil(c['memory'].get('endpoint_bytes_upper', 0) / (1 << 30)) + 1) for c in active)
        require(disk_bytes() + (endpoint + 32) * (1 << 30) <= DISK_LIMIT, 'whole per-family input and endpoint storage')
    prior = load(BASE / 'gpu-control-settled-checkpoint-v1.json')
    for item in prior['numerical_bindings']: resolve(item)
    effective.update(status='frozen_effective_comparison_with_prospective_tail', common_solver_wall_seconds=None,
                     common_outer_process_seconds=None, original_freeze=ref(ORIGINAL), resumption_source=ref(__file__),
                     time_budget_protocol=ref(PROTOCOL), readmission_protocol=ref(ROOT / 'docs/specifications/SPEC-0046-amendment-86.md'),
                     budget_envelope=ref(BASE / 'copt-fair-budget-envelope-v2.json'), reservation=envelope, untouched=untouched,
                     cpu_admission=ref(BASE / 'resources' / (CPU + '.settlement.json')), contracts=ref(BASE / 'resources' / (CONTRACTS + '.settlement.json')),
                     allowance_cohorts=[dict(name='historical', wall_seconds=1200, outer_seconds=1800,
                                             ids=[c['id'] for c in original['cells'] if c['id'] not in untouched]),
                                        dict(name='resumed', wall_seconds=2100, outer_seconds=2700, ids=untouched)])
    put(MANIFEST, effective)
    print(dict(untouched=len(untouched), reservation=envelope), flush=True)


def observation(identity):
    from lp_billion_availability import observe, stable
    require(identity.startswith('copt-fair-budget-idle-') and '/' not in identity, 'fresh availability identity')
    out = BASE / identity; out.mkdir(exist_ok=False); start = time.monotonic(); ready = False
    for index in range(8):
        target = start + index * 60
        while time.monotonic() < target: time.sleep(min(1, target - time.monotonic()))
        observe(GPU)
        paths = sorted((BASE / 'availability' / GPU).glob('*.json'), key=lambda p: int(p.stem))
        ready = stable([load(p) for p in paths], time.monotonic_ns())
        if ready: break
    put(out / 'result.json', dict(status='observed_idle' if ready else 'idle_gate_not_met', samples=[ref(p) for p in paths],
                                  source=ref(__file__), manifest=ref(MANIFEST)))


def admit(identity):
    from lp_billion_availability import observe, proof
    require(completed(CPU) and completed(CONTRACTS) and completed(identity), 'fresh settled CPU/contracts/idle admission')
    require(load(BASE / identity / 'result.json')['status'] == 'observed_idle', 'fresh sustained idle window')
    frozen = load(MANIFEST); resolve(frozen['resumption_source'])
    require(not (BASE / 'resources' / (GPU + '.reservation.json')).exists(), 'never-attempted operational GPU gate')
    observe(GPU); proof(GPU)
    put(MANIFEST.parent / 'idle-admission.json', dict(status='fresh_idle_observed', observation=ref(BASE / identity / 'result.json'),
                                                    proof=ref(BASE / 'availability' / (GPU + '.json')), manifest=ref(MANIFEST)))
    job(GPU, 180, ['python3', '-B', str(ROOT / 'tools/lp_billion_admit.py'), 'gpu', '--id', GPU, '--version', '2'], gpu=True)


def cleanup(family):
    if family == 'tall': return prune_tall()
    # The original cleanup routine's proofs/models have the same immutable IDs;
    # only the numerical wall allowances changed for these untouched cells.
    from lp_billion_copt_fair_run import cleanup as original_cleanup
    original_cleanup('1b', family)


def execute():
    require(completed(CPU) and completed(GPU) and completed(CONTRACTS), 'complete source-bound operational admission')
    frozen = load(MANIFEST); resolve(frozen['resumption_source'])
    require(not (MANIFEST.parent / 'completed.json').exists(), 'never repeat completed driver')
    for identity in frozen['untouched']:
        require(not (BASE / 'resources' / (identity + '.reservation.json')).exists(), 'all seven cells still untouched before starting driver')
    admit_envelope([c for c in frozen['cells'] if c['id'] in frozen['untouched']])
    for family in ['tall', 'coupled_blocks', 'ill_scaled', 'degenerate']:
        if family != 'tall':
            job('copt-fair-regenerate-1b-' + family + '-v1', 600, [str(PYTHON), '-B', str(ROOT / 'tools/lp_billion_copt_fair_run.py'),
                'regenerate', '--scale', '1b', '--family', family], phase='development', host=32, disk=40)
        for index, cell in enumerate(frozen['cells']):
            if cell['family'] != family or cell['id'] not in frozen['untouched']: continue
            memory = cell['memory']; disk = cell.get('disk_gib', math.ceil(memory.get('endpoint_bytes_upper', 0) / (1 << 30)) + 1)
            settled = run(cell['id'], 'development', cell['seconds'], True,
                          [str(PYTHON), '-B', str(resolve(frozen['source'])), 'worker', '--manifest', str(MANIFEST), '--index', str(index)],
                          memory['host_gib'], memory['device_gib'], disk)
            print(dict(cell=cell['id'], settlement=settled), flush=True)
            require(settled['cleanup_empty'] and not settled['overrun'], 'cleanup/overrun stops the untouched tail')
            identity = cell['id'] + '-full-audit'; require(not (BASE / 'resources' / (identity + '.reservation.json')).exists(), 'fresh complete independent audit')
            audited = run(identity, 'reporting', cell['audit_seconds'], False,
                          [str(PYTHON), '-B', str(resolve(frozen['audit'])), str(MANIFEST), str(index)], 64, 0,
                          math.ceil(8 * load(resolve(cell['model_result']))['rows'] / (1 << 30)) + 1)
            print(dict(audit=identity, settlement=audited), flush=True); require(audited['status'] == 'passed', 'complete strict proof coverage')
        suffix = 'tall-recovered' if family == 'tall' else family
        job('copt-fair-prune-1b-' + suffix + '-v1', 45,
            [str(PYTHON), '-B', str(ROOT / 'tools/lp_mixed2_reuse_place.py'), str(PYTHON), '-B', __file__, 'cleanup', '--family', family], phase='cleanup', host=8)
    put(MANIFEST.parent / 'completed.json', dict(status='all_seven_untouched_cells_attempted_and_audited', manifest=ref(MANIFEST)))
    put(ORIGINAL.parent / 'completed.json', dict(status='all_admitted_cells_attempted_and_audited', original_freeze=ref(ORIGINAL), effective_freeze=ref(MANIFEST)))
    job('copt-fair-complete-report-v1', 180,
        [str(PYTHON), '-B', str(ROOT / 'tools/lp_mixed2_reuse_place.py'), str(PYTHON), '-B', __file__, 'report'], phase='reporting', host=8)


def report():
    from lp_billion_full_report import record
    require((MANIFEST.parent / 'completed.json').exists(), 'complete effective roster')
    frozen = load(MANIFEST); rows = []
    for cell in frozen['cells']:
        row = recovered_record(cell) if cell['id'] == CELL else record(cell)
        row.update(timely_strict_certificate=False, requested_solver_wall_ns=int(cell['wall_seconds'] * NS),
                   outer_reservation_seconds=cell['seconds'], allowance_cohort='resumed' if cell['id'] in frozen['untouched'] else 'historical')
        if row.get('response'):
            response = load(resolve(row['response'])); row['timely_strict_certificate'] = timely(row, response, cell['wall_seconds'])
            row['requested_wall_exceeded'] = row['solver_wall_ns'] > row['requested_solver_wall_ns']
            row['iteration_safety_limit'] = 10000 if cell['lane'] == 'fp4x2' else None
            row['iteration_limit_reached'] = response.get('logical', 0) >= 10000 if cell['lane'] == 'fp4x2' else None
            if cell['lane'] != 'fp4x2': row.update(phase_journal=response['phase_journal'], interrupts=response['interrupts'])
        rows.append(row)
    comparisons = []
    for family in FAMILIES:
        project = next(r for r in rows if r['family'] == family and r['lane'] == 'fp4x2')
        vendor = next(r for r in rows if r['family'] == family and r['lane'] == 'copt-gpu-pdlp')
        comparisons.append(budgeted_pair(project, vendor))
    output = BASE / 'copt-fair-results-v1.json'; require(not output.exists(), 'fresh complete comparison report')
    put(output, dict(status='all_fair_comparison_outcomes_retained', cells=rows, comparisons=comparisons, freeze=ref(MANIFEST),
                     original_freeze=ref(ORIGINAL), source=ref(__file__), strict_original_tolerance=1e-9,
                     idle_admission=ref(MANIFEST.parent / 'idle-admission.json'),
                     limitations=['Only seven untouched cells receive larger prospective allowances; historical outcomes remain exact.',
                                  'Tall proof coverage is complete, but its original cold-proof timing is unavailable.',
                                  'Only jointly timely strictly certified pairs with equal requested allowances support total-time ratios.',
                                  'Every failure/full charge, capacity refusal, deadline and precision fallback remains visible.']))
    from lp_billion_copt_fair_report import main
    main()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['freeze', 'observation', 'admit', 'execute', 'cleanup', 'report'])
    parser.add_argument('--id'); parser.add_argument('--family'); args = parser.parse_args()
    if args.action in ['observation', 'admit']: globals()[args.action](args.id)
    elif args.action == 'cleanup': cleanup(args.family)
    else: globals()[args.action]()
