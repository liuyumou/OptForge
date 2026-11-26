"""Exact primal proposals with one dyadic conversion, and untrusted dual factors."""
import math
import time
import numpy as np
from scipy import sparse
from .factor_projection import inverse_proposal


def dyadic_integers(arrays):
    exponent=0;converted=[]
    for source in arrays:
        a=np.asarray(source,dtype=np.float64)
        if not np.isfinite(a).all():return None
        converted.append(a)
        for first in range(0,a.size,65536):
            block=np.ascontiguousarray(a.ravel()[first:first+65536]);bits=block.view(np.uint64);e=((bits>>52)&2047).astype(np.int64)
            mantissa=(bits&np.uint64((1<<52)-1))|np.where(e!=0,np.uint64(1<<52),np.uint64(0))
            nonzero=mantissa!=0
            if not np.any(nonzero):continue
            low=mantissa&(~mantissa+np.uint64(1));trailing=np.frexp(low.astype(np.float64))[1].astype(np.int64)-1
            needed=np.where(e==0,1074,1075-e)-trailing;exponent=max(exponent,int(np.max(needed[nonzero])))
            if exponent>24:return None
    integers=[]
    for a in converted:
        scaled=np.ldexp(a,exponent)
        if np.max(np.abs(scaled),initial=0)>2**40 or not np.equal(scaled,np.rint(scaled)).all():return None
        integers.append(np.ascontiguousarray(scaled,dtype=np.int64))
    return exponent,integers


def primal(a,b,c,x,encoded=None):
    start=time.perf_counter_ns();encoded=encoded if encoded is not None else dyadic_integers([a.data,b,c]);encoded_ns=time.perf_counter_ns()-start
    if encoded is None:return None,dict(reason='unsupported_dyadic_model',encoding_ns=encoded_ns)
    _,(av,bv,_)=encoded;ai=sparse.csr_matrix((av,a.indices,a.indptr),shape=a.shape)
    maximum_a=max(abs(int(av.min(initial=0))),abs(int(av.max(initial=0))));maximum_b=max(abs(int(bv.min(initial=0))),abs(int(bv.max(initial=0))));degree=int(np.diff(a.indptr).max(initial=0))
    for px in range(25):
        q=np.rint(np.ldexp(x,px))
        if not np.isfinite(q).all() or np.max(np.abs(q),initial=0)>2**40:break
        xi=q.astype(np.int64);bound=maximum_a*int(np.max(np.abs(xi),initial=0))*degree+maximum_b*(1<<px)
        if bound>=1<<62:continue
        lhs=ai@xi;rhs=bv*(1<<px);active=lhs==rhs
        if np.all(lhs<=rhs) and np.count_nonzero(active)>=a.shape[1]:
            return (np.ldexp(xi.astype(float),-px),active,px),dict(encoding_ns=encoded_ns,primal_search_ns=time.perf_counter_ns()-start-encoded_ns)
    return None,dict(reason='no_exact_active_primal',encoding_ns=encoded_ns,primal_search_ns=time.perf_counter_ns()-start-encoded_ns)


def build(a,b,c,x,y,encoded=None):
    start=time.perf_counter_ns();point,detail=primal(a,b,c,x,encoded)
    if point is None:return None,detail
    xp,active,px=point;n=a.shape[1]
    if not np.isfinite(y).all():return None,dict(reason='nonfinite_dual',**detail)
    maximum=float(np.max(np.maximum(y,0.),initial=0))
    if maximum>2**52:return None,dict(reason='dual_base_range',**detail)
    py=max(0,min(48,52-math.frexp(maximum)[1] if maximum else 48));rounded=np.rint(np.ldexp(np.maximum(y,0.),py))
    if np.max(rounded,initial=0)>2**52:return None,dict(reason='dual_base_range',**detail)
    y0=np.ldexp(rounded,-py);y0[~active]=0.;available=np.flatnonzero(active&(y0>0))
    if len(available)<n:return None,dict(reason='insufficient_positive_active_rows',**detail)
    attempts=[]
    for selected in (available[np.argsort(-y0[available],kind='stable')[:n]],available[np.linspace(0,len(available)-1,n,dtype=int)]):
        begin=time.perf_counter_ns()
        try:
            inverse=inverse_proposal(a[selected].toarray().T,gpu=False)
            if not np.isfinite(inverse).all():raise ArithmeticError('nonfinite inverse')
        except (ArithmeticError,ValueError,np.linalg.LinAlgError) as error:attempts.append(str(error));continue
        inverse_ns=time.perf_counter_ns()-begin;begin=time.perf_counter_ns();refined=y0.copy();steps=0
        for _ in range(2):
            residual=c-np.asarray(a.T@refined).ravel();q=np.rint(np.ldexp(refined[selected]+inverse@residual,py))
            if not np.isfinite(q).all() or np.min(q,initial=0)<0 or np.max(q,initial=0)>2**52:break
            refined[selected]=np.ldexp(q,-py);steps+=1
        return dict(x=xp,y0=refined,basis=selected.astype(np.uint32),inverse=inverse),dict(method='one_pass_adaptive_implicit_dual',primal_exponent=px,dual_base_exponent=py,
            inverse_ns=inverse_ns,dual_refinement_ns=time.perf_counter_ns()-begin,numerical_dual_refinement_steps=steps,
            builder_inverse_bound_omitted=True,gpu_inverse=False,active_rows=int(active.sum()),inverse_entries=n*n,attempts=attempts,elapsed_ns=time.perf_counter_ns()-start,**detail)
    return None,dict(reason='inverse_proposal_failed',attempts=attempts,**detail)
