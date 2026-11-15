"""Independent completion continuation; previous allocations remain closed."""
from lp_baseline_common import ROOT, DEVICE, NS, load, put, ref, require
from lp_mixed2_reuse_common import BASE as PRIOR, BINARY, IMAGE
BASE=ROOT/'artifacts/gpup-checker2-v1'
PREVIOUS=ROOT/'artifacts/gpup-mixed2-confirm-v1'
BASELINE='ff5066c'
CPU_CAPS=dict(implementation=16000,diagnosis=12000,native=16000,acceptance=12000,
              confirmation=32000,reporting=6000,cleanup=2000)
GPU_CAPS=dict(acceptance=2000,confirmation=10000)
SUPERVISOR_MODULE='lp_confirmation2_supervisor'
MAX_GAP_NS=1_000_000_000
ADVISORY_GAP_NS=100_000_000
