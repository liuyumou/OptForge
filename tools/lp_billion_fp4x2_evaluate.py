"""Fresh FP4x2 validation and measurement; guarded jobs, no historical driver reuse."""
import argparse
import copy
import itertools
import json
import math
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import time

from lp_billion_common import BASE, ROOT, put, load, ref, resolve, require
from lp_billion_fp4x2_overhead import preservation, commands
from lp_billion_readmission import passed

QUALITY = 'fp4x2-overhead-quality-v1'
IMAGE = BASE/'image-fp4x2-overhead-v1'
FLAGS = ('resident_preparation', 'resident_control', 'certificate_workspace', 'certificate_overlap')
SEMANTICS = ('schema_version','kind','execution','product_work_order','format_order',
             'selected_schedule','initial_fast_lanes','operator_storage_bytes','device_bytes_upper','settings','tensor_config','selected_initial_format','reference_product_nnz',
             'physical_product_work','accepted_product_work','tile_count','packed_bytes',
             'bound_proof','guard_policy','status','certified','certificate','endpoint',
             'physical','logical','restarts','attempted','accepted','recoveries','assessments',
             'rows','columns','nonzeros','model_sha256','cached_assessments')


def semantic(response):
    # Canonical JSON distinguishes -0.0 from +0.0; ordinary dict equality does not.
    return json.dumps({key: response[key] for key in SEMANTICS if key in response},
                      sort_keys=True, separators=(',', ':'), allow_nan=False)


def quality_bound():
    passed(QUALITY)
    for row in load(BASE/'sources'/QUALITY/'manifest.json')['sources']:
        if row['original']['path'].startswith('research/lp-billion-lowbit/'):
            resolve(row['original']); resolve(row['retained'])
    return preservation()


def job_directory(identity, gpu=False):
    reservation = load(BASE/'resources'/(identity+'.reservation.json'))
    require(reservation['gpu'] == gpu, 'matching supervised CPU/GPU reservation required')
    require(reservation['command'][-1] == identity, 'matching job identity')
    out = BASE/identity
    out.mkdir(exist_ok=False)
    return out


def seal(identity):
    out = job_directory(identity)
    quality_bound()
    old = load(BASE/'image-v12/binding.json')
    IMAGE.mkdir(exist_ok=False)
    files = {}
    for name, item in old['files'].items():
        source = resolve(item)
        if name == 'executor':
            source = resolve(load(BASE/QUALITY/'result.json')['executor'])
        shutil.copy2(source, IMAGE/name)
        files[name] = ref(IMAGE/name)
    shutil.copy2(BASE/'target/release/fp4x2_certificate_bench', IMAGE/'certificate-bench')
    files['certificate-bench'] = ref(IMAGE/'certificate-bench')
    put(IMAGE/'binding.json',dict(status='CPU_quality_only', files=files,
        quality=ref(BASE/QUALITY/'result.json'), baseline=ref(BASE/'image-v12/binding.json'),
        source_manifest=ref(BASE/'sources'/QUALITY/'manifest.json')))
    put(out/'result.json',dict(status='passed', image=ref(IMAGE/'binding.json'), preservation=preservation()))


def image_bound():
    quality_bound()
    image = load(IMAGE/'binding.json')
    for row in image['files'].values(): resolve(row)
    return image


def permissions(identity):
    """Repair mode bits from the first seal, preserving all sealed content bytes."""
    out = job_directory(identity)
    image = image_bound()
    changes = []
    for name in ['executor', 'certificate-bench']:
        path = resolve(image['files'][name])
        old_mode = path.stat().st_mode & 0o777
        path.chmod(old_mode | 0o100)
        require(ref(path) == image['files'][name], 'sealed content changed')
        changes.append(dict(file=name, before=oct(old_mode), after=oct(path.stat().st_mode & 0o777)))
    put(out/'result.json', dict(status='passed', changes=changes, image=ref(IMAGE/'binding.json'),
        reason='Initial copyfile seal preserved bytes but omitted executable mode; no failed execution or numerical changes'))


def cpu(identity):
    out = job_directory(identity)
    image = image_bound()
    p = subprocess.run([str(resolve(image['files']['certificate-bench']))],capture_output=True,text=True)
    (out/'stdout.json').write_text(p.stdout); (out/'stderr').write_text(p.stderr)
    require(p.returncode == 0, 'CPU benchmark completion')
    result = json.loads(p.stdout)
    require(result['status']=='passed' and all(s['exact'] for row in result['rows'] for s in row['samples']), 'exact CPU benchmark certificates')
    for row in result['rows']:
        row['scratch_over_workspace4_median'] = statistics.median(s['scratch_ns']/s['workspace4_ns'] for s in row['samples'])
        row['scratch_over_workspace3_median'] = statistics.median(s['scratch_ns']/s['workspace3_ns'] for s in row['samples'])
    put(out/'result.json',dict(result, quality=ref(BASE/QUALITY/'result.json'), image=ref(IMAGE/'binding.json'),
        default_promotion=False, reason='CPU microbenchmark is not complete FP4x2 solver evidence'))
    print([(r['case'],r['scratch_over_workspace4_median']) for r in result['rows']],flush=True)


def availability(identity):
    out=job_directory(identity)
    from lp_billion_idle import Nvml
    from lp_billion_availability import idle
    sensor=Nvml()
    try:sample=sensor.sample()
    finally:sensor.close()
    put(out/'result.json',dict(status='observed',idle=idle(sample),sample=sample,
        gpu_admission=False, scope='One read-only sample; no sustained-idle proof or device workload'))
    print(dict(idle=idle(sample),used_gib=sample['used']/2**30,utilization=sample['utilization']),flush=True)


def idle_window(identity):
    out=job_directory(identity)
    from lp_billion_availability import observe, proof
    require(not (BASE/'availability'/identity).exists(),'fresh availability identity')
    for index in range(7):
        if index:time.sleep(60)
        observe(identity)
    proof(identity)
    put(out/'result.json',dict(status='passed',proof=ref(BASE/'availability'/(identity+'.json'))))


def invoke(command, requests, out, name):
    put(out/(name+'.requests.json'),requests)
    p=subprocess.run(list(map(str,command)),input=''.join(json.dumps(r,allow_nan=False)+'\n' for r in requests),
        text=True,capture_output=True,timeout=180)
    (out/(name+'.stdout.jsonl')).write_text(p.stdout);(out/(name+'.stderr')).write_text(p.stderr)
    require(p.returncode==0,'candidate command '+name+': '+p.stderr[-1000:])
    responses=[json.loads(line) for line in p.stdout.splitlines()]
    require(len(responses)==len(requests),'complete response coverage')
    return responses


def audit_response(response,model,store,out,name):
    from lp_billion_full_audit import requests, validate
    from lp_billion_full_audit_v2 import certification_status
    queries,mapping,endpoints=requests(response,True)
    answers=invoke([BASE/'image-v1/executor','assess',model,store],queries,out,name)
    accepted=validate(answers,mapping,endpoints,ref(model)['sha256'],True)
    certification_status(response,True,accepted)
    return dict(checks=len(answers),endpoints=len(endpoints),accepted=accepted,results=ref(out/(name+'.stdout.jsonl')))


def correctness(identity, availability_id):
    out=job_directory(identity,True)
    require(availability_id is not None, 'fresh availability identity required')
    image_bound()
    from lp_billion_availability import stable
    from lp_general_models import generate
    from lp_general_oracle import settings
    from lp_billion_admit import validate_timings
    proof=load(BASE/'availability'/(availability_id+'.json'))
    require(proof['status']=='observed_idle' and stable([load(resolve(p)) for p in proof['samples']],time.monotonic_ns()),'fresh sustained idle proof')
    old=BASE/'image-v12';rows=[]; active=False; fallback=False; long_line=False
    variants=list(itertools.product([False,True],repeat=len(FLAGS)))
    families=[('dense',257),('irregular',4097),('rectangular',4097),('ill_scaled',65),('dense_blocks',129),('dense',1025)]
    for family,size in families:
        document,_=generate(family,size,20261127+size)
        model=out/(family+str(size)+'.json');put(model,document)
        conversion=subprocess.run([str(old/'executor'),'convert',str(model),str(BASE)],text=True,capture_output=True)
        require(conversion.returncode==0,'source model conversion')
        arrays=out/(family+str(size)+'.arrays.json');put(arrays,json.loads(conversion.stdout))
        formats=['fp4x2'] if size==1025 else ['native','fp32','fp4x1','fp4x2']
        for fmt in formats:
            for fault in ([None] if size==1025 else [None,'force_recovery_after','cancel_after','deadline']):
                options={**settings(fmt),'iteration_limit':32,'check_interval':16,'wall_ms':60000}
                if fault=='deadline':options['wall_ms']=1
                elif fault:options[fault]=3
                request=dict(settings=options,tensor=dict(control_interval=8,min_tile_nnz=128),
                    fast=dict(host_reductions=True,host_preparation=True,host_certificates=True,
                        auto_schedule=True,gpu_preparation=True,gpu_packing=True,gpu_control=True,gpu_feasibility=True),profile=True)
                name=f'{family}-{size}-{fmt}-{fault}'
                before=invoke([old/'executor','solve',arrays,BASE,old/'tensor.cubin'],[request],out,name+'-reference')[0]
                if fmt == 'fp4x2' and fault is None:
                    active |= before['accepted_product_work'][1] > 0
                    fallback |= before['selected_initial_format'] == 'fp32' and before['tile_count'] == 0
                    long_line |= before.get('gpu_preparation', {}).get('backend') == 'host-fallback'
                candidates=[]
                for flags in variants:
                    candidate=copy.deepcopy(request);candidate['fast'].update(zip(FLAGS,flags));candidates.append(candidate)
                after=invoke([IMAGE/'executor','solve',arrays,BASE,IMAGE/'tensor.cubin'],candidates,out,name+'-candidates')
                for index,result in enumerate(after):
                    validate_timings(result,True)
                    require(semantic(before)==semantic(result),'exact continuation '+name+' '+str(index))
                    audit=audit_response(result,arrays,BASE,out,name+'-proof-'+str(index))
                    rows.append(dict(case=name,variant=index,exact=True,audit=audit,
                        response_file=ref(out/(name+'-candidates.stdout.jsonl'))))
                print(dict(case=name,exact_variants=len(after)),flush=True)
    require(active and fallback and long_line, 'real FP4, zero-eligible and long-line fallback coverage')
    # Stress all new ownership/control paths with the unchanged CUDA modules.
    from lp_billion_prepare_admit import instrument
    from lp_billion_gpu_control_admit import sanitizer_clean
    sanitizers=[]
    for sanitizer in ['memcheck','racecheck','initcheck','synccheck']:
        for family,size in [('dense',257),('irregular',4097)]:
            arrays=out/(family+str(size)+'.arrays.json')
            for fault in [None,'force_recovery_after','cancel_after']:
                opts={**settings('fp4x2'),'iteration_limit':32,'check_interval':16,'wall_ms':60000}
                if fault:opts[fault]=3
                request=dict(settings=opts,tensor=dict(control_interval=8,min_tile_nnz=128),fast={**dict.fromkeys(FLAGS,True),
                    'host_preparation':True,'gpu_preparation':True,'gpu_packing':True,'gpu_control':True,'gpu_feasibility':True},profile=True)
                name=f'{sanitizer}-{family}-{fault}';log=out/(name+'.sanitizer')
                command=instrument([str(IMAGE/'executor'),'solve',str(arrays),str(BASE),str(IMAGE/'tensor.cubin')],sanitizer,log)
                response=invoke(command,[request],out,name)[0];sanitizer_clean(log)
                sanitizers.append(dict(tool=sanitizer,case=name,log=ref(log),audit=audit_response(response,arrays,BASE,out,name+'-proof')))
    put(out/'result.json',dict(status='passed',rows=rows,sanitizers=sanitizers,image=ref(IMAGE/'binding.json'),
        availability=ref(BASE/'availability'/(availability_id+'.json')),coverage=dict(fp4_active=active,zero_eligible=fallback,long_line=long_line),preservation=preservation()))


def environment(identity):
    directory = BASE/'fp4x2-overhead-env'
    require(not directory.exists(), 'fresh isolated Python environment')
    out, checks = commands(identity, [
        ('venv', [sys.executable, '-m', 'venv', '--system-site-packages', str(directory)]),
        ('dependencies', [str(directory/'bin/python'), '-m', 'pip', 'install', '--no-cache-dir',
                          '--disable-pip-version-check', '--no-deps', 'scipy==1.16.3', 'Markdown==3.7']),
        ('versions', [str(directory/'bin/python'), '-c',
                      'import numpy, scipy, markdown; print(numpy.__version__, scipy.__version__, markdown.__version__)']),
    ])
    put(out/'result.json', dict(status='passed', checks=checks, environment=str(directory),
        purpose='CPU-only focused PR30 regression and documentation dependencies'))


def verify(identity):
    image_bound()
    cpu_result = load(BASE/'fp4x2-certificate-measure-v1/result.json')
    observation = load(BASE/'fp4x2-overhead-availability-v1/result.json')
    for job in [QUALITY, 'fp4x2-overhead-seal-v1', 'fp4x2-overhead-permissions-v1',
                'fp4x2-certificate-measure-v1', 'fp4x2-overhead-availability-v1']:
        passed(job)
    summary = dict(status='CPU_validated_GPU_pending', strict_original_model_tolerance=1e-9,
        default_promotion=False, gpu_admission=False, rust_tests=73,
        preservation=preservation(), cpu_microbenchmark=cpu_result,
        availability=observation, quality=ref(BASE/QUALITY/'result.json'),
        scope_plan=ref(BASE/'fp4x2-overhead-v1/plan.json'),
        limitation='No GPU continuation, sanitizer or complete FP4x2 performance evidence; CPU component timings cannot promote defaults')
    summary_path = ROOT/'docs/benchmarks/lp-fp4x2-overhead-results.json'
    if summary_path.exists():
        require(load(summary_path) == summary, 'existing compact evidence differs')
    else:
        put(summary_path, summary)
    interpreter = str(BASE/'fp4x2-overhead-env/bin/python')
    out, checks = commands(identity, [
        ('policy', [interpreter, '-B', '-m', 'unittest', 'discover', '-s', 'tests/integration', '-p', 'test_lp_billion_fp4x2_overhead.py']),
        ('pricing_pipeline', [interpreter, '-B', '-m', 'unittest', 'discover', '-s', 'tests/integration', '-p', 'test_lp_sp_pricing_pipeline*.py']),
        ('pricing_parallel_proof', [interpreter, '-B', '-m', 'unittest', 'discover', '-s', 'tests/integration', '-p', 'test_lp_sp_pricing_primal_parallel.py']),
        ('docs', [interpreter, '-B', 'tools/build_docs.py', '--output', str(BASE/identity/'book')]),
        ('diff', ['git', 'diff', '--check']),
    ])
    put(out/'result.json',dict(status='passed',checks=checks,preservation=preservation(),
        summary=ref(ROOT/'docs/benchmarks/lp-fp4x2-overhead-results.json'),
        gpu_validated=False,default_promotion=False))


def cleanup(identity):
    out = job_directory(identity)
    passed('fp4x2-overhead-report-check-v2')
    passed('fp4x2-overhead-environment-v1')
    image_bound()
    removed = []
    for path in [BASE/'fp4x2-overhead-env', BASE/'fp4x2-overhead-report-check-v2/book']:
        require(path.is_dir() and not path.is_symlink(), 'owned generated directory required')
        shutil.rmtree(path)
        removed.append(str(path.relative_to(BASE)))
    put(out/'result.json', dict(status='passed', removed=removed, preservation=preservation(),
        retained='All images, measurements, logs, receipts, source objects and failure charges'))


def finalize(identity):
    from lp_billion_budget import accounting
    from lp_billion_common import CPU_CAPS, GPU_CAPS, NS
    image_bound()
    passed('fp4x2-overhead-report-check-v2')
    passed('fp4x2-overhead-cleanup-v1')
    jobs = []
    for path in sorted((BASE/'resources').glob('fp4x2-*.reservation.json')):
        name = path.name.removesuffix('.reservation.json')
        if name == identity:
            continue
        require((BASE/'resources'/(name+'.settlement.json')).exists(), 'prior unsettled job')
        settlement = load(BASE/'resources'/(name+'.settlement.json'))
        require(settlement['cleanup_empty'] and not settlement['overrun'], 'clean bounded settlement')
        jobs.append(dict(identity=name, settlement=settlement,
            receipt=ref(BASE/'resources'/(name+'.settlement.json'))))
    cpu_used, gpu_used = accounting()
    require(all(cpu_used[k] <= v*NS for k,v in CPU_CAPS.items()), 'CPU phase limits')
    require(all(gpu_used[k] <= v*NS for k,v in GPU_CAPS.items()), 'GPU phase limits')
    checkpoint = ROOT/'docs/benchmarks/lp-fp4x2-overhead-checkpoint.json'
    put(checkpoint, dict(status='CPU_validated_GPU_pending', defaults_promoted=False,
        strict_tolerance=1e-9, preservation=preservation(), completed_jobs=jobs,
        completed_job_cpu_ns=sum(j['settlement']['cpu_ns'] for j in jobs),
        completed_job_gpu_ns=sum(j['settlement']['gpu_ns'] for j in jobs),
        retained_failed_cpu_ns=sum(j['settlement']['cpu_ns'] for j in jobs if j['settlement']['status']!='passed'),
        cpu_by_phase_including_final_reservation_ns=cpu_used,
        gpu_by_phase_including_final_reservation_ns=gpu_used,
        final_reporting_reservation=ref(BASE/'resources'/(identity+'.reservation.json')),
        final_settlement_path='resources/'+identity+'.settlement.json',
        verification=ref(BASE/'fp4x2-overhead-report-check-v2/result.json'),
        note='This checkpoint lists settled jobs before its own reporting reservation; the final settlement supplies that last actual charge'))
    out, checks = commands(identity, [
        ('docs', [sys.executable, '-B', 'tools/build_docs.py', '--output', str(BASE/identity/'book')]),
        ('diff', ['git', 'diff', '--check']),
    ])
    shutil.rmtree(out/'book')
    put(out/'result.json',dict(status='passed',checks=checks,preservation=preservation(),checkpoint=ref(checkpoint),
        gpu_validated=False,default_promotion=False))


def promotion(rows,correctness=False):
    """Only matched complete outcomes can support promotion; failures stay visible."""
    reasons=[]
    if not correctness:reasons.append('correctness gates incomplete')
    families={r['family'] for r in rows}
    if not families:reasons.append('no complete measurements')
    if rows and (not any(r.get('fp4_share',0)>0 for r in rows) or not any(r.get('fp4_share',0)==0 for r in rows)):
        reasons.append('FP4-active and fallback coverage required')
    for family in families:
        group=[r for r in rows if r['family']==family]
        if len({r['seed'] for r in group})<3:reasons.append('three seeds required: '+family)
    for r in rows:
        if not r.get('exact') or not r.get('audited') or not r.get('memory_admitted') or r.get('status') not in ['certified','limit']:
            reasons.append('unmatched, unaudited, failed or resource-refused outcome')
        if any(not isinstance(r.get(k), (int,float)) or not math.isfinite(r[k]) or r[k] <= 0 for k in ['reference_ns','candidate_ns']):
            reasons.append('missing or invalid complete timing')
    speedups=[]
    if not reasons:
        speedups=[r['reference_ns']/r['candidate_ns'] for r in rows]
        if statistics.median(speedups)<1.05:reasons.append('median improvement below five percent')
        for family in families:
            ratios=[r['candidate_ns']/r['reference_ns'] for r in rows if r['family']==family]
            if statistics.median(ratios)>1.05:reasons.append('family regression exceeds five percent: '+family)
    return dict(promote=not reasons,reasons=sorted(set(reasons)),pairs=len(rows),
                median_speedup=statistics.median(speedups) if speedups else None,
                scope='matched certified or fixed-work iteration-limit complete costs; no deadline regrading')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['seal','cpu','availability','idle_window','correctness','permissions','verify','environment','cleanup','finalize'])
    p.add_argument('--availability-id');p.add_argument('--id',required=True)
    a=p.parse_args()
    if a.action=='correctness':correctness(a.id,a.availability_id)
    else:globals()[a.action](a.id)
