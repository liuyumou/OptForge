"""Frozen ADR-0023 (v3) repeated-solve throughput study (SPEC-0014).

A version-3 protocol declares explicit tolerance tiers, the merged development
plus extension manifests, per-instance solve limits, a variant seed band and
ordered blocks of (kind, instances, configurations, tiers, repetitions) with
batch sizes or fresh-variant indices. Block kinds: fresh and fresh-short are
ordinary fresh-process single solves (the primary endpoint, unchanged);
batch-repeat and batch-repeat-short solve one identical repeat batch per
attempt; batch-variant and batch-variant-short solve one bound-variant batch
per attempt from the tools/lp_variants.py family. A fresh-variant attempt
solves one materialized family variant fresh: it emits a solves=1 variant
batch request and runs the same batch command with N=1, so the Rust
materializer remains the only model serializer and the attempt's single solve
is the fresh materialized solve of the family's variant_index.

All work shares the GPUP supervisor, lease, ledger and verification path and
runs under identity gpup-throughput-v1 (prefix gpupt) inside the raised
cumulative ceiling the protocol itself authorizes (requirement 29).
"""
import argparse
import shutil
import subprocess
from collections import Counter
from functools import lru_cache
from pathlib import Path
from benchmark_lp import prepare_execution, provenance, quiet_device, source_identity, telemetry
from lp_protocol import ROOT, NS, checked_reference, file_hash, local, ordered, read_json, validate, write_json
from lp_research_budget import Study, category_usage, ledger_for, run
import lp_variants
CONFIG=ROOT/'benchmarks/configs/lp-throughput-v1.json'
V3_KEYS={'schema_version','id','prefix','output','acceptance_output','source_campaign','decision','additional_gpu_seconds','extension_manifest','tiers','configurations','blocks','short_proposals','planned_attempts','prior_gpu_ns','prior_events','prior_ledger_sha256','study_cap_seconds','acceptance_cap_seconds','combined_cap_seconds','cumulative_ceiling_ns','development_limit_seconds','variant_seed_base','variant_changes'}
FRESH_KINDS=('fresh','fresh-short')
BATCH_KINDS=('batch-repeat','batch-variant','batch-repeat-short','batch-variant-short','fresh-variant')
REPEAT_KINDS=('batch-repeat','batch-repeat-short')
VARIANT_KINDS=('batch-variant','batch-variant-short','fresh-variant')
KINDS=FRESH_KINDS+('fresh-variant',)+BATCH_KINDS[:4]


def protocol(path=CONFIG):
    value=read_json(path)
    if value.get('schema_version')!=3 or set(value)!=V3_KEYS:raise ValueError('throughput protocol schema')
    for tier,t in value['tiers'].items():
        if set(t)!={'absolute','relative','integrality'} or any(not 0<t[k]<=1e-1 for k in t):raise ValueError('throughput tier tolerances')
    ids=[c['id'] for c in value['configurations']]
    if len(set(ids))!=len(ids):raise ValueError('duplicate throughput configuration')
    for c in value['configurations']:
        if ('mode' in c)==('backend' in c):raise ValueError('throughput configuration shape')
    for block in value['blocks']:
        kind=block.get('kind')
        if kind not in KINDS:raise ValueError('throughput block kind')
        expected={'kind','instances','configurations','tiers','repetitions'}|({'sizes'} if kind in BATCH_KINDS[:4] else set())|({'variants'} if kind=='fresh-variant' else set())
        if set(block)!=expected:raise ValueError('throughput block schema')
        if type(block['instances']) is not list or not block['instances'] or any(type(i) is not str for i in block['instances']):raise ValueError('throughput block instances')
        if type(block['repetitions']) is not int or block['repetitions']<1:raise ValueError('throughput block repetitions')
        if any(c not in ids for c in block['configurations']) or any(t not in value['tiers'] for t in block['tiers']):raise ValueError('throughput block references')
        if any(type(s) is not int or s<1 for s in block.get('sizes',[])):raise ValueError('throughput batch sizes')
        if any(type(v) is not int or v<0 for v in block.get('variants',[])):raise ValueError('throughput fresh variants')
    if not local(ROOT,value['decision']['path']).is_file():raise ValueError('throughput decision record missing')
    base=read_json(checked_reference(ROOT,value['source_campaign']))
    manifest=read_json(ROOT/'benchmarks/manifests/lp-development-v1.json')
    extension=validate('manifest',read_json(checked_reference(ROOT,value['extension_manifest'])))
    if extension['partition']!='development' or extension['extends']['sha256']!=file_hash(ROOT/'benchmarks/manifests/lp-development-v1.json'):raise ValueError('extension manifest must extend the frozen development manifest')
    if {i['group'] for i in extension['instances']}&{i['group'] for i in manifest['instances']}:raise ValueError('extension groups collide with development groups')
    manifest=dict(manifest,instances=manifest['instances']+extension['instances'])
    known={i['id']:i for i in manifest['instances']}
    for block in value['blocks']:
        if any(i not in known for i in block['instances']):raise ValueError('throughput block names an unknown instance')
        if block['kind'] in VARIANT_KINDS and any(known[i]['witness'] is None for i in block['instances']):raise ValueError('a variant batch requires a frozen witness')
    return value,base,manifest


def jobs(value,base,manifest):
    by_id={c['id']:c for c in value['configurations']}
    index={i['id']:p for p,i in enumerate(manifest['instances'])}
    for number,block in enumerate(value['blocks']):
        sizes=block['sizes'] if 'sizes' in block else [None]
        fresh_variants=block['variants'] if 'variants' in block else [None]
        cells=[dict(id=c+'@'+t+('' if s is None else '@n'+str(s))+('' if v is None else '@v'+str(v)),config=c,tier=t,size=s,variant=v)
               for c in block['configurations'] for t in block['tiers'] for s in sizes for v in fresh_variants]
        for instance in manifest['instances']:
            if instance['id'] not in block['instances']:continue
            for repeat in range(block['repetitions']):
                for cell in ordered(cells,base['order_seed'],instance['id'],repeat):
                    yield dict(kind=block['kind'],block=number,instance=instance,config=by_id[cell['config']],tier=cell['tier'],
                               size=cell['size'],variant=cell['variant'],repeat=repeat,variant_seed=value['variant_seed_base']+index[instance['id']])


def label(job):
    key=f'{job["kind"]}-{job["instance"]["id"]}-{job["repeat"]}-{job["config"]["id"]}-{job["tier"]}'
    if job['size'] is not None:key+=f'-n{job["size"]}'
    if job['variant'] is not None:key+=f'-v{job["variant"]}'
    return key


def settings_for(job,base,value):
    """Options, method, supervisor limit and batch limit for one job; shared with the analysis."""
    method=dict(base['lp_settings']);options=dict(base['solve'])
    if job['kind'].endswith('-short'):method['iteration_limit']=value.get('short_proposals',200);options['iteration_limit']=method['iteration_limit']
    options['tolerances']=dict(value['tiers'][job['tier']])
    seconds=job['instance'].get('time_limit_seconds',value['development_limit_seconds'])
    options['time_limit_ms']=seconds*1000
    if job['size'] is None:return options,method,seconds,seconds*1000
    limit=(40+2*job['size']) if job['instance']['id'].startswith('gpup-extension-') else 20+job['size']
    return options,method,limit+2,limit*1000


@lru_cache(maxsize=None)
def family_for(instance_id,seed,changes,count):
    """One instance's variant family, generated once per (seed, changes, count)."""
    entry=lp_variants.instance_entry(instance_id)
    model=read_json(checked_reference(ROOT,entry['model']))
    witness=read_json(checked_reference(ROOT,entry['witness']))
    return lp_variants.variants(model,witness,seed,count,changes)


def batch_request_for(job,value,batch_time_limit_ms):
    """The lp-batch-request-v1 document for one batch-mode job."""
    instance=job['instance']
    if job['kind'] in REPEAT_KINDS:
        return lp_variants.request(instance['id'],'repeat',job['size'],[],None,None,batch_time_limit_ms)
    family=family_for(instance['id'],job['variant_seed'],value['variant_changes'],32 if job['kind']=='fresh-variant' else job['size'])
    if job['kind']=='fresh-variant':
        selected=[dict(index=0,changes=family[job['variant']]['changes'])]
        return lp_variants.request(instance['id'],'variant',1,selected,job['variant_seed'],value['variant_changes'],batch_time_limit_ms)
    return lp_variants.request(instance['id'],'variant',job['size'],family[:job['size']],job['variant_seed'],value['variant_changes'],batch_time_limit_ms)


def request_for(job,base,value,identity,model_sha256,research_sha256,code_object_sha256):
    options,method,_,_=settings_for(job,base,value)
    return dict(schema_version=1 if value['schema_version']==1 else 2,mode=job['config']['mode'],model_sha256=model_sha256,source_tree_sha256=identity,
                executable_sha256=research_sha256,code_object_sha256=code_object_sha256,device=base['device'],options=options,method=method,
                profile=False,device_buffer_bytes=base['limits']['device_buffer_bytes'])


def research_batch_request_for(job,base,value,identity,model_sha256,research_sha256,code_object_sha256):
    """The research batch request, version 1: research-v2 identity fields plus the batch document."""
    options,method,_,batch_ms=settings_for(job,base,value)
    return dict(schema_version=1,mode=job['config']['mode'],model_sha256=model_sha256,source_tree_sha256=identity,
                executable_sha256=research_sha256,code_object_sha256=code_object_sha256,device=base['device'],options=options,method=method,
                profile=False,device_buffer_bytes=base['limits']['device_buffer_bytes'],batch=batch_request_for(job,value,batch_ms))


def command(job,base,binary,research,identity,directory,value):
    key=label(job);c=job['config']
    options,method,seconds,batch_ms=settings_for(job,base,value)
    model=checked_reference(ROOT,job['instance']['model'])
    batch=job['kind'] in BATCH_KINDS
    evidence=directory/(key+'.batch') if batch else directory/(key+'.endpoint.json')
    cubin=file_hash(ROOT/'target/native/cuda/lp_pdhg_research.cubin')
    if 'mode' in c:
        if batch:
            request=research_batch_request_for(job,base,value,identity['source_tree_sha256'],file_hash(model),file_hash(research),cubin)
            request_path=directory/(key+'.research.json');write_json(request_path,request)
            cmd=[str(research),'batch',str(model),str(request_path),str(evidence)]
            verify=[str(research),'verify-batch',str(model),str(request_path),str(evidence)]
        else:
            request=request_for(job,base,value,identity['source_tree_sha256'],file_hash(model),file_hash(research),cubin)
            request_path=directory/(key+'.research.json');write_json(request_path,request)
            cmd=[str(research),'solve',str(model),str(request_path),str(evidence)]
            verify=[str(research),'verify',str(model),str(request_path),str(evidence)]
    else:
        paths={}
        for suffix,data in [('options',options),('method',method),('execution',c['execution'])]:
            path=directory/(key+'.'+suffix+'.json');write_json(path,data);paths[suffix]=str(path)
        if batch:
            batch_path=directory/(key+'.batch.json');write_json(batch_path,batch_request_for(job,value,batch_ms))
            cmd=[str(binary),'solve-batch','--model',str(model),'--batch',str(batch_path),'--config',paths['options'],
                 '--lp-settings',paths['method'],'--lp-execution',paths['execution'],'--device',base['device'],
                 '--lp-evidence',str(evidence),'--lp-profile','false','--lp-device-memory-bytes',str(base['limits']['device_buffer_bytes'])]
            verify=[str(binary),'lp-study','verify-batch','--model',str(model),'--batch',str(batch_path),'--evidence',str(evidence)]
        else:
            cmd=[str(binary),'solve','--backend','cuda-lp-tuned','--device',base['device'],'--model',str(model),'--config',paths['options'],
                 '--lp-settings',paths['method'],'--lp-execution',paths['execution'],'--lp-evidence',str(evidence),'--lp-profile','false',
                 '--lp-device-memory-bytes',str(base['limits']['device_buffer_bytes'])]
            verify=[str(binary),'lp-study','verify','--model',str(model),'--evidence',str(evidence)]
    return cmd,verify,evidence/'batch.json' if batch else evidence,seconds


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dry-run',action='store_true');p.add_argument('--protocol',type=Path,default=CONFIG);a=p.parse_args()
    value,base,manifest=protocol(a.protocol);schedule=list(jobs(value,base,manifest));study=Study.from_protocol(value)
    if len(schedule)!=value['planned_attempts']:raise ValueError('frozen attempt count differs')
    if a.dry_run:
        print(len(schedule),'planned attempts')
        for kind,count in sorted(Counter(j['kind'] for j in schedule).items()):print(kind,count)
        return
    binary=ROOT/'target/release/optimizer';research=ROOT/'target/release/examples/lp_precision_research'
    native=provenance(binary,base['device']);receipt=read_json(ROOT/'target/lp-native-gate.json')
    if not receipt.get('native') or receipt['source_tree_sha256']!=source_identity():raise ValueError('full native gate required on exact source')
    for name,key in [('lp_pdhg_tuned.cubin','code_object_sha256'),('lp_pdhg_precision.cubin','precision_code_object_sha256')]:
        if file_hash(ROOT/'target/native/cuda'/name)!=base[key]:raise ValueError('preserved code object changed: '+name)
    frozen=dict(protocol=value,protocol_sha256=file_hash(a.protocol),source=native,research_binary_sha256=file_hash(research),code_object_sha256=file_hash(ROOT/'target/native/cuda/lp_pdhg_research.cubin'),jobs=schedule)
    output=study.output
    with ledger_for(study,protocol=value) as ledger:
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
                    checked=subprocess.run(verify,capture_output=True,text=True,timeout=120 if job['size'] is None else 120+60*job['size'])
                    verification=dict(returncode=checked.returncode,stdout=checked.stdout,stderr=checked.stderr)
                    verified=checked.returncode==0
                result.update(job=job,endpoint_sha256=file_hash(endpoint) if endpoint.exists() else None,verified=verified,verification=verification,telemetry_after=telemetry(base['device']))
                write_json(output/(key+'.result.json'),result)
                print(key,result['worker']['reason'] if result['worker'] else 'missing worker','verified',verified,flush=True)
        finally:shutil.copyfile(ledger.path,output/'ledger.jsonl')
        print('study seconds',category_usage(ledger,'study',study.prefix)/NS,'acceptance',category_usage(ledger,'accept',study.prefix)/NS,'cumulative',ledger.totals()/NS)
if __name__=='__main__':main()
