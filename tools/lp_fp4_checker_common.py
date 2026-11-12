"""Independent exact-checker optimization allocation; old allocations stay closed."""
from lp_baseline_common import ROOT, DEVICE, NS, load, put, ref, require
BASE = ROOT / 'artifacts/gpup-fp4-checker-v1'
CPU_CAPS = dict(implementation=8000, acceptance=6000, study=6000, reporting=3000, cleanup=1000)
GPU_CAPS = dict(acceptance=300, study=900)
