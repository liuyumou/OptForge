"""Numerical full-row-space recovery; no numerical routine accepts a certificate."""
import ctypes as C
from pathlib import Path
import time
import numpy as np
from scipy import linalg,sparse
from scipy.sparse.linalg import splu
from .factor_projection import inverse_proposal

LIBRARY=Path(__file__).resolve().parents[2]/'target/release/libsp_wide_recovery.so'
D=C.POINTER(C.c_double)

def row_proposal(a,b,c,gpu=False):
    start=time.perf_counter_ns();m,n=a.shape
    if not 0<m<=n or m>4096 or m*n>1<<27:raise ValueError('row recovery shape')
    if gpu and m<n:
        lib=C.CDLL(str(LIBRARY));lib.sp_wide_proposal.argtypes=[C.c_int,C.c_int,D,D,D,D,D];lib.sp_wide_proposal.restype=C.c_int
        dense=np.asfortranarray(a.toarray());b=np.ascontiguousarray(b);c=np.ascontiguousarray(c);x=np.empty(n);y=np.empty(m)
        code=lib.sp_wide_proposal(m,n,dense.ctypes.data_as(D),b.ctypes.data_as(D),c.ctypes.data_as(D),x.ctypes.data_as(D),y.ctypes.data_as(D))
        if code:raise ArithmeticError('GPU row proposal '+str(code))
        method='gpu_row_gram_cholesky_two_rhs';entries=m*n+m*m
    elif m==n:
        if a.nnz/(m*n)>.2:
            factor=linalg.lu_factor(a.toarray());x=linalg.lu_solve(factor,b);y=linalg.lu_solve(factor,c,trans=1)
            method='cpu_square_lu_two_sides';entries=m*n
        else:
            factor=splu(a.tocsc());x=factor.solve(b);y=factor.solve(c,trans='T');method='cpu_sparse_square_lu_two_sides';entries=factor.L.nnz+factor.U.nnz
    else:
        gram=(a@a.T).tocsc();factor=splu(gram);rhs=np.column_stack((b,a@c));solved=factor.solve(rhs)
        x=np.asarray(a.T@solved[:,0]);y=solved[:,1];method='cpu_sparse_row_gram_two_rhs';entries=gram.nnz+factor.L.nnz+factor.U.nnz
    if not np.isfinite(x).all() or not np.isfinite(y).all():raise ArithmeticError('nonfinite row proposal')
    return x,y,dict(method=method,gpu=gpu and m<n,complete_ns=time.perf_counter_ns()-start,
        stored_factor_entries=int(entries),explicit_nullspace_entries=0,pricing_queries=0,market_scans=0)

def build(a,b,c,x,y,gpu_inverse=False):
    start=time.perf_counter_ns();m,n=a.shape
    if not 0<m<=n or m>4096 or len(x)!=n or len(y)!=m or not np.isfinite(x).all() or not np.isfinite(y).all():
        return None,dict(reason='primal_recovery_shape_or_range')
    # A floating zero is only a proposal filter; the separate checker performs
    # every stationarity product with arbitrary-precision integers.
    y0=None
    for exponent in range(33):
        rounded=np.rint(np.ldexp(y,exponent))
        if np.max(np.abs(rounded),initial=0)>2**52:break
        point=np.ldexp(rounded,-exponent)
        if np.min(point,initial=0)<0:continue
        if np.max(np.abs(a.T@point-c),initial=0)<=1e-12*(1+np.max(np.abs(c),initial=0)):
            y0=point;break
    if y0 is None:return None,dict(reason='no_short_dyadic_dual')
    # Structural matching avoids an expensive rectangular pivoted QR. Its
    # nonsingularity is not assumed: the independent inverse enclosure proves it.
    columns=sparse.csgraph.maximum_bipartite_matching(a,perm_type='column')
    if len(columns)!=m or np.any(columns<0):return None,dict(reason='no_full_row_structural_matching')
    basis=a[:,columns].toarray()
    try:r=inverse_proposal(basis,gpu=gpu_inverse)
    except (ArithmeticError,ValueError,np.linalg.LinAlgError) as e:return None,dict(reason='basis_factorization_failed',detail=str(e))
    maximum=float(np.max(np.abs(x),initial=0));px=min(40,max(0,48-int(np.ceil(np.log2(max(1.,maximum))))))
    x0=np.ldexp(np.rint(np.ldexp(x,px)),-px)
    return dict(x0=x0,y=y0,columns=columns.astype(np.uint32),inverse=r),dict(method='implicit_full_row_primal',
        primal_exponent=px,dual_exponent=exponent,basis_order=m,inverse_entries=m*m,explicit_nullspace_entries=0,
        gpu_inverse=gpu_inverse,elapsed_ns=time.perf_counter_ns()-start)
