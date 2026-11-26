"""Prospective study roster, bounded development, and original-model capacity gates."""
import argparse
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"research/lp-sp-pricing/python"))
from sp_pricing.exact import encode
from sp_pricing.calibration import paper_bounds
from lp_sp_pricing_run import attempt
from lp_sp_pricing_budget import put, binding

FAMILIES = ("dense", "irregular", "wide", "tall", "coupled", "ill_scaled", "degenerate")


def roster():
    cells = []
    for family in FAMILIES:
        for size, n in (("small", 16), ("medium", 64)):
            m = n//2 if family == "wide" else 8*n if family == "tall" else 2*n
            for seed in (38101, 38102):
                cells.append(dict(id=f"{family}-{size}-{seed}", family=family, size=size,
                    rows=m, columns=n, seed=seed, native_seconds=10 if size == "small" else 30,
                    outer_seconds=30 if size == "small" else 60, repetitions=3,
                    lanes=["practical", "retained_image_v11", "copt_scale_off"]))
    return cells


def generated(cell):
    """Fresh planted exact optima; construction witnesses remain separate."""
    rng = random.Random(cell["seed"])
    n, m, family = cell["columns"], cell["rows"], cell["family"]
    x = [Q(rng.randrange(-3, 4), 4) for _ in range(n)]
    a, b, y = [], [], []
    for i in range(m):
        row = [Q(0)]*n
        degree = n if family == "dense" else min(n, 3+i%6)
        indices = set((i%n, (i+1)%n))
        if family == "coupled":
            indices.update((i//4*4+j)%n for j in range(4))
        while len(indices) < degree:
            indices.add(rng.randrange(n))
        for j in sorted(indices):
            v = Q(rng.choice([-4, -3, -2, -1, 1, 2, 3, 4]))
            if family == "ill_scaled":
                exponent = (i%17-8)+(j%17-8)
                v *= Q(2)**exponent
            row[j] = v
        if family == "degenerate" and i%3 == 2:
            row = a[-1][:]
        tight = i%3 != 1 or family == "degenerate"
        dual = Q(rng.randrange(1, 4)) if tight else Q(0)
        a.append(row); y.append(dual)
        b.append(sum((v*t for v, t in zip(row, x)), Q(0))+(0 if tight else 1))
    c = [sum((a[i][j]*y[i] for i in range(m)), Q(0)) for j in range(n)]
    return encode(dict(A=a, b=b, c=c, sense="max")), encode(dict(status="optimal", x=x, y=y))


def capacity(rows, columns, nonzeros):
    n = rows+1
    optimum_n = 3*rows+2*columns+4
    # Original sparsity is not inherited by null-space bases and calibrated B.
    first_basis = 16*n*n
    optimum_basis = 16*optimum_n*optimum_n
    geometry_entries = (rows+1)*(columns+1)
    reasons = []
    if geometry_entries > 100_000:
        reasons.append("explicit_rational_geometry_entry_limit")
    if 2*max(n, optimum_n)**2 > 1_000_000:
        reasons.append("paired_basis_fill_limit")
    if 2*max(first_basis, optimum_basis) > 80 << 30:
        reasons.append("basis_and_transpose_exceed_device_limit")
    return dict(rows=rows, columns=columns, original_nonzeros=nonzeros,
        original_csr_bytes=12*nonzeros+8*(rows+1),
        first_basis_fp64_bytes=first_basis, optimality_basis_fp64_bytes=optimum_basis,
        basis_and_transpose_fp64_bytes=2*max(first_basis, optimum_basis),
        rational_geometry_entries=geometry_entries, host_rational_bytes_forecast=None,
        status="unsupported" if reasons else "capacity_unresolved",
        reasons=reasons, original_generated=False, original_solve_attempted=False,
        auxiliary_is_not_original_model=True)


def freeze(output):
    original_billion = [dict(id="fresh-dense-billion", family="dense", **capacity(32000, 31250, 1_000_000_000)),
                        dict(id="fresh-connected-sparse-billion", family="irregular", **capacity(1_000_000, 1_000_000, 1_000_000_000))]
    document = dict(schema=1, study="lp-sp-pricing-v1", roster=roster(), billion=original_billion,
        precision_modes=["fp64", "fp32x2", "fp32x4", "fp32x8", "fp4x1", "fp4x2", "fp4x4"],
        widths=[1, 8, 32, 64], source=binding(__file__), seed_policy="development separate from heldout",
        original_model_maximize_free=True, certificate_tiers=["exact_rational_original", "historical_1e-9_separate"],
        idle_seconds=30, heldout_execution="gated_on_complete_development_admission_and_baseline_adapters",
        no_paired_speedup_without_joint_timely_certificate=True,
        excluded_runtime_not_a_success=True, no_automatic_resource_cap_transfers=True)
    put(output, document)
    return document


def development(output, gpu_library=None):
    if gpu_library is not None:
        from lp_sp_pricing_gpu_admission import validate
        validate(gpu_library)
    fixtures = [
        ("infeasible", dict(A=[[0]], b=[-1], c=[1])),
        ("unbounded", dict(A=[], b=[], c=[1])),
        ("zero_objective", dict(A=[], b=[], c=[0])),
        ("bounded", dict(A=[[1], [-1]], b=[2, 0], c=[1])),
        ("degenerate", dict(A=[[1], [1], [-1]], b=[2, 2, 0], c=[1])),
        ("coupled", dict(A=[[1, 1], [-1, 0], [0, -1]], b=[2, 0, 0], c=[1, 1])),
    ]
    output.mkdir(exist_ok=False)
    rows = []
    # This is development, with the planned initial expert count unchanged.
    for name, model in fixtures:
        gpu = None if gpu_library is None else dict(library=str(gpu_library.resolve()), mode="fp32x2", sparse=False)
        result = attempt(model, seconds=10, operations=100_000_000, extra_experts=4096, gpu=gpu)
        put(output/(name+".model.json"), model)
        put(output/(name+".result.json"), result)
        row = dict(name=name, status=result["status"], audit=result["audit"], complete_ns=result["complete_ns"],
                   queries=result.get("queries", 0), reason=result.get("reason"),
                   result=binding(output/(name+".result.json")))
        rows.append(row)
        print(json.dumps(row), flush=True)
    put(output/"result.json", dict(status="development_attempts_recorded", rows=rows,
        all_certified=all(row["audit"]["accepted"] for row in rows), original_lp_attempts=len(rows),
        historical_baseline_comparison=False, gpu=gpu_library is not None))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["freeze", "development"])
    parser.add_argument("output", type=Path)
    parser.add_argument("--gpu-library", type=Path)
    args = parser.parse_args()
    if args.action == "freeze":
        document = freeze(args.output)
        print(json.dumps(dict(roster=len(document["roster"]), billion=document["billion"])))
    else:
        development(args.output, args.gpu_library)


if __name__ == "__main__":
    main()
