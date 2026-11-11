"""Independent GPUP-RESIDENT2 identity and resource authority (SPEC-0024)."""
from lp_baseline_common import ROOT, DEVICE, NS, load, put, ref, checked, require
BASE = ROOT / 'artifacts/gpup-resident2-v1'
CPU_CAPS = dict(implementation=8000, native=8000, acceptance=4000,
                study=8000, reporting=3200, cleanup=800)
GPU_CAPS = dict(acceptance=600, study=1200)
