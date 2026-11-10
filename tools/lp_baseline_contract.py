"""SPEC-0022 CPU-only contracts. This module never imports or executes a solver."""

import argparse
import hashlib
import json
import math
from pathlib import Path

from validate_artifacts import read_json_bytes, validator

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 128 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(value):
    require(type(value) in (int, float), "binary64 number required")
    try:
        converted = float(value)
    except OverflowError as error:
        raise ValueError("number outside binary64 range") from error
    require(math.isfinite(converted), "nonfinite number")
    require(type(value) is not int or converted == value, "inexact binary64 integer")
    return converted


def finite_tree(value):
    if isinstance(value, dict):
        for child in value.values():
            finite_tree(child)
    elif isinstance(value, list):
        for child in value:
            finite_tree(child)
    elif type(value) is float:
        number(value)


def schema(kind, document):
    validator(f"lp-baseline-{kind}-v1.schema.json").validate(document)
    finite_tree(document)


def read(path):
    path = Path(path)
    require(path.stat().st_size <= MAX_BYTES, "input exceeds 128 MiB")
    data = path.read_bytes()
    require(len(data) <= MAX_BYTES, "input exceeds 128 MiB")
    return data, read_json_bytes(data)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def checked_reference(reference, root=ROOT):
    root = Path(root).resolve()
    relative = Path(reference["path"])
    require(not relative.is_absolute(), "absolute artifact path")
    path = (root / relative).resolve()
    require(path.is_relative_to(root), "artifact path escapes root")
    raw, _ = read(path) if path.suffix == ".json" else (path.read_bytes(), None)
    require(sha256(raw) == reference["sha256"], "artifact hash mismatch")
    return raw


def validate_model(model):
    schema("model", model)
    n, m = len(model["variable_ids"]), len(model["row_ids"])
    for key in ("variable_ids", "row_ids"):
        require(all(type(i) is int for i in model[key]), "integer IDs required")
        require(model[key] == sorted(model[key]), "IDs must be sorted")
    for key, size in [("objective", n), ("variable_lower", n), ("variable_upper", n),
                      ("row_lower", m), ("row_upper", m)]:
        require(len(model[key]) == size, "array dimension: " + key)
        for value in model[key]:
            if value is not None:
                number(value)
    number(model["offset"])
    for side in ("variable", "row"):
        for lower, upper in zip(model[side + "_lower"], model[side + "_upper"]):
            require(lower is None or upper is None or lower <= upper, "reversed bounds")
    pointers, indices, values = (model[k] for k in ("column_pointers", "row_indices", "values"))
    require(all(type(i) is int for i in pointers + indices), "integer CSC indices required")
    require(len(pointers) == n + 1 and pointers[0] == 0, "CSC pointers shape/start")
    require(pointers[-1] == len(values) == len(indices), "CSC terminal/nnz")
    require(all(a <= b for a, b in zip(pointers, pointers[1:])), "CSC pointers decrease")
    require(all(i < m for i in indices), "CSC row out of range")
    for start, end in zip(pointers, pointers[1:]):
        column = indices[start:end]
        require(all(a < b for a, b in zip(column, column[1:])), "CSC duplicate/unsorted rows")
    for value in values:
        number(value)
    return model


def canonicalize(raw):
    """Lossless ordering/conversion only; no scaling, presolve or vendor import."""
    doc = read_json_bytes(raw)
    require(isinstance(doc, dict), "model object required")
    require(set(doc) == {"schema_version", "model_id", "variables", "constraints", "objective"},
            "original model fields")
    require(type(doc["schema_version"]) is int and doc["schema_version"] == 1, "model version")
    require(isinstance(doc["variables"], list) and isinstance(doc["constraints"], list), "model arrays")
    for items, fields in [(doc["variables"], {"id", "domain", "lower", "upper"}),
                          (doc["constraints"], {"id", "lower", "upper", "terms"})]:
        require(all(isinstance(v, dict) and set(v) == fields for v in items), "original item fields")
        ids = [v["id"] for v in items]
        require(all(type(i) is int and 0 <= i <= 0xffffffff for i in ids), "original ID range")
        require(len(set(ids)) == len(ids), "duplicate original ID")
    variables = sorted(doc["variables"], key=lambda v: v["id"])
    rows = sorted(doc["constraints"], key=lambda v: v["id"])
    require(all(v["domain"] == "continuous" for v in variables), "continuous LP required")
    index = {v["id"]: j for j, v in enumerate(variables)}

    def bound(value, lower):
        require(isinstance(value, dict) and "kind" in value, "bound object")
        if value["kind"] == "finite":
            require(set(value) == {"kind", "value"}, "finite bound fields")
            return number(value["value"])
        require(set(value) == {"kind"} and value["kind"] ==
                ("negative_infinity" if lower else "positive_infinity"), "bound orientation")
        return None

    def terms(items):
        require(isinstance(items, list), "terms array")
        seen = set()
        for term in items:
            require(isinstance(term, dict) and set(term) == {"variable_id", "coefficient"}, "term fields")
            key = term["variable_id"]
            require(type(key) is int and key in index and key not in seen, "unknown/duplicate term")
            seen.add(key)
            yield index[key], number(term["coefficient"])

    objective = doc["objective"]
    require(isinstance(objective, dict) and set(objective) == {"sense", "offset", "terms"}, "objective fields")
    costs = [0.0] * len(variables)
    for j, value in terms(objective["terms"]):
        costs[j] = value
    columns = [[] for _ in variables]
    for i, row in enumerate(rows):
        for j, value in terms(row["terms"]):
            columns[j].append((i, value))
    pointers, indices, values = [0], [], []
    for column in columns:
        for i, value in column:
            indices.append(i)
            values.append(value)
        pointers.append(len(indices))
    result = dict(schema_version=1, kind="lp-baseline-model", model_id=doc["model_id"],
                  original_sha256=sha256(raw), variable_ids=[v["id"] for v in variables],
                  row_ids=[r["id"] for r in rows], sense=objective["sense"],
                  offset=number(objective["offset"]), objective=costs,
                  column_pointers=pointers, row_indices=indices, values=values)
    for side, items in [("variable", variables), ("row", rows)]:
        for direction in ("lower", "upper"):
            result[side + "_" + direction] = [bound(v[direction], direction == "lower") for v in items]
    return validate_model(result)


def csr(model):
    """Return CSR arrays without coefficient arithmetic, including signed zeros."""
    validate_model(model)
    rows = [[] for _ in model["row_ids"]]
    for j, (start, end) in enumerate(zip(model["column_pointers"], model["column_pointers"][1:])):
        for at in range(start, end):
            rows[model["row_indices"][at]].append((j, model["values"][at]))
    pointers, indices, values = [0], [], []
    for row in rows:
        for j, value in row:
            indices.append(j)
            values.append(value)
        pointers.append(len(indices))
    return pointers, indices, values


def validate_endpoint(endpoint, model, model_hash):
    """Structural checks only. Accepted checker receipts still need independent verification."""
    schema("endpoint", endpoint)
    validate_model(model)
    require(endpoint["model_sha256"] == model_hash, "canonical model hash mismatch")
    require(endpoint["original_sha256"] == model["original_sha256"], "original hash mismatch")
    for key in ("variable_ids", "row_ids"):
        require(endpoint[key] == model[key], "endpoint ID mapping mismatch")
    for key, size in [("primal", len(model["variable_ids"])), ("dual", len(model["row_ids"])),
                      ("native_reduced_costs", len(model["variable_ids"]))]:
        values = endpoint[key]
        if values is not None:
            require(len(values) == size, "endpoint vector dimension")
            for value in values:
                number(value)
    if endpoint["executed_device"] == "gpu":
        require(endpoint["device_uuid"] is not None and endpoint["gpu_evidence"] is not None,
                "GPU execution requires evidence")
    if endpoint["executed_device"] == "not_run":
        require(endpoint["native_status"] == "not_run" and endpoint["primal"] is None and
                endpoint["dual"] is None, "unexecuted endpoint has solver output")
    checker = endpoint["checker"]
    for key in ("elapsed_ns", "native_solve_ns", "certificate_ns"):
        require(endpoint[key] is None or type(endpoint[key]) is int, "integer nanoseconds required")
    require((checker["state"] in ("accepted", "rejected")) == (checker["receipt"] is not None),
            "checker receipt/state mismatch")
    if checker["state"] == "accepted":
        require(endpoint["transport"] == "completed" and endpoint["primal"] is not None and
                endpoint["dual"] is not None and endpoint["elapsed_ns"] is not None and
                endpoint["certificate_ns"] is not None, "accepted endpoint is incomplete")
        require(endpoint["native_status"] in ("optimal", "limit", "unknown"), "contradictory native status")
    if endpoint["elapsed_ns"] is not None:
        for key in ("native_solve_ns", "certificate_ns"):
            require(endpoint[key] is None or endpoint[key] <= endpoint["elapsed_ns"], "phase exceeds envelope")
    if endpoint["transport"] == "unavailable":
        require(endpoint["executed_device"] == "not_run" and endpoint["elapsed_ns"] is None,
                "unavailable lane cannot have a timing")
    if any(endpoint[k] is None for k in ("primal", "dual", "native_solve_ns", "certificate_ns")):
        require(bool(endpoint["limitations"]), "missing observations require limitations")
    return endpoint


def normalize_original_sense_dual(values, sense):
    """Use only after admission proves that the vendor returns original-sense duals."""
    require(sense in ("minimize", "maximize"), "objective sense")
    sign = 1 if sense == "minimize" else -1
    return [sign * number(value) for value in values]


def screening_jobs(proposal):
    """Stable SHA-256 ordering, independent of Python PRNG/version and input array order."""
    for instance in sorted(proposal["instances"], key=lambda i: i["id"]):
        for repetition in range(proposal["repetitions"]):
            def key(config):
                return sha256(f"{proposal['order_seed']}\0{instance['id']}\0{repetition}\0{config['id']}".encode())
            for order, config in enumerate(sorted(proposal["configurations"], key=lambda c: (key(c), c["id"]))):
                yield dict(instance_id=instance["id"], configuration_id=config["id"],
                           repetition=repetition, order=order, gpu=config["gpu"])


def validate_proposal(proposal, verify_artifacts=False, root=ROOT):
    schema("proposal", proposal)
    configs, instances, phases = (proposal[k] for k in ("configurations", "instances", "phases"))
    for items in (configs, instances, phases):
        require(len({x["id"] for x in items}) == len(items), "duplicate proposal identity")
    require(len(configs) == 10 and len(instances) == 8, "frozen grid size")
    expected_ids = {"project-tuned-fp64", "project-precision-fp64", "highs-cpu",
                    "cuopt-pdlp-double", "cuopt-pdlp-mixed", "cuopt-pdlp-single",
                    "copt-cpu-pdlp", "copt-gpu-pdlp", "cuopt-concurrent", "copt-cpu-default"}
    require({c["id"] for c in configs} == expected_ids, "frozen lane identities")
    require({x["solver"] for x in configs} == {"project", "highs", "cuopt", "copt"}, "solver grid")
    require(sum(x["gpu"] for x in configs) == 7, "GPU lane count")
    require(len(proposal["smoke_instance_ids"]) == 2 and len(set(proposal["smoke_instance_ids"])) == 2,
            "two distinct smoke instances required")
    require(set(proposal["smoke_instance_ids"]) <= {i["id"] for i in instances}, "unknown smoke instance")
    for config in configs:
        params = config["parameters"]
        expected_solver = config["id"].split("-")[0]
        require(config["solver"] == expected_solver, "lane solver identity")
        require(config["version"] == {"project": "source_snapshot", "highs": "1.11.0",
                                      "cuopt": "26.10.0", "copt": "8.0.6"}[expected_solver], "solver version")
        expected_gpu = expected_solver in ("project", "cuopt") or config["id"] == "copt-gpu-pdlp"
        require(config["gpu"] == expected_gpu, "lane device identity")
        if config["solver"] == "cuopt":
            require(set(params) == {"method", "pdlp_precision", "pdlp_solver_mode", "presolve",
                    "dual_postsolve", "crossover", "num_cpu_threads", "time_limit", "iteration_limit", "random_seed"}
                    | {f"{s}_{k}_tolerance" for s in ("absolute", "relative") for k in ("primal", "dual", "gap")},
                    "cuOpt parameter names")
            require(all(type(v) is bool if k in ("dual_postsolve", "crossover") else type(v) in (int, float)
                        for k, v in params.items()), "cuOpt parameter types")
            require(params.get("num_cpu_threads") == 4 and params.get("time_limit") == 40, "cuOpt resource settings")
            concurrent = config["id"] == "cuopt-concurrent"
            require(config["algorithm"] == ("concurrent" if concurrent else "pdlp"), "cuOpt algorithm identity")
            require(params["presolve"] == (2 if concurrent else 0) and params["crossover"] == concurrent
                    and params["dual_postsolve"] is True, "cuOpt presolve/crossover")
            require(params["pdlp_solver_mode"] == 4 and params["iteration_limit"] == 50000 and params["random_seed"] == 17,
                    "cuOpt work controls")
            require(params.get("method") == (0 if config["algorithm"] == "concurrent" else 1), "cuOpt method")
            if config["algorithm"] == "pdlp":
                require(config["precision"] == config["id"].removeprefix("cuopt-pdlp-"), "cuOpt precision identity")
                require(params.get("pdlp_precision") == {"double": 1, "mixed": 2, "single": 0}.get(config["precision"]), "cuOpt precision")
            else:
                require(params["pdlp_precision"] == 1 and config["precision"] == "native", "concurrent precision")
            for scale in ("absolute", "relative"):
                for kind in ("primal", "dual", "gap"):
                    require(params.get(f"{scale}_{kind}_tolerance") == 1e-9, "cuOpt tolerance")
        elif config["solver"] == "copt":
            default = config["id"] == "copt-cpu-default"
            require(set(params) == {"LpMethod", "GPUMode", "GPUDevice", "Threads", "Crossover", "Presolve",
                    "Scaling", "TimeLimit", "FeasTol", "DualTol"} | (set() if default else {"PDLPTol"}), "COPT parameter names")
            require(all(type(v) in (int, float) for v in params.values()), "COPT parameter types")
            require(config["algorithm"] == ("default-lp" if default else "pdlp") and config["precision"] == "opaque", "COPT method identity")
            require(params["LpMethod"] == (-1 if default else 6) and params["Presolve"] == (-1 if default else 0)
                    and params["Crossover"] == int(default) and params["Scaling"] == -1 and params["GPUDevice"] == 0,
                    "COPT method settings")
            require(default or params["PDLPTol"] == 1e-9, "COPT PDLP tolerance")
            require(params.get("Threads") == 4 and params.get("TimeLimit") == 40, "COPT resource settings")
            require(params.get("GPUMode") == int(config["gpu"]), "COPT GPU setting")
            require(params.get("FeasTol") == params.get("DualTol") == 1e-9, "COPT tolerance")
        else:
            require(params.get("threads") == 4 and params.get("time_limit_ms") == 40000, "project/HiGHS resources")
            require(params.get("absolute") == params.get("relative") == 1e-9, "project/HiGHS tolerance")
    by_phase = {p["id"]: p for p in phases}
    expected = {"A-software": (2400, 0, 0, 0, 0), "A-hardware": (240, 60, 2, 2, 30),
                "A-adapter-acceptance": (2400, 420, 20, 14, 30), "A-report": (600, 0, 0, 0, 0),
                "A-cleanup-margin": (400, 0, 0, 0, 0), "B-screening": (57600, 10080, 240, 168, 60),
                "B-report": (600, 0, 0, 0, 0), "B-cleanup-margin": (400, 0, 0, 0, 0)}
    require(set(by_phase) == set(expected), "phase set")
    for name, expected_values in expected.items():
        p = by_phase[name]
        require(all(type(p[k]) is int for k in ("cpu_seconds", "gpu_seconds", "jobs", "gpu_jobs", "job_wall_seconds")),
                "integer reservation units required")
        require(tuple(p[k] for k in ("cpu_seconds", "gpu_seconds", "jobs", "gpu_jobs", "job_wall_seconds")) == expected_values,
                "changed resource proposal: " + name)
        if p["jobs"]:
            require(p["cpu_seconds"] == p["jobs"] * p["job_wall_seconds"] * proposal["cpu_slots"], "CPU reservation arithmetic")
            require(p["gpu_seconds"] == p["gpu_jobs"] * p["job_wall_seconds"], "GPU reservation arithmetic")
    jobs = list(screening_jobs(proposal))
    require(len(jobs) == by_phase["B-screening"]["jobs"] and sum(j["gpu"] for j in jobs) == by_phase["B-screening"]["gpu_jobs"], "grid/resource mismatch")
    for resource in ("cpu_seconds", "gpu_seconds"):
        require(sum(p[resource] for p in phases) == proposal["total_" + resource], "total resource arithmetic")
    if verify_artifacts:
        checked_reference(proposal["historical_accounting"], root)
        for instance in instances:
            manifest = read_json_bytes(checked_reference(instance["source_manifest"], root))
            entries = [i for i in manifest["instances"] if i["id"] == instance["id"]]
            require(len(entries) == 1, "instance absent/ambiguous in source manifest")
            for key in ("model", "family", "group", "license"):
                require(instance[key] == entries[0][key], "source manifest binding mismatch")
            checked_reference(instance["model"], root)
    return dict(contract_valid=True, execution_authorized=False, screening_jobs=len(jobs),
                proposed_cpu_seconds=proposal["total_cpu_seconds"], proposed_gpu_seconds=proposal["total_gpu_seconds"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=("proposal", "model", "endpoint", "canonicalize"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--model", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify-artifacts", action="store_true")
    args = parser.parse_args()
    raw, document = read(args.path)
    if args.kind == "proposal":
        result = validate_proposal(document, args.verify_artifacts)
    elif args.kind == "canonicalize":
        require(args.output is not None, "--output required")
        result = canonicalize(raw)
        with args.output.open("x") as output:
            output.write(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
        result = dict(contract_valid=True, kind="canonical-model", solver_accepted=False)
    elif args.kind == "model":
        validate_model(document)
        result = dict(contract_valid=True, solver_accepted=False)
    else:
        require(args.model is not None, "--model required")
        model_raw, model = read(args.model)
        validate_endpoint(document, model, sha256(model_raw))
        result = dict(contract_valid=True, solver_accepted=False)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
