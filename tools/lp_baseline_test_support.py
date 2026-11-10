"""Build CPU-only test checkers without borrowing a historical study artifact."""
from functools import lru_cache
import os
from pathlib import Path
import subprocess

from lp_baseline_common import ROOT, load, put, ref


@lru_cache(maxsize=2)
def checker(buffered=False):
    name = 'lp-external-baseline' + ('-buffered' if buffered else '')
    manifest = ROOT/'research'/name/'Cargo.toml'
    target = ROOT/'target/lp-baseline-tests'
    (ROOT/'artifacts').mkdir(exist_ok=True)
    env = {**os.environ, 'CUDA_VISIBLE_DEVICES': '', 'CARGO_BUILD_JOBS': '4'}
    command = ['cargo', 'build', '--locked', '--manifest-path', str(manifest),
               '--target-dir', str(target)]
    subprocess.run(command, cwd=ROOT, env=env, check=True, timeout=180)
    if buffered:
        # This standalone research crate is outside cargo test --workspace.
        subprocess.run([*command[:1], 'test', *command[2:]],
                       cwd=ROOT, env=env, check=True, timeout=120)
    return target/'debug'/name


def mock_vendor_manifest(directory: Path, checker_path: Path):
    """Minimal hash-bound worker context, explicitly unrelated to a real study."""
    proposal = ROOT/'benchmarks/configs/lp-external-baseline-proposal-v2.json'
    context = put(directory/'mock-context.json', dict(
        kind='cpu-unit-test-context', vendor_api='mocked', gpu_calls=0,
        historical_measurement=False))
    return dict(checker=ref(checker_path), configurations=load(proposal)['configurations'],
                self_reference=context, environment=context, proposal=ref(proposal),
                adapter=ref(ROOT/'tools/lp_baseline_adapters_v5.py'))
