"""Frozen ADR-0043 fresh-process matrix-quantization study; no retries."""
import argparse,os,shutil,signal,subprocess
from pathlib import Path
from benchmark_lp import prepare_execution,provenance,reference,telemetry,source_identity
from lp_tensor_residual_common import CONFIG,protocol,ledger_for,receipt
from lp_protocol import ROOT,read_json,write_json,file_hash,checked_reference,ordered
from benchmark_lp_refine import image_inventory as old_inventory,prepare_inputs as control_inputs,verify_endpoint as verify_control
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
 profile=job['kind']=='profile';seconds=value['profile_seconds'] if profile else (8 if job['instance']['id'].endswith('-1024') else 28)
 work=value['lp_settings']['iteration_limit']
 return dict(value['solve'],time_limit_ms=seconds*1000,iteration_limit=work),dict(value['lp_settings'],iteration_limit=work),seconds

def control_job(value,job):
 # The inherited control builder reads deadlines from the model descriptor.
 # Bind it explicitly to this protocol's 8/28-second fresh-process limits.
 return dict(job,instance=dict(job['instance'],time_limit_seconds=effective(value,job)[2]))

def worker_status(info, supervisor_returncode):
    if info is None:return 'missing_worker'
    if supervisor_returncode or (info['reason']=='completed' and info['returncode']!=0):return 'process_failure'
    return info['reason']


def freeze(value):
 from lp_tensor_residual_common import numeric_sources,verify_cpu_sources
 cpu=read_json(ROOT/'docs/benchmarks/data/tensor-residual/cpu-admission.json');proof=read_json(ROOT/'docs/benchmarks/data/tensor-residual/oracle.json');audit=read_json(ROOT/'docs/benchmarks/data/tensor-residual/instruction-admission.json')
 verify_cpu_sources(cpu)
 if cpu['status']!='passed' or cpu['gpu_seconds']!=0 or proof['status']!='passed' or proof['probe_sha256']!=file_hash(ROOT/'target/release/examples/tensor_residual_probe') or proof['oracle_sha256']!=file_hash(ROOT/'tools/lp_tensor_residual_oracle.py') or audit['status']!='passed' or audit['image_sha256']!=file_hash(ROOT/'target/native/cuda/lp_pdhg_tensor_residual.cubin') or cpu['image_sha256']!=audit['image_sha256'] or any(file_hash(ROOT/path)!=sha for path,sha in audit['sources'].items()):raise ValueError('exact Tensor CPU/proof/image admission required')
 binary=ROOT/'target/release/optimizer';exact=ROOT/'target/release/examples/lp_precision_tensor_residual';native=provenance(binary,value['device']);gate=read_json(ROOT/'target/lp-native-gate.json')
 if not gate.get('native') or gate['source_tree_sha256']!=native['source_tree_sha256']:raise ValueError('exact-source pinned-native gate required')
 code=ROOT/'target/native/cuda';images=old_inventory(code)
 for name in ['lp_pdhg_tensor_residual.cubin','lp_pdhg_tensor_residual.build.json']:images[name]=file_hash(code/name)
 native.update(code_object_sha256=images['lp_pdhg_tensor_residual.cubin'],exec_binary_sha256=file_hash(exact));d=ROOT/value['output'];prepare_execution(d,native)
 for source,name in [(binary,'optimizer'),(exact,'lp_precision_tensor_residual'),*[(code/name,name) for name in images]]:
  dest=d/name
  if dest.exists() and file_hash(dest)!=file_hash(source):raise ValueError('frozen executable/image changed')
  if not dest.exists():shutil.copy2(source,dest)
 build=read_json(ROOT/'target/lp-tensor-residual-binaries.json')
 if build['source_tree_sha256']!=native['source_tree_sha256']:raise ValueError('quant test source differs')
 binaries={}
 for key,ref in build['binaries'].items():
  source=checked_reference(ROOT,ref);dest=d/(source.name+'-'+ref['sha256'][:16])
  if not dest.exists():shutil.copy2(source,dest)
  if file_hash(dest)!=ref['sha256']:raise ValueError('frozen test binary differs')
  binaries[key]=reference(ROOT,dest)
 for name,data in [('campaign.json',value),('code-objects.json',images),('native-gate.json',gate),('acceptance-binaries.json',binaries),('cpu-admission.json',cpu),('oracle.json',proof),('instruction-admission.json',audit)]:
  dest=d/name
  if dest.exists() and read_json(dest)!=data:raise ValueError('frozen contract changed')
  if not dest.exists():write_json(dest,data)
 for j in jobs(value):
  _,documents=prepare_inputs(value,j,d,read_json(d/'execution.json'))
  for name,data in documents.items():
   path=d/name
   if path.exists() and read_json(path)!=data:raise ValueError('frozen input changed')
   if not path.exists():write_json(path,data)
 return d,read_json(d/'execution.json')
def prepare_inputs(value,job,directory,identity):
 if job['configuration']['backend']!='lp-tensor-residual-v1' and job['kind']=='timing':return control_inputs(value,control_job(value,job),directory,identity)
 from lp_tensor_residual_common import make_request
 solve,method,seconds=effective(value,job);key=job['id'];model=checked_reference(ROOT,job['instance']['model'])
 request=make_request(job['configuration'],model,directory/'lp_precision_tensor_residual',identity['source_tree_sha256'],work=method['iteration_limit'],horizon=value['profile_work'] if job['kind']=='profile' else 0,seconds=seconds)
 request['code_object_sha256']=identity['code_object_sha256']
 path=directory/(key+'.resident-request.json');command=[str(directory/'lp_precision_tensor_residual'),'solve',str(model),str(path),str(directory/(key+'.endpoint.json'))]
 worker=dict(schema_version=2,gpu_admission_seconds=3,command=['/usr/bin/env','AI_OPTIMIZER_CUDA_DIR='+str(directory),*command],directory=str(directory),prefix=key,solve_seconds=seconds,cleanup_seconds=2,host_rss_bytes=value['limits']['host_rss_bytes'],poll_ms=10,output_bytes=value['limits']['output_bytes'])
 return worker,{path.name:request}
def write_inputs(value,job,directory,identity):
 request,docs=prepare_inputs(value,job,directory,identity)
 for name,data in docs.items():
  path=directory/name
  if path.exists() and read_json(path)!=data:raise ValueError('resident frozen request changed')
  if not path.exists():write_json(path,data)
 return request
def verify_endpoint(value,job,directory,identity):
 if job['configuration']['backend']!='lp-tensor-residual-v1' and job['kind']=='timing':return verify_control(value,control_job(value,job),directory,identity)
 key=job['id'];path=directory/(key+'.endpoint.json');e=read_json(path);_,docs=prepare_inputs(value,job,directory,identity);expected=docs[key+'.resident-request.json']
 from validate_artifacts import validator
 validator('lp-tensor-residual-evidence-v1.schema.json').validate(e)
 if e['request']!=expected or e['executor']!='gpu':raise ValueError('quant exact request/executor differs')
 r=subprocess.run([str(directory/'lp_precision_tensor_residual'),'verify',str(checked_reference(ROOT,job['instance']['model'])),str(directory/(key+'.resident-request.json')),str(path)],capture_output=True,text=True,timeout=value['verification_seconds'])
 if r.returncode or r.stdout.strip()!='verified':raise ValueError('quant independent endpoint verification '+r.stderr[:1000])
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
    write_json(directory/(key+'.trial.json'),trial);write_json(directory/'budget.json',receipt(ledger))
    print(key+': '+trial['status']+'/'+str(trial['assessment']),flush=True)
    if interrupted or info is None or info['reason']=='activity_blocked' or charge>reservation['reserved_ns']:raise ValueError('uncertain/over-budget worker retained; stop')


def micro_jobs(value):
 return [dict(id=value['id']+'-profile-micro-'+str(i),kind='micro',category='profile',repetition=i) for i in range(3)]
def run_microprofiles(v,d,ledger,identity):
 for j in micro_jobs(v):
  key=j['id'];trial=d/(key+'.trial.json')
  if key in ledger.attempted() or trial.exists():continue
  test=checked_reference(ROOT,read_json(d/'acceptance-binaries.json')['tensor-residual'])
  command=['/usr/bin/env','AI_OPTIMIZER_CUDA_DIR='+str(d),'AI_OPTIMIZER_GPU=1',str(test),'tensor_products_match_exact_cpu_in_both_orientations','--nocapture','--test-threads','1']
  request=dict(schema_version=2,gpu_admission_seconds=3,command=command,directory=str(d),prefix=key,solve_seconds=29,cleanup_seconds=2,host_rss_bytes=v['limits']['host_rss_bytes'],poll_ms=10,output_bytes=v['limits']['output_bytes'])
  path=d/(key+'.request.json');write_json(path,request);write_json(d/(key+'.intent.json'),dict(id=key,job=j,status='reserved',charged_ns=0))
  reservation=ledger.reserve(key,35,phase='ablations');worker=subprocess.Popen(['bash',str(ROOT/'tools/gpu_job.sh'),v['device'],'--lp-study-request',str(path)],pass_fds=(ledger.lock.fileno(),))
  try:worker.wait(timeout=340)
  finally:
   if worker.poll() is None:worker.terminate();worker.wait(timeout=3)
   info=read_json(d/(key+'.worker.json')) if (d/(key+'.worker.json')).exists() else None
   charge=info['leased_ns'] if info else reservation['reserved_ns'];ledger.settle(reservation,charge)
   result=dict(id=key,job=j,status=worker_status(info,worker.returncode),charged_ns=charge,artifacts=refs(d,key));write_json(trial,result);write_json(d/'budget.json',receipt(ledger))
  print(key+': '+result['status'],flush=True)
  if info is None or info['reason']!='completed' or info['returncode']!=0 or charge>reservation['reserved_ns']:raise ValueError('Tensor diagnostic failed; retain and stop')

def main():
 p=argparse.ArgumentParser();p.add_argument('--dry-run',action='store_true');p.add_argument('--prepare',action='store_true');a=p.parse_args();v=protocol();roster=list(jobs(v));totals={k:sum(effective(v,j)[2]+6 for j in roster if j['kind']==k) for k in ['timing','profile']}
 totals['profile']+=105
 if len(roster)!=72 or totals!={'timing':1440,'profile':525}:raise ValueError('quant roster/reservations differ')
 if a.dry_run:print(dict(attempts=len(roster)+3,lp_attempts=len(roster),micro_jobs=3,reservations=totals,acceptance=700));return
 d,identity=freeze(v)
 if a.prepare:return
 from lp_tensor_residual_accept import check_acceptance
 check_acceptance(v,identity);admission=read_json(ROOT/'docs/benchmarks/data/tensor-residual/cpu-admission.json');eligible={(r['model'],r['configuration']):r['eligible'] for r in admission['rows']}
 with ledger_for(v) as ledger:
  recover(d,ledger)
  for j in roster:
   if j['id'] in ledger.attempted() or (d/(j['id']+'.trial.json')).exists():continue
   if not eligible[(j['instance']['id'],j['configuration']['id'])]:
    write_json(d/(j['id']+'.trial.json'),dict(id=j['id'],job=j,status='cpu_admission_refusal',assessment=None,charged_ns=0));continue
   run_trial(v,j,d,ledger,identity)
  run_microprofiles(v,d,ledger,identity)
  shutil.copy2(ledger.path,d/'ledger.jsonl')
if __name__=='__main__':main()
