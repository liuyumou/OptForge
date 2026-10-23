"""Bind final CPU admission to the sole pre-device lifetime-only source change."""
import hashlib,tarfile
from pathlib import Path
from lp_protocol import ROOT,read_json,write_json,file_hash,checked_reference
from benchmark_lp import reference
RECEIPT=ROOT/'docs/benchmarks/data/quant/cpu-source-bridge.json'
FILES=['crates/optimizer-lp/src/quant.rs','crates/optimizer-lp-cuda/src/quant.rs','crates/optimizer-experiment/src/lp_quant.rs']
INSERT='''    // Independent self-verification prepares a new operator. Release the solve's
    // preparation first so the admitted peak cannot contain two live operators.
    drop(op);
    drop(engine);
    drop(p);
    drop(model);
'''
def create():
 d=ROOT/'artifacts/gpup-quant-v1/final-admission';a=read_json(d/'admission.json');rows=[]
 with tarfile.open(d/'source.tar') as archive:
  for name in FILES:
   old=archive.extractfile(name).read();new=(ROOT/name).read_bytes();expected=old
   if name.endswith('lp_quant.rs'):
    expected=old.replace(b'    e.verify(bytes, &e.request)?;',INSERT.encode()+b'    e.verify(bytes, &e.request)?;')
   if expected!=new:raise ValueError('non-lifetime CPU admission source change '+name)
   rows.append(dict(path=name,admitted_sha256=hashlib.sha256(old).hexdigest(),reviewed_sha256=file_hash(ROOT/name),change='identical' if old==new else 'release preparation before self-verification'))
 receipt=dict(identity='gpup-quant-cpu-source-bridge-v1',gpu_seconds=0,admission=reference(ROOT,d/'admission.json'),source_archive=reference(ROOT,d/'source.tar'),tool_sha256=file_hash(ROOT/'tools/lp_quant_cpu_bridge.py'),files=rows)
 write_json(RECEIPT,receipt);return receipt
def verify():
 r=read_json(RECEIPT)
 if r['identity']!='gpup-quant-cpu-source-bridge-v1' or r['gpu_seconds']!=0 or r['tool_sha256']!=file_hash(ROOT/'tools/lp_quant_cpu_bridge.py') or [f['path'] for f in r['files']]!=FILES:raise ValueError('CPU source bridge authority')
 checked_reference(ROOT,r['admission']);archive=checked_reference(ROOT,r['source_archive'])
 with tarfile.open(archive) as a:
  for f in r['files']:
   old=a.extractfile(f['path']).read();new=(ROOT/f['path']).read_bytes();expected=old if f['change']=='identical' else old.replace(b'    e.verify(bytes, &e.request)?;',INSERT.encode()+b'    e.verify(bytes, &e.request)?;')
   if hashlib.sha256(old).hexdigest()!=f['admitted_sha256'] or file_hash(ROOT/f['path'])!=f['reviewed_sha256'] or new!=expected:raise ValueError('CPU source bridge differs '+f['path'])
 return r
if __name__=='__main__':create();verify();print('final CPU arithmetic exact; only preparation lifetime changes before device work')
