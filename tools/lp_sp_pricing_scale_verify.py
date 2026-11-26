"""Independent full original-LP proof with Python arbitrary-precision integers.

No solver, NumPy dot/reduction, native geometry library or planted witness is
used to decide acceptance. Coefficients are decoded with float.as_integer_ratio;
CSR products and objective comparisons use unbounded Python integer arithmetic.
"""
import argparse
from fractions import Fraction
import json
import math
from pathlib import Path
import time
import numpy as np
from lp_sp_pricing_budget import BASE,put,binding
from lp_billion_arrays import read as read_array


def number(v):
    if isinstance(v,bool):raise ValueError('boolean rational')
    if isinstance(v,dict):
        if set(v)!={'numerator','denominator'}:raise ValueError('rational fields')
        return Fraction(int(v['numerator']),int(v['denominator']))
    if isinstance(v,float) and not math.isfinite(v):raise ValueError('nonfinite rational')
    return Fraction(v)


def vector(values):
    values=[number(v) for v in values];den=1
    for q in values:
        den=math.lcm(den,q.denominator)
        if den.bit_length()>100000:raise ValueError('independent denominator resource limit')
    return [q.numerator*(den//q.denominator) for q in values],den


def verify_arrays(offsets,indices,values,b,c,x,y,seconds=300):
    start=time.perf_counter_ns();deadline=time.monotonic()+seconds
    m,n=len(b),len(c)
    if len(x)!=n or len(y)!=m or len(offsets)!=m+1 or int(offsets[0])!=0 or int(offsets[-1])!=len(values) or len(indices)!=len(values):
        return dict(accepted=False,reason='dimensions',elapsed_ns=time.perf_counter_ns()-start)
    xi,dx=vector(x);yi,dy=vector(y)
    if any(v<0 for v in yi):return dict(accepted=False,reason='dual_sign',elapsed_ns=time.perf_counter_ns()-start)
    d=1
    # Binary64 model values are original inputs. Their denominators are powers
    # of two, so the maximum is their exact common denominator.
    for array in (values,b,c):
        for first in range(0,len(array),65536):
            for raw in np.unique(array[first:first+65536]):
                value=float(raw)
                if not math.isfinite(value):raise ValueError('nonfinite original model')
                _,den=value.as_integer_ratio();d=max(d,den)
            if time.monotonic()>deadline:raise TimeoutError('independent proof deadline')
    cache={}
    def integer(raw):
        value=float(raw)
        if value in cache:return cache[value]
        num,den=value.as_integer_ratio();answer=num*(d//den)
        if len(cache)<4096:cache[value]=answer
        return answer
    bi=list(map(integer,b));ci=list(map(integer,c));dual=[0]*n;primal_ok=True;max_violation=0
    visited=0
    for i in range(m):
        first,last=int(offsets[i]),int(offsets[i+1])
        if first>last or first<0 or last>len(values):raise ValueError('invalid original offsets')
        total=0;previous=-1
        for k in range(first,last):
            j=int(indices[k])
            if not previous<j<n:raise ValueError('noncanonical original CSR')
            previous=j;coefficient=integer(values[k]);total+=coefficient*xi[j];dual[j]+=coefficient*yi[i]
        violation=total-bi[i]*dx;max_violation=max(max_violation,violation);primal_ok=primal_ok and violation<=0
        visited+=last-first
        if i%64==0 and time.monotonic()>deadline:raise TimeoutError('independent proof deadline')
    residuals=[v-q*dy for v,q in zip(dual,ci)];dual_ok=all(v==0 for v in residuals)
    primal_value=sum(q*v for q,v in zip(ci,xi));dual_value=sum(q*v for q,v in zip(bi,yi))
    gap=primal_value*dy-dual_value*dx
    return dict(accepted=bool(primal_ok and dual_ok and gap==0),primal_feasible=bool(primal_ok),dual_equations=dual_ok,
        zero_gap=gap==0,visited_nonzeros=visited,rows=m,columns=n,
        max_primal_violation_numerator=str(max_violation),max_dual_residual_numerator=str(max(map(abs,residuals),default=0)),
        gap_numerator=str(gap),model_denominator_bits=d.bit_length(),primal_denominator_bits=dx.bit_length(),dual_denominator_bits=dy.bit_length(),
        elapsed_ns=time.perf_counter_ns()-start,arithmetic='Python unbounded integer; complete original CSR traversal')


def check(model,response,root=BASE,seconds=300):
    start=time.perf_counter_ns();raw=json.loads(Path(model).read_text());result=json.loads(Path(response).read_text())
    arrays={k:read_array(root,v) for k,v in raw['arrays'].items()}
    m,n=raw['rows'],raw['columns'];oi=arrays['objective_indices']
    if (raw.get('schema_version')!=1 or raw['nonzeros']!=len(arrays['values']) or len(arrays['row_upper'])!=m
            or len(arrays['column_lower'])!=n or len(arrays['column_upper'])!=n or len(arrays['row_lower'])!=m
            or len(oi)!=len(arrays['objective_values']) or (len(oi) and (int(oi[-1])>=n or np.any(oi[1:]<=oi[:-1])))):
        raise ValueError('original model dimensions or objective ordering')
    if raw.get('sense')!='maximize' or raw.get('offset')!=0 or not (np.isneginf(arrays['column_lower']).all() and np.isposinf(arrays['column_upper']).all() and np.isneginf(arrays['row_lower']).all()):
        raise ValueError('canonical free-variable upper-row model required')
    endpoint=result.get('endpoint');certificate=result.get('certificate')
    if certificate and certificate.get('status')=='optimal':x,y=certificate['x'],certificate['y'];tier='exact_rational_endpoint'
    elif endpoint:
        x=list(map(float,read_array(root,endpoint['primal'])));y=[-float(v) for v in read_array(root,endpoint['dual'])];tier='raw_binary64_endpoint_exactly_decoded'
    else:return dict(accepted=False,reason='no_endpoint',complete_ns=time.perf_counter_ns()-start)
    c=np.zeros(raw['columns']);c[arrays['objective_indices']]=arrays['objective_values']
    proof=verify_arrays(arrays['offsets'],arrays['indices'],arrays['values'],arrays['row_upper'],c,x,y,seconds)
    # The published floating endpoint must represent the same rational proof.
    if certificate and endpoint:
        px=read_array(root,endpoint['primal']);py=read_array(root,endpoint['dual'])
        same=(len(px)==len(x) and len(py)==len(y) and all(number(q)==Fraction(float(v)) for q,v in zip(x,px))
            and all(number(q)==-Fraction(float(v)) for q,v in zip(y,py)))
        proof['published_endpoint_matches']=same;proof['accepted']=proof['accepted'] and same
    proof.update(tier=tier,complete_ns=time.perf_counter_ns()-start,model=binding(model),response=binding(response))
    return proof


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('model',type=Path);p.add_argument('response',type=Path);p.add_argument('output',type=Path);p.add_argument('--seconds',type=float,default=300);a=p.parse_args()
    put(a.output,check(a.model,a.response,seconds=a.seconds))
