"""Validate versioned records and local manifest checksums (SPEC-0007)."""

import argparse
import hashlib
import json
import math
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"


def read_json(path):
    def finite_float(value):
        result = float(value)
        if not math.isfinite(result):
            raise ValueError(f"non-finite JSON number: {value}")
        return result

    def reject_constant(value):
        raise ValueError(f"non-finite JSON number: {value}")

    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    return json.loads(path.read_text(), parse_constant=reject_constant, parse_float=finite_float, object_pairs_hook=unique_keys)


def validator(name):
    resources = []
    for path in sorted(SCHEMAS.glob("*.schema.json")):
        schema = read_json(path)
        Draft202012Validator.check_schema(schema)
        resources.append((path.name, Resource.from_contents(schema)))
    return Draft202012Validator(read_json(SCHEMAS / name), registry=Registry().with_resources(resources))


def validate_manifest(path):
    manifest = read_json(path)
    validator("benchmark-manifest-v1.schema.json").validate(manifest)
    ids = set()
    for instance in manifest["instances"]:
        if instance["id"] in ids:
            raise ValueError(f"duplicate instance ID: {instance['id']}")
        ids.add(instance["id"])
        target = (ROOT / instance["path"]).resolve()
        if not target.is_relative_to(ROOT):
            raise ValueError("instance path escapes repository")
        if hashlib.sha256(target.read_bytes()).hexdigest() != instance["sha256"]:
            raise ValueError(f"checksum mismatch: {target}")
    if manifest["configuration"]["seed"] not in manifest["seeds"]:
        raise ValueError("configuration seed is absent from manifest seeds")
    return manifest


def validate_run_record(path):
    """Validate one run record and its provenance (SPEC-0005)."""
    record = read_json(path)
    validator("run-record-v1.schema.json").validate(record)
    roles = [document["role"] for document in record["inputs"]]
    if sorted(roles) != ["config", "model"]:
        raise ValueError("run record must name exactly one model and one config input")
    # An input hash is verified when the document is still in the repository, so
    # a record cannot claim bytes the tree does not contain.
    for document in record["inputs"]:
        target = (ROOT / document["path"]).resolve()
        if not target.is_relative_to(ROOT):
            raise ValueError("input path escapes repository")
        if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() != document["sha256"]:
            raise ValueError(f"input checksum mismatch: {target}")
    if record["revision"] == "0" * 40 and not record["warnings"]:
        raise ValueError("an example record must say it is not a measurement")
    # A limit or failure never carries a proof, matching SPEC-0003.
    proven = {"proven_optimal", "proven_infeasible", "unbounded_or_infeasible"}
    if record["search"]["forfeited"] and record["search"]["outcome"] in proven:
        raise ValueError("a forfeited search must not report a completed proof")
    return record


def validate_result(path):
    result = read_json(path)
    validator("experiment-result-v1.schema.json").validate(result)
    target = (ROOT / result["manifest"]["path"]).resolve()
    if not target.is_relative_to(ROOT):
        raise ValueError("manifest path escapes repository")
    manifest = validate_manifest(target)
    if hashlib.sha256(target.read_bytes()).hexdigest() != result["manifest"]["sha256"]:
        raise ValueError("result manifest checksum mismatch")
    if result["configuration"] != manifest["configuration"]:
        raise ValueError("result configuration differs from manifest")
    device = result["configuration"]["device"]
    hardware = result["hardware"]
    if device == "cpu":
        if any(hardware[key] is not None for key in ("gpu_uuid", "gpu_name", "driver")):
            raise ValueError("CPU record must not claim GPU execution")
    elif hardware["gpu_uuid"] != device or not hardware["gpu_name"] or not hardware["driver"]:
        raise ValueError("GPU hardware must match the selected UUID and include driver/name")
    if result["kind"] == "measured" and result["revision"] == "0" * 40:
        raise ValueError("measured records require a real source revision")
    for key in ("clock", "includes"):
        if result["timing"][key] != manifest["timing"][key]:
            raise ValueError(f"timing protocol mismatch: {key}")
    if result["timing"]["samples"] != manifest["timing"]["measured_runs"]:
        raise ValueError("timing sample count differs from manifest")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path)
    args = parser.parse_args()
    if args.result:
        validate_result(args.result)
    else:
        validator("run-config-v1.schema.json").validate(read_json(ROOT / "examples/run-config.json"))
        validator("solve-config-v1.schema.json").validate(read_json(ROOT / "examples/solve-config-v1.json"))
        validator("search-config-v2.schema.json").validate(read_json(ROOT / "examples/search-config-v2.json"))
        validate_run_record(ROOT / "examples/run-record-v1.json")
        for path in sorted((ROOT / "benchmarks/manifests").glob("*.json")):
            validate_manifest(path)
        validate_result(ROOT / "examples/experiment-result.json")
    print("artifact schemas and provenance: passed")


if __name__ == "__main__":
    main()
