"""Complete only unexecuted baseline cells under SPEC-0023; preserve v1-v4."""
import argparse
import copy
import inspect
import math
import os
from pathlib import Path
import random
import statistics
import subprocess
import sys
import tarfile

from lp_baseline_common_v5 import (BASE, PRIOR, ROOT, CPU_CAPS, GPU_CAPS, DEVICE,
    PRIOR_ACCOUNTING, PRIOR_ACCOUNTING_SHA256, checked, load, put, ref, require,
    verify_certificate)
from lp_baseline_budget_v5 import accounting, run as reserve
from lp_baseline_native_policy import (comparison_pass, native_return_pass,
                                       pending_screening, quality_summary)
from lp_baseline_transport import launch
from validate_artifacts import validator

MANIFEST = BASE / 'manifest.json'


def prior_trials(manifest):
    return {j['id']: load(PRIOR/'trials'/(j['id']+'.json')) for j in manifest['jobs']}


def freeze():
    import lp_baseline_study_v4 as old_study
    import lp_baseline_adapters_v3 as old_adapter
    import lp_baseline_adapters_v5 as new_adapter
    import lp_baseline_budget_v4 as old_budget
    require(not MANIFEST.exists(), 'continuation already frozen')
    old = load(PRIOR/'manifest.json')
    old_study.verify_freeze(old)
    require(ref(PRIOR_ACCOUNTING)['sha256'] == PRIOR_ACCOUNTING_SHA256, 'prior accounting changed')
    ledger = load(PRIOR_ACCOUNTING)
    cpu, gpu = old_budget.accounting()
    require(cpu == ledger['cpu_charged_ns'] and gpu == ledger['gpu_charged_ns'], 'closed charges differ')
    require(sum(gpu.values()) + GPU_CAPS['screening']*10**9 <= 3600*10**9, 'cumulative GPU cap')
    for name in ('copt', 'retained', 'result', 'native_bounds', 'native_status'):
        require(getattr(new_adapter, name) is getattr(old_adapter, name), 'non-cuOpt adapter changed')
    prefix = lambda f: inspect.getsource(f).split('    solution = lp.Solve', 1)[0]
    require(prefix(old_adapter.cuopt) == prefix(new_adapter.cuopt), 'cuOpt input/settings/Solve prefix changed')
    for name in ('native-return-tests', 'native-return-api'):
        require(load(BASE/'resources'/(name+'.settlement.json'))['status']=='passed', 'new policy acceptance incomplete')
    require('retained.main()' in (ROOT/'tools/lp_baseline_worker_v5.py').read_text(), 'worker bridge differs')
    trials = prior_trials(old)
    pending = pending_screening(old['jobs'], trials)
    require(len(pending) == 117, 'pending roster changed')
    require(sum(j['configuration'].startswith('cuopt-') for j in pending) == 96, 'cuOpt roster changed')
    BASE.mkdir(parents=True, exist_ok=True)
    paths = subprocess.check_output(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], cwd=ROOT).decode().split('\0')
    paths = sorted(set(p for p in paths if p and (ROOT/p).is_file()))
    sources = [ref(ROOT/p) for p in paths]
    with tarfile.open(BASE/'source.tar.gz', 'x:gz') as archive:
        for p in paths:
            archive.add(ROOT/p, arcname=p, recursive=False)
    source_ref = put(BASE/'sources.json', dict(files=sources, archive=ref(BASE/'source.tar.gz')))
    m = copy.deepcopy(old)
    m.update(id='gpup-external-baseline-v5', sources=source_ref,
        adapter=ref(ROOT/'tools/lp_baseline_adapters_v5.py'),
        decision=ref(ROOT/'docs/decisions/ADR-0052-baseline-native-return.md'),
        acceptance_policy=ref(ROOT/'docs/specifications/SPEC-0023-baseline-native-return.md'),
        prior_manifest=ref(PRIOR/'manifest.json'), prior_accounting=ref(PRIOR_ACCOUNTING),
        cpu_caps_seconds=CPU_CAPS, gpu_caps_seconds=GPU_CAPS,
        pending_job_ids=[j['id'] for j in pending],
        reused_evidence=[ref(PRIOR/'manifest.json'), ref(PRIOR/'report.json'), ref(PRIOR_ACCOUNTING)]
            + [ref(PRIOR/'trials'/(j['id']+'.json')) for j in old['jobs']])
    m['legacy_checkers'] = [old['checker'], *old['legacy_checkers']]
    for j in m['jobs']:
        j['directory'] = str((BASE/'jobs'/j['id']).relative_to(ROOT))
    validator('lp-baseline-execution-v5.schema.json').validate(m)
    put(MANIFEST, m)
    for j in m['jobs']:
        if j['id'] not in m['pending_job_ids']:
            put(BASE/'trials'/(j['id']+'.json'), dict(trials[j['id']], job=j,
                reused_trial=ref(PRIOR/'trials'/(j['id']+'.json')),
                reuse_basis='Settled original result retained without solve or certificate rerun; strict outcomes unchanged.'))
    put(BASE/'release.json', dict(manifest=ref(MANIFEST), pending_cells=117,
        reused_screening=123, cuopt_release='user-authorized native-return policy',
        strict_admission='All original outcomes retained; no old refusal relabeled as passing.',
        cpu_new_cap=sum(CPU_CAPS.values()), gpu_new_cap=sum(GPU_CAPS.values()),
        gpu_prior_ns=ledger['gpu_total_ns'], gpu_total_cap=3600))
    print('Frozen 117 pending cells; 123 settled screening results reused.', flush=True)


def verify_freeze(m):
    validator('lp-baseline-execution-v5.schema.json').validate(m)
    require(m['cpu_caps_seconds'] == CPU_CAPS and m['gpu_caps_seconds'] == GPU_CAPS, 'resource authority changed')
    require(m['device_uuid'] == DEVICE, 'device changed')
    for key in ('sources', 'adapter', 'environment', 'checker', 'project_binary',
                'project_configuration', 'historical_ledger', 'decision',
                'acceptance_policy', 'prior_manifest', 'prior_accounting', 'proposal'):
        checked(m[key])
    old = load(checked(m['prior_manifest']))
    require(m['configurations'] == old['configurations'], 'native settings changed')
    require(m['cpu_affinity'] == old['cpu_affinity'], 'affinity changed')
    trials = prior_trials(old)
    require(m['pending_job_ids'] == [j['id'] for j in pending_screening(old['jobs'], trials)], 'pending roster differs')
    require([(j['id'], j['model'], j['configuration'], j['repetition']) for j in m['jobs']]
            == [(j['id'], j['model'], j['configuration'], j['repetition']) for j in old['jobs']], 'job order/model differs')
    for f in load(checked(m['sources']))['files']:
        if f['path'].startswith(('crates/', 'cuda/', 'research/', 'tools/', 'schemas/', 'tests/', 'benchmarks/')):
            checked(f)
    for f in m['reused_evidence'] + m['project_images']:
        checked(f)
    environment = load(checked(m['environment']))
    for key in ('native_and_python_files', 'validator_overlay', 'compiled_validator', 'validator_wheel'):
        for f in environment[key]:
            checked(f)
    checked(environment['highs_library'])
    require(Path(sys.executable).resolve().read_bytes() == checked(environment['python_runtime']).read_bytes(), 'Python runtime changed')
    for path, sha in {(j['model']['path'], j['model']['sha256']) for j in m['jobs']}:
        checked(dict(path=path, sha256=sha))


def launched(job_id):
    m = load(MANIFEST)
    j = next(j for j in m['jobs'] if j['id'] == job_id)
    c = next(c for c in m['configurations'] if c['id'] == j['configuration'])
    interpreter = Path(m['interpreters'][c['solver']])
    if not interpreter.is_absolute():
        interpreter = ROOT/interpreter
    env = {**os.environ, 'PYTHONPATH': str(PRIOR/'python-support'), 'PYTHONDONTWRITEBYTECODE': '1'}
    outcome = launch([str(interpreter), '-B', str(ROOT/'tools/lp_baseline_worker_v5.py'), str(MANIFEST), job_id],
                     env, BASE/'logs'/job_id)
    put(BASE/'clocks'/(job_id+'.json'), outcome)
    return outcome['returncode']


def screening():
    m = load(MANIFEST)
    verify_freeze(m)
    configs = {c['id']: c for c in m['configurations']}
    for j in m['jobs']:
        if j['id'] not in m['pending_job_ids']:
            continue
        path = BASE/'trials'/(j['id']+'.json')
        if path.exists():
            continue
        try:
            settlement = reserve(j['id'], 'screening', 60, configs[j['configuration']]['gpu'],
                [sys.executable, '-B', str(Path(__file__).resolve()), '_launch', j['id']])
        except ValueError as error:
            put(path, dict(job=j, status='unexecuted', reason=str(error)))
            if 'exhausted' in str(error):
                continue
            raise
        result = ROOT/j['directory']/'worker-result.json'
        clock = BASE/'clocks'/(j['id']+'.json')
        put(path, dict(job=j, status=settlement['status'],
            settlement=ref(BASE/'resources'/(j['id']+'.settlement.json')),
            result=ref(result) if result.exists() else None,
            clock=ref(clock) if clock.exists() else None))
        print(j['id'], settlement['status'], flush=True)
        require(not settlement['overrun'], 'resource overrun closes execution')


def trial_row(j, t, m):
    configs = {c['id']: c for c in m['configurations']}
    config = configs[j['configuration']]
    row = dict(id=j['id'], phase=j['phase'], configuration=j['configuration'], model=j['model_id'],
        repetition=j['repetition'], status=t['status'], reason=t.get('reason'),
        trial=ref(BASE/'trials'/(j['id']+'.json')), reused=bool(t.get('reused_trial')),
        certified=False, native_return_pass=None, comparison_pass=False,
        gpu_confirmed=False, elapsed_ns=None, native_solve_ns=None,
        transport=None, native_status=None, native_return=None, quality=None)
    if t.get('clock'):
        row['elapsed_ns'] = load(checked(t['clock']))['elapsed_ns']
    if t.get('result'):
        results = load(checked(t['result']))['results']
        if results:
            f = results[-1]
            cert = load(checked(f['certificate']))
            checker = next(c for c in [m['checker'], *m['legacy_checkers']]
                           if c['sha256'] == cert['checker_binary_sha256'])
            cert = verify_certificate(f['certificate'], f['candidate'], f['original'], checker)
            require(cert['accepted'] == f['accepted'], 'worker certificate outcome differs')
            endpoint = load(checked(f['endpoint']))
            require(endpoint['checker']['receipt'] == f['certificate'], 'endpoint certificate differs')
            row.update(certified=t['status']=='passed' and cert['accepted'],
                gpu_confirmed=f['gpu_confirmed'], quality=quality_summary(cert),
                transport=endpoint['transport'], native_status=endpoint['native_status'],
                native_solve_ns=endpoint['native_solve_ns'], endpoint=f['endpoint'], certificate=f['certificate'],
                adapter_error=f['error'], iterations=f['iterations'])
    # A native return may survive a later worker/checker failure. Never lose it.
    native_path = ROOT/j['directory']/'solve/vendor-return.json'
    if config['solver'] == 'cuopt' and native_path.exists():
        native = load(native_path)
        require(native['original_sha256'] == j['model']['sha256'], 'native original binding')
        require(native['parameters'] == dict(config['parameters'], time_limit=40), 'native effective settings')
        checked(native['canonical'])
        require(native['native_return_pass'] == native_return_pass(native), 'native return policy differs')
        row.update(native_return_pass=native_return_pass(native), native_return=ref(native_path),
                   native_observation=native)
    complete = t['status'] == 'passed' and row['transport'] == 'completed'
    row['comparison_pass'] = comparison_pass(config['solver'], complete, row['certified'], row.get('native_observation'))
    row['acceptance_basis'] = 'cuopt_native_return' if config['solver']=='cuopt' else 'strict_certificate'
    row['transport_family'] = ('generic-v2' if row['reused'] and j['model_id'].startswith('gpup-development-')
                               else 'compiled-buffered-v4')
    return row


def paired_comparisons(rows, configs):
    index = {(r['model'], r['configuration'], r['repetition']): r for r in rows}
    comparisons = []
    for model in sorted({r['model'] for r in rows}):
        for c in configs:
            if c['id'] == 'project-tuned-fp64':
                continue
            for policy in ('certified', 'comparison_pass'):
                logs = []
                transport_match = True
                for rep in range(3):
                    pair = [index.get((model, name, rep)) for name in ('project-tuned-fp64', c['id'])]
                    if all(r and r[policy] and r['elapsed_ns'] for r in pair):
                        if policy == 'certified' and (not pair[0]['gpu_confirmed'] or (c['gpu'] and not pair[1]['gpu_confirmed'])):
                            continue
                        logs.append(math.log(pair[0]['elapsed_ns']/pair[1]['elapsed_ns']))
                        transport_match &= pair[0]['transport_family'] == pair[1]['transport_family']
                value = dict(model=model, configuration=c['id'], reference='project-tuned-fp64',
                    policy=policy, complete_pairs=len(logs), transport_matched=transport_match,
                    quality_matched=policy=='certified' or c['solver']!='cuopt',
                    median_ratio=None, confidence95=None)
                if len(logs)==3 and transport_match:
                    rng = random.Random(17111)
                    boot = sorted(statistics.median([rng.choice(logs) for _ in logs]) for _ in range(10000))
                    value.update(median_ratio=math.exp(statistics.median(logs)),
                        confidence95=[math.exp(boot[249]), math.exp(boot[9749])])
                comparisons.append(value)
    return comparisons


def report():
    m = load(MANIFEST)
    rows = []
    for j in m['jobs']:
        p = BASE/'trials'/(j['id']+'.json')
        require(p.exists(), 'missing disposition: '+j['id'])
        t = load(p)
        if j['phase'] == 'screening':
            rows.append(trial_row(j, t, m))
    reference = {(r['model'],r['repetition']):r for r in rows
                 if r['configuration']=='project-tuned-fp64' and r['certified']}
    for r in rows:
        other = reference.get((r['model'],r['repetition']))
        r['objective_deviation'] = None
        if other and r['quality'] and r['quality']['objective'] is not None:
            difference = r['quality']['objective'] - other['quality']['objective']
            r['objective_deviation'] = dict(reference=other['id'], signed=difference,
                absolute=abs(difference), relative_to_one_plus_abs_reference=abs(difference)/(1+abs(other['quality']['objective'])),
                meaning='Objective deviation only; not an optimality gap when feasibility/certification is absent.')
    summaries = []
    for model in sorted({r['model'] for r in rows}):
        for c in m['configurations']:
            selected = [r for r in rows if r['model']==model and r['configuration']==c['id']]
            item = dict(model=model, configuration=c['id'], planned=3,
                executed=sum(r['status']!='unexecuted' for r in selected),
                native_return_passes=sum(r['native_return_pass'] is True for r in selected),
                certified=sum(r['certified'] for r in selected),
                comparison_passes=sum(r['comparison_pass'] for r in selected),
                gpu_confirmed=sum(r['gpu_confirmed'] for r in selected))
            for policy in ('certified', 'comparison_pass'):
                times = [r['elapsed_ns']/1e9 for r in selected if r[policy] and r['elapsed_ns']]
                item[policy+'_median_seconds'] = statistics.median(times) if len(times)==3 else None
            summaries.append(item)
    cpu, gpu = accounting()
    put(BASE/'report.json', dict(schema_version=1, kind='lp-baseline-native-return-report',
        manifest=ref(MANIFEST), rows=rows, summary=summaries,
        planned=240, executed=sum(r['status']!='unexecuted' for r in rows),
        certified=sum(r['certified'] for r in rows), comparison_passes=sum(r['comparison_pass'] for r in rows),
        full_comparison_complete=all(r['status']!='unexecuted' for r in rows),
        comparisons=paired_comparisons(rows, m['configurations']),
        cpu_snapshot_ns=cpu, gpu_snapshot_ns=gpu,
        limitations=['cuOpt native-return passes are not strict certificate passes.',
            'Generated development models only; no held-out or general commercial-solver ranking.',
            'Reused small-model v2 versus new v5 transport is unmatched; its paired ratio is withheld.',
            'Snapshot accounting can include the active report reservation; final settlement is authoritative.']))
    print('Report written; full roster and separate native/strict outcomes retained.', flush=True)


def main():
    if len(sys.argv)==3 and sys.argv[1]=='_launch':
        return launched(sys.argv[2])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['freeze', 'screening', 'report'])
    command = parser.parse_args().command
    {'freeze': freeze, 'screening': screening, 'report': report}[command]()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
