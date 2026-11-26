"""Factorized projections propose LP endpoints; independent proofs decide validity."""
import ctypes as C
from pathlib import Path
import time
import numpy as np
from scipy import linalg, sparse

LIBRARY = Path(__file__).resolve().parents[2]/'target/release/libsp_factor_projection.so'
D = C.POINTER(C.c_double)


class CpuProjection:
    def __init__(self, a, b, c, rho):
        self.a = a.toarray(order='F') if sparse.issparse(a) else np.asarray(a, order='F')
        self.b = b; self.c = c; self.rho = rho
        self.factor = linalg.cho_factor(self.a.T@self.a, lower=True, check_finite=True)
        self.x = np.zeros(len(c)); self.u = np.zeros(len(b)); self.s = np.maximum(b, 0.)
    def advance(self, steps):
        for _ in range(steps):
            self.x = linalg.cho_solve(self.factor, self.a.T@(self.b-self.s-self.u)+self.c/self.rho, check_finite=False)
            relaxed = 1.6*(self.a@self.x)+.6*(self.s-self.b)
            self.s = np.maximum(0., self.b-relaxed-self.u)
            self.u += relaxed+self.s-self.b
        return self.x.copy(), self.rho*self.u.copy()
    def close(self): pass


def library():
    lib = C.CDLL(str(LIBRARY))
    lib.sp_factor_create.argtypes = [C.c_int, C.c_int, D, D, D, C.c_double, C.POINTER(C.c_void_p)]
    lib.sp_factor_create.restype = C.c_int
    lib.sp_factor_advance.argtypes = [C.c_void_p, C.c_int, D, D]
    lib.sp_factor_advance.restype = C.c_int
    lib.sp_factor_destroy.argtypes = [C.c_void_p]
    lib.sp_factor_inverse.argtypes = [C.c_int, D, D]
    lib.sp_factor_inverse.restype = C.c_int
    return lib


class GpuProjection:
    def __init__(self, a, b, c, rho):
        self.lib = library(); self.handle = C.c_void_p(); self.m, self.n = a.shape
        dense = a.toarray(order='F') if sparse.issparse(a) else np.asarray(a, dtype=np.float64, order='F')
        b = np.ascontiguousarray(b, dtype=np.float64); c = np.ascontiguousarray(c, dtype=np.float64)
        if b.shape != (self.m,) or c.shape != (self.n,) or not np.isfinite(b).all() or not np.isfinite(c).all():
            raise ValueError('factor projection vector dimensions/range')
        code = self.lib.sp_factor_create(self.m, self.n, dense.ctypes.data_as(D), b.ctypes.data_as(D),
                                         c.ctypes.data_as(D), rho, C.byref(self.handle))
        if code:
            raise ArithmeticError('GPU factor setup '+str(code))
    def advance(self, steps):
        x = np.empty(self.n); y = np.empty(self.m)
        code = self.lib.sp_factor_advance(self.handle, steps, x.ctypes.data_as(D), y.ctypes.data_as(D))
        if code:
            raise ArithmeticError('GPU factor advancement '+str(code))
        return x, y
    def close(self):
        if self.handle:
            self.lib.sp_factor_destroy(self.handle); self.handle = C.c_void_p()


def inverse_proposal(basis_transpose, gpu=False):
    matrix = np.asfortranarray(basis_transpose, dtype=np.float64)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1] or not 1 <= len(matrix) <= 4096 or not np.isfinite(matrix).all():
        raise ValueError('inverse proposal dimensions/range')
    if gpu:
        out = np.empty(matrix.shape, dtype=np.float64, order='F')
        code = library().sp_factor_inverse(len(matrix), matrix.ctypes.data_as(D), out.ctypes.data_as(D))
        if code:
            raise ArithmeticError('GPU inverse proposal '+str(code))
        return np.asarray(out, order='C')
    factor = linalg.lu_factor(matrix, check_finite=True)
    return linalg.lu_solve(factor, np.eye(len(matrix)), check_finite=False)


def projection(a, b, c, seconds=30, gpu=True, max_steps=6000):
    start = time.perf_counter_ns(); deadline = time.monotonic()+seconds; m, n = a.shape
    if m < n or n > 4096 or m*n > 1 << 27 or not np.isfinite(a.data).all():
        raise ValueError('factorized projection shape/range')
    # Scaling only chooses a numerical proposal trajectory. It cannot accept a proof.
    rho = max(1e-8, min(1., float(np.linalg.norm(c))/max(float(np.linalg.norm(a.data))*np.sqrt(m), 1e-30)))
    state = (GpuProjection if gpu else CpuProjection)(a, b, c, rho)
    setup = time.perf_counter_ns()-start; x = y = None; records = []
    try:
        for k in range(0, max_steps, 100):
            if time.monotonic() >= deadline:
                break
            x, y = state.advance(min(100, max_steps-k))
            if not np.isfinite(x).all() or not np.isfinite(y).all():
                raise ArithmeticError('nonfinite factorized proposal')
            primal = float(np.max(a@x-b, initial=0))/(1+float(np.max(np.abs(b), initial=0)))
            dual = float(np.max(np.abs(a.T@y-c), initial=0))/(1+float(np.max(np.abs(c), initial=0)))
            records.append(dict(steps=k+100, primal=primal, dual=dual))
            if max(primal, dual) < 1e-10:
                break
    finally:
        state.close()
    if x is None:
        raise TimeoutError('factor setup consumed allowance')
    return x, y, dict(method='factorized_admm_projection', gpu=gpu, rho=rho, setup_ns=setup,
        complete_ns=time.perf_counter_ns()-start, steps=records[-1]['steps'], checkpoints=records,
        stored_matrix_entries=m*n+n*n, explicit_slack_nullspace_entries=0)
