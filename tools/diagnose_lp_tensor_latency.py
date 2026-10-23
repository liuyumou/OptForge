"""CPU-only, read-only analysis of the exhausted ADR-0043 study.

This reads already verified records; it does not rerun an LP verifier or a device
job. Hash bindings are checked and all new output must be created separately.
"""
import argparse
from collections import Counter, defaultdict
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "artifacts/gpup-tensor-residual-v1/study-v1"
LEDGER_SHA = "e1766490f8de2affa14f4f950afed18be7f69531c3c28eedfd74539fcc0d9db5"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def exclusive_subtree(phases, prefix):
    """Only cost/* leaves are exclusive; envelope phases overlap them."""
    if not prefix.startswith("cost/"):
        raise ValueError("only exclusive cost paths can be aggregated")
    return sum(value for key, value in phases.items()
               if key == prefix or key.startswith(prefix + "/"))


def control_path(kind, endpoint):
    if "outcome" in endpoint:
        if endpoint["request"]["layout"] == "original_tuned":
            if kind != "profile":
                raise ValueError("research wrapper cannot be a tuned timing control")
            return "research_wrapper_original_tuned"
        return "tensor_residual_research"
    if endpoint.get("format") != "lp-compact-v1":
        raise ValueError("unexpected tuned endpoint format")
    if endpoint["endpoint"]["record"]["backend"] != "cuda-lp-tuned":
        raise ValueError("unexpected control backend")
    return "unchanged_cuda_lp_tuned"


def analyze():
    delivery_path = ROOT / "docs/benchmarks/data/tensor-residual/acceptance.json"
    delivery = read(delivery_path)
    report_path = ROOT / delivery["report"]["path"]
    if digest(report_path) != delivery["report"]["sha256"]:
        raise ValueError("retained report binding changed")
    report = read(report_path)
    ledger_path = STUDY / "ledger.jsonl"
    if digest(ledger_path) != LEDGER_SHA:
        raise ValueError("ledger changed; proposal needs a new resource calculation")
    events = [json.loads(line) for line in ledger_path.read_text().splitlines()]
    if len(events) != 17362 or any(e["sequence"] != i for i, e in enumerate(events)):
        raise ValueError("ledger sequence changed")
    pending = set()
    phases, task = Counter(), Counter()
    for e in events:
        if e["kind"] == "reserve":
            pending.add(e["reservation_id"])
        else:
            pending.remove(e["reservation_id"])
        if e["resource"] == "gpu":
            phases[e["phase"]] += e["charged_ns"]
            if e["trial_id"].startswith(("gpup-tensor-v1-", "gpup-tensor-residual-v1-")):
                task[e["phase"]] += e["charged_ns"]
    if pending:
        raise ValueError("unsettled ledger")
    rows, inputs = [], []
    for original in report["rows"]:
        if original["kind"] not in ("timing", "profile"):
            continue
        key = original["id"]
        trial_path = STUDY / (key + ".trial.json")
        trial = read(trial_path)
        objects = {}
        for name in ("endpoint", "worker"):
            ref = trial["artifacts"][name]
            path = STUDY / ref["path"]
            if path.parent != STUDY or digest(path) != ref["sha256"]:
                raise ValueError("retained artifact hash/path differs")
            inputs.append({"path": str(path.relative_to(ROOT)), "sha256": ref["sha256"]})
            objects[name] = read(path)
        inputs.append({"path": str(trial_path.relative_to(ROOT)), "sha256": digest(trial_path)})
        e, w = objects["endpoint"], objects["worker"]
        if not original["verified"] or trial["status"] != "completed" or w["reason"] != "completed" or w["returncode"]:
            raise ValueError("incomplete/unverified record cannot support attribution")
        row = {k: original[k] for k in ("id", "model", "configuration", "kind", "repetition")}
        row.update(path=control_path(row["kind"], e), wall_ns=w["elapsed_ns"])
        if "outcome" in e:
            o, p = e["outcome"], e["phases_ns"]
            c, counts = o["core"], o["counts"]
            row.update({k: c[k] for k in ("iterations", "physical", "norm", "step")})
            row.update({k: e[k] for k in ("launches", "upload_bytes", "readback_bytes")})
            row.update(work=c["work"], counts=counts,
                       first_certified_iteration=o["first_certified_iteration"],
                       phases_ns=p)
            if row["kind"] == "profile":
                if c["iterations"] != 2000 or c["stop"] != "work_horizon" or c["failure"] is not None:
                    raise ValueError("incomplete profile horizon")
                row["exclusive_groups_ns"] = {
                    name: exclusive_subtree(p, prefix) for name, prefix in {
                        "pack_metadata": "cost/resident_pack_metadata_norm",
                        "host_audit": "cost/resident_solve_loop/resident_host_audit",
                        "device_window": "cost/resident_solve_loop/resident_device_window",
                        "controller_assessment": "cost/resident_solve_loop/controller_assessment",
                    }.items()}
                row["cost_sum_ns"] = sum(v for k, v in p.items() if k.startswith("cost/"))
                if row["cost_sum_ns"] > w["elapsed_ns"]:
                    raise ValueError("exclusive costs exceed worker envelope")
        else:
            endpoint = e["endpoint"]
            row.update(iterations=endpoint["control"]["logical_iterations"],
                       physical=endpoint["control"]["physical_iterations"],
                       launches=endpoint["execution"]["kernel_launches"],
                       upload_bytes=endpoint["execution"]["upload_bytes"],
                       readback_bytes=endpoint["execution"]["readback_bytes"],
                       assessments=endpoint["control"]["assessments"])
        rows.append(row)
    groups = defaultdict(list)
    for row in rows:
        if row["kind"] == "timing":
            groups[(row["model"], row["configuration"])].append(row)
    medians = []
    for (model, configuration), group in sorted(groups.items()):
        if sorted(r["repetition"] for r in group) != list(range(5)):
            raise ValueError("five distinct repetitions required")
        medians.append(dict(model=model, configuration=configuration,
                            wall_ns=statistics.median(r["wall_ns"] for r in group)))
    cpu_before = Decimal(str(delivery["combined_gpup8_cpu_upper_seconds"]))
    caps = dict(screening=1600, ablations=550, repeatability=850)
    return dict(identity="gpup8-latency-diagnosis-v1", gpu_seconds=0,
                evidence_scope="hash-checked retained records; no fresh numerical verification",
                input_receipts=inputs, delivery_sha256=digest(delivery_path),
                retained_report_sha256=digest(report_path), ledger_sha256=LEDGER_SHA,
                ledger_events=len(events), campaign_phase_charged_ns=dict(phases),
                gpup8_phase_charged_ns=dict(task),
                gpup8_phase_remaining_ns={k: v * 10**9 - task[k] for k, v in caps.items()},
                gpup8_remaining_gpu_ns=3000 * 10**9 - sum(task.values()),
                cpu_before_seconds=str(cpu_before), diagnosis_cpu_charge_seconds=400,
                cpu_remaining_after_diagnosis_seconds=str(Decimal(21600) - cpu_before - 400),
                medians=medians, rows=rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    allowed = ROOT / "docs/benchmarks/data/tensor-latency"
    if args.output.resolve().parent != allowed.resolve() or args.output.exists():
        raise ValueError("use a new separate diagnosis receipt")
    result = analyze()
    allowed.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print({k: result[k] for k in ("identity", "gpu_seconds", "ledger_events", "gpup8_phase_remaining_ns", "cpu_remaining_after_diagnosis_seconds")})
