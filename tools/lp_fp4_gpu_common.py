"""Independent GPUP-FP4-GPU-PILOT authority; no historical budget reuse."""
from lp_baseline_common import ROOT, DEVICE, NS, load, put, ref, checked, require
BASE = ROOT / 'artifacts/gpup-fp4-gpu-pilot-v1'
CPU_CAPS = dict(implementation=16000, native=24000, acceptance=16000,
                study=8000, reporting=6400, cleanup=1600)
GPU_CAPS = dict(acceptance=2400, study=7200)
