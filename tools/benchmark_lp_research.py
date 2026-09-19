"""Frozen ADR-0021 (v1) and ADR-0022 (v2) development-only research studies.

A version-1 protocol is the GPUP-5B twelve-configuration, 840-attempt schedule and
stays byte-identical. A version-2 protocol declares explicit tolerance tiers, a
development extension manifest, per-instance solve limits and ordered blocks of
(kind, instances, configurations, tiers, repetitions); its research requests use
research-v2 evidence. Both share the supervisor, lease, ledger and verification path.
"""
import argparse
import os
import shutil
import subprocess
from pathlib import Path
from benchmark_lp import prepare_execution, provenance, quiet_device, source_identity, telemetry
from lp_protocol import ROOT, NS, checked_reference, file_hash, ordered, read_json, validate, write_json
from lp_research_budget import OUTPUT, PRIOR_NS, Study, category_usage, ledger_for, run
CONFIG=ROOT/'benchmarks/configs/lp-research-v1.json'
NSYS=Path('/opt/nvidia/nsight-compute/2025.3.0/host/target-linux-x64/nsys')
V1_KEYS={'schema_version','id','source_campaign','configurations','profiles','traces','timing_repetitions','profile_repetitions','short_repetitions','short_proposals','planned_attempts','prior_gpu_ns','study_cap_seconds','acceptance_cap_seconds','cumulative_ceiling_ns'}
V2_KEYS={'schema_version','id','prefix','output','acceptance_output','source_campaign','extension_manifest','tiers','configurations','blocks','short_proposals','planned_attempts','prior_gpu_ns','prior_events','prior_ledger_sha256','study_cap_seconds','acceptance_cap_seconds','combined_cap_seconds','cumulative_ceiling_ns','development_limit_seconds'}


def protocol(path=CONFIG):
    value=read_json(path)
    version=value.get('schema_version')
    if version==1:
        if set(value)!=V1_KEYS:raise ValueError('research protocol schema')
    elif version==2:
        if set(value)!=V2_KEYS:raise ValueError('research protocol v2 schema')
        for tier,t in value['tiers'].items():
            if set(t)!={'absolute','relative','integrality'} or any(not 0<t[k]<=1e-1 for k in t):raise ValueError('research tier tolerances')
        ids=[c['id'] for c in value['configurations']]
        if len(set(ids))!=len(ids):raise ValueError('duplicate research configuration')
        for block in value['blocks']:
            if set(block)!={'kind','instances','configurations','tiers','repetitions'} or block['kind'] not in ('timing','profile','short','trace'):raise ValueError('research block schema')
            if any(c not in ids for c in block['configurations']) or any(t not in value['tiers'] for t in block['tiers']):raise ValueError('research block references')
    else:raise ValueError('research protocol schema')
    base=read_json(checked_reference(ROOT,value['source_campaign']))
    manifest=read_json(ROOT/'benchmarks/manifests/lp-development-v1.json')
    if version==2:
        extension=validate('manifest',read_json(checked_reference(ROOT,value['extension_manifest'])))
        if extension['partition']!='development' or extension['extends']['sha256']!=file_hash(ROOT/'benchmarks/manifests/lp-development-v1.json'):raise ValueError('extension manifest must extend the frozen development manifest')
        if {i['group'] for i in extension['instances']}&{i['group'] for i in manifest['instances']}:raise ValueError('extension groups collide with development groups')
        manifest=dict(manifest,instances=manifest['instances']+extension['instances'])
    return value,base,manifest


def jobs(value,base,manifest):
    if value['schema_version']==1:
        for kind,repetitions in [('timing',3),('profile',1),('short',7),('trace',1)]:
            for instance in manifest['instances']:
                if kind in ['profile','short'] and instance['id'] not in value['profiles']:continue
                if kind=='trace' and instance['id'] not in value['traces']:continue
                for repeat in range(repetitions):
                    for config in ordered(value['configurations'],base['order_seed'],instance['id'],repeat):
                        yield dict(kind=kind,instance=instance,config=config,repetition=repeat)
        return
    by_id={c['id']:c for c in value['configurations']}
    development=[i['id'] for i in manifest['instances'] if not i['id'].startswith('gpup-extension-')]
    for block in value['blocks']:
        selected=development if block['instances']=='development' else block['instances']
        cells=[dict(id=c+'@'+t,config=c,tier=t) for c in block['configurations'] for t in block['tiers']]
        for instance in manifest['instances']:
            if instance['id'] not in selected:continue
            for repeat in range(block['repetitions']):
                for cell in ordered(cells,base['order_seed'],instance['id'],repeat):
                    yield dict(kind=block['kind'],instance=instance,config=by_id[cell['config']],repetition=repeat,tier=cell['tier'])


def label(job):
    key=f'{job["kind"]}-{job["instance"]["id"]}-{job["repetition"]}-{job["config"]["id"]}'
    return key+'-'+job['tier'] if 'tier' in job else key


def settings_for(job,base,value):
    """Options, method and supervisor limit for one job; shared with the analysis."""
    method=dict(base['lp_settings']);options=dict(base['solve'])
    if job['kind'] in ['short','trace']:method['iteration_limit']=value.get('short_proposals',200);options['iteration_limit']=method['iteration_limit']
    seconds=10
    if 'tier' in job:
        options['tolerances']=dict(value['tiers'][job['tier']])
        seconds=job['instance'].get('time_limit_seconds',value['development_limit_seconds'])
        options['time_limit_ms']=seconds*1000
    return options,method,seconds


def request_for(job,base,value,identity,model_sha256,research_sha256,code_object_sha256):
    options,method,_=settings_for(job,base,value)
    return dict(schema_version=1 if value['schema_version']==1 else 2,mode=job['config']['mode'],model_sha256=model_sha256,source_tree_sha256=identity,
                executable_sha256=research_sha256,code_object_sha256=code_object_sha256,device=base['device'],options=options,method=method,
                profile=job['kind']!='timing',device_buffer_bytes=base['limits']['device_buffer_bytes'])


def command(job,base,binary,research,identity,directory,value=None):
    value=value or dict(schema_version=1)
    key=label(job);c=job['config'];profile=job['kind']!='timing'
    options,method,seconds=settings_for(job,base,value)
    model=checked_reference(ROOT,job['instance']['model']);endpoint=directory/(key+'.endpoint.json')
    if 'mode' in c:
        request=request_for(job,base,value,identity['source_tree_sha256'],file_hash(model),file_hash(research),file_hash(ROOT/'target/native/cuda/lp_pdhg_research.cubin'))
        request_path=directory/(key+'.research.json');write_json(request_path,request)
        cmd=[str(research),'solve',str(model),str(request_path),str(endpoint)]
        verify=[str(research),'verify',str(model),str(request_path),str(endpoint)]
    else:
        paths={}
        for suffix,data in [('options',options),('method',method),('execution',c['execution'])]:
            path=directory/(key+'.'+suffix+'.json');write_json(path,data);paths[suffix]=str(path)
        cmd=[str(binary),'solve','--backend','cuda-lp-tuned','--device',base['device'],'--model',str(model),'--config',paths['options'],
             '--lp-settings',paths['method'],'--lp-execution',paths['execution'],'--lp-evidence',str(endpoint),'--lp-profile',str(profile).lower(),
             '--lp-device-memory-bytes',str(base['limits']['device_buffer_bytes'])]
        if 'precision' in c:
            path=directory/(key+'.precision.json');write_json(path,c['precision']);cmd+=['--lp-precision',str(path)]
        verify=[str(binary),'lp-study','verify','--model',str(model),'--evidence',str(endpoint)]
    if job['kind']=='trace':cmd=[str(NSYS),'profile','--trace=cuda','--sample=none','--cpuctxsw=none','--cuda-event-trace=false','--stats=false','--force-overwrite=false','--export=sqlite','--output='+str(directory/key)]+cmd
    return cmd,verify,endpoint,seconds


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dry-run',action='store_true');p.add_argument('--protocol',type=Path,default=CONFIG);a=p.parse_args()
    value,base,manifest=protocol(a.protocol);schedule=list(jobs(value,base,manifest));study=Study.from_protocol(value)
    if len(schedule)!=value['planned_attempts']:raise ValueError('frozen attempt count differs')
    if a.dry_run:print(len(schedule),'planned attempts');return
    binary=ROOT/'target/release/optimizer';research=ROOT/'target/release/examples/lp_precision_research'
    native=provenance(binary,base['device']);receipt=read_json(ROOT/'target/lp-native-gate.json')
    if not receipt.get('native') or receipt['source_tree_sha256']!=source_identity():raise ValueError('full native gate required on exact source')
    for name,key in [('lp_pdhg_tuned.cubin','code_object_sha256'),('lp_pdhg_precision.cubin','precision_code_object_sha256')]:
        if file_hash(ROOT/'target/native/cuda'/name)!=base[key]:raise ValueError('preserved code object changed: '+name)
    frozen=dict(protocol=value,protocol_sha256=file_hash(a.protocol),source=native,research_binary_sha256=file_hash(research),code_object_sha256=file_hash(ROOT/'target/native/cuda/lp_pdhg_research.cubin'),jobs=schedule,nsys_sha256=file_hash(NSYS))
    output=study.output
    with ledger_for(study) as ledger:
        prepare_execution(output,native)
        path=output/'protocol.json'
        if path.exists() and read_json(path)!=frozen:raise ValueError('frozen protocol differs')
        write_json(path,frozen)
        for src in [binary,research,ROOT/'target/native/cuda/lp_pdhg_research.cubin',ROOT/'target/native/cuda/lp_pdhg_tuned.cubin',ROOT/'target/native/cuda/lp_pdhg_precision.cubin']:
            dst=output/src.name
            if dst.exists() and file_hash(dst)!=file_hash(src):raise ValueError('archived executable differs')
            if not dst.exists():shutil.copy2(src,dst)
        try:
            for job in schedule:
                key=label(job)
                if study.prefix+'-study-'+key in ledger.attempted():continue
                activity=quiet_device(base['device']);before=telemetry(base['device'])
                cmd,verify,endpoint,seconds=command(job,base,binary,research,native,output,value)
                write_json(output/(key+'.intent.json'),dict(job=job,command=cmd,verify=verify,activity=activity,telemetry_before=before))
                try: result=run(ledger,'study',key,cmd,seconds,output,study)
                except ValueError as e:
                    if 'budget exhausted' not in str(e):raise
                    print(str(e),flush=True);break
                verified=False;verification=None
                if endpoint.exists():
                    checked=subprocess.run(verify,capture_output=True,text=True,timeout=120)
                    verification=dict(returncode=checked.returncode,stdout=checked.stdout,stderr=checked.stderr)
                    verified=checked.returncode==0
                result.update(job=job,endpoint_sha256=file_hash(endpoint) if endpoint.exists() else None,verified=verified,verification=verification,telemetry_after=telemetry(base['device']))
                write_json(output/(key+'.result.json'),result)
                print(key,result['worker']['reason'] if result['worker'] else 'missing worker','verified',verified,flush=True)
        finally:shutil.copyfile(ledger.path,output/'ledger.jsonl')
        print('study seconds',category_usage(ledger,'study',study.prefix)/NS,'acceptance',category_usage(ledger,'accept',study.prefix)/NS,'cumulative',ledger.totals()/NS)
if __name__=='__main__':main()
