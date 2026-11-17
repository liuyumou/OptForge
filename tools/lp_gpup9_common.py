"""Independent GPUP-9 allocation and identities (SPEC-0044 / ADR-0078)."""
from lp_baseline_common import ROOT, DEVICE, NS, load, put, ref, require, checked

BASE = ROOT / 'artifacts/gpup9-v1'
BINARY = ROOT / 'artifacts/gpup-checker2-v1/build-v5/executor'
IMAGE = ROOT / 'artifacts/gpup-mixed2-fp4-v1/build-v8/mixed.cubin'
SERIAL = ROOT / 'artifacts/gpup-mixed2-fp4-v1/build-v10/executor'
CPU_CAPS = dict(implementation=12000, native=16000, acceptance=16000,
                screening=6000, validation=16000, holdout=32000,
                reporting=12000, cleanup=2000)
GPU_CAPS = dict(acceptance=2000, screening=1500, validation=4000, holdout=8000)
SUPERVISOR_MODULE = 'lp_confirmation2_supervisor'
MAX_GAP_NS = 1_000_000_000
FAMILIES = ['small-33', 'sparse-128', 'generic-1024', 'generic-2048',
            'coupled-1024', 'coupled-2048']
TIER = 'certified-1e-9'
SETTINGS = dict(audit_max=200, max_updates=10000, wall_ms=30000, fixed_audit=True)


def configs():
    return {f'{lane}-w{window}-s{int(scale)}':
            dict(lane=lane, window_max=window, equilibrate=scale)
            for lane in ['native', 'fp4x2'] for window in [16, 32]
            for scale in [False, True]}
