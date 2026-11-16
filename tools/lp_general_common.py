"""Independent general low-bit program (SPEC-0045); old allocations stay closed."""
from lp_baseline_common import ROOT, DEVICE, NS, load, put, ref, checked, require
BASE = ROOT / 'artifacts/gpup-general-v1'
CPU_CAPS = dict(implementation=60000, native=24000, admission=48000,
                development=48000, confirmation=40000, reporting=16000, cleanup=4000)
GPU_CAPS = dict(admission=8000, development=10000, confirmation=10000, reporting=2000)
SUPERVISOR_MODULE = 'lp_confirmation2_supervisor'
MAX_GAP_NS = 1_000_000_000
