"""SPEC-0024 immutable same-transport cold/prepared study and phase attribution."""
import argparse
import math
import os
import re
from pathlib import Path
import statistics
import subprocess
import sys
import time

from lp_resident2_common import BASE, CPU_CAPS, DEVICE, GPU_CAPS, ROOT, checked, load, put, ref, require
from lp_baseline_common import verify_certificate
from lp_resident2_budget import run

MANIFEST = BASE / 'manifest-v4.json'


def phase_totals(worker, checks, outer_ns):
    """Disjoint phase clocks plus explicit startup/teardown/metadata residual."""
    require(type(outer_ns) is int and outer_ns >= 0, 'invalid outer clock')
    rows = worker['rows']
    require(len(rows) == worker['solves'] == len(checks), 'missing solve/check phase')
    raw = [worker[name + '_ns'] for name in ('conversion', 'preparation', 'import')]
    raw += [row[name + '_ns'] for row in rows for name in ('native', 'export', 'output')] + checks
    require(all(type(v) is int and v >= 0 for v in raw), 'invalid raw phase clock')
    phases = {name: worker[name + '_ns'] for name in ('conversion', 'preparation', 'import')}
    for name in ('native', 'export', 'output'):
        phases[name] = sum(row[name + '_ns'] for row in rows)
    phases['check'] = sum(checks)
    require(all(type(v) is int and v >= 0 for v in phases.values()), 'invalid phase clock')
    require(sum(phases.values()) <= outer_ns, 'overlapping or inconsistent phase clocks')
    phases['unattributed'] = outer_ns - sum(phases.values())
    return phases


def physical_counts(row):
    """Actual host API observations; nested phase scopes are never double-counted."""
    profile=row['native_costs']
    require(not profile['unavailable'], 'incomplete native cost observation')
    scopes=profile['scopes']
    require(all(s['path'] and type(s['calls']) is int and s['calls']>=0 for s in scopes), 'invalid physical count')
    require(len({tuple(s['path']) for s in scopes})==len(scopes), 'duplicate cost path')
    names=dict(kernel_launches='kernel_submission', synchronizations='device_synchronization',
        upload_calls='host_to_device', readback_calls='device_to_host', allocations='device_allocation')
    counts={key:sum(s['calls'] for s in scopes if s['path'][-1]==name) for key,name in names.items()}
    for key,name in [('upload_bytes','host_to_device_bytes'),('readback_bytes','device_to_host_bytes'),('allocated_bytes','device_allocated_bytes')]:
        value=profile['counters'].get(name,0)
        require(type(value) is int and value>=0,'invalid physical bytes')
        counts[key]=value
    if row['error'] is None:
        require(counts['kernel_launches']==row['diagnostics']['kernel_launches'], 'submission count differs')
    return counts


def eligible(trial):
    return (trial.get('status') == 'completed' and trial.get('elapsed_ns', 0) > 0
            and all(r['accepted'] and r['stop'] == 'accepted' and r['iterations'] is not None
                    for r in trial.get('results', [])) and bool(trial.get('results')))


def compare(control, resident):
    require(all(control[k] == resident[k] for k in ('model', 'lifecycle', 'repetition', 'solves')),
            'unmatched comparison')
    if not (eligible(control) and eligible(resident)):
        return None
    return control['elapsed_ns'] / resident['elapsed_ns']


def roster(instances):
    jobs = []
    for index, instance in enumerate(instances):
        for lifecycle, reps, solves in [('cold', 3, 1), ('prepared', 1, 3)]:
            for rep in range(reps):
                modes = ['control', 'resident'] if (index + rep) % 2 == 0 else ['resident', 'control']
                for mode in modes:
                    jobs.append(dict(id=f'{index:02}-{lifecycle}-{rep}-{mode}', model=instance['model'],
                        model_id=instance['id'], lifecycle=lifecycle, repetition=rep, solves=solves, mode=mode,
                        iterations=50000, native_seconds=8, reserve_seconds=60 if solves == 1 else 100))
    return jobs


def freeze():
    gate = load(BASE/'resources/native-gate-v2.settlement.json')
    require(gate['status']=='passed' and not gate['overrun'], 'full native admission required')
    require(load(BASE/'resources/fixture-correction-v3.settlement.json')['status']=='passed', 'fixture validation required')
    checked(load(BASE/'fixture-source-bridge-v2.json')['after'])
    proposal = load(ROOT / 'benchmarks/configs/lp-external-baseline-proposal-v2.json')
    old = load(ROOT / 'artifacts/gpup-external-baseline-v5/manifest.json')
    sources = []
    for directory in ['crates', 'cuda', 'tools', 'schemas', 'research', 'tests']:
        for p in sorted((ROOT / directory).rglob('*')):
            if p.is_file() and p.suffix in ('.rs', '.cu', '.h', '.py', '.sh', '.toml', '.lock', '.json') and not any(
                    part in ('target', '__pycache__', '.venv') for part in p.parts):
                sources.append(ref(p))
    matches=re.findall(r'Running unittests src/lib.rs \(target/debug/deps/(optimizer_lp_cuda-[0-9a-f]+)\)', (BASE/'resources/fixture-correction-v3.resource.json.log').read_text())
    require(len(matches)==1, 'unambiguous current device test executable required')
    test_binary=ROOT/'target/debug/deps'/matches[0]
    image = ROOT / 'target/native/cuda/lp_pdhg_resident2.cubin'
    binary = ROOT / 'target/release/examples/lp_resident2'
    checked(old['checker'])
    for i in proposal['instances']:
        checked(i['model'])
    put(MANIFEST, dict(schema_version=1, kind='lp-resident2-manifest', device=DEVICE,
        cpu_affinity=sorted(os.sched_getaffinity(0))[:4], cpu_caps=CPU_CAPS, gpu_caps=GPU_CAPS,
        binary=ref(binary), test_binary=ref(test_binary), image=ref(image), checker=old['checker'], sources=sources,
        decision=ref(ROOT/'docs/decisions/ADR-0053-native-resident-execution.md'),
        specification=ref(ROOT/'docs/specifications/SPEC-0024-native-resident-execution.md'),
        fixture_bridge=ref(BASE/'fixture-source-bridge-v2.json'), jobs=roster(proposal['instances']),
        selection='No coverage loss; all paired certified cold model medians improve; geometric mean >=1.05 with useful work. Prepared is secondary, one batch of three, no independent uncertainty claim.'))


def verify(m):
    require(m['cpu_caps'] == CPU_CAPS and m['gpu_caps'] == GPU_CAPS and m['device'] == DEVICE, 'authority changed')
    for key in ('binary', 'test_binary', 'image', 'checker', 'decision', 'specification'):
        checked(m[key])
    for source in m['sources']:
        checked(source)
    for job in m['jobs']:
        checked(job['model'])


def worker(job_id):
    m = load(MANIFEST)
    require(os.environ.get('AI_OPTIMIZER_GPU_LEASE') == 'inherited', 'missing GPU lease')
    require(os.environ.get('CUDA_VISIBLE_DEVICES') == DEVICE, 'wrong device')
    require(sorted(os.sched_getaffinity(0)) == m['cpu_affinity'], 'wrong affinity')
    j = next(j for j in m['jobs'] if j['id'] == job_id)
    directory = BASE / 'jobs' / job_id
    directory.mkdir(parents=True, exist_ok=False)
    output = directory / 'worker'
    started = time.monotonic_ns()
    with (directory/'native.log').open('xb') as log:
        p = subprocess.run([str(checked(m['binary'])), j['mode'], str(checked(j['model'])), str(output),
            str(j['iterations']), str(j['native_seconds']), str(j['solves']), 'solve'], stdout=log, stderr=log)
    checks, results = [], []
    if p.returncode == 0:
        w = load(output/'worker.json')
        require(w['model_sha256'] == j['model']['sha256'] and w['mode'] == j['mode']
                and w['lifecycle'] == j['lifecycle'] and w['solves'] == j['solves'], 'worker identity differs')
        require(w['image_sha256'] == m['image']['sha256'], 'image changed')
        for row in w['rows']:
            candidate = output / f"candidate-{row['index']}.json"
            certificate = directory / f"certificate-{row['index']}.json"
            before = time.monotonic_ns()
            with (directory/f"checker-{row['index']}.log").open('xb') as log:
                subprocess.run([str(checked(m['checker'])), 'check', str(checked(j['model'])),
                    str(candidate), str(certificate)], check=True, stdout=log, stderr=log)
            checks.append(time.monotonic_ns()-before)
            c = verify_certificate(ref(certificate), ref(candidate), j['model'], m['checker'])
            results.append(dict(accepted=c['accepted'], candidate=ref(candidate), certificate=ref(certificate),
                iterations=row['iterations'], stop=row['stop'], error=row['error'], counters=physical_counts(row)))
        elapsed = time.monotonic_ns()-started
        phases = phase_totals(w, checks, elapsed)
        put(directory/'trial.json', dict(j, status='completed', elapsed_ns=elapsed, phases_ns=phases,
            results=results, worker=ref(output/'worker.json'), manifest=ref(MANIFEST),
            metadata_timing='Complete child delivery and independent checking; parent trial metadata write excluded.'))
    else:
        put(directory/'trial.json', dict(j, status='failed', elapsed_ns=time.monotonic_ns()-started,
            returncode=p.returncode, results=results))
    return p.returncode


def study():
    m=load(MANIFEST)
    verify(m)
    for gate in ['device-differential-v3', 'sanitizer-memcheck-v1', 'sanitizer-racecheck-v1', 'sanitizer-initcheck-v1', 'sanitizer-synccheck-v1']:
        receipt=load(BASE/'resources'/(gate+'.settlement.json'))
        require(receipt['status']=='passed' and not receipt['overrun'], 'device admission required: '+gate)
    require(load(BASE/'transport-admission.json')['status']=='passed', 'transport admission required')
    for j in m['jobs']:
        destination=BASE/'trials'/(j['id']+'.json')
        require(not destination.exists(), 'scientific cells cannot retry')
        try:
            settlement=run(j['id'],'study',j['reserve_seconds'],True,
                [sys.executable,'-B',str(Path(__file__).resolve()),'_worker',j['id']])
            trial=BASE/'jobs'/j['id']/'trial.json'
            if trial.exists():
                record=load(trial)
            else:
                record=dict(j,status='failed',results=[])
            record['settlement']=settlement
            if settlement['status'] != 'passed': record['status']='failed'
            put(destination,record)
            print(j['id'],record['status'],sum(r['accepted'] for r in record['results']),flush=True)
        except ValueError as error:
            put(destination,dict(j,status='unexecuted',reason=str(error),results=[]))


def report():
    m=load(MANIFEST)
    rows=[load(BASE/'trials'/(j['id']+'.json')) if (BASE/'trials'/(j['id']+'.json')).exists()
          else dict(j,status='unexecuted',results=[]) for j in m['jobs']]
    pairs=[]
    for c in rows:
        if c['mode']!='control': continue
        r=next(r for r in rows if r['mode']=='resident' and all(r[k]==c[k] for k in ('model_id','lifecycle','repetition')))
        pairs.append(dict(model_id=c['model_id'],lifecycle=c['lifecycle'],repetition=c['repetition'],
            ratio=compare(c,r),control_accepted=sum(x['accepted'] for x in c['results']),
            resident_accepted=sum(x['accepted'] for x in r['results'])))
    cold=[p for p in pairs if p['lifecycle']=='cold']
    medians={name:statistics.median(p['ratio'] for p in cold if p['model_id']==name)
             for name in {p['model_id'] for p in cold}
             if all(p['ratio'] is not None for p in cold if p['model_id']==name)}
    mean=math.exp(statistics.mean(math.log(x) for x in medians.values())) if medians else None
    no_loss=all(p['resident_accepted']>=p['control_accepted'] for p in pairs)
    useful=any(eligible(r) and any(x['iterations']>0 for x in r['results']) for r in rows if r['mode']=='resident')
    complete=all(r['status']!='unexecuted' for r in rows)
    retained=bool(complete and no_loss and useful and medians and all(x>1 for x in medians.values()) and mean>=1.05)
    return dict(schema_version=1,kind='lp-resident2-result',manifest=ref(MANIFEST),rows=rows,pairs=pairs,
        cold_model_medians=medians,cold_geomean=mean,no_coverage_loss=no_loss,retain_optimization=retained,
        decision='retain research optimization' if retained else 'no supported latency optimization; retain native control',
        prepared_limit='One batch of three per mode/model; descriptive throughput, not independent repetitions.')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['freeze','study','report','_worker']);p.add_argument('job',nargs='?');a=p.parse_args()
    if a.action=='freeze':freeze()
    elif a.action=='study':study()
    elif a.action=='_worker':return worker(a.job)
    else:put(ROOT/'docs/benchmarks/data/resident2-result-v1.json',report())
    return 0

if __name__=='__main__':raise SystemExit(main())
