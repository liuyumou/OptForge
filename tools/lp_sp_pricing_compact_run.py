"""Cold opt-in compact candidate; accepts canonical dense JSON or portable CSR."""
import argparse
from fractions import Fraction as Q
import json
from pathlib import Path
import resource
import sys
import time
from lp_sp_pricing_budget import ROOT,BASE,put,binding
from lp_billion_arrays import read as read_array,write

sys.path.insert(0,str(ROOT/'research/lp-sp-pricing/python'))
from sp_pricing.compact_basis import Rows,Storage
from sp_pricing.compact_solver import CompactSolver
from sp_pricing.exact import Work,Limit,encode,rational


def load(path):
    raw=json.loads(Path(path).read_text())
    if 'A' in raw:return raw
    if raw.get('schema_version')!=1 or raw.get('sense')!='maximize' or raw.get('offset')!=0:
        raise ValueError('canonical portable model required')
    data={k:read_array(BASE,v) for k,v in raw['arrays'].items()}
    import numpy as np
    if not (np.isneginf(data['column_lower']).all() and np.isposinf(data['column_upper']).all()
            and np.isneginf(data['row_lower']).all()):raise ValueError('free variables and upper rows required')
    cache={}
    def q(v):
        v=float(v)
        if v not in cache:
            if len(cache)>=4096:cache.clear()
            cache[v]=Q(v)
        return cache[v]
    def rows():
        for i in range(raw['rows']):
            first,last=map(int,data['offsets'][i:i+2])
            yield {int(data['indices'][k]):q(data['values'][k]) for k in range(first,last)}
    a=Rows(rows(),raw['columns']);c=[Q(0)]*raw['columns']
    for j,v in zip(data['objective_indices'],data['objective_values']):c[int(j)]=q(v)
    return dict(A=a,b=[q(v) for v in data['row_upper']],c=c,sense='max')


def verify(model,certificate):
    """Independent original inequalities/equalities; no geometry products reused."""
    if certificate is None:return dict(accepted=False,reason='no_endpoint')
    a=model['A'];m=len(model['b']);n=len(model['c'])
    row=lambda i:a.row(i).items() if isinstance(a,Rows) else enumerate(map(rational,a[i]))
    b=list(map(rational,model['b']));c=list(map(rational,model['c']))
    def primal(x):
        return len(x)==n and all(sum((v*x[j] for j,v in row(i)),Q(0))<=b[i] for i in range(m))
    def dual(y):
        if len(y)!=m or any(v<0 for v in y):return None
        value=[Q(0)]*n
        for i in range(m):
            if y[i]:
                for j,q in row(i):value[j]+=q*y[i]
        return value
    status=certificate['status'];accepted=False
    if status=='optimal':
        x=list(map(rational,certificate['x']));y=list(map(rational,certificate['y']))
        accepted=primal(x) and dual(y)==c and sum((v*q for v,q in zip(c,x)),Q(0))==sum((v*q for v,q in zip(b,y)),Q(0))
    elif status=='infeasible':
        y=list(map(rational,certificate['y']));accepted=dual(y)==[Q(0)]*n and sum((v*q for v,q in zip(b,y)),Q(0))<0
    elif status=='unbounded':
        x=list(map(rational,certificate['x']));d=list(map(rational,certificate['ray']))
        accepted=(primal(x) and len(d)==n and sum((v*q for v,q in zip(c,d)),Q(0))>0 and
            all(sum((q*d[j] for j,q in row(i)),Q(0))<=0 for i in range(m)))
    return dict(accepted=bool(accepted),outcome=status)


def run(path,output,seconds=20,gpu=True,pipeline=True,width=32,steps=128):
    complete=time.perf_counter_ns();model=load(path);input_ns=time.perf_counter_ns()-complete
    work=Work(seconds=seconds,max_operations=200000000,max_bits=16384)
    config=dict(steps=steps,pipeline=pipeline) if gpu else None
    solver=CompactSolver(work=work,extra_experts=4096,max_queries=1024,batch_width=width,gpu=config,market_backend='flow')
    start=time.perf_counter_ns()
    try:result=solver.solve(model)
    except Limit as e:result=dict(status='resource_limit',reason=str(e),certificate=None)
    except (ArithmeticError,ValueError,OverflowError) as e:result=dict(status='implementation_error',reason=repr(e),certificate=None)
    result.update(solve_ns=time.perf_counter_ns()-start,phase_ns=solver.phase_ns,events=solver.events,
        compact_geometry=solver.compact_profiles,storage_peak_entries=solver.storage.peak_entries,
        storage_peak_estimated_bytes=solver.storage.peak_bytes,queries=solver.queries,
        work=dict(operations=work.operations,peak_bits=work.peak_bits),configuration=config,
        input_ns=input_ns,model=binding(path),paper_algorithm_completed=False,strongly_polynomial_claim=False)
    audit_start=time.perf_counter_ns();result['audit']=verify(model,result['certificate'])
    result['independent_check_ns']=time.perf_counter_ns()-audit_start
    if result['certificate'] and not result['audit']['accepted']:raise ArithmeticError('independent original certificate rejected')
    if result['certificate'] and result['certificate']['status']=='optimal':
        proof=result['certificate'];result['endpoint']=dict(primal=write(BASE,[float(q) for q in proof['x']]),
            dual=write(BASE,[-float(q) for q in proof['y']]))
    result['complete_ns']=time.perf_counter_ns()-complete
    result['process_hwm_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
    put(output,encode(result));print(json.dumps({k:result[k] for k in ['status','solve_ns','audit','process_hwm_bytes']}),flush=True)
    return result['status']=='implementation_error'


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('model',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--seconds',type=float,default=20);p.add_argument('--cpu',action='store_true');p.add_argument('--serial',action='store_true')
    p.add_argument('--width',type=int,default=32);p.add_argument('--steps',type=int,default=128);a=p.parse_args()
    raise SystemExit(int(run(a.model,a.output,a.seconds,not a.cpu,not a.serial,a.width,a.steps)))
