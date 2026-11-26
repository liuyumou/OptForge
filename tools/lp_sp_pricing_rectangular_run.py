"""Opt-in direct projection only for the formerly rejected rectangular interval."""
import argparse
import json
from pathlib import Path
import resource
import time
from unittest.mock import patch
import numpy as np
import lp_sp_pricing_recovery_run_fast as previous
from lp_sp_pricing_budget import BASE,binding,put
from lp_billion_arrays import write
from sp_pricing import factor_projection


def run(model,output,seconds=60,gpu=True,wide_backend='auto',rho_multiplier=16):
    if rho_multiplier not in (16,64,256,1024):raise ValueError('admitted rectangular multiplier')
    start=time.perf_counter_ns();doc=json.loads(Path(model).read_text());m,n=doc.get('rows',0),doc.get('columns',0)
    if not n<m<2*n or n>4096 or m*n>1<<27:
        return previous.run(model,output,seconds,gpu,wide_backend)
    a,b,c,_,_=previous.original.legacy.load(model);loaded=time.perf_counter_ns()
    try:
        remaining=seconds-(loaded-start)/1e9
        if remaining<=0:raise TimeoutError('rectangular input consumed allowance')
        cls=factor_projection.GpuProjection if gpu else factor_projection.CpuProjection
        class Scaled(cls):
            def __init__(self,a,b,c,rho):super().__init__(a,b,c,rho*rho_multiplier)
        with patch.object(factor_projection,'GpuProjection' if gpu else 'CpuProjection',Scaled):x,y,detail=factor_projection.projection(a,b,c,remaining,gpu)
        detail['rho_multiplier']=rho_multiplier
        result=dict(status='numerical_proposal',endpoint=dict(primal=write(BASE,x),dual=write(BASE,-y)),proposal=detail)
    except (ArithmeticError,ValueError,TimeoutError,np.linalg.LinAlgError) as error:result=dict(status='inconclusive_recovery',reason=str(error))
    result.update(route='direct_factorized_mixed_projection',prior_presolve=dict(method='skipped_rectangular_lsmr',complete_ns=0),
        input_ns=loaded-start,solve_ns=time.perf_counter_ns()-start,complete_ns=time.perf_counter_ns()-start,model=binding(model),
        process_hwm_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,paper_algorithm_completed=False,strongly_polynomial_claim=False,
        certificate_authority='none; unchanged common independent postprocessor must accept')
    put(output,result);return False

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('model',type=Path);p.add_argument('output',type=Path);p.add_argument('--seconds',type=float,default=60);p.add_argument('--cpu',action='store_true');p.add_argument('--wide-backend',choices=['auto','cpu','gpu'],default='auto');p.add_argument('--rho-multiplier',type=int,choices=[16,64,256,1024],default=16);a=p.parse_args();raise SystemExit(int(run(a.model,a.output,a.seconds,not a.cpu,a.wide_backend,a.rho_multiplier)))
