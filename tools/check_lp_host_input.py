"""Bounded host-input producer diagnostic, not a new study or supported preset.

Two frozen original 32768-row N=8 fused-FP64 short batches, one repetition each.
The numerical requests are unchanged. Only source/executable identity changes.
One 48-second worker reserves 54 seconds in the existing gpupt study pool. There
is no retry or new allowance. Verification is CPU-only and uses both old and new
verifiers; times describe whole batch commands, never single-solve latency.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from analyze_lp_throughput import identity_count, research_bits
from benchmark_lp import prepare_execution, provenance, source_identity, telemetry
from benchmark_lp_throughput import CONFIG, jobs, label, protocol, research_batch_request_for
from lp_protocol import ROOT, checked_reference, file_hash, read_json, write_json
from lp_research_budget import Study, category_usage, ledger_for, run

OUTPUT = ROOT / 'artifacts/gpupt-host-input-20260922'
AUTHORITY = ROOT / 'benchmarks/configs/lp-throughput-controls-v1.json'
KINDS = ('batch-repeat-short', 'batch-variant-short')
KEY = 'host-input-review-20260922'


def unchanged(plan):
    for path, digest in plan['files'].items():
        if file_hash(ROOT / path) != digest:
            raise ValueError('frozen diagnostic input changed: ' + path)


def worker():
    if os.environ.get('AI_OPTIMIZER_GPU_LEASE') != 'inherited':
        raise ValueError('shared lease required')
    plan = read_json(OUTPUT / 'diagnostic-plan.json')
    unchanged(plan)
    for case in plan['cases']:
        started = time.monotonic_ns()
        result = subprocess.run(case['command'], capture_output=True, text=True, timeout=48)
        record = dict(elapsed_ns=time.monotonic_ns()-started, returncode=result.returncode,
                      stdout=result.stdout, stderr=result.stderr)
        write_json(OUTPUT / (case['id'] + '.command.json'), record)
        if result.returncode:
            raise ValueError('batch failed: ' + result.stderr)


def execute():
    if (OUTPUT / 'diagnostic-plan.json').exists():
        raise ValueError('diagnostic already frozen; no retry')
    value, base, manifest = protocol(CONFIG)
    authority = read_json(AUTHORITY)
    study = Study.from_protocol(authority)
    archive = ROOT / value['output']
    original = read_json(archive / 'protocol.json')
    if original['protocol'] != value or original['jobs'] != list(jobs(value, base, manifest)):
        raise ValueError('original frozen protocol differs')
    binary = OUTPUT / 'lp_precision_research.checked'
    if file_hash(binary) != file_hash(ROOT / 'target/release/examples/lp_precision_research'):
        raise ValueError('candidate differs from accepted release binary')
    source = source_identity()
    receipt = read_json(ROOT / 'target/lp-native-gate.json')
    if receipt != dict(native=True, source_tree_sha256=source):
        raise ValueError('full native gate required on exact source')
    cubin = ROOT / 'target/native/cuda/lp_pdhg_research.cubin'
    if file_hash(cubin) != original['code_object_sha256']:
        raise ValueError('kernel changed')
    native = provenance(binary, base['device'])
    prepare_execution(OUTPUT, native)
    shutil.copy2(cubin, OUTPUT / cubin.name)
    files = [binary, cubin, AUTHORITY, Path(__file__).resolve(), archive / 'protocol.json']
    cases = []
    for kind in KINDS:
        job = next(j for j in original['jobs'] if j['kind'] == kind
                   and j['instance']['id'] == 'gpup-extension-irregular-32768'
                   and j['config']['id'] == 'research-fused-fp64' and j['repeat'] == 0 and j['size'] == 8)
        key = label(job)
        model = checked_reference(ROOT, job['instance']['model'])
        old_request = archive / (key + '.research.json')
        expected = research_batch_request_for(job, base, value, original['source']['source_tree_sha256'],
                                             file_hash(model), original['research_binary_sha256'], file_hash(cubin))
        if read_json(old_request) != expected:
            raise ValueError('original numerical request differs')
        request = {**expected, 'source_tree_sha256': source, 'executable_sha256': file_hash(binary)}
        path = OUTPUT / (key + '.research.json')
        write_json(path, request)
        evidence = OUTPUT / (key + '.batch')
        cases.append(dict(id=key, command=[str(binary), 'batch', str(model), str(path), str(evidence)],
                          historical_elapsed_ns=read_json(archive / (key + '.result.json'))['worker']['elapsed_ns']))
        files += [model, path, old_request, archive / (key + '.batch/batch.json'), archive / (key + '.result.json')]
    plan = dict(schema_version=1, source=native, cases=cases, worker_seconds=48, reservation_seconds=54,
                accounting='existing gpupt study pool; no additional allowance',
                files={str(p.relative_to(ROOT)): file_hash(p) for p in files})
    write_json(OUTPUT / 'diagnostic-plan.json', plan)
    with ledger_for(study, protocol=authority) as ledger:
        try:
            result = run(ledger, 'study', KEY, ['python3', str(Path(__file__).resolve()), 'worker'], 48, OUTPUT, study)
            result.update(telemetry_after=telemetry(base['device']), study_gpu_ns=category_usage(ledger, 'study', study.prefix),
                          acceptance_gpu_ns=category_usage(ledger, 'accept', study.prefix), cumulative_gpu_ns=ledger.totals())
            write_json(OUTPUT / 'diagnostic-result.json', result)
        finally:
            shutil.copyfile(ledger.path, OUTPUT / 'ledger.jsonl')
    print(json.dumps(result))


def verify():
    destination = OUTPUT / 'diagnostic-verification.json'
    if destination.exists():
        raise ValueError('refusing to overwrite verification')
    plan = read_json(OUTPUT / 'diagnostic-plan.json')
    unchanged(plan)
    archive = ROOT / 'artifacts/gpup-throughput-v1'
    comparisons = []
    for case in plan['cases']:
        _, _, model, request, evidence = case['command']
        evidence = Path(evidence)
        receipts = []
        for binary in [OUTPUT / 'lp_precision_research.checked', archive / 'lp_precision_research']:
            check = subprocess.run([str(binary), 'verify-batch', model, request, str(evidence)],
                                   capture_output=True, text=True, timeout=180)
            if check.returncode or check.stdout.strip() != 'verified':
                raise ValueError('independent batch verification failed: ' + check.stderr)
            receipts.append(dict(binary_sha256=file_hash(binary), returncode=check.returncode, stdout=check.stdout))
        batch = read_json(evidence / 'batch.json')
        old_dir = archive / (case['id'] + '.batch')
        old = read_json(old_dir / 'batch.json')
        pairs = []
        for current, previous in zip(batch['solves'], old['solves'], strict=True):
            name = 'solve-%03d.json' % current['index']
            if (current['index'] != previous['index'] or current['model_sha256'] != previous['model_sha256']
                    or current['evidence_sha256'] != file_hash(evidence / name)
                    or previous['evidence_sha256'] != file_hash(old_dir / name)):
                raise ValueError('solve identity differs')
            pairs.append((research_bits(read_json(evidence / name)), research_bits(read_json(old_dir / name))))
        elapsed = read_json(OUTPUT / (case['id'] + '.command.json'))['elapsed_ns']
        comparisons.append(dict(id=case['id'], verification=receipts, **identity_count(pairs),
                                elapsed_ns=elapsed, historical_elapsed_ns=case['historical_elapsed_ns'],
                                historical_ratio=case['historical_elapsed_ns']/elapsed))
    write_json(destination, dict(cases=comparisons, endpoint='whole batch process time; one diagnostic repetition, historical unpaired comparison'))
    print(json.dumps(comparisons))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('run', 'worker', 'verify'))
    action = parser.parse_args().action
    {'run': execute, 'worker': worker, 'verify': verify}[action]()
