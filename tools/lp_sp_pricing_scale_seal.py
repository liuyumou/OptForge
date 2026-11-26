"""Read-only disposition of completed cells with failed final supervision."""
import json
from pathlib import Path
from lp_sp_pricing_budget import BASE, NS, put, binding
from lp_sp_pricing_gpu_opt_compare import read, verify
from lp_sp_pricing_scale_experiment import STUDY, validate
from lp_sp_pricing_finish import identities, still_same_process

FAILED = BASE/'resources/scale-gpu-group-1-v1'
RESULT = BASE/'scale-gpu-group-1-seal-v1/result.json'


def seal():
    frozen = validate()
    receipt = read(str(FAILED)+'.settlement.json')
    resource = read(str(FAILED)+'.resource.json')
    reservation = read(str(FAILED)+'.reservation.json')
    if (receipt['status'] != 'refused' or not receipt['cleanup_empty'] or receipt['overrun']
            or receipt['cpu_ns'] != 6240*NS or receipt['gpu_ns'] != 1560*NS
            or resource['result']['reason'] != 'coordinator_lost'):
        raise RuntimeError('unexpected failed-group disposition')
    verify(receipt['resource'])
    retained = []
    for source in reservation['sources']:
        snapshot = binding(source['retained'])
        if any(snapshot[k] != source[k] for k in ('bytes', 'sha256')):
            raise RuntimeError('retained source changed')
        retained.append(snapshot)
    owned = set(identities(resource)) | set(identities(read(str(FAILED)+'.journal.json')))
    if any(still_same_process(*item) for item in owned):
        raise RuntimeError('recorded owned process remains')
    if read(STUDY/'gpu-group-1-completed.json')['status'] != 'all_slots_disposed':
        raise RuntimeError('group completion marker missing')
    cells = [c for c in frozen['cells'] if c['group'] == 1 and c['lane'] != 'copt-auto']
    records = []
    for cell in cells:
        out = STUDY/'runs'/cell['id']; started = read(out/'started.json'); proc = read(out/'process.json')
        if started['cell'] != cell or proc['returncode'] != 0 or proc['timed_out']:
            raise RuntimeError('unexpected incomplete scientific process')
        verify(started['model'])
        records.append(dict(id=cell['id'], started=binding(out/'started.json'),
            process=binding(out/'process.json'), response=binding(out/'response.json')))
    RESULT.parent.mkdir(exist_ok=False)
    put(RESULT, dict(status='completed_outputs_retained_timing_excluded', source=binding(__file__),
        failure=binding(str(FAILED)+'.settlement.json'), resource=binding(str(FAILED)+'.resource.json'),
        frozen=binding(STUDY/'freeze.json'), records=records, retained_sources=retained,
        timing_excluded_ids=[c['id'] for c in cells], owned_identities=len(owned), live_owned_identities=[],
        mathematical_acceptance='must still pass the new independent endpoint audits',
        original_failure_regraded=False, scientific_reexecution=False,
        reason='coordinator_lost', preceding_cause='not established by retained evidence'))
    print(json.dumps(dict(status='outputs_sealed', timing_excluded_cells=len(cells), owned_identities=len(owned))), flush=True)


def checked():
    result = read(RESULT)
    from lp_sp_pricing_gpu_opt_report import bindings
    bindings(result)
    if read(BASE/'resources/scale-gpu-group-1-seal-v1.settlement.json')['status'] != 'passed':
        raise RuntimeError('read-only seal supervision failed')
    return result


if __name__ == '__main__':
    seal()
