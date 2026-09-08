"""Bounded CLI bootstrap measurement; this is not a solver benchmark."""

import argparse
import hashlib
import json
import os
import platform
import resource
import subprocess
import time
from pathlib import Path

from validate_artifacts import ROOT, validate_manifest, validate_result


def command(*args):
    return subprocess.check_output(args, cwd=ROOT, text=True, timeout=30, env={**os.environ, "LC_ALL": "C"}).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/bootstrap-smoke.json")
    args = parser.parse_args()
    manifest_path = ROOT / "benchmarks/manifests/bootstrap-smoke.json"
    manifest = validate_manifest(manifest_path)
    config = manifest["configuration"]
    if manifest["purpose"] != "bootstrap-smoke" or manifest["timing"]["warmup_runs"] != 0 or manifest["timing"]["measured_runs"] != 1:
        raise SystemExit("M0 smoke requires bootstrap-smoke purpose, zero warmups, and one measured run")
    cpu_fields = json.loads(command("lscpu", "--json"))["lscpu"]
    cpu_model = next(field["data"] for field in cpu_fields if field["field"] == "Model name:")
    binary = ROOT / "target/debug/optimizer"
    if not binary.is_file():
        raise SystemExit("run cargo build --workspace --locked first")

    def set_limits():
        memory = config["memory_limit_mib"] * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (memory, memory))

    start = time.monotonic_ns()
    output = subprocess.check_output(
        [str(binary), "hello"], text=True,
        timeout=config["time_limit_ms"] / 1000,
        env={**os.environ, "OMP_NUM_THREADS": str(config["threads"])},
        preexec_fn=set_limits,
    )
    elapsed = time.monotonic_ns() - start
    if output != "hello workspace\n":
        raise SystemExit(f"unexpected smoke output: {output!r}")
    record = {
        "schema_version": 1, "kind": "measured", "record_id": "m0-bootstrap-smoke",
        "manifest": {"path": str(manifest_path.relative_to(ROOT)), "sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest()},
        "revision": command("git", "rev-parse", "HEAD"),
        "dirty": bool(command("git", "status", "--porcelain")),
        "hardware": {"os": platform.platform(), "cpu": cpu_model, "logical_cpus": os.cpu_count(), "gpu_uuid": None, "gpu_name": None, "driver": None},
        "toolchain": {"rustc": command("rustc", "--version"), "cargo": command("cargo", "--version")},
        "configuration": config,
        "timing": {"clock": "monotonic", "includes": "end-to-end-with-transfers", "elapsed_ns": elapsed, "samples": 1},
        "status": "smoke_passed", "objective": None,
        "warnings": ["Bootstrap process smoke only; no optimization or GPU work performed."], "error": None,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2) + "\n")
    validate_result(args.output)
    print(f"bootstrap smoke passed: {args.output}")


if __name__ == "__main__":
    main()
