"""Independent SPEC-0030 FP4 integration resources."""
from lp_baseline_common import ROOT, DEVICE, NS, load, put, ref, checked, require
BASE = ROOT / 'artifacts/gpup-fp4-integrate-v1'
CPU_CAPS = dict(implementation=24000, native=16000, acceptance=24000,
                study=24000, reporting=6400, cleanup=1600)
GPU_CAPS = dict(acceptance=6000, study=8400)
