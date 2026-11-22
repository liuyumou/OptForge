"""Prospective COPT/project comparison. Execution requires the exact new approval."""
import argparse
import copy
import json
import math
import resource
import time
from pathlib import Path
from lp_billion_common import BASE, ROOT, NS, CPU_CAPS, GPU_CAPS, DISK_LIMIT, disk_bytes, put, load, ref, resolve, require
from lp_billion_budget import accounting, run
from lp_billion_prepare_continue import completed
from lp_billion_owned_process import execute as child
from lp_billion_copt_fair_policy import FAMILIES, PROJECT_AUDITS, VENDOR_AUDITS, forecast, timely, pair

PYTHON = ROOT / 'artifacts/gpup-copt-adapter-env/venv/bin/python'
ADAPTER = ROOT / 'tools/lp_billion_copt_diagnostic.py'
AUDIT = ROOT / 'tools/lp_billion_full_audit_v2.py'
POLICY = ROOT / 'tools/lp_billion_copt_fair_policy.py'
PROTOCOL = ROOT / 'docs/specifications/SPEC-0046-amendment-79.md'
MEMORY_MB = 48000.


def authorized():
    from lp_billion_copt_fair_allocation import validate
    validate(load(BASE / 'approved-copt-fair-extension-v1.json'),
             load(BASE / 'approved-assessment-extension-v1.json'), CPU_CAPS, GPU_CAPS)
    for identity in ['operational-cpu-v30', 'operational-gpu-v24']:
        require(completed(identity), 'fresh operational admission ' + identity)
    require(completed('copt-fair-contracts-v1'), 'fair comparison contracts')


def bindings():
    return dict(source=ref(__file__), adapter=ref(ADAPTER), audit=ref(AUDIT),
                child=ref(ROOT / 'tools/lp_billion_owned_process.py'), capacity=ref(POLICY),
                project_worker=ref(ROOT / 'tools/lp_billion_gpu_control_campaign.py'),
                checker=ref(BASE / 'image-v1/executor'), protocol=ref(PROTOCOL),
                allocation=ref(BASE / 'approved-copt-fair-extension-v1.json'),
                selection=ref(BASE / 'copt-diagnostic-results-v1.json'))


def regenerate(scale, family=None):
    authorized()
    from lp_billion_generate import generate
    families = [family] if family else (['wide', 'tall', 'degenerate'] if scale == '64m' else ['coupled_blocks', 'irregular'])
    require(scale != '1b' or family in FAMILIES, 'one original billion family at a time')
    for name in families:
        original = BASE / f'models-{scale}-{name}-v1/result.json'
        old = load(original); resolve(old['generator'])
        identity = f'copt-fair-regenerated-{scale}-{name}-v1'
        require(not (BASE / identity).exists(), 'fresh input regeneration')
        generate(identity, name, old['target'], old['seed'])
        fresh = load(BASE / identity / 'result.json')
        require(fresh['model']['sha256'] == old['model']['sha256'], 'exact original model hash')
        require(load(resolve(fresh['model'])) == load(resolve(old['model'])), 'exact original array manifests')
        print(dict(regenerated=identity, original_model_sha256=old['model']['sha256']), flush=True)


def reserve(cells, phase, extra_development=0):
    active = [c for c in cells if c['status'] == 'pending']
    cpu, gpu = accounting(); seconds = sum(c['seconds'] for c in active)
    audits = sum(c['audit_seconds'] for c in active)
    require(cpu[phase] + 4 * (seconds + extra_development) * NS <= CPU_CAPS[phase] * NS, 'whole CPU solve and regeneration reservation')
    require(gpu[phase] + seconds * NS <= GPU_CAPS[phase] * NS, 'whole GPU solve reservation')
    require(cpu['reporting'] + (4 * audits + 1800) * NS <= CPU_CAPS['reporting'] * NS, 'whole independent audit and report reservation')


def freeze_capacity(scale):
    authorized()
    require(scale in ['64m', '256m', '512m'], 'capacity scale')
    selected = load(BASE / 'copt-diagnostic-results-v1.json')['selected_variant']
    families = ['wide', 'tall', 'degenerate'] if scale == '64m' else ['coupled_blocks', 'irregular']
    if scale != '64m':
        previous = '64m' if scale == '256m' else '256m'
        require((BASE / f'copt-fair-capacity-{previous}-v1/completed.json').exists(), 'preceding capacity stage completed')
    seconds, wall, audit = {'64m': (150, 90., 90), '256m': (600, 300., 180), '512m': (900, 600., 300)}[scale]
    cells = []
    for family in families:
        path = BASE / f'models-{scale}-{family}-v1/result.json'; model = load(path)
        cells.append(dict(id=f'copt-fair-capacity-{scale}-v1-{family}', family=family,
                          lane='copt-gpu-pdlp', variant=selected, model=model['model'], model_result=ref(path),
                          seconds=seconds, wall_seconds=wall, audit_seconds=audit, audit_host_gib=64,
                          memory_mb=MEMORY_MB, memory=dict(host_gib=128, device_gib=80), disk_gib=3, status='pending'))
    reserve(cells, 'admission')
    manifest = BASE / f'copt-fair-capacity-{scale}-v1/freeze.json'
    require(not manifest.exists(), 'fresh capacity freeze')
    put(manifest, dict(status='frozen_selected_configuration_capacity', cells=cells, **bindings()))


def worker(manifest, index):
    frozen = load(manifest); c = frozen['cells'][index]
    for key in ['source', 'adapter', 'audit', 'child', 'capacity', 'project_worker']:
        resolve(frozen[key])
    require(c['status'] == 'pending', 'capacity-admitted cell')
    if c['lane'] == 'fp4x2':
        from lp_billion_gpu_control_campaign import worker as project
        return project(manifest, index)
    out = BASE / c['id']; out.mkdir(exist_ok=False)
    previous = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    process = child([str(PYTHON), '-B', str(ADAPTER), str(resolve(c['model'])), str(out / 'response.json'),
                     '--variant', c['variant'], '--wall', str(c['wall_seconds']), '--memory-mb', str(c['memory_mb'])],
                    out / 'stdout', out / 'stderr', c['seconds'] - 30)
    process.update(child_rusage_hwm_bytes=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss * 1024,
                   child_rusage_scope_is_single_solver=previous == 0)
    put(out / 'process.json', process)
    require(not process['timed_out'] and process['returncode'] == 0, 'retain interrupted child and durable journal; never retry')
    start = time.monotonic_ns(); response = load(out / 'response.json')
    require(response['model_sha256'] == c['model']['sha256'] and response['variant'] == c['variant'], 'exact original input and selected configuration')
    require(response['parameters']['MemLimit'] == c['memory_mb'], 'admitted vendor soft memory setting')
    require(sum(response['profile']['exclusive_ns'].values()) == response['profile']['total_ns'] <= process['elapsed_ns'], 'exact timing coverage')
    transport = time.monotonic_ns() - start
    put(out / 'result.json', dict(response=ref(out / 'response.json'), freeze=ref(manifest), process_ns=process['elapsed_ns'],
                                response_transport_ns=transport, fresh_process_ns=process['elapsed_ns'] + transport))


def execute(manifest, family=None):
    authorized(); frozen = load(manifest)
    require(not (manifest.parent / 'completed.json').exists(), 'never repeat completed driver')
    capacity_stage = frozen['status'] == 'frozen_selected_configuration_capacity'
    phase = 'admission' if capacity_stage else 'development'
    require(capacity_stage or family in FAMILIES, 'execute one billion family at a time')
    for index, c in enumerate(frozen['cells']):
        if family and c['family'] != family: continue
        if c['status'] != 'pending':
            print(dict(cell=c['id'], status=c['status']), flush=True); continue
        require(not (BASE / 'resources' / (c['id'] + '.reservation.json')).exists(), 'never repeat attempted scientific cell')
        memory = c['memory']
        disk = c.get('disk_gib', math.ceil(memory.get('endpoint_bytes_upper', 0) / (1 << 30)) + 1)
        settled = run(c['id'], phase, c['seconds'], True,
                      [str(PYTHON), '-B', __file__, 'worker', '--manifest', str(manifest), '--index', str(index)],
                      memory['host_gib'], memory['device_gib'], disk)
        print(dict(cell=c['id'], settlement=settled), flush=True)
        require(settled['cleanup_empty'] and not settled['overrun'], 'cleanup/overrun stops continuation')
        command = [str(PYTHON), '-B', str(AUDIT), str(manifest), str(index)]
        host = c['audit_host_gib']
        if host <= 16: command = [str(PYTHON), '-B', str(ROOT / 'tools/lp_mixed2_reuse_place.py'), *command]
        audited = run(c['id'] + '-full-audit', 'reporting', c['audit_seconds'], False, command, host, 0,
                      math.ceil(8 * load(resolve(c['model_result']))['rows'] / (1 << 30)) + 1)
        print(dict(audit=c['id'], settlement=audited), flush=True)
        require(audited['status'] == 'passed', 'complete strict independent final/intermediate audits')
    done = all(c['status'] != 'pending' or completed(c['id'] + '-full-audit') for c in frozen['cells'])
    if done: put(manifest.parent / 'completed.json', dict(status='all_admitted_cells_attempted_and_audited', freeze=ref(manifest)))


def readiness():
    authorized()
    from lp_billion_full_report import record
    from lp_billion_copt_readiness import workspace_observed
    selected = load(BASE / 'copt-diagnostic-results-v1.json')['selected_variant']
    paths = [BASE / 'copt-diagnostic-64m-v1/freeze.json'] + [BASE / f'copt-fair-capacity-{scale}-v1/freeze.json' for scale in ['64m', '256m', '512m']]
    rows = []
    for path in paths:
        require((path.parent / 'completed.json').exists(), 'complete capacity roster')
        for c in load(path)['cells']:
            if c['variant'] != selected: continue
            row = record(c); response = load(resolve(row['response'])) if row.get('response') else None
            row['requested_solver_wall_ns'] = int(c['wall_seconds'] * NS)
            if response:
                row['requested_wall_exceeded'] = response['solver_wall_ns'] > row['requested_solver_wall_ns']
                row['timely_strict_certificate'] = timely(row, response, c['wall_seconds'])
            model = load(resolve(c['model_result']))
            valid = bool(row.get('timing_eligible') and response and response['gpu_confirmed'] and row.get('sampled_peak_owned_device_bytes', 0) > 0
                         and workspace_observed(response, row.get('strict_endpoint_accepted', False)))
            if valid:
                require(row['sampled_aggregate_peak_rss_bytes'] - response['host_memory']['VmHWM'] <= 8 * (1 << 30), 'observed host coordination allowance')
            rows.append(dict(id=c['id'], family=c['family'], nonzeros=model['nonzeros'], capacity_observed=valid,
                             host_peak_bytes=response['host_memory']['VmHWM'] if response else 0,
                             owned_device_peak_bytes=row.get('sampled_peak_owned_device_bytes', 0),
                             vendor_mem_peak_mb=response['native']['MemPeak'] if response else 0,
                             response=row.get('response'), audit=row['audit'], settlement=row['settlement'], outcome=row))
    capacity = {family: forecast(load(BASE / f'models-1b-{family}-v1/result.json'), [r for r in rows if r['family'] == family], MEMORY_MB) for family in FAMILIES}
    put(BASE / 'copt-fair-capacity-v1.json', dict(status='all_capacity_outcomes_retained', selected_variant=selected, memory_mb=MEMORY_MB,
                                               cells=rows, capacity=capacity, manifests=[ref(p) for p in paths], **bindings()))
    print({family: c['reasons'] for family, c in capacity.items()}, flush=True)


def freeze_full(wall_seconds=600):
    authorized()
    require(wall_seconds in [600, 1200], 'bounded common comparison allowance')
    window_protocol = PROTOCOL if wall_seconds == 600 else ROOT / 'docs/specifications/SPEC-0046-amendment-81.md'
    require(window_protocol.exists(), 'document any prospective common-window change before freezing')
    from lp_billion_campaign import endpoint_bytes
    from lp_billion_gpu_control_capacity import capacity as project_capacity
    for identity in ['gpu-control-quality-v3', 'gpu-control-seal-v1', 'gpu-control-gpu-v1',
                     'gpu-control-memcheck-v1', 'gpu-control-racecheck-v1',
                     'gpu-control-initcheck-v1', 'gpu-control-synccheck-v1']:
        require(completed(identity), 'unchanged numerical image admission ' + identity)
    image = load(BASE / 'image-v11/binding.json')
    for item in image['files'].values(): resolve(item)
    for item in load(resolve(image['source_manifest']))['sources']:
        if item['original']['path'].endswith(('.rs', '.cu')) or Path(item['original']['path']).name.startswith('Cargo.'):
            resolve(item['original']); resolve(item['retained'])
    vendor = load(BASE / 'copt-fair-capacity-v1.json'); selected = vendor['selected_variant']
    old = load(BASE / 'gpu-control-1b-v1/freeze.json'); cells = []
    for i, family in enumerate(FAMILIES):
        project = copy.deepcopy(next(c for c in old['cells'] if c['family'] == family))
        model = load(resolve(project['model_result']))
        project.update(id=f'copt-fair-1b-v1-{family}-project', seconds=1800, wall_seconds=float(wall_seconds),
                       common_solver_wall_seconds=wall_seconds,
                       audit_seconds=PROJECT_AUDITS[family], memory=project_capacity(model))
        project['request']['settings']['iteration_limit'] = 10000
        project['request']['settings']['wall_ms'] = wall_seconds * 1000
        project['memory']['endpoint_bytes_upper'] = endpoint_bytes(model, 10000)
        project['status'] = 'pending' if project['memory']['admitted'] else 'unsupported_capacity'
        copt = dict(id=f'copt-fair-1b-v1-{family}-copt', family=family, lane='copt-gpu-pdlp', variant=selected,
                    model=project['model'], model_result=project['model_result'], seconds=1800, wall_seconds=float(wall_seconds),
                    memory_mb=MEMORY_MB, memory=vendor['capacity'][family], audit_seconds=VENDOR_AUDITS[family],
                    audit_host_gib=project['audit_host_gib'], disk_gib=math.ceil(8 * (model['rows'] + model['columns']) / (1 << 30)) + 1,
                    status='pending' if vendor['capacity'][family]['admitted'] else 'unsupported_capacity')
        cells.extend([project, copt] if i % 2 == 0 else [copt, project])
    reserve(cells, 'development', 6 * 600)
    for c in cells:
        require(not (BASE / 'resources' / (c['id'] + '.reservation.json')).exists(), 'fresh comparison identities')
    # Only one family's original chunks and complete repaired-witness bound coexist.
    for family in FAMILIES:
        current = [c for c in cells if c['family'] == family and c['status'] == 'pending']
        storage = sum(c.get('disk_gib', math.ceil(c['memory'].get('endpoint_bytes_upper', 0) / (1 << 30)) + 1) * (1 << 30) for c in current)
        require(disk_bytes() + storage + 32 * (1 << 30) <= DISK_LIMIT, 'whole per-family input/endpoint storage before execution')
    manifest = BASE / 'copt-fair-1b-v1/freeze.json'; require(not manifest.exists(), 'fresh full comparison freeze')
    put(manifest, dict(status='frozen_fair_billion_comparison', cells=cells, vendor_capacity=ref(BASE / 'copt-fair-capacity-v1.json'),
                       project_image=ref(BASE / 'image-v11/binding.json'), common_solver_wall_seconds=wall_seconds,
                       common_window_protocol=ref(window_protocol),
                       common_outer_process_seconds=1800, project_iteration_safety_limit=10000, **bindings()))


def report():
    from lp_billion_full_report import record
    manifest = BASE / 'copt-fair-1b-v1/freeze.json'; frozen = load(manifest)
    require((manifest.parent / 'completed.json').exists(), 'entire comparison roster complete')
    rows = []
    for c in frozen['cells']:
        row = record(c); row['timely_strict_certificate'] = False
        if row.get('response'):
            response = load(resolve(row['response']))
            row['timely_strict_certificate'] = timely(row, response, c['wall_seconds'])
            row['requested_solver_wall_ns'] = int(c['wall_seconds'] * NS)
            row['requested_wall_exceeded'] = row['solver_wall_ns'] > row['requested_solver_wall_ns']
            row['iteration_safety_limit'] = 10000 if c['lane'] == 'fp4x2' else None
            row['iteration_limit_reached'] = response.get('logical', 0) >= 10000 if c['lane'] == 'fp4x2' else None
            if c['lane'] != 'fp4x2': row.update(phase_journal=response['phase_journal'], interrupts=response['interrupts'])
        rows.append(row)
    comparisons = [pair(next(r for r in rows if r['family'] == f and r['lane'] == 'fp4x2'),
                        next(r for r in rows if r['family'] == f and r['lane'] == 'copt-gpu-pdlp')) for f in FAMILIES]
    put(BASE / 'copt-fair-results-v1.json', dict(status='all_fair_comparison_outcomes_retained', cells=rows, comparisons=comparisons,
                                               freeze=ref(manifest), source=ref(__file__), strict_original_tolerance=1e-9,
                                               limitations=['One rotated pair per family; no broad superiority claim.',
                                                            'Vendor internal preparation remains opaque; durable phase journals retain interrupted progress.',
                                                            'Both use the same physical limits; COPT additionally retains its admitted 48000 MB soft setting.',
                                                            'Missing, late, uncertified and capacity-refused outcomes remain visible.']))


def cleanup(scale, family=None):
    """Delete only named, fully audited content objects; keep every small receipt."""
    from lp_billion_portable import arrays
    output = BASE / ('copt-fair-prune-' + scale + ('-' + family if family else '') + '-v1.json')
    require(not output.exists(), 'fresh cleanup receipt')
    if scale == 'pilot':
        require(family is None, 'complete pilot cleanup scope')
        manifests = [BASE / 'copt-diagnostic-64m-v1/freeze.json']
        require((manifests[0].parent / 'completed.json').exists(), 'complete pilot and every dependent audit')
    elif scale == '1b':
        require(family in FAMILIES, 'one completed billion family')
        manifests = [BASE / 'copt-fair-1b-v1/freeze.json']
    else:
        require(scale in ['64m', '256m', '512m'], 'completed capacity scale')
        manifests = [BASE / f'copt-fair-capacity-{scale}-v1/freeze.json']
        if scale == '64m': manifests.append(BASE / 'copt-diagnostic-64m-v1/freeze.json')
        for manifest in manifests:
            require((manifest.parent / 'completed.json').exists(), 'all scale dependencies complete')
    cells = [c for manifest in manifests for c in load(manifest)['cells'] if not family or c['family'] == family]
    require(cells, 'explicit owned cleanup scope')
    documents = []; models = {}
    for c in cells:
        models[c['family']] = c['model_result']
        if c['status'] == 'pending':
            require(completed(c['id'] + '-full-audit'), 'all returned endpoints audited before deletion')
            audit = load(BASE / (c['id'] + '-full-audit/result.json'))
            require(audit['status'] in ['passed', 'no_endpoint', 'retained_missing_response'], 'completed audit disposition')
        documents.append(resolve(c['model']))
        for name in ['response.json', 'check-request.json']:
            path = BASE / c['id'] / name
            if path.exists(): documents.append(path)
        path = BASE / (c['id'] + '-full-audit/requests.json')
        if path.exists(): documents.append(path)
    for name, item in models.items():
        metadata = load(resolve(item)); documents.append(resolve(metadata['construction']))
        model_scale = '64m' if scale == 'pilot' else scale
        regenerated = BASE / f'copt-fair-regenerated-{model_scale}-{name}-v1/result.json'
        if not regenerated.exists(): regenerated = BASE / f'copt-diagnostic-regenerated-{model_scale}-{name}-v1/result.json'
        if regenerated.exists(): documents.append(resolve(load(regenerated)['construction']))
    chunks = {}
    for path in set(documents):
        for array in arrays(load(path)):
            for chunk in array['chunks']:
                sha, size = chunk['sha256'], chunk['bytes']
                require(len(sha) == 64 and all(ch in '0123456789abcdef' for ch in sha), 'content-addressed owned object')
                if sha in chunks: require(chunks[sha] == size, 'consistent object size')
                chunks[sha] = size
    deleted = []; root = BASE / 'objects'
    for sha, size in chunks.items():
        if size < 8 * (1 << 20): continue
        path = root / (sha + '.bin')
        if not path.exists(): continue
        require(not path.is_symlink() and path.resolve().parent == root.resolve() and path.stat().st_size == size,
                'exact owned object path and size')
        path.unlink(); deleted.append(dict(sha256=sha, bytes=size))
    put(output, dict(status='completed_audited_large_objects_deleted', deleted=deleted,
                     released_bytes=sum(c['bytes'] for c in deleted), manifests=[ref(p) for p in manifests], source=ref(__file__),
                     replay_requires_regeneration=True, small_results_and_failures_preserved=True))
    print(dict(deleted=len(deleted), released_bytes=sum(c['bytes'] for c in deleted)), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['regenerate', 'freeze_capacity', 'worker', 'execute', 'readiness', 'freeze_full', 'report', 'cleanup'])
    parser.add_argument('--scale', choices=['pilot', '64m', '256m', '512m', '1b']); parser.add_argument('--family', choices=FAMILIES)
    parser.add_argument('--wall-seconds', type=int, choices=[600, 1200], default=600)
    parser.add_argument('--manifest', type=Path); parser.add_argument('--index', type=int); args = parser.parse_args()
    if args.action == 'regenerate': regenerate(args.scale, args.family)
    elif args.action == 'cleanup': cleanup(args.scale, args.family)
    elif args.action == 'freeze_capacity': freeze_capacity(args.scale)
    elif args.action == 'worker': worker(args.manifest, args.index)
    elif args.action == 'execute': execute(args.manifest, args.family)
    elif args.action == 'freeze_full': freeze_full(args.wall_seconds)
    else: globals()[args.action]()
