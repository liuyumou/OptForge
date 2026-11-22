"""Recover original input and finish only the two never-attempted degenerate LPs."""
import argparse
import hashlib
import math
import time
from lp_billion_common import BASE, ROOT, NS, CPU_CAPS, GPU_CAPS, load, put, ref, resolve, require
from lp_billion_budget import accounting, run
from lp_billion_prepare_continue import completed, job
from lp_confirmation2_supervisor import same_process
from lp_billion_copt_fair_run import PYTHON
import lp_billion_copt_fair_headroom as previous

FAILED = 'copt-fair-regenerate-1b-degenerate-v1'
CPU = 'operational-cpu-v35'
GPU = 'operational-gpu-v27'
IDLE = 'copt-fair-headroom-idle-v3'
REGEN = 'copt-fair-regenerate-1b-degenerate-v2'
PLAN = BASE / 'copt-fair-degenerate-tail-v1/plan.json'
PROTOCOL = ROOT / 'docs/specifications/SPEC-0046-amendment-89.md'
REMAINING = ['copt-fair-1b-v1-degenerate-copt', 'copt-fair-1b-v1-degenerate-project']


def untouched(frozen):
    cells = [c for c in frozen['cells'] if c['status'] == 'pending'
             and not (BASE / 'resources' / (c['id'] + '.reservation.json')).exists()]
    require([c['id'] for c in cells] == REMAINING, 'exact two never-attempted LPs')
    require(all(c['family'] == 'degenerate' and c['wall_seconds'] == 1800 and c['seconds'] == 2700
                and c['audit_seconds'] == (900 if c['lane'] == 'copt-gpu-pdlp' else 4600) for c in cells),
            'unchanged solve and full-audit allowances')
    return cells


def envelope():
    c, g = accounting()
    cpu = dict(admission=3600, development=25200, reporting=26000, cleanup=240)
    gpu = dict(admission=180, development=5400)
    require(all(c[k] + v * NS <= CPU_CAPS[k] * NS for k, v in cpu.items()), 'complete remaining CPU envelope')
    require(all(g[k] + v * NS <= GPU_CAPS[k] * NS for k, v in gpu.items()), 'complete remaining GPU envelope')
    return dict(cpu=cpu, gpu=gpu, remaining_after_cpu_seconds={k:CPU_CAPS[k]-c[k]/NS-v for k,v in cpu.items()},
                remaining_after_gpu_seconds={k:GPU_CAPS[k]-g[k]/NS-v for k,v in gpu.items()})


def prepare():
    require(not PLAN.exists(), 'fresh recovery plan')
    frozen = load(previous.MANIFEST); resolve(frozen['resumption_source']); untouched(frozen)
    receipt = BASE / 'resources' / (FAILED + '.settlement.json'); settled = load(receipt)
    require(settled['status'] == 'refused' and not settled['overrun'] and not settled['cleanup_empty'], 'exact retained generation failure')
    resource = resolve(settled['resource']); journal = receipt.with_name(FAILED + '.cpu-journal.json'); identities = {}
    def collect(value):
        if isinstance(value, dict):
            if 'pid' in value and 'start_ticks' in value: identities[(value['pid'], value['start_ticks'])] = value
            for child in value.values(): collect(child)
        elif isinstance(value, list):
            for child in value: collect(child)
    collect(load(resource)); collect(load(journal))
    require(identities and not any(same_process(p) for p in identities.values()), 'all exact owned generation identities gone')
    disposition = receipt.with_name(FAILED + '.cleanup-disposition.json')
    require(not disposition.exists(), 'fresh additive cleanup proof')
    put(disposition, dict(status='cleanup_verified', settlement=ref(receipt), resource=ref(resource), journal=ref(journal),
        identities=list(identities.values()), admission_job=GPU, cpu_admission_job=CPU, protocol=ref(PROTOCOL),
        original_receipt_unchanged=True, preceding_trigger='unknown; retained receipt records cleanup_incomplete'))
    operational = BASE / 'operational-readmissions/v75.json'; require(not operational.exists(), 'fresh operational plan')
    put(operational, dict(status='prospective', cleanup_disposition=ref(disposition), admission_job=GPU,
        cpu_admission_job=CPU, availability_window_seconds=300, protocol=ref(PROTOCOL)))
    bindings = load(BASE / 'gpu-control-settled-checkpoint-v1.json')['numerical_bindings']
    for item in bindings: resolve(item)
    put(PLAN, dict(status='prospective_two_untouched_cells', source=ref(__file__), manifest=ref(previous.MANIFEST),
        remaining=REMAINING, failed_generation=ref(receipt), cleanup_disposition=ref(disposition), operational_plan=ref(operational),
        explicit_resumption=ref(BASE / 'copt-fair-headroom-resume-v1/plan.json'), protocol=ref(PROTOCOL),
        reservation=envelope(), numerical_bindings=bindings))


def observation():
    previous.IDLE = IDLE
    previous.observation()


def regenerate():
    from lp_billion_generate import generate
    from lp_billion_portable import arrays
    original = load(BASE / 'models-1b-degenerate-v1/result.json'); resolve(original['generator'])
    documents = [load(resolve(original[k])) for k in ['model', 'construction']]
    chunks = {q['sha256']:q['bytes'] for d in documents for a in arrays(d) for q in a['chunks']}
    failed = BASE / 'resources' / (FAILED + '.request.json'); checked = 0; removed = []
    for sha, size in chunks.items():
        path = BASE / 'objects' / (sha + '.bin')
        if not path.exists(): continue
        require(not path.is_symlink() and path.resolve().parent == (BASE / 'objects').resolve(), 'owned regular content object')
        data = path.read_bytes(); actual = hashlib.sha256(data).hexdigest(); checked += 1
        if len(data) != size or actual != sha:
            require(path.stat().st_mtime_ns >= failed.stat().st_mtime_ns, 'partial chunk belongs to interrupted generation')
            removed.append(dict(expected_sha256=sha, actual_sha256=actual, bytes=len(data), expected_bytes=size)); path.unlink()
    put(BASE / 'copt-fair-degenerate-partial-recovery-v1.json', dict(status='existing_chunks_checked', checked=checked,
        removed=removed, failed_reservation=ref(failed.with_name(FAILED + '.reservation.json')), source=ref(__file__)))
    identity = 'copt-fair-regenerated-1b-degenerate-v2'
    generate(identity, 'degenerate', original['target'], original['seed']); fresh = load(BASE / identity / 'result.json')
    require(fresh['model']['sha256'] == original['model']['sha256'], 'exact original model hash')
    for key in ['model', 'construction']:
        require(load(resolve(fresh[key])) == load(resolve(original[key])), 'exact regenerated ' + key)


def execute():
    plan = load(PLAN); resolve(plan['source']); frozen = load(resolve(plan['manifest'])); untouched(frozen)
    require(not (PLAN.parent / 'started.json').exists(), 'never repeat the two-cell driver')
    require(completed('operational-cpu-v34') and completed('operational-gpu-v26'), 'unchanged source-bound gates retained')
    require(all(completed(i) for i in [CPU, IDLE, GPU]), 'additional operational gates passed')
    require(load(BASE / IDLE / 'result.json')['status'] == 'capacity_and_idle_passed', 'fresh sustained idle and RAM admission')
    put(PLAN.parent / 'started.json', dict(plan=ref(PLAN), cpu=ref(BASE/'resources'/(CPU+'.settlement.json')),
        gpu=ref(BASE/'resources'/(GPU+'.settlement.json')), idle=ref(BASE/IDLE/'result.json')))
    job(REGEN, 900, [str(PYTHON), '-B', __file__, 'regenerate'], phase='development', host=32, disk=40)
    for i, cell in enumerate(frozen['cells']):
        if cell['id'] not in REMAINING: continue
        m = cell['memory']; disk = cell.get('disk_gib', math.ceil(m.get('endpoint_bytes_upper',0)/(1<<30))+1)
        result = run(cell['id'], 'development', 2700, True, [str(PYTHON), '-B', str(resolve(frozen['source'])),
            'worker', '--manifest', str(previous.MANIFEST), '--index', str(i)], m['host_gib'], m['device_gib'], disk)
        print(dict(cell=cell['id'], settlement=result), flush=True)
        require(result['cleanup_empty'] and not result['overrun'], 'cleanup/overrun stops continuation')
        audit = cell['id'] + '-full-audit'
        result = run(audit, 'reporting', cell['audit_seconds'], False, [str(PYTHON), '-B', str(resolve(frozen['audit'])),
            str(previous.MANIFEST), str(i)], 64, 0, math.ceil(8*load(resolve(cell['model_result']))['rows']/(1<<30))+1)
        print(dict(audit=audit, settlement=result), flush=True)
        require(result['status'] == 'passed', 'complete strict endpoint coverage')
    job('copt-fair-prune-1b-degenerate-v1', 60, [str(PYTHON), '-B', str(ROOT/'tools/lp_mixed2_reuse_place.py'),
        str(PYTHON), '-B', str(ROOT/'tools/lp_billion_copt_fair_run.py'), 'cleanup', '--scale', '1b', '--family', 'degenerate'], phase='cleanup', host=8)
    for path, status in [(PLAN.parent/'completed.json', 'two_cells_attempted_and_audited'),
                         (previous.MANIFEST.parent/'completed.json', 'all_remaining_cells_attempted_and_audited'),
                         (previous.previous.MANIFEST.parent/'completed.json', 'all_four_cells_attempted_and_audited'),
                         (previous.previous.ORIGINAL.parent/'completed.json', 'all_admitted_cells_attempted_and_audited')]:
        require(not path.exists(), 'fresh completion marker'); put(path, dict(status=status, effective_freeze=ref(previous.MANIFEST), recovery=ref(PLAN)))
    job('copt-fair-complete-report-v1', 180, [str(PYTHON), '-B', str(ROOT/'tools/lp_mixed2_reuse_place.py'),
        str(PYTHON), '-B', str(ROOT/'tools/lp_billion_copt_fair_headroom.py'), 'report'], phase='reporting', host=8)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['prepare', 'observation', 'regenerate', 'execute'])
    globals()[parser.parse_args().action]()
