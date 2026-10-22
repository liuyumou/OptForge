"""Final source-frozen CPU admission, retaining the first admission cohort intact."""
import concurrent.futures as cf,json,resource,shutil,subprocess,time
from lp_protocol import ROOT,read_json,write_json,file_hash,checked_reference
from benchmark_lp import provenance,prepare_execution,reference
from lp_quant_admission import configs
from lp_quant_oracle import codec,products,PROBE

def main():
 start=time.monotonic();before=resource.getrusage(resource.RUSAGE_CHILDREN);out=ROOT/'artifacts/gpup-quant-v1/final-admission';out.mkdir(parents=True,exist_ok=False);binary=ROOT/'target/release/examples/lp_precision_quant';v=read_json(ROOT/'benchmarks/configs/lp-exec-v1.json');native=provenance(binary,v['device']);native['build_profile']='release';prepare_execution(out,native);identity=read_json(out/'execution.json');frozen=out/'lp_precision_quant';shutil.copy2(binary,frozen);shutil.copy2(PROBE,out/'quant_probe')
 oracle=dict(identity='gpup-quant-final-oracle-v1',status='passed',codec_cases=codec(),original_unit_product_components=products(),probe_sha256=file_hash(PROBE),gpu_seconds=0);write_json(out/'oracle.json',oracle)
 models={i['id']:i for ref in v['manifests'] for i in read_json(checked_reference(ROOT,ref))['instances']};roster=[(name,c) for name in v['timing_instances'] for c in configs()]
 def run(item):
  name,c=item;d=out/(name+'-'+c['id']);d.mkdir();model=checked_reference(ROOT,models[name]['model']);request=dict(schema_version=1,identity='lp-quant-v1',settings=c['settings'],model_sha256=file_hash(model),source_tree_sha256=identity['source_tree_sha256'],executable_sha256=file_hash(frozen),code_object_sha256=file_hash(ROOT/'target/native/cuda/lp_pdhg_quant.cubin'),device=v['device'],options=dict(v['solve'],iteration_limit=200,time_limit_ms=30000),method=dict(v['lp_settings'],iteration_limit=200),diagnostic=True,device_buffer_bytes=1<<30);write_json(d/'request.json',request)
  prep=subprocess.run([str(out/'quant_probe'),'prepare',str(model),json.dumps(dict(settings=c['settings']))],capture_output=True,text=True,timeout=240);(d/'preparation.stdout').write_text(prep.stdout);(d/'preparation.stderr').write_text(prep.stderr)
  if prep.returncode:
   if not any(reason in prep.stderr for reason in ['preparation_memory_limit','scale_range','bound_range','operator_step_range','scaling_error_range']):raise ValueError('unexpected preparation failure '+prep.stderr)
   return dict(model=name,configuration=c['id'],eligible=False,status='preparation_refusal')
  preparation=json.loads(prep.stdout);r=subprocess.run([str(frozen),'trace-cpu',str(model),str(d/'request.json'),str(d/'endpoint.json')],capture_output=True,text=True,timeout=1200);(d/'stdout').write_text(r.stdout);(d/'stderr').write_text(r.stderr)
  if r.returncode:raise ValueError('final CPU execution failure '+r.stderr)
  e=read_json(d/'endpoint.json');o=e['outcome'];check=subprocess.run([str(frozen),'verify',str(model),str(d/'request.json'),str(d/'endpoint.json')],capture_output=True,text=True,timeout=240);(d/'verify.stdout').write_text(check.stdout);(d/'verify.stderr').write_text(check.stderr)
  if check.returncode:raise ValueError('final CPU verification failure '+check.stderr)
  row=dict(model=name,configuration=c['id'],eligible=o['stop'] not in ['numerical_failure','device_failure','time_limit','interrupted'],status=o['stop'],iterations=o['iterations'],physical=o['physical'],low_products=o['work']['low_products'],native=o['promotion']['native'],failure=o['failure'],preparation=preparation,endpoint=reference(ROOT,d/'endpoint.json'));print(name,c['id'],row['status'],flush=True);return row
 # Three simultaneous CPU children leave one slot for the retained first cohort.
 with cf.ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(run,roster))
 after=resource.getrusage(resource.RUSAGE_CHILDREN);result=dict(identity='gpup-quant-final-admission-v1',status='passed',gpu_seconds=0,source_tree_sha256=identity['source_tree_sha256'],source_archive=reference(ROOT,out/'source.tar'),executable_sha256=file_hash(frozen),oracle=reference(ROOT,out/'oracle.json'),rows=rows,cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,elapsed_seconds=time.monotonic()-start,max_child_rss_bytes=after.ru_maxrss*1024);write_json(out/'admission.json',result)
 print({k:result[k] for k in ['status','cpu_seconds','elapsed_seconds','max_child_rss_bytes']})
if __name__=='__main__':main()
