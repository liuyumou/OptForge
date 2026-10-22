"""Bind pre-sanitizer acceptance to the unchanged resident numerical cohort."""
import hashlib,tarfile
from pathlib import Path
from lp_protocol import ROOT,read_json,write_json,file_hash,checked_reference
from benchmark_lp import reference
from lp_quant_resident_common import numeric_sources
RECEIPT=ROOT/'docs/benchmarks/data/quant-resident/acceptance-source-bridge.json'
ALLOWED={'tools/lp_quant_resident_gpu_check.sh','tools/lp_quant_resident_accept.py','tools/lp_quant_resident_budget.py','tools/report_lp_quant_resident.py','tools/lp_quant_resident_bridge.py','benchmarks/configs/lp-quant-resident-v1.json','schemas/lp-quant-resident-study-v1.schema.json'}
def create():
 d=ROOT/'artifacts/gpup-quant-resident-v1/study';identity=read_json(d/'execution.json');changed=[];exact=[]
 with tarfile.open(d/'source.tar') as archive:
  original={m.name:archive.extractfile(m).read() for m in archive.getmembers()}
 for name in sorted(set(original)|ALLOWED):
  if not name.startswith(('crates/','cuda/','tools/','schemas/','benchmarks/configs/')):continue
  p=ROOT/name;before=original.get(name);after=p.read_bytes() if p.is_file() else None
  if before!=after or name in {'benchmarks/configs/lp-quant-resident-v1.json','schemas/lp-quant-resident-study-v1.schema.json'}:
   if name not in ALLOWED:raise ValueError('unapproved acceptance bridge change '+name)
   changed.append(dict(path=name,before_sha256=None if before is None else hashlib.sha256(before).hexdigest(),after_sha256=None if after is None else hashlib.sha256(after).hexdigest()))
  else:exact.append(dict(path=name,sha256=hashlib.sha256(before).hexdigest()))
 if not any(r['path']=='tools/lp_quant_resident_gpu_check.sh' for r in changed):raise ValueError('sanitizer scope change absent')
 a=read_json(ROOT/'docs/benchmarks/data/quant-resident/cpu-admission.json')
 if numeric_sources()!=a['numerical_sources'] or file_hash(d/'lp_precision_quant_resident')!=a['executable_sha256']:raise ValueError('numerical acceptance cohort changed')
 r=dict(identity='gpup-quant-resident-acceptance-source-bridge-v1',status='passed',gpu_seconds=0,before_source_tree_sha256=identity['source_tree_sha256'],before_archive=reference(ROOT,d/'source.tar'),before_protocol=reference(ROOT,d/'campaign.json'),numerical_sources=numeric_sources(),executable_sha256=file_hash(d/'lp_precision_quant_resident'),image_sha256=file_hash(d/'lp_pdhg_quant_resident.cubin'),changed=changed,unchanged_execution=exact,reason='Broaden pending sanitizer filter to include controller/update windows; retain ordinary/project jobs without retry. Reader accepts their exact source cohort. No arithmetic, limits, requests, or endpoints change.')
 write_json(RECEIPT,r);return r
def verify():
 r=read_json(RECEIPT)
 if r['status']!='passed' or r['gpu_seconds'] or r['numerical_sources']!=numeric_sources() or any(f['path'] not in ALLOWED for f in r['changed']):raise ValueError('resident acceptance bridge identity')
 checked_reference(ROOT,r['before_archive']);checked_reference(ROOT,r['before_protocol'])
 # Protocol/schema references to this receipt are necessarily filled afterward;
 # frozen campaign/schema copies and the native source gate bind those bytes.
 for f in r['changed']:
  if f['path'] not in {'benchmarks/configs/lp-quant-resident-v1.json','schemas/lp-quant-resident-study-v1.schema.json'} and file_hash(ROOT/f['path'])!=f['after_sha256']:raise ValueError('resident bridge source changed '+f['path'])
 for f in r['unchanged_execution']:
  if file_hash(ROOT/f['path'])!=f['sha256']:raise ValueError('resident measured execution changed '+f['path'])
 return r['before_source_tree_sha256']
if __name__=='__main__':create();verify();print('Pre-sanitizer source cohort bound; numerical/executable/image bodies unchanged.')
