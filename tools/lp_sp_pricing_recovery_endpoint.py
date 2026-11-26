"""Common exact reconstruction policy, adding implicit primal recovery."""
import argparse
from pathlib import Path
import time
from lp_sp_pricing_budget import BASE,binding,put
from lp_sp_pricing_gpu_opt_compare import read
from lp_sp_pricing_geometry_run import load
from lp_sp_pricing_nontall_experiment import endpoint as old_endpoint
from lp_billion_arrays import read as read_array,write
from sp_pricing.primal_recovery import build

def prepare(model,response,output):
    start=time.perf_counter_ns();old=output.with_name('preceding-response.json');old_endpoint(model,response,old)
    previous=old.with_name('adaptive-response.json') if old.with_name('adaptive-response.json').exists() else old
    result=read(previous);result['preceding_proposal']=binding(previous)
    if not result.get('certificate') and not result.get('implicit_certificate'):
        raw=read(response)
        if raw.get('endpoint'):
            a,b,c,_,_=load(model);x=read_array(BASE,raw['endpoint']['primal']);y=-read_array(BASE,raw['endpoint']['dual'])
            cert,detail=build(a,b,c,x,y);result['implicit_primal_construction']=detail
            if cert:result.update(status='implicit_primal_proposal',implicit_primal_certificate=dict(
                primal_base=write(BASE,cert['x0']),dual=write(BASE,cert['y']),columns=write(BASE,cert['columns'],'u32le'),inverse=write(BASE,cert['inverse'].ravel())))
    result['elapsed_ns']=time.perf_counter_ns()-start;put(output,result)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('model',type=Path);p.add_argument('response',type=Path);p.add_argument('output',type=Path);a=p.parse_args();prepare(a.model,a.response,a.output)
