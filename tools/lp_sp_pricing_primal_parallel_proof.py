"""Overlap three exact dual scans with the independent CPU basis proof.

Nonsingularity proves feasibility of the defined full-row primal for every
finite b and x0. Computing A*x0 is unnecessary for acceptance. No original
matrix entries are skipped in the exact stationarity scan.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
import ctypes
import multiprocessing as mp
from pathlib import Path
import time
from unittest.mock import patch
import numpy as np
from scipy import sparse
import lp_sp_pricing_primal_proof as original
from lp_sp_pricing_budget import put
from lp_sp_pricing_scale_verify import vector
from sp_pricing.implicit_certificate import inverse_bound

CONTEXT=None

def install(value):
    global CONTEXT
    CONTEXT=value

def scan(interval):
    offsets,indices,values,yi,denominator,cache,n,deadline=CONTEXT;dual=[0]*n;visited=0
    for i in range(*interval):
        previous=-1
        for k in range(int(offsets[i]),int(offsets[i+1])):
            j=int(indices[k])
            if not previous<j<n:return None,visited
            previous=j;raw=float(values[k]);coefficient=cache.get(raw)
            if coefficient is None:
                numerator,den=raw.as_integer_ratio();coefficient=numerator*(denominator//den)
            dual[j]+=coefficient*yi[i];visited+=1
        if i%64==0 and time.monotonic()>deadline:raise TimeoutError('parallel primal proof deadline')
    return dual,visited

def verify_arrays(offsets,indices,values,b,c,x0,y,columns,inverse,seconds=120,force_parallel=False):
    if len(values)<100000 and not force_parallel:return original.verify_arrays(offsets,indices,values,b,c,x0,y,columns,inverse,seconds)
    start=time.perf_counter_ns();deadline=time.monotonic()+seconds;m,n=len(b),len(c)
    columns=np.asarray(columns);offsets=np.asarray(offsets);indices=np.asarray(indices)
    if ctypes.CDLL(None).fegetround()!=0:return dict(accepted=False,reason='non_nearest_CPU_rounding')
    if (not 0<m<=n or m>4096 or len(x0)!=n or len(y)!=m or len(offsets)!=m+1 or offsets.dtype.kind not in 'iu'
        or indices.dtype.kind not in 'iu' or columns.dtype.kind not in 'iu' or columns.shape!=(m,)
        or len(np.unique(columns))!=m or int(columns.min())<0 or int(columns.max())>=n
        or offsets[0]!=0 or offsets[-1]!=len(values) or len(indices)!=len(values) or np.any(offsets[1:]<offsets[:-1])):
        return dict(accepted=False,reason='dimensions_or_basis')
    if not all(np.isfinite(v).all() for v in (values,b,c,x0,y,inverse)):return dict(accepted=False,reason='nonfinite')
    _,dx=vector(list(map(float,x0)));yi,dy=vector(list(map(float,y)))
    if any(v<0 for v in yi):return dict(accepted=False,reason='negative_dual')
    denominator=1;cache={}
    for array in (values,b,c):
        for first in range(0,len(array),65536):
            for raw in np.unique(array[first:first+65536]):denominator=max(denominator,float(raw).as_integer_ratio()[1])
    if max(denominator.bit_length(),dx.bit_length(),dy.bit_length())>53:return dict(accepted=False,reason='dyadic_resource_limit')
    def integer(raw):
        raw=float(raw)
        if raw in cache:return cache[raw]
        numerator,den=raw.as_integer_ratio();value=numerator*(denominator//den)
        if len(cache)<8192:cache[raw]=value
        return value
    for first in range(0,len(values),65536):
        for raw in np.unique(values[first:first+65536]):integer(raw)
    workers=min(3,m);edges=[0]+[int(np.searchsorted(offsets,len(values)*i//workers,side='left')) for i in range(1,workers)]+[m]
    context=(offsets,indices,values,yi,denominator,cache,n,deadline);overlap=time.perf_counter_ns()
    with ProcessPoolExecutor(max_workers=workers,mp_context=mp.get_context('fork'),initializer=install,initargs=(context,)) as executor:
        futures=[executor.submit(scan,(edges[i],edges[i+1])) for i in range(workers)]
        a=sparse.csr_matrix((values,indices,offsets),shape=(m,n));enclosure=inverse_bound(a[:,columns.astype(np.int64)].toarray(),inverse)
        parts=[f.result() for f in futures]
    if time.monotonic()>deadline:raise TimeoutError('parallel primal proof deadline')
    if any(p[0] is None for p in parts):return dict(accepted=False,reason='noncanonical_CSR')
    visited=sum(p[1] for p in parts);dual=[sum(v) for v in zip(*(p[0] for p in parts))]
    stationarity=all(integer(q)*dy==v for q,v in zip(c,dual))
    if not stationarity:return dict(accepted=False,reason='exact_dual_equations',visited_nonzeros=visited)
    return dict(accepted=bool(enclosure['accepted'] and visited==len(values)),kind='rigorous_implicit_exact_primal',
        primal_feasible='exact by nonsingular full-row correction' if enclosure['accepted'] else False,
        dual_nonnegative=True,dual_equations=True,zero_gap='exact by stationarity and all rows active',
        inverse_proof=enclosure,visited_nonzeros=visited,rows=m,columns=n,
        primal_definition='x=x0+E_J*delta; B*delta=b-A*x0; B=A[:,J]',
        arithmetic='Python unbounded integer worker products and exact parent sum; independent CPU inverse enclosure',
        independent_cpu_workers=workers,overlapped_scan_and_inverse_ns=time.perf_counter_ns()-overlap,elapsed_ns=time.perf_counter_ns()-start)

def check(model,certificate):
    # Keep the serial function reachable for small cases while substituting
    # only the checking entry point used by the unchanged original loader.
    serial=original.verify_arrays
    def dispatch(*args,**kwargs):
        if len(args[2])<100000:return serial(*args,**kwargs)
        return verify_arrays(*args,**kwargs)
    with patch.object(original,'verify_arrays',dispatch):return original.check(model,certificate)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('model',type=Path);p.add_argument('certificate',type=Path);p.add_argument('output',type=Path);a=p.parse_args();put(a.output,check(a.model,a.certificate))
