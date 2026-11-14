"""Independent completion continuation; previous allocations remain closed."""
from lp_baseline_common import ROOT, DEVICE, NS, load, put, ref, require
from lp_mixed2_reuse_common import BASE as PRIOR, BINARY, IMAGE
BASE=ROOT/'artifacts/gpup-mixed2-confirm2-v1'
PREVIOUS=ROOT/'artifacts/gpup-mixed2-confirm-v1'
BASELINE='4657c8a'
CPU_CAPS=dict(implementation=8000,diagnosis=14000,native=12000,acceptance=8000,
              confirmation=40000,reporting=12000,cleanup=2000)
GPU_CAPS=dict(acceptance=1800,confirmation=10200)
SUPERVISOR_MODULE='lp_confirmation2_supervisor'
MAX_GAP_NS=1_000_000_000
ADVISORY_GAP_NS=100_000_000
