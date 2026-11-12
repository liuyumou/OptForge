"""Final readback, source preservation and cleanup checks; no numerical execution."""
import ast,gzip,hashlib,json,os
from pathlib import Path
from lp_fp4_integrate_common import ROOT,BASE,load,ref,require,put

def verify():
 for p in (ROOT/'tools').glob('*fp4_integrate*.py'):ast.parse(p.read_text(),filename=str(p))
 for name in ('diagnostic-v1','performance-v1'):
  manifest=load(BASE/name/'manifest.json')
  require(ref(BASE/name/'manifest.json')==load(BASE/name/'freeze-receipt.json')['manifest'],'manifest changed')
  for binding in manifest['sources']+[manifest['binary'],manifest['image']]:require(ref(ROOT/binding['path'])==binding,'frozen source changed')
 navigation={'AGENTS.md','state/active-task.md','state/backlog.yaml','docs/plans/gpu-lp-precision-roadmap.md'}
 history=load(BASE/'history.json')
 for binding in history['files']:
  if binding['path'] not in navigation:require(ref(ROOT/binding['path'])==binding,'history changed')
 index=load(ROOT/'docs/benchmarks/data/fp4-integrate-endpoints-v1.json');require(ref(ROOT/index['payload']['path'])==index['payload'],'endpoint archive changed')
 raw=gzip.decompress((ROOT/index['payload']['path']).read_bytes());require(hashlib.sha256(raw).hexdigest()==index['uncompressed_sha256'],'decompression changed payload');data=json.loads(raw)
 require(len(data['models_utf8'])==8 and len(data['endpoints'])==176 and len(data['cells'])==672,'endpoint archive coverage')
 for digest,value in data['models_utf8'].items():require(hashlib.sha256(value.encode()).hexdigest()==digest,'original model bytes changed')
 receipts=[]
 for p in (BASE/'resources').glob('*.settlement.json'):
  s=load(p);require(not s['overrun'],'overrun');r=load(ROOT/s['resource']['path']);require(r['guardian_cleanup']['empty'] and r['result']['cleanup']['empty'],'nonempty supervisor cleanup');receipts.append(ref(p))
 active=[]
 for path in Path('/proc').glob('[0-9]*/exe'):
  try:
   if os.readlink(path).endswith('/lp-fp4-integrate'):
    active.append(int(path.parent.name))
  except (FileNotFoundError,PermissionError,ProcessLookupError):pass
 require(not active,'integration service remains')
 result=dict(status='passed',historical_files=len(history['files']),frozen_cells=672,original_models=8,unique_endpoints=176,active_service_pids=active,settled_receipts=receipts)
 put(BASE/'final-readback-v1.json',result);print(dict(status='passed',historical_files=len(history['files']),active_service_pids=active))
if __name__=='__main__':verify()
