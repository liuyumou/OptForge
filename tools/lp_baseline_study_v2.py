"""Freeze, admit and report the full bounded GPUP-BASELINE roster."""
import argparse
import math
import os
from pathlib import Path
import random
import shutil
import statistics
import subprocess
import sys
import tarfile
import time
import copy
import inspect

from lp_baseline_common_v2 import (BASE, CPU_CAPS, DEVICE, GPU_CAPS, NS, PROPOSAL,
    ROOT, checked, load, put, ref, require, verify_certificate)
from lp_baseline_contract import screening_jobs, validate_endpoint, validate_proposal as validate_original_proposal
from lp_baseline_budget_v2 import accounting, run as reserve
from validate_artifacts import validator

MANIFEST = BASE / 'manifest.json'
CHECKER = ROOT / 'research/lp-external-baseline/target/release/lp-external-baseline'
CUOPT = ROOT / 'artifacts/cuopt-26.10.0-cu13/venv/bin/python'
COPT = ROOT / 'artifacts/gpup-copt-adapter-env/venv/bin/python'
PRIOR = ROOT/'artifacts/gpup-external-baseline-v1'


def validate_proposal(proposal, verify_artifacts=False):
    validator('lp-baseline-proposal-v2.schema.json').validate(proposal)
    expected = load(ROOT/'benchmarks/configs/lp-external-baseline-proposal-v1.json')
    expected['id']='gpup-external-baseline-v2'
    for c in expected['configurations']:
        if c['solver'] in ('project','highs'): c['parameters']['threads']=1
    require(proposal==expected, 'corrected proposal has unauthorized differences')
    original=copy.deepcopy(proposal)
    original['id']='gpup-external-baseline-v1'
    for c in original['configurations']:
        if c['solver'] in ('project','highs'): c['parameters']['threads']=4
    validate_original_proposal(original,verify_artifacts=verify_artifacts)


def retained_admission(configurations):
    import lp_baseline_adapters as prior_adapter
    import lp_baseline_adapters_v2 as current_adapter
    require(inspect.getsource(prior_adapter.copt)==inspect.getsource(current_adapter.copt), 'COPT implementation changed')
    old=load(PRIOR/'manifest.json')
    require(ref(CHECKER)['sha256']==old['checker']['sha256'], 'retained checker binary differs')
    for c in configurations:
        if c['solver']=='copt':
            require(c==next(v for v in old['configurations'] if v['id']==c['id']), 'COPT configuration differs')
    references=[ref(PRIOR/'manifest.json'),ref(PRIOR/'report.json')]
    references += [ref(p) for p in sorted((PRIOR/'resources').glob('*.settlement.json'))]
    for kind in ('project','cuopt'):
        p=PRIOR/('hardware-'+kind+'.json')
        require(load(p)['status']=='passed', 'retained hardware did not pass')
        shutil.copy2(p,BASE/p.name)
        references.append(ref(p))
    return references


def support():
    """Separate immutable validator overlay; never mutate the cuOpt installation."""
    import importlib
    directory = BASE / 'python-support'
    directory.mkdir(parents=True, exist_ok=False)
    for name in ('jsonschema', 'jsonschema_specifications', 'referencing', 'rpds', 'attr', 'attrs'):
        module = importlib.import_module(name)
        source = Path(module.__file__).parent
        shutil.copytree(source, directory / name, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    return [ref(p) for p in sorted(directory.rglob('*')) if p.is_file()]


def freeze():
    proposal = load(PROPOSAL)
    validate_proposal(proposal, verify_artifacts=True)
    require(not MANIFEST.exists(), 'execution identity already frozen')
    BASE.mkdir(parents=True, exist_ok=True)
    reused = retained_admission(proposal['configurations'])
    overlay = support()
    inventory = subprocess.check_output(['nvidia-smi', '--query-gpu=uuid,name,driver_version,memory.total', '--format=csv,noheader'], text=True)
    require(DEVICE + ', NVIDIA RTX PRO 6000 Blackwell Server Edition' in inventory, 'selected device differs')
    project = ROOT / 'artifacts/gpup-tensor-expanded-v1/study-v1/optimizer'
    old = load(ROOT/'artifacts/gpup-tensor-expanded-v1/study-v1/freeze.json')
    require(ref(project) in old['files'], 'retained executable binding differs')
    code = ROOT/'artifacts/gpup-tensor-expanded-v1/study-v1'
    binaries = BASE / 'bin'
    binaries.mkdir(exist_ok=False)
    shutil.copy2(CHECKER, binaries/'checker')
    shutil.copy2(Path(sys.executable).resolve(), binaries/'python-runtime')
    source_paths = subprocess.check_output(['git','ls-files','-z'], cwd=ROOT).decode().split('\0')
    source_paths += [str(p.relative_to(ROOT)) for group in [
        ROOT.glob('tools/lp_baseline*.py'), ROOT.glob('schemas/lp-baseline*.json'),
        ROOT.glob('tests/integration/test_lp_baseline*.py'),
        (ROOT/'research/lp-external-baseline/src').glob('*.rs')]
        for p in group]
    source_paths += ['research/lp-external-baseline/Cargo.toml','research/lp-external-baseline/Cargo.lock',
                     'docs/decisions/ADR-0049-baseline-adapter-correction.md']
    source_paths = sorted(set(p for p in source_paths if p and (ROOT/p).is_file()))
    sources = [ref(ROOT/p) for p in source_paths]
    with tarfile.open(BASE/'source.tar.gz','x:gz') as archive:
        for p in source_paths: archive.add(ROOT/p, arcname=p, recursive=False)
    source = put(BASE/'sources.json', dict(files=sources, archive=ref(BASE/'source.tar.gz')))
    # Hash loaded native code and package files, not license contents. The setup
    # lock remains the pinned package authority; this adds exact installed bytes.
    env_paths = []
    for env_root in (CUOPT.parent.parent/'lib/python3.11/site-packages', COPT.parent.parent/'lib/python3.11/site-packages'):
        for p in env_root.rglob('*'):
            if p.is_file() and (p.suffix in ('.py','.json') or '.so' in p.name) and '__pycache__' not in p.parts:
                env_paths.append(p)
    environment = put(BASE/'environment.json', dict(
        python_runtime=ref(binaries/'python-runtime'),
        native_and_python_files=[ref(p) for p in sorted(set(env_paths))], validator_overlay=overlay,
        cuopt_lock=ref(ROOT/'tools/cuopt-requirements-cu13.lock'),
        copt_environment=ref(ROOT/'artifacts/gpup-copt-adapter-env/identity.json'),
        highs_library=ref(ROOT/'target/native/highs-1.11.0/install/lib/libhighs.a'),
        inventory=inventory, driver='580.105.08', host_python=sys.version))
    jobs = []
    instances = {i['id']:i for i in proposal['instances']}
    for config in proposal['configurations']:
        for index, name in enumerate(proposal['smoke_instance_ids']):
            id_ = 'admission-' + config['id'] + '-' + str(index)
            jobs.append(dict(id=id_, configuration=config['id'], phase='admission',
                model=instances[name]['model'], model_id=name, repetition=index,
                directory=str((BASE/'jobs'/id_).relative_to(ROOT))))
    for j in screening_jobs(proposal):
        model, repetition, config = j['instance_id'], j['repetition'], j['configuration_id']
        id_ = f'screening-{model}-{repetition}-{config}'
        jobs.append(dict(id=id_, configuration=config, phase='screening', model=instances[model]['model'],
            model_id=model, repetition=repetition, directory=str((BASE/'jobs'/id_).relative_to(ROOT))))
    manifest = dict(schema_version=1, kind='lp-baseline-execution', id='gpup-external-baseline-v2',
        proposal=ref(PROPOSAL), decision=ref(ROOT/'docs/decisions/ADR-0049-baseline-adapter-correction.md'),
        sources=source, adapter=ref(ROOT/'tools/lp_baseline_adapters_v2.py'), environment=environment,
        checker=ref(binaries/'checker'), project_binary=ref(project),
        project_cuda_directory=str(code.relative_to(ROOT)),
        project_images=[ref(p) for p in sorted(code.glob('*.cubin'))],
        project_configuration=ref(ROOT/'benchmarks/configs/lp-convergence-v1.json'),
        device_uuid=DEVICE, cpu_affinity=sorted(os.sched_getaffinity(0))[:4],
        cpu_caps_seconds=CPU_CAPS, gpu_caps_seconds=GPU_CAPS, configurations=proposal['configurations'], jobs=jobs,
        interpreters=dict(cuopt=str(CUOPT.relative_to(ROOT)), copt=str(COPT.relative_to(ROOT)),
                          project=sys.executable, highs=sys.executable),
        historical_ledger=ref(ROOT/'artifacts/lp-campaign-ledgers/gpup-baseline-v1/ledger.jsonl'),
        hardware_jobs=['project-device-probe','cuopt-context-probe'],
        source_policy='all behavior and dependencies immutable after freeze; task/report documentation may evolve',
        reused_evidence=reused)
    validator('lp-baseline-execution-v2.schema.json').validate(manifest)
    put(MANIFEST, manifest)
    for j in jobs:
        if j['phase']=='admission' and j['configuration'].startswith('copt-'):
            old_path=PRIOR/'trials'/(j['id']+'.json')
            old=load(old_path)
            require(old['status']=='passed' and old['job']['model']==j['model'], 'retained admission mismatch')
            view=dict(old,job=j,reused_trial=ref(old_path),reuse_basis='Identical COPT function/configuration/models/checker; no numerical rerun.')
            put(BASE/'trials'/(j['id']+'.json'),view)
    print('Frozen',len(jobs),'jobs; no solver work performed.',flush=True)


def verify_freeze(m):
    validator('lp-baseline-execution-v2.schema.json').validate(m)
    proposal = load(checked(m['proposal']))
    validate_proposal(proposal)
    for f in m['reused_evidence']: checked(f)
    require(m['schema_version']==1 and m['kind']=='lp-baseline-execution', 'execution manifest version')
    require(m['configurations']==proposal['configurations'], 'frozen configurations differ')
    require(m['device_uuid']==DEVICE and m['cpu_caps_seconds']==CPU_CAPS and m['gpu_caps_seconds']==GPU_CAPS, 'execution authority differs')
    require(len(m['cpu_affinity'])==4 and len(set(m['cpu_affinity']))==4, 'four CPU slots required')
    require(len(m['jobs'])==260 and len({j['id'] for j in m['jobs']})==260, 'full unique job roster required')
    expected=list(screening_jobs(proposal))
    actual=[j for j in m['jobs'] if j['phase']=='screening']
    require([(j['model_id'],j['repetition'],j['configuration']) for j in actual]==
            [(j['instance_id'],j['repetition'],j['configuration_id']) for j in expected], 'screening order differs')
    for key in ('proposal','decision','sources','adapter','environment','checker','project_binary','project_configuration','historical_ledger'):
        checked(m[key])
    for f in load(checked(m['sources']))['files']:
        path = f['path']
        if path.startswith(('crates/','cuda/','research/','tools/','schemas/','tests/','benchmarks/')):
            checked(f)
    for f in m['project_images']: checked(f)
    env = load(checked(m['environment']))
    checked(env['highs_library'])
    require(Path(sys.executable).resolve().read_bytes()==checked(env['python_runtime']).read_bytes(), 'Python runtime changed')
    for f in env['native_and_python_files'] + env['validator_overlay']: checked(f)
    for j in m['jobs']: checked(j['model'])


def launched(manifest_path, job_id):
    m = load(manifest_path)
    job = next(j for j in m['jobs'] if j['id'] == job_id)
    config = next(c for c in m['configurations'] if c['id'] == job['configuration'])
    interpreter = m['interpreters'][config['solver']]
    interpreter = str(ROOT/interpreter) if not Path(interpreter).is_absolute() else interpreter
    env = {**os.environ, 'PYTHONPATH':str(BASE/'python-support'), 'PYTHONDONTWRITEBYTECODE':'1'}
    start = time.monotonic_ns()
    p = subprocess.run([interpreter,'-B',str(ROOT/'tools/lp_baseline_worker_v2.py'), str(manifest_path),job_id], env=env)
    elapsed = time.monotonic_ns()-start
    put(BASE/'clocks'/(job_id+'.json'), dict(elapsed_ns=elapsed, returncode=p.returncode,
        definition='immediately before fresh worker launch through exit after durable endpoint and independent checker output'))
    return p.returncode


def run_phase(phase):
    m = load(MANIFEST)
    verify_freeze(m)
    configs = {c['id']:c for c in m['configurations']}
    blocked = set()
    for c in configs.values():
        if c['gpu']:
            hardware = BASE/('hardware-cuopt.json' if c['solver']=='cuopt' else 'hardware-project.json')
            if not hardware.exists() or load(hardware)['status']!='passed': blocked.add(c['id'])
    if phase == 'screening':
        for c in configs:
            required = [j for j in m['jobs'] if j['phase']=='admission' and j['configuration']==c]
            if not all((BASE/'trials'/(j['id']+'.json')).exists() and load(BASE/'trials'/(j['id']+'.json'))['status']=='passed' for j in required):
                blocked.add(c)
    for j in [j for j in m['jobs'] if j['phase']==phase]:
        path = BASE/'trials'/(j['id']+'.json')
        if path.exists():
            old = load(path)
            if phase=='admission' and old['status']!='passed': blocked.add(j['configuration'])
            continue
        if j['configuration'] in blocked:
            put(path,dict(job=j, status='unexecuted', reason='hardware or lane admission did not pass'))
            continue
        seconds = 30 if phase=='admission' else 60
        try:
            settlement = reserve(j['id'],phase,seconds,configs[j['configuration']]['gpu'],
                [sys.executable,'-B',str(Path(__file__).resolve()),'_launch',str(MANIFEST),j['id']])
        except ValueError as error:
            put(path,dict(job=j,status='unexecuted',reason=str(error)))
            if 'exhausted' in str(error): continue
            raise
        result_path = ROOT/j['directory']/'worker-result.json'
        result = load(result_path) if result_path.exists() else None
        status = settlement['status']
        if result:
            for r in result['results']:
                c = verify_certificate(r['certificate'],r['candidate'],r['original'],m['checker'])
                endpoint = load(checked(r['endpoint']))
                validate_endpoint(endpoint, load(checked(r['canonical'])),r['canonical']['sha256'])
                require(c['accepted']==r['accepted'] and endpoint['checker']['receipt']==r['certificate'], 'worker certificate discrepancy')
        clock = BASE/'clocks'/(j['id']+'.json')
        put(path,dict(job=j,status=status,settlement=ref(BASE/'resources'/(j['id']+'.settlement.json')),
            result=ref(result_path) if result else None, clock=ref(clock) if clock.exists() else None))
        print(j['id'],status,flush=True)
        if phase=='admission' and status!='passed': blocked.add(j['configuration'])
        if settlement['overrun']: raise ValueError('resource overrun closes execution')


def report():
    m = load(MANIFEST)
    rows = []
    for j in m['jobs']:
        p = BASE/'trials'/(j['id']+'.json')
        t = load(p) if p.exists() else dict(status='unexecuted',reason='not released')
        row = dict(id=j['id'],phase=j['phase'],configuration=j['configuration'],model=j['model_id'],
                   repetition=j['repetition'],status=t['status'],certified=False,gpu_confirmed=False,elapsed_ns=None,
                   reason=t.get('reason'),trial=ref(p) if p.exists() else None)
        if t.get('result'):
            result = load(checked(t['result']))
            final = result['results'][-1]
            c = verify_certificate(final['certificate'],final['candidate'],final['original'],m['checker'])
            row['certified'] = t['status']=='passed' and c['accepted']
            row['gpu_confirmed'] = final['gpu_confirmed']
        if t.get('clock'): row['elapsed_ns'] = load(checked(t['clock']))['elapsed_ns']
        rows.append(row)
    cpu,gpu=accounting()
    put(BASE/'report.json',dict(schema_version=1,kind='lp-baseline-report',manifest=ref(MANIFEST),
        cpu_charged_ns=cpu,gpu_charged_ns=gpu,rows=rows,planned_admission=20,planned_screening=240,
        admission_passes=sum(r['status']=='passed' for r in rows if r['phase']=='admission'),
        screening_certified=sum(r['certified'] for r in rows if r['phase']=='screening'),
        scientific_complete=all(r['status']!='unexecuted' for r in rows),
        paired_comparisons=paired_comparisons(rows,m),
        limitations=['Generated development corpus only; Gurobi unavailable; no held-out or real-world claim.',
                    'No speedup is reported unless all three corresponding paired certified measurements exist.']))
    print('Report:',BASE/'report.json',flush=True)


def paired_comparisons(rows, manifest):
    """No dropped failed pairs: require all three certified matched cells."""
    configs={c['id']:c for c in manifest['configurations']}
    models=sorted({r['model'] for r in rows if r['phase']=='screening'})
    index={(r['model'],r['configuration'],r['repetition']):r for r in rows if r['phase']=='screening'}
    comparisons=[]
    for model in models:
        for config in configs:
            if config=='project-tuned-fp64': continue
            logs=[]; missing=[]
            for rep in range(3):
                pair=[index.get((model,c,rep)) for c in ('project-tuned-fp64',config)]
                if all(r and r['certified'] and r['elapsed_ns'] and
                       (not configs[r['configuration']]['gpu'] or r['gpu_confirmed']) for r in pair):
                    logs.append(math.log(pair[0]['elapsed_ns']/pair[1]['elapsed_ns']))
                else: missing.append(rep)
            value=dict(model=model,reference='project-tuned-fp64',configuration=config,
                       complete_pairs=len(logs),missing_repetitions=missing,median_speedup=None,confidence95=None)
            if not missing:
                rng=random.Random(17111)
                bootstrap=sorted(statistics.median([rng.choice(logs) for _ in logs]) for _ in range(10000))
                value.update(median_speedup=math.exp(statistics.median(logs)),
                             confidence95=[math.exp(bootstrap[249]),math.exp(bootstrap[9749])])
            comparisons.append(value)
    return comparisons


def hardware():
    m=load(MANIFEST)
    verify_freeze(m)
    for kind in ('project','cuopt'):
        identity=kind+'-'+('device' if kind=='project' else 'context')+'-probe'
        interpreter=sys.executable if kind=='project' else str(CUOPT)
        result=reserve(identity,'hardware',30,True,
            ['/usr/bin/env','PYTHONPATH='+str(BASE/'python-support'),interpreter,'-B',str(ROOT/'tools/lp_baseline_hardware_v2.py'),kind])
        print(identity,result['status'],flush=True)


def main():
    if len(sys.argv)==4 and sys.argv[1]=='_launch': return launched(sys.argv[2],sys.argv[3])
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['freeze','hardware','admission','screening','report'])
    a=p.parse_args()
    if a.command=='freeze': freeze()
    elif a.command=='hardware': hardware()
    elif a.command=='report': report()
    else: run_phase(a.command)
    return 0


if __name__=='__main__': raise SystemExit(main())
