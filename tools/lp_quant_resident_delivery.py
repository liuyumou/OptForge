"""CPU-only final bindings for all retained GPUP-7R source/binary cohorts."""
import hashlib,tarfile
from pathlib import Path
from lp_protocol import ROOT,read_json,write_json,file_hash,checked_reference
from benchmark_lp import reference,source_identity
from lp_quant_resident_budget import protocol
from lp_quant_resident_bridge import verify as bridge

def metadata(e):
 """Check physical submissions and conservative transfer bounds independently."""
 if e['executor']!='gpu':return
 o=e['outcome'];c=o['counts'];w=o['core']['work'];windows=c['windows'];size=len(o['core']['primal'])+len(o['core']['dual'])
 if c['predicated']>31*windows or e['host_product_scans'] or e['product_vector_transfers']:raise ValueError('nonresident or inconsistent predicated work')
 if o['counts']['uncertain']==0 and o['core']['failure'] is None:
  slots=w['proposals']+c['predicated'];per=6 if o['layout']=='original_tuned' else 9 if o['layout']=='tuned' else 7
  expected=per*slots+(0 if o['layout']=='original_tuned' else 2*windows)
  if e['launches']!=expected:raise ValueError('inconsistent physical launch count')
 if e['launches']>10*(w['proposals']+c['predicated'])+2*windows:raise ValueError('oversized launch counter')
 # Initial buffers, at most ten promotion generations, and full state/anchor
 # uploads at every window conservatively bound all possible HtoD traffic.
 upload=e['device_peak_bytes']+10*(4*len(o['core']['promotion']['mask'])+24*max(size,1))+64*max(size,1)*windows
 readback=(88+32*max(size,1))*windows
 if e['upload_bytes']>upload or e['readback_bytes']>readback:raise ValueError('oversized transfer counter')

def archive_digest(path):
 digest=hashlib.sha256()
 with tarfile.open(path) as archive:
  members=archive.getmembers();names=[m.name for m in members]
  if names!=sorted(set(names)) or any(not m.isfile() or Path(m.name).is_absolute() or '..' in Path(m.name).parts for m in members):raise ValueError('invalid source archive')
  for m in members:digest.update(m.name.encode()+b'\0'+archive.extractfile(m).read()+b'\0')
 return digest.hexdigest()

def frozen(directory):
 identity=read_json(directory/'execution.json')
 if archive_digest(directory/'source.tar')!=identity['source_tree_sha256'] or file_hash(directory/'source.tar')!=identity['source_archive_sha256']:raise ValueError('source archive binding')
 for name,key in [('optimizer','binary_sha256'),('lp_precision_quant_resident','exec_binary_sha256')]:
  if file_hash(directory/name)!=identity[key]:raise ValueError('frozen executable changed')
 for name,sha in read_json(directory/'code-objects.json').items():
  if file_hash(directory/name)!=sha:raise ValueError('frozen image changed')
 for ref in read_json(directory/'acceptance-binaries.json').values():checked_reference(ROOT,ref)
 gate=read_json(directory/'native-gate.json')
 if gate!={'native':True,'source_tree_sha256':identity['source_tree_sha256']}:raise ValueError('native cohort gate differs')
 return identity

def verify():
 v=protocol();base=ROOT/'artifacts/gpup-quant-resident-v1';d=ROOT/v['output'];before=base/'study';identities={i['source_tree_sha256']:(p,i) for p in [before,d] for i in [frozen(p)]}
 if bridge() not in identities:raise ValueError('pre-sanitizer source missing')
 for source in (ROOT/v['acceptance_output']).glob('*.source.json'):
  s=read_json(source);cohort,identity=identities[s['source_tree_sha256']];request=read_json(source.with_name(source.name.replace('.source.','.request.')))
  if request['command'][:2]!=['/usr/bin/env','AI_OPTIMIZER_CUDA_DIR='+str(cohort)] or request['command'][2:]!=s['command']:raise ValueError('gate context/image directory differs')
  approved={r['sha256'] for r in read_json(cohort/'acceptance-binaries.json').values()}
  for arg in s['command']:
   path=Path(arg)
   if path.is_file() and path.open('rb').read(4)==b'\x7fELF' and file_hash(path) not in approved:raise ValueError('gate executable not frozen')
 for p in [*d.glob('*.endpoint.json'),*(ROOT/v['acceptance_output']/'project').glob('*.endpoint.json'),*(ROOT/v['acceptance_output']/'project').glob('*.replay.json')]:
  e=read_json(p)
  if 'outcome' in e:metadata(e)
 cpu=[]
 for name in ['cpu-admission','final-admission','accepted-admission']:
  a=read_json(base/name/'admission.json');archive=checked_reference(ROOT,a['source_archive'])
  if archive_digest(archive)!=a['source_tree_sha256'] or file_hash(base/name/'lp_precision_quant_resident')!=a['executable_sha256']:raise ValueError('CPU source/executable cohort differs')
  for row in a['rows']:
   if 'endpoint' in row:checked_reference(ROOT,row['endpoint'])
  cpu.append(dict(cohort=name,source_tree_sha256=a['source_tree_sha256'],executable_sha256=a['executable_sha256']))
 fixture=ROOT/'tests/fixtures/lp-quant-resident-evidence-v1.json'
 if file_hash(fixture)!=file_hash(base/'acceptance/project/gpup-development-small-4-fp16-uniform.endpoint.json'):raise ValueError('portable fixture differs from verified endpoint')
 report=read_json(ROOT/'docs/benchmarks/data/quant-resident/report.json');micro=read_json(ROOT/'docs/benchmarks/data/quant-resident/micro-admission.json')
 if report['source_tree_sha256'] not in identities or report['ledger_sha256']!=file_hash(d/'ledger.jsonl') or len(report['cpu_cohorts'])!=3 or sum(c['verified'] for c in report['cpu_cohorts'])!=216 or report['acceptance_endpoints_verified']!=58:raise ValueError('independent endpoint verification incomplete')
 if len(micro['rows'])!=28 or micro['status']!='passed':raise ValueError('micro admission witness incomplete')
 for ref in [micro['probe'],micro['script'],micro['vectors']]:checked_reference(ROOT,ref)
 for row in micro['rows']:checked_reference(ROOT,row['raw'])
 receipts=[];cpu_seconds=0.;peak=0
 for p in sorted(base.glob('*resources.json')):
  r=read_json(p)
  # The invalid interpreter preflight is retained; it never reserved a GPU job.
  if r['returncode']!=0 and p.name!='project-device-resources.json':raise ValueError('failed resource receipt '+p.name)
  if r['reason']!='completed':raise ValueError('incomplete resource receipt '+p.name)
  cpu_seconds+=r['cpu_seconds'];peak=max(peak,r['peak_process_tree_rss_bytes']);receipts.append(reference(ROOT,p))
 # Conservatively charge uninstrumented compile/proof preparation and reserve
 # 1000 CPU seconds for final acceptance/delivery beyond these measured jobs.
 upper=cpu_seconds+6000+1000
 if upper>v['cpu_cap_seconds'] or peak>v['limits']['host_rss_bytes']:raise ValueError('CPU/RSS bound exceeded')
 artifact_bytes=sum(p.stat().st_size for p in base.rglob('*') if p.is_file())
 if artifact_bytes>v['artifact_bytes']:raise ValueError('artifact limit exceeded')
 return dict(identity='gpup-quant-resident-delivery-v1',status='passed',additional_gpu_seconds=0,verification_gpu_seconds=0,measured_source_tree_sha256=report['source_tree_sha256'],reviewed_source_tree_sha256=source_identity(),report=reference(ROOT,ROOT/'docs/benchmarks/data/quant-resident/report.json'),micro_admission=reference(ROOT,ROOT/'docs/benchmarks/data/quant-resident/micro-admission.json'),acceptance_source_bridge=v['acceptance_source_bridge'],portable_fixture=reference(ROOT,fixture),cpu_cohorts=cpu,study_endpoints_verified=report['verified'],acceptance_endpoints_verified=58,cpu_endpoints_verified=216,micro_endpoints_verified=sum(m['verified'] for m in report['micro']),resource_receipts=receipts,measured_cpu_seconds=cpu_seconds,uninstrumented_preparation_allowance_seconds=6000,remaining_acceptance_cpu_reserve_seconds=1000,cpu_upper_bound_seconds=upper,cpu_cap_seconds=v['cpu_cap_seconds'],peak_process_tree_rss_bytes=peak,artifact_bytes=artifact_bytes,artifact_cap_bytes=v['artifact_bytes'],task_gpu_ns=report['task_gpu_ns'],cumulative_gpu_ns=report['cumulative_gpu_ns'],ledger_events=report['ledger_events'],ledger_sha256=report['ledger_sha256'])

if __name__=='__main__':
 result=verify();write_json(ROOT/'docs/benchmarks/data/quant-resident/acceptance.json',result);print({k:v for k,v in result.items() if k.endswith('_verified') or k in ['status','cpu_upper_bound_seconds','artifact_bytes']})
