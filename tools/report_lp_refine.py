"""Independently verify every frozen ADR-0037 attempt, endpoint and ledger charge."""
import argparse
from collections import Counter
import hashlib
from pathlib import Path
import tarfile
from benchmark_lp_refine import jobs,effective,check_request,verify_endpoint,refs,endpoint_shape
from lp_refine_accept import check_acceptance
from lp_refine_budget import CONFIG,PREFIX,protocol
from lp_protocol import ROOT,checked_reference,file_hash,read_json,validate,write_json
from lp_refine_review import pre_review_sha,changes,RECEIPT


def archive(directory,value):
    identity=read_json(directory/'execution.json')
    if read_json(directory/'campaign.json')!=value:raise ValueError('refine archived protocol differs')
    for name,key in [('optimizer','binary_sha256'),('lp_precision_refine','exec_binary_sha256'),('source.tar','source_archive_sha256')]:
        if file_hash(directory/name)!=identity[key]:raise ValueError('refine archive identity: '+name)
    inventory=read_json(directory/'code-objects.json')
    for name,sha in inventory.items():
        if file_hash(directory/name)!=sha:raise ValueError('refine image/build receipt differs: '+name)
    if inventory['lp_pdhg_refine.cubin']!=identity['code_object_sha256']:raise ValueError('refine image identity differs')
    gate=read_json(directory/'native-gate.json')
    if not gate['native'] or gate['source_tree_sha256']!=identity['source_tree_sha256']:raise ValueError('refine source native gate differs')
    correction_path=ROOT/'docs/benchmarks/data/refine/report-correction.json'
    correction=read_json(correction_path) if correction_path.exists() else None
    corrections={} if correction is None else {f['path']:f for f in correction['files']}
    if correction is not None and (correction['identity']!='gpup-refine-report-correction-v1' or correction['source_tree_sha256']!=identity['source_tree_sha256'] or len(corrections)!=len(correction['files']) or not set(corrections)<={'tools/report_lp_refine.py','tests/integration/test_lp_refine.py'}):raise ValueError('report correction scope/identity differs')
    if correction is not None:checked_reference(ROOT,correction['original_failure'])
    changed=set()
    with tarfile.open(directory/'source.tar') as frozen:
        members=frozen.getmembers();names=[m.name for m in members]
        if names!=sorted(set(names)) or any(not m.isfile() or Path(m.name).is_absolute() or '..' in Path(m.name).parts for m in members):raise ValueError('refine source archive shape')
        digest=hashlib.sha256()
        for member in members:
            content=frozen.extractfile(member).read();digest.update(member.name.encode()+b'\0'+content+b'\0')
            if member.name.startswith(('crates/','cuda/','tools/','schemas/','benchmarks/','tests/')) or member.name in ['Cargo.toml','Cargo.lock']:
                projected=pre_review_sha(member.name)
                if projected!=hashlib.sha256(content).hexdigest():
                    fix=corrections.get(member.name)
                    if not fix or fix['measured_sha256']!=hashlib.sha256(content).hexdigest() or fix['reviewed_sha256']!=projected:raise ValueError('undeclared measured source change: '+member.name)
                    changed.add(member.name)
        if digest.hexdigest()!=identity['source_tree_sha256']:raise ValueError('refine archived source tree differs')
    if changed!=set(corrections):raise ValueError('report correction file set differs')
    identity['report_correction']=correction
    return identity


def ledger(value,path):
    raw=path.read_bytes();lines=raw.splitlines(keepends=True)
    if not raw.endswith(b'\n') or hashlib.sha256(b''.join(lines[:value['prior_events']])).hexdigest()!=PREFIX:raise ValueError('refine ledger historical prefix differs')
    rows=[read_json_bytes(x) for x in lines];pending={};seen=set();phases=Counter();charges=Counter()
    for index,event in enumerate(rows):
        validate('ledger',event)
        if event['sequence']!=index or event['campaign_sha256']!=value['budget_authority']['sha256']:raise ValueError('refine ledger sequence/campaign')
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
    if pending or sum(phases.values())>value['cumulative_gpu_ns'] or any(phases[p]>cap*10**9 for p,cap in value['phase_gpu_seconds'].items()) or any(charges[k]>v['seconds']*10**9 for k,v in value['categories'].items()) or sum(charges.values())>value['combined_cap_seconds']*10**9:raise ValueError('refine outstanding/exceeded resource authority')
    return rows,dict(charges),sum(phases.values())


def read_json_bytes(data):
    from validate_artifacts import read_json_bytes as read
    return read(data)


def check_assessment(trial,assessment):
    # A recovered interrupted identity can have a complete independently valid
    # endpoint. Keep its interruption and conservative charge while verifying it.
    if trial['status']=='interrupted' and trial['assessment'] is None:return
    if assessment!=trial['assessment']:raise ValueError('refine assessment differs from retained trial')



def verify_prior_refusal(value,events,directory):
    parent=read_json(checked_reference(ROOT,value['previous_protocol']))
    original=ROOT/parent['output'];identity=read_json(original/'execution.json')
    for name,key in [('optimizer','binary_sha256'),('lp_precision_refine','exec_binary_sha256'),('source.tar','source_archive_sha256')]:
        if file_hash(original/name)!=identity[key]:raise ValueError('original refusal archive differs: '+name)
    inventory=read_json(original/'code-objects.json')
    for name,sha in inventory.items():
        if file_hash(original/name)!=sha or file_hash(directory/name)!=sha:raise ValueError('continuation changed executable/image/build input: '+name)
    for name in ['optimizer','lp_precision_refine']:
        if file_hash(original/name)!=file_hash(directory/name):raise ValueError('continuation changed numerical executable')
    allowed={'tools/lp_activity.py','tools/lp_refine_budget.py','tools/report_lp_refine.py','tests/integration/test_lp_refine.py','tests/integration/test_lp_overheads.py'}
    changed=[];digest=hashlib.sha256()
    with tarfile.open(original/'source.tar') as archive:
        for item in archive.getmembers():
            if not item.isfile() or Path(item.name).is_absolute() or '..' in Path(item.name).parts:raise ValueError('original refusal source shape')
            content=archive.extractfile(item).read();digest.update(item.name.encode()+b'\0'+content+b'\0')
            if item.name.startswith(('crates/','cuda/','tools/','schemas/','benchmarks/','tests/')) or item.name in ['Cargo.toml','Cargo.lock']:
                projected=pre_review_sha(item.name)
                if projected!=hashlib.sha256(content).hexdigest():
                    if item.name not in allowed:raise ValueError('continuation changed undeclared source: '+item.name)
                    changed.append(dict(path=item.name,original_sha256=hashlib.sha256(content).hexdigest(),continued_sha256=projected))
    if digest.hexdigest()!=identity['source_tree_sha256']:raise ValueError('original refusal source identity')
    gate=read_json(original/'native-gate.json')
    if not gate['native'] or gate['source_tree_sha256']!=identity['source_tree_sha256']:raise ValueError('original source native gate differs')
    acceptance=ROOT/parent['acceptance_output'];key=parent['id']+'-accept-regular'
    worker=read_json(acceptance/(key+'.worker.json'));request=read_json(acceptance/(key+'.request.json'));binding=read_json(acceptance/(key+'.source.json'))
    if binding['source_tree_sha256']!=identity['source_tree_sha256'] or binding['request_sha256']!=file_hash(acceptance/(key+'.request.json')) or worker['reason']!='activity_blocked' or worker['returncode'] is not None or worker['elapsed_ns']!=0 or worker['peak_rss_bytes']!=0 or worker['activity']['device']!=value['device'] or 'telemetry_unavailable' not in worker['activity']['reason']:raise ValueError('original activity refusal differs')
    transactions=[e for e in events if e['trial_id'].startswith(parent['id']+'-')]
    if len(transactions)!=2 or transactions[0]['trial_id']!=key or transactions[0]['kind']!='reserve' or transactions[1]['kind']!='settle' or transactions[1]['charged_ns']!=125948387 or worker['leased_ns']!=125948387 or transactions[0]['reserved_ns']!=126000000000:raise ValueError('original refusal charge/attempt differs')
    if list(original.glob('*.trial.json')):raise ValueError('original numerical cells must remain unexecuted')
    return dict(id=key,status='activity_blocked',charged_ns=125948387,source_tree_sha256=identity['source_tree_sha256'],request_sha256=file_hash(acceptance/(key+'.request.json')),worker_sha256=file_hash(acceptance/(key+'.worker.json')),unexecuted_primary_cells=108,unexecuted_other_acceptance_gates=6,changed_source=changed)


def load_endpoint(job,path):
    if job['configuration']['backend']=='lp-refine-v1':return read_json(path)
    return endpoint_shape(path,'compact-v1')


def report():
    value=protocol();directory=ROOT/value['output'];identity=archive(directory,value);check_acceptance(value,identity)
    events,charges,cumulative=ledger(value,directory/'ledger.jsonl');prior=verify_prior_refusal(value,events,directory);cohort_charges=dict(charges);charges['accept']=charges.get('accept',0)+prior['charged_ns'];rows=[];timings={};coverage={};states=Counter();verified=0;certified=0
    for job in jobs(value):
        key=job['id'];path=directory/(key+'.trial.json');instance=job['instance']['id'];config=job['configuration']['id']
        if not path.exists():
            if any(e['trial_id']==key for e in events):raise ValueError('attempted identity has no retained trial')
            rows.append(dict(id=key,instance=instance,configuration=config,kind=job['kind'],repetition=job['repetition'],status='unexecuted',verified=False,certified=False));continue
        trial=read_json(path);request=read_json(directory/(key+'.request.json'))
        if trial['id']!=key or trial['job']!=job or trial['campaign_sha256']!=file_hash(CONFIG) or trial['source_tree_sha256']!=identity['source_tree_sha256'] or trial['request_sha256']!=file_hash(directory/(key+'.request.json')):raise ValueError('refine trial identity differs')
        check_request(value,job,directory,identity,request)
        if trial['artifacts']!=refs(directory,key):raise ValueError('refine trial artifact binding differs')
        transactions=[e for e in events if e['trial_id']==key]
        if len(transactions)!=2 or transactions[0]['kind']!='reserve' or transactions[1]['kind'] not in ['settle','recover'] or any(e['reserved_ns']!=(effective(value,job)[2]+6)*10**9 or e['phase']!=value['categories'][job['category']]['phase'] for e in transactions):raise ValueError('refine trial charge/reservation differs')
        worker=read_json(directory/(key+'.worker.json')) if trial['artifacts']['worker'] else None
        charge=transactions[1]['charged_ns']
        if charge!=trial.get('charged_ns',charge) or charge!=(worker['leased_ns'] if worker and transactions[1]['kind']=='settle' else transactions[0]['reserved_ns']):raise ValueError('refine worker charge differs')
        if worker and (worker['activity']['device']!=value['device'] or charge>transactions[0]['reserved_ns']):raise ValueError('refine worker device/reservation differs')
        endpoint=None;assessment=None;verification_error=None
        if trial['artifacts']['endpoint']:
            try:
                endpoint=load_endpoint(job,directory/(key+'.endpoint.json'));assessment=verify_endpoint(value,job,directory,identity)
            except Exception as error:
                if trial['assessment'] is not None:raise
                endpoint=None;verification_error=str(error)
        check_assessment(trial,assessment)
        good=bool(assessment and assessment['gap_closed'] and worker and worker['reason']=='completed' and worker['returncode']==0 and trial['status']=='completed' and (endpoint['witness']['outcome']['status']=='accepted' if job['configuration']['backend']=='lp-refine-v1' else endpoint['record']['backend']=='cuda-lp-tuned'))
        row=dict(id=key,instance=instance,configuration=config,kind=job['kind'],repetition=job['repetition'],status=trial['status'],verified=assessment is not None,certified=good,classification=None if assessment is None else assessment['classification'],elapsed_ns=None if worker is None else worker['elapsed_ns'],charged_ns=charge,sampled_rss_bytes=None if worker is None else worker['peak_rss_bytes'],verification_error=verification_error)
        if endpoint and 'witness' in endpoint:
            o=endpoint['witness']['outcome'];row.update(termination=o['status'],failure=o['failure'],work=o['work'],observations=endpoint['witness']['observations'],actual_width=o['width'])
        elif endpoint:row.update(termination=endpoint['record']['termination'],iterations=endpoint['diagnostics']['iterations'])
        states[row.get('termination',trial['status'])]+=1;verified+=assessment is not None
        if job['kind']=='timing':
            cell=coverage.setdefault(instance,{}).setdefault(config,dict(attempts=0,verified=0,certified=0));cell['attempts']+=1;cell['verified']+=assessment is not None;cell['certified']+=good;certified+=good
            if good:timings[(instance,config,job['repetition'])]=worker['elapsed_ns']
        rows.append(row)
    comparisons=[]
    for name in value['timing_instances']:
        for configuration in value['configurations'][1:]:
            config=configuration['id'];pairs=[(timings[(name,'tuned-fp64',r)],timings[(name,config,r)]) for r in range(3) if (name,'tuned-fp64',r) in timings and (name,config,r) in timings]
            from report_lp_setup import paired_ratios
            comparisons.append(dict(instance=name,candidate=config,pairs=len(pairs),paired_uncertainty=None if not pairs else paired_ratios(pairs,**{k:value['analysis'][k] for k in ['seed','resamples']})))
    return dict(identity='gpup-refine-report-v1',source_tree_sha256=identity['source_tree_sha256'],report_correction=identity['report_correction'],planned_attempts=108,attempts=sum(x['status']!='unexecuted' for x in rows),verified=verified,certified_timings=certified,statuses=dict(states),coverage=coverage,comparisons=comparisons,rows=rows,prior_refusal=prior,cohort_categories_ns=cohort_charges,categories_ns=charges,task_gpu_ns=sum(charges.values()),cumulative_gpu_ns=cumulative,ledger_events=len(events),ledger_sha256=file_hash(directory/'ledger.jsonl'),limitations=['Development roster on the selected RTX 5090 only.','Native FP64 state and host control; no expansion state, assessment policy or supported preset.','Per-product independent host interval guards are included in full cost and may dominate.','Host-observed device phases include synchronization and readback; no hardware-counter claim.','Ratios require paired certified successes; missing or rejected cases are not timings.'])


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args()
    historical=ROOT/protocol()['output'].replace('/study','/report.json')
    output=a.output or (ROOT/'artifacts/gpup-refine-review-20261022/report.json' if changes() else historical)
    if changes() and output.resolve()==historical.resolve():raise ValueError('review must not overwrite historical report')
    value=report();write_json(output,value)
    if changes():write_json(output.with_suffix('.source-review.json'),dict(review_source_sha256=file_hash(RECEIPT),report_sha256=file_hash(output)))
    print({k:value[k] for k in ['attempts','verified','certified_timings','task_gpu_ns','cumulative_gpu_ns','ledger_events','ledger_sha256']})
if __name__=='__main__':main()
