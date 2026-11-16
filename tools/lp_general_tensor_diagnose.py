"""Prospective attribution of the unchanged admitted Tensor Core executor.

Profiling is diagnostic, never a replacement for the frozen solve-time cohort.
Raw traces, profiler disturbance, and exact numerical comparisons are retained.
"""
import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path

from lp_general_common import BASE, ROOT, load, put, ref, require

NSYS = Path('/opt/nvidia/nsight-compute/2025.3.0/host/target-linux-x64/nsys')
NCU = Path('/usr/local/cuda-13.0/bin/ncu')
FORMATS = ['native', 'fp32', 'fp4x4']


def external_ref(path):
    return dict(path=str(path.resolve()), sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def freeze(identity):
    out = BASE / identity
    out.mkdir(exist_ok=False)
    old = load(BASE / 'tensor-ablation-v1/freeze.json')
    admission = BASE / 'tensor-admission-v4.json'
    a = load(admission)
    require(a['status'] == 'passed', 'admission required')
    require(a['binary'] == old['binary'] and a['image'] == old['image'], 'admission binding')
    cells = []
    # Small dense, larger dense, and larger sparse/block-dense operators.
    # Same 500-update numerical work as the existing admitted ablation.
    for index in [21, 3, 18]:
        for fmt in FORMATS:
            cell = next(c for c in old['cells'] if c['model_index'] == index and c['format'] == fmt)
            request = json.loads(json.dumps(cell['request']))
            # Allow profiler replay overhead, with the same iteration ceiling.
            request['settings']['wall_ms'] = 120000
            reference = BASE / 'tensor-ablation-v1' / f'm{index:02d}' / (cell['id'] + '.response.json')
            cells.append(dict(id=f'm{index:02d}-{fmt}', model=old['models'][index]['model'],
                              request=request, reference=ref(reference),
                              timeline_order=['plain-before', 'nsys', 'plain-after']))
    put(out / 'freeze.json', dict(kind='unchanged-image-attribution', admission=ref(admission),
        binary=a['binary'], image=a['image'], cells=cells, harness=ref(__file__),
        nsys=external_ref(NSYS), ncu=external_ref(NCU),
        counters=dict(model_index=21, formats=FORMATS,
                      kernels=dict(native=['tensor_step'], fp32=['tensor_step'],
                                   fp4x4=['tensor_product', 'tensor_encode', 'tensor_step']),
                      launch_skip=100, launch_count=2),
        claim='Descriptive kernel attribution only. No scientific retry, changed image, or adoption test.'))


def run(identity, cell_id, mode, kernel):
    root = BASE / identity
    f = load(root / 'freeze.json')
    require(ref(__file__) == f['harness'], 'diagnostic harness changed')
    for key in ['binary', 'image']:
        require(ref(ROOT / f[key]['path']) == f[key], key + ' changed')
    for key in ['nsys', 'ncu']:
        require(external_ref(Path(f[key]['path'])) == f[key], key + ' changed')
    cell = next(c for c in f['cells'] if c['id'] == cell_id)
    for key in ['model', 'reference']:
        require(ref(ROOT / cell[key]['path']) == cell[key], key + ' changed')
    label = cell_id + '-' + mode + (('-' + kernel) if kernel else '')
    out = root / label
    out.mkdir(exist_ok=False)
    command = [str(ROOT / f['binary']['path']), 'gpu-tensor',
               str(ROOT / cell['model']['path']), str(ROOT / f['image']['path'])]
    if mode == 'nsys':
        command = [str(NSYS), 'profile', '--trace=cuda', '--sample=none', '--cpuctxsw=none',
                   '--cuda-event-trace=false', '--export=sqlite', '--stats=false',
                   '--output=' + str(out / 'trace'), *command]
    elif mode == 'ncu':
        require(cell_id.startswith('m21-') and kernel in f['counters']['kernels'][cell['request']['settings']['format']], 'unplanned counter probe')
        command = [str(NCU), '--clock-control', 'none', '--cache-control', 'none',
                   '--kernel-name', kernel, '--launch-skip', '100', '--launch-count', '2',
                   '--section', 'SpeedOfLight', '--section', 'LaunchStats', '--section', 'Occupancy',
                   '--section', 'SchedulerStats', '--section', 'InstructionStats',
                   '--section', 'MemoryWorkloadAnalysis', '--section', 'WarpStateStats',
                   '--log-file', str(out / 'profile.txt'), '--export', str(out / 'profile'), *command]
    else:
        require(mode in ['plain-before', 'plain-after'], 'unplanned mode')
    wire = json.dumps(cell['request']) + '\n'
    (out / 'input.jsonl').write_text(wire)
    put(out / 'command.json', dict(argv=command, source=ref(__file__)))
    start = time.monotonic_ns()
    p = subprocess.run(command, input=wire, text=True, capture_output=True)
    elapsed = time.monotonic_ns() - start
    (out / 'stdout').write_text(p.stdout)
    (out / 'stderr').write_text(p.stderr)
    put(out / 'process.json', dict(returncode=p.returncode, outer_ns=elapsed))
    require(p.returncode == 0, 'diagnostic process failed: ' + p.stderr[-1500:])
    responses = [json.loads(line) for line in p.stdout.splitlines() if line.startswith('{')]
    require(len(responses) == 1, 'one numerical response required')
    r = responses[0]
    put(out / 'response.json', r)
    historical = load(ROOT / cell['reference']['path'])
    ignored = {'cost_ns', 'elapsed_ns', 'settings'}
    require({k: v for k, v in r.items() if k not in ignored} ==
            {k: v for k, v in historical.items() if k not in ignored}, 'numerical transcript differs')
    require({k: v for k, v in r['settings'].items() if k != 'wall_ms'} ==
            {k: v for k, v in historical['settings'].items() if k != 'wall_ms'}, 'numerical settings differ')
    require(r['logical'] == r['physical'] == 500, 'fixed work required')
    if mode == 'ncu':
        report = (out / 'profile.txt').read_text()
        require('ERR_' not in report and report.count('Section: GPU Speed Of Light Throughput') == 2,
                'both directional profiles required')
    if mode == 'nsys':
        require((out / 'trace.sqlite').exists(), 'timeline database required')
    put(out / 'result.json', dict(status='passed', cell=cell_id, mode=mode, kernel=kernel,
        response=ref(out / 'response.json'), reference=cell['reference'],
        exact_numerical_match=True, cost_ns=r['cost_ns'], elapsed_ns=r['elapsed_ns'],
        outer_ns=elapsed, profiler_overhead_included=mode in ['nsys', 'ncu']))
    print(dict(cell=cell_id, mode=mode, kernel=kernel, exact=True,
               execution_ms=r['cost_ns']['execution'] / 1e6), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['freeze', 'run', 'timeline'])
    p.add_argument('--id', required=True)
    p.add_argument('--cell')
    p.add_argument('--mode', choices=['plain-before', 'plain-after', 'nsys', 'ncu'])
    p.add_argument('--kernel')
    args = p.parse_args()
    if args.action == 'freeze':
        freeze(args.id)
    elif args.action == 'timeline':
        for mode in ['plain-before', 'nsys', 'plain-after']:
            run(args.id, args.cell, mode, None)
    else:
        run(args.id, args.cell, args.mode, args.kernel)
