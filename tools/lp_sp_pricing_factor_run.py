"""Opt-in tall projection; square/wide dispatch preserves the previous solver."""
import argparse
import json
from pathlib import Path
import resource
import time
from unittest.mock import patch
from lp_sp_pricing_budget import BASE, put, binding
from lp_sp_pricing_geometry_run import load, run as previous
from lp_billion_arrays import write
from sp_pricing import geometry_fast
from sp_pricing.certificate_guard import guarded_certificate


def run(model, output, seconds=60, gpu=True):
    start = time.perf_counter_ns(); doc = json.loads(Path(model).read_text())
    m, n = doc.get('rows', 0), doc.get('columns', 0)
    if not (n and m >= 2*n and n <= 4096 and m*n <= 1 << 27):
        with patch.object(geometry_fast, 'exact_certificate', guarded_certificate):
            return previous(model, output, seconds, gpu)
    from sp_pricing.factor_projection import projection
    a,b,c,_,_ = load(model); input_ns = time.perf_counter_ns()-start
    solve = time.perf_counter_ns()
    try:
        x,y,details = projection(a,b,c,seconds,gpu)
        result = dict(status='numerical_proposal', endpoint=dict(primal=write(BASE,x), dual=write(BASE,-y)), proposal=details)
    except (ArithmeticError, ValueError, TimeoutError) as error:
        result = dict(status='inconclusive_factor_proposal', reason=str(error))
    result.update(route='factorized_tall_projection', input_ns=input_ns, solve_ns=time.perf_counter_ns()-solve,
        complete_ns=time.perf_counter_ns()-start, model=binding(model),
        process_hwm_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        paper_algorithm_completed=False, strongly_polynomial_claim=False,
        certificate_authority='none; common independent postprocessor must accept')
    put(output,result)
    return False


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('model',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--seconds',type=float,default=60);p.add_argument('--cpu',action='store_true');a=p.parse_args()
    raise SystemExit(int(run(a.model,a.output,a.seconds,not a.cpu)))
