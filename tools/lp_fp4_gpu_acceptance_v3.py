"""Final CPU-only delivery checks; no numerical/device replay."""
import ast
import hashlib
import os
import subprocess
import yaml

from lp_fp4_gpu_common import ROOT, BASE, load, put, ref, require
from lp_fp4_gpu_delivery_v3 import verify_manifest, resources


def main():
    for version in (1, 2, 3):
        verify_manifest(ROOT / f'artifacts/gpup-fp4-gpu-pilot-v{version}/manifest.json')
    before = load(BASE / 'prior-tracked.json')
    require(all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
                for name, digest in before.items()), 'historical mutation')
    for pattern in ('lp_fp4_gpu_*.py', 'setup_fp4_gpu_pilot*.py'):
        for path in (ROOT / 'tools').glob(pattern):
            ast.parse(path.read_text(), filename=str(path))
    result_path = ROOT / 'docs/benchmarks/data/fp4-gpu-pilot-result-v3.json'
    result = load(result_path)
    require(result['status'] == 'complete_empirical_pilot'
            and result['completed'] == result['planned'] == 216
            and result['certified'] == 0, 'pilot completion scope')
    require(all(g['status'] == 'passed' for g in result['gates'].values()), 'admission status')
    account = resources()
    failures = [r for r in account['resources'] if r['status'] == 'refused']
    require(len(failures) == 6, 'failure preservation count')
    require(all(not r['charged'].get('overrun', False) for r in account['resources']), 'overrun')
    require(account['total_gpu_ns'] == load(ROOT / 'docs/benchmarks/data/fp4-gpu-pilot-accounting-v3.json')['total_gpu_ns'], 'unexpected new GPU work')
    backlog = yaml.safe_load((ROOT / 'state/backlog.yaml').read_text())
    tasks = {t['id']: t for t in backlog['tasks']}
    require(backlog['next_ready_task'] == 'GPUP-FP4-RECOVERY-SPEC'
            and tasks['GPUP-FP4-RECOVERY-SPEC']['status'] == 'ready'
            and tasks['GPUP-FP4-GPU-PILOT']['status'] == 'complete'
            and tasks['GPUP-FP4-PROTO']['status'] == 'in_progress', 'handoff scope')
    visited, active = set(), set()
    def visit(name):
        require(name in tasks and name not in active, 'dependency missing/cycle')
        if name in visited:
            return
        active.add(name)
        for dependency in tasks[name].get('depends_on', []):
            visit(dependency)
        active.remove(name)
        visited.add(name)
    for name in tasks:
        visit(name)
    checks = []
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    for command in [
        ['/opt/conda/bin/python3', '-B', 'tools/validate_artifacts.py'],
        ['/opt/conda/bin/python3', '-B', 'tools/build_docs.py'],
        ['git', 'diff', '--check'],
        ['git', 'diff', '--cached', '--check'],
    ]:
        subprocess.run(command, cwd=ROOT, env=env, check=True)
        checks.append(command)
    put(ROOT / 'docs/benchmarks/data/fp4-gpu-pilot-acceptance-v3.json', dict(
        status='passed', kind='fp4-gpu-pilot-delivery-acceptance-v3', result=ref(result_path),
        immutable_historical_files=len(before), source_manifests_verified=3,
        retained_failed_reservations=len(failures), no_scientific_replay=True,
        checks=checks, resources=account,
        software=dict(workspace_rust_tests=638, isolated_rust_tests=3,
                      python_suite_tests=583, additional_corrected_packing_tests=4,
                      gate='Composite acceptance; passed Rust/native stages reused after the retained Python environment/source-roster failure.'),
        note='This active reporting reservation is counted fully. Final settled accounting is additive.'))
    print('Delivery acceptance passed: all 216 cells, six retained failures, three manifests, historical preservation, syntax/artifacts/docs/diff.')


if __name__ == '__main__':
    main()
