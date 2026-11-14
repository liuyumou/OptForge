"""Independent reliability and changing-model reuse study, SPEC-0039."""
from lp_baseline_common import ROOT, DEVICE, NS, load, put, ref, require

BASE = ROOT / 'artifacts/gpup-mixed2-reuse-v1'
OLD = ROOT / 'artifacts/gpup-mixed2-fp4-v1'
BINARY = BASE / 'build-v2/executor'
IMAGE = OLD / 'build-v8/mixed.cubin'
BASELINE = '8040747'
CPU_CAPS = dict(implementation=12000, diagnosis=4000, native=16000,
                acceptance=12000, confirmation=27200, reporting=6800, cleanup=2000)
GPU_CAPS = dict(diagnosis=200, acceptance=1600, confirmation=6600)
