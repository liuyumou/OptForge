"""Common tall endpoint policy avoiding the unsuccessful short-dual ladder."""
import argparse
from pathlib import Path
import time
import numpy as np
from lp_sp_pricing_budget import BASE,binding,put
from lp_sp_pricing_gpu_opt_compare import read
from lp_sp_pricing_geometry_run import load
from lp_sp_pricing_factor_endpoint import prepare as previous
from lp_sp_pricing_factor_proof import exact_primal_proposal,inverse_proposal
from lp_billion_arrays import read as read_array,write


def build(a,b,c,x,y,gpu=False):
    start=time.perf_counter_ns();primal=exact_primal_proposal(a,b,c,x)
    if primal is None:return None,dict(reason='no_exact_active_primal')
    xp,active,px=primal;n=a.shape[1];rounded=np.rint(np.ldexp(np.maximum(y,0.),48))
    if not np.isfinite(rounded).all() or np.max(rounded,initial=0)>2**52:return None,dict(reason='dual_base_range')
    y0=np.ldexp(rounded,-48);y0[~active]=0.;available=np.flatnonzero(active&(y0>0))
    if len(available)<n:return None,dict(reason='insufficient_positive_active_rows')
    attempts=[]
    for selected in (available[np.argsort(-y0[available],kind='stable')[:n]],available[np.linspace(0,len(available)-1,n,dtype=int)]):
        try:
            inverse=inverse_proposal(a[selected].toarray().T,gpu=gpu)
            if not np.isfinite(inverse).all():raise ArithmeticError('nonfinite inverse')
        except (ArithmeticError,ValueError,np.linalg.LinAlgError) as error:
            attempts.append(str(error));continue
        refined=y0.copy();refinement_steps=0
        for _ in range(2):
            residual=c-np.asarray(a.T@refined).ravel()
            proposed=np.rint(np.ldexp(refined[selected]+inverse@residual,48))
            if not np.isfinite(proposed).all() or np.min(proposed,initial=0)<0 or np.max(proposed,initial=0)>2**52:break
            refined[selected]=np.ldexp(proposed,-48)
            refinement_steps+=1
        # No proof acceptance here. The independent checker computes the full
        # inverse enclosure once, alongside its original-model integer scan.
        return dict(x=xp,y0=refined,basis=selected.astype(np.uint32),inverse=inverse),dict(
            method='untrusted_implicit_dual_proposal',primal_exponent=px,dual_base_exponent=48,
            gpu_inverse=gpu,builder_inverse_bound_omitted=True,numerical_dual_refinement_steps=refinement_steps,basis_rows=n,active_rows=int(active.sum()),
            inverse_entries=n*n,explicit_rational_nullspace_entries=0,elapsed_ns=time.perf_counter_ns()-start,attempts=attempts)
    return None,dict(reason='inverse_proposal_failed',attempts=attempts)


def prepare(model,response,output):
    start=time.perf_counter_ns();doc=read(model)
    if not (doc['rows']>=2*doc['columns'] and doc['columns']<=4096):
        return previous(model,response,output,True)
    raw=read(response);result=dict(model=binding(model),original_response=binding(response),status='no_certificate',
        policy='tall implicit correction directly; no short-dual quantization search')
    if raw.get('endpoint'):
        a,b,c,_,_=load(model);x=read_array(BASE,raw['endpoint']['primal']);y=-read_array(BASE,raw['endpoint']['dual'])
        cert,detail=build(a,b,c,x,y,gpu=a.shape[1]>2048);result['implicit_construction']=detail
        if cert:
            result.update(status='implicit_exact_proposal',implicit_certificate=dict(primal=write(BASE,cert['x']),
                dual_base=write(BASE,cert['y0']),basis=write(BASE,cert['basis'],'u32le'),inverse=write(BASE,cert['inverse'].ravel())))
    result['elapsed_ns']=time.perf_counter_ns()-start;put(output,result)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('model',type=Path);p.add_argument('response',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    prepare(a.model,a.response,a.output)
