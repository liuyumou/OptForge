"""Re-execute a committed run record against the current build (SPEC-0005).

Every re-execution test in the Rust suites produces its record moments earlier in
the same process, against the same binary. That covers the comparison logic but
not the property the specification actually claims: that a record committed at an
earlier revision, by an author who is gone, is still enough to repeat its search.

This runs `optimizer verify` on the committed example and requires agreement. It
also requires the negative direction to hold, because a verifier that cannot fail
establishes nothing about the one that passed.
"""

import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BINARY = ROOT / "target/debug/optimizer"
RECORD = ROOT / "examples/run-record-v1.json"
MODEL = ROOT / "examples/model-v1.json"
SCHEDULE_RECORD = ROOT / "examples/schedule-run-record-v1.json"
SCHEDULE_MODEL = ROOT / "examples/schedule-model-v1.json"
INSTANCE = ROOT / "examples/flow-shop-v1.json"
REGISTRY = ROOT / "examples/extension-registry-v1.json"


def verify(record, model, extra=()):
    """Run one verification and return its exit code with stdout and stderr."""
    completed = subprocess.run(
        [str(BINARY), "verify", "--record", str(record), "--model", str(model), *extra],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=ROOT,
    )
    return completed.returncode, completed.stdout, completed.stderr


def registry_arguments():
    """Flags re-executing the committed scheduling record needs."""
    return (
        "--instance",
        str(INSTANCE),
        "--registry",
        str(REGISTRY),
    )


def check_registry_backed_record():
    """Re-execute a committed record produced with an extension registered.

    This is the property C8 exists to establish, and it cannot be established
    inside a single process: every Rust test builds its record moments earlier
    against the same binary. Here the record was committed at an earlier revision
    and its producer is reconstructed from the committed registry.
    """
    code, stdout, stderr = verify(SCHEDULE_RECORD, SCHEDULE_MODEL, registry_arguments())
    if code != 0:
        raise SystemExit(f"committed registry-backed record failed to verify: {stderr}")
    verdict = json.loads(stdout)
    if not verdict["agreement"]:
        raise SystemExit("committed registry-backed record did not agree")
    if verdict["extensions"] != ["flow-shop-neh"]:
        raise SystemExit(f"the producer must be reconstructed, got {verdict['extensions']}")
    if verdict["extensions_differ"]:
        raise SystemExit(f"the producer behaved differently: {verdict['extension_differences']}")

    # Without the registry the same record must be refused, and as unsupported
    # rather than as divergence. A verifier that accepted it either way would make
    # the pass above meaningless.
    code, _, stderr = verify(SCHEDULE_RECORD, SCHEDULE_MODEL)
    if code != 2 or "unsupported" not in stderr:
        raise SystemExit(
            f"a record naming an extension must be refused without a registry, got {code}: {stderr}"
        )
    if "divergence" in stderr:
        raise SystemExit(f"a missing registry must not be reported as divergence: {stderr}")

    # Two different rules live here and were previously conflated. Restamping the
    # registry is refused by resolution's declaration check, whose message also
    # contains the restamped version, so asserting only that the version appears
    # in stderr passed on the wrong error and never reached SPEC-0009
    # requirement 20's comparison at all. Both are now covered and each asserts
    # the message its own rule produces.
    with tempfile.TemporaryDirectory() as directory:
        # (1) Resolution: the registry claims a version the extension does not
        # report. Refused before requirement 20 is reached.
        restamped = Path(directory) / "registry.json"
        registry = json.loads(REGISTRY.read_text())
        for entry in registry["entries"]:
            if entry["extension_id"] == "flow-shop-neh":
                entry["version"] = "9.9.9"
                # The promotion claim is checked before the declaration
                # comparison, so it is dropped here to reach that comparison.
                entry["promotion"] = {"state": "experimental"}
        restamped.write_text(json.dumps(registry))
        code, _, stderr = verify(
            SCHEDULE_RECORD,
            SCHEDULE_MODEL,
            ("--instance", str(INSTANCE), "--registry", str(restamped), "--allow-experimental"),
        )
        if code != 2 or "but the extension declares" not in stderr:
            raise SystemExit(
                f"a registry naming another version must be refused by the "
                f"declaration check, got {code}: {stderr}"
            )
        if "divergence" in stderr:
            raise SystemExit(f"a version mismatch must not be a divergence: {stderr}")

        # (2) Requirement 20 proper: the registry is honest, so resolution
        # succeeds, and the *record* names a version this build no longer
        # declares. This is the case a record outliving its build produces, and
        # it is the only one that reaches the record-versus-resolved comparison.
        restated = Path(directory) / "record.json"
        record = json.loads(SCHEDULE_RECORD.read_text())
        summaries = record["search"]["extensions"]
        if not summaries or summaries[0]["extension_id"] != "flow-shop-neh":
            raise SystemExit("the committed schedule record must name flow-shop-neh")
        summaries[0]["version"] = "9.9.9"
        restated.write_text(json.dumps(record))
        code, _, stderr = verify(
            restated,
            SCHEDULE_MODEL,
            ("--instance", str(INSTANCE), "--registry", str(REGISTRY), "--allow-experimental"),
        )
        if code != 2 or "but the record names version 9.9.9" not in stderr:
            raise SystemExit(
                f"a record naming another extension version must be refused by "
                f"requirement 20, got {code}: {stderr}"
            )
        if "divergence" in stderr:
            raise SystemExit(f"a version mismatch must not be a divergence: {stderr}")


def main():
    if not BINARY.is_file():
        raise SystemExit("run cargo build --workspace --locked first")

    code, stdout, stderr = verify(RECORD, MODEL)
    if "not provisioned" in stderr:
        raise SystemExit("HiGHS not provisioned; run bash tools/setup_highs.sh")
    if code != 0:
        raise SystemExit(f"committed record failed to verify: {stderr}")

    verdict = json.loads(stdout)
    if not verdict["agreement"]:
        raise SystemExit("committed record did not agree")
    # The committed record is an example, so it is deliberately not evidence even
    # though it verifies. Asserting this keeps the two ideas distinct.
    if verdict["evidence"]:
        raise SystemExit("the example record must not claim to be evidence")

    # A changed model under an unchanged model_id must be refused, and a mutated
    # measurement must diverge. Without these, the pass above proves nothing.
    with tempfile.TemporaryDirectory() as directory:
        directory = Path(directory)

        changed = directory / "changed-model.json"
        model = json.loads(MODEL.read_text())
        model["objective"]["terms"][0]["coefficient"] += 0.5
        changed.write_text(json.dumps(model))
        code, _, stderr = verify(RECORD, changed)
        if code != 2 or "fingerprint mismatch" not in stderr:
            raise SystemExit(
                f"a changed model must be refused on its fingerprint, got {code}: {stderr}"
            )

        mutated = directory / "mutated-record.json"
        record = json.loads(RECORD.read_text())
        record["search"]["nodes_explored"] += 1
        mutated.write_text(json.dumps(record))
        code, _, stderr = verify(mutated, MODEL)
        if code != 2 or "nodes_explored" not in stderr:
            raise SystemExit(
                f"a mutated counter must diverge by name, got {code}: {stderr}"
            )

    check_registry_backed_record()

    print("committed run records re-executed and verified: passed")


if __name__ == "__main__":
    main()
