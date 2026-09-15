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
    validator("run-record-v2.schema.json").validate(record)
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


def validate_registry(path):
    """Validate the extension registry stored at `path` (SPEC-0009)."""
    return validate_registry_document(read_json(path))


def validate_registry_document(document):
    """Validate one extension registry and every promotion claim (SPEC-0009).

    Takes a parsed document so a test can check a mutated variant without writing
    a file, and so the schema and the cross-field rules are reachable separately.
    """
    validator("extension-registry-v1.schema.json").validate(document)
    ids = set()
    for entry in document["entries"]:
        if entry["extension_id"] in ids:
            raise ValueError(f"duplicate extension ID: {entry['extension_id']}")
        ids.add(entry["extension_id"])
        # Authority is derived from the category, never chosen by an entry. The
        # Rust resolution path enforces this too; checking it here keeps the two
        # authorities from disagreeing about a document either accepts.
        expected = {
            "candidate_producer": "propose_validated_candidate",
            "search_adviser": "propose_checked_action",
        }.get(entry["category"])
        if expected is None:
            raise ValueError(f"category {entry['category']} is not admitted")
        if entry["authority_basis"] != expected:
            raise ValueError(
                f"{entry['extension_id']}: category {entry['category']} implies {expected}"
            )
        if set(entry["requires"]) & set(entry["conflicts_with"]):
            raise ValueError(f"{entry['extension_id']}: requires and conflicts_with overlap")
        if entry["extension_id"] in set(entry["requires"]) | set(entry["conflicts_with"]):
            raise ValueError(f"{entry['extension_id']}: names its own identity")
        promotion = entry["promotion"]
        if promotion["state"] != "promoted":
            continue
        # A promotion claim is checkable, so it is checked: the cited record must
        # exist, hash as recorded, pass, and describe this extension and version.
        target = (ROOT / promotion["conformance_path"]).resolve()
        if not target.is_relative_to(ROOT):
            raise ValueError("conformance path escapes repository")
        if not target.exists():
            raise ValueError(f"conformance record missing: {target}")
        if hashlib.sha256(target.read_bytes()).hexdigest() != promotion["conformance_sha256"]:
            raise ValueError(f"conformance checksum mismatch: {target}")
        record = validate_conformance(target)
        if not record["outcome"]:
            raise ValueError(f"{entry['extension_id']}: cited conformance record did not pass")
        if record["extension_id"] != entry["extension_id"]:
            raise ValueError(f"{entry['extension_id']}: conformance record describes another extension")
        if record["version"] != entry["version"]:
            raise ValueError(f"{entry['extension_id']}: conformance record describes another version")
    return document


def validate_conformance(path):
    """Validate the conformance record stored at `path` (SPEC-0009)."""
    return validate_conformance_record(read_json(path))


def validate_conformance_record(record):
    """Validate one conformance record (SPEC-0009)."""
    validator("conformance-record-v1.schema.json").validate(record)
    # A record claiming to pass while carrying a failing check would let a promoted
    # entry cite evidence that contradicts itself.
    if record["outcome"] != all(check["passed"] for check in record["checks"]):
        raise ValueError("conformance outcome disagrees with its own checks")
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
        # The first-order settings example, which SPEC-0011 requirements 9 and 10
        # make recorded state. Validated here so the committed example cannot
        # drift from the schema a record embeds it under.
        validator("lp-settings-v1.schema.json").validate(
            read_json(ROOT / "examples/lp-settings-v1.json")
        )
        validator("search-config-v3.schema.json").validate(read_json(ROOT / "examples/search-config-v3.json"))
        validator("search-config-v3.schema.json").validate(
            read_json(ROOT / "examples/search-config-neh-v3.json")
        )
        # The frozen node-budget configuration the timing diagnostic drives. It is
        # validated here for the same reason every other committed configuration is:
        # the schema and the Rust parser must agree about it, and a measurement run
        # against a configuration the engine would reject is worth nothing.
        validator("search-config-v3.schema.json").validate(
            read_json(ROOT / "benchmarks/configs/search-node-budget-v3.json")
        )
        # The multi-node fixture's configuration. Its `node_limit` is set and its
        # `time_limit_ms` is null on purpose, so the tree it explores is the same
        # one on any host and the record stays re-executable rather than becoming
        # a record of how fast the machine that produced it was.
        validator("search-config-v3.schema.json").validate(
            read_json(ROOT / "examples/search-config-multi-node-v3.json")
        )
        validate_run_record(ROOT / "examples/run-record-v2.json")
        # The registry-backed scheduling record is validated by the same schema and
        # the same provenance rules, which is the point: SPEC-0009 introduces no new
        # record type and does not re-version this one.
        validate_run_record(ROOT / "examples/schedule-run-record-v2.json")
        # The record whose search actually branched. Same schema and same rules
        # again; what it adds is a committed tree deeper than the root.
        validate_run_record(ROOT / "examples/multi-node-run-record-v2.json")
        validate_registry(ROOT / "examples/extension-registry-v1.json")
        validate_conformance(ROOT / "examples/conformance-record-v1.json")
        from lp_protocol import campaign, validate
        for kind in ["trial", "ledger"]:
            validate(kind, read_json(ROOT / f"examples/lp-{kind}-v1.synthetic.json"))
        campaign(ROOT / "benchmarks/configs/lp-campaign-v1.json")
        for path in sorted((ROOT / "benchmarks/manifests").glob("*.json")):
            if not path.name.startswith("lp-"):
                validate_manifest(path)
        validate_result(ROOT / "examples/experiment-result.json")
    print("artifact schemas and provenance: passed")


if __name__ == "__main__":
    main()
