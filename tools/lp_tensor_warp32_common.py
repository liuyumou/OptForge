"""ADR-0045 isolated authority, joint admission and verification receipts."""
import copy
import hashlib
import json
import os
import time
from lp_protocol import ROOT, read_json, write_json, file_hash, checked_reference
from lp_copt_budget import ComparisonLedger, receipt
from benchmark_lp import reference
import lp_tensor_cost_common as retained

BASE = ROOT / 'artifacts/gpup-tensor-warp32-v1'
CONFIG = ROOT / 'benchmarks/configs/lp-tensor-warp32-v1.json'
IMAGE = BASE / 'build/lp_pdhg_tensor_cost.cubin'
DATA = ROOT / 'docs/benchmarks/data/tensor-warp32'
JOURNAL = BASE / 'cpu-journal-recovery-v3.json'
PREFIX = '9142829b3be8afdb1865425c83ca9122371284ca0e16f7bc8b18d303a5894426'


def numeric_sources():
    result = retained.numeric_sources()
    for path in [*ROOT.glob('cuda/lp_pdhg_tensor_warp32/*.h'),
                 ROOT / 'crates/optimizer-lp/examples/tensor_warp32_probe.rs']:
        result[str(path.relative_to(ROOT))] = file_hash(path)
    return result


def protocol():
    # The unchanged reader validates every inherited numerical/schema field.
    expected = copy.deepcopy(retained.protocol())
    expected.update(id='gpup-tensor-warp32-v1', output='artifacts/gpup-tensor-warp32-v1/study-v1',
                    acceptance_output='artifacts/gpup-tensor-warp32-v1/acceptance-v1',
                    prior_events=17366, prior_gpu_ns=22222794320335,
                    prior_ledger_sha256=PREFIX, allocated_gpu_seconds=790,
                    combined_cap_seconds=790, cpu_cap_seconds=6100,
                    decision=dict(path='docs/decisions/ADR-0045-warp32-tensor-reference-recovery.md',
                                  sha256=file_hash(ROOT / 'docs/decisions/ADR-0045-warp32-tensor-reference-recovery.md')),
                    categories=dict(accept=dict(phase='repeatability', seconds=290),
                                    profile=dict(phase='ablations', seconds=200),
                                    timing=dict(phase='screening', seconds=300)))
    value = read_json(CONFIG)
    if value != expected:
        raise ValueError('warp32 authority or inherited numerical contract differs')
    checked_reference(ROOT, value['decision'])
    return value


def instances(value):
    return retained.instances(value)


def make_request(configuration, model, binary, source, work=50000, horizon=0, seconds=16):
    request = retained.make_request(configuration, model, binary, source, work, horizon, seconds)
    request['code_object_sha256'] = file_hash(IMAGE)
    return request


def worker_remaining_ns():
    journal = read_json(JOURNAL)
    active = journal['active']
    if journal['failed'] or not active or active['stage'] != 'workers' or 'LP_CPU_ALLOWED_CPUS' not in os.environ:
        raise ValueError('GPU execution lacks active inherited CPU worker admission')
    allowed = set(json.loads(os.environ['LP_CPU_ALLOWED_CPUS']))
    if len(allowed) != 4 or not os.sched_getaffinity(0) <= allowed:
        raise ValueError('worker affinity differs')
    return max(0, active['started_ns'] + active['reserved_cpu_ns'] // 4 - 2_000_000_000 - time.monotonic_ns())


class JointLedger(ComparisonLedger):
    def reserve(self, trial_id, seconds, resource='gpu', phase='ablations'):
        if resource != 'gpu' or worker_remaining_ns() < int((seconds + 120) * 1e9):
            raise ValueError('joint CPU/lease/verification admission exhausted')
        return super().reserve(trial_id, seconds, resource, phase)


def ledger_for(value):
    if value != protocol():
        raise ValueError('warp32 protocol differs')
    authority = checked_reference(ROOT, value['budget_authority'])
    path = ROOT / 'artifacts/lp-campaign-ledgers' / read_json(authority)['id'] / 'ledger.jsonl'
    prefix = b''.join(path.read_bytes().splitlines(keepends=True)[:17366])
    if len(prefix.splitlines()) != 17366 or hashlib.sha256(prefix).hexdigest() != PREFIX:
        raise ValueError('exact 17366-event historical prefix differs')
    events = [json.loads(line) for line in prefix.splitlines()]
    if sum(e['charged_ns'] for e in events if e['resource'] == 'gpu') != value['prior_gpu_ns']:
        raise ValueError('prior GPU charge differs')
    return JointLedger(path.parent, file_hash(authority), value)


def verify_cpu_sources(cpu):
    if cpu['numerical_sources'] != numeric_sources():
        raise ValueError('warp32 CPU numerical sources differ')


def verification_binding(model, request, endpoint, binary, source):
    return dict(model=reference(ROOT, model), request=reference(ROOT, request),
                endpoint=reference(ROOT, endpoint), executable=reference(ROOT, binary),
                source_tree_sha256=source, verification_helper_sha256=file_hash(ROOT / 'tools/lp_tensor_warp32_common.py'))


def save_verification(path, model, request, endpoint, binary, source, assessment, elapsed_ns):
    if path.exists():
        raise ValueError('independent verification receipt already exists')
    write_json(path, dict(identity='gpup-tensor-warp32-independent-verification-v1',
                         status='passed', binding=verification_binding(model, request, endpoint, binary, source),
                         assessment=assessment, elapsed_ns=elapsed_ns))


def read_verification(path, model, request, endpoint, binary, source):
    value = read_json(path)
    if (value.get('identity') != 'gpup-tensor-warp32-independent-verification-v1'
            or value.get('status') != 'passed'
            or value.get('binding') != verification_binding(model, request, endpoint, binary, source)
            or type(value.get('elapsed_ns')) is not int or value['elapsed_ns'] < 0):
        raise ValueError('independent verification receipt/source binding differs')
    return value
