"""Independently verify frozen GPUP-6 attempts and report coverage, pairing and recovery costs."""
import argparse
from collections import Counter,defaultdict
import fcntl
import hashlib
import statistics
import subprocess
from pathlib import Path
from benchmark_lp_adaptive import jobs
from lp_adaptive_budget import CONFIG,protocol,ledger_for
from lp_protocol import ROOT,NS,checked_reference,digest,encoded,file_hash,read_json,validate,write_json
from lp_report import paired_ratio,successful


def report(directory,binary,config_path=CONFIG):
    value=protocol(config_path);planned={j[0]:j for j in jobs(value)};campaign_hash=file_hash(config_path)
    identities=read_json(directory/'configuration-executions.json');execution=read_json(directory/'execution.json')
    if file_hash(directory/'source.tar')!=execution['source_archive_sha256'] or file_hash(directory/'optimizer')!=execution['binary_sha256']:
        raise ValueError('archived source/binary identity differs')
    if file_hash(binary)!=execution['binary_sha256']:raise ValueError('verify with the archived measured executable')
    image_manifest=directory/'code-objects.json'
    if image_manifest.exists():
        for name,expected in read_json(image_manifest).items():
            if name not in ('schedule_eval.cubin','lp_pdhg.cubin','lp_pdhg_tuned.cubin','lp_pdhg_precision.cubin') or file_hash(directory/name)!=expected:raise ValueError('archived code image differs')
    elif (directory/'archive-repair.json').exists():
        repair=read_json(directory/'archive-repair.json')
        if repair['artifact']!='schedule_eval.cubin' or file_hash(directory/repair['artifact'])!=repair['sha256']:raise ValueError('discovery archive repair differs')
    else:raise ValueError('missing discovery archive identity')
    snapshot=(directory/'ledger.jsonl').read_bytes()
    ledger=ledger_for(value)
    with (ledger.directory/'campaign.lock').open('rb') as lock:
        fcntl.flock(lock,fcntl.LOCK_SH|fcntl.LOCK_NB)
        active=ledger.path.read_bytes()
        if not snapshot.endswith(b'\n') or not active.startswith(snapshot):raise ValueError('historical snapshot is not an intact prefix')
        # _load is non-mutating for an explicitly checked complete ledger.
        if not active.endswith(b'\n'):raise ValueError('live ledger requires recovery')
        ledger._load();ledger.events=ledger.events[:len(snapshot.splitlines())]
        if ledger.pending():raise ValueError('unsettled historical reservations')
    if ledger.usage('study')>value['study_cap_seconds']*NS or ledger.usage('accept')>value['acceptance_cap_seconds']*NS or ledger.totals()>value['cumulative_gpu_ns']:
        raise ValueError('adaptive budget exceeded')
    for phase,cap in value['phase_gpu_seconds'].items():
        if ledger.totals(phase=phase)>cap*NS:raise ValueError('phase cap exceeded')
    trials=[];endpoints={};seen=set();raw=[]
    for path in sorted(directory.glob('*.trial.json')):
        t=validate('trial',read_json(path));identity=t['id']
        if identity in seen or identity not in planned:raise ValueError('duplicate or unplanned trial')
        seen.add(identity);_,instance,configuration,repeat,order,mode=planned[identity]
        expected=dict(campaign_sha256=campaign_hash,instance_id=instance['id'],model_sha256=instance['model']['sha256'],config_id=configuration['id'],requested_backend=configuration['backend'],repetition=repeat,order=order,mode=mode,block=f'{identity.split("-study-",1)[1].split("-",1)[0]}:{instance["id"]}:{repeat}',limits=value['limits'])
        expected['config_sha256']=digest(encoded(dict(configuration=configuration,solve=value['solve'],lp_settings=value['lp_settings'] if configuration['backend']!='highs' else None)))
        if any(t[k]!=v for k,v in expected.items()):raise ValueError('trial differs from frozen schedule: '+identity)
        expected_identity=identities[configuration['id']]
        for key,expected_value in expected_identity.items():
            if key not in ('telemetry_before','telemetry_after') and t['provenance'][key]!=expected_value:raise ValueError('trial provenance differs')
        for key in ('source_tree_sha256','binary_sha256','highs_library_sha256','device','cpu_affinity','build_profile'):
            if expected_identity[key]!=execution[key]:raise ValueError('configuration execution differs')
        image='lp_pdhg_precision.cubin' if 'adaptive' in configuration or 'precision' in configuration else 'lp_pdhg_tuned.cubin' if configuration['backend']=='cuda-lp-tuned' else 'lp_pdhg.cubin'
        expected_code=file_hash(directory/image) if configuration['backend'].startswith('cuda-') else None
        if expected_identity['code_object_sha256']!=expected_code:raise ValueError('configuration code object differs')
        if t['provenance']['schema_snapshot_sha256']!=execution['schema_snapshot_sha256']:raise ValueError('trial schema snapshot differs')
        for role in ['worker','stdout','stderr','endpoint','activity']:
            if t[role] is not None:checked_reference(directory,t[role])
        if t['endpoint'] is not None and t['status']!='invalid_evidence':
            endpoint_path=checked_reference(directory,t['endpoint']);e=validate('endpoint',read_json(endpoint_path))
            model=checked_reference(ROOT,instance['model'])
            if e['model_sha256']!=t['model_sha256'] or e['requested_backend']!=configuration['backend'] or e['record']['options']!=value['solve']:raise ValueError('endpoint request differs')
            if e['record']['backend']!='highs' and e['record'].get('lp_settings')!=value['lp_settings']:raise ValueError('endpoint method differs')
            for field in ['adaptive','precision']:
                if field in configuration and e.get(field,{}).get('settings')!=configuration[field]:raise ValueError('endpoint '+field+' differs')
            if configuration['backend']=='cuda-lp-tuned' and (e['execution']['settings']!=configuration['execution'] or e['execution']['code_object_sha256']!=expected_code):raise ValueError('endpoint code identity differs')
            checked=subprocess.run([str(binary),'lp-study','verify','--model',str(model),'--evidence',str(endpoint_path)],capture_output=True,text=True,timeout=20)
            if checked.returncode:raise ValueError('independent endpoint refusal: '+identity+': '+checked.stderr[:1000])
            if t['executed_backend']!=e['record']['backend'] or t['endpoint_class']!=e['assessment']['classification']:raise ValueError('trial classification differs')
            endpoints[identity]=e
        elif successful(t):raise ValueError('success without verified evidence')
        raw.append(dict(path=path.name,sha256=file_hash(path)));trials.append(t)
    admitted={e['trial_id'] for e in ledger.events if e['kind']=='reserve' and e['trial_id'].startswith(value['id']+'-study-')}
    if seen!=admitted:raise ValueError('ledger/trial attempt coverage differs')
    groups=defaultdict(list)
    for t in trials:
        block=t['id'].split('-study-',1)[1].split('-',1)[0]
        groups[(block,t['instance_id'],t['config_id'])].append(t)
    rows=[];ratios=[];profiles=[]
    for block in value['blocks']:
        for instance in block['instances']:
            for cid in block['configurations']:
                observed=groups[(block['id'],instance,cid)];accepted=[t for t in observed if successful(t)]
                rows.append(dict(block=block['id'],instance=instance,configuration=cid,planned=block['repetitions'],attempted=len(observed),certified=len(accepted),certified_median_ns=statistics.median(t['elapsed_ns'] for t in accepted) if accepted else None,outcomes=dict(Counter(t['status']+'/'+str(t['endpoint_class'])+('/fallback' if t['executed_backend'] and t['executed_backend']!=t['requested_backend'] else '') for t in observed))))
                if block['mode']=='timing':
                    left={t['repetition']:t for t in groups[(block['id'],instance,'tuned-fp64')]}
                    pairs=[(left[t['repetition']]['elapsed_ns'],t['elapsed_ns']) for t in accepted if t['repetition'] in left and successful(left[t['repetition']])]
                    ratios.append(dict(block=block['id'],instance=instance,configuration=cid,reference='tuned-fp64',statistics=paired_ratio(pairs,value['analysis']['seed'],value['analysis']['resamples'])))
    work=[]
    for t in trials:
        if t['id'] not in endpoints:continue
        e=endpoints[t['id']]
        item=dict(trial=t['id'],instance=t['instance_id'],configuration=t['config_id'],mode=t['mode'],assessment=e['assessment'],control=e.get('control'),adaptive=e.get('adaptive'),execution=e.get('execution'),phases_ns=e['diagnostics']['phases_ns'],device_buffer_peak_bytes=e['diagnostics']['device_buffer_peak_bytes'])
        work.append(item)
        if t['mode']=='profile':profiles.append(item)
    result=dict(schema_version=1,status='complete' if len(trials)==len(planned) else 'interim',planned=len(planned),attempted=len(trials),verified_endpoints=len(endpoints),missing_trials=sorted(set(planned)-seen),outcomes=dict(Counter(t['status']+'/'+str(t['endpoint_class']) for t in trials)),coverage=rows,paired_ratios=ratios,work=work,profiles=profiles,raw_trials=raw,campaign_sha256=campaign_hash,source_tree_sha256=execution['source_tree_sha256'],binary_sha256=execution['binary_sha256'],source_archive_sha256=execution['source_archive_sha256'],ledger_sha256=hashlib.sha256(snapshot).hexdigest(),ledger_events=len(ledger.events),cumulative_gpu_ns=ledger.totals(),study_gpu_ns=ledger.usage('study'),acceptance_gpu_ns=ledger.usage('accept'),phase_gpu_ns={p:ledger.totals(phase=p) for p in value['phase_gpu_seconds']})
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',type=Path,default=ROOT/'artifacts/gpup6-adaptive-v1');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('refusing existing report')
    result=report(a.directory,a.directory/'optimizer');write_json(a.output,result)
    print({k:result[k] for k in ['status','planned','attempted','verified_endpoints','cumulative_gpu_ns','study_gpu_ns','acceptance_gpu_ns','ledger_sha256']})
if __name__=='__main__':main()
