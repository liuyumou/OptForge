"""Exact-checked early projection and power-of-two row balancing for rectangular LPs."""
import argparse
import json
from pathlib import Path
import resource
import time
import numpy as np
import lp_sp_pricing_rectangular_run as previous
from lp_sp_pricing_budget import BASE,binding,put
from lp_sp_pricing_geometry_run import load
from lp_billion_arrays import write
from sp_pricing import factor_projection
from sp_pricing.dual_recovery_fast import build,dyadic_integers
from lp_sp_pricing_dual_fast_proof import verify_arrays


def equilibrate(a,b):
    degree=np.diff(a.indptr);nonempty=degree>0;maximum=np.ones(a.shape[0])
    if np.any(nonempty):maximum[nonempty]=np.maximum.reduceat(np.abs(a.data),a.indptr[:-1][nonempty])
    positive=maximum[maximum>0];spread=float(positive.max()/positive.min()) if len(positive) else 1.
    if not np.isfinite(spread) or spread<4:return a,b,np.ones(len(b)),dict(applied=False,row_norm_spread=spread if np.isfinite(spread) else None)
    exponent=np.where(maximum>0,np.frexp(maximum)[1]-1,0);scale=np.ldexp(np.ones(len(b)),-exponent)
    with np.errstate(over='ignore',under='ignore',invalid='ignore'):
        values=a.data*np.repeat(scale,degree);rhs=b*scale
    if not np.isfinite(values).all() or not np.isfinite(rhs).all() or np.any((a.data!=0)&(values==0)) or np.any((b!=0)&(rhs==0)):
        return a,b,np.ones(len(b)),dict(applied=False,reason='power_of_two_range')
    transformed=a.copy();transformed.data=values
    return transformed,rhs,scale,dict(applied=True,row_norm_spread=spread,minimum_scale=float(scale.min()),maximum_scale=float(scale.max()))


def projection(a,b,c,seconds=60,gpu=True,early=True,balance=True):
    start=time.perf_counter_ns();deadline=time.monotonic()+seconds;m,n=a.shape
    if not n<m or n>4096 or m*n>1<<27:raise ValueError('final projection shape')
    transformed,rhs,scale,balancing=equilibrate(a,b) if balance else (a,b,np.ones(m),dict(applied=False))
    rho=16*max(1e-8,min(1.,float(np.linalg.norm(c))/max(float(np.linalg.norm(transformed.data))*np.sqrt(m),1e-30)))
    state=(factor_projection.GpuProjection if gpu else factor_projection.CpuProjection)(transformed,rhs,c,rho)
    setup=time.perf_counter_ns()-start;records=[];trials=[];cert=None;x=y=None;encoded=None
    enabled=early and (m<2*n or balancing['applied'])
    try:
        for step in range(100,6001,100):
            if time.monotonic()>=deadline:break
            x,dual=state.advance(100);y=scale*dual
            if not np.isfinite(x).all() or not np.isfinite(y).all():raise ArithmeticError('nonfinite projection')
            primal=float(np.max(a@x-b,initial=0))/(1+float(np.max(np.abs(b),initial=0)));stationarity=float(np.max(np.abs(a.T@y-c),initial=0))/(1+float(np.max(np.abs(c),initial=0)))
            records.append(dict(steps=step,primal=primal,dual=stationarity))
            if enabled and max(primal,stationarity)<1e-5 and len(trials)<12:
                begin=time.perf_counter_ns()
                if encoded is None:encoded=dyadic_integers([a.data,b,c])
                proposal,detail=build(a,b,c,x,y,encoded);proof=None
                if proposal:
                    proof=verify_arrays(a.indptr,a.indices,a.data,b,c,proposal['x'],proposal['y0'],proposal['basis'],proposal['inverse'],seconds=max(.001,deadline-time.monotonic()))
                trials.append(dict(steps=step,construction=detail,accepted=bool(proof and proof['accepted']),check=proof,complete_ns=time.perf_counter_ns()-begin))
                if proof and proof['accepted']:cert=proposal;break
            if max(primal,stationarity)<1e-10:break
    finally:state.close()
    if x is None:raise TimeoutError('projection setup consumed allowance')
    return x,y,cert,dict(method='checked_early_factor_projection',gpu=gpu,rho=rho,rho_multiplier=16,setup_ns=setup,complete_ns=time.perf_counter_ns()-start,
        steps=records[-1]['steps'],checkpoints=records,early_trials=trials,balancing=balancing,early_enabled=enabled,stored_matrix_entries=m*n+n*n,explicit_nullspace_entries=0)


def run(model,output,seconds=60,gpu=True,wide_backend='cpu'):
    start=time.perf_counter_ns();doc=json.loads(Path(model).read_text());m,n=doc.get('rows',0),doc.get('columns',0)
    if not n<m or n>4096 or m*n>1<<27:return previous.run(model,output,seconds,gpu,wide_backend,16)
    a,b,c,_,_=load(model);loaded=time.perf_counter_ns()
    try:
        x,y,cert,detail=projection(a,b,c,max(.001,seconds-(loaded-start)/1e9),gpu)
        result=dict(status='numerical_proposal',endpoint=dict(primal=write(BASE,x),dual=write(BASE,-y)),proposal=detail)
        if cert:result['implicit_certificate']=dict(primal=write(BASE,cert['x']),dual_base=write(BASE,cert['y0']),basis=write(BASE,cert['basis'],'u32le'),inverse=write(BASE,cert['inverse'].ravel()))
    except (ArithmeticError,ValueError,TimeoutError,np.linalg.LinAlgError) as error:result=dict(status='inconclusive_projection',reason=str(error))
    result.update(route='balanced_checked_projection',input_ns=loaded-start,solve_ns=time.perf_counter_ns()-start,complete_ns=time.perf_counter_ns()-start,model=binding(model),
        process_hwm_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,paper_algorithm_completed=False,strongly_polynomial_claim=False,certificate_authority='Separate cold independent original-model checker')
    put(output,result);return False

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('model',type=Path);p.add_argument('output',type=Path);p.add_argument('--seconds',type=float,default=60);p.add_argument('--cpu',action='store_true');p.add_argument('--wide-backend',choices=['cpu','gpu','auto'],default='cpu');a=p.parse_args();raise SystemExit(int(run(a.model,a.output,a.seconds,not a.cpu,a.wide_backend)))
