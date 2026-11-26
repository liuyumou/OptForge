"""Fresh bounded CPU diagnosis; profiling timings are not benchmark timings."""
import cProfile
import json
from pathlib import Path
import pstats
import sys

from lp_sp_pricing_budget import BASE, put, binding
from lp_sp_pricing_run import attempt


def main():
    out = BASE/sys.argv[1]
    out.mkdir(exist_ok=False)
    models = {
        "bounded": dict(A=[[1], [-1]], b=[2, 0], c=[1]),
        "coupled": dict(A=[[1, 1], [-1, 0], [0, -1]], b=[2, 0, 0], c=[1, 1]),
    }
    rows = []
    for name, model in models.items():
        profiler = cProfile.Profile()
        result = profiler.runcall(attempt, model, seconds=15, operations=100_000_000)
        profiler.dump_stats(str(out/(name+".pstats")))
        with (out/(name+".txt")).open("x") as stream:
            pstats.Stats(profiler, stream=stream).strip_dirs().sort_stats("cumulative").print_stats(35)
        put(out/(name+".result.json"), result)
        rows.append(dict(name=name, status=result["status"], phases=result["phase_ns"],
                         profile=binding(out/(name+".pstats"))))
    put(out/"result.json", dict(status="profiled", benchmark=False, rows=rows))
    print(json.dumps(rows))


if __name__ == "__main__":
    main()
