"""Independent MIXED2 FP4 implementation and larger-scale evaluation."""
from lp_baseline_common import ROOT, DEVICE, NS, load, put, ref, require
BASE=ROOT/'artifacts/gpup-mixed2-fp4-v1'
CPU_CAPS=dict(implementation=40000,native=12000,acceptance=30000,development=30000,confirmation=32000,reporting=12000,cleanup=4000)
GPU_CAPS=dict(acceptance=6000,development=6000,confirmation=12000)
BINARY=BASE/'build-v10/executor'
BASELINE='4bebce3'
