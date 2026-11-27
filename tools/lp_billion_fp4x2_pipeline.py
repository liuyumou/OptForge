"""CPU-only FP4x2 component diagnosis and parallel-assessment follow-up."""
import argparse
import csv
import json
import shutil
import statistics
import subprocess
import sys
from pathlib import Path
from lp_billion_common import BASE, ROOT, put, load, ref, resolve, require
from lp_billion_fp4x2_overhead import commands, preservation, quality
from lp_billion_readmission import passed

QUALITY = 'fp4x2-pipeline-quality-v4'
SCOPE = BASE/'fp4x2-pipeline-v1'


def directory(identity):
    reservation = load(BASE/'resources'/(identity+'.reservation.json'))
    require(not reservation['gpu'] and reservation['command'][-1] == identity,
            'matching CPU-only reservation required')
    out = BASE/identity
    out.mkdir(exist_ok=False)
    return out


def diagnose(identity):
    out = directory(identity)
    preservation()
    source = ROOT/'docs/benchmarks/lp-billion-gpu-control-phases.csv'
    rows = list(csv.DictReader(source.open()))
    result = []
    for row in rows:
        if row['version'] != 'v11' or row['timing_eligible'] != 'True':
            continue
        complete = float(row['complete_seconds'])
        phases = {k.removesuffix('_seconds'): float(v) for k, v in row.items()
                  if k.endswith('_seconds') and v and k not in ['complete_seconds','preparation_seconds','packing_seconds']}
        require(abs(sum(phases.values())-complete) < 1e-6, 'exclusive phase coverage')
        result.append(dict(scale=row['scale'],family=row['family'],status=row['status'],
            certified=row['certified']=='True',fp4_share=float(row['fp4_work_share']),complete_seconds=complete,
            phases_seconds=phases, largest=sorted(phases,key=phases.get,reverse=True)[:6]))
    SCOPE.mkdir(exist_ok=False)
    original = ROOT/'research/lp-billion-lowbit/src/certificate_workspace.rs'
    shutil.copy2(original, SCOPE/'certificate_workspace_v1.rs')
    put(SCOPE/'plan.json', dict(base_commit='0e59839', protocol=ref(ROOT/'docs/specifications/SPEC-0046-amendment-95.md'),
        previous_workspace=ref(SCOPE/'certificate_workspace_v1.rs'), preservation=preservation(),
        stages=['weighted CPU certificate work','reuse control snapshots and downloads','overlap same-snapshot GPU feasibility/CPU proof/output'],
        gpu_jobs=False,default_promotion=False))
    put(out/'result.json',dict(status='passed',source=ref(source),rows=result,plan=ref(SCOPE/'plan.json'),
        limitation='Retained v11 descriptive timings; unequal work, deadlines and independent final proof remain visible; not a new GPU profile'))
    print(json.dumps([dict(scale=r['scale'],family=r['family'],complete=r['complete_seconds'],largest=r['largest']) for r in result]),flush=True)


def check(identity):
    out, checks=commands(identity,[
        ('format',['cargo','fmt','--manifest-path','research/lp-billion-lowbit/Cargo.toml','--check']),
        ('check',['cargo','check','--manifest-path','research/lp-billion-lowbit/Cargo.toml','--all-targets','--offline']),
        ('clippy',['cargo','clippy','--manifest-path','research/lp-billion-lowbit/Cargo.toml','--all-targets','--offline','--','-D','warnings']),
    ])
    put(out/'result.json',dict(status='passed',checks=checks,preservation=preservation()))


def compile_release(identity):
    out, checks=commands(identity,[
        ('format',['cargo','fmt','--manifest-path','research/lp-billion-lowbit/Cargo.toml','--check']),
        ('compile_tests',['cargo','test','--manifest-path','research/lp-billion-lowbit/Cargo.toml','--release','--offline','--no-run']),
        ('clippy',['cargo','clippy','--manifest-path','research/lp-billion-lowbit/Cargo.toml','--all-targets','--offline','--','-D','warnings']),
    ])
    put(out/'result.json',dict(status='passed',checks=checks,preservation=preservation(),tests_executed=False))


def bound():
    passed(QUALITY)
    for row in load(BASE/'sources'/QUALITY/'manifest.json')['sources']:
        if row['original']['path'].startswith('research/lp-billion-lowbit/'):
            resolve(row['original']); resolve(row['retained'])
    previous=resolve(load(SCOPE/'plan.json')['previous_workspace']).read_text()
    fixture=(ROOT/'research/lp-billion-lowbit/diagnostics/fp4x2_workspace_v1.rs').read_text()
    require((ROOT/'research/lp-billion-lowbit/src/certificate_staged.rs').read_text() == previous, 'unchanged balanced certificate routine')
    require(previous[previous.index('#[derive(Default)]'):] == fixture[fixture.index('#[derive(Default)]'):], 'exact previous workspace benchmark body')
    return preservation()


def configured_evaluator():
    import lp_billion_fp4x2_evaluate as evaluator
    evaluator.QUALITY=QUALITY
    evaluator.IMAGE=BASE/'image-fp4x2-pipeline-v2'
    evaluator.FLAGS=tuple(dict.fromkeys((*evaluator.FLAGS,'host_state_reuse')))
    return evaluator


def seal(identity):
    bound()
    configured_evaluator().seal(identity)


def correctness(identity, availability_id):
    bound()
    configured_evaluator().correctness(identity,availability_id)


def measure(identity):
    out = directory(identity)
    bound()
    executable = BASE/'target/release/fp4x2_pipeline_bench'
    shutil.copy2(executable,out/'benchmark')
    p = subprocess.run([str(out/'benchmark')],capture_output=True,text=True)
    (out/'stdout.json').write_text(p.stdout);(out/'stderr').write_text(p.stderr)
    require(p.returncode==0,'CPU benchmark completion')
    data=json.loads(p.stdout)
    require(data['status']=='passed' and all(s['exact'] for row in data['rows'] for s in row['samples']),'exact benchmark certificates')
    for row in data['rows']:
        row['previous_over_new4_median']=statistics.median(s['previous4_ns']/s['workspace4_ns'] for s in row['samples'])
        row['previous_over_new3_median']=statistics.median(s['previous4_ns']/s['workspace3_ns'] for s in row['samples'])
    put(out/'result.json',dict(data,quality=ref(BASE/QUALITY/'result.json'),executable=ref(out/'benchmark'),
        previous_workspace=load(SCOPE/'plan.json')['previous_workspace'],defaults_promoted=False))
    print([(r['case'],r['seed'],r['previous_over_new4_median']) for r in data['rows']],flush=True)


def report(identity):
    reservation = load(BASE/'resources'/(identity+'.reservation.json'))
    require(not reservation['gpu'] and reservation['command'][-1] == identity,
            'matching CPU-only reporting reservation required')
    preserved = bound()
    passed('fp4x2-pipeline-seal-v2')
    configured_evaluator().image_bound()
    measurements = []
    for version in range(1,5):
        job = f'fp4x2-pipeline-measure-v{version}'
        passed(job)
        data = load(BASE/job/'result.json')
        resolve(data['quality']); resolve(data['executable'])
        require(all(s['exact'] for row in data['rows'] for s in row['samples']),
                'every comparison retains exact certificate bits')
        aggregates = []
        for case in dict.fromkeys(row['case'] for row in data['rows']):
            rows = [row for row in data['rows'] if row['case'] == case]
            aggregates.append(dict(case=case,
                previous4_over_new4=statistics.median(r['previous_over_new4_median'] for r in rows),
                previous4_over_new3=statistics.median(r['previous_over_new3_median'] for r in rows)))
        measurements.append(dict(version=version, result=ref(BASE/job/'result.json'),
            data=data, aggregates=aggregates,
            interpretation='comparison-context confound; retained only' if version==1 else
                'superseded implementation; all regressions retained' if version<4 else
                'final candidate; CPU component evidence only'))
    jobs = []
    for path in sorted((BASE/'resources').glob('fp4x2-pipeline-*.reservation.json')):
        job = path.name.removesuffix('.reservation.json')
        if job == identity:
            continue
        settled = path.with_name(job+'.settlement.json')
        receipt = load(settled)
        require(not receipt['gpu'] and receipt['gpu_ns']==0 and
                receipt['cleanup_empty'] and not receipt['overrun'], 'settled CPU-only job')
        jobs.append(dict(identity=job, reservation=ref(path), receipt=ref(settled), settlement=receipt))
    from lp_billion_budget import accounting
    cpu, gpu = accounting()
    compact = ROOT/'docs/benchmarks/lp-fp4x2-pipeline-results.json'
    diagnosis = BASE/'fp4x2-pipeline-diagnosis-v1/result.json'
    passed('fp4x2-pipeline-diagnosis-v1')
    resolve(load(diagnosis)['source'])
    put(compact, dict(status='CPU_validated_GPU_pending', defaults_promoted=False,
        preservation=preserved, quality=ref(BASE/QUALITY/'result.json'),
        quality_data=load(BASE/QUALITY/'result.json'),
        image=ref(BASE/'image-fp4x2-pipeline-v2/binding.json'),
        diagnosis=ref(diagnosis), diagnosis_data=load(diagnosis), measurements=measurements,
        completed_jobs=jobs, completed_cpu_ns=sum(j['settlement']['cpu_ns'] for j in jobs),
        completed_gpu_ns=0,
        failed_cpu_ns=sum(j['settlement']['cpu_ns'] for j in jobs if j['settlement']['status']!='passed'),
        global_cpu_including_current_reservation=cpu, global_gpu=gpu,
        current_reporting_reservation=ref(BASE/'resources'/(identity+'.reservation.json')),
        note='Reporting reservation is shown at its full reserve until its separate settlement; no GPU admission or complete-solver speedup claim'))
    out, checks = commands(identity, [
        ('policy', [sys.executable,'-B','-m','unittest','discover','-s','tests/integration','-p','test_lp_billion_fp4x2*.py']),
        ('docs', [sys.executable,'-B','tools/build_docs.py','--output',str(BASE/identity/'book')]),
        ('diff', ['git','diff','--check']),
    ])
    shutil.rmtree(out/'book')
    put(out/'result.json',dict(status='passed', checks=checks, preservation=bound(),
        compact=ref(compact), gpu_admission=False, defaults_promoted=False,
        removed_generated_html=True))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['diagnose','check','quality','measure','compile_release','seal','correctness','report']);p.add_argument('--availability-id');p.add_argument('--id',required=True)
    a=p.parse_args()
    if a.action=='correctness':correctness(a.id,a.availability_id)
    else:globals()[a.action](a.id)
