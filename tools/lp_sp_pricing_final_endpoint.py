"""Common certificate construction; unchanged non-tall success paths."""
if __name__=='__main__':
    import json,os,sys
    if len(sys.argv)>1 and not sys.argv[1].startswith('-'):
        with open(sys.argv[1]) as stream:_shape=json.load(stream)
        if _shape['rows']>_shape['columns'] and _shape['columns']<=4096:
            os.environ['OPENBLAS_NUM_THREADS']='4';os.environ['MKL_NUM_THREADS']='4'
import argparse
from pathlib import Path
import time
from lp_sp_pricing_budget import BASE,binding,put
from lp_sp_pricing_gpu_opt_compare import read
from lp_sp_pricing_geometry_run import load
from lp_sp_pricing_recovery_endpoint_balanced import prepare as previous
from lp_billion_arrays import read as read_array,write
from sp_pricing.dual_recovery_fast import build


def prepare(model,response,output):
    start=time.perf_counter_ns();doc=read(model)
    if not doc['rows']>doc['columns'] or doc['columns']>4096:return previous(model,response,output)
    raw=read(response);result=dict(status='no_certificate',model=binding(model),original_response=binding(response),policy='common adaptive implicit dual; independent checker alone accepts')
    if raw.get('implicit_certificate'):
        result.update(status='implicit_exact_proposal',implicit_certificate=raw['implicit_certificate'],construction=dict(method='reuse_untrusted_proposal_no_acceptance'))
    elif raw.get('endpoint'):
        a,b,c,_,_=load(model);x=read_array(BASE,raw['endpoint']['primal']);y=-read_array(BASE,raw['endpoint']['dual']);cert,detail=build(a,b,c,x,y);result['construction']=detail
        if cert:result.update(status='implicit_exact_proposal',implicit_certificate=dict(primal=write(BASE,cert['x']),dual_base=write(BASE,cert['y0']),basis=write(BASE,cert['basis'],'u32le'),inverse=write(BASE,cert['inverse'].ravel())))
    result['elapsed_ns']=time.perf_counter_ns()-start;put(output,result)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('model',type=Path);p.add_argument('response',type=Path);p.add_argument('output',type=Path);a=p.parse_args();prepare(a.model,a.response,a.output)
