"""Independent DELIVERY4 allocation; all historical allocations remain closed."""
from lp_baseline_common import ROOT, DEVICE, NS, load, put, ref, require
BASE = ROOT / 'artifacts/gpup-delivery4-v1'
CPU_CAPS = dict(implementation=12000, native=12000, acceptance=8000, diagnosis=8000,
                confirmation=16000, reporting=6000, cleanup=2000)
GPU_CAPS = dict(acceptance=600, diagnosis=600, confirmation=3600)
BINARY = ROOT / 'research/lp-delivery4/target/release/lp-delivery4'
VARIANTS = ('control', 'candidate')
LANES = ('nativefast', 'gridfp4x2')
TIERS = ('certified-1e-7', 'certified-1e-9')
TARGETS = ('dense-generic-128', 'dense-generic-256', 'dense-generic-512')
