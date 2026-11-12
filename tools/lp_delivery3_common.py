"""Independent DELIVERY3 allocation; every historical allocation remains closed."""
from lp_baseline_common import ROOT, DEVICE, NS, load, put, ref, require
BASE = ROOT / 'artifacts/gpup-delivery3-v1'
CPU_CAPS = dict(implementation=10000, native=12000, acceptance=6000, diagnosis=8000,
                confirmation=24000, reporting=3000, cleanup=1000)
GPU_CAPS = dict(acceptance=600, diagnosis=1200, confirmation=6000)
BINARY = ROOT / 'research/lp-delivery3/target/release/lp-delivery3'
VARIANTS = ('control', 'batch', 'overlap', 'combined')
LANES = ('nativefast', 'gridfp4x2')
TIERS = ('certified-1e-7', 'certified-1e-9')
TARGETS = ('dense-generic-128', 'dense-generic-256', 'dense-generic-512')
