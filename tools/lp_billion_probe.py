"""Audit ownership from admitted Rust CUDA runs, without CUDA driver calls.

The initial standalone context probe remains in its immutable snapshot/receipt.
Current admission uses the existing optimizer-cuda-sys boundary and the complete
continuation/sanitizer traces.
"""
import json
from lp_billion_common import BASE, ROOT, load, put, ref, require
from lp_billion_idle import validate_gpu


def audit():
    rows = []
    for name in ['array-gpu-v1', 'array-memcheck-v1', 'array-racecheck-v1',
                 'array-initcheck-v1', 'array-synccheck-v1']:
        settlement = BASE/'resources'/(name+'.settlement.json')
        require(load(settlement)['status'] == 'passed', 'complete Rust device admission')
        reservation = BASE/'resources'/(name+'.reservation.json')
        for sample in load(reservation)['idle']:
            require(not sample['processes'] and sample['utilization'] == 0, 'idle start')
        trace = BASE/'resources'/(name+'.resource.json.capacity.jsonl')
        count = owned = 0
        for line in trace.open():
            record = json.loads(line)
            if 'gpu' not in record:
                continue
            sample = record['gpu']
            sample['processes'] = {int(k): v for k, v in sample['processes'].items()}
            validate_gpu(sample, set(record['owned_physical_pids']))
            count += 1
            owned += bool(sample['processes'])
        require(owned > 0, 'live owned CUDA context observed')
        rows.append(dict(reservation=ref(reservation), settlement=ref(settlement),
                         trace=ref(trace), samples=count, owned_samples=owned))
    put(BASE/'gpu-ownership-v2.json', dict(status='passed', rows=rows,
        guard=ref(ROOT/'tools/lp_billion_idle.py'),
        authority='Admitted Rust executor through optimizer-cuda-sys only.',
        retained_initial_probe=ref(BASE/'gpu-ownership-v1.json'), initial_probe_superseded=True))

if __name__ == '__main__':
    audit()
