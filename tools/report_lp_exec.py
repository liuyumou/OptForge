"""Independent archive, authority, coverage and paired-cost report for ADR-0035."""
import argparse
from collections import Counter
import hashlib
from pathlib import Path
import statistics
import tarfile
from benchmark_lp_exec import jobs,effective,check_request,verify_endpoint,refs
from lp_exec_accept import check_acceptance,numerical
from lp_exec_budget import CONFIG,protocol
from lp_protocol import ROOT,Ledger,checked_reference,file_hash,read_json,write_json
from report_lp_setup import paired_ratios

def check_archive(directory,value):
    identity=read_json(directory/'execution.json')
    if read_json(directory/'campaign.json')!=value:raise ValueError('archived campaign differs')
    for name,key in [('optimizer','binary_sha256'),('lp_precision_exec','exec_binary_sha256'),('source.tar','source_archive_sha256')]:
        if file_hash(directory/name)!=identity[key]:raise ValueError('archived executable/source differs: '+name)
    images=read_json(directory/'code-objects.json')
    for name,sha in images.items():
        if file_hash(directory/name)!=sha:raise ValueError('archived image differs: '+name)
    if images['lp_pdhg_exec.cubin']!=identity['code_object_sha256']:raise ValueError('exact image identity differs')
    gate=read_json(directory/'native-gate.json')
    if not gate['native'] or gate['source_tree_sha256']!=identity['source_tree_sha256']:raise ValueError('native source gate differs')
    with tarfile.open(directory/'source.tar') as archive:
        members=archive.getmembers();names=[m.name for m in members]
        if names!=sorted(set(names)) or any(not m.isfile() or Path(m.name).is_absolute() or '..' in Path(m.name).parts for m in members):raise ValueError('source archive shape differs')
        digest=hashlib.sha256()
        for m in members:
            data=archive.extractfile(m).read();digest.update(m.name.encode()+b'\0'+data+b'\0')
            # Measurement workers and arithmetic must still be inspectable as measured.
            if m.name.startswith(('crates/','cuda/')) and (ROOT/m.name).read_bytes()!=data:raise ValueError('measured runtime source differs: '+m.name)
        if digest.hexdigest()!=identity['source_tree_sha256']:raise ValueError('source archive content identity differs')
    return identity

def check_trial(value,job,trial,directory,identity,events):
    key=job['id'];request=read_json(directory/(key+'.request.json'))
    if trial['id']!=key or trial['job']!=job or trial['campaign_sha256']!=file_hash(CONFIG) or trial['source_tree_sha256']!=identity['source_tree_sha256'] or trial['request_sha256']!=file_hash(directory/(key+'.request.json')):raise ValueError('trial frozen identity differs')
    check_request(value,job,directory,identity,request)
    if trial['artifacts']!=refs(directory,key):raise ValueError('trial artifact binding differs')
    rows=[e for e in events if e['trial_id']==key]
    if len(rows)!=2 or rows[0]['kind']!='reserve' or rows[1]['kind'] not in ['settle','recover']:raise ValueError('trial reservation/settlement differs')
    if any(e['resource']!='gpu' or e['phase']!=value['categories'][job['category']]['phase'] or e['reserved_ns']!=(effective(value,job)[2]+6)*10**9 for e in rows):raise ValueError('trial ledger phase/limit differs')
    charge=rows[1]['charged_ns']
    worker=None
    if trial['artifacts']['worker']:
        worker=read_json(checked_reference(directory,trial['artifacts']['worker']))
        if rows[1]['kind']=='settle' and charge!=worker['leased_ns']:raise ValueError('trial worker charge differs')
        if worker['activity']['device']!=value['device']:raise ValueError('trial worker device differs')
        if charge>rows[0]['reserved_ns']:raise ValueError('trial exceeded reservation')
    elif charge!=rows[0]['reserved_ns']:raise ValueError('missing worker was undercharged')
    if trial.get('charged_ns',charge)!=charge:raise ValueError('trial charge receipt differs')
    return worker

def check_discovery_image(value,directory,identity,acceptance):
    # Bind the restored discovery-only dependency to the immutable acceptance
    # archive. The numerical images and measured worker archive remain unchanged.
    expected={read_json(checked_reference(ROOT,ref))['images']['schedule_eval.cubin']['sha256'] for ref in acceptance.values()}
    if len(expected)!=1 or file_hash(directory/'schedule_eval.cubin') not in expected:raise ValueError('discovery image differs from accepted dependency')
    path=directory.parent/'discovery-image-repair.json'
    repair=read_json(path)
    if repair['identity']!='gpup-exec-discovery-image-repair-v1' or repair['source_tree_sha256']!=identity['source_tree_sha256'] or repair['dependency']['sha256'] not in expected or checked_reference(ROOT,repair['dependency']).read_bytes()!=(directory/'schedule_eval.cubin').read_bytes():raise ValueError('discovery repair binding differs')
    return repair

def report(value,directory):
    identity=check_archive(directory,value);acceptance=check_acceptance(value,identity)
    repair=check_discovery_image(value,directory,identity,acceptance)
    ledger=Ledger(directory,value['budget_authority']['sha256'],value['phase_gpu_seconds'],cumulative_ns=value['cumulative_gpu_ns'])
    if not ledger.path.read_bytes().endswith(b'\n'):raise ValueError('report cannot repair a torn ledger')
    ledger._load()
    if ledger.pending():raise ValueError('report cannot recover pending reservations')
    prefix=b''.join(ledger.path.read_bytes().splitlines(keepends=True)[:value['prior_events']])
    if hashlib.sha256(prefix).hexdigest()!=value['prior_ledger_sha256']:raise ValueError('historical ledger prefix differs')
    if ledger.totals()>value['cumulative_gpu_ns']:raise ValueError('cumulative allowance exceeded')
    for phase,cap in value['phase_gpu_seconds'].items():
        if ledger.totals(phase=phase)>cap*10**9:raise ValueError('phase cap exceeded')
    charges={category:sum(e['charged_ns'] for e in ledger.events if e['trial_id'].startswith(value['id']+'-'+category+'-') and e['resource']=='gpu') for category in value['categories']}
    if sum(charges.values())>value['combined_cap_seconds']*10**9 or any(charges[c]>value['categories'][c]['seconds']*10**9 for c in charges):raise ValueError('task cap exceeded')
    schedule=list(jobs(value));allowed={j['id'] for j in schedule}
    if {e['trial_id'] for e in ledger.events if e['trial_id'].startswith(value['id']+'-') and not e['trial_id'].startswith(value['id']+'-accept-')}!=allowed:raise ValueError('frozen attempt coverage differs')
    rows=[];latencies={};coverage={};statuses=Counter();verified=0;certified=0;cache_pairs={}
    for job in schedule:
        key=job['id'];trial=read_json(directory/(key+'.trial.json'));worker=check_trial(value,job,trial,directory,identity,ledger.events)
        assessment=None;e=None
        if trial['artifacts']['endpoint']:
            try:
                assessment=verify_endpoint(value,job,directory,identity);verified+=1;e=read_json(directory/(key+'.endpoint.json'));e=e.get('endpoint',e)
            except Exception:
                if trial['status'] not in ['invalid_evidence','interrupted']:raise
        if assessment!=trial['assessment']:raise ValueError('recorded assessment differs from independent verifier')
        exact=job['configuration']['backend']=='lp-exec-v1'
        eligible=bool(assessment and assessment['classification']=='certified_success' and worker and worker['reason']=='completed' and worker['returncode']==0 and trial['status']=='completed' and (e['witness']['status']=='accepted' if exact else e['record']['backend']==job['configuration']['backend']))
        instance=job['instance']['id'];config=job['configuration']['id'];kind=job['kind']
        row=dict(id=key,instance=instance,configuration=config,kind=kind,repetition=job['repetition'],status=trial['status'],verified=assessment is not None,certified=eligible,classification=None if assessment is None else assessment['classification'],elapsed_ns=None if worker is None else worker['elapsed_ns'])
        row.update(worker_reason=None if worker is None else worker['reason'],worker_returncode=None if worker is None else worker['returncode'],sampled_rss_bytes=None if worker is None else worker['peak_rss_bytes'])
        if e:
            diagnostic=e['witness']['diagnostics'] if exact else e['diagnostics']
            row.update(termination=e['witness']['status'] if exact else e['record']['termination'],iterations=e['witness']['physical_steps'] if exact else diagnostic['iterations'],phases_ns=diagnostic['phases_ns'],execution=e['witness']['execution'] if exact else e.get('execution'))
            if exact:row.update(operator=e['witness']['operator_receipt'],rounding_flags=e['witness']['rounding_flags'],failure=e['witness']['failure'])
        if exact and e:cache_pairs.setdefault((kind,instance,job['repetition']),{})[job['configuration']['mode']]=numerical(e)
        if kind=='timing':
            cell=coverage.setdefault(instance,{}).setdefault(config,dict(attempts=0,verified=0,certified=0))
            cell['attempts']+=1;cell['verified']+=int(assessment is not None);cell['certified']+=int(eligible)
            if eligible:latencies[(instance,config,job['repetition'])]=worker['elapsed_ns'];certified+=1
        statuses[row.get('termination',trial['status'])]+=1;rows.append(row)
    missing={r['id'] for r in rows if r['status']=='missing_evidence'}
    if missing!=set(repair['completed_missing_evidence_attempts']):raise ValueError('discovery failure roster differs')
    for key in missing:
        stderr=(directory/(key+'.stderr')).read_text()
        worker=read_json(directory/(key+'.worker.json'))
        if 'no device code object at ' not in stderr or '/schedule_eval.cubin' not in stderr or worker['returncode']!=2:raise ValueError('discovery failure diagnosis differs')
    comparisons=[]
    for instance in value['timing_instances']:
        for control,candidate in [('tuned-fp64','exact-cached'),('precision-fp64','exact-cached'),('exact-uncached','exact-cached')]:
            pairs=[(latencies[(instance,control,r)],latencies[(instance,candidate,r)]) for r in range(3) if (instance,control,r) in latencies and (instance,candidate,r) in latencies]
            comparisons.append(dict(instance=instance,control=control,candidate=candidate,paired=paired_ratios(pairs,value['analysis']['seed'],value['analysis']['resamples'])))
    equivalence=[dict(kind=k[0],instance=k[1],repetition=k[2],matched=set(v)=={'cached','uncached'} and v['cached']==v['uncached']) for k,v in sorted(cache_pairs.items())]
    return dict(identity='gpup-exec-report-v1',cache_equivalence=equivalence,discovery_repair=repair,source_tree_sha256=identity['source_tree_sha256'],attempts=len(rows),verified=verified,certified_timings=certified,statuses=dict(statuses),coverage=coverage,comparisons=comparisons,rows=rows,acceptance=acceptance,categories_ns=charges,task_gpu_ns=sum(charges.values()),cumulative_gpu_ns=ledger.totals(),ledger_events=len(ledger.events),ledger_sha256=file_hash(ledger.path),limitations=['Development data only; three repetitions per timing cell.','Ratios use paired certified successes and must be read with full coverage.','Worker elapsed time includes fresh preparation, assessments and output; lease time additionally charges admission/teardown.','Profile phases are host-observed envelopes, not hardware GPU-busy counters.','No preset or full expansion-state claim.'])

def export_report(value,directory,result,destination):
    """Deterministic, reviewable summaries; raw witnesses stay in the archive."""
    import csv
    import gzip
    import json
    from benchmark_lp import reference
    destination.mkdir(parents=True,exist_ok=True)
    write_json(destination/'summary.json',{k:v for k,v in result.items() if k not in ['rows']})
    write_json(destination/'profiles.json',[r for r in result['rows'] if r['kind']=='profile'])
    with (destination/'trials.csv').open('w',newline='') as output:
        fields=['id','instance','configuration','kind','repetition','status','verified','certified','classification','elapsed_ns','termination','iterations','failure']
        writer=csv.DictWriter(output,fieldnames=fields,extrasaction='ignore',lineterminator='\n');writer.writeheader();writer.writerows(result['rows'])
    payload=(json.dumps(result,sort_keys=True,separators=(',',':'))+'\n').encode()
    (destination/'analysis.json.gz').write_bytes(gzip.compress(payload,mtime=0))
    paths=sorted(set([*directory.rglob('*'),*(ROOT/value['acceptance_output']).rglob('*'),*(directory.parent/name for name in ['instruction-audit.json','exec.sass','exec.resources','native-device-freeze.log','source-only.log','source-only-final.log','post-study-contracts.log','oracle-final.log','report-original.json','report-original.log','discovery-image-repair.json'])]))
    files=[p for p in paths if p.is_file() and p.suffix!='.lock']
    write_json(destination/'provenance.json',dict(identity='gpup-exec-artifact-catalog-v1',protocol=reference(ROOT,CONFIG),files=[reference(ROOT,p) for p in files]))
    write_json(destination/'instructions.json',read_json(directory/'instruction-audit.json'))
    write_json(destination/'discovery-repair.json',read_json(directory.parent/'discovery-image-repair.json'))
    workers=[read_json(p) for p in directory.glob('*.worker.json')]+[read_json(p) for p in (ROOT/value['acceptance_output']).glob('*.worker.json')]
    write_json(destination/'resources.json',dict(identity='gpup-exec-resource-receipt-v1',limits=dict(cpu_seconds=value['cpu_cap_seconds'],build_jobs=4,host_rss_bytes=value['limits']['host_rss_bytes'],artifact_bytes=value['artifact_bytes'],categories=value['categories'],task_gpu_seconds=value['combined_cap_seconds'],cumulative_gpu_ns=value['cumulative_gpu_ns'],phase_gpu_seconds=value['phase_gpu_seconds']),categories_ns=result['categories_ns'],task_gpu_ns=result['task_gpu_ns'],cumulative_gpu_ns=result['cumulative_gpu_ns'],ledger_events=result['ledger_events'],ledger_sha256=result['ledger_sha256'],max_worker_sampled_rss_bytes=max(w['peak_rss_bytes'] for w in workers),catalog_artifact_bytes=sum(p.stat().st_size for p in files),cpu_time='CPU work is not metered by the GPU ledger; gates use four build jobs and no GPU opt-in.'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=ROOT/'artifacts/gpup-exec-v1/report.json');p.add_argument('--export',type=Path);a=p.parse_args();value=protocol();result=report(value,ROOT/value['output']);write_json(a.output,result)
    if a.export:export_report(value,ROOT/value['output'],result,a.export)
    print({k:result[k] for k in ['attempts','verified','certified_timings','task_gpu_ns','cumulative_gpu_ns','ledger_events','ledger_sha256']})
