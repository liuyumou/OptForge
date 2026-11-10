"""Separate SPEC-0023 continuation allocation; historical budgets stay closed."""
from lp_baseline_common_v4 import (ROOT, DEVICE, NS, PROPOSAL, checked, digest,
                                  load, put, ref, require, verify_certificate)

BASE = ROOT / 'artifacts/gpup-external-baseline-v5'
PRIOR = ROOT / 'artifacts/gpup-external-baseline-v4'
PRIOR_ACCOUNTING = ROOT / 'docs/benchmarks/data/external-baseline-final-accounting-v1.json'
PRIOR_ACCOUNTING_SHA256 = '7b1c054af4d0cec97fc3f1137706e76ae7b73c2aaa79cf8a0c3a93d16b274d2c'
CPU_CAPS = dict(implementation=1600, screening=28080, reporting=1600, cleanup=720)
GPU_CAPS = dict(screening=2322)
PREPARATION_CPU_SECONDS = 128
TOTAL_BASELINE_GPU_SECONDS = 3600
