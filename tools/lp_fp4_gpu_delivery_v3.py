"""Additive recovery delivery; verifies retained evidence without rerunning cells."""
import hashlib
import json
import statistics

from lp_fp4_gpu_common import ROOT, CPU_CAPS, GPU_CAPS, load, put, ref, checked, require
from lp_fp4_gpu_budget import accounting
from lp_fp4_gpu_study_v3 import BASE, PREVIOUS_BASE, PRIOR_BASE, MANIFEST, cells

DEST = ROOT / 'docs/benchmarks/data'
GATES = ('primitive', 'device', 'memcheck', 'racecheck', 'initcheck', 'synccheck')


def verify_manifest(path):
    m = load(path)
    for item in m['sources']:
        checked(item)
    for key in ('binary', 'image', 'build', 'ptx', 'sass', 'inventory',
                'cpu_acceptance', 'kernel_path_bridge', 'recovery_release',
                'prior_failed_manifest', 'correction_test', 'correction_build',
                'previous_manifest', 'synchronization_audit', 'synchronization_build'):
        if key in m:
            checked(m[key])
    return m


def resources():
    cpu, gpu = accounting()
    rows = []
    for path in sorted((PRIOR_BASE / 'resources').glob('*.reservation.json')):
        settlement = path.with_name(path.name.replace('.reservation.json', '.settlement.json'))
        report = path.with_name(path.name.replace('.reservation.json', '.resource.json'))
        item = load(settlement) if settlement.exists() else load(path)
        empty = None
        if report.exists():
            receipt = load(report)
            empty = (receipt.get('guardian_cleanup', {}).get('empty')
                     and receipt.get('result', {}).get('cleanup', {}).get('empty'))
            require(empty, 'nonempty cleanup receipt: ' + str(path))
        rows.append(dict(reservation=ref(path),
                         settlement=ref(settlement) if settlement.exists() else None,
                         cleanup_empty=empty, status=item.get('status', 'unsettled'),
                         charged=item))
    require(all(cpu[p] <= cap * 10**9 for p, cap in CPU_CAPS.items()), 'CPU cap exceeded')
    require(all(gpu[p] <= cap * 10**9 for p, cap in GPU_CAPS.items()), 'GPU cap exceeded')
    return dict(cpu_ns=cpu, gpu_ns=gpu, cpu_cap_seconds=CPU_CAPS,
                gpu_cap_seconds=GPU_CAPS, total_cpu_ns=sum(cpu.values()),
                total_gpu_ns=sum(gpu.values()), resources=rows,
                note='Active delivery reservation counted in full. Final settled accounting is additive; all failed charges retained.')


def main():
    before = load(PRIOR_BASE / 'prior-tracked.json')
    differences = [p for p, h in before.items() if hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != h]
    require(not differences, 'historical source/evidence mutation: ' + str(differences))
    verify_manifest(PRIOR_BASE / 'manifest.json')
    verify_manifest(PREVIOUS_BASE / 'manifest.json')
    m = verify_manifest(MANIFEST)
    require(m['cells'] == cells(), 'frozen cell roster differs')
    gates = {}
    for name in GATES:
        path = BASE / (name + '.json')
        suite = load(path)
        require(suite['status'] == 'passed', 'gate did not pass: ' + name)
        expected, reused = dict(primitive=(50, 10), device=(75, 15), memcheck=(20, 4), racecheck=(20, 4), initcheck=(24, 0), synccheck=(24, 0))[name]
        require(len(suite.get('reused_control_rows', [])) == reused, 'retained coverage: ' + name)
        require(len(suite['rows']) == expected, 'gate coverage: ' + name)
        for row in suite['rows'] + suite.get('reused_control_rows', []):
            for key in ('input', 'output', 'stdout', 'stderr'):
                checked(row[key])
            require(row['returncode'] == 0, 'nonzero worker return')
        if name == 'primitive':
            require(len(suite['reused_control_rows']) == 10, 'retained control coverage')
        gates[name] = dict(status='passed', cases=expected,
                           reused_cases=len(suite.get('reused_control_rows', [])), receipt=ref(path))
    rows = []
    receipts = []
    for path in sorted(BASE.glob('profiles-*.json')):
        suite = load(path)
        require(suite['status'] == 'passed' and len(suite['rows']) == 24, 'profile suite coverage')
        for row in suite['rows']:
            for key in ('input', 'output', 'stdout', 'stderr'):
                checked(row[key])
            require(row['returncode'] == 0 and row['certified'] is False, 'profile outcome')
            c = row['counts']
            expected = dict(split=128, fused=32, persistent=1, roundtrip=96)[row['variant']]
            require(c['iteration_launches'] == expected, 'launch attribution')
            require(c['iteration_copies'] == (64 if row['variant'] == 'roundtrip' else 0), 'copy attribution')
            out = load(checked(row['output']))
            require(out['status'] == 'completed' and out['physical_updates'] == 32
                    and out['logical_updates'] == 32, 'profile update count')
        rows.extend(suite['rows'])
        receipts.append(ref(path))
    by_id = {r['id']: r for r in rows}
    require(len(rows) == len(by_id) == 216 and set(by_id) == {r['id'] for r in cells()}, 'full profile coverage')
    summaries = []
    for name in ('dense-32', 'irregular-29', 'dense-2048'):
        for variant in ('split', 'fused', 'persistent', 'roundtrip'):
            native = [r for r in rows if r['workload'] == name and r['variant'] == variant and r['format'] == 64]
            for f, k in ((64, 1), (8, 4), (16, 2), (4, 2), (4, 4), (4, 8)):
                selected = [r for r in rows if r['workload'] == name and r['variant'] == variant and r['format'] == f and r['components'] == k]
                require({r['repetition'] for r in selected} == {0, 1, 2}, 'repetition coverage')
                cold = [r['cold_ns'] for r in selected]
                iteration = [r['phases_ns']['iteration'] for r in selected]
                summary = dict(workload=name, variant=variant, format=f, components=k,
                               cold_median_ns=statistics.median(cold), cold_range_ns=[min(cold), max(cold)],
                               iteration_median_ns=statistics.median(iteration), iteration_range_ns=[min(iteration), max(iteration)],
                               cold_speedup=statistics.median(r['cold_ns'] for r in native) / statistics.median(cold),
                               iteration_speedup=statistics.median(r['phases_ns']['iteration'] for r in native) / statistics.median(iteration),
                               max_observed_error=max(r['observation']['max_absolute'] for r in selected),
                               max_primal_residual=max(r['original_a_primal_residual'] for r in selected),
                               counts=selected[0]['counts'], work=selected[0]['work'],
                               phase_median_ns={p: statistics.median(r['phases_ns'][p] for r in selected) for p in selected[0]['phases_ns']},
                               preparation_median_ns=statistics.median(r['preparation_ns'] for r in selected))
                require(all(r['counts'] == summary['counts'] and r['work'] == summary['work'] for r in selected), 'work counter variation')
                summaries.append(summary)
    result = dict(kind='fp4-gpu-pilot-result-v3', status='complete_empirical_pilot',
                  completed=216, planned=216, certified=0, selected_solver_preset=None,
                  cells=[dict(c, disposition='completed', result=by_id[c['id']]) for c in cells()],
                  summaries=summaries, gates=gates, profile_receipts=receipts,
                  manifest=ref(MANIFEST), retained_v1_result=ref(DEST / 'fp4-gpu-pilot-result-v1.json'),
                  retained_diagnosis=ref(DEST / 'fp4-gpu-pilot-diagnosis-v1.json'),
                  retained_v2_diagnosis=ref(DEST / 'fp4-gpu-pilot-race-diagnosis-v2.json'),
                  historical_files_preserved=len(before), historical_hashes=ref(PRIOR_BASE / 'prior-tracked.json'),
                  limitations=[
                      'Only independent 32-variable blocks and 32 updates; no coupled sparse LP integration.',
                      'Empirical iterate differences and primal residuals are not enclosures or certificates.',
                      'CUDA stream span includes host submission gaps; iteration wall includes event management and synchronization.',
                      'Cold cost includes CPU preparation and worker process execution. Coordinator request serialization, postprocess reference checking and protocol receipt work are excluded.',
                      'No endpoint certification cost is measured; no time-to-certificate claim follows.',
                      'Three repetitions give observed ranges, not statistically established acceleration.',
                      'Matrix preparation uses the exact rational Python oracle, not an optimized production encoder.',
                      'Safety coverage uses injected sticky refusal and scheduled cancellation on bounded pilot inputs, not arbitrary solver inputs.'])
    put(DEST / 'fp4-gpu-pilot-result-v3.json', result)
    account = resources()
    put(DEST / 'fp4-gpu-pilot-accounting-v3.json', account)
    put(DEST / 'fp4-gpu-pilot-evidence-v3.json', dict(
        manifest=m, previous_manifest=load(PREVIOUS_BASE / 'manifest.json'), original_manifest=load(PRIOR_BASE / 'manifest.json'),
        compiler=load(PRIOR_BASE / 'build-v3/receipt.json'),
        software_acceptance={name: load(PRIOR_BASE / ('resources/' + name + '.settlement.json')) for name in (
            'research-build-v2', 'native-acceptance-v2', 'native-completion-v3',
            'packing-correction-cpu-v2', 'corrected-compile-v2',
            'synchronization-audit-v3', 'synchronization-compile-v3')},
        gates={name: load(BASE / (name + '.json')) for name in GATES}))
    print(json.dumps(dict(status=result['status'], completed=216,
                          cpu_seconds=account['total_cpu_ns']/1e9,
                          gpu_seconds=account['total_gpu_ns']/1e9)))


if __name__ == '__main__':
    main()
