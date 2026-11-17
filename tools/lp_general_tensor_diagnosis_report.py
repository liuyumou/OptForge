"""Read-only timeline attribution with explicit failed-job provenance."""
import argparse
import collections
import json
import re
import sqlite3
import statistics
from pathlib import Path

from lp_general_common import BASE, ROOT, load, put, ref, require
from lp_general_budget import accounting


def distribution(values):
    values = sorted(values)
    return dict(count=len(values), sum=sum(values), minimum=values[0],
                median=statistics.median(values), maximum=values[-1],
                p05=values[int(.05 * len(values))], p95=values[int(.95 * len(values))])


def timeline(path):
    c = sqlite3.connect('file:' + str(path) + '?mode=ro', uri=True)
    c.row_factory = sqlite3.Row
    kernels = [dict(r) for r in c.execute('''SELECT k.*, s.value AS name
        FROM CUPTI_ACTIVITY_KIND_KERNEL k JOIN StringIds s ON k.shortName=s.id ORDER BY start''')]
    require(len({(r['deviceId'], r['streamId']) for r in kernels}) == 1, 'one device/stream required')
    require(all(a['end'] <= b['start'] for a, b in zip(kernels, kernels[1:])), 'unexpected kernel overlap')
    mappings = list(c.execute('SELECT DISTINCT gpuId FROM TARGET_INFO_CUDA_DEVICE WHERE cudaId=?', (kernels[0]['deviceId'],)))
    require(len(mappings) == 1, 'CUDA ordinal must map to one physical GPU')
    device = dict(c.execute('SELECT * FROM TARGET_INFO_GPU WHERE id=?', (mappings[0]['gpuId'],)).fetchone())
    require(device['uuid'] == '6721b13a-30f9-83ec-dace-ba2d9738556f', 'pinned device differs')
    summaries = []
    groups = collections.defaultdict(list)
    for r in kernels:
        groups[(r['name'], r['gridX'], r['blockX'])].append(r)
    for (name, grid, block), rows in sorted(groups.items()):
        summaries.append(dict(name=name, grid=grid, block=block,
            duration_ns=distribution([r['end'] - r['start'] for r in rows]),
            registers_per_thread=sorted({r['registersPerThread'] for r in rows}),
            local_memory_bytes_per_thread=sorted({r['localMemoryPerThread'] for r in rows}),
            grid_warps=grid * block // 32,
            grid_warps_fraction_device_capacity=grid * block / 32 / (device['smCount'] * device['maxWarpsPerSm']),
            block_count_fraction_sm_count=grid / device['smCount']))
    windows = []
    current = []
    for row in kernels:
        if row['name'] in ['tensor_product', 'tensor_encode', 'tensor_step']:
            current.append(row)
        elif current:
            windows.append(current)
            current = []
    if current:
        windows.append(current)
    require(len(windows) == 5 and all(len(w) in [200, 600] for w in windows), 'five fixed-work windows required')
    active = sum(r['end'] - r['start'] for w in windows for r in w)
    span = sum(w[-1]['end'] - w[0]['start'] for w in windows)
    api = [dict(r) for r in c.execute('''SELECT s.value AS name, count(*) AS count,
        sum(end-start) AS duration_ns FROM CUPTI_ACTIVITY_KIND_RUNTIME r
        JOIN StringIds s ON r.nameId=s.id GROUP BY nameId ORDER BY duration_ns DESC''')]
    copies = dict(c.execute('SELECT count(*) AS count, sum(end-start) AS duration_ns, sum(bytes) AS bytes FROM CUPTI_ACTIVITY_KIND_MEMCPY').fetchone())
    c.close()
    return dict(database=ref(path), device={k: device[k] for k in ['name','uuid','smCount','maxWarpsPerSm','l2CacheSize']},
        kernels=summaries, update_windows=len(windows), update_kernels=sum(map(len, windows)),
        update_kernel_ns=active, update_span_ns=span, inter_kernel_gap_ns=span-active,
        api=api, copies=copies,
        limits='Grid capacity is a mathematical upper bound, not measured occupancy. API waits overlap GPU execution; do not add them to kernel time.')


def report(identity, output):
    root = BASE / identity
    frozen = load(root / 'freeze.json')
    admission = load(ROOT / frozen['admission']['path'])
    require(ref(ROOT / frozen['admission']['path']) == frozen['admission'], 'admission changed')
    for key in ['image', 'binary']:
        require(ref(ROOT / frozen[key]['path']) == frozen[key], 'image changed')
    numerical_sources = []
    for item in admission['sources']:
        path = item['path'].split('tensor-admission-v4-sources/', 1)[1]
        require(ref(ROOT / path)['sha256'] == item['sha256'], 'numerical source changed: ' + path)
        numerical_sources.append(ref(ROOT / path))
    cells = []
    count = 0
    for cell in frozen['cells']:
        historical = load(ROOT / cell['reference']['path'])
        require(ref(ROOT / cell['reference']['path']) == cell['reference'], 'old response changed')
        modes = {}
        for mode in cell['timeline_order']:
            directory = root / (cell['id'] + '-' + mode)
            path = directory / 'response.json'
            if not path.exists():
                modes[mode] = dict(status='missing', reason='failed timeline job stopped before this observation')
                continue
            r = load(path)
            ignored = {'cost_ns', 'elapsed_ns', 'settings'}
            require({k:v for k,v in r.items() if k not in ignored} ==
                    {k:v for k,v in historical.items() if k not in ignored}, 'numerical trajectory differs')
            require({k:v for k,v in r['settings'].items() if k != 'wall_ms'} ==
                    {k:v for k,v in historical['settings'].items() if k != 'wall_ms'}, 'settings differ')
            require(r['logical'] == r['physical'] == 500, 'fixed work')
            count += 1
            modes[mode] = dict(status='retained', response=ref(path), exact_numerical_match=True,
                cost_ns=r['cost_ns'], elapsed_ns=r['elapsed_ns'], process=load(directory/'process.json'))
            if mode == 'nsys':
                database = directory / ('offline.sqlite' if cell['id']=='m21-fp4x4' else 'trace.sqlite')
                modes[mode]['timeline'] = timeline(database)
        resource = BASE/'resources'/('tensor-diagnose-'+cell['id']+'-timeline-v1.settlement.json')
        settlement = load(resource)
        before = modes['plain-before']['cost_ns']['execution']
        after = modes['plain-after'].get('cost_ns', {}).get('execution')
        trace = modes['nsys']['cost_ns']['execution']
        r = historical
        work = r['accepted_product_work']
        cells.append(dict(id=cell['id'], model=cell['model'], resource=ref(resource), job_status=settlement['status'],
            offline_import=cell['id']=='m21-fp4x4', modes=modes,
            rows=r['rows'], columns=r['columns'], nonzeros=r['nonzeros'], tile_count=r['tile_count'],
            packed_bytes=r['packed_bytes'], operator_storage_bytes=r['operator_storage_bytes'],
            accepted_product_work=work, reference_product_nnz=r['reference_product_nnz'],
            tensor_fraction=work[1]/work[3],
            profiler_execution_ratio_to_before=trace/before,
            profiler_execution_ratio_to_after=None if after is None else trace/after))
    require(count == 26 and len(cells) == 9, 'retained coverage differs')
    sass_path = BASE/'tensor-image-v6/tensor.sass'
    sass = sass_path.read_text()
    spills = {}
    for name in ['tensor_encode','tensor_product','tensor_step']:
        section = sass.split('Function : '+name+'\n')[1].split('Function :')[0]
        spills[name] = {instruction:len(re.findall(r'\b'+instruction+r'\.',section)) for instruction in ['LDL','STL']}
    failed = []
    for job in ['tensor-diagnose-m21-fp4x4-timeline-v1','tensor-diagnose-m21-fp4x4-product-v1','tensor-diagnose-analysis-v1']:
        path = BASE/'resources'/(job+'.settlement.json')
        s = load(path)
        r=load(BASE/'resources'/(job+'.reservation.json'))
        require(s['status']=='refused' and s['cpu_ns']==r['cpu_ns'] and s['gpu_ns']==r['gpu_ns'], 'full failure charge')
        failed.append(dict(job=job, settlement=ref(path),cpu_ns=s['cpu_ns'],gpu_ns=s['gpu_ns']))
    cpu,gpu=accounting()
    artifact_files = [ref(p) for p in sorted(root.rglob('*')) if p.is_file()]
    result = dict(kind='unchanged-image-tensor-attribution', status='diagnosis-complete-with-counter-refusal',
        freeze=ref(root/'freeze.json'), sources=numerical_sources, analyzer=ref(__file__),
        artifact_files=artifact_files, cells=cells, matched_responses=count, planned_timeline_responses=27,
        recovered_timelines=9, completed_timeline_jobs=8, failed_jobs=failed,
        counters=dict(status='unavailable',reason='ERR_NVGPUCTRPERM',attempted=1,planned=5,
            unattempted=4, permission_unchanged=True,
            evidence=ref(root/'m21-fp4x4-ncu-tensor_product/profile.txt')),
        sass=dict(source=ref(sass_path), spill_instructions=spills),
        accounting_checkpoint_ns=dict(cpu=cpu,gpu=gpu),
        limits=['No changed solver or CUDA image.',
                'The first timeline was imported offline; its failed receipt and missing after observation remain.',
                'Kernel timings are instrumented descriptive observations on a shared GPU, not new solve-time evidence.',
                'No hardware counter attribution between FP64 guards, memory stalls and component reconstruction is available.',
                'All 26 retained numerical transcripts exactly match the prior admitted 500-update ablation.'])
    put(output,result)
    print(dict(cells=len(cells),responses=count,timelines=9,counters='unavailable'),flush=True)


if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--id',required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    report(args.id,args.output)
