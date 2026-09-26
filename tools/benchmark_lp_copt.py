"""Frozen ADR-0026 comparison and cost diagnosis; no historical runner is changed."""
import argparse
import copy
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
from benchmark_lp import prepare_execution,provenance,quiet_device,telemetry,reference,recover_intents
from benchmark_lp_adaptive import code_images
from lp_copt_budget import CONFIG,protocol,ledger_for,receipt
from lp_protocol import ROOT,checked_reference,digest,encoded,file_hash,ordered,read_json,validate,write_json
from lp_cost import validate_profile
from validate_artifacts import validator,schema_snapshot

def jobs(value):
    manifests=[read_json(checked_reference(ROOT,m)) for m in value['manifests']]
    instances={i['id']:i for m in manifests for i in m['instances']};configs={c['id']:c for c in value['configurations']}
    all_names=list(instances);all_configs=list(configs)
    stages=[('timing',all_names,all_configs,[0]),('profile',value['profile_instances'],value['profile_configurations'],range(3)),
            ('short',value['short_instances'],value['short_configurations'],range(3)),
            ('profile',value['profile_instances'],[c for c in configs if c not in value['profile_configurations']],[0]),
            ('trace',value['trace_instances'],value['trace_configurations'],[0]),('timing',all_names,all_configs,[1,2])]
    for kind,names,modes,repeats in stages:
        category='profile' if kind in ('profile','short') else kind
        for repeat in repeats:
            for name in names:
                for order,c in enumerate(ordered([configs[c] for c in modes],value['order_seed'],name,repeat)):
                    key=f'{value["id"]}-{category}-{kind}-{name}-{repeat}-{c["id"]}'
                    yield dict(id=key,kind=kind,category=category,instance=instances[name],configuration=c,repetition=repeat,order=order)

def effective(value,job):
    seconds=job['instance'].get('time_limit_seconds',10)
    solve={**value['solve'],'time_limit_ms':seconds*1000};method=copy.deepcopy(value['lp_settings']);limits=dict(value['limits'],solve_seconds=seconds)
    if job['kind']=='short':solve['iteration_limit']=method['iteration_limit']=value['short_work']
    if job['kind']=='trace':limits.update(solve_seconds=seconds+value['trace_extra_seconds'],output_bytes=value['trace_output_bytes'])
    return solve,method,limits

def is_gpu(job):
    return job['configuration']['backend'].startswith('cuda-') or job['configuration']['backend']=='copt-gpu-pdlp'

def command(value,job,binary,directory):
    key=job['id'];c=job['configuration'];endpoint=directory/(key+'.endpoint.json');raw=directory/(key+'.raw-cost.json')
    solve,method,limits=effective(value,job)
    config=directory/(key+'.solve.json');settings=directory/(key+'.method.json')
    write_json(config,solve);write_json(settings,method)
    model=checked_reference(ROOT,job['instance']['model']);profile=job['kind']!='timing'
    if c['backend'].startswith('copt-'):
        args=[str(ROOT/value['copt_python']),'-B',str(ROOT/'tools/lp_copt_comparison.py'),'--model',str(model),'--config',str(config),
              '--output',str(endpoint),'--binary',str(binary),'--method',c['backend'],'--device',value['device'] if is_gpu(job) else 'cpu']
        if profile:args+=['--cost-profile',str(raw)]
        args=['/usr/bin/env','COPT_HOME='+value['copt_installation'],'COPT_LICENSE_DIR='+value['copt_installation'],
              'LD_LIBRARY_PATH=/usr/local/cuda/lib64'+(':'+os.environ['LD_LIBRARY_PATH'] if os.environ.get('LD_LIBRARY_PATH') else ''),
              *([] if is_gpu(job) else ['CUDA_VISIBLE_DEVICES=']),*args]
    else:
        args=[str(binary),'lp-study','solve','--model',str(model),'--model-byte-limit',str(value['model_byte_limit']),
              '--config',str(config),'--backend',c['backend'],'--lp-evidence',str(endpoint),'--lp-profile',str(profile).lower(),
              '--lp-device-memory-bytes',str(limits['device_buffer_bytes'])]
        if c['backend']!='highs':args+=['--lp-settings',str(settings)]
        for key_name,flag in [('execution','--lp-execution'),('precision','--lp-precision'),('adaptive','--lp-adaptive')]:
            if key_name in c:
                path=directory/(key+'.'+key_name+'.json');write_json(path,c[key_name]);args+=[flag,str(path)]
        if is_gpu(job):args+=['--device',value['device']]
        if profile:args+=['--cost-profile',str(raw)]
    args=['/usr/bin/env','AI_OPTIMIZER_CUDA_DIR='+str(directory),*args]
    if job['kind']=='trace':
        args=[value['nsys'],'profile','--trace=cuda,nvtx','--sample=none','--cpuctxsw=none','--cuda-event-trace=false','--stats=false',
              '--force-overwrite=false','--export=none','--output='+str(directory/key),*args]
    return args

def verify_endpoint(value,job,directory,binary,identity):
    path=directory/(job['id']+'.endpoint.json');endpoint=read_json(path);c=job['configuration'];solve,method,_=effective(value,job)
    external=c['backend'].startswith('copt-')
    if external:
        validator('lp-external-endpoint-v2.schema.json').validate(endpoint);record=endpoint['witness']
        if record['options']!=solve or record['library_sha256']!=identity['copt_library_sha256'] or record['binding_sha256']!=identity['copt_binding_sha256']:
            raise ValueError('external options/library identity differs')
        from lp_copt import gpu_started
        if record['gpu_confirmed']!=gpu_started(path.with_suffix('.copt.log').read_text()):raise ValueError('GPU execution log differs')
        backend=record['executed_backend'];verify='external-verify'
    else:
        validate('endpoint',endpoint);record=endpoint
        if endpoint['record']['options']!=solve:raise ValueError('solve options differ')
        backend=endpoint['record']['backend'];verify='verify'
        if backend!='highs' and endpoint['record']['lp_settings']!=method:raise ValueError('method settings differ')
        for key in ['execution','precision','adaptive']:
            if key in c and endpoint.get(key,{}).get('settings')!=c[key]:raise ValueError('executed '+key+' differs')
        if c['backend']=='cuda-lp-tuned' and endpoint.get('execution',{}).get('code_object_sha256')!=identity['code_object_sha256']:
            raise ValueError('code object identity differs')
    if record['model_sha256']!=job['instance']['model']['sha256'] or record['requested_backend']!=c['backend']:raise ValueError('model/backend differs')
    model=checked_reference(ROOT,job['instance']['model'])
    verified=subprocess.run([str(binary),'lp-study',verify,'--model',str(model),'--model-byte-limit',str(value['model_byte_limit']),
                             '--evidence',str(path)],capture_output=True,text=True,timeout=value['verification_seconds'])
    if verified.returncode:raise ValueError('independent verification failed: '+verified.stderr[:1000])
    return backend,endpoint['assessment']['classification']

def cost_artifact(job,directory,trial,nsys_hash):
    key=job['id'];endpoint=directory/(key+'.endpoint.json');observations=[]
    for process,path,parent in [('solve',directory/(key+'.raw-cost.json'),None),('host-certifier',endpoint.with_suffix('.cert-cost.json'),['copt','host_certification'])]:
        if path.exists():
            validate_profile(read_json(path));observations.append(dict(process=process,parent_scope=parent,artifact=reference(directory,path)))
    traces=[directory/(key+suffix) for suffix in ['.qdstrm','.nsys-rep']]
    trace=next((reference(directory,p) for p in traces if p.exists()),None)
    value=dict(schema_version=1,trial_id=key,model_sha256=trial['model_sha256'],request_sha256=trial['request_sha256'],
        source_tree_sha256=trial['provenance']['source_tree_sha256'],binary_sha256=trial['provenance']['binary_sha256'],
        endpoint_sha256=trial['endpoint']['sha256'] if trial['endpoint'] else None,profiler_sha256=nsys_hash if job['kind']=='trace' else None,
        observations=observations,native_observations=reference(directory,endpoint.with_suffix('.copt-observations.json')),trace=trace,
        partial=trial['status']!='completed' or not observations or (job['kind']=='trace' and trace is None))
    validator('lp-cost-v1.schema.json').validate(value);path=directory/(key+'.cost.json');write_json(path,value);return reference(directory,path)

def run_trial(value,job,binary,directory,ledger,identity,protocol_hash,nsys_hash):
    key=job['id'];gpu=is_gpu(job);c=job['configuration'];solve,method,limits=effective(value,job)
    activity=quiet_device(value['device']) if gpu else None
    if activity:write_json(directory/(key+'.activity.json'),activity)
    args=command(value,job,binary,directory)
    request={k:limits[k] for k in ['solve_seconds','cleanup_seconds','host_rss_bytes','poll_ms','output_bytes']}
    request.update(command=args,directory=str(directory),prefix=key)
    if gpu:request.update(schema_version=2,gpu_admission_seconds=3)
    request_path=directory/(key+'.request.json');write_json(request_path,request)
    trial=dict(schema_version=6,id=key,campaign_sha256=protocol_hash,instance_id=job['instance']['id'],model_sha256=job['instance']['model']['sha256'],
        config_id=c['id'],config_sha256=digest(encoded(dict(configuration=c,solve=solve,lp_settings=method))),
        block=f'{job["kind"]}:{job["instance"]["id"]}:{job["repetition"]}',repetition=job['repetition'],order=job['order'],mode=job['kind'],category=job['category'],
        requested_backend=c['backend'],executed_backend=None,status='process_failure',endpoint_class=None,endpoint=None,worker=None,stdout=None,stderr=None,
        elapsed_ns=None,queue_ns=None,leased_ns=None,verification_ns=None,peak_rss_bytes=None,memory_method='unavailable: worker not completed',limits=limits,
        provenance={**identity,'telemetry_before':telemetry(value['device']),'schema_snapshot_sha256':schema_snapshot().sha256},error='unfinished trial intent',
        budget_authority_sha256=ledger.campaign_hash,activity_wait_ns=activity['elapsed_ns'] if activity else None,
        activity=reference(directory,directory/(key+'.activity.json')),solve=solve,lp_settings=method,request_sha256=file_hash(request_path),cost=None)
    validate('trial',trial);write_json(directory/(key+'.intent.json'),trial)
    reservation=ledger.reserve(key,limits['solve_seconds']+limits['cleanup_seconds']+(4 if gpu else 1),resource='gpu' if gpu else 'cpu',phase=value['categories'][job['category']]['phase'])
    worker_args=['bash',str(ROOT/'tools/gpu_job.sh'),value['device'],'--lp-study-request',str(request_path)] if gpu else [sys.executable,str(ROOT/'tools/lp_supervise.py'),'--request',str(request_path)]
    worker=subprocess.Popen(worker_args,pass_fds=(ledger.lock.fileno(),))
    interrupted=False
    try:worker.wait(timeout=limits['solve_seconds']+limits['cleanup_seconds']+(310 if gpu else 10))
    except (subprocess.TimeoutExpired,KeyboardInterrupt):
        interrupted=True;worker.send_signal(signal.SIGTERM)
        try:worker.wait(timeout=3)
        except subprocess.TimeoutExpired:worker.kill();worker.wait()
    worker_path=directory/(key+'.worker.json');info=read_json(worker_path) if worker_path.exists() else None
    charge=(info['leased_ns'] if gpu else info['elapsed_ns']) if info else reservation['reserved_ns'];ledger.settle(reservation,charge)
    if info:
        trial.update(status=info['reason'] if worker.returncode==0 else 'process_failure',elapsed_ns=info['elapsed_ns'],queue_ns=info['queue_ns'],leased_ns=info['leased_ns'],
                     peak_rss_bytes=info['peak_rss_bytes'],memory_method=info['memory_method'],error=None if worker.returncode==0 else 'supervisor failed')
    else:trial['error']='missing worker report; full reservation charged'
    trial['worker']=reference(directory,worker_path)
    for role in ['stdout','stderr','endpoint']:trial[role]=reference(directory,directory/(key+('.endpoint.json' if role=='endpoint' else '.'+role)))
    verification=time.monotonic_ns()
    if trial['endpoint']:
        try:trial['executed_backend'],trial['endpoint_class']=verify_endpoint(value,job,directory,binary,identity)
        except Exception as error:trial.update(status='invalid_evidence',error=str(error)[:2000])
    elif trial['status']=='completed':trial.update(status='missing_evidence',error='no complete endpoint')
    trial['verification_ns']=time.monotonic_ns()-verification;trial['provenance']['telemetry_after']=telemetry(value['device'])
    if job['kind']!='timing':
        try:trial['cost']=cost_artifact(job,directory,trial,nsys_hash)
        except Exception as error:trial.update(status='invalid_evidence',error='component evidence: '+str(error)[:1600])
    validate('trial',trial);write_json(directory/(key+'.trial.json'),trial)
    write_json(directory/'budget.json',receipt(ledger))
    print(key+': '+trial['status']+'/'+str(trial['endpoint_class'])+'; GPU '+str(round(ledger.totals()/1e9,3))+' s',flush=True)
    if interrupted or info is None or charge>reservation['reserved_ns']:raise ValueError('interrupted/uncertain worker retained; stop')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--protocol',type=Path,default=CONFIG);p.add_argument('--binary',type=Path,default=ROOT/'target/release/optimizer');p.add_argument('--dry-run',action='store_true');a=p.parse_args()
    value=protocol(a.protocol);schedule=list(jobs(value))
    if len(schedule)!=value['planned_attempts'] or len({j['id'] for j in schedule})!=len(schedule):raise ValueError('frozen schedule count differs')
    if a.dry_run:
        from collections import Counter
        print(len(schedule),'planned attempts;',dict(Counter(j['kind'] for j in schedule)));return
    binary=a.binary.resolve();native=provenance(binary,value['device']);gate=read_json(ROOT/'target/lp-native-gate.json')
    if native['build_profile']!='release' or not gate.get('native') or gate['source_tree_sha256']!=native['source_tree_sha256']:raise ValueError('exact-source full native gate/release build required')
    for m in value['manifests']:
        for i in read_json(checked_reference(ROOT,m))['instances']:
            path=checked_reference(ROOT,i['model'])
            if path.stat().st_size>value['model_byte_limit']:raise ValueError('model exceeds admitted input limit')
    code=ROOT/'target/native/cuda';images=code_images(code);original=read_json(ROOT/'benchmarks/configs/lp-precision-v4.json')
    if images['lp_pdhg_precision.cubin']!=original['precision_code_object_sha256'] or images['lp_pdhg_tuned.cubin']!=original['code_object_sha256']:raise ValueError('legacy kernel bytes changed')
    copt=ROOT/'artifacts/gpup5-copt/venv/lib/python3.11/site-packages/coptpy'
    libraries={k:file_hash(copt/f) for k,f in [('copt_library_sha256','libcopt_python.so'),('copt_binding_sha256','coptcore.so')]}
    if any(libraries[k]!=original[k] for k in libraries):raise ValueError('installed COPT identity changed')
    nsys_hash=file_hash(Path(value['nsys']));native.update(copt_library_sha256=None,copt_binding_sha256=None)
    identities={}
    for c in value['configurations']:
        item=dict(native);item['code_object_sha256']=images['lp_pdhg_precision.cubin' if 'precision' in c or 'adaptive' in c else 'lp_pdhg_tuned.cubin' if c['backend']=='cuda-lp-tuned' else 'lp_pdhg.cubin'] if c['backend'].startswith('cuda-') else None
        if c['backend'].startswith('copt-'):item.update(libraries)
        identities[c['id']]=item
    directory=ROOT/value['output']
    with ledger_for(value) as ledger:
        prepare_execution(directory,native)
        for source in [binary,*[code/name for name in images]]:
            dest=directory/source.name
            if dest.exists() and file_hash(dest)!=file_hash(source):raise ValueError('archived binary changed')
            if not dest.exists():shutil.copy2(source,dest)
        frozen={'campaign.json':value,'configuration-executions.json':identities,'code-objects.json':images,'profiler.json':dict(path=value['nsys'],sha256=nsys_hash),
                'budget-binding.json':dict(ledger_directory=str(ledger.path.parent.relative_to(ROOT)))}
        for name,data in frozen.items():
            path=directory/name
            if path.exists() and read_json(path)!=data:raise ValueError('frozen execution differs: '+name)
            write_json(path,data)
        recover_intents(directory,ledger.attempted());exhausted=set()
        try:
            for job in schedule:
                if job['id'] in ledger.attempted() or (job['category'],is_gpu(job)) in exhausted:continue
                try:run_trial(value,job,directory/binary.name,directory,ledger,identities[job['configuration']['id']],file_hash(a.protocol),nsys_hash)
                except ValueError as error:
                    if 'budget exhausted' not in str(error).lower():raise
                    exhausted.add((job['category'],is_gpu(job)));print(str(error),flush=True)
        finally:
            shutil.copyfile(ledger.path,directory/'ledger.jsonl');write_json(directory/'budget.json',receipt(ledger))
            write_json(directory/'exhausted.json',[dict(category=c,gpu=g) for c,g in sorted(exhausted)])
if __name__=='__main__':main()
