"""Overlap a bounded exact correction worker with unchanged GPU projection."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import time
from unittest.mock import patch
import numpy as np
import lp_sp_pricing_final_screened_run as previous
import lp_sp_pricing_final_run as original
from sp_pricing.dual_recovery_cached import CachedCorrection,blas_threads
from sp_pricing.factor_projection import GpuProjection
from lp_sp_pricing_dual_fast_proof import verify_arrays
OLD_PROJECTION=original.projection


def projection(a,b,c,seconds=60,gpu=True,early=True,balance=True,inverse_gpu=True,pipeline=True):
    start=time.perf_counter_ns();deadline=time.monotonic()+seconds;m,n=a.shape
    transformed,rhs,scale,balancing=original.equilibrate(a,b) if balance else (a,b,np.ones(m),dict(applied=False))
    if not (gpu and early and m>=2*n and balancing['applied']):
        with patch.object(original,'equilibrate',return_value=(transformed,rhs,scale,balancing)):
            return OLD_PROJECTION(a,b,c,seconds,gpu,early,balance)
    rho=16*max(1e-8,min(1.,float(np.linalg.norm(c))/max(float(np.linalg.norm(transformed.data))*np.sqrt(m),1e-30)))
    state=GpuProjection(transformed,rhs,c,rho);setup=time.perf_counter_ns()-start
    cache=CachedCorrection(a,b,c,inverse_gpu);records=[];trials=[];advances=[];future=None;certificate=None;x=y=None;accepted_step=None;wait_ns=0
    def work(x,y,step):
        begin=time.perf_counter_ns();k,detail=cache.build(x,y);proof=None
        if k is not None:
            proof=verify_arrays(a.indptr,a.indices,a.data,b,c,k['x'],k['y0'],k['basis'],k['inverse'],seconds=max(.001,deadline-time.monotonic()))
        end=time.perf_counter_ns();return x,y,k,dict(steps=step,construction=detail,check=proof,accepted=bool(proof and proof['accepted']),start_ns=begin-start,end_ns=end-start,complete_ns=end-begin)
    def consume(result):
        sx,sy,k,detail=result;trials.append(detail)
        return (sx,sy,k,detail['steps']) if detail['accepted'] else None
    pool=None
    try:
        with blas_threads(3) as thread_settings:
            pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='exact-correction') if pipeline else None
            for step in range(100,6001,100):
                if time.monotonic()>=deadline:break
                begin=time.perf_counter_ns();x,dual=state.advance(100);end=time.perf_counter_ns();advances.append((begin-start,end-start));y=scale*dual
                if not np.isfinite(x).all() or not np.isfinite(y).all():raise ArithmeticError('nonfinite projection')
                primal=float(np.max(a@x-b,initial=0))/(1+float(np.max(np.abs(b),initial=0)));dual=float(np.max(np.abs(a.T@y-c),initial=0))/(1+float(np.max(np.abs(c),initial=0)))
                records.append(dict(steps=step,primal=primal,dual=dual))
                if future is not None and future.done():
                    result=consume(future.result());future=None
                    if result is not None:x,y,certificate,accepted_step=result;break
                if future is None and max(primal,dual)<1e-5 and len(trials)<12:
                    if pipeline:future=pool.submit(work,x.copy(),y.copy(),step)
                    else:
                        result=consume(work(x,y,step))
                        if result is not None:x,y,certificate,accepted_step=result;break
                if max(primal,dual)<1e-10:break
            if future is not None:
                begin=time.perf_counter_ns();result=consume(future.result());wait_ns+=time.perf_counter_ns()-begin;future=None
                if result is not None:x,y,certificate,accepted_step=result
            if pool is not None:pool.shutdown(wait=True);pool=None
    finally:
        if pool is not None:pool.shutdown(wait=True)
        state.close()
    if x is None:raise TimeoutError('projection setup consumed allowance')
    overlap=sum(max(0,min(end,t['end_ns'])-max(begin,t['start_ns'])) for begin,end in advances for t in trials)
    return x,y,certificate,dict(method='cached_pipelined_exact_correction',gpu=True,rho=rho,rho_multiplier=16,setup_ns=setup,complete_ns=time.perf_counter_ns()-start,steps=records[-1]['steps'],checkpoints=records,early_trials=trials,balancing=balancing,early_enabled=True,certificate_snapshot_step=accepted_step,
        pipeline=pipeline,inverse_gpu=inverse_gpu,cache_builds=cache.builds,cache_hits=cache.hits,resident_inverses=len(cache.cache),maximum_pending_corrections=1,blas_threads=thread_settings,
        projection_advance_ns=sum(end-begin for begin,end in advances),correction_active_ns=sum(t['complete_ns'] for t in trials),correction_projection_overlap_ns=overlap,main_wait_ns=wait_ns,
        overlap_definition='Intersection of worker wall intervals with host-observed GPU advance calls; not kernel-active time.',stored_matrix_entries=m*n+n*n,explicit_nullspace_entries=0)


def run(model,output,seconds=60,gpu=True,wide_backend='cpu',inverse_gpu=True,pipeline=True):
    def selected(*args,**kwargs):return projection(*args,**kwargs,inverse_gpu=inverse_gpu,pipeline=pipeline)
    with patch.object(original,'projection',selected):return previous.run(model,output,seconds,gpu,wide_backend)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('model',type=Path);p.add_argument('output',type=Path);p.add_argument('--seconds',type=float,default=60);p.add_argument('--cpu',action='store_true');p.add_argument('--wide-backend',choices=['cpu','gpu','auto'],default='cpu');p.add_argument('--inverse-backend',choices=['cpu','gpu'],default='gpu');p.add_argument('--synchronous',action='store_true');a=p.parse_args();raise SystemExit(int(run(a.model,a.output,a.seconds,not a.cpu,a.wide_backend,a.inverse_backend=='gpu',not a.synchronous)))
