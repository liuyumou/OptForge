"""Frozen ADR-0039 fresh single-solve assessment study; no retries."""
import argparse
import os
from pathlib import Path
import shutil
import signal
import subprocess
from benchmark_lp import prepare_execution,provenance,reference,telemetry
from lp_assess_budget import CONFIG,protocol,ledger_for,receipt
from lp_protocol import ROOT,checked_reference,file_hash,ordered,read_json,write_json
SUFFIXES=dict(request='.request.json',worker='.worker.json',stdout='.stdout',stderr='.stderr',endpoint='.endpoint.json')

def instances(value):
    return {i['id']:i for ref in value['manifests'] for i in read_json(checked_reference(ROOT,ref))['instances']}

def jobs(value):
    models=instances(value)
    for kind,names,repetitions in [('timing',value['timing_instances'],range(value['timing_repetitions'])),('profile',value['profile_instances'],range(1))]:
        for repetition in repetitions:
            for name in names:
                for order,c in enumerate(ordered(value['configurations'],value['order_seed'],kind+':'+name,repetition)):
                    yield dict(id=f'{value["id"]}-{kind}-{name}-{repetition}-{c["id"]}',kind=kind,category=kind,repetition=repetition,order=order,instance=models[name],configuration=c)

def effective(value,job):
    profile=job['kind']=='profile'
    seconds=value['profile_seconds'] if profile else job['instance'].get('time_limit_seconds',10)
    work=value['profile_work'] if profile else value['lp_settings']['iteration_limit']
    return dict(value['solve'],time_limit_ms=seconds*1000,iteration_limit=work),dict(value['lp_settings'],iteration_limit=work),seconds

def worker_status(info, supervisor_returncode):
    if info is None:return 'missing_worker'
    if supervisor_returncode or (info['reason']=='completed' and info['returncode']!=0):return 'process_failure'
    return info['reason']

def refs(directory,key):return {role:reference(directory,directory/(key+suffix)) for role,suffix in SUFFIXES.items()}

def recover(directory,ledger):
    for path in directory.glob('*.intent.json'):
        intent=read_json(path);key=intent['id'];dest=directory/(key+'.trial.json')
        if key in ledger.attempted() and not dest.exists():
            intent.update(status='interrupted',error='coordinator interrupted; actual or full reservation charge retained; no retry',artifacts=refs(directory,key),assessment=None)
            write_json(dest,intent)

def run_trial(value,job,directory,ledger,identity):
    key=job['id']
    if key in ledger.attempted() or (directory/(key+'.request.json')).exists():raise ValueError('attempt identity cannot retry')
    request=write_inputs(value,job,directory,identity)
    request_path=directory/(key+'.request.json');write_json(request_path,request)
    intent=dict(schema_version=1,id=key,job=job,campaign_sha256=file_hash(CONFIG),source_tree_sha256=identity['source_tree_sha256'],request_sha256=file_hash(request_path),status='reserved',assessment=None,error=None,telemetry_before=telemetry(value['device']))
    write_json(directory/(key+'.intent.json'),intent)
    reservation=ledger.reserve(key,request['solve_seconds']+6,phase=value['categories'][job['category']]['phase'])
    worker=subprocess.Popen(['bash',str(ROOT/'tools/gpu_job.sh'),value['device'],'--lp-study-request',str(request_path)],pass_fds=(ledger.lock.fileno(),))
    interrupted=False
    try:worker.wait(timeout=request['solve_seconds']+310)
    except (subprocess.TimeoutExpired,KeyboardInterrupt):
        interrupted=True;worker.send_signal(signal.SIGTERM)
        try:worker.wait(timeout=3)
        except subprocess.TimeoutExpired:worker.kill();worker.wait()
    worker_path=directory/(key+'.worker.json');info=read_json(worker_path) if worker_path.exists() else None
    charge=info['leased_ns'] if info else reservation['reserved_ns'];ledger.settle(reservation,charge)
    trial=dict(intent,status=worker_status(info,worker.returncode),worker_returncode=worker.returncode,charged_ns=charge,artifacts=refs(directory,key),telemetry_after=telemetry(value['device']))
    if trial['artifacts']['endpoint']:
        try:trial['assessment']=verify_endpoint(value,job,directory,identity)
        except Exception as error:trial.update(status='invalid_evidence',error=str(error)[:2000])
    elif trial['status']=='completed':trial.update(status='missing_evidence',error='no complete endpoint')
    write_json(directory/(key+'.trial.json'),trial);write_json(directory/'budget.json',receipt(ledger))
    print(key+': '+trial['status']+'/'+str(trial['assessment']),flush=True)
    if interrupted or info is None or charge>reservation['reserved_ns']:raise ValueError('uncertain/over-budget worker retained; stop')

def image_inventory(directory):
    from benchmark_lp_refine import image_inventory as inherited
    return inherited(directory)

def freeze(value):
    binary=ROOT/'target/release/examples/lp_precision_assess';gate=read_json(ROOT/'target/lp-native-gate.json')
    native=provenance(binary,value['device'])
    # The generic helper sees the examples/ directory; this binary is built in release.
    native['build_profile']='release'
    if not gate.get('native') or gate['source_tree_sha256']!=native['source_tree_sha256']:raise ValueError('exact-source full pinned-native gate required')
    images=image_inventory(ROOT/'target/native/cuda')
    historical=read_json(ROOT/'artifacts/gpup-refine-v2/study/code-objects.json')
    if images!=historical:raise ValueError('assessment must reuse unchanged complete CUDA inventory')
    native.update(exec_binary_sha256=file_hash(binary),code_object_sha256=images['lp_pdhg_tuned.cubin'])
    directory=ROOT/value['output'];prepare_execution(directory,native)
    for source,name in [(binary,'lp_precision_assess'),*[(ROOT/'target/native/cuda'/n,n) for n in images]]:
        target=directory/name
        if target.exists() and file_hash(target)!=file_hash(source):raise ValueError('assessment frozen executable/image changed')
        if not target.exists():shutil.copy2(source,target)
    for name,data in [('campaign.json',value),('code-objects.json',images),('native-gate.json',gate)]:
        target=directory/name
        if target.exists() and read_json(target)!=data:raise ValueError('assessment frozen contract changed')
        if not target.exists():write_json(target,data)
    build=read_json(ROOT/'target/lp-assess-binaries.json')
    if build['source_tree_sha256']!=native['source_tree_sha256']:raise ValueError('assessment test binary source differs')
    archived={}
    for key,ref in build['binaries'].items():
        source=checked_reference(ROOT,ref);target=directory/(source.name+'-'+ref['sha256'][:16])
        if target.exists() and file_hash(target)!=ref['sha256']:raise ValueError('assessment frozen test binary differs')
        if not target.exists():shutil.copy2(source,target)
        archived[key]=reference(ROOT,target)
    manifest=directory/'acceptance-binaries.json'
    if manifest.exists() and read_json(manifest)!=archived:raise ValueError('assessment acceptance binary identity differs')
    if not manifest.exists():write_json(manifest,archived)
    return directory,read_json(directory/'execution.json')

def prepare_inputs(value,job,directory,identity):
    solve,method,seconds=effective(value,job);key=job['id'];c=job['configuration']
    images=read_json(directory/'code-objects.json') if (directory/'code-objects.json').exists() else identity['images']
    request=dict(schema_version=1,identity='lp-assess-v1',arithmetic=c['arithmetic'],policy=c['policy'],model_sha256=job['instance']['model']['sha256'],source_tree_sha256=identity['source_tree_sha256'],executable_sha256=identity['exec_binary_sha256'],code_object_sha256=images['lp_pdhg_tuned.cubin' if c['arithmetic']=='tuned_fp64' else 'lp_pdhg_precision.cubin'],device=value['device'],options=solve,method=method,diagnostic=job['kind']=='profile',device_buffer_bytes=value['limits']['device_buffer_bytes'])
    payload=directory/(key+'.assess-request.json');model=checked_reference(ROOT,job['instance']['model'])
    command=[str(directory/'lp_precision_assess'),'solve',str(model),str(payload),str(directory/(key+'.endpoint.json'))]
    worker=dict(schema_version=2,gpu_admission_seconds=3,command=['/usr/bin/env','AI_OPTIMIZER_CUDA_DIR='+str(directory),*command],directory=str(directory),prefix=key,solve_seconds=seconds,cleanup_seconds=2,host_rss_bytes=value['limits']['host_rss_bytes'],poll_ms=10,output_bytes=value['limits']['output_bytes'])
    return worker,{payload.name:request}

def write_inputs(value,job,directory,identity):
    request,documents=prepare_inputs(value,job,directory,identity)
    for name,data in documents.items():write_json(directory/name,data)
    return request

def check_request(value,job,directory,identity,request):
    expected,documents=prepare_inputs(value,job,directory,identity)
    if request!=expected:raise ValueError('assessment worker command/limits differ')
    for name,data in documents.items():
        if read_json(directory/name)!=data:raise ValueError('assessment frozen request differs')

def verify_endpoint(value,job,directory,identity):
    key=job['id'];endpoint=directory/(key+'.endpoint.json');e=read_json(endpoint)
    from validate_artifacts import validator
    validator('lp-assess-evidence-v1.schema.json').validate(e)
    _,documents=prepare_inputs(value,job,directory,identity);expected=documents[key+'.assess-request.json']
    if e['witness']['request']!=expected or e['witness']['executor']!='gpu':raise ValueError('assessment endpoint complete request differs')
    result=subprocess.run([str(directory/'lp_precision_assess'),'verify',str(checked_reference(ROOT,job['instance']['model'])),str(directory/(key+'.assess-request.json')),str(endpoint)],capture_output=True,text=True,timeout=value['verification_seconds'])
    if result.returncode or result.stdout.strip()!='verified':raise ValueError('assessment host verification failed: '+result.stderr[:2000])
    return e['assessment']

def main():
    p=argparse.ArgumentParser();p.add_argument('--dry-run',action='store_true');p.add_argument('--prepare',action='store_true');a=p.parse_args()
    value=protocol();schedule=list(jobs(value));totals={k:sum(effective(value,j)[2]+6 for j in schedule if j['kind']==k) for k in ['timing','profile']}
    if len(schedule)!=60 or len({j['id'] for j in schedule})!=60 or totals!={'timing':1248,'profile':432}:raise ValueError('assessment frozen roster differs')
    if a.dry_run:print(dict(attempts=60,reservations=totals,acceptance=516));return
    directory,identity=freeze(value)
    if a.prepare:return
    from lp_assess_accept import check_acceptance
    check_acceptance(value,identity)
    with ledger_for(value) as ledger:
        recover(directory,ledger)
        try:
            for job in schedule:
                if job['id'] in ledger.attempted():continue
                run_trial(value,job,directory,ledger,identity)
        finally:shutil.copy2(ledger.path,directory/'ledger.jsonl');write_json(directory/'budget.json',receipt(ledger))
if __name__=='__main__':main()
