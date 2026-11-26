"""One bounded pricing attempt, with explicit proof/implementation provenance."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"research/lp-sp-pricing/python"))
from sp_pricing.exact import Work, Limit, encode
from sp_pricing.solver import PricingSolver
from lp_sp_pricing_verify import verify


def attempt(model, *, seconds=30, operations=2_000_000, bits=16384,
            mode="practical", extra_experts=4096, queries=1024, batch=32, seed=20261125, gpu=None,
            market_backend="auto", compact_trace=False):
    started = time.perf_counter_ns()
    work = Work(max_operations=operations, max_bits=bits, seconds=seconds)
    solver = PricingSolver(work, extra_experts, queries, batch, seed, gpu, market_backend)
    if compact_trace:
        class CompactEvents(list):
            def append(self, event):
                keys=("query","kind","epoch","extra_experts","preceding_queries","wealth_reset",
                      "auxiliary_calls","recovered_labels","expert_epoch","gpu_work","gpu")
                super().append({key:event[key] for key in keys if key in event})
        solver.events=CompactEvents()
    try:
        result = solver.solve(model, mode)
    except Limit as error:
        result = dict(status="resource_limit", reason=str(error), certificate=None,
                      mode=mode, paper_algorithm_completed=False, strongly_polynomial_claim=False,
                      queries=solver.queries, exact_recovery_lps=solver.recovery_lps,
                      events=solver.events, gpu_work=gpu is not None)
    except (ArithmeticError, ValueError, OverflowError) as error:
        result = dict(status="implementation_error", reason=repr(error), certificate=None,
                      mode=mode, paper_algorithm_completed=False, strongly_polynomial_claim=False,
                      queries=solver.queries, events=solver.events, gpu_work=gpu is not None)
    result = encode(result)
    result["phase_ns"] = solver.phase_ns
    result["work"] = dict(operations=work.operations, peak_bits=work.peak_bits)
    result["solve_ns"] = time.perf_counter_ns()-started
    audit_start = time.perf_counter_ns()
    result["audit"] = verify(model, result) if result.get("certificate") else dict(accepted=False, reason="no_endpoint")
    result["independent_check_ns"] = time.perf_counter_ns()-audit_start
    result["complete_ns"] = time.perf_counter_ns()-started
    result["timing_scope"] = "in_process_solve_encode_and_independent_check_excludes_startup_and_file_publication"
    result["limits"] = dict(seconds=seconds, operations=operations, bits=bits, queries=queries)
    result["configuration"] = dict(extra_experts=extra_experts, batch=batch, seed=seed, gpu=gpu, market_backend=market_backend)
    result["search_complexity_guarantee"] = False
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--mode", choices=["practical", "paper_reference", "certified_acceleration"], default="practical")
    parser.add_argument("--seconds", type=float, default=30)
    parser.add_argument("--operations", type=int, default=2_000_000)
    parser.add_argument("--bits", type=int, default=16384)
    parser.add_argument("--extra-experts", type=int, default=4096)
    parser.add_argument("--queries", type=int, default=1024)
    parser.add_argument("--batch", type=int, choices=[1, 8, 32, 64], default=32)
    parser.add_argument("--gpu-library", type=Path)
    parser.add_argument("--precision", choices=["fp64", "fp32x2", "fp32x4", "fp32x8", "fp4x1", "fp4x2", "fp4x4"], default="fp32x2")
    parser.add_argument("--sparse", action="store_true")
    parser.add_argument("--market", choices=["auto", "flow", "cuts"], default="auto")
    args = parser.parse_args()
    gpu = None if args.gpu_library is None else dict(library=str(args.gpu_library.resolve()),
                                                   mode=args.precision, sparse=args.sparse)
    result = attempt(json.loads(args.model.read_text()), seconds=args.seconds, operations=args.operations,
        bits=args.bits, mode=args.mode, extra_experts=args.extra_experts, queries=args.queries, batch=args.batch,
        gpu=gpu, market_backend=args.market)
    result["model_sha256"] = hashlib.sha256(args.model.read_bytes()).hexdigest()
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(json.dumps({k: result[k] for k in ("status", "audit", "complete_ns")}))
    return int(result["status"] == "implementation_error")


if __name__ == "__main__":
    raise SystemExit(main())
