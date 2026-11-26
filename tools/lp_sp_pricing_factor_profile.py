"""Fresh exact-GMP geometry scaling diagnostic with immutable old source."""
import json
import time
from fractions import Fraction as Q
from unittest.mock import patch
from lp_sp_pricing_budget import BASE,ROOT,put,binding
from lp_sp_pricing_factor_admit import fixture,validate
from lp_sp_pricing_factor_proof import build,verify_arrays
from sp_pricing import compact_solver
from sp_pricing.compact_basis import Rows,Storage
from sp_pricing.geometry_fast import native_rref
from sp_pricing.factor_projection import projection
from sp_pricing.exact import Work,Limit


def run():
    validate();out=BASE/'factor-geometry-profile-v1';out.mkdir(exist_ok=False);rows=[]
    for n in (16,32,64,128,256):
        a,b,c,_,_=fixture(n,123951+n);start=time.perf_counter_ns()
        exact=Rows(({int(a.indices[k]):Q(float(a.data[k])) for k in range(a.indptr[i],a.indptr[i+1])} for i in range(a.shape[0])),n)
        rhs=list(map(lambda v:Q(float(v)),b));conversion=time.perf_counter_ns()-start
        work=Work(seconds=8,max_operations=200000000,max_bits=16384);storage=Storage();start=time.perf_counter_ns();status='completed';rank=None
        try:
            with patch.object(compact_solver,'sparse_rref',native_rref):
                reduced,pivots=compact_solver.slack_factors(exact,rhs,work,storage)
            rank=len(pivots)
        except Limit as error:status=str(error)
        elapsed=time.perf_counter_ns()-start
        x,y,detail=projection(a,b,c,seconds=8,gpu=False,max_steps=3000)
        cert,meta=build(a,b,c,x,y,gpu=False)
        proof=verify_arrays(a.indptr,a.indices,a.data,b,c,cert['x'],cert['y0'],cert['basis'],cert['inverse']) if cert else dict(accepted=False)
        row=dict(n=n,m=a.shape[0],nonzeros=a.nnz,conversion_ns=conversion,exact_rref_ns=elapsed,
            exact_status=status,rank=rank,completed_operation_count=work.operations,completed_peak_bits=work.peak_bits,
            completed_peak_fill_entries=storage.peak_entries,projection=detail,implicit_construction=meta,proof=proof,
            incomplete_counters=status!='completed')
        rows.append(row);print(json.dumps(row),flush=True)
    put(out/'result.json',dict(rows=rows,sources=[binding(__file__),binding(ROOT/'research/lp-sp-pricing/native/geometry_exact.cpp')],
        interpretation='Geometry-only timings versus numerical projection plus proof; distinct operations, not equal-algorithm speedups. Native failure discards internal counters; never infer zero work from them.'))


if __name__=='__main__':run()
