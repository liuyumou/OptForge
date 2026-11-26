"""Independent exact acceptance of x=x0+E_J B^-1(b-Ax0), B=A[:,J].

All rows are equalities in the defined primal. Full original CSR integer scans
prove A.T*y=c and y>=0. A separately recomputed inverse enclosure proves that
B is nonsingular. No dyadic representation of the corrected primal is assumed.
"""
import argparse
import ctypes
import json
import math
from pathlib import Path
import sys
import time
import numpy as np
from scipy import sparse
from lp_sp_pricing_budget import ROOT,BASE,binding,put
from lp_billion_arrays import read as read_array
from lp_sp_pricing_scale_verify import vector
sys.path.insert(0,str(ROOT/'research/lp-sp-pricing/python'))
from sp_pricing.implicit_certificate import inverse_bound

def verify_arrays(offsets,indices,values,b,c,x0,y,columns,inverse,seconds=120):
    start=time.perf_counter_ns();deadline=time.monotonic()+seconds;m,n=len(b),len(c)
    columns=np.asarray(columns);offsets=np.asarray(offsets);indices=np.asarray(indices)
    if ctypes.CDLL(None).fegetround()!=0:return dict(accepted=False,reason='non_nearest_CPU_rounding')
    if (not 0<m<=n or m>4096 or len(x0)!=n or len(y)!=m or len(offsets)!=m+1 or offsets.dtype.kind not in 'iu'
        or indices.dtype.kind not in 'iu' or columns.dtype.kind not in 'iu' or columns.shape!=(m,)
        or len(np.unique(columns))!=m or int(columns.min())<0 or int(columns.max())>=n
        or offsets[0]!=0 or offsets[-1]!=len(values) or len(indices)!=len(values) or np.any(offsets[1:]<offsets[:-1])):
        return dict(accepted=False,reason='dimensions_or_basis')
    if not all(np.isfinite(v).all() for v in (values,b,c,x0,y,inverse)):return dict(accepted=False,reason='nonfinite')
    xi,dx=vector(list(map(float,x0)));yi,dy=vector(list(map(float,y)))
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
    dual=[0]*n;residual=[];visited=0
    for i in range(m):
        total=0;previous=-1
        for k in range(int(offsets[i]),int(offsets[i+1])):
            j=int(indices[k])
            if not previous<j<n:return dict(accepted=False,reason='noncanonical_CSR')
            previous=j;coefficient=integer(values[k]);dual[j]+=coefficient*yi[i];total+=coefficient*xi[j];visited+=1
        residual.append(integer(b[i])*dx-total)
        if i%32==0 and time.monotonic()>deadline:raise TimeoutError('implicit primal proof deadline')
    stationarity=all(integer(q)*dy==v for q,v in zip(c,dual))
    if not stationarity:return dict(accepted=False,reason='exact_dual_equations',visited_nonzeros=visited)
    a=sparse.csr_matrix((values,indices,offsets),shape=(m,n));enclosure=inverse_bound(a[:,columns.astype(np.int64)].toarray(),inverse)
    if time.monotonic()>deadline:raise TimeoutError('implicit primal proof deadline')
    return dict(accepted=bool(enclosure['accepted'] and visited==len(values)),kind='rigorous_implicit_exact_primal',
        primal_feasible='exact by nonsingular full-row correction' if enclosure['accepted'] else False,
        dual_nonnegative=True,dual_equations=True,zero_gap='exact by stationarity and all rows active',
        inverse_proof=enclosure,visited_nonzeros=visited,rows=m,columns=n,
        primal_residual_max_numerator=str(max(map(abs,residual),default=0)),primal_residual_denominator=str(denominator*dx),
        primal_definition='x=x0+E_J*delta; B*delta=b-A*x0; B=A[:,J]',
        arithmetic='Python unbounded integer original-model products; independent CPU inverse enclosure',elapsed_ns=time.perf_counter_ns()-start)

def check(model,certificate):
    start=time.perf_counter_ns();raw=json.loads(Path(model).read_text());cert=json.loads(Path(certificate).read_text());arrays={k:read_array(BASE,v) for k,v in raw['arrays'].items()}
    m,n=raw['rows'],raw['columns'];oi=arrays['objective_indices']
    if (raw.get('schema_version')!=1 or raw['sense']!='maximize' or raw['offset']!=0 or raw['nonzeros']!=len(arrays['values'])
        or len(arrays['row_upper'])!=m or len(arrays['row_lower'])!=m or len(arrays['column_lower'])!=n or len(arrays['column_upper'])!=n
        or len(oi)!=len(arrays['objective_values']) or (len(oi) and (int(oi[-1])>=n or np.any(oi[1:]<=oi[:-1])))
        or not (np.isneginf(arrays['column_lower']).all() and np.isposinf(arrays['column_upper']).all() and np.isneginf(arrays['row_lower']).all())):
        raise ValueError('canonical original model')
    c=np.zeros(n);c[oi]=arrays['objective_values'];data=cert['implicit_primal_certificate']
    result=verify_arrays(arrays['offsets'],arrays['indices'],arrays['values'],arrays['row_upper'],c,
        read_array(BASE,data['primal_base']),read_array(BASE,data['dual']),read_array(BASE,data['columns']),read_array(BASE,data['inverse']).reshape(m,m))
    result.update(complete_ns=time.perf_counter_ns()-start,model=binding(model),certificate=binding(certificate));return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('model',type=Path);p.add_argument('certificate',type=Path);p.add_argument('output',type=Path);a=p.parse_args();put(a.output,check(a.model,a.certificate))
