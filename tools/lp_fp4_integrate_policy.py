"""Fast readback of the exact policy admitted by the CPU schema tests.

Avoid constructing the repository-wide JSON schema registry in each cold solve.
The expected canonical digest is part of this source-bound integration version.
"""
import json
from pathlib import Path
from lp_fp4_recovery_contract import digest
POLICY_SHA256 = '916583891a322081bd23a216e67e11660efff37de9c6526da4c943208f72225e'

def admitted_policy(path=None):
    path = Path(path) if path is not None else Path(__file__).resolve().parents[1]/'benchmarks/configs/lp-fp4-recovery-v1.json'
    value = json.loads(path.read_text())
    if digest(value) != POLICY_SHA256:
        raise ValueError('policy differs from CPU-admitted immutable bytes')
    return value
