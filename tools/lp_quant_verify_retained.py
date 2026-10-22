"""Fresh CPU-only verification of study, acceptance/replay and both CPU cohorts."""
import concurrent.futures as cf,json,subprocess,time
from lp_protocol import ROOT,read_json,write_json,checked_reference,file_hash
from lp_quant_budget import protocol

def main():
 v=protocol();study=ROOT/v['output'];models={i['model']['sha256']:checked_reference(ROOT,i['model']) for ref in v['manifests'] for i in read_json(checked_reference(ROOT,ref))['instances']};binary=study/'lp_precision_quant';tasks=[]
 for path in sorted(study.glob('*.trial.json')):
  t=read_json(path);j=t['job'];key=t['id'];ep=study/(key+'.endpoint.json')
  if not ep.exists():continue
  if j['configuration']['backend']=='lp-quant-v1':tasks.append(('study',ep,study/(key+'.quant-request.json')))
  else:tasks.append(('control',ep,checked_reference(ROOT,j['instance']['model'])))
 a=read_json(ROOT/v['acceptance_output']/'project/acceptance.json')
 for row in a['rows']:
  original=checked_reference(ROOT,row['endpoint']);request=original.with_name(original.name.replace('.endpoint.json','.request.json'))
  tasks.extend([('acceptance',original,request),('replay',checked_reference(ROOT,row['replay']),request)])
 for cohort in ['cpu-admission','final-admission']:
  d=ROOT/'artifacts/gpup-quant-v1'/cohort
  for row in read_json(d/'admission.json')['rows']:
   if row.get('endpoint'):ep=checked_reference(ROOT,row['endpoint']);tasks.append((cohort,ep,ep.with_name('request.json')))
 if len(tasks)!=182:raise ValueError('retained endpoint roster differs '+str(len(tasks)))
 out=ROOT/'artifacts/gpup-quant-v1/retained-verification';out.mkdir(parents=True,exist_ok=False);start=time.monotonic()
 def check(item):
  kind,ep,arg=item
  if kind=='control':command=[str(study/'optimizer'),'lp-study','verify','--model',str(arg),'--model-byte-limit',str(v['model_byte_limit']),'--evidence',str(ep)]
  else:
   request=read_json(arg);model=models[request['model_sha256']];command=[str(binary),'verify',str(model),str(arg),str(ep)]
  r=subprocess.run(command,capture_output=True,text=True,timeout=240);stem=str(ep.relative_to(ROOT)).replace('/','_');(out/(stem+'.stdout')).write_text(r.stdout);(out/(stem+'.stderr')).write_text(r.stderr)
  row=dict(kind=kind,endpoint=str(ep.relative_to(ROOT)),endpoint_sha256=file_hash(ep),returncode=r.returncode)
  if r.returncode:raise ValueError('retained verification failed '+str(ep)+' '+r.stderr[:1000])
  return row
 with cf.ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(check,tasks))
 result=dict(identity='gpup-quant-retained-verification-v1',status='passed',gpu_seconds=0,rows=rows,endpoints=len(rows),elapsed_seconds=time.monotonic()-start,verifier_sha256=file_hash(binary),control_verifier_sha256=file_hash(study/'optimizer'));write_json(out/'verification.json',result);print({k:result[k] for k in ['status','endpoints','elapsed_seconds','gpu_seconds']})
if __name__=='__main__':main()
