"""Read-only history/dependency checks and source-bound SPEC-0029 evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

import lp_fp4_recovery_contract as contract

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'artifacts/gpup-fp4-recovery-spec-v1'
NAVIGATION = {'AGENTS.md', 'state/active-task.md', 'state/backlog.yaml',
              'docs/plans/gpu-lp-precision-roadmap.md'}
SOURCES = ['tools/lp_fp4_recovery_contract.py', 'tools/lp_fp4_recovery_delivery.py',
           'tests/integration/test_lp_fp4_recovery_contract.py',
           'benchmarks/configs/lp-fp4-recovery-v1.json',
           'schemas/lp-fp4-recovery-v1.schema.json',
           'schemas/lp-fp4-recovery-checkpoint-v1.schema.json',
           'docs/specifications/SPEC-0029-fp4-recovery-policy.md',
           'docs/decisions/ADR-0061-fp4-operational-recovery.md']


def ref(path):
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    return dict(path=str(path.relative_to(ROOT)), bytes=path.stat().st_size,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def verify():
    history = json.loads((BASE / 'history-v1.json').read_text())
    contract.require(re.fullmatch('[0-9a-f]{40}', history['head']), 'invalid historical commit')
    verified = []
    for old in history['files']:
        path = old['path']
        if path not in NAVIGATION:
            contract.require(ref(path) == old, f'history changed: {path}')
            verified.append(path)
    # Appending the current handoff must retain every byte of old dated entries.
    for path in ('AGENTS.md', 'state/active-task.md'):
        old = subprocess.check_output(['git', 'show', f"{history['head']}:{path}"], cwd=ROOT)
        contract.require((ROOT/path).read_bytes().endswith(old.split(b'\n\n', 1)[1]),
                         f'old handoff changed: {path}')
    # Backlog is intentionally simple YAML; parse just its task/dependency fields
    # without introducing a new runtime dependency for this CPU-only contract.
    tasks, current = {}, None
    text = (ROOT/'state/backlog.yaml').read_text()
    for line in text.splitlines():
        if line.startswith('  - id: '):
            current = line.split(': ', 1)[1]
            contract.require(current not in tasks, 'duplicate backlog identity')
            tasks[current] = {}
        elif current and line.startswith('    status: '):
            tasks[current]['status'] = line.split(': ', 1)[1]
        elif current and line.startswith('    depends_on: '):
            deps = line.split('[', 1)[1].split(']', 1)[0]
            tasks[current]['dependencies'] = [v.strip() for v in deps.split(',') if v.strip()]
    visited, stack = set(), set()

    def visit(task):
        contract.require(task not in stack, 'dependency cycle')
        contract.require(task in tasks, 'missing dependency')
        if task in visited:
            return
        stack.add(task)
        for dep in tasks[task].get('dependencies', []):
            visit(dep)
        stack.remove(task)
        visited.add(task)

    # Validate the research subgraph; unrelated capability tasks use milestone refs.
    visit('GPUP-FP4-INTEGRATE')
    contract.require(tasks['GPUP-FP4-RECOVERY-SPEC']['status'] == 'complete', 'recovery incomplete')
    contract.require(tasks['GPUP-FP4-INTEGRATE']['status'] == 'ready', 'integration not ready')
    contract.require('next_ready_task: GPUP-FP4-INTEGRATE\n' in text, 'next task differs')
    for dep in tasks['GPUP-FP4-INTEGRATE']['dependencies']:
        contract.require(tasks[dep]['status'] == 'complete', 'integration prerequisite incomplete')
    cells = contract.proposed_cells()
    p = contract.policy()['integration_proposal']
    contract.require(len(cells) == len({v['id'] for v in cells}) == p['trajectory_cells'], 'grid differs')
    for resource in ('cpu', 'gpu'):
        total = sum(j['jobs'] * j[f'{resource}_seconds_each'] for j in p['resource_jobs'])
        contract.require(total == p[f'{resource}_seconds'], 'proposal resource total differs')
    return dict(kind='lp-fp4-recovery-evidence', schema_version=1,
                authority='CPU operational-policy contract; no global enclosure or device qualification',
                history=ref(BASE/'history-v1.json'), historical_head=history['head'],
                historical_files_unchanged=len(verified), allowed_navigation_changes=sorted(NAVIGATION),
                old_dated_handoffs_exact=True, integration_dependencies_complete=True,
                sources=[ref(p) for p in SOURCES],
                proposal_cells=cells, proposed_resources=dict(cpu_seconds=p['cpu_seconds'],
                gpu_seconds=p['gpu_seconds'], executable=False), actual_gpu_seconds=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = verify()
    # Retained delivery identities must never be silently overwritten.
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps(dict(status='passed', historical_files=result['historical_files_unchanged'],
                         proposed_cells=len(result['proposal_cells']), actual_gpu_seconds=0)))


if __name__ == '__main__':
    main()
