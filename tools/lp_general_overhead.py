"""Matched FP4 surrounding-work development, with exact historical controls."""
import argparse
import json
import re
from pathlib import Path

from lp_general_common import BASE, ROOT, NS, CPU_CAPS, GPU_CAPS, load, put, ref, require
from lp_general_budget import accounting
from lp_general_fast_bench import run, campaign


def sanitizers(identity, image, sanitizer):
    from lp_general_fast_boundary import run as boundary
    from lp_general_fast_split import run as split
    boundary(identity + '-boundary', image, sanitizer)
    split(identity + '-split', image, sanitizer)
    out = BASE / identity
    out.mkdir(exist_ok=False)
    put(out / 'result.json', dict(status='passed', image=ref(image), sanitizer=sanitizer,
        proofs=[ref(BASE / (identity + suffix) / 'result.json') for suffix in ['-boundary', '-split']]))


def admit(identity):
    image = BASE / 'fast-image-v10/tensor.cubin'
    binary = BASE / 'fast-image-v10/executor'
    cpu = 'fast-overhead-cpu-v1'
    native = 'fast-overhead-native-v1'
    names = [cpu, cpu + '-oracle', 'fast-overhead-gpu-v1', 'fast-overhead-boundary-v1',
             'fast-overhead-split-v1']
    names += ['fast-overhead-' + s + ('-v2' if s == 'racecheck' else '-v1') for s in ['memcheck', 'racecheck', 'initcheck', 'synccheck']]
    proofs, resources = {}, {}
    for name in names:
        path = BASE / name / 'result.json'
        r = load(path)
        require(r['status'] == 'passed', 'incomplete proof ' + name)
        if r.get('image'):
            require(r['image'] == ref(image), 'wrong admitted image')
        for item in r.get('proofs', []):
            require(ref(ROOT / item['path']) == item, 'sanitizer proof changed')
            child = load(ROOT / item['path'])
            require(child['status'] == 'passed' and child['image'] == ref(image), 'child admission')
            require(child['binary']['sha256'] == ref(binary)['sha256'], 'child binary')
        if 'binary' in r:
            require(r['binary']['sha256'] == ref(binary)['sha256'], 'wrong binary')
        job = cpu if name == cpu + '-oracle' else name
        receipt = BASE / 'resources' / (job + '.settlement.json')
        require(load(receipt)['status'] == 'passed', 'unsettled proof')
        proofs[name], resources[name] = ref(path), ref(receipt)
    native_receipt = BASE / 'resources' / (native + '.settlement.json')
    require(load(native_receipt)['status'] == 'passed', 'native acceptance')
    for p in (ROOT / 'crates').rglob('*.rs'):
        require(p.read_bytes() == (BASE / 'sources' / native / p.relative_to(ROOT)).read_bytes(), 'root sources changed')
    retained = []
    dest = BASE / (identity + '-sources')
    dest.mkdir(exist_ok=False)
    for p in sorted((ROOT / 'research/lp-general-lowbit/src').glob('*.rs')) + sorted((ROOT / 'research/lp-general-lowbit/cuda').glob('*')):
        require(p.read_bytes() == (BASE / 'sources' / cpu / p.relative_to(ROOT)).read_bytes(), 'compiled source differs')
        q = dest / p.relative_to(ROOT)
        q.parent.mkdir(parents=True, exist_ok=True)
        q.write_bytes(p.read_bytes())
        retained.append(ref(q))
    sass = (BASE / 'fast-image-v10/tensor.sass').read_text()
    previous_sass = (BASE / 'fast-image-v9/tensor.sass').read_text()
    section = lambda s, k: s.split('Function : ' + k + '\n')[1].split('Function :')[0]
    unchanged = ['fast_step_' + str(mode) + '_' + str(lanes) for mode in [0, 1] for lanes in [1, 4, 8, 32]]
    unchanged += ['fast_product_' + str(k) for k in range(1, 5)] + ['fast_step_2_32']
    for kernel in unchanged:
        code = lambda s: re.findall(r'/\* 0x([0-9a-f]+) \*/', section(s, kernel))
        require(code(sass) and code(sass) == code(previous_sass), 'control machine code changed ' + kernel)
    for k in range(1, 5):
        for kernel in ['fast_product_', 'fast_combined_']:
            section = sass.split('Function : ' + kernel + str(k) + '\n')[1].split('Function :')[0]
            require('QMMA.16832.F32.E2M1.E2M1' in section, 'actual FP4 MMA required')
    comparisons = []
    for old, new in [('fast-gpu-v5', 'fast-overhead-gpu-v1'), ('fast-boundary-gpu-v3', 'fast-overhead-boundary-v1'), ('fast-split-gpu-v1', 'fast-overhead-split-v1')]:
        a = sorted((BASE / old).glob('*.response.json'))
        require({p.name for p in a} == {p.name for p in (BASE / new).glob('*.response.json')}, 'comparison coverage differs')
        for p in a:
            q = BASE / new / p.name
            canonical = lambda r: json.dumps({k: v for k, v in r.items() if k not in {'elapsed_ns', 'cost_ns', 'device_bytes_upper'}}, sort_keys=True, separators=(',', ':'))
            require(canonical(load(p)) == canonical(load(q)), 'numerical transcript changed ' + str(q))
            comparisons.append(dict(before=ref(p), after=ref(q)))
    put(BASE / (identity + '.json'), dict(status='passed', binary=ref(binary), image=ref(image),
        proofs=proofs, resources=resources, native=ref(native_receipt), sources=retained,
        exact_responses=len(comparisons), comparisons=comparisons,
        identical_machine_code=unchanged,
        sanitizer_scope='Changed projection/encoding paths: combined all component counts, long rows, multi-tile reductions, empty dimensions; split all lane counts, fused/unfused, positive certificates and recovery/cancellation.',
        operational=ref(BASE / 'operational-readmission-v2.json')))
    print('admitted', len(comparisons), 'exact responses', flush=True)


def freeze(identity, pilot):
    admission = BASE / 'fast-overhead-admission-v1.json'
    a, old = load(admission), load(BASE / 'fast-admission-v5.json')
    require(a['status'] == old['status'] == 'passed', 'admitted controls required')
    for r in [a, old]:
        for k in ['image', 'binary']:
            require(ref(ROOT / r[k]['path']) == r[k], 'source changed')
    models = load(BASE / 'fast-broad-v2/freeze.json')['models']
    indices = [3, 9, 11, 13, 18, 21] if pilot else list(range(len(models)))
    cells = []
    for index in indices:
        for repeat in range(4 if pilot else 1):
            for ti, tol in enumerate([1e-9] if pilot else [1e-7, 1e-9]):
                formats = ['native', 'fp32', 'fp4x2', 'fp4x2-split', 'previous-fp4x2', 'previous-fp4x2-split']
                if not pilot:
                    formats = ['native', 'fp32', 'fp4x2', 'fp4x2-split']
                # Rotate and reverse deterministically; no timing-dependent order.
                shift = (index + repeat + ti) % len(formats)
                formats = formats[shift:] + formats[:shift]
                if (index + repeat + ti) % 2:
                    formats.reverse()
                for fmt in formats:
                    source = old if fmt.startswith('previous-') else a
                    actual = fmt.removeprefix('previous-').removesuffix('-split')
                    from lp_general_oracle import settings
                    cells.append(dict(id=f'm{index:02d}-r{repeat}-t{ti}-{fmt}', model_index=index, format=fmt, tolerance=tol,
                        command='gpu-fast', binary=source['binary'], image=source['image'],
                        request=dict(settings={**settings(actual), 'tolerance':tol, 'iteration_limit':500 if pilot else 20000,
                            'check_interval':500, 'wall_ms':10000 if pilot else 30000},
                            tensor=dict(min_tile_nnz=128, control_interval=100), fast=dict(combined=not fmt.endswith('-split')))))
    seconds = 120 if pilot else 180
    cpu, gpu = accounting()
    require(cpu['development'] + len(indices)*4*seconds*NS <= CPU_CAPS['development']*NS, 'whole CPU reservation')
    require(gpu['development'] + len(indices)*seconds*NS <= GPU_CAPS['development']*NS, 'whole GPU reservation')
    root = BASE / identity
    root.mkdir(exist_ok=False)
    put(root / 'freeze.json', dict(kind='fast-proposal-development', pilot=pilot, models=models, indices=indices, cells=cells,
        seconds_per_job=seconds, admission=ref(admission), previous=ref(BASE / 'fast-admission-v5.json'),
        harness=ref(ROOT / 'tools/lp_general_fast_bench.py'), design=ref(__file__),
        claim='Matched development observations; all original-model certificates mandatory. No confirmation or adoption.'))


def tail(identity):
    original = BASE / 'fast-overhead-broad-v1/freeze.json'
    f = load(original)
    failed = BASE / 'resources/fast-overhead-broad-v1-m16.settlement.json'
    s = load(failed)
    require(s['status'] == 'refused' and not s['overrun'], 'expected stopped campaign')
    r = load(ROOT / s['resource']['path'])
    require(r['result']['reason'] == 'guardian_cpu_wall_deadline' and r['guardian_cleanup']['empty'], 'unexpected refusal')
    indices = list(range(17, 22))
    for i in indices:
        require(not (BASE / 'resources' / f'fast-overhead-broad-v1-m{i:02d}.reservation.json').exists(), 'group already attempted')
        require(not (BASE / 'fast-overhead-broad-v1' / f'm{i:02d}').exists(), 'group already started')
    cpu, gpu = accounting()
    require(cpu['development'] + len(indices)*1200*NS <= CPU_CAPS['development']*NS, 'remaining CPU reservation')
    require(gpu['development'] + len(indices)*300*NS <= GPU_CAPS['development']*NS, 'remaining GPU reservation')
    root = BASE / identity
    root.mkdir(exist_ok=False)
    put(root / 'freeze.json', dict(**{k:v for k,v in f.items() if k not in {'indices','cells','seconds_per_job','design'}},
        indices=indices, cells=[c for c in f['cells'] if c['model_index'] in indices], seconds_per_job=300,
        design=ref(__file__), completion_of=ref(original), stopped_group=ref(failed),
        excluded_attempted_group=16, claim_scope='Only five never-reserved model groups; no attempted cell repeated. Group 16 retains seven responses and one missing endpoint.'))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['sanitizers', 'admit', 'freeze', 'tail', 'campaign'])
    p.add_argument('--id', required=True)
    p.add_argument('--image', type=Path)
    p.add_argument('--sanitizer', choices=['memcheck', 'racecheck', 'initcheck', 'synccheck'])
    p.add_argument('--pilot', action='store_true')
    a = p.parse_args()
    if a.action == 'sanitizers': sanitizers(a.id, a.image, a.sanitizer)
    elif a.action == 'admit': admit(a.id)
    elif a.action == 'freeze': freeze(a.id, a.pilot)
    elif a.action == 'tail': tail(a.id)
    else: campaign(a.id)
