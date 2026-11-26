"""Separate-seed development ladder; all attempted outcomes remain visible."""
import argparse
import json
from pathlib import Path
from lp_sp_pricing_budget import BASE, put, binding
from lp_sp_pricing_run import attempt
from lp_sp_pricing_study import FAMILIES, generated


def main():
    p = argparse.ArgumentParser()
    p.add_argument("identity")
    p.add_argument("--sizes", type=int, nargs="+", default=[4, 8])
    p.add_argument("--seconds", type=float, default=10)
    p.add_argument("--gpu-library", type=Path)
    args = p.parse_args()
    out = BASE/args.identity
    out.mkdir(exist_ok=False)
    cells = [dict(id=f"{family}-{n}-73011", family=family, columns=n,
                  rows=max(2,n//2) if family=="wide" else 4*n if family=="tall" else 2*n,
                  seed=73011) for n in args.sizes for family in FAMILIES]
    put(out/"plan.json", dict(cells=cells, seconds=args.seconds, source=binding(__file__), heldout=False))
    rows = []
    gpu = None if args.gpu_library is None else dict(library=str(args.gpu_library.resolve()), mode="fp32x2", sparse=True)
    if gpu:
        from lp_sp_pricing_gpu_admission import validate
        validate(args.gpu_library)
    for cell in cells:
        directory = out/cell["id"]
        directory.mkdir()
        model, construction = generated(cell)
        put(directory/"model.json", model);put(directory/"construction.json", construction)
        put(directory/"started.json", dict(model=binding(directory/"model.json")))
        result = attempt(model, seconds=args.seconds, operations=200_000_000, gpu=gpu)
        put(directory/"result.json", result)
        row = dict(id=cell["id"], status=result["status"], accepted=result["audit"]["accepted"],
                   reason=result.get("reason"), elapsed_ns=result["complete_ns"], queries=result.get("queries",0),
                   phases=result["phase_ns"], result=binding(directory/"result.json"))
        rows.append(row);print(json.dumps(row), flush=True)
    put(out/"result.json", dict(status="all_development_cells_attempted", rows=rows))


if __name__ == "__main__":
    main()
