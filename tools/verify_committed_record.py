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
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BINARY = ROOT / "target/debug/optimizer"
RECORD = ROOT / "examples/run-record-v1.json"
MODEL = ROOT / "examples/model-v1.json"


def verify(record, model):
    """Run one verification and return its exit code with stdout and stderr."""
    completed = subprocess.run(
        [str(BINARY), "verify", "--record", str(record), "--model", str(model)],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=ROOT,
    )
    return completed.returncode, completed.stdout, completed.stderr


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

    print("committed run record re-executed and verified: passed")


if __name__ == "__main__":
    main()
