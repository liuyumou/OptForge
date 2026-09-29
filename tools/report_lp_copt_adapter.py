"""Independent SPEC-0019 artifact, command, budget and certification verification."""
import argparse
from collections import Counter
import hashlib
from pathlib import Path
import statistics
import subprocess
import tarfile
from benchmark_lp import reference
from benchmark_lp_copt import effective, is_gpu, verify_endpoint
from benchmark_lp_copt_adapter import RECOVERED, SUFFIXES, jobs, request_for, configuration_hash, validate_trial
from lp_copt_adapter_budget import CONFIG, protocol, ledger_for, receipt
from lp_protocol import ROOT, checked_reference, file_hash, read_json, write_json
from report_lp_copt import check_worker, checked_component_rows, numerical_digest
from report_lp_setup import paired_ratios
from validate_artifacts import schema_snapshot, validator


def check_identity(value, job, trial, request, directory, binary, protocol_hash):
    config = job['configuration']; solve, method, limits = effective(value, job)
    expected = dict(id=job['id'], campaign_sha256=protocol_hash, instance_id=job['instance']['id'], model_sha256=job['instance']['model']['sha256'],
                    config_id=config['id'], config_sha256=configuration_hash(value, job), adapter_id=config['adapter_id'],
                    dependencies_sha256=value['dependencies']['sha256'], requested_backend=config['backend'], repetition=job['repetition'], order=job['order'],
                    block=f'{job["kind"]}:{job["instance"]["id"]}:{job["repetition"]}', mode=job['kind'], category=job['category'],
                    solve=solve, lp_settings=method, limits=limits, budget_authority_sha256=value['budget_authority']['sha256'])
    if any(trial[k] != v for k, v in expected.items()): raise ValueError('trial adapter/schedule identity differs')
    if request != request_for(value, job, binary, directory): raise ValueError('frozen command/request differs')
    if read_json(directory / (job['id'] + '.solve.json')) != solve: raise ValueError('effective solve differs')


def check_artifacts(directory, trial):
    for role, suffix in SUFFIXES.items():
        ref = trial[role]; path = directory / (trial['id'] + suffix)
        if ref is None:
            if path.exists(): raise ValueError('unbound existing artifact: ' + role)
        else:
            if ref['path'] != trial['id'] + suffix: raise ValueError('artifact filename differs: ' + role)
            checked_reference(directory, ref)


def check_accounting(trial, worker, settlement, gpu):
    recovered = trial['error'] == RECOVERED
    if recovered and trial['status'] != 'process_failure':
        raise ValueError('recovered coordinator cannot qualify as completed')
    if worker:
        if recovered:
            for key in ['elapsed_ns', 'queue_ns', 'leased_ns', 'peak_rss_bytes', 'memory_method']:
                if trial[key] != worker[key]: raise ValueError('recovered worker observation differs')
        else:
            check_worker(trial, worker)
    if settlement['kind'] == 'recover':
        if not recovered: raise ValueError('recovered reservation requires interrupted trial')
        charge = settlement['reserved_ns']
    else:
        charge = (worker['leased_ns'] if gpu else worker['elapsed_ns']) if worker else settlement['reserved_ns']
    if settlement['charged_ns'] != charge: raise ValueError('worker/reservation charge differs')


def check_measured_source(directory):
    """Only declared CPU review corrections may differ from the measured snapshot."""
    review_path = ROOT / 'docs/benchmarks/data/copt-adapter/adapter-review-corrections.json'
    review = read_json(review_path) if review_path.exists() else {'files': []}
    corrections = {item['path']: item for item in review['files']}
    allowed = {'tools/benchmark_lp_copt_adapter.py', 'tools/report_lp_copt_adapter.py', 'tools/export_lp_copt_adapter.py'}
    if len(corrections) != len(review['files']) or not set(corrections) <= allowed:
        raise ValueError('invalid review correction scope')
    measured = []; corrected = []
    with tarfile.open(directory / 'source.tar') as archive:
        for member in archive.getmembers():
            if member.isfile() and (member.name.startswith(('tools/', 'schemas/', 'crates/', 'cuda/', 'benchmarks/')) or member.name in ['Cargo.toml', 'Cargo.lock']):
                content = archive.extractfile(member).read(); current = ROOT / member.name
                if content != current.read_bytes():
                    correction = corrections.get(member.name)
                    if not correction or correction['measured_sha256'] != hashlib.sha256(content).hexdigest() or correction['reviewed_sha256'] != file_hash(current):
                        raise ValueError('undeclared measured source change: ' + member.name)
                    corrected.append(member.name)
                measured.append(member.name)
    if set(corrected) != set(corrections): raise ValueError('review correction does not match source difference')
    return measured, corrected


def check_cost(directory, trial, endpoint):
    cost = read_json(checked_reference(directory, trial['cost'])); validator('lp-cost-v1.schema.json').validate(cost)
    for key, expected in dict(trial_id=trial['id'], model_sha256=trial['model_sha256'], request_sha256=trial['request_sha256'],
                             source_tree_sha256=trial['provenance']['source_tree_sha256'], binary_sha256=trial['provenance']['binary_sha256'],
                             endpoint_sha256=trial['endpoint']['sha256'] if trial['endpoint'] else None, profiler_sha256=None, trace=None,
                             native_observations=trial['observations']).items():
        if cost[key] != expected: raise ValueError('cost identity differs: ' + key)
    expected = [('solve', None, trial['raw_cost']), ('host-certifier', ['copt', 'host_certification'], trial['cert_cost'])]
    expected = [dict(process=p, parent_scope=scope, artifact=ref) for p, scope, ref in expected if ref]
    if cost['observations'] != expected: raise ValueError('cost observation binding differs')
    return checked_component_rows(cost, directory, endpoint, True)


def check_archive(directory, value):
    execution = read_json(directory / 'execution.json')
    if read_json(directory / 'campaign.json') != value or file_hash(directory / 'dependencies.json') != value['dependencies']['sha256']:
        raise ValueError('archived protocol/dependency identity differs')
    if execution['binary_sha256'] != file_hash(directory / 'optimizer') or execution['source_archive_sha256'] != file_hash(directory / 'source.tar') or execution['schema_snapshot_sha256'] != schema_snapshot().sha256:
        raise ValueError('archived source/binary/schema identity differs')
    baseline = read_json(ROOT / value['baseline_output'] / 'execution.json')
    if baseline['dirty'] or baseline['revision'] != value['baseline_revision'] or baseline['source_archive_sha256'] != file_hash(directory / 'baseline-source.tar') or baseline['binary_sha256'] != file_hash(directory / 'optimizer-baseline'):
        raise ValueError('baseline identity differs')
    check_measured_source(directory)
    subprocess.run([str(ROOT / value['copt_python']), '-B', str(ROOT / 'tools/setup_copt_adapter.py'), '--identity'], check=True, capture_output=True, timeout=120)
    return execution


def check_acceptance_archive(value, execution):
    directory = ROOT / value['acceptance_output']; results = []
    for name, count in [('readback.json',12), ('endpoints-cpu.json',16), ('endpoints-gpu.json',8)]:
        data = read_json(directory / name)
        if data['status'] != 'passed' or data['source_tree_sha256'] != execution['source_tree_sha256'] or data['dependencies_sha256'] != value['dependencies']['sha256'] or len(data.get('cases', data.get('results', []))) != count:
            raise ValueError('acceptance archive differs')
        results += data.get('results', [])
    expected = {(sense, method, adapter, profile) for sense in ['minimize', 'maximize'] for method in ['copt-cpu-default','copt-cpu-pdlp','copt-gpu-pdlp'] for adapter in ['scalar','bulk'] for profile in [False,True]}
    if len(results) != 24 or {(r['sense'],r['method'],r['adapter'],r['profile']) for r in results} != expected: raise ValueError('acceptance coverage differs')
    for r in results:
        key = 'accept-' + r['sense'] + '-' + r['method'] + '-' + r['adapter'] + ('-on' if r['profile'] else '-off')
        if r['id'] != key or r['endpoint']['path'] != key + '.json' or r['model']['path'] != 'accept-' + r['sense'] + '.model.json': raise ValueError('acceptance filename differs')
        model = checked_reference(directory, r['model']); endpoint = checked_reference(directory, r['endpoint']); e = read_json(endpoint)
        if numerical_digest(e) != r['numerical_sha256'] or e['assessment']['classification'] != 'certified_success' or e['witness']['requested_backend'] != r['method'] or e['witness']['executed_backend'] != r['method']:
            raise ValueError('acceptance numerical identity differs')
        for name in ['optimizer','optimizer-baseline']:
            result = subprocess.run([str(ROOT / value['output'] / name), 'lp-study', 'external-verify', '--model', str(model), '--evidence', str(endpoint)], capture_output=True, timeout=120)
            if result.returncode: raise ValueError('independent acceptance verify failed')
    key = value['id'] + '-accept-endpoints'; binding = read_json(directory / (key + '.source.json')); worker = read_json(directory / (key + '.worker.json')); request = read_json(directory / (key + '.request.json'))
    if binding['source_tree_sha256'] != execution['source_tree_sha256'] or binding['request_sha256'] != file_hash(directory / (key + '.request.json')) or worker['reason'] != 'completed' or worker['returncode'] != 0:
        raise ValueError('acceptance worker differs')
    if request['command'] != ['python3', '-B', 'tools/lp_copt_adapter_accept.py', 'gpu']: raise ValueError('acceptance command differs')
    return dict(endpoints=len(results), readbacks=12, leased_ns=worker['leased_ns'])


def report(value):
    directory = ROOT / value['output']; execution = check_archive(directory, value)
    acceptance = check_acceptance_archive(value, execution)
    ledger = ledger_for(value); data = ledger.path.read_bytes()
    if data and not data.endswith(b'\n'): raise ValueError('torn ledger; report cannot repair')
    ledger._load()
    if ledger.pending(): raise ValueError('unsettled ledger; report cannot recover')
    if file_hash(directory / 'ledger.jsonl') != file_hash(ledger.path): raise ValueError('archived ledger differs')
    if any(ledger.totals(phase=p) > cap * 1e9 for p, cap in value['phase_gpu_seconds'].items()) or ledger.totals() > value['cumulative_gpu_ns']:
        raise ValueError('campaign cap exceeded')
    if any(ledger.usage(k) > r['seconds'] * 1e9 for k,r in value['categories'].items()) or sum(ledger.usage(k) for k in value['categories']) > value['combined_cap_seconds'] * 1e9:
        raise ValueError('category cap exceeded')
    schedule = list(jobs(value)); trials = {p.stem[:-6]: read_json(p) for p in directory.glob('*.trial.json')}
    planned = {j['id'] for j in schedule}
    if not set(trials) <= planned: raise ValueError('unexpected trial filename')
    expected_provenance = {k:v for k,v in execution.items() if k != 'source_archive_sha256'}
    rows=[]; endpoints={}; profiles=[]
    for job in schedule:
        key=job['id']; trial=trials.get(key); c=job['configuration']
        row=dict(id=key, instance_id=job['instance']['id'], method=c['backend'], adapter=c['adapter_id'], mode=job['kind'], repetition=job['repetition'],
                 attempted=trial is not None, verified=False, certified=False, status='unattempted', classification=None, elapsed_ns=None, leased_ns=None, error=None)
        rows.append(row)
        events=[e for e in ledger.events if e['trial_id']==key]
        if trial is None:
            if events: raise ValueError('admitted attempt missing trial')
            continue
        validate_trial(trial)
        request_path=directory/(key+'.request.json')
        if file_hash(request_path)!=trial['request_sha256']: raise ValueError('request bytes differ')
        check_identity(value,job,trial,read_json(request_path),directory,directory/'optimizer',file_hash(CONFIG))
        if trial['provenance']!=expected_provenance: raise ValueError('execution provenance differs')
        check_artifacts(directory,trial)
        expected_resource='gpu' if is_gpu(job) else 'cpu';limits=effective(value,job)[2]
        expected_reserve=(limits['solve_seconds']+limits['cleanup_seconds']+(4 if is_gpu(job) else 1))*1000000000
        if len(events)!=2 or events[0]['kind']!='reserve' or events[1]['kind'] not in ['settle','recover'] or any(e['resource']!=expected_resource or e['phase']!=value['categories'][job['category']]['phase'] or e['reserved_ns']!=expected_reserve for e in events):
            raise ValueError('attempt ledger binding differs')
        worker=read_json(checked_reference(directory,trial['worker'])) if trial['worker'] else None
        check_accounting(trial, worker, events[1], is_gpu(job))
        row.update(status=trial['status'],error=trial['error'],elapsed_ns=trial['elapsed_ns'],leased_ns=trial['leased_ns'])
        endpoint=None
        if trial['endpoint']:
            try:
                endpoint=read_json(checked_reference(directory,trial['endpoint']))
                if endpoint['witness']!=read_json(checked_reference(directory,trial['witness'])): raise ValueError('witness file differs')
                outcomes=[verify_endpoint(value,job,directory,directory/name,trial['provenance']) for name in ['optimizer','optimizer-baseline']]
                if outcomes[0]!=outcomes[1] or outcomes[0]!=(trial['executed_backend'],trial['endpoint_class']): raise ValueError('endpoint outcome identity differs')
                row.update(verified=True,classification=outcomes[0][1]);endpoints[key]=endpoint
                row['certified']=bool(trial['status']=='completed' and worker and worker['returncode']==0 and worker['reason']=='completed' and outcomes[0]==(c['backend'],'certified_success'))
            except Exception:
                if trial['status'] not in ['invalid_evidence','process_failure','timeout','output_limit']: raise
                endpoint=None
        if trial['cost']:
            raw=check_cost(directory,trial,endpoint)
            parent=raw.get('solve')
            if parent:
                if parent['elapsed_ns']>worker['elapsed_ns']: raise ValueError('profile exceeds process')
                profiles.append(dict(id=key,instance_id=row['instance_id'],method=c['backend'],adapter=c['adapter_id'],process_ns=worker['elapsed_ns'],
                                     residual_ns=worker['elapsed_ns']-parent['elapsed_ns'],scopes=parent['scopes'],certifier=raw.get('host-certifier'),verified=row['verified'],certified=row['certified']))
    groups=[];ratios=[];equivalence=[]
    for instance in value['instances']:
        for method in ['copt-cpu-default','copt-cpu-pdlp','copt-gpu-pdlp']:
            group=[r for r in rows if r['instance_id']==instance and r['method']==method and r['mode']=='timing']
            for adapter in ['copt-scalar-v1','copt-bulk-v1']:
                sample=[r for r in group if r['adapter']==adapter];valid=[r['elapsed_ns'] for r in sample if r['certified']]
                groups.append(dict(instance_id=instance,method=method,adapter=adapter,attempted=sum(r['attempted'] for r in sample),verified=sum(r['verified'] for r in sample),certified=len(valid),median_ns=statistics.median(valid) if valid else None))
            pairs=[]
            for repeat in range(3):
                a=next(r for r in group if r['adapter']=='copt-scalar-v1' and r['repetition']==repeat);b=next(r for r in group if r['adapter']=='copt-bulk-v1' and r['repetition']==repeat)
                if a['certified'] and b['certified']:pairs.append((a['elapsed_ns'],b['elapsed_ns']))
                if a['verified'] and b['verified']: equivalence.append(dict(scalar=a['id'],bulk=b['id'],matching=numerical_digest(endpoints[a['id']])==numerical_digest(endpoints[b['id']])))
            ratios.append(dict(instance_id=instance,method=method,paired=paired_ratios(pairs,**{'seed':value['analysis']['seed'],'resamples':value['analysis']['resamples']})))
    for p in profiles:
        group=next(g for g in groups if all(g[k]==p[k] for k in ['instance_id','method','adapter']))
        p['profile_to_timing_median']=p['process_ns']/group['median_ns'] if group['median_ns'] else None
        counterpart=next(r for r in rows if r['mode']=='timing' and r['repetition']==0 and all(r[k]==p[k] for k in ['instance_id','method','adapter']))
        p['numerical_work_matches_timing']=numerical_digest(endpoints[p['id']])==numerical_digest(endpoints[counterpart['id']]) if p['id'] in endpoints and counterpart['id'] in endpoints else None
    result=dict(id=value['id'],planned=len(rows),attempted=sum(r['attempted'] for r in rows),verified=sum(r['verified'] for r in rows),
                certified_timings=sum(r['certified'] for r in rows if r['mode']=='timing'),certified_profiles=sum(r['certified'] for r in rows if r['mode']=='profile'),
                rows=rows,groups=groups,ratios=ratios,equivalence=equivalence,profiles=profiles,acceptance=acceptance,budget=receipt(ledger),
                limitations=['Development only; no preset.', 'COPT hard PDLP iteration/seed controls unavailable; native counters are not project updates.',
                             'Historical wrapper timings and racecheck/session/mixed-65536 gaps remain unchanged.'])
    write_json(directory/'report.json',result)
    print({k:result[k] for k in ['planned','attempted','verified','certified_timings','certified_profiles']})
    return result


if __name__=='__main__': report(protocol())
