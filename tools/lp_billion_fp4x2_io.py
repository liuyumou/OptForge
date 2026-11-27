"""Guarded CPU-only input and strict-proof optimization evaluation."""
import argparse
import json
import shutil
import statistics
import subprocess
import sys
from lp_billion_common import BASE, ROOT, put, load, ref, resolve, require
from lp_billion_fp4x2_overhead import commands, preservation, quality
from lp_billion_readmission import passed

QUALITY='fp4x2-io-quality-v4'
SCOPE=BASE/'fp4x2-io-v1'


def plan(identity):
    out=BASE/identity
    out.mkdir(exist_ok=False)
    require(load(BASE/'resources'/(identity+'.reservation.json'))['command'][-1]==identity,'supervised plan')
    SCOPE.mkdir(exist_ok=False)
    sources=[]
    for name in ['src/array_input.rs','src/host-lp/problem.rs','src/certificate_workspace.rs','src/certificate_staged.rs','src/bin/billion.rs']:
        source=ROOT/'research/lp-billion-lowbit'/name
        dest=SCOPE/'baseline'/name
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,dest)
        sources.append(dict(original=ref(source),retained=ref(dest)))
    put(SCOPE/'plan.json',dict(base='7647a3d',protocol=ref(ROOT/'docs/specifications/SPEC-0046-amendment-96.md'),sources=sources,preservation=preservation(),gpu=False))
    put(out/'result.json',dict(status='passed',plan=ref(SCOPE/'plan.json')))


def check(identity):
    out,checks=commands(identity,[
        ('format',['cargo','fmt','--manifest-path','research/lp-billion-lowbit/Cargo.toml']),
        ('check',['cargo','check','--manifest-path','research/lp-billion-lowbit/Cargo.toml','--all-targets','--offline']),
        ('clippy',['cargo','clippy','--manifest-path','research/lp-billion-lowbit/Cargo.toml','--all-targets','--offline','--','-D','warnings']),
    ])
    put(out/'result.json',dict(status='passed',checks=checks,preservation=preservation()))


def bound():
    passed(QUALITY)
    for row in load(BASE/'sources'/QUALITY/'manifest.json')['sources']:
        if row['original']['path'].startswith('research/lp-billion-lowbit/'):
            resolve(row['original']);resolve(row['retained'])
    for row in load(SCOPE/'plan.json')['sources']:resolve(row['retained'])
    return preservation()


def measure(identity):
    reservation=load(BASE/'resources'/(identity+'.reservation.json'))
    require(not reservation['gpu'] and reservation['command'][-1]==identity,'matching CPU-only measurement')
    bound()
    out=BASE/identity;out.mkdir(exist_ok=False)
    for executable in ['fp4x2_io_bench','billion']:
        shutil.copy2(BASE/'target/release'/executable,out/executable)
    rows=[]
    with (out/'stderr').open('w') as err,(out/'stdout.jsonl').open('w') as raw:
        p=subprocess.Popen([str(out/'fp4x2_io_bench'),str(out/'data'),str(out/'billion')],stdout=subprocess.PIPE,stderr=err,text=True)
        for line in p.stdout:
            raw.write(line);raw.flush()
            row=json.loads(line)
            require(all(sample['exact'] for sample in row['samples']) and row['synthetic_data_removed_after_exact_checks'],'exact comparison and audited cleanup')
            rows.append(row)
            print(dict(case=row['case'],seed=row['seed'],complete=len(rows)),flush=True)
        require(p.wait()==0,'complete CPU benchmark')
    require(len(rows)==12 and not (out/'data').exists(),'all fresh fixtures complete and removed')
    aggregates=[]
    for case in dict.fromkeys(row['case'] for row in rows):
        group=[row for row in rows if row['case']==case]
        ratio=lambda f:statistics.median(statistics.median(f(sample) for sample in row['samples']) for row in group)
        aggregates.append(dict(case=case,
            input_chunks=ratio(lambda s:s['inputs'][0]['total_ns']/s['inputs'][1]['total_ns']),
            input_transpose=ratio(lambda s:s['inputs'][0]['total_ns']/s['inputs'][2]['total_ns']),
            input_combined=ratio(lambda s:s['inputs'][0]['total_ns']/s['inputs'][3]['total_ns']),
            certificate=ratio(lambda s:s['certificate_ns'][0]/s['certificate_ns'][1]),
            complete_input_only=ratio(lambda s:s['processes'][0]['complete_ns']/s['processes'][1]['complete_ns']),
            complete_proof_only=ratio(lambda s:s['processes'][0]['complete_ns']/s['processes'][2]['complete_ns']),
            complete_combined=ratio(lambda s:s['processes'][0]['complete_ns']/s['processes'][3]['complete_ns'])))
    put(out/'result.json',dict(status='passed',rows=rows,aggregates=aggregates,
        quality=ref(BASE/QUALITY/'result.json'),benchmark=ref(out/'fp4x2_io_bench'),executor=ref(out/'billion'),
        preservation=bound(),gpu=False,defaults_promoted=False,
        input_modes=['original','parallel_chunks','parallel_transpose','both'],
        process_modes=['original_assess','parallel_input','assess_fast','both'],
        cache_scope='cold processes; OS page caches are not flushed',
        scope='fresh synthetic input and independent CPU assessment; not complete PDLP solve'))
    print(json.dumps(aggregates),flush=True)


def report(identity):
    reservation=load(BASE/'resources'/(identity+'.reservation.json'))
    require(not reservation['gpu'] and reservation['command'][-1]==identity,'matching CPU-only report')
    preserved=bound()
    measured='fp4x2-io-measure-v1'
    passed(measured)
    data=load(BASE/measured/'result.json')
    resolve(data['quality']);resolve(data['benchmark']);resolve(data['executor'])
    image=BASE/'image-fp4x2-io-v1';image.mkdir(exist_ok=False)
    files={}
    for name,item in load(BASE/'image-v12/binding.json')['files'].items():
        source=resolve(load(BASE/QUALITY/'result.json')['executor']) if name=='executor' else resolve(item)
        shutil.copy2(source,image/name);files[name]=ref(image/name)
    put(image/'binding.json',dict(status='CPU_quality_only',files=files,quality=ref(BASE/QUALITY/'result.json'),
        source_manifest=ref(BASE/'sources'/QUALITY/'manifest.json'),baseline=ref(BASE/'image-v12/binding.json')))
    passed('fp4x2-io-availability-v1')
    availability=load(BASE/'fp4x2-io-availability-v1/result.json')
    jobs=[]
    for path in sorted((BASE/'resources').glob('fp4x2-io-*.reservation.json')):
        job=path.name.removesuffix('.reservation.json')
        if job==identity:continue
        settlement=path.with_name(job+'.settlement.json');receipt=load(settlement)
        require(not receipt['gpu'] and receipt['gpu_ns']==0 and receipt['cleanup_empty'] and not receipt['overrun'],'settled bounded CPU job')
        jobs.append(dict(identity=job,reservation=ref(path),receipt=ref(settlement),settlement=receipt))
    from lp_billion_budget import accounting
    cpu,gpu=accounting()
    compact=ROOT/'docs/benchmarks/lp-fp4x2-io-proof-results.json'
    put(compact,dict(status='CPU_validated_GPU_pending',quality=ref(BASE/QUALITY/'result.json'),quality_data=load(BASE/QUALITY/'result.json'),
        measurement=ref(BASE/measured/'result.json'),measurement_data=data,image=ref(image/'binding.json'),
        preservation=preserved,availability=availability,completed_jobs=jobs,
        completed_cpu_ns=sum(j['settlement']['cpu_ns'] for j in jobs),completed_gpu_ns=0,
        failed_cpu_ns=sum(j['settlement']['cpu_ns'] for j in jobs if j['settlement']['status']!='passed'),
        global_cpu_with_current_reservation=cpu,global_gpu=gpu,
        current_reporting_reservation=ref(BASE/'resources'/(identity+'.reservation.json')),
        defaults_promoted=False,scientific_history_unchanged=True))
    out,checks=commands(identity,[
        ('policy',[sys.executable,'-B','-m','unittest','discover','-s','tests/integration','-p','test_lp_billion_fp4x2*.py']),
        ('docs',[sys.executable,'-B','tools/build_docs.py','--output',str(BASE/identity/'book')]),
        ('diff',['git','diff','--check']),
    ])
    shutil.rmtree(out/'book')
    put(out/'result.json',dict(status='passed',checks=checks,preservation=bound(),compact=ref(compact),
        image=ref(image/'binding.json'),gpu_admission=False,defaults_promoted=False,removed_generated_html=True))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['plan','check','quality','measure','report']);p.add_argument('--id',required=True)
    a=p.parse_args();globals()[a.action](a.id)
