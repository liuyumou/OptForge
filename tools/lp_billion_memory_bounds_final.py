"""Final source-specific bound; preserve formula 5 and its original reservations."""
import math
from lp_billion_memory_bounds import bounded_capacity as preliminary_capacity
from lp_billion_campaign import GIB


def bounded_capacity(model,lane):
    result=preliminary_capacity(model,lane)
    m,n,z=(model[k] for k in ['rows','columns','nonzeros'])
    stages=dict(result['stage_live_bytes'])
    # Isolated precondition.rs streams at most one line per worker. Summed
    # retained capacities of four disjoint maximal lines are <=2*z+16.
    # Old diagonals and both aggregate/worker output capacities fit resident's
    # dimension coefficients. Retain fixed-tree scratch and constant slack.
    stages['cpu_pock']=40*z+56*m+84*n+16*((z+1023)//1024)+65536
    result.update(formula_version=6,stage_live_bytes=stages,peak_stage=max(stages,key=stages.get),
        host_bytes=max(stages.values())+8*GIB,
        CPU_preparation_host_gib=math.ceil((max(stages[k] for k in ['preparation','cpu_construction','cpu_pock','cpu_spectral'])+8*GIB)/GIB))
    result['host_gib']=math.ceil(result['host_bytes']/GIB)
    result['admitted']=result['host_bytes']<=128*GIB and result['device_bytes']<=80*GIB and result['physical_fragment_index_upper']<2**32
    result['reason']=None if result['admitted'] else 'complete host/device/index allowance exceeds approved ceiling'
    return result
