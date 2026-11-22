"""Exact shared host overhead: frozen matched development and complete reporting."""
import argparse
import json
import statistics
import sys

from lp_general_common import BASE, ROOT, CPU_CAPS, GPU_CAPS, NS, load, put, ref, require
from lp_general_budget import accounting
from lp_general_oracle import settings
from lp_general_scale_io import memory_estimate
from lp_general_scale_report import campaign
from lp_general_scale_evidence import read as read_response


def freeze(identity, version, full_solve=False):
    prefix = 'host-cost-' if version == 8 else 'host-cost-final-'
    names = ['host-cost-native-v1', f'scale-cpu-v{version}', prefix + 'gpu-v1'] + [
        prefix + s + '-v1' for s in ['memcheck', 'racecheck', 'initcheck', 'synccheck']]
    proofs = []
    for name in names:
        p = BASE / 'resources' / (name + '.settlement.json')
        require(load(p)['status'] == 'passed', 'host cost admission ' + name)
        proofs.append(ref(p))
    require(ref(BASE/'scale-image-v6/tensor.cubin')['sha256'] ==
            ref(BASE/f'scale-image-v{version}/tensor.cubin')['sha256'], 'unchanged CUDA image')
    for p in (ROOT/'research/lp-general-lowbit/src').glob('*.rs'):
        require(p.read_bytes() == (BASE/f'sources/scale-cpu-v{version}'/p.relative_to(ROOT)).read_bytes(),
                'admitted numerical source changed')
    models = [m for m in load(BASE/'scale-final-main-v1/freeze.json')['models']
              if m.get('seed') == 831001 or m['family'] in ['public-square31', 'public-scpm1']]
    require(len(models) == 8, 'complete six-family and two-public pilot roster')
    cells, memory = [], []
    for i, m in enumerate(models):
        estimate = memory_estimate(m['rows'], m['columns'], m['nonzeros'])
        # Four intermediate snapshots plus final endpoint and parsing/audit copies.
        snapshots = 42 if full_solve else 6
        host = estimate['host_allowance_bytes'] + 192 * (m['rows'] + m['columns']) * snapshots
        require(estimate['admits_domain'] and host < 15 << 30 and
                estimate['device_allowance_bytes'] < 12 << 30, 'complete pilot capacity')
        require(64 * (m['rows'] + m['columns']) * snapshots + (1 << 20) < 4 << 30,
                'complete response transport capacity')
        memory.append(dict(model=m['model'], host_allowance_bytes=host,
                           device_allowance_bytes=estimate['device_allowance_bytes']))
        for repeat in range(1 if full_solve else 2):
            lanes = ['native', 'previous-native', 'fp32', 'previous-fp32', 'fp4x2', 'previous-fp4x2']
            shift = (i + repeat) % len(lanes)
            lanes = lanes[shift:] + lanes[:shift]
            if (i + repeat) % 2:
                lanes.reverse()
            for lane in lanes:
                request = dict(settings={**settings(lane.removeprefix('previous-')),
                    'iteration_limit': 20000 if full_solve else 1000,
                    'check_interval': 500 if full_solve else 250, 'wall_ms': 30000},
                    tensor=dict(control_interval=100, min_tile_nnz=128),
                    fast=dict(host_reductions=True, host_preparation=True,
                              host_certificates=True, auto_schedule=True))
                image = 'scale-image-v6' if lane.startswith('previous-') else f'scale-image-v{version}'
                cells.append(dict(id=f'm{i:02d}-r{repeat}-t0-{lane}', model_index=i,
                    lane=lane, tolerance=1e-9, repeat=repeat, request=request,
                    binary=ref(BASE/image/'executor')))
    deadlines = [900 if m['family'] == 'public-scpm1' else 300 for m in models]
    if full_solve:
        require(version == 9, 'full-solve final candidate only')
        require(load(BASE/'resources/host-cost-report-v2.settlement.json')['status'] == 'passed',
                'complete final fixed-work comparison first')
        deadlines = [900 if m['family'] == 'public-scpm1' else
                     450 if m['family'] == 'public-square31' else
                     240 if m['family'] in ['tall', 'coupled_blocks', 'degenerate'] else 300
                     for m in models]
    cpu, gpu = accounting()
    require(cpu['development'] + 4 * sum(deadlines) * NS <= CPU_CAPS['development'] * NS,
            'complete host cost CPU cohort')
    require(gpu['development'] + sum(deadlines) * NS <= GPU_CAPS['development'] * NS,
            'complete host cost GPU cohort')
    out = BASE/identity
    out.mkdir(exist_ok=False)
    runner = out/'runner.py'
    runner.write_bytes((ROOT/'tools/lp_general_scale_bench.py').read_bytes())
    fingerprints = []
    for p in (ROOT/'research/lp-general-lowbit/target/release/.fingerprint').glob('lp-general-lowbit-*/bin-lp-general-lowbit.json'):
        if load(p)['rustflags'] == []:
            saved = out/'candidate-fingerprint.json'
            saved.write_bytes(p.read_bytes())
            fingerprints.append(ref(saved))
            break
    require(fingerprints, 'default Rust host target fingerprint')
    put(out/'freeze.json', dict(mode='scale' if full_solve else 'pilot', models=models, cells=cells,
        memory_preflight=memory, job_seconds=deadlines, seconds_per_job=300,
        binary=ref(BASE/'scale-image-v6/executor'), image=ref(BASE/'scale-image-v6/tensor.cubin'),
        harness=ref(runner), design=ref(__file__), baseline_solve_seconds=30, proofs=proofs,
        baseline_worker=ref(ROOT/'tools/lp_general_scale_copt.py'),
        evidence_worker=ref(ROOT/'tools/lp_general_scale_evidence.py'), fingerprints=fingerprints,
        full_solve=full_solve,
        claim='Shared host implementation and unchanged CUDA image; descriptive development, not confirmation. '
              + ('Single solves to certificate, 20000 updates or 30 seconds.' if full_solve else
                 'Matched 1000-update pilot; bounded work is not general certified-solve value.')))


def report(identity, output, compact):
    data = campaign(identity)
    keyed = {(r['model_index'], r['repeat'], r['lane']): r for r in data['rows']}
    if load(BASE/identity/'freeze.json').get('full_solve'):
        for b in data['rows']:
            if b['lane'] not in ['native', 'fp32', 'fp4x2']:
                continue
            a = keyed[(b['model_index'], b['repeat'], 'previous-' + b['lane'])]
            deadline = 'deadline' in [a['status'], b['status']]
            same_work = (a['logical'], a['physical']) == (b['logical'], b['physical'])
            exact = False
            x, y = read_response(ROOT/a['response']['path']), read_response(ROOT/b['response']['path'])
            common = min(len(x['assessments']), len(y['assessments']))
            require(all(json.dumps(left, sort_keys=True) == json.dumps(right, sort_keys=True)
                        for left, right in zip(x['assessments'], y['assessments'])),
                    'shared assessment prefix differs')
            if not deadline:
                keys = ['primal', 'dual', 'certificate', 'assessments', 'logical', 'physical',
                        'accepted', 'attempted', 'recoveries', 'accepted_product_work', 'physical_product_work']
                exact = all(json.dumps(x[k], sort_keys=True) == json.dumps(y[k], sort_keys=True) for k in keys)
                require(same_work and exact, 'non-deadline solve arithmetic differs')
            data['matched'].append(dict(model_index=b['model_index'], lane=b['lane'], repeat=b['repeat'],
                exact=exact, equal_work=same_work, deadline_pair=deadline,
                exact_common_assessments=common,
                supervised=a['supervised'] and b['supervised'], status_same=a['status'] == b['status'],
                primary_ratio=a['primary_seconds']/b['primary_seconds'],
                process_ratio=a['process_seconds']/b['process_seconds'],
                preparation_ratio=a['cost_seconds']['host_preparation']/b['cost_seconds']['host_preparation'],
                before_primary_seconds=a['primary_seconds'], after_primary_seconds=b['primary_seconds']))
    for pair in data['matched']:
        key = pair['model_index'], pair['repeat']
        a = keyed[(*key, 'previous-' + pair['lane'])]
        b = keyed[(*key, pair['lane'])]
        pair['cost_ratios'] = {k: a['cost_seconds'][k] / v if v else None
                              for k, v in b['cost_seconds'].items()}
        pair['jointly_certified'] = a['certified'] and b['certified']
    valid = [p for p in data['matched'] if p['exact'] and p['equal_work'] and p['supervised']]
    summary = dict(exact_pairs=len(valid), planned_pairs=len(data['matched']))
    certified = [p for p in valid if p['jointly_certified']]
    summary['jointly_certified_pairs'] = len(certified)
    summary['certified_primary_median'] = statistics.median(p['primary_ratio'] for p in certified) if certified else None
    for lane in ['all', 'native', 'fp32', 'fp4x2']:
        pairs = [p for p in valid if lane == 'all' or p['lane'] == lane]
        summary[lane] = dict(pairs=len(pairs),
            primary_median=statistics.median(p['primary_ratio'] for p in pairs) if pairs else None,
            cost_medians={k: statistics.median(p['cost_ratios'][k] for p in pairs
                if p['cost_ratios'][k] is not None) for k in ['host_preparation', 'assessment', 'execution']} if pairs else {})
    summary['families'] = []
    for i, model in enumerate(load(BASE/identity/'freeze.json')['models']):
        pairs = [p for p in valid if p['model_index'] == i]
        summary['families'].append(dict(family=model['family'], pairs=len(pairs),
            primary_median=statistics.median(p['primary_ratio'] for p in pairs) if pairs else None,
            assessment_median=statistics.median(p['cost_ratios']['assessment'] for p in pairs) if pairs else None))
    cpu, gpu = accounting()
    data.update(summary=summary, cpu_seconds={k: v/NS for k, v in cpu.items()},
                gpu_seconds={k: v/NS for k, v in gpu.items()}, source=ref(__file__))
    put(output, data)
    columns = ['id', 'model_index', 'lane', 'repeat', 'status', 'certified', 'supervised',
               'primary_seconds', 'independent_seconds', 'audit_seconds', 'logical', 'physical',
               'fp4_share', 'nonzeros', 'cost_seconds']
    put(compact, {
        **{k: v for k, v in data.items() if k not in ['rows', 'comparisons']},
        'full_local_results': ref(output), 'cell_columns': columns,
        'cells': [[r.get(k) for k in columns] for r in data['rows']],
        'claim': load(BASE/identity/'freeze.json')['claim']})
    print(json.dumps(summary, indent=2), flush=True)


def device_admission(version):
    from lp_general_budget import run
    require(load(BASE/'resources/host-cost-native-v1.settlement.json')['status'] == 'passed',
            'native acceptance before device work')
    for sanitizer in [None, 'memcheck', 'racecheck', 'initcheck', 'synccheck']:
        prefix = 'host-cost-' if version == 8 else 'host-cost-final-'
        identity = prefix + (sanitizer or 'gpu') + '-v1'
        command = [sys.executable, '-B', '-c',
            'import sys; sys.path.insert(0,"tools"); '
            'from lp_general_scale_admit import gpu; '
            f'gpu({identity!r}, {sanitizer!r}, {version})']
        result = run(identity, 'admission', 180 if sanitizer is None else 120, True, command)
        require(result['status'] == 'passed', 'device admission stopped: ' + identity)
        print(identity, result, flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['freeze', 'report', 'device'])
    p.add_argument('--id', required=True)
    p.add_argument('--output')
    p.add_argument('--compact-output')
    p.add_argument('--version', type=int, choices=[8, 9], default=8)
    p.add_argument('--full-solve', action='store_true')
    a = p.parse_args()
    if a.action == 'device':
        device_admission(a.version)
    elif a.action == 'freeze':
        freeze(a.id, a.version, a.full_solve)
    else:
        require(a.output and a.compact_output, 'report destinations required')
        report(a.id, a.output, a.compact_output)
