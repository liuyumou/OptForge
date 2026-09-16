"""Frozen ADR-0021 development-only scaling and component study."""
import argparse
import os
import shutil
import subprocess
from pathlib import Path
from benchmark_lp import prepare_execution, provenance, quiet_device, source_identity, telemetry
from lp_protocol import ROOT, NS, checked_reference, file_hash, ordered, read_json, write_json
from lp_research_budget import OUTPUT, PRIOR_NS, category_usage, ledger_for, run
CONFIG=ROOT/'benchmarks/configs/lp-research-v1.json'
NSYS=Path('/opt/nvidia/nsight-compute/2025.3.0/host/target-linux-x64/nsys')


def protocol():
    value=read_json(CONFIG)
    if set(value)!={'schema_version','id','source_campaign','configurations','profiles','traces','timing_repetitions','profile_repetitions','short_repetitions','short_proposals','planned_attempts','prior_gpu_ns','study_cap_seconds','acceptance_cap_seconds','cumulative_ceiling_ns'} or value['schema_version']!=1:raise ValueError('research protocol schema')
    base=read_json(checked_reference(ROOT,value['source_campaign']))
    manifest=read_json(ROOT/'benchmarks/manifests/lp-development-v1.json')
    return value,base,manifest


def jobs(value,base,manifest):
    for kind,repetitions in [('timing',3),('profile',1),('short',7),('trace',1)]:
        for instance in manifest['instances']:
            if kind in ['profile','short'] and instance['id'] not in value['profiles']:continue
            if kind=='trace' and instance['id'] not in value['traces']:continue
            for repeat in range(repetitions):
                for config in ordered(value['configurations'],base['order_seed'],instance['id'],repeat):
                    yield dict(kind=kind,instance=instance,config=config,repetition=repeat)


def label(job):return f'{job["kind"]}-{job["instance"]["id"]}-{job["repetition"]}-{job["config"]["id"]}'


def command(job,base,binary,research,identity,directory):
    key=label(job);c=job['config'];short=job['kind'] in ['short','trace'];profile=job['kind']!='timing'
    method=dict(base['lp_settings']);options=dict(base['solve'])
    if short: method['iteration_limit']=200;options['iteration_limit']=200
    model=checked_reference(ROOT,job['instance']['model']);endpoint=directory/(key+'.endpoint.json')
    if 'mode' in c:
        request=dict(schema_version=1,mode=c['mode'],model_sha256=file_hash(model),source_tree_sha256=identity['source_tree_sha256'],
                     executable_sha256=file_hash(research),code_object_sha256=file_hash(ROOT/'target/native/cuda/lp_pdhg_research.cubin'),
                     device=base['device'],options=options,method=method,profile=profile,device_buffer_bytes=base['limits']['device_buffer_bytes'])
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
    return cmd,verify,endpoint


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dry-run',action='store_true');a=p.parse_args()
    value,base,manifest=protocol();schedule=list(jobs(value,base,manifest))
    if len(schedule)!=840:raise ValueError('frozen attempt count differs')
    if a.dry_run:print(len(schedule),'planned attempts');return
    binary=ROOT/'target/release/optimizer';research=ROOT/'target/release/examples/lp_precision_research'
    native=provenance(binary,base['device']);receipt=read_json(ROOT/'target/lp-native-gate.json')
    if not receipt.get('native') or receipt['source_tree_sha256']!=source_identity():raise ValueError('full native gate required on exact source')
    for name,key in [('lp_pdhg_tuned.cubin','code_object_sha256'),('lp_pdhg_precision.cubin','precision_code_object_sha256')]:
        if file_hash(ROOT/'target/native/cuda'/name)!=base[key]:raise ValueError('preserved code object changed: '+name)
    frozen=dict(protocol=value,protocol_sha256=file_hash(CONFIG),source=native,research_binary_sha256=file_hash(research),code_object_sha256=file_hash(ROOT/'target/native/cuda/lp_pdhg_research.cubin'),jobs=schedule,nsys_sha256=file_hash(NSYS))
    with ledger_for() as ledger:
        prepare_execution(OUTPUT,native)
        path=OUTPUT/'protocol.json'
        if path.exists() and read_json(path)!=frozen:raise ValueError('frozen protocol differs')
        write_json(path,frozen)
        for src in [binary,research,ROOT/'target/native/cuda/lp_pdhg_research.cubin',ROOT/'target/native/cuda/lp_pdhg_tuned.cubin',ROOT/'target/native/cuda/lp_pdhg_precision.cubin']:
            dst=OUTPUT/src.name
            if dst.exists() and file_hash(dst)!=file_hash(src):raise ValueError('archived executable differs')
            if not dst.exists():shutil.copy2(src,dst)
        try:
            for job in schedule:
                key=label(job)
                if 'gpup5b-study-'+key in ledger.attempted():continue
                activity=quiet_device(base['device']);before=telemetry(base['device'])
                cmd,verify,endpoint=command(job,base,binary,research,native,OUTPUT)
                write_json(OUTPUT/(key+'.intent.json'),dict(job=job,command=cmd,verify=verify,activity=activity,telemetry_before=before))
                try: result=run(ledger,'study',key,cmd,10)
                except ValueError as e:
                    if 'budget exhausted' not in str(e):raise
                    print(str(e),flush=True);break
                verified=False;verification=None
                if endpoint.exists():
                    checked=subprocess.run(verify,capture_output=True,text=True,timeout=60)
                    verification=dict(returncode=checked.returncode,stdout=checked.stdout,stderr=checked.stderr)
                    verified=checked.returncode==0
                result.update(job=job,endpoint_sha256=file_hash(endpoint) if endpoint.exists() else None,verified=verified,verification=verification,telemetry_after=telemetry(base['device']))
                write_json(OUTPUT/(key+'.result.json'),result)
                print(key,result['worker']['reason'] if result['worker'] else 'missing worker','verified',verified,flush=True)
        finally:shutil.copyfile(ledger.path,OUTPUT/'ledger.jsonl')
        print('study seconds',category_usage(ledger,'study')/NS,'acceptance',category_usage(ledger,'accept')/NS,'cumulative',ledger.totals()/NS)
if __name__=='__main__':main()
