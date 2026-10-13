"""Frozen ADR-0035 development study. Every attempt is leased, charged and retained."""
import argparse
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time
from benchmark_lp import prepare_execution, provenance, source_identity, reference, telemetry
from benchmark_lp_adaptive_cost import endpoint_shape
from lp_exec_budget import CONFIG, ledger_for, protocol, receipt
from lp_protocol import ROOT, checked_reference, digest, encoded, file_hash, ordered, read_json, write_json

SUFFIXES=dict(request='.request.json',worker='.worker.json',stdout='.stdout',stderr='.stderr',endpoint='.endpoint.json',raw_cost='.raw-cost.json')

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

def image_inventory(directory):
    # Legacy CLI discovery loads its scheduling image even for LP-only solves.
    # Require every runtime dependency before freezing or reserving an attempt.
    return {name:file_hash(directory/name) for name in ['schedule_eval.cubin','lp_pdhg.cubin','lp_pdhg_tuned.cubin','lp_pdhg_precision.cubin','lp_pdhg_exec.cubin']}

def worker_status(info, supervisor_returncode):
    if info is None:return 'missing_worker'
    if supervisor_returncode or (info['reason']=='completed' and info['returncode']!=0):return 'process_failure'
    return info['reason']

def freeze(value):
    binary=ROOT/'target/release/optimizer';exact=ROOT/'target/release/examples/lp_precision_exec'
    native=provenance(binary,value['device']);gate=read_json(ROOT/'target/lp-native-gate.json')
    if not gate.get('native') or gate['source_tree_sha256']!=native['source_tree_sha256']:raise ValueError('exact-source full native gate required')
    code=ROOT/'target/native/cuda'
    images=image_inventory(code)
    original=read_json(ROOT/'benchmarks/configs/lp-precision-v4.json')
    if images['lp_pdhg_tuned.cubin']!=original['code_object_sha256'] or images['lp_pdhg_precision.cubin']!=original['precision_code_object_sha256']:raise ValueError('legacy code image differs')
    native['code_object_sha256']=images['lp_pdhg_exec.cubin'];native['exec_binary_sha256']=file_hash(exact)
    directory=ROOT/value['output'];prepare_execution(directory,native)
    for source,name in [(binary,'optimizer'),(exact,'lp_precision_exec'),*[(code/name,name) for name in images]]:
        target=directory/name
        if target.exists() and file_hash(target)!=file_hash(source):raise ValueError('frozen executable/image changed')
        if not target.exists():shutil.copy2(source,target)
    for name,data in [('campaign.json',value),('code-objects.json',images),('native-gate.json',gate)]:
        p=directory/name
        if p.exists() and read_json(p)!=data:raise ValueError('frozen identity changed: '+name)
        if not p.exists():write_json(p,data)
    from check_lp_exec_instructions import audit
    audit(directory/'lp_pdhg_exec.cubin',directory)
    return directory,read_json(directory/'execution.json')

def prepare_inputs(value,job,directory,identity):
    documents={}
    def emit(path,data):documents[path.name]=data
    solve,method,seconds=effective(value,job);key=job['id'];c=job['configuration']
    model=checked_reference(ROOT,job['instance']['model']);profile=job['kind']=='profile'
    endpoint=directory/(key+'.endpoint.json')
    if c['backend']=='lp-exec-v1':
        request=dict(schema_version=1,mode=c['mode'],model_sha256=job['instance']['model']['sha256'],source_tree_sha256=identity['source_tree_sha256'],executable_sha256=identity['exec_binary_sha256'],code_object_sha256=identity['code_object_sha256'],device=value['device'],options=solve,method=method,profile=profile,device_buffer_bytes=value['limits']['device_buffer_bytes'])
        emit(directory/(key+'.exec-request.json'),request)
        command=[str(directory/'lp_precision_exec'),'solve',str(model),str(directory/(key+'.exec-request.json')),str(endpoint)]
    else:
        emit(directory/(key+'.solve.json'),solve);emit(directory/(key+'.method.json'),method)
        command=[str(directory/'optimizer'),'lp-study','solve','--model',str(model),'--model-byte-limit',str(value['model_byte_limit']),'--config',str(directory/(key+'.solve.json')),'--backend',c['backend'],'--device',value['device'],'--lp-settings',str(directory/(key+'.method.json')),'--lp-profile',str(profile).lower(),'--lp-device-memory-bytes',str(value['limits']['device_buffer_bytes']),'--lp-evidence',str(endpoint),'--evidence-format','compact-v1']
        for field in ['execution','precision']:
            if field in c:
                emit(directory/(key+'.'+field+'.json'),c[field]);command+=['--lp-'+field,str(directory/(key+'.'+field+'.json'))]
        if profile:command+=['--cost-profile',str(directory/(key+'.raw-cost.json'))]
    return dict(schema_version=2,gpu_admission_seconds=3,command=['/usr/bin/env','AI_OPTIMIZER_CUDA_DIR='+str(directory),*command],directory=str(directory),prefix=key,solve_seconds=seconds,cleanup_seconds=2,host_rss_bytes=value['limits']['host_rss_bytes'],poll_ms=10,output_bytes=value['limits']['output_bytes']),documents

def write_inputs(value,job,directory,identity):
    request,documents=prepare_inputs(value,job,directory,identity)
    for name,data in documents.items():write_json(directory/name,data)
    return request

def check_request(value,job,directory,identity,request):
    expected,documents=prepare_inputs(value,job,directory,identity)
    if request!=expected:raise ValueError('worker command/limits differ from frozen job')
    for name,data in documents.items():
        if read_json(directory/name)!=data:raise ValueError('frozen input differs: '+name)


def verify_endpoint(value,job,directory,identity):
    key=job['id'];c=job['configuration'];path=directory/(key+'.endpoint.json')
    if c['backend']!='lp-exec-v1':
        e=endpoint_shape(path,'compact-v1');solve,method,_=effective(value,job)
        if e['model_sha256']!=job['instance']['model']['sha256'] or e['requested_backend']!=c['backend'] or e['record']['options']!=solve or e['record']['lp_settings']!=method:raise ValueError('control model/method differs')
        for name in ['execution','precision','adaptive']:
            if e.get(name,{}).get('settings')!=c.get(name):raise ValueError('control executed settings differ: '+name)
        if e['diagnostics']['profile']!=(job['kind']=='profile'):raise ValueError('control profile identity differs')
        images=read_json(directory/'code-objects.json');expected=images['lp_pdhg_precision.cubin' if 'precision' in c else 'lp_pdhg_tuned.cubin']
        observed=e['execution']['code_object_sha256']
        if observed not in (None,expected) or (e['record']['backend']==c['backend'] and observed!=expected):raise ValueError('control image differs')
        from lp_protocol import strict_loads
        result=subprocess.run([str(directory/'optimizer'),'lp-study','verify','--model',str(checked_reference(ROOT,job['instance']['model'])),'--model-byte-limit',str(value['model_byte_limit']),'--evidence',str(path)],capture_output=True,text=True,timeout=value['verification_seconds'])
        if result.returncode or strict_loads(result.stdout)!=e['assessment']:raise ValueError('independent control verification failed: '+result.stderr[:1000])
        return e['assessment']
    request=read_json(directory/(key+'.exec-request.json'));solve,method,_=effective(value,job)
    expected=dict(schema_version=1,mode=c['mode'],model_sha256=job['instance']['model']['sha256'],source_tree_sha256=identity['source_tree_sha256'],executable_sha256=identity['exec_binary_sha256'],code_object_sha256=identity['code_object_sha256'],device=value['device'],options=solve,method=method,profile=job['kind']=='profile',device_buffer_bytes=value['limits']['device_buffer_bytes'])
    if request!=expected:raise ValueError('exact request is not the frozen job')
    e=read_json(path)
    if not isinstance(e,dict) or e['witness']['request']!=request:raise ValueError('exact endpoint request differs')
    check=subprocess.run([str(directory/'lp_precision_exec'),'verify',str(checked_reference(ROOT,job['instance']['model'])),str(directory/(key+'.exec-request.json')),str(path)],capture_output=True,text=True,timeout=value['verification_seconds'])
    if check.returncode or check.stdout.strip()!='verified':raise ValueError('independent exact verification failed: '+check.stderr[:1000])
    return e['assessment']

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

def main():
    p=argparse.ArgumentParser();p.add_argument('--dry-run',action='store_true');p.add_argument('--prepare',action='store_true');a=p.parse_args()
    value=protocol();schedule=list(jobs(value))
    if len(schedule)!=108 or len({j['id'] for j in schedule})!=108:raise ValueError('schedule differs')
    totals={category:sum(effective(value,j)[2]+6 for j in schedule if j['category']==category) for category in ['timing','profile']}
    if totals!={'timing':2256,'profile':432}:raise ValueError('worst-case reservations differ')
    if a.dry_run:print(dict(attempts=len(schedule),worst_case_gpu_seconds=totals));return
    directory,identity=freeze(value)
    if a.prepare:return
    from lp_exec_accept import check_acceptance
    check_acceptance(value,identity)
    with ledger_for(value) as ledger:
        recover(directory,ledger)
        try:
            for job in schedule:
                if job['id'] in ledger.attempted():continue
                run_trial(value,job,directory,ledger,identity)
        finally:
            shutil.copy2(ledger.path,directory/'ledger.jsonl');write_json(directory/'budget.json',receipt(ledger))

if __name__=='__main__':main()
