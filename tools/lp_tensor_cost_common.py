"""ADR-0044 cost protocol; inherited authority and exact prefix stay immutable."""
import hashlib
from lp_protocol import ROOT,read_json,write_json,file_hash,checked_reference
from lp_copt_budget import ComparisonLedger,receipt

BASE=ROOT/'artifacts/gpup-tensor-cost-v1'
CONFIG=ROOT/'benchmarks/configs/lp-tensor-cost-v1.json'
PREFIX='e1766490f8de2affa14f4f950afed18be7f69531c3c28eedfd74539fcc0d9db5'

def numeric_sources():
    return {str(p.relative_to(ROOT)):file_hash(p) for p in sorted({*ROOT.glob('crates/*/src/**/*.rs'),*ROOT.glob('cuda/**/*.cu'),*ROOT.glob('cuda/lp_pdhg_tensor_cost/*.h'),ROOT/'crates/optimizer-experiment/examples/lp_precision_tensor_cost.rs'})}

def protocol():
    v=read_json(CONFIG)
    from validate_artifacts import validator
    validator('lp-tensor-cost-study-v1.schema.json').validate(v)
    for ref in [v['decision'],v['budget_authority'],*v['manifests']]:checked_reference(ROOT,ref)
    if (v['id'],v['prior_events'],v['prior_gpu_ns'],v['allocated_gpu_seconds'],v['additional_gpu_seconds'],v['cumulative_gpu_ns'],v['prior_ledger_sha256'])!=('gpup-tensor-cost-v1',17362,22184699888064,1806,0,25202574545061,PREFIX):raise ValueError('cost authority differs')
    return v

def instances(v):
    return {i['id']:i for ref in v['manifests'] for i in read_json(checked_reference(ROOT,ref))['instances']}

def make_request(c,model,binary,source,work=50000,horizon=0,seconds=16):
    v=protocol();original=c['layout']=='original_tuned'
    return dict(schema_version=1,identity='lp-tensor-cost-v1',settings=c['settings'],model_sha256=file_hash(model),source_tree_sha256=source,executable_sha256=file_hash(binary),code_object_sha256=file_hash(ROOT/'target/native/cuda/lp_pdhg_tensor_cost.cubin'),device=v['device'],options=dict(v['solve'],iteration_limit=work,time_limit_ms=seconds*1000),method=dict(v['lp_settings'],iteration_limit=work),diagnostic=horizon!=0,layout=c['layout'],horizon=horizon,guard='none-original-tuned-v1' if original else 'tensor-cost-successor-bound-v1',reduction='tuned-warp32-v1' if original else 'exact-tile128-residual-fp64-v1',norm_policy='original-tuned-v1' if original else c.get('norm_policy','disjoint-interval-gram-v1'),audit_policy=c.get('audit_policy','device_ordered_v1'),device_buffer_bytes=1<<30)

def ledger_for(v):
    if v!=protocol():raise ValueError('cost protocol differs')
    authority=checked_reference(ROOT,v['budget_authority']);base=read_json(authority)
    path=ROOT/'artifacts/lp-campaign-ledgers'/base['id']/'ledger.jsonl'
    prefix=b''.join(path.read_bytes().splitlines(keepends=True)[:17362])
    if len(prefix.splitlines())!=17362 or hashlib.sha256(prefix).hexdigest()!=PREFIX:raise ValueError('historical prefix differs')
    import json
    events=[json.loads(line) for line in prefix.splitlines()]
    if sum(e['charged_ns'] for e in events if e['resource']=='gpu')!=v['prior_gpu_ns']:raise ValueError('prior GPU charge differs')
    return ComparisonLedger(path.parent,file_hash(authority),v)

def verify_cpu_sources(cpu):
    if cpu['numerical_sources']!=numeric_sources():raise ValueError('cost numerical source differs')
