"""Identical bounded endpoint-reconstruction policy for every solver lane."""
import argparse
from pathlib import Path
import time
from lp_sp_pricing_budget import BASE, binding, put
from lp_sp_pricing_gpu_opt_compare import read
from lp_sp_pricing_geometry_run import load
from lp_sp_pricing_scale_reconstruct import reconstruct
from lp_sp_pricing_factor_proof import build
from lp_billion_arrays import read as read_array, write


def prepare(model,response,output,gpu=False):
    start=time.perf_counter_ns(); raw=read(response)
    result=dict(model=binding(model),original_response=binding(response),status='no_certificate')
    if raw.get('endpoint'):
        a,b,c,_,_=load(model)
        x=read_array(BASE,raw['endpoint']['primal']);y=-read_array(BASE,raw['endpoint']['dual'])
        endpoint,detail=reconstruct(a,b,c,x,y,seconds=30)
        result['dyadic_reconstruction']=detail
        if endpoint:
            certificate,px,py=endpoint
            result.update(status='explicit_exact_proposal',certificate=certificate,
                endpoint=dict(primal=write(BASE,px),dual=write(BASE,-py)))
        elif a.shape[0]>=a.shape[1] and a.shape[1]<=4096:
            # Cold GPU context setup exceeds the saved factor work at 2000
            # columns in the development microbenchmark. Keep small inverses
            # on CPU; use GPU for the larger square correction factors.
            cert,detail=build(a,b,c,x,y,gpu=gpu and a.shape[1]>2048);result['implicit_construction']=detail
            if cert:
                result.update(status='implicit_exact_proposal',implicit_certificate=dict(
                    primal=write(BASE,cert['x']),dual_base=write(BASE,cert['y0']),
                    basis=write(BASE,cert['basis'],'u32le'),inverse=write(BASE,cert['inverse'].ravel())))
    result['elapsed_ns']=time.perf_counter_ns()-start;put(output,result)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('model',type=Path);p.add_argument('response',type=Path)
    p.add_argument('output',type=Path);p.add_argument('--gpu',action='store_true');a=p.parse_args()
    prepare(a.model,a.response,a.output,a.gpu)
