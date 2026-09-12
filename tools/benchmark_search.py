"""Diagnostic timing for the branch-and-bound node path.

This is NOT a benchmark result and NOT evidence. It exists so that
behaviour-preserving work on the per-node path can be shown to change timing
without changing conclusions, and it refuses to report a speedup it cannot back
with identical search counters.

Two design choices are deliberate and worth stating, because both were arrived at
rather than defaulted to.

The unit of work is a fixed node budget, not a time limit. `time_limit_ms` is null
in the frozen configuration, so an outcome cannot depend on how fast the host
happens to be. A time-limited workload would explore different trees before and
after a change, which would make the comparison meaningless *and* legitimately move
the ten fields SPEC-0005 requirement 11 compares.

The tool lives here rather than in `benches/` as a criterion harness. `tools/check.sh`
runs `cargo clippy --workspace --all-targets`, which compiles bench targets on every
gate run, and `cargo deny --locked check`, which makes every transitive dependency a
policy obligation. Criterion would put both on the gate's critical path for a
measurement run by hand. Driving the built binary also makes the timing end-to-end
by construction, which `docs/benchmarks/protocol.md` requires.

Usage:
    python3 tools/benchmark_search.py --output artifacts/node-path-<label>.json
    python3 tools/benchmark_search.py --compare artifacts/a.json artifacts/b.json
"""

import argparse
import hashlib
import json
import os
import resource
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BINARY = ROOT / "target/release/optimizer"
MANIFEST = ROOT / "benchmarks/manifests/perf-node-budget-v1.json"
CONFIG = ROOT / "benchmarks/configs/search-node-budget-v2.json"

# Every field SPEC-0005 requirement 11 compares, plus the node counters that make a
# per-node change visible. A timing difference accompanied by any difference here is
# a bug report, not a speedup.
CONCLUSIONS = (
    "outcome",
    "objective",
    "dual_bound",
    "gap",
    "forfeited",
    "nodes_explored",
    "nodes_pruned_infeasible",
    "nodes_pruned_bound",
    "open_nodes_remaining",
    "relaxations_solved",
)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def text(program, *args):
    try:
        out = subprocess.check_output(
            [program, *args], cwd=ROOT, text=True, timeout=30,
            env={**os.environ, "LC_ALL": "C"},
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return out.strip() or "unknown"


def hardware():
    cpu = "unknown"
    for line in text("lscpu").splitlines():
        if line.startswith("Model name:"):
            cpu = line.split(":", 1)[1].strip()
            break
    return {"os": text("uname", "-sr"), "cpu": cpu, "logical_cpus": os.cpu_count()}


def limit_address_space(mib):
    def apply():
        limit = mib * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))

    return apply


def solve(instance, out_dir, memory_mib, timeout_s):
    """Run one search end to end and return (elapsed_ns, record) or raise."""
    record = out_dir / f"{instance['id']}-run.json"
    model = out_dir / f"{instance['id']}-model.json"
    command = [
        str(BINARY), "schedule", "solve",
        "--instance", str(ROOT / instance["path"]),
        "--config", str(CONFIG),
        "--output", str(record),
        "--output-model", str(model),
    ]
    started = time.monotonic_ns()
    completed = subprocess.run(
        command, cwd=ROOT, capture_output=True, text=True, timeout=timeout_s,
        preexec_fn=limit_address_space(memory_mib),
        env={**os.environ, "OMP_NUM_THREADS": "1", "LC_ALL": "C"},
    )
    elapsed = time.monotonic_ns() - started
    # A node-limited search exits 1 by the CLI mapping; that is the expected
    # outcome here and is not a failure.
    if completed.returncode not in (0, 1):
        raise SystemExit(
            f"{instance['id']}: solve exited {completed.returncode}: {completed.stderr}"
        )
    return elapsed, json.loads(record.read_text())


def measure(label):
    if not BINARY.is_file():
        raise SystemExit("run cargo build --release --workspace --locked first")
    manifest = json.loads(MANIFEST.read_text())
    memory_mib = manifest["configuration"]["memory_limit_mib"]
    timeout_s = manifest["configuration"]["time_limit_ms"] / 1000
    warmups = manifest["timing"]["warmup_runs"]
    measured = manifest["timing"]["measured_runs"]

    out_dir = ROOT / "artifacts" / "node-path"
    out_dir.mkdir(parents=True, exist_ok=True)

    instances = []
    for instance in manifest["instances"]:
        path = ROOT / instance["path"]
        if sha256(path) != instance["sha256"]:
            raise SystemExit(f"{instance['id']}: instance checksum differs from the manifest")

        for _ in range(warmups):
            solve(instance, out_dir, memory_mib, timeout_s)

        samples, conclusions = [], None
        for _ in range(measured):
            elapsed, record = solve(instance, out_dir, memory_mib, timeout_s)
            samples.append(elapsed)
            observed = {key: record["search"].get(key) for key in CONCLUSIONS}
            observed["model_fingerprint"] = record["model_fingerprint"]
            if conclusions is None:
                conclusions = observed
            elif observed != conclusions:
                raise SystemExit(
                    f"{instance['id']}: the same search reached different conclusions "
                    f"across repeats, which is a determinism bug rather than a "
                    f"measurement: {conclusions} then {observed}"
                )
            print(f"  {instance['id']}: {elapsed / 1e6:9.1f} ms", file=sys.stderr)

        samples.sort()
        instances.append({
            "id": instance["id"],
            "sha256": instance["sha256"],
            "elapsed_ns_min": samples[0],
            "elapsed_ns_median": samples[len(samples) // 2],
            "conclusions": conclusions,
        })

    return {
        "kind": "node-path-timing-diagnostic",
        "claim": "none",
        "note": (
            "Diagnostic timing for behaviour-preserving work. Not a benchmark "
            "result, not evidence, and no acceptance threshold is defined or "
            "implied. Comparable only against another run of this tool on the "
            "same host and manifest."
        ),
        "label": label,
        "revision": text("git", "rev-parse", "HEAD"),
        "dirty": text("git", "status", "--porcelain") != "",
        "hardware": hardware(),
        "toolchain": {"rustc": text("rustc", "--version"), "cargo": text("cargo", "--version")},
        "manifest": {"path": str(MANIFEST.relative_to(ROOT)), "sha256": sha256(MANIFEST)},
        "search_config": {"path": str(CONFIG.relative_to(ROOT)), "sha256": sha256(CONFIG)},
        "seed": manifest["configuration"]["seed"],
        "timing": {
            "clock": "monotonic",
            "includes": "end-to-end-with-transfers",
            "warmup_runs": warmups,
            "measured_runs": measured,
        },
        "instances": instances,
    }


def compare(before_path, after_path):
    """Report a delta, refusing to call it a speedup if any conclusion moved."""
    before = json.loads(Path(before_path).read_text())
    after = json.loads(Path(after_path).read_text())
    if before["manifest"]["sha256"] != after["manifest"]["sha256"]:
        raise SystemExit("the two runs used different manifests and are not comparable")
    if before["search_config"]["sha256"] != after["search_config"]["sha256"]:
        raise SystemExit("the two runs used different configurations and are not comparable")

    by_id = {i["id"]: i for i in before["instances"]}
    divergent, rows = [], []
    for after_instance in after["instances"]:
        before_instance = by_id.get(after_instance["id"])
        if before_instance is None:
            raise SystemExit(f"{after_instance['id']} is absent from the baseline")
        if before_instance["conclusions"] != after_instance["conclusions"]:
            divergent.append(after_instance["id"])
        rows.append((
            after_instance["id"],
            before_instance["elapsed_ns_min"] / 1e6,
            after_instance["elapsed_ns_min"] / 1e6,
        ))

    print(f"{'instance':10} {'before ms':>12} {'after ms':>12} {'change':>10}")
    for name, before_ms, after_ms in rows:
        change = (after_ms - before_ms) / before_ms * 100 if before_ms else 0.0
        print(f"{name:10} {before_ms:12.1f} {after_ms:12.1f} {change:9.1f}%")

    if divergent:
        raise SystemExit(
            "\nCONCLUSIONS CHANGED on: " + ", ".join(divergent) +
            "\nThis is a bug report, not a speedup. Behaviour-preserving work must "
            "leave every compared field and node counter identical."
        )
    print("\nconclusions identical on every instance; the change is behaviour-preserving")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", help="write a measurement document here")
    parser.add_argument("--label", default="unlabelled", help="what this run measures")
    parser.add_argument("--compare", nargs=2, metavar=("BEFORE", "AFTER"))
    arguments = parser.parse_args()

    if arguments.compare:
        compare(*arguments.compare)
        return

    document = measure(arguments.label)
    text_out = json.dumps(document, indent=2) + "\n"
    if arguments.output:
        destination = Path(arguments.output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text_out)
        print(f"measurement written: {destination}", file=sys.stderr)
    else:
        print(text_out)


if __name__ == "__main__":
    main()
