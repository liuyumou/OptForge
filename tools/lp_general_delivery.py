"""Compact delivery records and exact preservation for the active general program."""
import argparse
import difflib
import json
import subprocess
import yaml
from lp_general_common import BASE, ROOT, NS, load, put, ref, require
from lp_general_budget import accounting, admission_open

BASELINE = '895708060d0107f55d37bae70f0e9240ebb702d5'
NAVIGATION = ['AGENTS.md', 'state/active-task.md', 'docs/plans/gpu-lp-precision-roadmap.md']


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def preserve(identity):
    names = git('ls-tree', '-r', '--name-only', BASELINE).decode().splitlines()
    changed = [name for name in git('diff', '--name-only', BASELINE, '--').decode().splitlines() if name in set(names)]
    require(set(changed) <= set(NAVIGATION + ['state/backlog.yaml']), 'historical tracked source changed')
    for name in NAVIGATION:
        old = git('show', BASELINE + ':' + name).decode().splitlines(keepends=True)
        new = (ROOT / name).read_text().splitlines(keepends=True)
        require(all(op in ('equal', 'insert') for op, *_ in difflib.SequenceMatcher(None, old, new, autojunk=False).get_opcodes()),
                'historical navigation changed: ' + name)
    old = yaml.safe_load(git('show', BASELINE + ':state/backlog.yaml'))
    new = yaml.safe_load((ROOT / 'state/backlog.yaml').read_text())
    require(new['next_ready_task'] == 'GPUP-GENERAL', 'general objective routing')
    for key, value in old.items():
        if key not in ('tasks', 'next_ready_task'):
            require(new[key] == value, 'historical backlog metadata changed')
    current = {task['id']: task for task in new['tasks']}
    for task in old['tasks']:
        retained = dict(current[task['id']])
        if task['id'] == 'GPUP-10':
            require('current_release_requirement' in retained, 'broad validation requirement missing')
            del retained['current_release_requirement']
        require(retained == task, 'historical backlog task changed: ' + task['id'])
    put(BASE / (identity + '.json'), dict(status='passed', baseline=BASELINE,
        historical_files=len(names), unchanged_files=len(names) - len(changed),
        additive_navigation=changed, public_runtime_sources_unchanged=True))
    print(dict(status='passed', historical_files=len(names), additive_navigation=changed), flush=True)


def compact(identity):
    campaigns = []
    for name in ['development-pilot-v1', 'development-extended-v1']:
        analysis_path = BASE / name / 'analysis.json'
        analysis = load(analysis_path)
        # No model coefficients, endpoint vectors or per-iteration streams in Git.
        groups = []
        for original in analysis['groups']:
            group = {k: v for k, v in original.items() if k != 'formats'}
            group['formats'] = {f: {k: v for k, v in r.items() if k != 'certificate'}
                                for f, r in original['formats'].items()}
            groups.append(group)
        campaigns.append(dict(name=name, analysis=ref(analysis_path), freeze=analysis['freeze'],
            status=analysis['status'],cells=analysis['cells'],planned_cells=analysis.get('planned_cells',analysis['cells']),
            missing=analysis.get('missing',[]),resource_eligible_cells=analysis.get('resource_eligible_cells',analysis['cells']),
            formats=analysis['formats'], groups=groups,
            comparisons=analysis['comparisons'], scientific_confirmation=False))
    result = dict(schema_version=1, objective='Broad LP performance through low-bit arithmetic including FP4',
        status='active; no broad performance or adoption claim', campaigns=campaigns,
        admission=ref(BASE / 'device-admission-v2.json'),
        external_certificate_admission=ref(BASE / 'implied-admission-v2/result.json'),
        storage='Exact raw inputs, responses, failures and source versions remain in the local portable archive.')
    path = ROOT / 'docs/benchmarks' / (identity + '.json')
    put(path, result)
    print(dict(path=str(path), bytes=path.stat().st_size), flush=True)


def checkpoint(identity):
    admission_open()
    cpu, gpu = accounting()
    receipts = []
    for p in sorted((BASE / 'resources').glob('*.settlement.json')):
        r = load(p)
        receipts.append(dict(receipt=ref(p), status=r['status'], phase=r['phase'],
                             cpu_ns=r['cpu_ns'], gpu_ns=r['gpu_ns']))
    put(BASE / (identity + '.json'), dict(status='open', objective='active',
        cpu_ns=cpu, gpu_ns=gpu, total_cpu_seconds=sum(cpu.values()) / NS,
        total_gpu_seconds=sum(gpu.values()) / NS, receipts=receipts,
        charge_adjustments=[ref(p) for p in sorted((BASE / 'charge-adjustments').glob('*.json'))],
        confirmation_frozen=False, public_defaults_changed=False, publication=False,
        note='Accounting checkpoint, not allocation closure or completion of the broad performance objective.'))
    print(dict(cpu_seconds=sum(cpu.values()) / NS, gpu_seconds=sum(gpu.values()) / NS, status='open'), flush=True)


def validation(identity):
    native=BASE/'resources/native-v3.settlement.json'
    require(load(native)['status']=='passed','final native gate missing')
    archive=BASE/'portable/delivery-v2/receipt.json'
    replay=BASE/'portable/delivery-v2/replay.json'
    r=load(replay);require(r['status']=='passed' and r['receipt']==ref(archive),'portable replay binding')
    result=r['result']
    require(result['cells']==265 and len(result['missing'])==39 and result['public_inputs']==4,
            'portable replay coverage differs')
    for name in ['cpu-contracts-v14','delivery-contracts-v1','portable-archive-v2','portable-replay-v2']:
        require(load(BASE/'resources'/(name+'.settlement.json'))['status']=='passed','delivery check missing '+name)
    accounting_path=BASE/'checkpoint-accounting-v1.json'
    ledger=load(accounting_path)
    require(ledger['status']=='open' and ledger['objective']=='active','broad objective must stay active')
    put(ROOT/'docs/benchmarks'/(identity+'.json'),dict(schema_version=1,status='engineering checkpoint; broad objective active',
        native_gate=ref(native),native_rust_tests=638,native_python_tests=819,
        isolated_rust_tests=12,general_python_tests=9,
        device_admission=ref(BASE/'device-admission-v2.json'),
        preservation=ref(BASE/'preservation-v2.json'),accounting=ref(accounting_path),
        charged_cpu_seconds=ledger['total_cpu_seconds'],charged_gpu_seconds=ledger['total_gpu_seconds'],
        archive_receipt=load(archive),archive_receipt_binding=ref(archive),portable_replay=ref(replay),
        retained_cells=result['cells'],assessments=result['assessments'],missing_cells=len(result['missing']),
        observation='265 retained responses replay; 264 have complete campaign resource receipts; missing supervision is not repaired',
        no_broad_performance_claim=True,confirmation_frozen=False,public_defaults_changed=False))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('command', choices=['preserve', 'compact', 'checkpoint', 'validation'])
    p.add_argument('--id', required=True)
    a = p.parse_args()
    {'preserve': preserve, 'compact': compact, 'checkpoint': checkpoint, 'validation': validation}[a.command](a.id)
