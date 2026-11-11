"""Publish compact local integration evidence without altering retained records."""
import gzip,hashlib,json,statistics
from pathlib import Path
from lp_fp4_integrate_common import ROOT,BASE,put,ref,load,require
from lp_fp4_recovery_contract import digest

def main():
 out=ROOT/'docs/benchmarks/data';d=load(BASE/'diagnostic-v1/result.json');p=load(BASE/'performance-v1/result.json');analysis=load(BASE/'analysis-v1.json');replay=load(BASE/'replay-v1/result.json');require(replay['status']=='passed','replay refusal')
 models={};endpoints={};cells=[]
 for grid in ('diagnostic-v1','performance-v1'):
  for row in load(BASE/grid/'result.json')['rows']:
   r=load(ROOT/row['result']['path'])
   for name in ('model','final_checkpoint','binary','image'):require(ref(ROOT/r[name]['path'])==r[name],'changed cell binding')
   cert=load(ROOT/r['certificate']['certificate']['path']);key=digest(dict(model=cert['model_sha256'],endpoint=cert['endpoint_sha256'],tier=r['tier']))
   models[cert['model_sha256']]=(ROOT/r['model']['path']).read_text()
   endpoints[key]=dict(original_model_sha256=cert['model_sha256'],endpoint_bytes=(ROOT/r['certificate']['endpoint']['path']).read_text(),certificate=cert)
   cells.append(dict(grid=grid,id=row['id'],key=key))
 payload=dict(schema_version=1,models_utf8=models,endpoints=endpoints,cells=cells,independent_replay=ref(BASE/'replay-v1/result.json'))
 raw=(json.dumps(payload,indent=2,sort_keys=True)+'\n').encode();archive=out/'fp4-integrate-endpoints-v1.json.gz'
 with archive.open('xb') as stream:stream.write(gzip.compress(raw,compresslevel=9,mtime=0))
 put(out/'fp4-integrate-endpoints-v1.json',dict(schema_version=1,format='gzip-compressed UTF-8 JSON',payload=ref(archive),uncompressed_sha256=hashlib.sha256(raw).hexdigest(),models=len(models),unique_endpoints=len(endpoints),formal_cells=len(cells)))
 put(out/'fp4-integrate-results-v1.json',dict(schema_version=1,diagnostic=d,performance=p,analysis=analysis,manifests={grid:load(BASE/grid/'manifest.json') for grid in ('diagnostic-v1','performance-v1')}))
 failures=[];resources=[];peak=0
 for path in sorted((BASE/'resources').glob('*.settlement.json')):
  s=load(path);resource=load(ROOT/s['resource']['path']);require(resource['guardian_cleanup']['empty'] and resource['result']['cleanup']['empty'],'nonempty cleanup')
  peak=max(peak,resource['result']['peak_rss_bytes']);resources.append(dict(job=path.stem.replace('.settlement',''),settlement=ref(path)))
  if s['status']!='passed':failures.append(dict(job=path.stem.replace('.settlement',''),settlement=s,log=ref(Path(str(ROOT/s['resource']['path'])+'.log'))))
 evidence=dict(schema_version=1,status='passed',admission=load(BASE/'admission-v1.json'),replay=ref(BASE/'replay-v1/result.json'),replayed_cells=len(replay['cells']),unique_endpoints=replay['unique_endpoints'],ablation=load(BASE/'cached-pairs-ablation-v1/result.json'),binary_archives=load(BASE/'binary-archive-verified-v1.json'),failures=failures,resources=resources,sampled_peak_host_rss_bytes=peak,accounting='Final charges and cleanup are in fp4-integrate-accounting-v1.json; no publication or historical retry.',diagnostic_certified=sum(r['certified'] for r in d['rows']),performance_certified=sum(r['certified'] for r in p['rows']))
 put(out/'fp4-integrate-evidence-v1.json',evidence)
 print(dict(status='passed',published_endpoints=len(endpoints),models=len(models),peak_rss_bytes=peak))
if __name__=='__main__':main()
