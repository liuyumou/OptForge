"""Exact preparation/control continuation: source admission and frozen comparisons."""
import argparse
import json
import statistics
import subprocess
import sys

from lp_general_common import BASE, ROOT, CPU_CAPS, GPU_CAPS, NS, load, put, ref, require
from lp_general_budget import accounting, run
from lp_general_host_cost import report
from lp_general_oracle import settings
from lp_general_scale_io import memory_estimate

VERSION = 12


def device(version=VERSION):
    require(load(BASE/f'scale-cpu-v{version}/result.json')['status'] == 'passed', 'CPU admission')
    if version == 14:
        require(load(BASE/'resources/prep-control-native-v2.settlement.json')['status'] == 'passed',
                'fresh native acceptance')
    for sanitizer in [None, 'memcheck', 'racecheck', 'initcheck', 'synccheck']:
        identity = ('prep-control-indexed-' if version == 14 else 'prep-control-') + (sanitizer or 'gpu') + '-v1'
        command = [sys.executable, '-B', '-c',
            'import sys; sys.path.insert(0,"tools"); '
            'from lp_general_scale_admit import gpu; '
            f'gpu({identity!r}, {sanitizer!r}, {version})']
        result = run(identity, 'admission', 180 if sanitizer is None else 120, True, command)
        require(result['status'] == 'passed', 'device admission stopped: ' + identity)
        print(identity, result, flush=True)


def control_admission(identity):
    from lp_general_models import generate
    from lp_general_scale_io import write, from_document
    from lp_general_device import serial
    out = BASE/identity
    out.mkdir(exist_ok=False)
    rows = []
    for family, size in [('dense', 385), ('irregular', 4097), ('rectangular', 4097)]:
        doc, _ = generate(family, size, 841100 + size)
        original, compact = out/(family+'.json'), out/(family+'.lpcsr')
        put(original, doc)
        write(compact, from_document(doc))
        cases = [(lane, None) for lane in ['native', 'fp32', 'fp4x2']]
        if family == 'dense':
            cases += [('fp4x2', 'force_recovery_after'), ('fp4x2', 'cancel_after')]
        for lane, fault in cases:
            s = {**settings(lane), 'iteration_limit': 1000, 'check_interval': 500}
            if fault:
                s[fault] = 3
            request = dict(settings=s, tensor=dict(control_interval=500, min_tile_nnz=128),
                fast=dict(host_reductions=True, host_preparation=True, host_certificates=True, auto_schedule=True))
            responses = []
            for version in [9, VERSION]:
                command = [str(BASE/f'scale-image-v{version}/executor'), 'gpu-fast', str(compact),
                           str(BASE/f'scale-image-v{version}/tensor.cubin')]
                child = subprocess.run(command, input=json.dumps(request)+'\n', text=True, capture_output=True)
                name = f'{family}-{lane}-{fault}-v{version}'
                (out/(name+'.stderr')).write_text(child.stderr)
                require(child.returncode == 0, '500-update control admission: '+name)
                response = json.loads(child.stdout)
                put(out/(name+'.response.json'), response)
                proofs = [serial(original, {**endpoint, 'bound_proof': response['bound_proof']},
                                 s['tolerance'], out, name+'-'+str(i))
                          for i, endpoint in enumerate([*response['assessments'], response])]
                rows.append(dict(response=ref(out/(name+'.response.json')), serial=proofs))
                responses.append({k: v for k, v in response.items() if k not in ['elapsed_ns', 'cost_ns']})
            require(responses[0] == responses[1], 'exact 500-update continuation differs')
    put(out/'result.json', dict(status='passed', rows=rows, exact_pairs=len(rows)//2,
        image=ref(BASE/f'scale-image-v{VERSION}/executor'), source=ref(__file__),
        claim='Same 500-update control setting against the admitted original host; independent endpoint checking.'))
    print(dict(status='passed', exact_pairs=len(rows)//2), flush=True)


def freeze(identity, control=False):
    proofs = []
    for name in ['host-cost-native-v1', f'scale-cpu-v{VERSION}', 'prep-control-gpu-v1'] + [
            'prep-control-' + s + '-v1' for s in ['memcheck', 'racecheck', 'initcheck', 'synccheck']]:
        p = BASE/'resources'/(name + '.settlement.json')
        require(load(p)['status'] == 'passed', 'complete admission: ' + name)
        proofs.append(ref(p))
    if control:
        p = BASE/'resources/prep-control-cadence-admission-v1.settlement.json'
        require(load(p)['status'] == 'passed', '500-update admission')
        proofs.append(ref(p))
    for p in (ROOT/'research/lp-general-lowbit/src').rglob('*.rs'):
        require(p.read_bytes() == (BASE/f'sources/scale-cpu-v{VERSION}'/p.relative_to(ROOT)).read_bytes(),
                'admitted source differs')
    require(ref(BASE/f'scale-image-v{VERSION}/tensor.cubin')['sha256'] ==
            ref(BASE/'scale-image-v9/tensor.cubin')['sha256'], 'unchanged CUDA')
    models = load(BASE/'host-cost-solve-v1/freeze.json')['models']
    require(len(models) == 8, 'complete development roster')
    cells, memory = [], []
    for i, m in enumerate(models):
        estimate = memory_estimate(m['rows'], m['columns'], m['nonzeros'])
        vectors = m['rows'] + m['columns']
        # Reused host product vectors and four per-worker reduction/output
        # buffers, in addition to the prior complete transport/audit allowance.
        host = estimate['host_allowance_bytes'] + 192 * vectors * 42 + 128 * vectors
        raw = 64 * vectors * 42 + (1 << 20)
        require(estimate['admits_domain'] and host < 15 << 30 and raw < 4 << 30
                and estimate['device_allowance_bytes'] < 12 << 30, 'complete capacity')
        memory.append(dict(model=m['model'], host_allowance_bytes=host,
            raw_response_allowance_bytes=raw, device_allowance_bytes=estimate['device_allowance_bytes']))
        lanes = ['native', 'previous-native', 'fp32', 'previous-fp32', 'fp4x2', 'previous-fp4x2']
        if control:
            lanes = ['native', 'fp32', 'fp4x2']
        shift = (i + 1) % len(lanes)
        lanes = lanes[shift:] + lanes[:shift]
        if i % 2:
            lanes.reverse()
        for lane in lanes:
            request = dict(settings={**settings(lane.removeprefix('previous-')),
                'iteration_limit': 20000, 'check_interval': 500, 'wall_ms': 15000},
                tensor=dict(control_interval=500 if control else 100, min_tile_nnz=128),
                fast=dict(host_reductions=True, host_preparation=True, host_certificates=True, auto_schedule=True))
            version = 9 if lane.startswith('previous-') else VERSION
            cells.append(dict(id=f'm{i:02d}-r0-t0-{lane}', model_index=i,
                lane=lane, tolerance=1e-9, repeat=0, request=request,
                binary=ref(BASE/f'scale-image-v{version}/executor')))
    deadlines = [540 if m['family'] == 'public-scpm1' else
                 330 if m['family'] == 'public-square31' else 210 for m in models]
    if control:
        deadlines = [300 if m['family'] == 'public-scpm1' else
                     180 if m['family'] == 'public-square31' else 120 for m in models]
    cpu, gpu = accounting()
    require(cpu['development'] + 4 * sum(deadlines) * NS <= CPU_CAPS['development'] * NS, 'whole CPU cohort')
    require(gpu['development'] + sum(deadlines) * NS <= GPU_CAPS['development'] * NS, 'whole GPU cohort')
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
    require(fingerprints, 'default Rust host target')
    put(out/'freeze.json', dict(mode='scale', full_solve=not control, models=models, cells=cells,
        memory_preflight=memory, job_seconds=deadlines, seconds_per_job=210,
        binary=ref(BASE/'scale-image-v6/executor'), image=ref(BASE/'scale-image-v6/tensor.cubin'),
        harness=ref(runner), design=ref(__file__), baseline_solve_seconds=15,
        baseline_worker=ref(ROOT/'tools/lp_general_scale_copt.py'),
        evidence_worker=ref(ROOT/'tools/lp_general_scale_evidence.py'),
        proofs=proofs, fingerprints=fingerprints,
        control_interval=500 if control else 100,
        control_baseline=ref(BASE/'prep-control-solve-v1/freeze.json') if control else None,
        claim='Descriptive preparation/control development: fresh single solves, 20000 updates or 15 seconds; '
              'unchanged strict certificates and CUDA. No broad FP4 superiority or confirmation. ' +
              ('500-update control changes numerical trajectories; comparison to the preceding 100-update cohort is not contemporaneous.'
               if control else 'Matched host implementation preserves numerical trajectories.')))


def freeze_large(identity):
    source = BASE/'scale-models-16000000-v3/manifest.json'
    manifest = load(source)
    models = [m for m in manifest['models'] if m['status'] == 'generated' and m['seed'] == 831001]
    require(len(models) == 2 and {m['family'] for m in models} == {'tall', 'coupled_blocks'},
            'both capacity-admitted families')
    prior = load(BASE/'prep-control-cadence-v1/freeze.json')
    for p in (ROOT/'research/lp-general-lowbit/src').rglob('*.rs'):
        require(p.read_bytes() == (BASE/f'sources/scale-cpu-v{VERSION}'/p.relative_to(ROOT)).read_bytes(),
                'admitted source differs')
    cells, memory = [], []
    for i, m in enumerate(models):
        estimate = memory_estimate(m['rows'], m['columns'], m['nonzeros'])
        vectors = m['rows'] + m['columns']
        host = estimate['host_allowance_bytes'] + (192*42 + 128)*vectors
        raw = 64*vectors*42 + (1 << 20)
        require(estimate['admits_domain'] and host < 15 << 30 and raw < 4 << 30
                and estimate['device_allowance_bytes'] < 12 << 30, 'complete large-scale capacity')
        memory.append(dict(model=m['model'], host_allowance_bytes=host,
            raw_response_allowance_bytes=raw, device_allowance_bytes=estimate['device_allowance_bytes']))
        lanes = ['previous-native', 'native', 'coarse-native', 'coarse-fp32', 'fp32',
                 'previous-fp32', 'previous-fp4x2', 'fp4x2', 'coarse-fp4x2']
        if i:
            lanes.reverse()
        for lane in lanes:
            request = dict(settings={**settings(lane.removeprefix('previous-').removeprefix('coarse-')),
                'iteration_limit': 20000, 'check_interval': 500, 'wall_ms': 30000},
                tensor=dict(control_interval=500 if lane.startswith('coarse-') else 100, min_tile_nnz=128),
                fast=dict(host_reductions=True, host_preparation=True, host_certificates=True, auto_schedule=True))
            version = 9 if lane.startswith('previous-') else VERSION
            cells.append(dict(id=f'm{i:02d}-r0-t0-{lane}', model_index=i, lane=lane,
                tolerance=1e-9, repeat=0, request=request, binary=ref(BASE/f'scale-image-v{version}/executor')))
    cpu, gpu = accounting()
    require(cpu['development'] + 4*1100*NS <= CPU_CAPS['development']*NS, 'whole large CPU cohort')
    require(gpu['development'] + 1100*NS <= GPU_CAPS['development']*NS, 'whole large GPU cohort')
    out = BASE/identity
    out.mkdir(exist_ok=False)
    runner = out/'runner.py'
    runner.write_bytes((ROOT/'tools/lp_general_scale_bench.py').read_bytes())
    put(out/'freeze.json', {**prior, 'models': models, 'cells': cells, 'full_solve': True,
        'baseline_solve_seconds': 30,
        'memory_preflight': memory, 'job_seconds': [550, 550], 'seconds_per_job': 550,
        'harness': ref(runner), 'design': ref(__file__), 'control_baseline': None,
        'capacity_manifest': ref(source), 'unsupported_models': [m for m in manifest['models'] if m['status'] != 'generated'],
        'unmeasured_capacity_models': [m for m in manifest['models'] if m['status'] == 'generated' and m['seed'] != 831001],
        'claim': 'Contemporaneous preparation/control comparison on the first seed of both capacity-admitted '
                 '16 M families: scale-image-v9/100, v12/100 and v12/500, native/FP32/FP4x2, 30-second solve limits. '
                 'Configuration changes may alter work. Twelve unsupported and four unmeasured models stay explicit; no broad claim.'})


def freeze_final(identity):
    proofs = []
    for name in ['prep-control-native-v2', 'scale-cpu-v14', 'prep-control-indexed-gpu-v1'] + [
            'prep-control-indexed-'+s+'-v1' for s in ['memcheck', 'racecheck', 'initcheck', 'synccheck']]:
        p = BASE/'resources'/(name+'.settlement.json')
        require(load(p)['status'] == 'passed', 'final admission: '+name)
        proofs.append(ref(p))
    source = BASE/'sources/scale-cpu-v14'
    paths = list((ROOT/'research/lp-general-lowbit/src').rglob('*.rs'))
    paths += list((ROOT/'research/lp-general-lowbit/tests').glob('*.rs'))
    paths += [ROOT/'research/lp-general-lowbit/Cargo.toml', ROOT/'research/lp-general-lowbit/Cargo.lock']
    paths += list((ROOT/'crates/optimizer-lp/src').glob('*.rs'))
    for p in paths:
        require(p.read_bytes() == (source/p.relative_to(ROOT)).read_bytes(), 'final admitted source differs')
    from lp_general_scale_imports import validate as validate_imports
    proofs.append(validate_imports('scale-cpu-v14'))
    prior = load(BASE/'prep-control-solve-v1/freeze.json')
    cells = []
    for c in prior['cells']:
        request = {**c['request'], 'settings': {**c['request']['settings'], 'wall_ms': 10000}}
        version = 12 if c['lane'].startswith('previous-') else 14
        cells.append({**c, 'request': request, 'binary': ref(BASE/f'scale-image-v{version}/executor')})
    deadlines = [400 if m['family'] == 'public-scpm1' else
                 270 if m['family'] == 'public-square31' else 180 for m in prior['models']]
    cpu, gpu = accounting()
    require(cpu['development'] + 4*sum(deadlines)*NS <= CPU_CAPS['development']*NS, 'complete final CPU cohort')
    require(gpu['development'] + sum(deadlines)*NS <= GPU_CAPS['development']*NS, 'complete final GPU cohort')
    out = BASE/identity
    out.mkdir(exist_ok=False)
    runner = out/'runner.py'
    runner.write_bytes((ROOT/'tools/lp_general_scale_bench.py').read_bytes())
    # The added optimizer-lp feature can create another Cargo unit fingerprint.
    # Bind the most recently built binary unit, not an older matching target.
    candidates = list((ROOT/'research/lp-general-lowbit/target/release/.fingerprint').glob('lp-general-lowbit-*/bin-lp-general-lowbit.json'))
    fingerprint = max(candidates, key=lambda p: p.stat().st_mtime_ns)
    require(load(fingerprint)['rustflags'] == [], 'final default Rust target')
    require(ref(ROOT/'research/lp-general-lowbit/target/release/lp-general-lowbit')['sha256'] ==
            ref(BASE/'scale-image-v14/executor')['sha256'], 'final built image')
    saved = out/'candidate-fingerprint.json'
    saved.write_bytes(fingerprint.read_bytes())
    put(out/'freeze.json', {**prior, 'cells': cells, 'job_seconds': deadlines, 'seconds_per_job': 180,
        'harness': ref(runner), 'design': ref(__file__), 'proofs': proofs, 'baseline_solve_seconds': 10,
        'fingerprints': [ref(saved)], 'host_features': ['optimizer-lp-host/precision-research'],
        'claim': 'Final opt-in indexed-constructor comparison: v12 versus v14 on all eight development models, '
                 'three lanes, exact arithmetic and unchanged 100-update control/500-update certificates, '
                 '20000 updates or 10 seconds. Public constructor/defaults remain unchanged. Descriptive development only.'})


def freeze_final_large(identity):
    prior = load(BASE/'prep-control-large-v1/freeze.json')
    admitted = load(BASE/'prep-control-indexed-v1/freeze.json')
    cells = []
    for c in prior['cells']:
        if c['lane'].startswith('coarse-'):
            continue
        version = 12 if c['lane'].startswith('previous-') else 14
        cells.append({**c, 'binary': ref(BASE/f'scale-image-v{version}/executor')})
    cpu, gpu = accounting()
    require(cpu['development'] + 4*900*NS <= CPU_CAPS['development']*NS, 'complete final large CPU cohort')
    require(gpu['development'] + 900*NS <= GPU_CAPS['development']*NS, 'complete final large GPU cohort')
    out = BASE/identity
    out.mkdir(exist_ok=False)
    runner = out/'runner.py'
    runner.write_bytes((ROOT/'tools/lp_general_scale_bench.py').read_bytes())
    put(out/'freeze.json', {**prior, 'cells': cells, 'job_seconds': [450, 450], 'seconds_per_job': 450,
        'harness': ref(runner), 'design': ref(__file__), 'proofs': admitted['proofs'],
        'fingerprints': admitted['fingerprints'], 'host_features': admitted['host_features'],
        'claim': 'Final indexed-constructor comparison, v12 versus v14, on seed 831001 of both capacity-admitted '
                 '16 M families; unchanged 100-update control, strict certificates and arithmetic, all three lanes. '
                 'Twelve unsupported and four unmeasured capacity models retained. No broad claim.'})


def control_report(identity, output, compact):
    from lp_general_scale_report import campaign
    data = campaign(identity)
    coarse = any(r['lane'].startswith('coarse-') for r in data['rows'])
    contemporaneous = coarse or any(r['lane'].startswith('previous-') for r in data['rows'])
    baseline = data if contemporaneous else campaign('prep-control-solve-v1')
    keyed = {(r['model_index'], r['lane']): r for r in baseline['rows']}
    comparisons = []
    for r in data['rows']:
        if r['lane'].startswith('previous-') or (coarse and not r['lane'].startswith('coarse-')):
            continue
        lane = r['lane'].removeprefix('coarse-')
        before = keyed[(r['model_index'], ('previous-' if contemporaneous and not coarse else '') + lane)]
        comparisons.append(dict(model_index=r['model_index'], family=r['family'], lane=lane,
            before_certified=before['certified'], after_certified=r['certified'],
            before_logical=before['logical'], after_logical=r['logical'],
            before_fp4_share=before['fp4_share'], after_fp4_share=r['fp4_share'],
            supervised=before['supervised'] and r['supervised'],
            primary_ratio=before['primary_seconds']/r['primary_seconds'],
            before_primary_seconds=before['primary_seconds'], after_primary_seconds=r['primary_seconds'],
            cost_ratios={k: before['cost_seconds'][k]/v if v else None for k,v in r['cost_seconds'].items()}))
    certified = [r for r in comparisons if r['before_certified'] and r['after_certified'] and r['supervised']]
    data['control_comparisons'] = comparisons
    data['control_summary'] = dict(jointly_certified=len(certified),
        contemporaneous=contemporaneous,
        complete_median=statistics.median(r['primary_ratio'] for r in certified) if certified else None,
        before_certified=sum(r['before_certified'] for r in comparisons),
        after_certified=sum(r['after_certified'] for r in comparisons))
    data['claim'] = load(BASE/identity/'freeze.json')['claim']
    put(output, data)
    columns = ['id', 'model_index', 'lane', 'repeat', 'status', 'certified', 'supervised',
               'primary_seconds', 'independent_seconds', 'audit_seconds', 'logical', 'physical',
               'fp4_share', 'nonzeros', 'cost_seconds']
    put(compact, {**{k:v for k,v in data.items() if k not in ['rows', 'comparisons']},
        'full_local_results': ref(output), 'cell_columns': columns,
        'cells': [[r.get(k) for k in columns] for r in data['rows']]})
    print(data['control_summary'], flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['device', 'freeze', 'freeze-large', 'freeze-final', 'freeze-final-large', 'report', 'control-admission', 'control-report'])
    p.add_argument('--id', required=True)
    p.add_argument('--output')
    p.add_argument('--compact-output')
    p.add_argument('--control', action='store_true')
    p.add_argument('--version', type=int, choices=[12, 14], default=12)
    a = p.parse_args()
    if a.action == 'device':
        device(a.version)
    elif a.action == 'freeze':
        freeze(a.id, a.control)
    elif a.action == 'control-admission':
        control_admission(a.id)
    elif a.action == 'freeze-large':
        freeze_large(a.id)
    elif a.action == 'freeze-final':
        freeze_final(a.id)
    elif a.action == 'freeze-final-large':
        freeze_final_large(a.id)
    elif a.action == 'control-report':
        control_report(a.id, a.output, a.compact_output)
    else:
        report(a.id, a.output, a.compact_output)
