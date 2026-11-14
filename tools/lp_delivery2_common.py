"""Independent DELIVERY2 allocation; historical ledgers remain closed."""
from lp_baseline_common import ROOT, DEVICE, NS, load, put, ref, require
BASE = ROOT / 'artifacts/gpup-delivery2-v1'
CPU_CAPS = dict(implementation=8000, acceptance=12000, study=8000, reporting=3000, cleanup=1000)
GPU_CAPS = dict(acceptance=300, study=1500)
