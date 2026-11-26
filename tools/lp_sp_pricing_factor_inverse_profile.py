"""Cold CPU/GPU inverse proposal costs on a retained development basis."""
import time
import json
from lp_sp_pricing_budget import BASE,put,binding
from lp_sp_pricing_gpu_opt_compare import read
from lp_sp_pricing_factor_admit import validate
from lp_sp_pricing_geometry_run import load
from lp_billion_arrays import read as read_array
from sp_pricing.factor_projection import inverse_proposal
from sp_pricing.implicit_certificate import inverse_bound


def run():
    validate();out=BASE/'factor-inverse-profile-v1';out.mkdir(exist_ok=False)
    source=BASE/'factor-development-v1/candidate/postprocess/response.json';cert=read(source)
    a,_,_,_,_=load(cert['model']['path']);basis=read_array(BASE,cert['implicit_certificate']['basis'])
    bt=a[basis].toarray().T;rows=[]
    for gpu in (False,True):
        start=time.perf_counter_ns();inverse=inverse_proposal(bt,gpu=gpu);proposal=time.perf_counter_ns()-start
        start=time.perf_counter_ns();proof=inverse_bound(bt,inverse);verification=time.perf_counter_ns()-start
        rows.append(dict(gpu=gpu,proposal_ns=proposal,verification_ns=verification,proof=proof))
    put(out/'result.json',dict(source=binding(__file__),certificate=binding(source),rows=rows,
        disclosure='Same retained basis, fresh inverse microbenchmark; no repeated LP solve. CPU first, no cache flushing. GPU initialization included.'))
    print(json.dumps(rows),flush=True)


if __name__=='__main__':run()
