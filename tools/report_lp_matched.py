"""Verify ADR-0016 raw evidence, pairing, provenance and cumulative spending."""
import argparse
from collections import Counter, defaultdict
import fcntl
from pathlib import Path
import statistics
import subprocess
from benchmark_lp_matched import CONFIG, OUTPUT, protocol
from benchmark_lp import schedule
from lp_protocol import ROOT, NS, Ledger, checked_reference, file_hash, read_json, write_json
from lp_report import load_trials, paired_ratio, successful

COMPARISONS=[('reference-cuda-lp','cuda-lp'),('cuda-lp','cuda-lp-matched'),('host-lp','cuda-lp-matched')]


def analyze(trials, value, instances):
    groups=defaultdict(dict)
    for trial in trials:
        if trial['mode']!='timing':continue
        key=(trial['instance_id'],trial['config_id'])
        if trial['repetition'] in groups[key]:raise ValueError('duplicate paired repetition')
        groups[key][trial['repetition']]=trial
    rows=[];ratios=[]
    for instance in instances:
        for config in value['configurations']:
            observed=list(groups[(instance['id'],config['id'])].values())
            certified=[t for t in observed if successful(t)]
            times=[t['elapsed_ns'] for t in observed if t['elapsed_ns'] is not None and t['elapsed_ns']>0]
            rows.append({'instance':instance['id'],'configuration':config['id'],'planned':value['repetitions'],
                'attempted':len(observed),'certified':len(certified),
                'observed_median_ns':statistics.median(times) if times else None,
                'certified_median_ns':statistics.median(t['elapsed_ns'] for t in certified) if certified else None,
                'censored_timeouts':sum(t['status']=='timeout' or t['endpoint_class']=='timeout' for t in observed),
                'outcomes':dict(Counter(t['status']+'/'+str(t['endpoint_class']) for t in observed))})
        for left,right in COMPARISONS:
            a=groups[(instance['id'],left)];b=groups[(instance['id'],right)]
            pairs=[(a[r]['elapsed_ns'],b[r]['elapsed_ns']) for r in sorted(a.keys()&b.keys()) if successful(a[r]) and successful(b[r])]
            ratios.append({'instance':instance['id'],'comparison':left+'/'+right,
                'statistics':paired_ratio(pairs,value['analysis']['seed'],value['analysis']['resamples'])})
    return rows,ratios


def load(directory, config_path=CONFIG, verify=True):
    value,baseline,manifests=protocol(config_path)
    if read_json(directory/'campaign.json')!=value:raise ValueError('artifact protocol differs')
    trials,endpoints=load_trials(directory,value,manifests,file_hash(config_path))
    jobs={job[0]:job for job in schedule(value,manifests)}
    authority=ROOT/'artifacts/lp-campaign-ledgers'/baseline['id']
    if read_json(directory/'budget-binding.json')['ledger_directory']!=str(authority.relative_to(ROOT)):
        raise ValueError('wrong budget authority')
    with (authority/'campaign.lock').open('rb') as lock:
        fcntl.flock(lock,fcntl.LOCK_SH|fcntl.LOCK_NB)
        snapshot=(directory/'ledger.jsonl').read_bytes()
        if not (authority/'ledger.jsonl').read_bytes().startswith(snapshot):raise ValueError('ledger snapshot is not authoritative history')
        ledger=Ledger(directory,value['budget_authority']['sha256'])
        ledger._load()
        if ledger.pending():raise ValueError('unsettled ledger; resume coordinator recovery first')
    current=read_json(directory/'execution.json');old=read_json(directory/'reference-execution.json')
    if file_hash(directory/'source.tar')!=current['source_archive_sha256']:raise ValueError('source archive changed')
    if file_hash(ROOT/'artifacts/gpup3-reference/source.tar')!=old['source_archive_sha256']:raise ValueError('reference archive changed')
    settles={e['trial_id']:e for e in ledger.events if e['kind'] in ('settle','recover')}
    reservations={e['trial_id']:e for e in ledger.events if e['kind']=='reserve'}
    for trial in trials:
        identity=trial['id'];job=jobs[identity]
        if identity not in settles or identity not in reservations:raise ValueError('trial lacks settled reservation')
        gpu=job[2]['backend']!='host-lp';reservation=reservations[identity]
        if reservation['reserved_ns']!=(16 if gpu else 13)*NS or reservation['resource']!=('gpu' if gpu else 'cpu'):
            raise ValueError('trial reservation differs from full allowance')
        if trial['budget_authority_sha256']!=value['budget_authority']['sha256']:raise ValueError('trial budget authority differs')
        base=old if job[2]['binary']=='reference' else current
        for key in ['revision','dirty','source_tree_sha256','binary_sha256','code_object_sha256','highs_library_sha256','device','cpu_affinity','build_profile']:
            if trial['provenance'][key]!=base[key]:raise ValueError('trial executable/source identity differs: '+key)
        if trial['provenance']['schema_snapshot_sha256']!=current['schema_snapshot_sha256']:raise ValueError('schema snapshot identity differs')
        if trial['activity'] is not None:
            activity=read_json(checked_reference(directory,trial['activity']))
            if activity['reason']!='quiet' or activity['elapsed_ns']!=trial['activity_wait_ns']:raise ValueError('activity admission differs')
        elif gpu and trial['status']!='process_failure':raise ValueError('GPU trial lacks admission evidence')
        if trial['worker'] is not None:
            worker=read_json(checked_reference(directory,trial['worker']))
            for key in ['elapsed_ns','queue_ns','leased_ns','peak_rss_bytes']:
                if trial[key]!=worker[key]:raise ValueError('worker timing/resource differs: '+key)
            charge=worker['leased_ns'] if gpu else worker['elapsed_ns']
            if settles[identity]['charged_ns']!=charge:raise ValueError('worker/ledger charge differs')
            if gpu and worker['schema_version']!=2:raise ValueError('missing leased admission')
            if gpu and worker['reason']=='completed' and worker['activity']['reason']!='quiet':raise ValueError('launch without quiet leased admission')
        elif settles[identity]['charged_ns']!=reservation['reserved_ns']:
            raise ValueError('missing worker not fully charged')
        if identity in endpoints and verify:
            model=checked_reference(ROOT,job[1]['model'])
            run=subprocess.run([str(ROOT/'target/release/optimizer'),'lp-study','verify','--model',str(model),
                '--evidence',str(checked_reference(directory,trial['endpoint']))],capture_output=True,text=True,timeout=15)
            if run.returncode:raise ValueError('Rust endpoint verification failed: '+run.stderr[:1000])
    if not value['prior_gpu_ns']<=ledger.totals()<=min(900*NS,value['prior_gpu_ns']+600*NS):raise ValueError('supplementary budget accounting differs')
    return value,manifests,trials,endpoints,ledger,jobs


def complete_evidence(trials, planned):
    incomplete={'invalid_evidence','missing_evidence','process_failure','activity_blocked',
                'lease_timeout','lease_cancelled','cancelled_before_launch'}
    return len(trials)==planned and not any(t['status'] in incomplete for t in trials)


def report(directory, config_path=CONFIG, verify=True):
    value,manifests,trials,endpoints,ledger,jobs=load(directory,config_path,verify)
    instances=next(m['instances'] for m in manifests if m['partition']=='development')
    rows,ratios=analyze(trials,value,instances)
    observations=[]
    for trial in trials:
        endpoint=endpoints.get(trial['id'])
        observations.append({'id':trial['id'],'instance':trial['instance_id'],'configuration':trial['config_id'],
            'mode':trial['mode'],'elapsed_ns':trial['elapsed_ns'],'peak_rss_bytes':trial['peak_rss_bytes'],
            'diagnostics':endpoint['diagnostics'] if endpoint else None,
            'control':endpoint.get('control') if endpoint else None,
            'assessment':endpoint['assessment'] if endpoint else None})
    references=[]
    for path in sorted(directory.iterdir()):
        if path.is_file() and path.name not in ['summary.json','report.md','artifact-index.json']:
            references.append({'path':path.name,'sha256':file_hash(path)})
    write_json(directory/'artifact-index.json',references)
    summary={'schema_version':2,'status':'complete' if complete_evidence(trials,len(jobs)) else 'interim',
        'planned_trials':len(jobs),'attempted_trials':len(trials),'protocol_sha256':file_hash(config_path),
        'ledger_sha256':file_hash(directory/'ledger.jsonl'),'artifact_index_sha256':file_hash(directory/'artifact-index.json'),
        'prior_gpu_seconds':value['prior_gpu_ns']/NS,'additional_gpu_seconds':(ledger.totals()-value['prior_gpu_ns'])/NS,
        'cumulative_gpu_seconds':ledger.totals()/NS,
        'cpu_job_seconds':sum(t['elapsed_ns'] or 0 for t in trials if t['requested_backend']=='host-lp')/NS,
        'verification_seconds':sum(t['verification_ns'] or 0 for t in trials)/NS,
        'activity_wait_seconds':sum(t['activity_wait_ns'] or 0 for t in trials)/NS,
        'lease_queue_seconds':sum(t['queue_ns'] or 0 for t in trials)/NS,
        'rows':rows,'ratios':ratios,'observations':observations,
        'limitations':['Three repetitions give weak variability evidence; no cross-problem generalization.',
            'Ratios use only mutually certified repetitions. Failed endpoints and censored timeouts remain in coverage.',
            'Observed medians include work/time limits and are not time-to-certified-solution estimates.',
            'Profiles are separate synchronized runs. Primary runs add no profiling synchronization.',
            'RSS is a sampled process-tree estimate; LP buffer bytes exclude driver/context allocations.',
            'Hardware bandwidth/occupancy counters remain unavailable; startup and residency optimization are later work.']}
    write_json(directory/'summary.json',summary)
    lines=['# Matched FP64 study', '',f'Status: {summary["status"]}; {len(trials)}/{len(jobs)} attempts.',
        f'Additional GPU: {summary["additional_gpu_seconds"]:.6f} seconds; cumulative: {summary["cumulative_gpu_seconds"]:.6f}.','',
        '| Instance | Configuration | Certified / attempted | Observed median ms | Certified median ms | Timeouts |',
        '| --- | --- | --- | --- | --- | --- |']
    ms=lambda n:'unavailable' if n is None else f'{n/1e6:.3f}'
    for row in rows:lines.append(f'| {row["instance"]} | {row["configuration"]} | {row["certified"]}/{row["attempted"]} | {ms(row["observed_median_ns"])} | {ms(row["certified_median_ns"])} | {row["censored_timeouts"]} |')
    lines+=['','## Paired certified ratios','','| Instance | Comparison | Pairs | Ratio | 95% interval |','| --- | --- | --- | --- | --- |']
    for row in ratios:
        result=row['statistics'];tail='0 | unavailable | unavailable' if result is None else f'{result["paired_repetitions"]} | {result["ratio"]:.4f} | {result["ci95"]}'
        lines.append(f'| {row["instance"]} | {row["comparison"]} | {tail} |')
    lines+=['','## Limits','']+['- '+line for line in summary['limitations']]
    lines+=['',f'Raw index SHA-256: `{summary["artifact_index_sha256"]}`. Ledger SHA-256: `{summary["ledger_sha256"]}`.','']
    (directory/'report.md').write_text('\n'.join(lines))
    return summary

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input',type=Path,default=OUTPUT)
    parser.add_argument('--campaign',type=Path,default=CONFIG);args=parser.parse_args()
    result=report(args.input.resolve(),args.campaign)
    print(f'{result["status"]}: {result["attempted_trials"]}/{result["planned_trials"]}; {result["additional_gpu_seconds"]:.6f} additional GPU seconds')
