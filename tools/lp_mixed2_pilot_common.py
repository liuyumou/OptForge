"""Independent MIXED2 diagnostic pilot; historical allocations stay closed."""
from lp_baseline_common import ROOT, DEVICE, NS, load, put, ref, require
BASE=ROOT/'artifacts/gpup-mixed2-pilot-v1'
CPU_CAPS=dict(implementation=12000,native=8000,acceptance=12000,study=10000,reporting=4000,cleanup=2000)
GPU_CAPS=dict(acceptance=1200,study=1200)
BINARY=ROOT/'research/lp-mixed2-pilot/target/release/lp-mixed2-pilot'
IMAGE=BASE/'build-v2/pilot.cubin'
BASELINE='6172ea7'
VARIANTS=('control','profile')
TARGETS=('dense-generic-128','dense-generic-256','dense-generic-512')
