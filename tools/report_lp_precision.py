"""Verify every GPUP-5 endpoint, frozen pairing and cumulative budget before reporting."""
import argparse,fcntl,re,statistics,subprocess
from collections import Counter,defaultdict
from pathlib import Path
from benchmark_lp_precision import CONFIG,OUTPUT,protocol,require_prior_history
from benchmark_lp import schedule
from lp_protocol import ROOT,NS,Ledger,checked_reference,file_hash,read_json,write_json
from lp_report import load_trials,successful,paired_ratio
from lp_copt import gpu_started

def use_historical_snapshot(ledger,snapshot,active):
    if not snapshot.endswith(b'\n') or not active.startswith(snapshot):
        raise ValueError('archived campaign ledger is not an intact historical prefix')
    ledger.events=ledger.events[:len(snapshot.splitlines())]
    if ledger.pending():raise ValueError('historical snapshot has unsettled reservations')

def report(directory,config_path,binary):
    value,base,manifests=protocol(config_path);trials,endpoints=load_trials(directory,value,manifests,file_hash(config_path))
    identities=read_json(directory/'configuration-executions.json');groups=defaultdict(dict);work=[]
    for trial in trials:
        expected=identities[trial['config_id']]
        for key in expected.keys()-{'telemetry_before','telemetry_after'}:
            if trial['provenance'][key]!=expected[key]:raise ValueError('trial provenance differs')
        if trial['mode']=='timing':groups[(trial['instance_id'],trial['config_id'])][trial['repetition']]=trial
        if trial['id'] not in endpoints:continue
        endpoint=endpoints[trial['id']];external=trial['requested_backend'].startswith('copt-')
        job=next(j for j in schedule(value,manifests) if j[0]==trial['id']);model=checked_reference(ROOT,job[1]['model']);path=checked_reference(directory,trial['endpoint'])
        cmd='external-verify' if external else 'verify'
        result=subprocess.run([str(binary),'lp-study',cmd,'--model',str(model),'--evidence',str(path)],capture_output=True,text=True,timeout=12)
        if result.returncode:raise ValueError('independent endpoint verification: '+trial['id']+': '+result.stderr[:500])
        if external:
            witness=endpoint['witness'];log=path.with_suffix('.copt.log')
            confirmed=gpu_started(log.read_text())
            if witness['gpu_confirmed']!=confirmed:raise ValueError('COPT actual GPU log differs')
            if witness['library_sha256']!=expected['copt_library_sha256'] or witness['binding_sha256']!=expected['copt_binding_sha256']:raise ValueError('COPT library identity differs')
            native_times=re.findall(r'Status:.*?Time:\s*([0-9.]+)s',log.read_text())
            native_seconds=float(native_times[-1]) if native_times else None
            observation=dict(iterations=witness['iterations'],limitations=witness['limitations'],
                native_solve_seconds_rounded=native_seconds,
                outside_native_solve_ns=max(0,trial['elapsed_ns']-round(native_seconds*NS)) if native_seconds is not None else None,
                outside_native_scope='Combined binding/license/model setup, witness export, Rust certification, process startup and teardown; native log time is rounded to 0.01 seconds.')
        else:
            observation=dict(diagnostics=endpoint['diagnostics'],execution=endpoint.get('execution'),precision=endpoint.get('precision'),control=endpoint.get('control'))
        work.append(dict(trial=trial['id'],config=trial['config_id'],instance=trial['instance_id'],mode=trial['mode'],assessment=endpoint['assessment'],observations=observation))
    ledger_dir=ROOT/'artifacts/lp-campaign-ledgers'/base['id'];require_prior_history(ledger_dir/'ledger.jsonl')
    with (ledger_dir/'campaign.lock').open('rb') as lock:
        fcntl.flock(lock,fcntl.LOCK_SH|fcntl.LOCK_NB)
        ledger=Ledger(ledger_dir,value['budget_authority']['sha256'],base['phase_gpu_seconds'],cumulative_ns=value['cumulative_gpu_ns']);ledger._load()
        if ledger.pending():raise ValueError('unsettled campaign reservations')
        # Later diagnostics append to the same authority; historical charges stay
        # bound to the original settled snapshot, never to subsequent jobs.
        use_historical_snapshot(ledger,(directory/'ledger.jsonl').read_bytes(),ledger.path.read_bytes())
        charged=ledger.totals()
        if charged>value['cumulative_gpu_ns']:raise ValueError('slice cumulative ceiling exceeded')
        settled={e['trial_id'] for e in ledger.events if e['kind'] in ('settle','recover')}
        if any(t['id'] not in settled for t in trials):raise ValueError('trial missing ledger settlement')
    rows=[];ratios=[];instances=next(m['instances'] for m in manifests if m['partition']=='development')
    for instance in instances:
        for config in value['configurations']:
            observed=list(groups[(instance['id'],config['id'])].values());accepted=[t for t in observed if successful(t)]
            rows.append(dict(instance=instance['id'],config=config['id'],attempted=len(observed),planned=3,certified=len(accepted),median_ns=statistics.median(t['elapsed_ns'] for t in accepted) if accepted else None,outcomes=dict(Counter(t['status']+'/'+str(t['endpoint_class']) for t in observed))))
            if config['id']=='reference-matched':continue
            for reference in ['reference-matched','precision-fp64']:
                left=groups[(instance['id'],reference)];right=groups[(instance['id'],config['id'])]
                pairs=[(left[r]['elapsed_ns'],right[r]['elapsed_ns']) for r in left.keys()&right.keys() if successful(left[r]) and successful(right[r])]
                ratios.append(dict(instance=instance['id'],reference=reference,candidate=config['id'],statistics=paired_ratio(pairs,value['analysis']['seed'],value['analysis']['resamples'])))
    expected=len(list(schedule(value,manifests)));bad={'process_failure','invalid_evidence','missing_evidence','lease_timeout','lease_cancelled','cancelled_before_launch','activity_blocked'}
    summary=dict(schema_version=4,status='complete' if len(trials)==expected and not any(t['status'] in bad for t in trials) else 'interim',planned=expected,attempted=len(trials),verified_endpoints=len(endpoints),prior_gpu_seconds=value['prior_gpu_ns']/NS,additional_gpu_seconds=(charged-value['prior_gpu_ns'])/NS,cumulative_gpu_seconds=charged/NS,ceiling_gpu_seconds=value['cumulative_gpu_ns']/NS,protocol_sha256=file_hash(config_path),ledger_sha256=file_hash(directory/'ledger.jsonl'),outcomes=dict(Counter(t['status']+'/'+str(t['endpoint_class']) for t in trials)),rows=rows,ratios=ratios,work=work)
    write_json(directory/'summary.json',summary)
    files=[dict(path=p.name,sha256=file_hash(p)) for p in sorted(directory.iterdir()) if p.is_file() and p.name!='artifact-index.json']
    write_json(directory/'artifact-index.json',files)
    print(summary['status'],len(trials),'attempts;',len(endpoints),'verified endpoints;',charged/NS,'campaign GPU seconds')
    return summary
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',type=Path,default=OUTPUT);p.add_argument('--campaign',type=Path,default=CONFIG);p.add_argument('--binary',type=Path,default=ROOT/'target/release/optimizer');a=p.parse_args();report(a.directory,a.campaign,a.binary)
