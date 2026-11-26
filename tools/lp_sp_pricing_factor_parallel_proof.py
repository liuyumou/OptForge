"""Full arbitrary-integer certificate scan with three CPU workers.

The parent overlaps the independent FP64 inverse enclosure with exact CSR
blocks. Workers return integer partial dual products, never floating sums.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
import ctypes
import json
import math
import multiprocessing as mp
from pathlib import Path
import time
import numpy as np
from scipy import sparse
from lp_sp_pricing_budget import BASE,binding,put
from lp_billion_arrays import read as read_array
from lp_sp_pricing_factor_proof import vector,inverse_bound,correction_bound,up,verify_arrays as serial

_CONTEXT=None


def install(context):
    global _CONTEXT
    _CONTEXT=context


def block(interval):
    offsets,indices,values,bi,xi,yi,dx,denominator,cache,n,basis,deadline=_CONTEXT
    dual=[0]*n;feasible=support=selected=True;visited=0
    def integer(raw):
        value=float(raw)
        if value in cache:return cache[value]
        numerator,den=value.as_integer_ratio();return numerator*(denominator//den)
    for i in range(*interval):
        begin,end=int(offsets[i]),int(offsets[i+1])
        if not 0<=begin<=end<=len(values):raise ValueError('offsets')
        total=0;previous=-1
        for k in range(begin,end):
            j=int(indices[k])
            if not previous<j<n:raise ValueError('noncanonical_CSR')
            previous=j;coefficient=integer(values[k]);total+=coefficient*xi[j];dual[j]+=coefficient*yi[i]
        slack=bi[i]*dx-total;feasible=feasible and slack>=0;support=support and (yi[i]==0 or slack==0)
        selected=selected and (i not in basis or slack==0);visited+=end-begin
        if i%64==0 and time.monotonic()>deadline:raise TimeoutError('parallel proof deadline')
    return dual,feasible,support,selected,visited


def verify_arrays(offsets,indices,values,b,c,x,y0,basis,inverse,seconds=120,force_parallel=False):
    if len(values)<100000 and not force_parallel:return serial(offsets,indices,values,b,c,x,y0,basis,inverse,seconds)
    start=time.perf_counter_ns();deadline=time.monotonic()+seconds;m,n=len(b),len(c);basis=np.asarray(basis)
    if ctypes.CDLL(None).fegetround()!=0:return dict(accepted=False,reason='non_nearest_CPU_rounding')
    if (len(x)!=n or len(y0)!=m or len(offsets)!=m+1 or int(offsets[0])!=0 or int(offsets[-1])!=len(values)
            or len(indices)!=len(values) or basis.shape!=(n,) or basis.dtype.kind not in 'iu'
            or np.asarray(offsets).dtype.kind not in 'iu' or np.asarray(indices).dtype.kind not in 'iu'
            or np.any(np.asarray(offsets)[1:]<np.asarray(offsets)[:-1])
            or len(np.unique(basis))!=n or n==0 or int(basis.min())<0 or int(basis.max())>=m):
        return dict(accepted=False,reason='dimensions_or_basis')
    xi,dx=vector(list(map(float,x)));yi,dy=vector(list(map(float,y0)))
    if any(v<0 for v in yi):return dict(accepted=False,reason='negative_dual_base')
    denominator=1;cache={}
    for array in (values,b,c):
        for first in range(0,len(array),65536):
            for raw in np.unique(array[first:first+65536]):
                value=float(raw)
                if not math.isfinite(value):return dict(accepted=False,reason='nonfinite_original_model')
                _,den=value.as_integer_ratio();denominator=max(denominator,den)
            if time.monotonic()>deadline:raise TimeoutError('parallel proof deadline')
    if max(denominator.bit_length(),dx.bit_length(),dy.bit_length())>53:return dict(accepted=False,reason='implicit_proof_dyadic_resource_limit')
    def integer(raw):
        value=float(raw)
        if value in cache:return cache[value]
        numerator,den=value.as_integer_ratio();answer=numerator*(denominator//den)
        if len(cache)<8192:cache[value]=answer
        return answer
    for first in range(0,len(values),65536):
        for value in np.unique(values[first:first+65536]):integer(value)
    bi=list(map(integer,b));ci=list(map(integer,c));workers=min(3,m)
    edges=[0]+[int(np.searchsorted(offsets,len(values)*i//workers,side='left')) for i in range(1,workers)]+[m]
    context=(offsets,indices,values,bi,xi,yi,dx,denominator,cache,n,set(map(int,basis)),deadline)
    overlap=time.perf_counter_ns()
    with ProcessPoolExecutor(max_workers=workers,mp_context=mp.get_context('fork'),initializer=install,initargs=(context,)) as executor:
        futures=[executor.submit(block,(edges[i],edges[i+1])) for i in range(workers)]
        a=sparse.csr_matrix((values,indices,offsets),shape=(m,n))
        enclosure=inverse_bound(a[basis.astype(np.int64)].toarray().T,inverse)
        parts=[future.result() for future in futures]
    overlap_ns=time.perf_counter_ns()-overlap
    if time.monotonic()>deadline:raise TimeoutError('parallel proof deadline')
    feasible=all(p[1] for p in parts);support=all(p[2] for p in parts);selected=all(p[3] for p in parts);visited=sum(p[4] for p in parts)
    if visited!=len(values):return dict(accepted=False,reason='incomplete_CSR_coverage',visited_nonzeros=visited)
    if not feasible or not support or not selected:return dict(accepted=False,reason='primal_or_complementarity',primal_feasible=feasible,supported_on_exactly_active_rows=support,visited_nonzeros=visited)
    dual=[sum(entries) for entries in zip(*(p[0] for p in parts))]
    residual=max((abs(q*dy-v) for q,v in zip(ci,dual)),default=0);exponent=denominator.bit_length()+dy.bit_length()-2
    residual_upper=0. if not residual else up(max(math.ldexp(up(float(residual)),-exponent),np.finfo(float).tiny))
    delta=correction_bound(enclosure['inverse_norm_upper'],residual_upper) if enclosure['accepted'] else math.inf
    minimum=float(np.min(np.asarray(y0)[basis.astype(np.int64)],initial=math.inf))
    return dict(accepted=bool(enclosure['accepted'] and minimum>=delta),kind='rigorous_implicit_exact_dual',
        primal_feasible=feasible,supported_on_exactly_active_rows=support,dual_stationarity='exact by the defined nonsingular solve',
        zero_gap='exact by complementarity',inverse_proof=enclosure,residual_numerator=str(residual),residual_denominator_exponent=exponent,
        residual_upper=residual_upper,correction_infinity_upper=delta if math.isfinite(delta) else None,minimum_selected_dual_base=minimum,
        visited_nonzeros=visited,rows=m,columns=n,elapsed_ns=time.perf_counter_ns()-start,independent_cpu_workers=workers,
        overlapped_exact_scan_and_inverse_bound_ns=overlap_ns,arithmetic='Python unbounded integer partial products and exact parent sum',
        proof_definition='y=y0+E_basis*delta; B.T*delta=c-A.T*y0; all other y entries unchanged')


def check(model,certificate,seconds=120):
    start=time.perf_counter_ns();raw=json.loads(Path(model).read_text());cert=json.loads(Path(certificate).read_text())
    arrays={k:read_array(BASE,v) for k,v in raw['arrays'].items()};m,n=raw['rows'],raw['columns'];oi=arrays['objective_indices']
    if (raw.get('schema_version')!=1 or raw['nonzeros']!=len(arrays['values']) or len(arrays['row_upper'])!=m
            or len(arrays['column_lower'])!=n or len(arrays['column_upper'])!=n or len(arrays['row_lower'])!=m
            or len(oi)!=len(arrays['objective_values']) or (len(oi) and (int(oi[-1])>=n or np.any(oi[1:]<=oi[:-1])))):
        raise ValueError('original model dimensions or objective ordering')
    if raw['sense']!='maximize' or raw['offset']!=0 or not (np.isneginf(arrays['column_lower']).all() and np.isposinf(arrays['column_upper']).all() and np.isneginf(arrays['row_lower']).all()):raise ValueError('canonical original model')
    c=np.zeros(n);c[oi]=arrays['objective_values'];data=cert['implicit_certificate']
    result=verify_arrays(arrays['offsets'],arrays['indices'],arrays['values'],arrays['row_upper'],c,
        read_array(BASE,data['primal']),read_array(BASE,data['dual_base']),read_array(BASE,data['basis']),read_array(BASE,data['inverse']).reshape(n,n),seconds)
    result.update(complete_ns=time.perf_counter_ns()-start,model=binding(model),certificate=binding(certificate));return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('model',type=Path);p.add_argument('certificate',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    put(a.output,check(a.model,a.certificate))
