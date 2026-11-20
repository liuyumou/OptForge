"""Audit retained process identities and GPU-memory history without changing jobs."""
import argparse
import json
from pathlib import Path
from lp_billion_common import BASE, ROOT, load, put, ref, require
from lp_confirmation2_supervisor import same_process
from lp_billion_diagnose import visible_handles


def identities(value):
    if isinstance(value, dict):
        if {'pid', 'start_ticks'} <= value.keys():
            yield value
        for child in value.values():
            yield from identities(child)
    elif isinstance(value, list):
        for child in value:
            yield from identities(child)


def compact(sample):
    return dict(start_ns=sample['start_ns'], end_ns=sample['end_ns'], used=sample['used'],
                attributed=sum(sample['processes'].values()), utilization=sample['utilization'],
                processes=sample['processes'])


def main(identity):
    require(identity and Path(identity).name == identity and identity not in ['.', '..'], 'audit identity')
    out = BASE/identity
    out.mkdir(exist_ok=False)
    paths = sorted((ROOT/'artifacts').glob('*/resources/*.resource.json'))
    paths += sorted((BASE/'resources').glob('*.resource.json'))
    known = {}
    receipts = []
    for path in paths:
        document = load(path)
        process_keys = set()
        for item in identities(document):
            key = item['pid'], item['start_ticks']
            known[key] = item
            process_keys.add(key)
        receipts.append(dict(receipt=ref(path), status=document.get('status'),
            coordinator_cleanup=((document.get('result') or {}).get('cleanup') or {}).get('empty'),
            guardian_cleanup=(document.get('guardian_cleanup') or {}).get('empty'),
            process_identities=len(process_keys)))
    # A PID alone cannot establish that an old job is still present.
    surviving = [item for item in known.values() if same_process(item)]
    put(out/'receipts.json', receipts)
    put(out/'identities.json', sorted(known.values(), key=lambda p:(p['pid'],p['start_ticks'])))
    timelines = []
    for name in ['ladder-128m-v2-0-fp4x2', 'ladder-512m-v2-0-fp4x2',
                 'ladder-512m-v2-1-fp4x2', 'operational-gpu-v7']:
        trace = BASE/'resources'/(name+'.resource.json.capacity.jsonl')
        samples = [line['gpu'] for text in trace.read_text().splitlines()
                   if 'gpu' in (line := json.loads(text))]
        timelines.append(dict(job=name, trace=ref(trace), samples=len(samples),
            first=compact(samples[0]), last=compact(samples[-1]),
            min_used=min(s['used'] for s in samples), max_used=max(s['used'] for s in samples),
            max_attributed=max(sum(s['processes'].values()) for s in samples),
            samples_with_listed_processes=sum(bool(s['processes']) for s in samples)))
    last_end = timelines[-1]['last']['end_ns']
    later = []
    for path in sorted((BASE/'availability/operational-gpu-v8').glob('*.json'),key=lambda p:int(p.stem)):
        sample = load(path)
        if sample['start_ns'] > last_end:
            later.append(dict(sample=ref(path), **compact(sample)))
    gpu_jobs = [dict(id=p.name.removesuffix('.reservation.json'), reservation=ref(p))
                for p in (BASE/'resources').glob('*.reservation.json') if load(p)['gpu']]
    responses = []
    for path in (BASE/'operational-gpu-v7').glob('*-new.stdout.jsonl'):
        for text in path.read_text().splitlines():
            response = json.loads(text)
            responses.append(dict(response=ref(path), device_bytes_upper=response.get('device_bytes_upper')))
    put(out/'post_admission_observations.json', later)
    result = dict(status='audited', retained_resource_receipts=len(receipts),
        recorded_process_identities=len(known), surviving_recorded_identities=surviving,
        visible_handles=visible_handles(), receipts=ref(out/'receipts.json'), identities=ref(out/'identities.json'),
        timelines=timelines, restored_idle=ref(BASE/'availability/idle-restored-v1.json'),
        interrupted_cleanup=ref(BASE/'resources/ladder-128m-v2-0-fp4x2.cleanup-disposition.json'),
        post_last_admission=ref(out/'post_admission_observations.json'),
        later_min_used=min(s['used'] for s in later), later_max_used=max(s['used'] for s in later),
        later_max_utilization=max(s['utilization'] for s in later),
        gpu_reservations=gpu_jobs, partial_last_admission_responses=responses,
        max_declared_buffers_last_admission=max(r['device_bytes_upper'] or 0 for r in responses),
        cuda_ownership_source=ref(ROOT/'research/lp-tensor-expanded-device/cuda-sys/src/lib.rs'),
        no_device_or_process_mutations=True,
        limitation='Recorded process identities and visible handles exclude only observed surviving owners. No host PID view or kernel log is available; driver-level orphan allocations cannot be conclusively excluded. Historical process telemetry is empty even during our runs, so it cannot independently attribute allocations.')
    put(out/'result.json', result)
    print({k:result[k] for k in ['status','retained_resource_receipts','recorded_process_identities',
        'surviving_recorded_identities','max_declared_buffers_last_admission','later_max_used','later_max_utilization']},flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--id',required=True)
    main(parser.parse_args().id)
