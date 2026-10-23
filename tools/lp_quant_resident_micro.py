"""Frozen independent-product diagnostics, never LP timings or certificates."""
import os,subprocess,math
from lp_protocol import ROOT,read_json,write_json,checked_reference,file_hash,ordered
from lp_quant_resident_admission import make_request
def prepare(v,d,identity):
 admission=read_json(checked_reference(ROOT,v['cpu_admission']));name='gpup-extension-irregular-32768';row=next(r for r in admission['rows'] if r['model']==name and r['configuration']=='resident-matched-fp64');point=read_json(checked_reference(ROOT,row['endpoint']))['outcome']['core'];vectors=[]
 for kind in ['synthetic','recorded']:
  for t in [False,True]:
   values=point['scaled_dual' if t else 'scaled_primal']
   if kind=='synthetic':values=[(-1. if i%3==0 else 1.)*math.ldexp(1+(i%7)/8,-30) for i in range(len(values))]
   vectors.append(dict(name=kind+('-dual' if t else '-primal'),transpose=t,values=values))
 from benchmark_lp_quant_resident import instances
 model=checked_reference(ROOT,instances(v)[name]['model']);doc=dict(schema_version=1,model_sha256=file_hash(model),vectors=vectors);path=d/'micro-vectors.json'
 if path.exists() and read_json(path)!=doc:raise ValueError('resident frozen micro vectors differ')
 if not path.exists():write_json(path,doc)
 directory=d/'micro';directory.mkdir(exist_ok=True)
 for mode in ['fused','product','guard']:
  for c in v['configurations'][:7]:
   r=make_request(c,model,d/'lp_precision_quant_resident',identity['source_tree_sha256'],work=50000,horizon=16,seconds=30);r['code_object_sha256']=identity['code_object_sha256'];request=dict(request=r,vectors_sha256=file_hash(path),mode=mode,products=16);p=directory/(mode+'-'+c['id']+'.request.json')
   if p.exists() and read_json(p)!=request:raise ValueError('resident frozen micro request differs')
   if not p.exists():write_json(p,request)
def verify_available(v,d,mode):
 from benchmark_lp_quant_resident import instances
 name='gpup-extension-irregular-32768';model=checked_reference(ROOT,instances(v)[name]['model']);rows=[]
 for c in v['configurations'][:7]:
  stem=mode+'-'+c['id'];ep=d/'micro'/(stem+'.endpoint.json');rp=d/'micro'/(stem+'.request.json')
  if not ep.exists():continue
  r=subprocess.run([str(d/'lp_precision_quant_resident'),'micro-verify',str(model),str(rp),str(d/'micro-vectors.json'),str(ep)],capture_output=True,text=True,timeout=v['verification_seconds']);(d/'micro'/(stem+'.verify.stdout')).write_text(r.stdout);(d/'micro'/(stem+'.verify.stderr')).write_text(r.stderr)
  if r.returncode or r.stdout.strip()!='verified':raise ValueError('resident micro witness rejection '+r.stderr[:2000])
  rows.append(dict(configuration=c['id'],endpoint_sha256=file_hash(ep),verified=True))
 write_json(d/'micro'/(mode+'.verification.json'),dict(mode=mode,rows=rows,complete=len(rows)==7))
 return rows
def main():
 import sys
 from lp_quant_resident_budget import protocol
 from benchmark_lp_quant_resident import instances
 v=protocol();d=ROOT/v['output'];mode=sys.argv[1]
 if mode not in ['fused','product','guard'] or os.environ.get('AI_OPTIMIZER_GPU_LEASE')!='inherited' or os.environ.get('CUDA_VISIBLE_DEVICES')!=v['device']:raise ValueError('resident selected diagnostic lease/mode required')
 identity=read_json(d/'execution.json');name='gpup-extension-irregular-32768';model=checked_reference(ROOT,instances(v)[name]['model'])
 for c in ordered(v['configurations'][:7],v['order_seed'],'micro:'+mode,0):
  stem=mode+'-'+c['id'];rp=d/'micro'/(stem+'.request.json');ep=d/'micro'/(stem+'.endpoint.json')
  if ep.exists():raise ValueError('resident micro cannot retry')
  r=subprocess.run([str(d/'lp_precision_quant_resident'),'micro-solve',str(model),str(rp),str(d/'micro-vectors.json'),str(ep)],capture_output=True,text=True,timeout=30);(d/'micro'/(stem+'.stdout')).write_text(r.stdout);(d/'micro'/(stem+'.stderr')).write_text(r.stderr)
  if r.returncode:raise ValueError('resident micro execution failed '+r.stderr[:2000])
 print('seven operator diagnostic configurations completed; no LP certification',flush=True)
if __name__=='__main__':main()
