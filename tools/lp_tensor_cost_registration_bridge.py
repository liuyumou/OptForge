"""Retain exact earlier registration bytes; never rewrite historical receipts."""
import difflib
import hashlib
import subprocess
from lp_protocol import ROOT,read_json,write_json,file_hash

ALLOWED={'crates/optimizer-lp/src/lib.rs','crates/optimizer-lp-cuda/src/lib.rs',
 'crates/optimizer-experiment/src/lib.rs','crates/optimizer-experiment/Cargo.toml',
 'tools/check.sh','tests/integration/test_lp_quant_pr_review.py'}

def main():
 prior=read_json(ROOT/'docs/benchmarks/data/tensor-residual/prerequisite-source-bridge.json')
 directory=ROOT/'docs/benchmarks/data/tensor-cost/prerequisite-prior'
 directory.mkdir(parents=True,exist_ok=True);rows=[]
 for row in prior['files']:
  path=row['path'];current=(ROOT/path).read_bytes();before=row['after_sha256'];after=file_hash(ROOT/path)
  if before==after:continue
  if path not in ALLOWED:raise ValueError('unapproved historical source change: '+path)
  old=subprocess.check_output(['git','show','HEAD:'+path],cwd=ROOT)
  if hashlib.sha256(old).hexdigest()!=before:raise ValueError('prior committed bytes differ: '+path)
  if path.endswith('lib.rs'):
   # These are module registrations. Every original line stays exact and ordered.
   for tag,a,b,c,d in difflib.SequenceMatcher(None,old.splitlines(),current.splitlines()).get_opcodes():
    if tag not in ['equal','insert']:raise ValueError('historical Rust body changed: '+path)
    if tag=='insert':
     allowed={b'',b'pub mod tensor_cost;',b'pub mod lp_tensor_cost;',b'mod tensor_cost_prepare;'}
     allowed.update(line for line in old.splitlines() if line.startswith(b'#[cfg('))
     if any(line not in allowed and not line.startswith(b'///') for line in current.splitlines()[c:d]):raise ValueError('unapproved Rust registration: '+path)
  frozen=directory/(before+'.txt')
  if frozen.exists() and frozen.read_bytes()!=old:raise ValueError('immutable prior source differs')
  if not frozen.exists():frozen.write_bytes(old)
  rows.append(dict(path=path,before_sha256=before,after_sha256=after,frozen_path=str(frozen.relative_to(ROOT))))
 destination=directory.parent/'prerequisite-source-bridge.json'
 result=dict(identity='gpup-tensor-cost-prerequisite-source-bridge-v1',gpu_seconds=0,scope='isolated module/example registration and portable acceptance guard; historical numerical bodies unchanged',files=rows)
 if destination.exists() and read_json(destination)!=result:raise ValueError('registration bridge already exists')
 if not destination.exists():write_json(destination,result)
 print('Retained',len(rows),'registration/acceptance source bridges')

if __name__=='__main__':main()
