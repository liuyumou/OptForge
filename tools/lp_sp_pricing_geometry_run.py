"""Cold exact-certified factor presolve, then native/compact pricing fallback."""
import argparse
from fractions import Fraction as Q
import json
from pathlib import Path
import resource
import sys
import time
import numpy as np
from scipy import sparse
from lp_sp_pricing_budget import ROOT,BASE,put,binding
from lp_billion_arrays import read as read_array,write
from lp_sp_pricing_compact_run import load as old_load,verify

sys.path.insert(0,str(ROOT/'research/lp-sp-pricing/python'))
from sp_pricing.geometry_fast import FastGeometrySolver,certified_factor_proposal
from sp_pricing.compact_basis import Rows
from sp_pricing.exact import Work,Limit,encode,rational


def load(path):
    doc=json.loads(Path(path).read_text())
    if 'A' in doc:
        model=old_load(path);a=sparse.csr_matrix([[float(rational(q)) for q in row] for row in model['A']])
        b=np.asarray(list(map(lambda v:float(rational(v)),model['b'])));c=np.asarray(list(map(lambda v:float(rational(v)),model['c'])))
        exact=all(Q(float(q))==rational(v) for row,raw in zip(a.toarray(),model['A']) for q,v in zip(row,raw))
        exact=exact and all(Q(float(q))==rational(v) for q,v in zip(b,model['b'])) and all(Q(float(q))==rational(v) for q,v in zip(c,model['c']))
        return a,b,c,model,exact
    if doc.get('schema_version')!=1 or doc.get('sense')!='maximize' or doc.get('offset')!=0:raise ValueError('canonical portable model')
    data={k:read_array(BASE,v) for k,v in doc['arrays'].items()}
    if not (np.isneginf(data['column_lower']).all() and np.isposinf(data['column_upper']).all() and np.isneginf(data['row_lower']).all()):raise ValueError('free variables and upper rows required')
    a=sparse.csr_matrix((data['values'],data['indices'],data['offsets']),shape=(doc['rows'],doc['columns']))
    if not a.has_canonical_format or not np.isfinite(a.data).all():raise ValueError('canonical finite CSR')
    b=np.asarray(data['row_upper']);c=np.zeros(doc['columns']);c[data['objective_indices']]=data['objective_values']
    return a,b,c,None,True


def run(path,output,seconds=30,gpu=True,presolve=True):
    complete=time.perf_counter_ns();a,b,c,model,can_propose=load(path);input_ns=time.perf_counter_ns()-complete
    work=Work(seconds=seconds,max_operations=200000000,max_bits=16384)
    solver=FastGeometrySolver(work=work,extra_experts=4096,max_queries=1024,batch_width=32,
        gpu=dict(steps=128,pipeline=True) if gpu else None,market_backend='flow',rank_gpu=gpu)
    start=time.perf_counter_ns();proposal={};proof=None
    try:
        if presolve and can_propose:proof,proposal=certified_factor_proposal(a,b,c,work)
        if proof:
            result=dict(status='certificate_returned',certificate=proof,route='exact_certified_factor_presolve',
                audit=dict(accepted=True,outcome='optimal',authority='exact_bounded_integer_original_model'))
        else:
            convert=time.perf_counter_ns()
            if model is None:model=old_load(path)
            proposal['fallback_input_ns']=time.perf_counter_ns()-convert
            result=solver.solve(model);result['route']='native_compact_pricing'
            checked=time.perf_counter_ns();result['audit']=verify(model,result.get('certificate'))
            result['independent_check_ns']=time.perf_counter_ns()-checked
    except Limit as e:result=dict(status='resource_limit',reason=str(e),certificate=None,route='native_compact_pricing',audit=dict(accepted=False))
    except (ArithmeticError,ValueError,OverflowError) as e:result=dict(status='implementation_error',reason=repr(e),certificate=None,audit=dict(accepted=False))
    result.update(solve_ns=time.perf_counter_ns()-start,input_ns=input_ns,proposal=proposal,
        phase_ns=solver.phase_ns,geometry_diagnostics=solver.geometry_diagnostics,events=solver.events,
        queries=solver.queries,storage_peak_entries=solver.storage.peak_entries,
        work=dict(operations=work.operations,peak_bits=work.peak_bits),model=binding(path),
        paper_algorithm_completed=False,strongly_polynomial_claim=False)
    if result.get('certificate') and result['certificate']['status']=='optimal':
        proof=result['certificate'];result['endpoint']=dict(primal=write(BASE,[float(v) for v in proof['x']]),dual=write(BASE,[-float(v) for v in proof['y']]))
    result['complete_ns']=time.perf_counter_ns()-complete;result['process_hwm_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
    put(output,encode(result));print(json.dumps({k:result[k] for k in ['status','solve_ns','route','audit']}),flush=True)
    return result['status']=='implementation_error'


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('model',type=Path);p.add_argument('output',type=Path);p.add_argument('--seconds',type=float,default=30)
    p.add_argument('--cpu',action='store_true');p.add_argument('--no-presolve',action='store_true');a=p.parse_args()
    raise SystemExit(int(run(a.model,a.output,a.seconds,not a.cpu,not a.no_presolve)))
