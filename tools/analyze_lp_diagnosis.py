"""Summarize ADR-0015 diagnostics, checking raw hashes, ledger and trace counts."""
import argparse
import json
from pathlib import Path
import sqlite3
import statistics
from diagnose_lp import JOBS, OUTPUT, PRIOR_NS
from lp_protocol import ROOT, NS, Ledger, file_hash, read_json, strict_loads, write_json
from validate_artifacts import validator


def trace(path, expected_launches):
    database=sqlite3.connect('file:'+str(path)+'?mode=ro',uri=True)
    with database:
        apis=database.execute('select s.value,count(*),sum(d.end-d.start) from CUPTI_ACTIVITY_KIND_RUNTIME d join StringIds s on s.id=d.nameId group by s.value order by sum(d.end-d.start) desc').fetchall()
        kernels=database.execute('select s.value,count(*),sum(k.end-k.start),avg(k.end-k.start),k.gridX,k.blockX,k.dynamicSharedMemory from CUPTI_ACTIVITY_KIND_KERNEL k join StringIds s on s.id=k.shortName group by s.value').fetchall()
        count,busy,span=database.execute('select count(*),sum(end-start),max(end)-min(start) from CUPTI_ACTIVITY_KIND_KERNEL').fetchone()
        copies=database.execute('select copyKind,count(*),sum(bytes),sum(end-start) from CUPTI_ACTIVITY_KIND_MEMCPY group by copyKind').fetchall()
    database.close()
    if count!=expected_launches or next(x[1] for x in apis if x[0]=='cuLaunchKernel')!=count:
        raise ValueError('trace and endpoint launch counts differ')
    return {'apis':apis,'kernels':kernels,'launches':count,'kernel_busy_ns':busy,
            'kernel_span_ns':span,'kernel_gap_fraction':1-busy/span,'copies':copies,
            'copy_ns':sum(x[3] for x in copies)}


def main(directory):
    baseline=ROOT/'artifacts/gpup-baseline-v1'
    if file_hash(baseline/'summary.json')!='c57de898e75b5c422efd09ed3590e8e9d39f97f2b50ce99535f63d1c41a6cc63':
        raise ValueError('original baseline summary changed')
    original=(baseline/'ledger.jsonl').read_bytes();cumulative=(directory/'ledger.jsonl').read_bytes()
    if not cumulative.startswith(original):raise ValueError('historical ledger prefix changed')
    events=[strict_loads(line) for line in cumulative.splitlines()]
    compiled=validator('lp-ledger-v1.schema.json')
    for sequence,event in enumerate(events):
        compiled.validate(event)
        if event['sequence']!=sequence or event['campaign_sha256']!=events[0]['campaign_sha256']:
            raise ValueError('ledger sequence/identity differs')
    ledger=Ledger(directory,events[0]['campaign_sha256']);ledger.events=events
    if ledger.pending():raise ValueError('unresolved diagnostic reservations')
    expected={'gpup2-diagnosis-v1-'+job[0] for job in JOBS}
    added=events[len(original.splitlines()):]
    if {e['trial_id'] for e in added}!=expected:raise ValueError('supplementary ledger coverage differs')
    if ledger.totals()-PRIOR_NS>120*NS:raise ValueError('supplementary budget exceeded')
    results=[]
    endpoint_schema=validator('lp-endpoint-v1.schema.json')
    for label,name,iterations,traced in JOBS:
        result=read_json(directory/(label+'.result.json'))
        endpoint_path=directory/(label+'.endpoint.json');endpoint=read_json(endpoint_path)
        endpoint_schema.validate(endpoint)
        if not result['endpoint_verified'] or result['endpoint_sha256']!=file_hash(endpoint_path):
            raise ValueError('unverified/altered endpoint')
        charges=[e['charged_ns'] for e in added if e['trial_id']==result['id'] and e['kind']=='settle']
        if charges!=[result['charged_ns']]:raise ValueError('trial/ledger charge differs')
        row={'label':label,'job_ns':result['worker']['elapsed_ns'],
             'endpoint_class':endpoint['assessment']['classification'],
             'phases_ns':endpoint['diagnostics']['phases_ns']}
        if traced:row['trace']=trace(directory/(label+'.sqlite'),endpoint['diagnostics']['kernel_launches'])
        results.append(row)
    cost={}
    for name in ['small-4','irregular-256','irregular-2048','dense_block-1024']:
        raw=read_json(directory/f'cost-{name}.json')
        cost[name]={'rows':raw['rows'],'columns':raw['columns'],'nonzeros':raw['nonzeros'],
            'median_ns':{k:statistics.median(v) for k,v in raw['nanoseconds_per_call'].items()}}
    replays={}
    for name in ['irregular-256','scaling-64']:
        raw=read_json(directory/f'replay-{name}.json')
        if raw['primal_bit_mismatches'] or raw['dual_bit_mismatches']:raise ValueError('GPU/host replay differs')
        replays[name]=raw
    summary={'schema_version':1,'kind':'diagnosis_not_baseline','gpu_jobs':results,'cpu_costs':cost,
        'fixed_host_replays':replays,'python_cost':read_json(directory/'python-cost.json'),
        'baseline_orchestration':read_json(directory/'baseline-orchestration.json'),
        'additional_gpu_ns':ledger.totals()-PRIOR_NS,'cumulative_gpu_ns':ledger.totals(),
        'ledger_sha256':file_hash(directory/'ledger.jsonl'),
        'limitations':['supplementary profiles have one sample each and are excluded from baseline ratios',
            'Nsight tracing perturbs startup and submission; traced durations do not predict untraced latency',
            'CPU stack sampling unavailable (perf_event_open denied); bandwidth/occupancy counters not collected',
            'host fixed-control agreement checked on two development instances only',
            'schema reuse measured as a counterfactual, not a changed production runner']}
    write_json(directory/'diagnosis.json',summary)
    write_json(directory/'artifact-hashes.json',{p.name:file_hash(p) for p in sorted(directory.iterdir())
        if p.is_file() and p.name!='artifact-hashes.json'})
    print(f'7 endpoints and both traces verified; additional GPU {summary["additional_gpu_ns"]/NS:.9f}s; total {summary["cumulative_gpu_ns"]/NS:.9f}s')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=OUTPUT)
    args=parser.parse_args();main(args.input.resolve())
