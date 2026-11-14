"""Separate CPU-only DELIVERY/MIXED2 PR integration allocation."""
from lp_baseline_common import ROOT, DEVICE, NS, load, put, ref, require
BASE = ROOT/'artifacts/gpup-delivery-pr-v1'
CPU_CAPS = dict(implementation=2000, native=16000, research=8000,
                portability=8000, publishing=10000, reporting=3000, cleanup=1000)
GPU_CAPS = {}
