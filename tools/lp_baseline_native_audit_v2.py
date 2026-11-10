"""Final metadata-only audit of SPEC-0023 delivery; never invokes a solver."""
import ast
import hashlib
from pathlib import Path
import re
import subprocess
import sys

import yaml

from lp_baseline_common_v5 import (BASE, ROOT, PRIOR_ACCOUNTING,
    PRIOR_ACCOUNTING_SHA256, checked, load, put, ref, require)
from lp_baseline_native_policy import comparison_pass, native_return_pass
from lp_baseline_study_v5 import verify_freeze


def main():
    manifest = load(BASE/'manifest.json')
    verify_freeze(manifest)
    require(ref(PRIOR_ACCOUNTING)['sha256'] == PRIOR_ACCOUNTING_SHA256,
            'historical accounting changed')
    before = load('/tmp/ai-optimizer-diagnosis-evidence-before.json')
    for path, sha in before.items():
        require(hashlib.sha256(Path(path).read_bytes()).hexdigest() == sha,
                'historical evidence changed: '+path)
    api = load(ROOT/'docs/benchmarks/data/baseline-spec-api-inspection-v1.json')
    for f in api['source_files']:
        # The original inspection explicitly includes two external COPT sources.
        p = Path(f['path'])
        if not p.is_absolute():
            p = ROOT/p
        require(hashlib.sha256(p.read_bytes()).hexdigest() == f['sha256'],
                'inspected API source changed: '+str(p))
    ledger = checked(manifest['historical_ledger'])
    require(len(ledger.read_bytes().splitlines()) == 17438, 'ledger length differs')
    frozen = load(checked(manifest['sources']))['files']
    preserved = []
    for f in frozen:
        if (f['path'].startswith('docs/benchmarks/data/')
                or f['path'].startswith(('docs/decisions/', 'docs/specifications/'))
                or f['path'] == 'docs/benchmarks/lp-external-baseline-gpup-baseline.md'):
            checked(f)
            preserved.append(f)

    report = load(BASE/'report.json')
    rows = report['rows']
    jobs = {j['id']: j for j in manifest['jobs'] if j['phase']=='screening'}
    require(len(jobs)==len(rows)==240, 'planned denominator')
    require(set(jobs)=={r['id'] for r in rows}, 'complete exact roster')
    require(all(r['status']!='unexecuted' for r in rows), 'unexecuted cell')
    require(sum(r['reused'] for r in rows)==123, 'reuse count')
    require(sum(not r['reused'] for r in rows)==117, 'new count')
    require(report['full_comparison_complete'], 'incomplete report')
    require(report['executed']==240, 'attempt count')
    for key in ('certified', 'comparison_pass'):
        target = 'comparison_passes' if key=='comparison_pass' else key
        require(sum(r[key] for r in rows)==report[target], 'summary count')
    configs = {c['id']: c for c in manifest['configurations']}
    native_refs = []
    raw_refs = []
    for row in rows:
        trial = load(checked(row['trial']))
        require(trial['status']==row['status'], 'trial disposition differs')
        if trial.get('reused_trial'):
            old = load(checked(trial['reused_trial']))
            for key in ('status', 'settlement', 'clock', 'result', 'reason'):
                require(old.get(key)==trial.get(key), 'reused evidence differs')
        native = row.get('native_observation')
        if native:
            require(load(checked(row['native_return']))==native, 'native observation differs')
            require(row['native_return_pass']==native_return_pass(native), 'native pass differs')
            native_refs.append(row['native_return'])
        complete = row['status']=='passed' and row['transport']=='completed'
        require(row['comparison_pass']==comparison_pass(
            configs[row['configuration']]['solver'], complete, row['certified'], native),
            'comparison policy differs')
        if row['certified']:
            require(complete and row['quality']['certified'], 'certificate relabeling')
        if trial.get('result'):
            result = load(checked(trial['result']))
            for item in result['results']:
                for key in ('endpoint', 'certificate', 'candidate', 'original', 'execution'):
                    checked(item[key])
                if native:
                    execution = load(checked(item['execution']))
                    require(execution['native']['native_return']==row['native_return'],
                            'completed endpoint native binding differs')
                    checked(execution['native']['raw_vectors'])
                    raw_refs.append(execution['native']['raw_vectors'])
        elif native:
            # Failed deliveries retain partial observations without inventing an endpoint.
            raw = ROOT/jobs[row['id']]['directory']/'solve/vendor-vectors.json'
            if raw.exists():
                raw_refs.append(ref(raw))
    for item in report['summary']:
        selected = [r for r in rows if (r['model'],r['configuration'])==
                    (item['model'],item['configuration'])]
        require(len(selected)==3, 'replicate denominator')
        for key in ('certified', 'comparison_pass'):
            count = sum(r[key] for r in selected)
            count_key = 'comparison_passes' if key=='comparison_pass' else key
            require(item[count_key]==count, 'replicate count')
            require((item[key+'_median_seconds'] is not None)==(count==3),
                    'median drops failed repetitions')
    for item in report['comparisons']:
        require((item['median_ratio'] is not None)==
                (item['complete_pairs']==3 and item['transport_matched']),
                'paired ratio eligibility')
        if item['policy']=='comparison_pass' and item['configuration'].startswith('cuopt-'):
            require(not item['quality_matched'], 'native tier labeled quality matched')
    require((BASE/'report.json').read_bytes()==
            (ROOT/'docs/benchmarks/data/external-baseline-native-result-v1.json').read_bytes(),
            'machine delivery differs')
    observations_path = ROOT/'docs/benchmarks/data/external-baseline-native-observations-v1.json'
    observations = load(observations_path)
    require(observations['report']==ref(BASE/'report.json'), 'native limit report binding')
    require(observations['solver_runs']==observations['certificate_recomputations']==0,
            'native limit observations must reuse evidence')
    require(len(observations['project_mixed'])==6, 'native limit roster')
    for item in observations['project_mixed']:
        native = load(checked(item['source']))['endpoint']
        require(item['termination']==native['record']['termination'] and
                item['native_assessment']==native['assessment'], 'native limit observation differs')
    findings = load(BASE/'delivery-findings.json')
    checked(findings['source'])
    checked(findings['human_report'])
    require(findings['observations']==ref(observations_path), 'findings observation binding')

    settlements = []
    pending = []
    for p in sorted((BASE/'resources').glob('*.reservation.json')):
        s = p.with_name(p.name.replace('.reservation.json','.settlement.json'))
        if not s.exists():
            pending.append(p.name)
            continue
        value = load(s)
        require(not value['overrun'], 'resource overrun')
        receipt = load(checked(value['resource']))
        require(receipt['guardian_cleanup']['empty'] and receipt['result']['cleanup']['empty'],
                'cleanup not empty')
        settlements.append(ref(s))
    require(pending==['native-final-delivery-audit-v2.reservation.json'],
            'only this audit may be pending')

    backlog = yaml.safe_load((ROOT/'state/backlog.yaml').read_text())
    tasks = {t['id']:t for t in backlog['tasks']}
    require(len(tasks)==len(backlog['tasks'])==50, 'task roster differs')
    visiting = set()
    done = set()
    def visit(name):
        require(name in tasks and name not in visiting, 'invalid/cyclic dependency')
        if name in done:
            return
        visiting.add(name)
        for dependency in tasks[name]['depends_on']:
            visit(dependency)
        visiting.remove(name)
        done.add(name)
    for name in tasks:
        visit(name)
    require(backlog['next_ready_task']=='GPUP-RESIDENT2', 'next task differs')
    require(tasks['GPUP-RESIDENT2']['status']=='ready', 'resident task not ready')
    require(all(tasks[d]['status']=='complete' for d in tasks['GPUP-RESIDENT2']['depends_on']),
            'resident dependency incomplete')
    require(tasks['GPUP-8']['status']!='complete' and 'GPUP-8' in tasks['GPUP-9']['depends_on'],
            'historical scientific gate changed')
    subprocess.run(['git','diff','--check'],cwd=ROOT,check=True)
    new_paths = [ROOT/'tools'/name for name in (
        'lp_baseline_native_policy.py','lp_baseline_common_v5.py','lp_baseline_budget_v5.py',
        'lp_baseline_adapters_v5.py','lp_baseline_worker_v5.py','lp_baseline_study_v5.py',
        'lp_baseline_native_api_check.py','lp_baseline_native_delivery.py','lp_baseline_native_audit.py','lp_baseline_native_audit_v2.py')]
    new_paths += [ROOT/'tests/integration/test_lp_baseline_native_return.py',
        ROOT/'schemas/lp-baseline-execution-v5.schema.json',
        ROOT/'docs/decisions/ADR-0052-baseline-native-return.md',
        ROOT/'docs/specifications/SPEC-0023-baseline-native-return.md',
        ROOT/'docs/benchmarks/lp-external-baseline-native-return.md']
    eof_exception = dict(path='tools/lp_baseline_adapters_v5.py', sha256='455dfd7fabf3298e1600a5991cc91d0e8a48b27cc144aff90284bc953d59e34d')
    require(eof_exception in frozen, 'EOF exception must match the executed frozen source')
    checked(eof_exception)
    for p in new_paths:
        text = p.read_text()
        if p == ROOT/eof_exception['path']:
            require(text.endswith('\n\n') and not text.endswith('\n\n\n'), 'exact frozen EOF exception')
        else:
            require(text.endswith('\n') and not text.endswith('\n\n'), 'EOF hygiene: '+str(p))
        require(all(line==line.rstrip() for line in text.splitlines()), 'trailing space: '+str(p))
        if p.suffix=='.py':
            ast.parse(text, filename=str(p))
    built = subprocess.check_output([sys.executable, 'tools/build_docs.py',
        '--output', str(BASE/'book')],cwd=ROOT,text=True)
    match = re.search(r'documentation built: (\d+) pages',built)
    require(match is not None, 'documentation result missing')
    put(BASE/'delivery-checks.json',dict(schema_version=1,kind='lp-baseline-native-delivery-audit',
        status='passed',source=ref(Path(__file__)),report=ref(BASE/'report.json'),
        frozen_sources_preserved=True,historical_evidence_files=len(before),
        api_source_files=len(api['source_files']),preserved_prior_documents=preserved,
        historical_ledger=ref(ledger),historical_ledger_events=17438,
        planned=240,reused=123,new=117,native_returns=native_refs,raw_vectors=raw_refs,
        retained_native_observations=ref(observations_path),
        settled_resources=settlements,own_reservation_pending=pending,
        cleanup_empty=True,backlog_tasks=50,backlog_acyclic=True,next_ready_task='GPUP-RESIDENT2',
        documentation_pages=int(match.group(1)),diff_hygiene=True,new_text_hygiene=True,
        exact_frozen_eof_exceptions=[eof_exception],
        retained_prior_audit=ref(BASE/'resources/native-final-delivery-audit.settlement.json'),
        scientific_gate_reruns=0,certificate_recomputations=0,
        limitations=['Delivery accounting/acceptance are mutable drafts during this audit; seal after settlement.']))
    print(built.strip(),flush=True)
    print('Exact roster, native/certificate separation, provenance, cleanup and roadmap checks passed.',flush=True)


if __name__=='__main__':
    main()
