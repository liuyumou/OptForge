"""Separate CPU-only PR integration allocation; scientific budgets stay closed."""
from lp_baseline_common import ROOT, DEVICE, NS, load, put, ref, require
BASE = ROOT/'artifacts/gpup-fp4-pr-v1'
CPU_CAPS = dict(implementation=2400, acceptance=8000, reporting=1200, cleanup=400)
GPU_CAPS = {}
