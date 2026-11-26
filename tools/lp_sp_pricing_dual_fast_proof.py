"""Independent exact sparse products with proved int64 limb bounds and CPU enclosure."""
# Four BLAS threads replace the old parent plus three integer scan workers.
# Only the new implicit-dual CLI uses this setting; imports never alter it.
if __name__=='__main__':
    import os
    os.environ['OPENBLAS_NUM_THREADS']='4'
    os.environ['MKL_NUM_THREADS']='4'
import argparse
import ctypes
import math
from pathlib import Path
import time
from unittest.mock import patch
import numpy as np
from scipy import sparse
from lp_sp_pricing_budget import put
import lp_sp_pricing_factor_proof as original
SERIAL=original.verify_arrays


def canonical(offsets,indices,n):
    visited=0
    for first in range(0,len(indices),65536):
        last=min(len(indices),first+65536);lo=max(0,first-1);block=indices[lo:last]
        if np.any(block<0) or np.any(block>=n):return False,visited
        bad=lo+np.flatnonzero(block[1:]<=block[:-1])+1
        if len(bad):
            positions=np.searchsorted(offsets,bad)
            if np.any(offsets[positions]!=bad):return False,visited
        visited+=last-first
    return True,visited


def products(a,vector,transpose=False):
    """Every multiply and partial sum fits signed int64; combine limbs in Python."""
    v=np.asarray(vector,dtype=np.int64);maximum=max(abs(int(a.data.min(initial=0))),abs(int(a.data.max(initial=0))))
    count=a.shape[0] if transpose else int(np.diff(a.indptr).max(initial=0));operator=a.T if transpose else a
    peak=max(map(abs,map(int,v)),default=0)
    if maximum*count*peak<(1<<62):return list(map(int,operator@v)),1
    limit=((1<<62)-1)//max(1,maximum*count);bits=min(26,limit.bit_length()-1)
    if bits<1:raise OverflowError('no provably safe limb width')
    magnitude=np.abs(v);sign=np.where(v<0,-1,1);answer=[0]*operator.shape[0];limbs=0
    for shift in range(0,peak.bit_length(),bits):
        digit=((magnitude>>shift)&((1<<bits)-1))*sign
        if maximum*count*int(np.max(np.abs(digit),initial=0))>=1<<62:raise OverflowError('limb bound')
        part=operator@digit
        answer=[old+(int(value)<<shift) for old,value in zip(answer,part)];limbs+=1
    return answer,limbs


def verify_arrays(offsets,indices,values,b,c,x,y0,basis,inverse,seconds=120):
    start=time.perf_counter_ns();deadline=time.monotonic()+seconds;m,n=len(b),len(c)
    offsets=np.asarray(offsets);indices=np.asarray(indices);basis=np.asarray(basis);values=np.asarray(values)
    if ctypes.CDLL(None).fegetround()!=0:return dict(accepted=False,reason='non_nearest_CPU_rounding')
    if (not n or m<n or len(x)!=n or len(y0)!=m or len(offsets)!=m+1 or offsets.dtype.kind not in 'iu' or indices.dtype.kind not in 'iu'
        or offsets[0]!=0 or offsets[-1]!=len(values) or len(indices)!=len(values) or np.any(offsets[1:]<offsets[:-1])
        or np.any(offsets>len(values)) or basis.dtype.kind not in 'iu' or basis.shape!=(n,) or len(np.unique(basis))!=n or basis.min()<0 or basis.max()>=m
        or np.shape(inverse)!=(n,n)):
        return dict(accepted=False,reason='dimensions_or_basis')
    if not all(np.isfinite(v).all() for v in (values,b,c,x,y0,inverse)):return dict(accepted=False,reason='nonfinite')
    ok,visited=canonical(offsets,indices,n)
    if not ok:return dict(accepted=False,reason='noncanonical_CSR',visited_nonzeros=visited)
    xi,dx=original.vector(list(map(float,x)));yi,dy=original.vector(list(map(float,y0)))
    if any(v<0 for v in yi):return dict(accepted=False,reason='negative_dual_base')
    denominator=1
    # Independent exponent discovery uses exact scalar ratios, not the builder's bit decoder.
    for array in (values,b,c):
        for first in range(0,len(array),65536):
            for raw in np.unique(array[first:first+65536]):denominator=max(denominator,float(raw).as_integer_ratio()[1])
            if time.monotonic()>deadline:raise TimeoutError('independent dual proof deadline')
    if max(denominator.bit_length(),dx.bit_length(),dy.bit_length())>53:return dict(accepted=False,reason='implicit_proof_dyadic_resource_limit')
    def integer(raw):
        numerator,den=float(raw).as_integer_ratio();return numerator*(denominator//den)
    bi=list(map(integer,b));ci=list(map(integer,c));scaled=np.ldexp(values,denominator.bit_length()-1)
    if np.max(np.abs(scaled),initial=0)>=2**62 or any(abs(v)>=1<<62 for v in xi+yi):
        result=SERIAL(offsets,indices,values,b,c,x,y0,basis,inverse,seconds);result['integer_path']='arbitrary_integer_serial_fallback';return result
    av=scaled.astype(np.int64)
    if not np.equal(scaled,av).all():raise ArithmeticError('integer encoding mismatch')
    encoded_ns=time.perf_counter_ns()-start;a=sparse.csr_matrix((av,indices,offsets),shape=(m,n));begin=time.perf_counter_ns()
    try:lhs,pl=products(a,xi);dual,dl=products(a,yi,True)
    except OverflowError:
        result=SERIAL(offsets,indices,values,b,c,x,y0,basis,inverse,seconds);result['integer_path']='arbitrary_integer_serial_fallback';return result
    slacks=[q*dx-v for q,v in zip(bi,lhs)];feasible=all(v>=0 for v in slacks);support=all(v==0 or yi[i]==0 for i,v in enumerate(slacks));selected=all(slacks[int(i)]==0 for i in basis)
    products_ns=time.perf_counter_ns()-begin
    if not feasible or not support or not selected:return dict(accepted=False,reason='primal_or_complementarity',primal_feasible=feasible,supported_on_exactly_active_rows=support,visited_nonzeros=visited)
    residual=max((abs(q*dy-v) for q,v in zip(ci,dual)),default=0);exponent=denominator.bit_length()+dy.bit_length()-2
    residual_upper=0. if not residual else original.up(max(math.ldexp(original.up(float(residual)),-exponent),np.finfo(float).tiny))
    begin=time.perf_counter_ns();floating=sparse.csr_matrix((values,indices,offsets),shape=(m,n));enclosure=original.inverse_bound(floating[basis.astype(np.int64)].toarray().T,inverse);inverse_ns=time.perf_counter_ns()-begin
    delta=original.correction_bound(enclosure['inverse_norm_upper'],residual_upper) if enclosure['accepted'] else math.inf;minimum=float(np.min(np.asarray(y0)[basis.astype(np.int64)],initial=math.inf))
    if time.monotonic()>deadline:raise TimeoutError('independent dual proof deadline')
    return dict(accepted=bool(enclosure['accepted'] and minimum>=delta),kind='rigorous_implicit_exact_dual',primal_feasible=feasible,supported_on_exactly_active_rows=support,
        dual_stationarity='exact by the defined nonsingular solve',zero_gap='exact by complementarity',inverse_proof=enclosure,residual_numerator=str(residual),residual_denominator_exponent=exponent,
        residual_upper=residual_upper,correction_infinity_upper=delta if math.isfinite(delta) else None,minimum_selected_dual_base=minimum,visited_nonzeros=visited,rows=m,columns=n,
        encoding_and_validation_ns=encoded_ns,exact_products_ns=products_ns,inverse_enclosure_ns=inverse_ns,primal_limbs=pl,dual_limbs=dl,elapsed_ns=time.perf_counter_ns()-start,
        arithmetic='Bounded signed-int64 sparse products; exact Python integer limb combination; independent CPU inverse enclosure',integer_path='proved_int64_limbs',
        proof_definition='y=y0+E_basis*delta; B.T*delta=c-A.T*y0; all other y entries unchanged')


def check(model,certificate,seconds=120):
    with patch.object(original,'verify_arrays',verify_arrays):return original.check(model,certificate,seconds)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('model',type=Path);p.add_argument('certificate',type=Path);p.add_argument('output',type=Path);a=p.parse_args();put(a.output,check(a.model,a.certificate))
