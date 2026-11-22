"""Fresh availability after a non-passing idle window; no completed driver repeats."""
import argparse
import math
import time
from lp_billion_common import BASE, ROOT, NS, CPU_CAPS, GPU_CAPS, load, put, ref, resolve, require
from lp_billion_budget import accounting, run
from lp_billion_prepare_continue import job, completed
from lp_billion_availability import observe, proof, stable
from lp_billion_copt_fair_recovery_v2 import CPU, GPU, SEAL, PYTHON, PLAN, MANIFEST, PROTOCOL, prune_tall, report


def observation(identity):
    require(identity.startswith('copt-fair-tail-idle-') and '/' not in identity, 'bounded availability identity')
    out = BASE / identity; out.mkdir(exist_ok=False); ready = False; started = time.monotonic()
    for index in range(8):
        target = started + index * 60
        while time.monotonic() < target: time.sleep(min(1, target - time.monotonic()))
        observe(GPU)
        paths = sorted((BASE / 'availability' / GPU).glob('*.json'), key=lambda p: int(p.stem))
        ready = stable([load(p) for p in paths], time.monotonic_ns())
        if ready: break
    put(out / 'result.json', dict(status='observed_idle' if ready else 'idle_gate_not_met', samples=[ref(p) for p in paths],
                                  previous_window=ref(BASE / 'copt-fair-tail-idle-v1/result.json'), source=ref(__file__)))


def resume(identity):
    require(completed(CPU) and completed(SEAL) and completed(identity), 'settled CPU, proof-seal and availability gates')
    require(load(BASE / identity / 'result.json')['status'] == 'observed_idle', 'complete sustained idle window')
    bound = load(PLAN); resolve(bound['source']); resolve(bound['freeze'])
    frozen = load(MANIFEST)
    untouched = [c for c in frozen['cells'] if c['status'] == 'pending' and not (BASE / 'resources' / (c['id'] + '.reservation.json')).exists()]
    require([c['id'] for c in untouched] == bound['never_started'], 'exact seven untouched frozen LP cells')
    cpu, gpu = accounting()
    needed = dict(admission=480, development=4 * (sum(c['seconds'] for c in untouched) + 1800),
                  reporting=4 * (sum(c['audit_seconds'] for c in untouched) + 600), cleanup=480)
    require(all(cpu[k] + value * NS <= CPU_CAPS[k] * NS for k, value in needed.items()), 'whole remaining CPU reservation')
    require(gpu['admission'] + 120 * NS <= GPU_CAPS['admission'] * NS and gpu['development'] + sum(c['seconds'] for c in untouched) * NS <= GPU_CAPS['development'] * NS, 'whole remaining GPU reservation')
    observe(GPU); proof(GPU)
    receipt = BASE / 'copt-fair-idle-resume-v1/plan.json'; require(not receipt.exists(), 'fresh availability continuation')
    put(receipt, dict(status='frozen_untouched_tail_after_idle_readmission', source=ref(__file__), previous_plan=ref(PLAN),
                      freeze=ref(MANIFEST), protocol=ref(PROTOCOL), never_started=bound['never_started'],
                      cpu_gate=ref(BASE / 'resources' / (CPU + '.settlement.json')), proof_seal=ref(BASE / SEAL / 'result.json'),
                      unavailable_window=ref(BASE / 'copt-fair-tail-idle-v1/result.json'),
                      fresh_window=ref(BASE / identity / 'result.json'), final_idle_proof=ref(BASE / 'availability' / (GPU + '.json')),
                      cpu_reserve_seconds=needed, lp_solves_repeated=False))
    require(not (BASE / 'resources' / (GPU + '.reservation.json')).exists(), 'GPU operational gate never attempted')
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
    put(MANIFEST.parent / 'completed.json', dict(status='all_admitted_cells_attempted_and_audited', freeze=ref(MANIFEST), recovery=ref(PLAN), idle_readmission=ref(receipt)))
    put(PLAN.parent / 'completed.json', dict(status='complete', plan=ref(PLAN), idle_readmission=ref(receipt)))
    job('copt-fair-complete-report-v1', 120, [str(PYTHON), '-B', str(ROOT / 'tools/lp_mixed2_reuse_place.py'), str(PYTHON), '-B', __file__, 'report'], phase='reporting', host=8)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['observation', 'resume', 'prune_tall', 'report']); parser.add_argument('--id')
    args = parser.parse_args()
    if args.action in ['observation', 'resume']: globals()[args.action](args.id)
    else: globals()[args.action]()
