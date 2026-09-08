# First Bootstrap Experiment

Purpose: produce and inspect a reproducible smoke record. Scope: CPU M0.

From a committed checkout after [tool installation](../operations/build.md):

```bash
cargo build --workspace --locked
cargo run -p optimizer-cli -- hello
python3 tools/validate_artifacts.py
python3 tools/benchmark_smoke.py --output artifacts/bootstrap-smoke.json
python3 tools/validate_artifacts.py --result artifacts/bootstrap-smoke.json
```

Expected CLI output: hello workspace. Validation prints
artifact schemas and provenance: passed. The smoke prints its output path.
Inspect that JSON for revision, dirty state, hardware, seed, limits, manifest hash,
elapsed nanoseconds, and smoke_passed. It is a process smoke, not a solver result.

[The example record](../../examples/experiment-result.json) is marked example
and uses an all-zero revision to avoid pretending it is measurement evidence.
Real measured records require a Git revision. Generated artifacts are ignored by
Git; retain them through CI artifact storage or a separately reviewed evidence package.
