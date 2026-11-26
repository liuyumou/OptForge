"""Use dense BLAS for dense CPU row-Gram proposals, preserving sparse/GPU paths."""
import time
import numpy as np
from scipy import linalg
from .primal_recovery import row_proposal as previous

def row_proposal(a,b,c,gpu=False):
    m,n=a.shape
    if gpu or not (0<m<n and m<=4096 and m*n<=1<<27 and a.nnz/(m*n)>.2):return previous(a,b,c,gpu)
    start=time.perf_counter_ns();dense=a.toarray(order='F');factor=linalg.cho_factor(dense@dense.T,lower=True)
    solved=linalg.cho_solve(factor,np.column_stack((b,dense@c)));x=dense.T@solved[:,0];y=solved[:,1]
    if not np.isfinite(x).all() or not np.isfinite(y).all():raise ArithmeticError('nonfinite dense row proposal')
    return x,y,dict(method='cpu_dense_row_gram_cholesky_two_rhs',gpu=False,complete_ns=time.perf_counter_ns()-start,
        stored_factor_entries=m*n+m*m,explicit_nullspace_entries=0,pricing_queries=0,market_scans=0)
