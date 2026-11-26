"""Validate exact-certificate buffers before any narrowing or native call.

This opt-in boundary leaves the previously measured geometry module immutable.
The solver already emits bounded signed integers; direct callers also receive
range and cache-fidelity validation here.
"""
import numpy as np
from . import geometry_fast

_native_frontend=geometry_fast.exact_certificate

def bounded_integer(value,shape):
    value=np.asarray(value)
    if value.shape!=shape or value.dtype.kind not in 'iu':return None
    # Check in the original dtype BEFORE conversion; uint64 must not wrap.
    if value.size and (int(value.min())<-(1<<40) or int(value.max())>(1<<40)):return None
    return np.ascontiguousarray(value,dtype=np.int64)

def guarded_certificate(a,b,c,x,px,y,py,integer_model=None):
    if type(px) is not int or type(py) is not int or not 0<=px<=24 or not 0<=py<=24:return False
    a=a.tocsr(copy=False);b=np.asarray(b);c=np.asarray(c);m,n=a.shape
    if (a.dtype!=np.float64 or b.dtype!=np.float64 or c.dtype!=np.float64 or b.shape!=(m,) or c.shape!=(n,)
            or not a.has_canonical_format or min(m,n)<1 or max(m,n)>1<<20):return False
    if any(not np.isfinite(v).all() for v in (a.data,b,c)):return False
    xv=bounded_integer(x,(n,));yv=bounded_integer(y,(m,))
    if xv is None or yv is None:return False
    if integer_model is None:encoded=geometry_fast.dyadic_integers([a.data,b,c])
    else:
        if not isinstance(integer_model,(tuple,list)) or len(integer_model)!=2:return False
        exponent,arrays=integer_model
        if type(exponent) is not int or not 0<=exponent<=24 or not isinstance(arrays,(tuple,list)) or len(arrays)!=3:return False
        validated=[]
        for original,integer in zip((a.data,b,c),arrays):
            value=bounded_integer(integer,original.shape)
            if value is None or not np.equal(np.ldexp(original,exponent),value).all():return False
            validated.append(value)
        encoded=exponent,validated
    if encoded is None:return False
    return _native_frontend(a,b,c,xv,px,yv,py,encoded)
