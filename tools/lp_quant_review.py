"""CPU-only report-reader review; measured execution and host authority stay exact."""
import difflib,hashlib,tarfile
from pathlib import Path
from lp_protocol import ROOT,read_json,write_json,file_hash,checked_reference
from benchmark_lp import reference
RECEIPT=ROOT/'docs/benchmarks/data/quant/cpu-review-source.json'
CHANGED=['tools/report_lp_quant.py','tests/integration/test_lp_quant.py']
EXACT=['crates/optimizer-lp/src/quant.rs','crates/optimizer-lp-cuda/src/quant.rs','crates/optimizer-experiment/src/lp_quant.rs','crates/optimizer-experiment/examples/lp_precision_quant.rs','cuda/lp_pdhg_quant/lp_pdhg_quant.cu','tools/benchmark_lp_quant.py','tools/lp_quant_budget.py','tools/lp_quant_accept.py']
def create():
 d=ROOT/'artifacts/gpup-quant-v1';out=d/'cpu-review';out.mkdir(parents=True,exist_ok=True);files=[];exact=[]
 with tarfile.open(d/'study/source.tar') as a:
  for name in EXACT:
   before=a.extractfile(name).read();assert before==(ROOT/name).read_bytes(),name;exact.append(dict(path=name,sha256=hashlib.sha256(before).hexdigest()))
  for name in CHANGED:
   before=a.extractfile(name).read();after=(ROOT/name).read_bytes();bp=out/'before'/name;ap=out/'after'/name;dp=out/(Path(name).name+'.diff');bp.parent.mkdir(parents=True,exist_ok=True);ap.parent.mkdir(parents=True,exist_ok=True)
   if bp.exists() and bp.read_bytes()!=before:raise ValueError('original review source differs')
   bp.write_bytes(before);ap.write_bytes(after);dp.write_text(''.join(difflib.unified_diff(before.decode().splitlines(keepends=True),after.decode().splitlines(keepends=True),fromfile=name+' (measured)',tofile=name+' (reviewed)')))
   files.append(dict(path=name,before=reference(ROOT,bp),after=reference(ROOT,ap),diff=reference(ROOT,dp),reviewed_sha256=file_hash(ROOT/name)))
 r=dict(identity='gpup-quant-cpu-review-v1',gpu_seconds=0,additional_gpu_seconds=0,tool_sha256=file_hash(ROOT/'tools/lp_quant_review.py'),source_archive=reference(ROOT,d/'study/source.tar'),original_report=reference(ROOT,d/'report.json'),original_markdown=reference(ROOT,d/'report-original.md'),files=files,unchanged_execution=exact);write_json(RECEIPT,r);return r
def verify():
 r=read_json(RECEIPT)
 if r['identity']!='gpup-quant-cpu-review-v1' or r['gpu_seconds']!=0 or r['additional_gpu_seconds']!=0 or r['tool_sha256']!=file_hash(ROOT/'tools/lp_quant_review.py') or [f['path'] for f in r['files']]!=CHANGED or [f['path'] for f in r['unchanged_execution']]!=EXACT:raise ValueError('quant CPU review authority')
 checked_reference(ROOT,r['source_archive']);checked_reference(ROOT,r['original_report']);checked_reference(ROOT,r['original_markdown'])
 for f in r['files']:
  for k in ['before','after','diff']:checked_reference(ROOT,f[k])
  if file_hash(ROOT/f['path'])!=f['reviewed_sha256']:raise ValueError('undeclared reader source change')
 for f in r['unchanged_execution']:
  if file_hash(ROOT/f['path'])!=f['sha256']:raise ValueError('measured execution changed '+f['path'])
 return r
if __name__=='__main__':create();verify();print('CPU-only reader review bound; measured runtime/executable/image cohorts unchanged')
