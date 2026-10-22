"""Independent ADR-0039 archive, endpoint, common-trajectory and ledger report."""
import argparse
from collections import Counter
import hashlib
from pathlib import Path
import subprocess
import tarfile
from benchmark_lp_assess import jobs,effective,check_request,verify_endpoint,refs
from lp_assess_budget import CONFIG,PREFIX,protocol
from lp_protocol import ROOT,checked_reference,file_hash,read_json,validate,write_json
from lp_assess_admission import replay
from lp_assess_pr_review import projected_sha,review,RECEIPT

def ledger(value,path):
    raw=path.read_bytes();lines=raw.splitlines(keepends=True)
    if not raw.endswith(b'\n') or hashlib.sha256(b''.join(lines[:value['prior_events']])).hexdigest()!=PREFIX:raise ValueError('assessment ledger historical prefix differs')
    rows=[read_json_bytes(x) for x in lines];pending={};seen=set();phases=Counter();charges=Counter()
    for index,event in enumerate(rows):
        validate('ledger',event)
        if event['sequence']!=index or event['campaign_sha256']!=value['budget_authority']['sha256']:raise ValueError('assessment ledger sequence/campaign')
        key=event['reservation_id']
        if event['kind']=='reserve':
            if key in seen or event['charged_ns']!=0:raise ValueError('duplicate/refilled ledger reservation')
            pending[key]=event;seen.add(key)
        else:
            before=pending.pop(key,None)
            if before is None or any(before[k]!=event[k] for k in ['resource','phase','trial_id','reserved_ns']):raise ValueError('unmatched ledger settlement')
            if event['kind']=='recover' and event['charged_ns']!=event['reserved_ns']:raise ValueError('ledger recovery undercharged')
        if event['resource']=='gpu':
            phases[event['phase']]+=event['charged_ns']
            for category in value['categories']:
                if event['trial_id'].startswith(value['id']+'-'+category+'-'):charges[category]+=event['charged_ns']
    if pending or sum(phases.values())>value['cumulative_gpu_ns'] or any(phases[p]>cap*10**9 for p,cap in value['phase_gpu_seconds'].items()) or any(charges[k]>v['seconds']*10**9 for k,v in value['categories'].items()) or sum(charges.values())>value['combined_cap_seconds']*10**9:raise ValueError('assessment outstanding/exceeded resource authority')
    return rows,dict(charges),sum(phases.values())

def read_json_bytes(data):
    from validate_artifacts import read_json_bytes as read
    return read(data)

def check_assessment(trial,assessment):
    # A recovered interrupted identity can have a complete independently valid
    # endpoint. Keep its interruption and conservative charge while verifying it.
    if trial['status']=='interrupted' and trial['assessment'] is None:return
    if assessment!=trial['assessment']:raise ValueError('assessment assessment differs from retained trial')

def archive(directory,value):
    identity=read_json(directory/'execution.json')
    if read_json(directory/'campaign.json')!=value:raise ValueError('assessment archived protocol differs')
    for name,key in [('lp_precision_assess','exec_binary_sha256'),('source.tar','source_archive_sha256')]:
        if file_hash(directory/name)!=identity[key]:raise ValueError('assessment archive identity '+name)
    for name,sha in read_json(directory/'code-objects.json').items():
        if file_hash(directory/name)!=sha:raise ValueError('assessment archived CUDA inventory differs')
    native=read_json(directory/'native-gate.json')
    if not native.get('native') or native['source_tree_sha256']!=identity['source_tree_sha256']:raise ValueError('assessment exact-source native gate differs')
    digest=hashlib.sha256()
    with tarfile.open(directory/'source.tar') as frozen:
        members=frozen.getmembers();names=[m.name for m in members]
        if names!=sorted(set(names)) or any(not m.isfile() or Path(m.name).is_absolute() or '..' in Path(m.name).parts for m in members):raise ValueError('assessment source archive shape')
        for member in members:
            data=frozen.extractfile(member).read();digest.update(member.name.encode()+b'\0'+data+b'\0')
            if member.name.startswith(('crates/','cuda/','tools/','schemas/','benchmarks/','tests/')) or member.name in ['Cargo.toml','Cargo.lock']:
                if not (ROOT/member.name).is_file() or projected_sha(member.name)!=hashlib.sha256(data).hexdigest():raise ValueError('undeclared measured source change '+member.name)
    if digest.hexdigest()!=identity['source_tree_sha256']:raise ValueError('assessment source digest differs')
    return identity

def profile_comparisons(value,directory,verified_ids):
    result=[]
    for instance in value['profile_instances']:
        for arithmetic in ['tuned_fp64','accumulation_fp32']:
            endpoints={}
            for policy in ['fixed_200','bounded_800']:
                key=f"{value['id']}-profile-{instance}-0-{arithmetic}-{policy}"
                path=directory/(key+'.endpoint.json')
                if key in verified_ids and path.exists():endpoints[policy]=(key,read_json(path))
            if set(endpoints)!= {'fixed_200','bounded_800'}:
                result.append(dict(instance=instance,arithmetic=arithmetic,available=False));continue
            key,fixed=endpoints['fixed_200'];_,bounded=endpoints['bounded_800']
            wf=fixed['witness'];wb=bounded['witness'];of=wf['outcome'];ob=wb['outcome']
            if any(o['status']!='iteration_limit' or o['physical_steps']!=value['profile_work'] or o['logical_steps']!=value['profile_work'] for o in [of,ob]):
                result.append(dict(instance=instance,arithmetic=arithmetic,available=False,reason='incomplete diagnostic horizon'));continue
            frames=[read_json(directory/r['name']) for r in wf['traces']]
            model=checked_reference(ROOT,next(j for j in jobs(value) if j['instance']['id']==instance)['instance']['model'])
            checked=subprocess.run([str(directory/'lp_precision_assess'),'replay-trace',str(model),str(directory/(key+'.assess-request.json')),str(directory/(key+'.endpoint.json'))],capture_output=True,text=True,timeout=value['verification_seconds'])
            if checked.returncode:raise ValueError('profile independent all-boundary assessment failed '+checked.stderr[:2000])
            from lp_protocol import strict_loads
            assessments=strict_loads(checked.stdout);analysis=replay(frames,wf['initial'],[a['gap_closed'] for a in assessments],None if of['point'] is None else of['point']['iteration'],fixed['assessment']['gap_closed'])
            shared=min(len(wf['traces']),len(wb['traces']))
            same_prefix=all(wf['traces'][i]['sha256']==wb['traces'][i]['sha256'] for i in range(shared))
            equal_work=of['physical_steps']==ob['physical_steps'] and of['logical_steps']==ob['logical_steps']
            if shared and not same_prefix:raise ValueError('assessment policies changed a diagnostic trajectory')
            if equal_work and ([e['decision'] for e in ob['events']]!=analysis['decisions'] or __import__('json').dumps(of['point'],sort_keys=True)!=__import__('json').dumps(ob['point'],sort_keys=True) or of['controller_checks']!=ob['controller_checks']):raise ValueError('online schedule differs from common-trajectory replay')
            result.append(dict(instance=instance,arithmetic=arithmetic,available=True,common_frames=shared,identical_prefix=same_prefix,equal_work=equal_work,
                fixed_assessments=of['assessments'],bounded_assessments=ob['assessments'],fixed_phases_ns=wf['phases_ns'],bounded_phases_ns=wb['phases_ns'],**analysis))
    return result

def report():
    value=protocol();directory=ROOT/value['output'];identity=archive(directory,value)
    from lp_assess_accept import check_acceptance
    acceptance=check_acceptance(value,identity)
    events,charges,cumulative=ledger(value,directory/'ledger.jsonl');rows=[];timings={};coverage={}
    for job in jobs(value):
        key=job['id'];path=directory/(key+'.trial.json');instance=job['instance']['id'];config=job['configuration']['id']
        if not path.exists():
            if any(e['trial_id']==key for e in events):raise ValueError('assessment attempted identity lacks trial')
            rows.append(dict(id=key,instance=instance,configuration=config,kind=job['kind'],repetition=job['repetition'],status='unexecuted',verified=False,certified=False));continue
        trial=read_json(path);request=read_json(directory/(key+'.request.json'))
        if trial['id']!=key or trial['job']!=job or trial['campaign_sha256']!=file_hash(CONFIG) or trial['source_tree_sha256']!=identity['source_tree_sha256'] or trial['request_sha256']!=file_hash(directory/(key+'.request.json')):raise ValueError('assessment trial identity differs')
        check_request(value,job,directory,identity,request)
        if trial['artifacts']!=refs(directory,key):raise ValueError('assessment raw artifact hashes differ')
        transactions=[e for e in events if e['trial_id']==key]
        if len(transactions)!=2 or transactions[0]['kind']!='reserve' or transactions[1]['kind'] not in ['settle','recover'] or any(e['reserved_ns']!=(effective(value,job)[2]+6)*10**9 or e['phase']!=value['categories'][job['category']]['phase'] for e in transactions):raise ValueError('assessment reservation differs')
        worker=read_json(directory/(key+'.worker.json')) if trial['artifacts']['worker'] else None
        charge=transactions[1]['charged_ns']
        if charge!=trial.get('charged_ns',charge) or charge!=(worker['leased_ns'] if worker and transactions[1]['kind']=='settle' else transactions[0]['reserved_ns']):raise ValueError('assessment charge differs')
        if worker and (worker['activity']['device']!=value['device'] or charge>transactions[0]['reserved_ns']):raise ValueError('assessment worker device/charge differs')
        assessed=None;endpoint=None;error=None
        if trial['artifacts']['endpoint']:
            try:assessed=verify_endpoint(value,job,directory,identity);endpoint=read_json(directory/(key+'.endpoint.json'))
            except Exception as e:
                if trial['assessment'] is not None:raise
                error=str(e)
        check_assessment(trial,assessed)
        good=bool(assessed and assessed['gap_closed'] and endpoint['witness']['outcome']['status']=='accepted' and worker and worker['reason']=='completed' and worker['returncode']==0 and trial['status']=='completed')
        row=dict(id=key,instance=instance,configuration=config,kind=job['kind'],repetition=job['repetition'],status=trial['status'],verified=assessed is not None,certified=good,assessment=assessed,verification_error=error,elapsed_ns=None if worker is None else worker['elapsed_ns'],charged_ns=charge,sampled_rss_bytes=None if worker is None else worker['peak_rss_bytes'])
        if endpoint:
            o=endpoint['witness']['outcome'];row.update(termination=o['status'],failure=o['failure'],physical_steps=o['physical_steps'],logical_steps=o['logical_steps'],assessments=o['assessments'],controller_checks=o['controller_checks'],restarts=o['restarts'],phases_ns=endpoint['witness']['phases_ns'])
        if job['kind']=='timing':
            cell=coverage.setdefault(instance,{}).setdefault(config,dict(attempts=0,verified=0,certified=0));cell['attempts']+=1;cell['verified']+=assessed is not None;cell['certified']+=good
            if good:timings[(instance,config,job['repetition'])]=worker['elapsed_ns']
        rows.append(row)
    comparisons=[]
    from report_lp_setup import paired_ratios
    for instance in value['timing_instances']:
        for arithmetic in ['tuned_fp64','accumulation_fp32']:
            fixed=arithmetic+'-fixed_200';candidate=arithmetic+'-bounded_800'
            pairs=[(timings[(instance,fixed,r)],timings[(instance,candidate,r)]) for r in range(3) if (instance,fixed,r) in timings and (instance,candidate,r) in timings]
            comparisons.append(dict(instance=instance,arithmetic=arithmetic,pairs=len(pairs),paired_uncertainty=None if not pairs else paired_ratios(pairs,seed=value['analysis']['seed'],resamples=value['analysis']['resamples'])))
    return dict(source_review=None if review() is None else dict(path=str(RECEIPT.relative_to(ROOT)),sha256=file_hash(RECEIPT)),identity='gpup-assess-report-v1',source_tree_sha256=identity['source_tree_sha256'],cpu_admission=value['cpu_admission'],acceptance=acceptance,planned_attempts=60,attempts=sum(r['status']!='unexecuted' for r in rows),verified=sum(r['verified'] for r in rows),certified_timings=sum(r['kind']=='timing' and r['certified'] for r in rows),coverage=coverage,comparisons=comparisons,profiles=profile_comparisons(value,directory,{r['id'] for r in rows if r['verified']}),rows=rows,categories_ns=charges,task_gpu_ns=sum(charges.values()),cumulative_gpu_ns=cumulative,ledger_events=len(events),ledger_sha256=file_hash(directory/'ledger.jsonl'))

def report_output(output=None):
    historical=ROOT/'artifacts/gpup-assess-v1/report.json'
    output=output or ROOT/'artifacts/gpup-assess-pr-review-20261022/report-final.json'
    if output.resolve() in {historical.resolve(),historical.with_name('report-reviewed.json').resolve()}:raise ValueError('PR review cannot overwrite either historical report')
    return output

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args()
    output=report_output(a.output)
    r=report();write_json(output,r);print({k:r[k] for k in ['attempts','verified','certified_timings','task_gpu_ns','cumulative_gpu_ns','ledger_events','ledger_sha256']})
if __name__=='__main__':main()
