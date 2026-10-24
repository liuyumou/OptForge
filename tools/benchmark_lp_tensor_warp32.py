"""Frozen ADR-0044 fresh-process matrix-quantization study; no retries."""
import argparse,os,shutil,signal,subprocess,time
from pathlib import Path
from benchmark_lp import prepare_execution,provenance,reference,telemetry,source_identity
from lp_tensor_warp32_common import CONFIG,protocol,ledger_for,receipt
from lp_protocol import ROOT,read_json,write_json,file_hash,checked_reference,ordered
from benchmark_lp_refine import image_inventory as old_inventory,prepare_inputs as control_inputs,verify_endpoint as verify_control
SUFFIXES=dict(request='.request.json',worker='.worker.json',stdout='.stdout',stderr='.stderr',endpoint='.endpoint.json',raw_cost='.raw-cost.json',verification='.verification.json')
def instances(value):
    return {i['id']:i for ref in value['manifests'] for i in read_json(checked_reference(ROOT,ref))['instances']}

def jobs(value):
    models=instances(value)
    for kind,names,repetitions in [('profile',value['profile_instances'],range(1)),('timing',value['timing_instances'],range(5))]:
        for repetition in repetitions:
            for name in names:
                for order,c in enumerate(ordered(value['configurations'],value['order_seed'],kind+':'+name,repetition)):
                    yield dict(id=f'{value["id"]}-{kind}-{name}-{repetition}-{c["id"]}',kind=kind,category=kind,repetition=repetition,order=order,instance=models[name],configuration=c)
        if kind=='profile':
            name=value['profile_instances'][1]
            for c in value['configurations'][:2]:
                for ablation,policy in [('old-norm',dict(norm_policy='legacy-twice-absolute-v1')),('host-audit',dict(audit_policy='host_oracle_v1'))]:
                    yield dict(id=value['id']+'-profile-ablation-'+c['id']+'-'+ablation,kind='profile',category='profile',repetition=0,order=0,instance=models[name],configuration=dict(c,**policy),ablation=ablation)

def effective(value,job):
    small=job['instance']['id'].endswith('-1024')
    seconds=20 if 'ablation' in job else (6 if small else 18) if job['kind']=='profile' else (5 if small else 16)
    work=value['profile_work'] if job['kind']=='profile' and job['configuration']['backend']=='cuda-lp-tuned' else value['lp_settings']['iteration_limit']
    return dict(value['solve'],time_limit_ms=seconds*1000,iteration_limit=work),dict(value['lp_settings'],iteration_limit=work),seconds

def control_job(value,job):
    return dict(job,instance=dict(job['instance'],time_limit_seconds=effective(value,job)[2]))

def control_value(value,job):
    return dict(value,profile_seconds=effective(value,job)[2])

def numeric_command(command):
    return ['python3',str(ROOT/'tools/lp_tensor_cost_exec.py'),'--memory-bytes',str(2<<30),'--',*command]

def artifact_limit(value):
    root=ROOT/value['output'];total=sum(p.stat().st_size for p in root.parent.rglob('*') if p.is_file())
    if total>value['artifact_bytes']:raise ValueError('artifact resource ceiling exceeded')

def worker_status(info, supervisor_returncode):
    if info is None:return 'missing_worker'
    if supervisor_returncode or (info['reason']=='completed' and info['returncode']!=0):return 'process_failure'
    return info['reason']


def freeze(value):
 from lp_tensor_warp32_common import numeric_sources
 from lp_tensor_warp32_availability_bridge import verify_cpu_sources
 cpu=read_json(ROOT/'docs/benchmarks/data/tensor-warp32/cpu-admission-v1.json');proof=read_json(ROOT/'docs/benchmarks/data/tensor-cost/proofs-v2.json');audit=read_json(ROOT/'docs/benchmarks/data/tensor-warp32/instruction-admission.json')
 verify_cpu_sources(cpu)
 resource=read_json(ROOT/'docs/benchmarks/data/tensor-cost/resource-admission-v4.json');norm=read_json(ROOT/'docs/benchmarks/data/tensor-cost/norm-proof-v2.json')
 if resource['status']!='passed' or resource['supervisor_sha256']!=file_hash(ROOT/'tools/lp_cpu_admission.py') or norm['status']!='passed' or norm['oracle_sha256']!=file_hash(ROOT/'tools/lp_tensor_cost_norm_oracle.py'):raise ValueError('resource/norm admission differs')
 if norm['probe_sha256']!=file_hash(ROOT/'target/release/examples/tensor_cost_norm_probe') or norm['compact_probe_sha256']!=file_hash(ROOT/'target/release/examples/tensor_cost_compact_probe'):raise ValueError('norm oracle executable differs')
 from lp_tensor_warp32_common import IMAGE
 from lp_tensor_warp32_build import preserve
 preserve()
 reduction=read_json(ROOT/'docs/benchmarks/data/tensor-warp32/reduction-proof.json')
 if reduction['status']!='passed' or reduction['image_sha256']!=file_hash(IMAGE) or reduction['oracle_sha256']!=file_hash(ROOT/'tools/lp_tensor_warp32_oracle.py') or reduction['probe_sha256']!=file_hash(ROOT/'target/release/examples/tensor_warp32_probe'):raise ValueError('warp32 independent reduction proof differs')
 if cpu['status']!='passed' or cpu['gpu_seconds']!=0 or proof['status']!='passed' or proof['probe_sha256']!=file_hash(ROOT/'target/release/examples/tensor_cost_probe') or proof['oracle_sha256']!=file_hash(ROOT/'tools/lp_tensor_cost_oracle.py') or audit['status']!='passed' or audit['image_sha256']!=file_hash(IMAGE) or cpu['image_sha256']!=audit['image_sha256'] or any(file_hash(ROOT/path)!=sha for path,sha in audit['sources'].items()):raise ValueError('exact Tensor CPU/proof/image admission required')
 binary=ROOT/'target/release/optimizer';exact=ROOT/'target/release/examples/lp_precision_tensor_cost';native=provenance(binary,value['device']);gate=read_json(ROOT/'target/lp-native-gate.json')
 historical=read_json(ROOT/'artifacts/gpup-tensor-warp32-v1/historical-bindings.json')['old_execution']
 if file_hash(binary)!=historical['binary_sha256'] or file_hash(exact)!=historical['exec_binary_sha256']:raise ValueError('unchanged host executable differs')
 if not gate.get('native') or gate['source_tree_sha256']!=native['source_tree_sha256']:raise ValueError('exact-source pinned-native gate required')
 code=ROOT/'artifacts/gpup-tensor-warp32-v1/image-directory';images=old_inventory(code)
 original=read_json(ROOT/'benchmarks/configs/lp-precision-v4.json')
 if images['lp_pdhg_tuned.cubin']!=original['code_object_sha256']:raise ValueError('unchanged tuned image differs')
 for name in ['lp_pdhg_tensor_cost.cubin','lp_pdhg_tensor_cost.build.json']:images[name]=file_hash(code/name)
 native.update(code_object_sha256=images['lp_pdhg_tensor_cost.cubin'],exec_binary_sha256=file_hash(exact),cpu_affinity=sorted(os.sched_getaffinity(0)));d=ROOT/value['output'];prepare_execution(d,native)
 for source,name in [(binary,'optimizer'),(exact,'lp_precision_tensor_cost'),*[(code/name,name) for name in images]]:
  dest=d/name
  if dest.exists() and file_hash(dest)!=file_hash(source):raise ValueError('frozen executable/image changed')
  if not dest.exists():shutil.copy2(source,dest)
 build=read_json(ROOT/'target/lp-tensor-warp32-binaries.json')
 if build['source_tree_sha256']!=native['source_tree_sha256']:raise ValueError('quant test source differs')
 binaries={}
 for key,ref in build['binaries'].items():
  source=checked_reference(ROOT,ref);dest=d/(source.name+'-'+ref['sha256'][:16])
  if not dest.exists():shutil.copy2(source,dest)
  if file_hash(dest)!=ref['sha256']:raise ValueError('frozen test binary differs')
  binaries[key]=reference(ROOT,dest)
 for name,data in [('campaign.json',value),('code-objects.json',images),('native-gate.json',gate),('acceptance-binaries.json',binaries),('cpu-admission.json',cpu),('oracle.json',proof),('instruction-admission.json',audit),('norm-proof.json',norm),('resource-admission.json',resource)]:
  dest=d/name
  if dest.exists() and read_json(dest)!=data:raise ValueError('frozen contract changed')
  if not dest.exists():write_json(dest,data)
 from lp_tensor_warp32_screen import RULE,RESOURCE_RULE
 from lp_tensor_warp32_accept import acceptance_jobs,acceptance_request
 for name,data in [('forecast-rule.json',RULE),('resource-rule.json',RESOURCE_RULE),('roster.json',list(jobs(value)))]:
  path=d/name
  if path.exists() and read_json(path)!=data:raise ValueError('frozen rule/roster changed')
  if not path.exists():write_json(path,data)
 for gate,seconds in acceptance_jobs():
  request=acceptance_request(value,d,gate,seconds)
  path=d/(value['id']+'-accept-'+gate+'.frozen.json')
  if path.exists() and read_json(path)!=request:raise ValueError('frozen acceptance differs')
  if not path.exists():write_json(path,request)
 for j in jobs(value):
  worker,documents=prepare_inputs(value,j,d,read_json(d/'execution.json'))
  documents[j['id']+'.frozen.json']=worker
  for name,data in documents.items():
   path=d/name
   if path.exists() and read_json(path)!=data:raise ValueError('frozen input changed')
   if not path.exists():write_json(path,data)
 return d,read_json(d/'execution.json')
def prepare_inputs(value,job,directory,identity):
 if job['configuration']['backend']!='lp-tensor-cost-v1':
  worker,docs=control_inputs(control_value(value,job),control_job(value,job),directory,identity)
  worker['command']=worker['command'][:2]+numeric_command(worker['command'][2:])
  return worker,docs
 from lp_tensor_warp32_common import make_request
 solve,method,seconds=effective(value,job);key=job['id'];model=checked_reference(ROOT,job['instance']['model'])
 request=make_request(job['configuration'],model,directory/'lp_precision_tensor_cost',identity['source_tree_sha256'],work=method['iteration_limit'],horizon=value['profile_work'] if job['kind']=='profile' else 0,seconds=seconds)
 request['code_object_sha256']=identity['code_object_sha256']
 path=directory/(key+'.resident-request.json');command=[str(directory/'lp_precision_tensor_cost'),'solve',str(model),str(path),str(directory/(key+'.endpoint.json'))]
 worker=dict(schema_version=2,gpu_admission_seconds=3,command=['/usr/bin/env','AI_OPTIMIZER_CUDA_DIR='+str(directory),*numeric_command(command)],directory=str(directory),prefix=key,solve_seconds=seconds,cleanup_seconds=2,host_rss_bytes=value['limits']['host_rss_bytes'],poll_ms=10,output_bytes=value['limits']['output_bytes'])
 return worker,{path.name:request}
def write_inputs(value,job,directory,identity):
 request,docs=prepare_inputs(value,job,directory,identity)
 for name,data in docs.items():
  path=directory/name
  if path.exists() and read_json(path)!=data:raise ValueError('resident frozen request changed')
  if not path.exists():write_json(path,data)
 return request
def _verify_endpoint_fresh(value,job,directory,identity):
 if job['configuration']['backend']!='lp-tensor-cost-v1':
  from benchmark_lp_adaptive_cost import endpoint_shape
  from lp_protocol import strict_loads
  path=directory/(job['id']+'.endpoint.json');e=endpoint_shape(path,'compact-v1');c=job['configuration'];solve,method,_=effective(value,job)
  if e['model_sha256']!=job['instance']['model']['sha256'] or e['requested_backend']!=c['backend'] or e['record']['options']!=solve or e['record']['lp_settings']!=method:raise ValueError('control model/method differs')
  for name in ['execution','precision','adaptive']:
   if e.get(name,{}).get('settings')!=c.get(name):raise ValueError('control executed settings differ: '+name)
  if e['diagnostics']['profile']!=(job['kind']=='profile'):raise ValueError('control profile identity differs')
  expected=read_json(directory/'code-objects.json')['lp_pdhg_tuned.cubin'];observed=e['execution']['code_object_sha256']
  if observed not in (None,expected) or (e['record']['backend']==c['backend'] and observed!=expected):raise ValueError('control image differs')
  command=[str(directory/'optimizer'),'lp-study','verify','--model',str(checked_reference(ROOT,job['instance']['model'])),'--model-byte-limit',str(value['model_byte_limit']),'--evidence',str(path)]
  r=subprocess.run(numeric_command(command),capture_output=True,text=True,timeout=value['verification_seconds'])
  if r.returncode or strict_loads(r.stdout)!=e['assessment']:raise ValueError('independent control verification failed: '+r.stderr[:1000])
  return e['assessment']
 key=job['id'];path=directory/(key+'.endpoint.json');e=read_json(path);_,docs=prepare_inputs(value,job,directory,identity);expected=docs[key+'.resident-request.json']
 from validate_artifacts import validator
 validator('lp-tensor-cost-evidence-v1.schema.json').validate(e)
 if e['request']!=expected or e['executor']!='gpu':raise ValueError('quant exact request/executor differs')
 r=subprocess.run(numeric_command([str(directory/'lp_precision_tensor_cost'),'verify',str(checked_reference(ROOT,job['instance']['model'])),str(directory/(key+'.resident-request.json')),str(path)]),capture_output=True,text=True,timeout=value['verification_seconds'])
 if r.returncode or r.stdout.strip()!='verified':raise ValueError('quant independent endpoint verification '+r.stderr[:1000])
 return e['assessment']

def verify_endpoint(value,job,directory,identity):
 from lp_tensor_warp32_common import read_verification,save_verification
 from benchmark_lp_adaptive_cost import endpoint_shape
 import time
 key=job['id'];endpoint=directory/(key+'.endpoint.json');cache=directory/(key+'.verification.json')
 worker,docs=prepare_inputs(value,job,directory,identity)
 if read_json(directory/(key+'.frozen.json'))!=worker or any(read_json(directory/name)!=document for name,document in docs.items()):raise ValueError('verification frozen input differs')
 custom=job['configuration']['backend']=='lp-tensor-cost-v1'
 request=directory/(key+('.resident-request.json' if custom else '.frozen.json'))
 binary=directory/('lp_precision_tensor_cost' if custom else 'optimizer');model=checked_reference(ROOT,job['instance']['model'])
 if cache.exists():
  trial=read_json(directory/(key+'.trial.json'))
  if checked_reference(directory,trial['artifacts']['verification'])!=cache:raise ValueError('trial verification receipt binding differs')
  result=read_verification(cache,model,request,endpoint,binary,identity['source_tree_sha256'])
  e=read_json(endpoint) if custom else endpoint_shape(endpoint,'compact-v1')
  if result['assessment']!=e['assessment']:raise ValueError('cached assessment differs')
  return result['assessment']
 started=time.monotonic_ns();assessment=_verify_endpoint_fresh(value,job,directory,identity)
 save_verification(cache,model,request,endpoint,binary,identity['source_tree_sha256'],assessment,time.monotonic_ns()-started)
 return assessment

def refs(directory,key):return {role:reference(directory,directory/(key+suffix)) for role,suffix in SUFFIXES.items()}

def recover(directory,ledger):
    for path in directory.glob('*.intent.json'):
        intent=read_json(path);key=intent['id'];dest=directory/(key+'.trial.json')
        if key in ledger.attempted() and not dest.exists():
            intent.update(status='interrupted',error='coordinator interrupted; actual or full reservation charge retained; no retry',artifacts=refs(directory,key),assessment=None)
            write_json(dest,intent)

def run_trial(value,job,directory,ledger,identity):
    coordinator_started=time.monotonic_ns()
    key=job['id']
    artifact_limit(value)
    if read_json(directory/(key+'.frozen.json'))!=prepare_inputs(value,job,directory,identity)[0]:raise ValueError('frozen worker changed')
    if source_identity()!=identity['source_tree_sha256']:raise ValueError('resident source changed before execution')
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
    trial['coordinator_wall_ns']=time.monotonic_ns()-coordinator_started
    write_json(directory/(key+'.trial.json'),trial);write_json(directory/'budget.json',receipt(ledger));shutil.copy2(ledger.path,directory/'ledger.jsonl')
    print(key+': '+trial['status']+'/'+str(trial['assessment']),flush=True)
    if trial['status']!='completed' or trial['assessment'] is None or interrupted or info is None or info['reason']=='activity_blocked' or charge>reservation['reserved_ns']:raise ValueError('uncertain/over-budget worker retained; stop')


def main():
 p=argparse.ArgumentParser()
 p.add_argument('--phase',choices=['prepare','accept','profiles','forecast','timings'],default='prepare')
 p.add_argument('--dry-run',action='store_true');a=p.parse_args();v=protocol();roster=list(jobs(v))
 totals={k:sum(effective(v,j)[2]+6 for j in roster if j['kind']==k) for k in ['timing','profile']}
 if len(roster)!=76 or totals!={'timing':990,'profile':320}:raise ValueError('cost roster/reservations differ')
 if a.dry_run:print(dict(attempts=76,reservations=totals,acceptance=290,aggregate_caps=v['categories']));return
 if a.phase=='prepare':freeze(v);print('Frozen 76 study and six acceptance identities; zero GPU reservations');return
 d=ROOT/v['output'];identity=read_json(d/'execution.json')
 if source_identity()!=identity['source_tree_sha256']:raise ValueError('frozen source changed')
 from lp_tensor_warp32_accept import check_acceptance,run_acceptance
 if a.phase=='accept':run_acceptance(v,d,identity);return
 check_acceptance(v,identity)
 from lp_tensor_warp32_screen import forecast
 if a.phase=='forecast':print(forecast(v,d,identity));return
 if a.phase=='timings':
  screen=forecast(v,d,identity)
  if not screen['passed']:raise ValueError('forecast gate refuses primary timings')
  from lp_tensor_warp32_screen import resource_forecast
  if not resource_forecast(v,d,identity)['passed']:raise ValueError('joint resource-fit gate refuses primary timings')
 with ledger_for(v) as ledger:
  recover(d,ledger)
  for j in roster:
   if j['kind']!=('profile' if a.phase=='profiles' else 'timing'):continue
   if j['id'] in ledger.attempted() or (d/(j['id']+'.trial.json')).exists():raise ValueError('phase cannot retry attempted identity')
   run_trial(v,j,d,ledger,identity)
  shutil.copy2(ledger.path,d/'ledger.jsonl')
if __name__=='__main__':main()
