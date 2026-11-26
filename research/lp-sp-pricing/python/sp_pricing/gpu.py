"""Batched numerical proposals with exact acceptance and per-target fallback.

Matrix upload and transpose construction are charged to preparation. Every batch
has independent primal/dual state, sharing only its immutable calibrated basis.
Sparse mode builds both CSR directions; original sparse inputs can still acquire
dense bases. No sparse scalability claim follows from supporting CSR products.
"""
import ctypes as C
import hashlib
import math
from pathlib import Path
import time
from fractions import Fraction as Q
from .exact import dot, rational

MODES = {"fp64": 0, "fp32x2": 1, "fp32x4": 2, "fp32x8": 3,
         "fp4x1": 4, "fp4x2": 5, "fp4x4": 6}


def accept_proposal(oracle, target, xi, dual):
    """Exact primal feasibility or box-support dual upper bound, never tolerance.

    For every feasible z, c.z <= H*||c-Bu||_1 + support_[L,U](u).
    This remains valid for arbitrary u and arbitrary inaccurate GPU arithmetic.
    """
    if not 0 <= target < oracle.n or len(xi) != oracle.r or len(dual) != 2*oracle.n:
        raise ValueError("proposal dimensions")
    if any(not math.isfinite(v) for v in [*xi, *dual]):
        return dict(accepted=False, reason="nonfinite_proposal")
    x = [max(-oracle.h, min(oracle.h, rational(v))) for v in xi]
    y = oracle.multiply(x)
    scale = Q(1)
    for value in y:
        if value > 2:
            scale = min(scale, 2/value)
        elif value < -oracle.epsilon:
            scale = min(scale, -oracle.epsilon/value)
    x = [v*scale for v in x]
    y = oracle.witness(x)
    established = {}
    for i in range(oracle.n):
        if y[2*i+1] >= Q(1, 4):
            established[i] = 1
        elif oracle.broadcast_negative and y[2*i] >= Q(1, 4):
            established[i] = -1
    u = list(map(rational, dual))
    residual = oracle.residual(target, u)
    upper = oracle.h*sum(map(abs, residual), Q(0))
    upper += sum((2*v if v >= 0 else -oracle.epsilon*v for v in u), Q(0))
    oracle.work.tick(upper)
    if upper < Q(1, 4):
        if established.get(target) == 1:
            raise ArithmeticError("primal and dual proofs contradict")
        established[target] = -1
    return dict(accepted=target in established, target=target, established=established,
                x=x, dual=u, dual_upper=upper, witness=y, epoch=oracle.epoch,
                kind="exact_checked_gpu_proposal")


class GpuBatch:
    def __init__(self, library, basis, sparse=False):
        self.path = Path(library).resolve()
        self.digest = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.r, self.s = len(basis), len(basis[0])
        if any(len(row) != self.s for row in basis):
            raise ValueError("basis dimensions")
        self.lib = C.CDLL(str(self.path))
        ptr = C.POINTER(C.c_double)
        self.lib.sp_create.argtypes = [C.c_int]*3+[ptr, C.POINTER(C.c_void_p)]
        self.lib.sp_create.restype = C.c_int
        self.lib.sp_propose.argtypes = [C.c_void_p, C.c_int, C.POINTER(C.c_int),
            C.c_double, C.c_double, C.c_int, C.c_int, ptr, ptr, ptr]
        self.lib.sp_propose.restype = C.c_int
        self.lib.sp_propose_slots.argtypes=self.lib.sp_propose.argtypes
        self.lib.sp_propose_slots.restype=C.c_int
        self.lib.sp_destroy.argtypes = [C.c_void_p]
        self.lib.sp_destroy.restype = C.c_int
        self.handle = C.c_void_p()
        begin = time.perf_counter_ns()
        array = (C.c_double*(self.r*self.s))(*(float(v) for row in basis for v in row))
        self.check(self.lib.sp_create(self.r, self.s, int(sparse), array, C.byref(self.handle)))
        self.preparation_ns = time.perf_counter_ns()-begin
        self.sparse = sparse

    @staticmethod
    def check(code):
        if code:
            raise RuntimeError("CUDA proposal engine error " + str(code))

    def propose(self, targets, h, epsilon, steps=1000, mode="fp64", slot_targets=False):
        width = len(targets)
        if width not in (1, 8, 32, 64) or not 1 <= steps <= 10000 or mode not in MODES:
            raise ValueError("proposal configuration")
        if not self.handle:
            raise ValueError("closed GPU batch")
        ids = (C.c_int*width)(*targets)
        x, u = (C.c_double*(width*self.r))(), (C.c_double*(width*self.s))()
        ms = C.c_double()
        begin = time.perf_counter_ns()
        function=self.lib.sp_propose_slots if slot_targets else self.lib.sp_propose
        self.check(function(self.handle, width, ids, float(h), float(epsilon),
            steps, MODES[mode], x, u, C.byref(ms)))
        elapsed = time.perf_counter_ns()-begin
        return dict(x=[list(x[i*self.r:(i+1)*self.r]) for i in range(width)],
                    dual=[list(u[i*self.s:(i+1)*self.s]) for i in range(width)],
                    elapsed_ns=elapsed, device_iteration_ms=ms.value,
                    width=width, mode=mode, steps=steps)

    def close(self):
        if self.handle:
            handle, self.handle = self.handle, C.c_void_p()
            self.check(self.lib.sp_destroy(handle))

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def propose_labels(oracle, library, width, mode="fp32x2", sparse=False, steps=1000, backend="legacy"):
    if backend == "lean":
        from .gpu_lean import propose_labels as lean_labels
        return lean_labels(oracle, library, width, sparse=sparse, steps=steps)
    if backend != "legacy":
        raise ValueError("unknown GPU proposal backend")
    labels, proofs, traces = {}, [], []
    if width not in (1, 8, 32, 64):
        raise ValueError("unadmitted batch width")
    with GpuBatch(library, oracle.b, sparse) as engine:
        # Active compaction occurs between precision passes; proof objects carry
        # calibration epochs so proposals cannot leak across compression restarts.
        for precision in dict.fromkeys((mode, "fp64")):
            active = [2*i+h for i in range(oracle.n) if i not in labels for h in (1,0)]
            for start in range(0, len(active), width):
                targets = [s for s in active[start:start+width] if s//2 not in labels]
                if not targets:
                    continue
                padded = targets+[targets[-1]]*(width-len(targets))
                result = engine.propose(padded, oracle.h, oracle.epsilon, steps, precision,slot_targets=True)
                proof_begin = time.perf_counter_ns()
                for offset, slot in enumerate(targets):
                    target=slot//2
                    proof = accept_proposal(oracle, target, result["x"][offset], result["dual"][offset])
                    proof['requested_slot']=slot
                    for index, sign in proof.get("established", {}).items():
                        if index in labels and labels[index] != sign:
                            raise ArithmeticError("inconsistent GPU certificates")
                        labels[index] = sign
                    proofs.append(proof)
                traces.append({k: v for k, v in result.items() if k not in ("x", "dual")}
                              | dict(active_slots=targets, exact_check_ns=time.perf_counter_ns()-proof_begin))
        metadata = dict(preparation_ns=engine.preparation_ns, native_sha256=engine.digest,
                        sparse=sparse, batches=traces, gpu_labels=len(labels),
                        product_backend="cuda_cores_explicit_components", tensor_cores=False)
    return labels, proofs, metadata
