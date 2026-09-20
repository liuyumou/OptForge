"""Verify raw LP study references and report paired coverage and diagnostic phases."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import statistics
from benchmark_lp import CAMPAIGN, schedule
from lp_generate import Random
from lp_protocol import (ROOT, NS, Ledger, campaign, checked_reference, digest, encoded,
                         file_hash, local, read_json, validate, write_json)


def successful(trial):
    return (trial['status']=='completed' and trial['endpoint_class']=='certified_success'
            and trial['requested_backend']==trial['executed_backend'])

def percentile(values,q):
    ordered=sorted(values); index=(len(ordered)-1)*q; low=int(index); high=min(low+1,len(ordered)-1)
    return ordered[low]+(ordered[high]-ordered[low])*(index-low)

def paired_ratio(pairs,seed=17002,resamples=10000):
    """Median baseline/candidate latency, preserving repetition pairing in resampling."""
    if not pairs:return None
    if any(a<=0 or b<=0 for a,b in pairs):return None
    ratio=lambda sample: statistics.median(a for a,b in sample)/statistics.median(b for a,b in sample)
    rng=Random(seed); estimates=[]
    for _ in range(resamples):
        estimates.append(ratio([pairs[rng.integer(len(pairs))] for _ in pairs]))
    return {'paired_repetitions':len(pairs),'ratio':ratio(pairs),
            'ci95':[percentile(estimates,0.025),percentile(estimates,0.975)]}

def analyze(trials,value,instances):
    groups=defaultdict(list)
    for trial in trials:
        if trial['mode']=='timing':groups[(trial['instance_id'],trial['config_id'])].append(trial)
    rows=[];ratios=[]
    for instance in instances:
        for config in value['configurations']:
            observed=groups[(instance['id'],config['id'])]
            accepted=[t for t in observed if successful(t)]
            rows.append({'instance':instance['id'],'backend':config['id'],'planned':value['repetitions'],
                'attempted':len(observed),'certified':len(accepted),
                'certified_median_ns':statistics.median(t['elapsed_ns'] for t in accepted) if accepted else None,
                'outcomes':dict(Counter((t['status']+'/'+str(t['endpoint_class'])+
                    ('/fallback' if t['executed_backend'] and t['executed_backend']!=t['requested_backend'] else '')) for t in observed))})
        for reference in ['highs','host-lp']:
            left={t['repetition']:t for t in groups[(instance['id'],reference)]}
            right={t['repetition']:t for t in groups[(instance['id'],'cuda-lp')]}
            pairs=[(t['elapsed_ns'],right[r]['elapsed_ns']) for r,t in left.items()
                   if r in right and successful(t) and successful(right[r])]
            ratios.append({'instance':instance['id'],'comparison':reference+'/cuda-lp',
                           'statistics':paired_ratio(pairs,value['analysis']['seed'],value['analysis']['resamples'])})
    return rows,ratios

def load_trials(directory,value,manifests,campaign_hash):
    planned={job[0]:job for job in schedule(value,manifests)}
    trials=[];seen=set(); endpoints={}
    for path in sorted(directory.glob('*.trial.json')):
        trial=validate('trial',read_json(path));identity=trial['id']
        if identity in seen or identity not in planned:raise ValueError('duplicate/unplanned trial')
        seen.add(identity)
        _,instance,config,repetition,order,mode=planned[identity]
        expected_hash=digest(encoded({'configuration':config,'solve':value['solve'],
                            'lp_settings':value['lp_settings'] if config['backend']!='highs' else None}))
        expected={'campaign_sha256':campaign_hash,'instance_id':instance['id'],
                  'model_sha256':instance['model']['sha256'],'config_id':config['id'],
                  'requested_backend':config['backend'],'config_sha256':expected_hash,
                  'repetition':repetition,'order':order,'mode':mode,'block':f'{instance["id"]}:{repetition}',
                  'limits':value['limits']}
        if any(trial[k]!=v for k,v in expected.items()):raise ValueError('trial differs from frozen schedule/configuration')
        if successful(trial) and (trial['elapsed_ns'] is None or trial['endpoint'] is None):
            raise ValueError('success without measured endpoint')
        for role in ['worker','stdout','stderr','endpoint']:
            if trial[role] is not None:checked_reference(directory,trial[role])
        if trial['endpoint'] is not None and trial['status']!='invalid_evidence':
            endpoint=read_json(checked_reference(directory,trial['endpoint']))
            if trial['requested_backend'].startswith('copt-'):
                from validate_artifacts import validator
                validator('lp-external-endpoint-v1.schema.json').validate(endpoint)
                record=endpoint['witness'];executed=record['executed_backend']
            else:
                validate('endpoint',endpoint);record=endpoint;executed=endpoint['record']['backend']
            if endpoint['assessment']['classification']!=trial['endpoint_class'] or executed!=trial['executed_backend']:
                raise ValueError('trial endpoint classification differs')
            if record['model_sha256']!=trial['model_sha256'] or record['requested_backend']!=trial['requested_backend']:
                raise ValueError('trial endpoint identity differs')
            endpoints[identity]=endpoint
        trials.append(trial)
    return trials,endpoints

def report(directory,campaign_path):
    value,manifests=campaign(campaign_path)
    campaign_hash=file_hash(campaign_path)
    trials,endpoints=load_trials(directory,value,manifests,campaign_hash)
    # Reading a report cannot repair a ledger or consume/reserve budget.
    ledger=Ledger(directory,campaign_hash,value['phase_gpu_seconds'],value['slice_gpu_seconds'])
    if not ledger.path.exists():raise ValueError('missing budget ledger')
    if ledger.path.read_bytes() and not ledger.path.read_bytes().endswith(b'\n'):raise ValueError('interrupted ledger requires runner recovery')
    import fcntl
    binding=read_json(directory/'budget-binding.json')
    active_directory=local(ROOT,binding['ledger_directory'])
    with (active_directory/'campaign.lock').open('rb') as lock:
        fcntl.flock(lock,fcntl.LOCK_SH|fcntl.LOCK_NB)
        if ledger.path.read_bytes() and not ledger.path.read_bytes().endswith(b'\n'):
            raise ValueError('interrupted ledger requires runner recovery')
        ledger._load()
    if ledger.pending():raise ValueError('unsettled jobs require conservative runner recovery')
    execution_path=directory/'execution.json'
    if not execution_path.is_file():raise ValueError('missing execution provenance')
    execution=read_json(execution_path)
    if file_hash(directory/'source.tar')!=execution['source_archive_sha256']:
        raise ValueError('source archive checksum differs')
    for trial in trials:
        for key in ['source_tree_sha256','binary_sha256','code_object_sha256','highs_library_sha256','device','cpu_affinity','build_profile']:
            if trial['provenance'][key]!=execution[key]:raise ValueError('trial execution provenance differs')
    attempts=ledger.attempted()
    if {t['id'] for t in trials}!=attempts:raise ValueError('ledger/trial attempt coverage differs')
    selected=next(m for m in manifests if m['partition']=='development')['instances']
    rows,ratios=analyze(trials,value,selected)
    profiles=[]
    for trial in trials:
        if trial['mode']!='profile' or trial['id'] not in endpoints:continue
        endpoint=endpoints[trial['id']]
        diagnostics=endpoint['diagnostics']
        profiles.append({'instance':trial['instance_id'],'backend':trial['config_id'],
            'executed_backend':trial['executed_backend'],'status':trial['status'],
            'phases_ns':diagnostics['phases_ns'],'iterations':diagnostics['iterations'],
            'assessment_iteration':diagnostics['assessment_iteration'],'restarts':diagnostics['restarts'],
            'kernel_launches':diagnostics['kernel_launches'],
            'device_buffer_peak_bytes':diagnostics['device_buffer_peak_bytes'],
            'certificate':endpoint['assessment'],
            'audit_count':0,'retry_count':0,'precision_transitions':0,
            'unavailable':diagnostics['unavailable']})
    planned=len(list(schedule(value,manifests)))
    summary={'schema_version':1,'campaign_sha256':campaign_hash,
        'status':'baseline_complete' if len(trials)==planned else 'interim',
        'planned_trials':planned,'attempted_trials':len(trials),
        'gpu_seconds':ledger.totals()/NS,'cpu_job_seconds':ledger.totals('cpu')/NS,
        'additional_host_verification_seconds':sum(t['verification_ns'] or 0 for t in trials)/NS,
        'ledger_sha256':file_hash(ledger.path),'raw_trials':[{'path':p.name,'sha256':file_hash(p)} for p in sorted(directory.glob('*.trial.json'))],
        'rows':rows,'ratios':ratios,'profiles':profiles,
        'limitations':['development only; three repetitions are insufficient for finalist claims',
            'host adaptive restart/weight and GPU fixed controller differ; no pure device speedup claim',
            'ratios cover only mutually certified pairs; all attempts and censored failures remain visible',
            'phase profiles are separate executions; uninstrumented startup/output/teardown remains in primary elapsed time',
            'RSS watchdog is sampled; device buffer peak excludes driver/context memory; thermal telemetry is sampled',
            'no tuned matched control exists before GPUP-3/4; no precision recipe is selected']}
    write_json(directory/'summary.json',summary)
    lines=['# GPUP-2 development baseline report','',
        f'Status: {summary["status"]}; {len(trials)}/{planned} attempted trials. GPU study consumption: {summary["gpu_seconds"]:.3f}/900 seconds.',
        f'CPU-only job time: {summary["cpu_job_seconds"]:.3f} seconds; additional host verification: {summary["additional_host_verification_seconds"]:.3f} seconds.','',
        'Primary endpoint: fresh-process completion including original-model validation, host certification, evidence output and teardown. Certified median excludes unsuccessful endpoints; the complete outcome column preserves them.','',
        '| Instance | Backend | Certified / attempted / planned | Certified median ms | Outcomes |',
        '| --- | --- | --- | --- | --- |']
    for row in rows:
        median='unavailable' if row['certified_median_ns'] is None else f'{row["certified_median_ns"]/1e6:.3f}'
        lines.append(f'| {row["instance"]} | {row["backend"]} | {row["certified"]}/{row["attempted"]}/{row["planned"]} | {median} | {json.dumps(row["outcomes"],sort_keys=True)} |')
    lines+=['','## Paired ratios','', '| Instance | Comparison | Successful pairs | Median ratio | 95% interval |','| --- | --- | --- | --- | --- |']
    for row in ratios:
        result=row['statistics']
        tail='0 | unavailable | unavailable' if result is None else f'{result["paired_repetitions"]} | {result["ratio"]:.4f} | [{result["ci95"][0]:.4f}, {result["ci95"][1]:.4f}]'
        lines.append(f'| {row["instance"]} | {row["comparison"]} | {tail} |')
    lines+=['','## Separate profiling observations','',
        '| Instance | Requested / executed | Largest observed phase | Phase ms | Iterations | LP buffer bytes |',
        '| --- | --- | --- | --- | --- | --- |']
    for row in profiles:
        phase=max(row['phases_ns'],key=row['phases_ns'].get) if row['phases_ns'] else None
        lines.append(f'| {row["instance"]} | {row["backend"]} / {row["executed_backend"]} | {phase or "unavailable"} | {row["phases_ns"][phase]/1e6 if phase else "unavailable"} | {row["iterations"]} | {row["device_buffer_peak_bytes"]} |')
    lines+=['','## Interpretation and reproducibility','']+['- '+s for s in summary['limitations']]
    lines+=['',f'Campaign SHA-256: `{campaign_hash}`. Ledger SHA-256: `{summary["ledger_sha256"]}`.',
            'The adjacent summary.json preserves every raw trial hash, all profile phases, work and certificate diagnostics.',
            'Reproduce inputs with tools/lp_generate.py, pass the native gate, then run tools/benchmark_lp.py and tools/lp_report.py. Resume uses the same output directory and ledger.','']
    (directory/'report.md').write_text('\n'.join(lines))
    return summary

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=ROOT/'artifacts/gpup-baseline-v1')
    parser.add_argument('--campaign',type=Path,default=CAMPAIGN)
    args=parser.parse_args(); result=report(args.input.resolve(),args.campaign)
    print(f'{result["status"]}: {result["attempted_trials"]}/{result["planned_trials"]} trials, {result["gpu_seconds"]:.3f} GPU seconds')
