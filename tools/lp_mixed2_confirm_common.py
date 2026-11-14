"""Independent completion allocation and immutable numerical dependencies."""
from lp_baseline_common import ROOT, DEVICE, NS, load, put, ref, require
from lp_mixed2_reuse_common import BASE as PRIOR, BINARY, IMAGE
BASE=ROOT/'artifacts/gpup-mixed2-confirm-v1'
BASELINE='a6f6372'
CPU_CAPS=dict(implementation=10000,diagnosis=8000,native=20000,acceptance=6000,
              confirmation=28800,reporting=14000,cleanup=3200)
GPU_CAPS=dict(diagnosis=400,acceptance=1200,confirmation=7400)
