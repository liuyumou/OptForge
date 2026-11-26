"""Fresh CPU geometry diagnostics; no historical LP or driver is repeated."""
import cProfile
import io
import json
import pstats
import sys
import time
from fractions import Fraction as Q
from lp_sp_pricing_budget import BASE, ROOT, put, binding
from lp_sp_pricing_million import matrix, ORIGINAL
from sp_pricing.compact_basis import Rows, Storage, PairedRows
from sp_pricing.compact_solver import slack_factors
from sp_pricing.compact_geometry import CompactCalibration
from sp_pricing.exact import Work, Limit


def run(identity):
    out=BASE/identity;out.mkdir(exist_ok=False);results=[]
    for spec in ORIGINAL:
        start=time.perf_counter_ns();a=matrix(spec['m'],spec['n'],spec['degree'],122101,spec['shift'])
        pool={i:Q(i,16) for i in range(1,32)}
        rows=Rows(({int(a.indices[k]):pool[int(a.data[k]*16)]
            for k in range(a.indptr[i],a.indptr[i+1])} for i in range(a.shape[0])),a.shape[1])
        b=[sum(row.values(),Q(0)) for row in rows.rows]
        input_ns=time.perf_counter_ns()-start
        work=Work(seconds=8,max_operations=200000000);storage=Storage();profile=cProfile.Profile()
        stage='slack_rref';status='completed';reason=None;begin=time.perf_counter_ns()
        profile.enable()
        try:
            reduced,pivots=slack_factors(rows,b,work,storage)
            stage='initial_calibration';CompactCalibration(PairedRows(reduced,pivots),work,storage)
        except Limit as error:status='resource_limit';reason=str(error)
        finally:profile.disable()
        profile.dump_stats(str(out/(spec['name']+'.pstats')))
        stream=io.StringIO();pstats.Stats(profile,stream=stream).strip_dirs().sort_stats('cumulative').print_stats(35)
        (out/(spec['name']+'.txt')).write_text(stream.getvalue())
        result=dict(model=spec,seed=122101,status=status,reason=reason,stage=stage,
            input_ns=input_ns,geometry_ns=time.perf_counter_ns()-begin,operations=work.operations,
            peak_bits=work.peak_bits,storage_peak_entries=storage.peak_entries,
            profile=binding(out/(spec['name']+'.txt')))
        results.append(result);print(json.dumps(result),flush=True)
    put(out/'result.json',dict(status='profiled',rows=results,source=binding(__file__),
        limitation='cProfile adds overhead; these timings diagnose call costs, not uninstrumented throughput'))


if __name__=='__main__':run(sys.argv[1])
