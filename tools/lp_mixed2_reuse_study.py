"""Full-lifecycle changing-model sessions; one immutable attempt per cell."""
import time
from pathlib import Path
from lp_mixed2_reuse_common import BASE, BINARY, IMAGE, ROOT, load, put, ref, require
from lp_mixed2_reuse_transport import Service


def execute_session(out, cell, models, count=32, transcript=False):
    paths = models['groups'][cell['family']]
    started = time.monotonic_ns()
    service = Service(IMAGE, ROOT/paths[0]['path'], out/(cell['id']+'.log'))
    ready = time.monotonic_ns()-started
    records = []
    try:
        require(service.ready['model_sha256']==paths[0]['sha256'], 'initial model identity')
        for item in paths[1:]:
            response = service.call('cache_model', model_path=str(ROOT/item['path']))
            require(response['cached_model_sha256']==item['sha256'], 'cached model identity')
        service.call('prepare', lane=cell['lane'])
        setup = time.monotonic_ns()-started
        for index in range(count):
            scenario = index % 4
            item = paths[scenario]
            begin = time.monotonic_ns()
            response = service.call('select_model', model_hash=item['sha256'])
            require(response['selected_model_sha256']==item['sha256'], 'selected model identity')
            switch_ns = time.monotonic_ns()-begin
            dest = out/(cell['id']+f'-r{index:02d}.json')
            result, solve_ns = service.solve_to_file(dest, lane=cell['lane'], tier=cell['tier'],
                **(models['settings'] | dict(fixed_audit=True, window_max=32 if cell['lane']=='native' else 16)))
            complete_ns = time.monotonic_ns()-begin
            require(result['model_sha256']==item['sha256'], 'solve bound to stale model')
            require(result['certified'] and result['certificate']['accepted'], 'scenario certificate refusal')
            require(result['physical']==sum(result['attempted'].values()), 'physical work accounting')
            records.append(dict(index=index, scenario=scenario, result=ref(dest),
                switch_ns=switch_ns, solve_ns=solve_ns, complete_ns=complete_ns,
                prefix_ns=time.monotonic_ns()-started, physical=result['physical'],
                logical=result['logical'], gpu_us=result['gpu_us'], costs_ns=result['costs_ns'],
                recoveries=[e for e in result['events'] if e['kind']=='recovery']))
    finally:
        before = time.monotonic_ns(); service.close(); teardown = time.monotonic_ns()-before
    total = time.monotonic_ns()-started
    row = dict(**cell, count=count, ready_ns=ready, setup_ns=setup, teardown_ns=teardown,
               complete_session_ns=total, records=records)
    put(out/(cell['id']+'.session.json'), row)
    print(dict(cell=cell['id'], session_ms=total/1e6, setup_ms=setup/1e6,
               updates=sorted({r['physical'] for r in records})), flush=True)
    return row
