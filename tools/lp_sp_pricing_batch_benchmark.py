"""Fixed-work auxiliary batching benchmark; never a complete LP speedup claim."""
from fractions import Fraction as Q
import json
import os
from pathlib import Path
import statistics
import sys
import time

from lp_sp_pricing_budget import ROOT, put
from lp_sp_pricing_gpu_admission import validate
sys.path.insert(0, str(ROOT/"research/lp-sp-pricing/python"))
from sp_pricing.exact import Work
from sp_pricing.geometry import paired_space, LabelOracle
from sp_pricing.gpu import GpuBatch, MODES, accept_proposal


def main():
    output = Path(sys.argv[1])
    library = ROOT/"research/lp-sp-pricing/target/release/liblp_sp_pricing.so"
    validate(library)
    work = Work(max_operations=100_000_000, seconds=300)
    n = 32
    space = [[Q(int(i == j)) for j in range(n)] for i in range(n//2)]
    oracle = LabelOracle(paired_space(space, work), Q(1), Q(1, 1024*n), work)
    expected = [1]*(n//2)+[-1]*(n//2)
    configurations = [(mode, width) for mode in MODES for width in (1, 8, 32, 64)]
    rows, attempted, incomplete = [], set(), []
    resume_from = Path(sys.argv[2]) if len(sys.argv) == 3 else None
    def key(row):
        return row["sparse"], row["repetition"], row["mode"], row["width"]
    if resume_from is not None:
        completed = set()
        for line in resume_from.read_text().splitlines():
            event = json.loads(line)
            identity = key(event)
            if identity[0] not in (False, True) or identity[1] not in range(3) or identity[2:] not in configurations:
                raise ValueError("unknown previous benchmark cell")
            if event["event"] == "started":
                if identity in attempted:
                    raise ValueError("repeated benchmark start")
                attempted.add(identity)
            elif event["event"] == "completed":
                if identity not in attempted or identity in completed:
                    raise ValueError("invalid benchmark completion")
                completed.add(identity)
                rows.append({k: v for k, v in event.items() if k != "event"})
            else:
                raise ValueError("unknown benchmark event")
        incomplete = [dict(sparse=k[0], repetition=k[1], mode=k[2], width=k[3],
            status="missing_complete_exact_check", never_retried=True) for k in sorted(attempted-completed)]
    journal = Path(str(output)+".journal.jsonl").open("x")
    def record(value):
        journal.write(json.dumps(value, sort_keys=True)+"\n")
        journal.flush()
        os.fsync(journal.fileno())
    for sparse in (False, True):
        with GpuBatch(library, oracle.b, sparse) as engine:
            for repetition in range(3):
                # Fixed rotated order, no configuration selected after seeing data.
                rotated = configurations[repetition:]+configurations[:repetition]
                for mode, width in rotated:
                    if (sparse, repetition, mode, width) in attempted:
                        continue
                    record(dict(event="started", sparse=sparse, repetition=repetition, mode=mode, width=width))
                    begin = time.perf_counter_ns()
                    native_ns, device_ms, endpoints = 0, 0.0, {}
                    for start in range(0, 64, width):
                        targets = [(start+i)%n for i in range(width)]
                        proposal = engine.propose(targets, oracle.h, oracle.epsilon, 128, mode)
                        native_ns += proposal["elapsed_ns"]
                        device_ms += proposal["device_iteration_ms"]
                        for i, target in enumerate(targets):
                            endpoints.setdefault(target, (proposal["x"][i], proposal["dual"][i]))
                    check_begin = time.perf_counter_ns()
                    accepted = 0
                    for target, (x, u) in endpoints.items():
                        proof = accept_proposal(oracle, target, x, u)
                        for index, sign in proof.get("established", {}).items():
                            if sign != expected[index]:
                                raise ArithmeticError("batch benchmark label mismatch")
                        accepted += proof["accepted"]
                    rows.append(dict(sparse=sparse, repetition=repetition, mode=mode, width=width,
                        proposals=64, distinct_targets=n, steps_per_proposal=128,
                        accepted_distinct_targets=accepted, native_ns=native_ns,
                        device_iteration_ms=device_ms, exact_check_ns=time.perf_counter_ns()-check_begin,
                        in_process_ns=time.perf_counter_ns()-begin,
                        matrix_preparation_ns=engine.preparation_ns))
                    record(dict(event="completed", **rows[-1]))
                    work.tick()
    comparisons = []
    for sparse in (False, True):
        for mode in MODES:
            for width in (8, 32, 64):
                ratios = []
                for repetition in range(3):
                    def eligible(w):
                        return [r for r in rows if r["sparse"] == sparse and r["mode"] == mode
                                and r["width"] == w and r["repetition"] == repetition
                                and r["accepted_distinct_targets"] == r["distinct_targets"]]
                    control, candidate = eligible(1), eligible(width)
                    if control and candidate:
                        ratios.append(control[0]["native_ns"]/candidate[0]["native_ns"])
                comparisons.append(dict(sparse=sparse, mode=mode, width=width,
                    jointly_checked_repetitions=len(ratios),
                    sequential_over_batched_native_ratio=statistics.median(ratios) if ratios else None))
    put(output, dict(status="measured_with_incomplete_cell" if incomplete else "measured",
        rows=rows, incomplete=incomplete, previous_journal=str(resume_from) if resume_from else None,
        comparisons=comparisons,
        native_sha256=engine.digest, matrix="32-dimensional_diagonal_paired_space",
        timing_scope="64_fixed_work_auxiliary_proposals_with_resident_matrix",
        includes="state_allocation_initialization_kernel_launches_and_endpoint_transfers",
        excludes="shared_matrix_upload_exact_checks_and_original_LP_pipeline",
        complete_lp_speedup_claim=False, tensor_cores=False,
        limitations=["Small structured problem; launch and allocation overhead dominate.",
                     "One device, warm context, three fixed rotations; not held-out optimization.",
                     "A resumed tail has a fresh GPU context; interrupted cells remain excluded, not retried."] ))
    print(json.dumps(dict(status="measured", cells=len(rows), comparisons=len(comparisons))))
    journal.close()


if __name__ == "__main__":
    main()
