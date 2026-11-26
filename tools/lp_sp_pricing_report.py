"""Audit retained small evidence and publish a candid, compact research receipt."""
import json
from pathlib import Path
import statistics
import subprocess
import sys

from lp_sp_pricing_budget import ROOT, BASE, CPU, GPU, binding
from lp_sp_pricing_verify import verify
from lp_sp_pricing_gpu_admission import validate


def load(path):
    return json.loads(Path(path).read_text())


def resource_summary():
    totals = dict(cpu_ns=0, gpu_ns=0)
    failures, unsettled, retained, cleanup_dispositions = [], [], 0, []
    for reservation in sorted((BASE/"resources").glob("*.reservation.json")):
        data = load(reservation)
        for source in data["sources"]:
            actual = binding(source["retained"])
            if actual["sha256"] != source["sha256"] or actual["bytes"] != source["bytes"]:
                raise ValueError("retained source snapshot changed")
            retained += 1
        settlement = reservation.with_name(reservation.name.replace(".reservation.", ".settlement."))
        if not settlement.exists():
            unsettled.append(reservation.stem.replace(".reservation", ""))
            continue
        receipt = load(settlement)
        if receipt["overrun"]:
            raise ValueError("unresolved resource supervision")
        if not receipt["cleanup_empty"]:
            from lp_sp_pricing_cleanup import verify as verify_cleanup
            verify_cleanup(reservation)
            cleanup_dispositions.append(binding(str(reservation).replace('.reservation.json','.cleanup-disposition.json')))
        for key in totals:
            totals[key] += receipt[key]
        if receipt["status"] != "passed":
            if any(receipt[key] < data[key] for key in totals):
                raise ValueError("failed full charge missing")
            failures.append(dict(identity=reservation.stem.replace(".reservation", ""),
                cpu_ns=receipt["cpu_ns"], gpu_ns=receipt["gpu_ns"], settlement=binding(settlement)))
    return dict(**totals, cpu_cap_seconds=sum(CPU.values()), gpu_cap_seconds=sum(GPU.values()),
                failures=failures, pending_at_snapshot=unsettled, retained_source_files_verified=retained,
                subsequent_cleanup_dispositions=cleanup_dispositions)


def report():
    library = ROOT/"research/lp-sp-pricing/target/release/liblp_sp_pricing.so"
    validate(library)
    groups = {}
    audits = 0
    for identity in ("development-cpu-v1", "development-cpu-v2", "development-gpu-v1"):
        summary = load(BASE/identity/"result.json")
        rows = []
        for row in summary["rows"]:
            model = load(BASE/identity/(row["name"]+".model.json"))
            path = BASE/identity/(row["name"]+".result.json")
            if binding(path) != row["result"]:
                raise ValueError("development endpoint binding")
            result = load(path)
            if result.get("certificate"):
                audit = verify(model, result)
                if not audit["accepted"] or audit != result["audit"]:
                    raise ValueError("independent endpoint audit disagreement")
                audits += 1
            elif result["audit"]["accepted"]:
                raise ValueError("missing endpoint reported accepted")
            market = result.get("phase_ns", {}).get("market")
            rows.append(dict(name=row["name"], status=row["status"], outcome=row["audit"].get("outcome"),
                accepted=row["audit"]["accepted"], reason=row["reason"], queries=row["queries"],
                in_process_seconds=row["complete_ns"]/1e9,
                market_share=market/result["solve_ns"] if market is not None else None,
                result=row["result"]))
        groups[identity] = rows
    batch = load(BASE/"batch-benchmark-tail-v1.json")
    if len(batch["rows"])+len(batch["incomplete"]) != 168 or len(batch["rows"]) != 167:
        raise ValueError("complete batching roster")
    identities = [(r["sparse"], r["repetition"], r["mode"], r["width"]) for r in batch["rows"]+batch["incomplete"]]
    if len(set(identities)) != 168:
        raise ValueError("duplicate batching identity")
    if any(r["accepted_distinct_targets"] != r["distinct_targets"] for r in batch["rows"]):
        raise ValueError("unchecked auxiliary result")
    protocol = load(BASE/"protocol-v1.json")
    result = dict(status="prototype_evidence_audited_full_plan_incomplete", schema=1,
        paper_algorithm_completed=False, reference_implementation_complete=False,
        baseline_comparison_run=False, heldout_original_instances_run=0,
        native_library=binding(library), admission=binding(BASE/"gpu-admission-v2.json"),
        native_quality_combinations=112, sanitizers=["memcheck", "racecheck", "initcheck", "synccheck"],
        independently_rechecked_original_certificates=audits,
        development=groups, batching=dict(completed=167, incomplete=batch["incomplete"],
            comparisons=batch["comparisons"], evidence=binding(BASE/"batch-benchmark-tail-v1.json"),
            scope=batch["timing_scope"], limitations=batch["limitations"]),
        billion_capacity=protocol["billion"], protocol=binding(BASE/"protocol-v1.json"),
        resources=resource_summary(), interpretation="auxiliary_batching_works_cpu_market_bottleneck_no_solver_speedup_established")
    path = ROOT/"docs/benchmarks/lp-sp-pricing-results.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n")
    cpu, gpu = groups["development-cpu-v2"], groups["development-gpu-v1"]
    lines = ["# Pricing LP prototype: measured outcomes", "", "Date: 2026-11-25.", "",
        "**The practical prototype runs; the full paper algorithm and held-out baseline comparison remain unfinished.**",
        "GPU batching substantially improves the fixed-work auxiliary diagnostic, while exact CPU markets dominate the small original-LP attempts.", "",
        "See the [implementation plan](../plans/lp-sp-pricing.md), [research code](../../research/lp-sp-pricing/README.md), and [compact evidence](lp-sp-pricing-results.json).", "",
        "## Original-LP development", "",
        "These six separate development fixtures use 4096 seeded extra experts and ten-second native windows.",
        "CPU-v2 and GPU-v1 each return three independently accepted exact certificates; the other three attempts reach their deadlines.",
        "These are single diagnostic attempts, not the frozen 28-instance confirmation roster.", "",
        "| Fixture | CPU seconds | GPU seconds | Outcome in both lanes |",
        "| --- | ---: | ---: | --- |"]
    for left, right in zip(cpu, gpu):
        if left["name"] != right["name"]:
            raise ValueError("development roster mismatch")
        outcome = right["outcome"] or right["reason"]
        lines.append(f'| {left["name"]} | {left["in_process_seconds"]:.3f} | {right["in_process_seconds"]:.3f} | {outcome} |')
    shares = [r["market_share"] for r in gpu if r["market_share"] is not None]
    lines += ["", f'The median measured market share of GPU-lane solve time is {statistics.median(shares):.1%}.',
        "Times include in-process solving, result encoding, and the independent exact check. They exclude process startup and file publication; they are not complete certified-time comparisons against another solver.",
        "All earlier CPU-v1 outcomes remain in the evidence, including four operation-limit refusals. The later CPU-v2 run uses a larger operation allowance within the same ten-second window and preserves duplicate-expert multiplicities while reducing redundant market work.", "",
        "## Auxiliary batching", "",
        "The diagnostic uses a resident, 32-dimensional diagonal paired space, 64 proposals at 128 iterations each, seven arithmetic modes, both storage formats, four widths, and three fixed order rotations.",
        "There are 167 fully checked cells and one incomplete CSR FP32x8 width-64 cell, which was never retried. Ratios use only jointly checked repetitions.", "",
        "| FP64 storage | Batch 8 | Batch 32 | Batch 64 |",
        "| --- | ---: | ---: | ---: |"]
    for sparse, name in ((False, "Dense"), (True, "CSR")):
        ratios = [next(r["sequential_over_batched_native_ratio"] for r in batch["comparisons"]
                       if r["sparse"] == sparse and r["mode"] == "fp64" and r["width"] == width) for width in (8, 32, 64)]
        lines.append("| "+name+" | "+" | ".join(f"{ratio:.2f}x" for ratio in ratios)+" |")
    lines += ["", "The ratios measure sequential native proposal time divided by batched native proposal time, including state allocation and endpoint transfers. Shared-matrix upload and exact checking are reported separately and excluded from these ratios.",
        "This small structured workload is dominated by launch and allocation overhead. The interrupted tail uses a fresh GPU context. These measurements establish neither a complete-LP speedup nor tensor-core performance; all kernels use CUDA cores and FP4 is simulated with unpacked components.", "",
        "## Admission, limits, and retained failures", "",
        "The native candidate passes 112 quality combinations and all four complete sanitizer smoke processes, with no reported errors or hazards. The independent checker rechecks every returned development endpoint. The final CPU regression and documentation results are recorded in the reporting reservation.",
        "Two failed reservations retain 4800 CPU / 1200 GPU seconds: an interrupted sanitizer coordinator and the batching exact-checker operation cap. Both have empty cleanup and no overrun. The interrupted scientific cell remains incomplete.",
        "Both proposed original billion-nonzero LPs fail capacity admission before generation. The mixed optimality reduction requires about 804 GB and 800 TB for a dense FP64 basis and transpose alone, beyond the 80 GiB device limit. Original sparse input does not ensure sparse subspace bases.",
        "The 28-instance held-out comparison, COPT/image-v11 adapters, full grouped-market/ellipsoid reference integration, adaptive expert-pool expansion, tensor-core products, and concurrent independent outer searches remain pending. No old scientific identity was rerun, and no public solver default changed.", ""]
    (ROOT/"docs/benchmarks/lp-sp-pricing.md").write_text("\n".join(lines))
    print(json.dumps(dict(status=result["status"], checked_original_certificates=audits,
                         completed_batching_cells=len(batch["rows"]))))


def main():
    subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests/integration", "-p", "test_lp_sp_pricing.py"], cwd=ROOT, check=True)
    report()
    subprocess.run([sys.executable, "-B", "tools/build_docs.py"], cwd=ROOT, check=True)
    subprocess.run(["git", "diff", "--check"], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
