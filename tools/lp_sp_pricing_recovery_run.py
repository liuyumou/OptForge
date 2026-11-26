"""Additive wide recovery; preserve successful square and irregular dispatch."""
import argparse
import json
from pathlib import Path
import resource
import time
from unittest.mock import patch
import numpy as np
import lp_sp_pricing_geometry_run as legacy
from lp_sp_pricing_transform_run import transformed
from lp_sp_pricing_budget import BASE,binding,put
from lp_billion_arrays import write
from sp_pricing.primal_recovery import row_proposal
from sp_pricing import factor_projection

class Recover(Exception):
    def __init__(self,a,b,c,detail,work):self.a,self.b,self.c,self.detail,self.work=a,b,c,detail,work

def run(model,output,seconds=60,gpu=True,wide_backend='auto'):
    start=time.perf_counter_ns();doc=json.loads(Path(model).read_text());m,n=doc.get('rows',0),doc.get('columns',0)
    if not n or m>=2*n or min(m,n)>4096 or m*n>1<<27:
        return transformed(model,output,seconds,16,'factor')
    prior={};solve=start
    if m>=n:
        # Successful old square/irregular fast paths run through the exact old
        # entry point. Only a rejected factor proposal reaches new work.
        original=legacy.certified_factor_proposal
        def intercept(a,b,c,work):
            proof,detail=original(a,b,c,work)
            if proof:return proof,detail
            raise Recover(a,b,c,detail,work)
        try:
            with patch.object(legacy,'certified_factor_proposal',intercept):return transformed(model,output,seconds,16,'factor')
        except Recover as item:
            a,b,c=item.a,item.b,item.c;prior=item.detail
            remaining=seconds-(time.monotonic()-item.work.started);solve=start
    else:
        a,b,c,_,_=legacy.load(model);remaining=seconds;solve=time.perf_counter_ns()
    try:
        if remaining<=0:raise TimeoutError('old presolve consumed allowance')
        if m<=n:
            use_gpu=gpu and m<n and (wide_backend=='gpu' or (wide_backend=='auto' and a.nnz/(m*n)>.2))
            x,y,detail=row_proposal(a,b,c,use_gpu)
        else:
            original=factor_projection.GpuProjection if gpu else factor_projection.CpuProjection
            class Scaled(original):
                def __init__(self,a,b,c,rho):super().__init__(a,b,c,rho*16)
            name='GpuProjection' if gpu else 'CpuProjection'
            with patch.object(factor_projection,name,Scaled):x,y,detail=factor_projection.projection(a,b,c,remaining,gpu)
            detail['rho_multiplier']=16
        result=dict(status='numerical_proposal',endpoint=dict(primal=write(BASE,x),dual=write(BASE,-y)),proposal=detail)
    except (ArithmeticError,ValueError,TimeoutError,np.linalg.LinAlgError) as error:result=dict(status='inconclusive_recovery',reason=str(error))
    result.update(route='factorized_row_recovery' if m<=n else 'factorized_mixed_projection',prior_presolve=prior,
        solve_ns=time.perf_counter_ns()-solve,input_ns=solve-start,complete_ns=time.perf_counter_ns()-start,model=binding(model),
        process_hwm_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,paper_algorithm_completed=False,strongly_polynomial_claim=False,
        certificate_authority='none; common independent postprocessor must accept')
    put(output,result);return False

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('model',type=Path);p.add_argument('output',type=Path);p.add_argument('--seconds',type=float,default=60);p.add_argument('--cpu',action='store_true');p.add_argument('--wide-backend',choices=['auto','cpu','gpu'],default='auto');a=p.parse_args();raise SystemExit(int(run(a.model,a.output,a.seconds,not a.cpu,a.wide_backend)))
