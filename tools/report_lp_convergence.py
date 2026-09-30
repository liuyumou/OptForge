"""Independent ADR-0032 convergence, work, identity, cost and certification report."""
import argparse
from collections import Counter
import hashlib
from pathlib import Path
import statistics
import subprocess
import tarfile
from benchmark_lp import reference
from benchmark_lp_convergence import effective, is_gpu, verify_endpoint, evidence_format, endpoint_shape
from benchmark_lp_convergence import RECOVERED, SUFFIXES, jobs, request_for, configuration_hash, validate_trial
from lp_convergence_budget import CONFIG, protocol, ledger_for, receipt
from lp_protocol import ROOT, checked_reference, file_hash, read_json, write_json
from report_lp_copt import check_worker, checked_component_rows, numerical_digest
from report_lp_setup import paired_ratios
from validate_artifacts import schema_snapshot, validator


def check_identity(value, job, trial, request, directory, binary, protocol_hash):
    config = job['configuration']; solve, method, limits = effective(value, job)
    expected = dict(id=job['id'], campaign_sha256=protocol_hash, instance_id=job['instance']['id'], model_sha256=job['instance']['model']['sha256'],
                    config_id=config['id'], config_sha256=configuration_hash(value, job), work_limit=method['iteration_limit'], evidence_format=evidence_format(job),
                    dependencies_sha256=value['dependencies']['sha256'], requested_backend=config['backend'], repetition=job['repetition'], order=job['order'],
                    block=f'{job["kind"]}:{job["instance"]["id"]}:{job["repetition"]}', mode=job['kind'], category=job['category'],
                    solve=solve, lp_settings=method, limits=limits, budget_authority_sha256=value['budget_authority']['sha256'])
    if any(trial[k] != v for k, v in expected.items()): raise ValueError('trial adapter/schedule identity differs')
    if request != request_for(value, job, binary, directory): raise ValueError('frozen command/request differs')
    for name, expected in [('solve', solve), ('method', method), *[(n, config[n]) for n in ['execution', 'precision', 'adaptive'] if n in config]]:
        if read_json(directory / (job['id'] + '.' + name + '.json')) != expected: raise ValueError('effective input differs: ' + name)


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
    """Bind declared CPU review repairs; measured solver/collector bytes stay intact."""
    path = ROOT / 'docs/benchmarks/data/convergence/convergence-review-corrections.json'
    review = read_json(path) if path.exists() else {'files': []}
    corrections = {item['path']: item for item in review['files']}
    allowed = {'tools/benchmark_lp_convergence.py', 'tools/report_lp_convergence.py', 'tools/export_lp_convergence.py'}
    if len(corrections) != len(review['files']) or not set(corrections) <= allowed: raise ValueError('invalid review correction scope')
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
    return measured


def check_cost(directory, trial, endpoint, external):
    cost = read_json(checked_reference(directory, trial['cost'])); validator('lp-cost-v1.schema.json').validate(cost)
    for key, expected in dict(trial_id=trial['id'], model_sha256=trial['model_sha256'], request_sha256=trial['request_sha256'],
                             source_tree_sha256=trial['provenance']['source_tree_sha256'], binary_sha256=trial['provenance']['binary_sha256'],
                             endpoint_sha256=trial['endpoint']['sha256'] if trial['endpoint'] else None, profiler_sha256=None, trace=None,
                             native_observations=trial['observations']).items():
        if cost[key] != expected: raise ValueError('cost identity differs: ' + key)
    expected = [('solve', None, trial['raw_cost']), ('host-certifier', ['copt', 'host_certification'], trial['cert_cost'])]
    expected = [dict(process=p, parent_scope=scope, artifact=ref) for p, scope, ref in expected if ref]
    if cost['observations'] != expected: raise ValueError('cost observation binding differs')
    return checked_component_rows(cost, directory, endpoint, external)


def check_archive(directory, value):
    execution = read_json(directory / 'execution.json')
    if read_json(directory / 'campaign.json') != value or file_hash(directory / 'dependencies.json') != value['dependencies']['sha256']:
        raise ValueError('archived protocol/dependency identity differs')
    if execution['binary_sha256'] != file_hash(directory / 'optimizer') or execution['source_archive_sha256'] != file_hash(directory / 'source.tar') or execution['schema_snapshot_sha256'] != schema_snapshot().sha256:
        raise ValueError('archived source/binary/schema identity differs')
    for name, sha in read_json(directory / 'code-objects.json').items():
        if file_hash(directory / name) != sha: raise ValueError('archived code image differs')
    gate = read_json(directory / 'native-gate.json')
    if not gate['native'] or gate['source_tree_sha256'] != execution['source_tree_sha256']: raise ValueError('native receipt differs')
    check_measured_source(directory)
    subprocess.run([str(ROOT / value['copt_python']), '-B', str(ROOT / 'tools/setup_copt_adapter.py'), '--identity'], check=True, capture_output=True, timeout=120)
    return execution


def check_project_acceptance_identity(value, config, model_sha, endpoint, profile, images):
    record = endpoint['record']
    expected_solve = dict(value['solve'], iteration_limit=value['acceptance_work'], time_limit_ms=30000)
    expected_method = dict(value['lp_settings'], iteration_limit=value['acceptance_work'])
    if endpoint['model_sha256'] != model_sha or endpoint['requested_backend'] != config['backend'] or record['backend'] != config['backend']:
        raise ValueError('project acceptance model/backend differs')
    if record['options'] != expected_solve or record['lp_settings'] != expected_method:
        raise ValueError('project acceptance work/settings differ')
    if record['termination'] in ('interrupted', 'time_limit') or endpoint['diagnostics']['profile'] is not profile:
        raise ValueError('project acceptance deadline/profile differs')
    for name in ['execution', 'precision', 'adaptive']:
        if (endpoint.get(name) or {}).get('settings') != config.get(name):
            raise ValueError('project acceptance configuration differs: ' + name)
    image = 'lp_pdhg_precision.cubin' if 'precision' in config or 'adaptive' in config else 'lp_pdhg_tuned.cubin'
    if endpoint['execution']['code_object_sha256'] != images[image]:
        raise ValueError('project acceptance code image differs')


def check_external_acceptance_model(original, sense, model):
    import copy
    if sense not in ['minimize', 'maximize']: raise ValueError('external acceptance sense differs')
    expected = copy.deepcopy(original)
    expected['objective'].update(sense=sense, offset=7.0)
    if sense == 'maximize':
        for term in expected['objective']['terms']: term['coefficient'] = -term['coefficient']
    if model != expected: raise ValueError('external acceptance original model/sense/offset differs')


def check_external_acceptance_identity(value, method, model_sha, endpoint, execution):
    from lp_copt import parameters
    witness = endpoint['witness']; gpu = method == 'copt-gpu-pdlp'
    solve = dict(value['solve'], time_limit_ms=30000)
    if witness['model_sha256'] != model_sha or witness['requested_backend'] != method or witness['executed_backend'] != method:
        raise ValueError('external acceptance model/backend differs')
    if witness['options'] != solve or witness['parameters'] != parameters(solve, gpu):
        raise ValueError('external acceptance settings differ')
    if witness['library_sha256'] != execution['copt_library_sha256'] or witness['binding_sha256'] != execution['copt_binding_sha256'] or witness['copt_version'] != '8.0.6':
        raise ValueError('external acceptance dependency differs')
    if witness['gpu_confirmed'] is not gpu or endpoint['assessment']['classification'] != 'certified_success':
        raise ValueError('external acceptance execution/certification differs')


def check_acceptance_archive(value, execution):
    from lp_convergence_accept import check_acceptance
    from lp_cost import validate_profile
    result = check_acceptance(value); directory = ROOT / value['acceptance_output']; binary = ROOT / value['output'] / 'optimizer'
    models = {i['id']: i for ref in value['manifests'] for i in read_json(checked_reference(ROOT, ref))['instances']}
    configurations = {c['id']: c for c in value['configurations']}
    images = read_json(ROOT / value['output'] / 'code-objects.json')
    for pair in read_json(directory / 'project.json')['pairs']:
        model_ref = models[pair['instance']]['model']; model = checked_reference(ROOT, model_ref)
        endpoints = []
        for label, ref in pair['endpoints'].items():
            evidence = checked_reference(ROOT, ref)
            # check_acceptance already validates the compact schema and numerical
            # digest; bind its metadata to the claimed acceptance cell as well.
            endpoint = read_json(evidence)['endpoint']; endpoints.append(endpoint)
            check_project_acceptance_identity(value, configurations[pair['configuration']], model_ref['sha256'], endpoint, label == 'on', images)
            check = subprocess.run([str(binary), 'lp-study', 'verify', '--model', str(model), '--model-byte-limit', str(value['model_byte_limit']),
                                    '--evidence', str(evidence)], capture_output=True, timeout=value['verification_seconds'])
            if check.returncode: raise ValueError('independent project acceptance verification failed')
        if len({numerical_digest(e) for e in endpoints}) != 1 or any(e['execution'] != endpoints[0]['execution'] for e in endpoints):
            raise ValueError('project acceptance profile/replay state or work differs')
        validate_profile(read_json(checked_reference(ROOT, pair['cost'])))
    original = read_json(checked_reference(ROOT, models['gpup-development-irregular-256']['model']))
    for name in ['external-cpu.json', 'external-gpu.json']:
        pairs = {}
        for row in read_json(directory / name)['results']:
            model = checked_reference(ROOT, row['model']); evidence = checked_reference(ROOT, row['endpoint'])
            key = 'accept-' + row['sense'] + '-' + row['method'] + ('-on' if row['profile'] else '-off')
            if evidence != directory / (key + '.json'): raise ValueError('external acceptance profile artifact differs')
            check_external_acceptance_model(original, row['sense'], read_json(model))
            endpoint = read_json(evidence)
            check_external_acceptance_identity(value, row['method'], row['model']['sha256'], endpoint, execution)
            pairs.setdefault(row['sense'], []).append(numerical_digest(endpoint))
            if row['profile']: validate_profile(read_json(directory / (key + '.cost.json')))
            check = subprocess.run([str(binary), 'lp-study', 'external-verify', '--model', str(model),
                                    '--evidence', str(evidence)], capture_output=True, timeout=value['verification_seconds'])
            if check.returncode: raise ValueError('independent external acceptance verification failed')
        if any(len(set(digests)) != 1 for digests in pairs.values()): raise ValueError('external acceptance profile state/work differs')
    return result


def work_observation(e):
    if 'witness' in e:
        w = e['witness']
        return dict(units='COPT native iterations; not project physical updates', native=w['native'], iterations=w['iterations'], assessment=e['assessment'])
    control = e.get('control') or {}; d = e['diagnostics']; a = e.get('adaptive'); p = e.get('precision')
    physical = control.get('physical_iterations', d['iterations']); logical = control.get('logical_iterations', d['iterations'])
    if a:
        if physical != a['proposed_steps'] + a['audit_steps'] + a['probe_steps']: raise ValueError('adaptive physical work is inconsistent')
        if sum(a['rung_proposals']) != a['proposed_steps']: raise ValueError('per-rung proposals differ')
        if any(a[k] > a['proposed_steps'] for k in ['rejected_steps','replay_steps']): raise ValueError('overlapping subset exceeds proposals')
    proposals = a['proposed_steps'] if a else p['proposed_steps'] if p else physical
    return dict(units='project physical updates', physical=physical, logical=logical, proposals=proposals,
                audits=a['audit_steps'] if a else 0, probes=a['probe_steps'] if a else 0,
                rejected=a['rejected_steps'] if a else p['rejected_steps'] if p else None, replay=a['replay_steps'] if a else None,
                physical_per_logical=physical / logical if logical else None, step=a['step'] if a else p['step'] if p else None,
                operator_bounds=p['operator_bounds'] if p else None, restarts=d['restarts'], assessments=control.get('assessments'),
                assessment_iteration=d['assessment_iteration'], adaptive=a, precision=p, control=control, execution=e.get('execution'), assessment=e['assessment'])


def cost_group(path):
    from report_lp_copt import component_group
    if 'audit_comparison' in path: return 'audit_comparison'
    if 'adaptive_probe' in path: return 'probes'
    if 'reference_fp64_update' in path: return 'reference_arithmetic'
    if any(n in path for n in ['kernels_and_synchronization','kernel_submission','synchronization']): return 'device_execution_host_envelope'
    return component_group(path)


def cost_groups(raw, process_ns):
    # Exclusive scopes partition one process. Child certifier time is separately
    # reported, never added again to its containing host-certification scope.
    result = Counter()
    for row in raw['scopes']: result[cost_group(row['path'])] += row['exclusive_ns']
    if sum(result.values()) > raw['elapsed_ns'] or raw['elapsed_ns'] > process_ns: raise ValueError('cost scopes exceed process envelope')
    result['unattributed'] += process_ns - sum(result.values())
    return dict(result)


def profile_envelope(raw, worker):
    if worker is None: return None
    process_ns = worker['elapsed_ns']
    return dict(process_ns=process_ns, residual_ns=process_ns-raw['elapsed_ns'], groups_ns=cost_groups(raw, process_ns))


def paired(pairs, value):
    if not pairs: return None
    if any(a <= 0 or b <= 0 for a,b in pairs): raise ValueError('non-positive paired latency')
    if len(pairs) == 1: return dict(paired_repetitions=1,ratio=pairs[0][0]/pairs[0][1],ci95=None)
    return paired_ratios(pairs,seed=value['analysis']['seed'],resamples=value['analysis']['resamples'])


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
        row=dict(id=key, instance_id=job['instance']['id'], method=c['backend'], configuration=c['id'], mode=job['kind'], repetition=job['repetition'],
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
        if any(trial['provenance'][k] != v for k,v in expected_provenance.items() if k not in ['telemetry_before','telemetry_after']): raise ValueError('execution provenance differs')
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
                endpoint = endpoint_shape(checked_reference(directory,trial['endpoint']), 'compact-v1') if evidence_format(job) == 'compact-v1' else read_json(checked_reference(directory,trial['endpoint']))
                outcome = verify_endpoint(value,job,directory,directory/'optimizer',trial['provenance'])
                if outcome != (trial['executed_backend'],trial['endpoint_class']): raise ValueError('endpoint outcome identity differs')
                outcomes = [outcome]
                row.update(verified=True,classification=outcomes[0][1]);endpoints[key]=endpoint
                row['certified']=bool(trial['status']=='completed' and worker and worker['returncode']==0 and worker['reason']=='completed' and outcomes[0]==(c['backend'],'certified_success'))
            except Exception as error:
                if trial['status'] not in ['invalid_evidence','process_failure','timeout','output_limit']: raise
                endpoint=None; row['verification_error']=str(error)[:2000]
        if trial['cost']:
            raw=check_cost(directory,trial,endpoint,evidence_format(job)=='external-v2')
            parent=raw.get('solve')
            envelope = profile_envelope(parent, worker) if parent else None
            if parent and envelope is None: row['profile_unavailable'] = 'missing worker envelope; raw scopes retained'
            if envelope:
                profiles.append(dict(id=key,instance_id=row['instance_id'],method=c['backend'],configuration=c['id'],mode=job['kind'],**envelope,
                                     scopes=parent['scopes'],certifier=raw.get('host-certifier'),verified=row['verified'],certified=row['certified']))
    groups=[]; ratios=[]; equivalence=[]; work=[]
    for row in rows:
        if row['id'] in endpoints:
            work.append(dict(id=row['id'],instance_id=row['instance_id'],configuration=row['configuration'],mode=row['mode'],
                             certified=row['certified'], **work_observation(endpoints[row['id']])))
    for instance in value['timing_instances'] + value['single_instances']:
        for config in value['configurations']:
            sample=[r for r in rows if r['instance_id']==instance and r['configuration']==config['id'] and r['mode']=='timing']
            valid=[r['elapsed_ns'] for r in sample if r['certified']]
            groups.append(dict(instance_id=instance,configuration=config['id'],planned=len(sample),attempted=sum(r['attempted'] for r in sample),
                               verified=sum(r['verified'] for r in sample),certified=len(valid),median_ns=statistics.median(valid) if valid else None,
                               outcomes=dict(Counter(r['classification'] or r['status'] for r in sample))))
            base=[r for r in rows if r['instance_id']==instance and r['configuration']=='tuned-fp64' and r['mode']=='timing']
            pairs=[(a['elapsed_ns'],b['elapsed_ns']) for a in base for b in sample if a['repetition']==b['repetition'] and a['certified'] and b['certified']]
            ratios.append(dict(instance_id=instance,configuration=config['id'],reference='tuned-fp64',paired=paired(pairs,value)))
    by_id={w['id']:w for w in work}
    for p in profiles:
        if p['mode']!='profile': continue
        group=next(g for g in groups if all(g[k]==p[k] for k in ['instance_id','configuration']))
        p['profile_to_timing_median']=p['process_ns']/group['median_ns'] if group['median_ns'] else None
        counterpart=next(r for r in rows if r['mode']=='timing' and r['repetition']==0 and all(r[k]==p[k] for k in ['instance_id','configuration']))
        match=numerical_digest(endpoints[p['id']])==numerical_digest(endpoints[counterpart['id']]) if p['id'] in endpoints and counterpart['id'] in endpoints else None
        equivalence.append(dict(profile=p['id'],timing=counterpart['id'],matching=match))
    # Compare certified physical totals only within project units. Short profiles
    # expose their actual mixtures without claiming equal proposal counts.
    amplification=[]
    for row in rows:
        w=by_id.get(row['id']); base=next((r for r in rows if r['mode']==row['mode'] and r['instance_id']==row['instance_id'] and r['repetition']==row['repetition'] and r['configuration']=='tuned-fp64'),None)
        bw=by_id.get(base['id']) if base else None
        if not w or not bw or 'physical' not in w: continue
        eligible=row['certified'] and base['certified'] and row['mode'] in ['timing','profile']
        amplification.append(dict(id=row['id'],reference=base['id'],certified_pair=eligible,
                                  physical_ratio=w['physical']/bw['physical'] if eligible and bw['physical'] else None,
                                  proposal_ratio=w['proposals']/bw['proposals'] if eligible and bw['proposals'] else None))
    result=dict(id=value['id'],planned=len(rows),attempted=sum(r['attempted'] for r in rows),verified=sum(r['verified'] for r in rows),
                certified_timings=sum(r['certified'] for r in rows if r['mode']=='timing'),certified_profiles=sum(r['certified'] for r in rows if r['mode']!='timing'),
                rows=rows,groups=groups,ratios=ratios,equivalence=equivalence,profiles=profiles,work=work,amplification=amplification,acceptance=acceptance,budget=receipt(ledger),
                limitations=['Development only; no tuning or preset.', 'Mixed-65536 has one timing repetition; no repeatability interval.',
                             'Equal physical allowances need not yield equal proposals, logical progress, step sizes or work mixtures.',
                             'COPT native iterations are not project updates; hard PDLP iteration/seed controls and graph internals remain unavailable.',
                             'Host device-execution scopes include submission/synchronization, not measured device busy time.',
                             'Historical racecheck/session/mixed-model gaps remain explicit.'])
    write_json(directory/'report.json',result)
    print({k:result[k] for k in ['planned','attempted','verified','certified_timings','certified_profiles']})
    return result


if __name__=='__main__': report(protocol())
