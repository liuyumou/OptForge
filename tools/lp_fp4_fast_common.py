"""Independent FP4 optimization allocation under the user's performance request."""
from lp_baseline_common import ROOT, DEVICE, NS, load, put, ref, checked, require
BASE = ROOT / 'artifacts/gpup-fp4-fast-v1'
CPU_CAPS = dict(implementation=24000, native=16000, acceptance=32000,
                study=48000, reporting=6400, cleanup=1600)
GPU_CAPS = dict(acceptance=7200, study=10800)
