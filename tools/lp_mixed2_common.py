"""Independent MIXED2 CPU admission; historical allocations stay closed."""
from lp_baseline_common import ROOT, DEVICE, NS, load, put, ref, require
BASE = ROOT / 'artifacts/gpup-mixed2-v1'
CPU_CAPS = dict(implementation=4096, native=8000, diagnosis=2048, reporting=1200, cleanup=656)
GPU_CAPS = {}
BASELINE = '34af0d368e4f628b83d8d7cf98937c532a0c3c29'
BINARY = ROOT / 'research/lp-mixed2/target/debug/lp-mixed2'
