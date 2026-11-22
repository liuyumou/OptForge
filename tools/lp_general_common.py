"""Independent general low-bit program (SPEC-0045); old allocations stay closed."""
from lp_baseline_common import ROOT, DEVICE, NS, load, put, ref, checked, require
BASE = ROOT / 'artifacts/gpup-general-v1'
CPU_CAPS = dict(implementation=20000, native=35000, admission=48000,
                development=92000, confirmation=0, reporting=41000, cleanup=4000)
GPU_CAPS = dict(admission=8150, development=21850, confirmation=0, reporting=0)
SUPERVISOR_MODULE = 'lp_confirmation2_supervisor'
MAX_GAP_NS = 1_000_000_000
