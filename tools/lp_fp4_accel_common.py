"""Independent SPEC-0031 corrected FP4 acceleration resources."""
from lp_baseline_common import ROOT, DEVICE, NS, load, put, ref, checked, require
BASE = ROOT / 'artifacts/gpup-fp4-accel-v1'
CPU_CAPS = dict(implementation=48000, native=16000, acceptance=40000, study=40000, reporting=12000, cleanup=4000)
GPU_CAPS = dict(acceptance=8000, study=16000)
