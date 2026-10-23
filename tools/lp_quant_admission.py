"""CPU-only original-unit quantizer admission on the eight frozen executor models."""
import json,subprocess,time,resource,shutil
from benchmark_lp import source_identity,reference
from lp_protocol import ROOT,read_json,write_json,checked_reference,file_hash
from lp_quant_oracle import main as oracle_main
FORMATS=['fp16','e4m3','e5m2']
def settings(fmt,policy):return dict(format=fmt,policy=policy,tile_size=32,rounding='nearest_even',primal_budget=1e-7,dual_budget=1e-7,audit_interval=32,audit_absolute=1e-7,audit_relative=1e-7)
def configs():return [dict(id=f+'-'+p,backend='lp-quant-v1',settings=settings(f,p)) for f in FORMATS for p in ['uniform','selective']]+[dict(id='matched-fp64',backend='lp-quant-v1',settings=settings('fp64','uniform'))]
def main():
 oracle_main();start=time.monotonic();before=resource.getrusage(resource.RUSAGE_CHILDREN);out=ROOT/'artifacts/gpup-quant-v1/cpu-admission';out.mkdir(parents=True,exist_ok=False)
 binary=ROOT/'target/release/examples/lp_precision_quant';frozen=out/'lp_precision_quant';shutil.copy2(binary,frozen);probe=ROOT/'target/release/examples/quant_probe';shutil.copy2(probe,out/'quant_probe')
 parent=read_json(ROOT/'benchmarks/configs/lp-exec-v1.json');models={i['id']:i for ref in parent['manifests'] for i in read_json(checked_reference(ROOT,ref))['instances']};rows=[];source=source_identity()
 for name in parent['timing_instances']:
  for c in configs():
   d=out/(name+'-'+c['id']);d.mkdir();model=checked_reference(ROOT,models[name]['model'])
   req=dict(schema_version=1,identity='lp-quant-v1',settings=c['settings'],model_sha256=models[name]['model']['sha256'],source_tree_sha256=source,executable_sha256=file_hash(frozen),code_object_sha256=file_hash(ROOT/'target/native/cuda/lp_pdhg_quant.cubin'),device=parent['device'],options=dict(parent['solve'],iteration_limit=200,time_limit_ms=30000),method=dict(parent['lp_settings'],iteration_limit=200),diagnostic=True,device_buffer_bytes=1<<30)
   write_json(d/'request.json',req);cmd=[str(frozen),'trace-cpu',str(model),str(d/'request.json'),str(d/'endpoint.json')]
   r=subprocess.run(cmd,capture_output=True,text=True,timeout=1200);(d/'stdout').write_text(r.stdout);(d/'stderr').write_text(r.stderr)
   row=dict(model=name,configuration=c['id'],eligible=False,status='preparation_refusal',returncode=r.returncode)
   if r.returncode==0:
    e=read_json(d/'endpoint.json');o=e['outcome'];row.update(status=o['stop'],eligible=o['stop'] not in ['numerical_failure','device_failure','interrupted','time_limit'],iterations=o['iterations'],physical=o['physical'],low_products=o['work']['low_products'],native=o['promotion']['native'],failure=o['failure'],endpoint=reference(ROOT,d/'endpoint.json'))
    v=subprocess.run([str(frozen),'verify',str(model),str(d/'request.json'),str(d/'endpoint.json')],capture_output=True,text=True,timeout=1200)
    if v.returncode:raise ValueError('CPU endpoint verification failed '+v.stderr)
   elif 'quant outcome' in r.stderr or 'panic' in r.stderr:raise ValueError('CPU admission implementation failure '+r.stderr)
   rows.append(row);print(name,c['id'],row['status'],flush=True)
 after=resource.getrusage(resource.RUSAGE_CHILDREN);v=dict(identity='gpup-quant-admission-v1',status='passed',rows=rows,gpu_seconds=0,elapsed_seconds=time.monotonic()-start,cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,max_child_rss_bytes=after.ru_maxrss*1024,source_tree_sha256=source,executable_sha256=file_hash(frozen),oracle=reference(ROOT,ROOT/'artifacts/gpup-quant-v1/admission/oracle.json'))
 write_json(out/'admission.json',v);dest=ROOT/'docs/benchmarks/data/quant';dest.mkdir(parents=True,exist_ok=True);write_json(dest/'cpu-admission.json',v)
if __name__=='__main__':main()
