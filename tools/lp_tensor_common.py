"""Isolated ADR-0042 protocol, requests and historical resource authority."""
import hashlib,json,shutil,subprocess
from pathlib import Path
from lp_protocol import ROOT,read_json,write_json,file_hash,checked_reference
from lp_copt_budget import ComparisonLedger,receipt
CONFIG=ROOT/'benchmarks/configs/lp-tensor-v1.json'
BASE=ROOT/'artifacts/gpup-tensor-v1'

def numeric_sources():
 return {str(p.relative_to(ROOT)):file_hash(p) for p in sorted({*ROOT.glob('crates/*/src/**/*.rs'),*ROOT.glob('cuda/**/*.cu'),*ROOT.glob('cuda/lp_pdhg_tensor/*.h'),ROOT/'crates/optimizer-experiment/examples/lp_precision_tensor.rs'})}

def protocol():
 v=read_json(CONFIG)
 from validate_artifacts import validator
 validator('lp-tensor-study-v1.schema.json').validate(v)
 for ref in [v['decision'],v['budget_authority'],*v['manifests']]:checked_reference(ROOT,ref)
 if (v['prior_events'],v['prior_gpu_ns'],v['allocated_gpu_seconds'],v['additional_gpu_seconds'],v['cumulative_gpu_ns'])!=(17132,21359585855789,3000,0,25202574545061):raise ValueError('Tensor authority differs')
 return v

def ledger_for(v):
 if v!=protocol():raise ValueError('Tensor protocol differs')
 authority=checked_reference(ROOT,v['budget_authority']);base=read_json(authority)
 parent=read_json(ROOT/'benchmarks/configs/lp-quant-resident-v1.json');quant=read_json(checked_reference(ROOT,parent['previous_protocol']))
 checked_reference(ROOT,parent['decision']);checked_reference(ROOT,quant['decision'])
 if v['budget_authority']!=parent['budget_authority'] or v['phase_gpu_seconds']!=parent['phase_gpu_seconds'] or v['phase_gpu_seconds']!=quant['phase_gpu_seconds'] or v['cumulative_gpu_ns']!=parent['cumulative_gpu_ns'] or v['cumulative_gpu_ns']!=quant['cumulative_gpu_ns'] or v['total_gpu_seconds']!=base['total_gpu_seconds']:raise ValueError('accepted amended phase authority differs')
 directory=ROOT/'artifacts/lp-campaign-ledgers'/base['id'];raw=(directory/'ledger.jsonl').read_bytes();prefix=b''.join(raw.splitlines(keepends=True)[:17132])
 if len(prefix.splitlines())!=17132 or hashlib.sha256(prefix).hexdigest()!=v['prior_ledger_sha256'] or sum(json.loads(x)['charged_ns'] for x in prefix.splitlines() if json.loads(x)['resource']=='gpu')!=v['prior_gpu_ns']:raise ValueError('historical prefix differs')
 return ComparisonLedger(directory,file_hash(authority),v)

def instances(v):return {i['id']:i for ref in v['manifests'] for i in read_json(checked_reference(ROOT,ref))['instances']}

def make_request(c,model,binary,source,work=50000,horizon=0,seconds=30):
 v=protocol();original=c['layout']=='original_tuned'
 return dict(schema_version=1,identity='lp-tensor-v1',settings=c['settings'],model_sha256=file_hash(model),source_tree_sha256=source,executable_sha256=file_hash(binary),code_object_sha256=file_hash(ROOT/'target/native/cuda/lp_pdhg_tensor.cubin'),device=v['device'],options=dict(v['solve'],iteration_limit=work,time_limit_ms=seconds*1000),method=dict(v['lp_settings'],iteration_limit=work),diagnostic=horizon!=0,layout=c['layout'],horizon=horizon,guard='none-original-tuned-v1' if original else 'tensor-successor-bound-v1',reduction='tuned-warp32-v1' if original else 'exact-tile128-serial-fp64-v1',norm_policy='original-tuned-v1' if original else 'twice-absolute-original-v1',device_buffer_bytes=1<<30)

def verify_cpu_sources(cpu):
 """Retain exact CPU payloads; admit only proved divisibility spelling changes."""
 current=numeric_sources()
 if cpu['numerical_sources']==current:return
 import tarfile
 bridge=read_json(ROOT/'docs/benchmarks/data/tensor/cpu-source-bridge.json')
 if bridge['cpu_numerical_sources']!=cpu['numerical_sources'] or bridge['current_numerical_sources']!=current:raise ValueError('CPU source bridge binding differs')
 changed={p for p in current if current[p]!=cpu['numerical_sources'].get(p)}
 allowed={'crates/optimizer-lp/src/tensor.rs','crates/optimizer-experiment/src/lp_tensor.rs'}
 if set(cpu['numerical_sources'])!=set(current) or changed!=allowed:raise ValueError('CPU bridge changed-file set differs')
 with tarfile.open(checked_reference(ROOT,cpu['source_archive'])) as archive:
  for path in sorted(allowed):
   before=archive.extractfile(path).read().decode()
   if path.endswith('/src/tensor.rs'):
    after=before.replace('c.component_products % 1024 == 0','c.component_products.is_multiple_of(1024)').replace('c.mma_instructions % per == 0','c.mma_instructions.is_multiple_of(per)').replace('pub const GUARD: &str = "global-then-coordinate-successor-rn-v1";','pub const GUARD: &str = "tensor-successor-bound-v1";').replace('pub const TREE: &str = "segmented-serial-fp32-fp64-v1";','pub const TREE: &str = "exact-tile128-serial-fp64-v1";')
   else:
    prefix,tail=before.split('\n#[cfg(test)]\nmod tests {',1)
    after=prefix+'\n#[cfg(test)]\nmod tests {'+tail.replace('optimizer_lp::quant::Format::Fp16,','optimizer_lp::quant::Format::Fp64,').replace('gpu.launches = 7 *','gpu.launches = 11 *').replace('+ 2 * gpu.device_windows;','+ 4 * gpu.device_windows;')
   if after!=(ROOT/path).read_text():raise ValueError('CPU numerical body changed outside proven bridge')
