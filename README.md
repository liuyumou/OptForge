# AI Optimizer

A Rust-first research project for mathematical optimization and scheduling with
selective GPU acceleration. The current milestone is **C8 complete: a search that
registers an extension is reproducible from its record**. It validates original
linear models and candidates, solves them with an independently validated incumbent,
proves optimality with its own search, accepts separately authored extensions
without granting them any mathematical authority, and records each search with the
provenance needed to re-execute it. Flow-shop instances reach that same machinery
through an exactly linear encoding, and their makespans are recomputed by a
recurrence that shares no code with the heuristics proposing schedules. A local
registry resolves a named extension into a run and refuses every claim it cannot
check, which is what lets an extension-influenced record be re-executed rather than
merely read.

## Quick start

Supported development platform: Linux x86-64. CPU checks require Rust (installed
through rustup), Python 3.11+, Git, and util-linux `flock`. Solving requires the
pinned HiGHS 1.11.0 build, which needs CMake and a C++ compiler; NVIDIA drivers
are optional for discovery and CUDA is not a build dependency.

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r tools/requirements.txt
cargo install cargo-deny --version 0.19.0 --locked
bash tools/setup_highs.sh
cargo build --workspace --locked
cargo run -p optimizer-cli -- hello
cargo run -p optimizer-cli -- model validate --model examples/model-v1.json
cargo run -p optimizer-cli -- solve \
  --model examples/model-v1.json --config examples/solve-config-v1.json
cargo run -p optimizer-cli -- search \
  --model examples/model-v1.json --config examples/search-config-v3.json \
  --output artifacts/run.json
cargo run -p optimizer-cli -- verify \
  --record artifacts/run.json --model examples/model-v1.json
cargo run -p optimizer-cli -- gpu discover --dry-run
bash tools/gpu_job.sh GPU-<uuid> \
  cargo run -p optimizer-cli -- gpu probe --device GPU-<uuid>
bash tools/check.sh
```

The hello command prints `hello workspace`. Solving prints a version-1 solve
record whose objective and violations are recomputed by the core, not echoed from
the backend; exit 0 means a completed outcome, 1 a limit, 130 an interruption.
Searching prints a version-1 run record whose embedded search record carries the
executive's own proof claim, plus the revision, model fingerprint and input
hashes needed to repeat it. Verifying re-runs that search from the record alone
and exits 2 on any divergence, naming the field; agreement establishes
determinism on this host, not optimality.
Discovery prints JSON with `status: available` and devices sorted by UUID with their
driver version, or `status: unavailable` and a diagnostic. It never creates a CUDA
context. Probing does: it takes the shared host lease, creates a context on one named
device, and reports the UUID the driver read back beside the one that was requested,
along with the compute capability and the kernels the provisioned code object
provides. A probe that cannot reach a device exits 2 and writes no report. Checks
include a bounded process smoke measurement whose artifact is written to
`artifacts/bootstrap-smoke.json`. A Git commit is required for that measured record.

`tools/setup_highs.sh` fetches and builds the pinned library under `target/native`,
outside tracked source. `tools/check.sh` requires it; set
`AI_OPTIMIZER_SKIP_NATIVE=1` to run without it, which reports that native
acceptance was not covered.

## Project navigation

- [Current status and milestones](wiki/status.md)
- [Contributor and autonomous workflow](CONTRIBUTING.md)
- [Architecture and ownership](docs/architecture/overview.md)
- [Bootstrap specification](docs/specifications/SPEC-0000-bootstrap.md)
- [Model and validation specification](docs/specifications/SPEC-0001-model-and-validation.md)
- [Backend contract specification](docs/specifications/SPEC-0002-backend-contract.md)
- [Solver executive specification](docs/specifications/SPEC-0003-solver-executive.md)
- [Extension runtime specification](docs/specifications/SPEC-0004-extension-runtime.md)
- [Run surface specification](docs/specifications/SPEC-0005-run-surface.md)
- [Flow-shop scheduling specification](docs/specifications/SPEC-0008-flow-shop.md)
- [Extension registry specification](docs/specifications/SPEC-0009-extension-registry.md)
- [Validate a model and candidate](docs/tutorials/model-validation.md)
- [Solve a model](docs/tutorials/solve-a-model.md)
- [Run and verify a search](docs/tutorials/run-and-verify.md)
- [Register an extension](docs/tutorials/register-an-extension.md)
- [GPU discovery and lease contract](docs/specifications/SPEC-0006-gpu-lease.md)
- [Heterogeneous computation specification](docs/specifications/SPEC-0010-heterogeneous-computation.md)
- [GPU LP backend specification](docs/specifications/SPEC-0011-gpu-lp-backend.md)
- [Artifact contract](docs/specifications/SPEC-0007-artifacts.md)
- [Build and verification](docs/operations/build.md)
- [GPU operations](docs/operations/gpu.md)
- [First experiment tutorial](docs/tutorials/first-experiment.md)
- [Benchmark policy](docs/benchmarks/protocol.md)
- [Glossary](wiki/glossary.md)
- [Backlog](state/backlog.yaml) and [active task](state/active-task.md)
- [Changelog](CHANGELOG.md)

The source [implementation plan](implementation-plan.md) defines the evidence
stages and capability roadmap. The [research plan](ai-native-optimizer-plan.md)
provides long-term direction. Their unvalidated research claims are hypotheses.

## Layout

`crates/` contains the Rust workspace. optimizer-core owns original models,
versioned JSON, objective recomputation, candidate feasibility with explicit
tolerances, and the backend-neutral solve contract. optimizer-highs implements
that contract against the pinned CPU HiGHS build and is the only crate permitted
to contain unsafe code. optimizer-solver owns the branch-and-bound executive and
consumes the solve contract as a relaxation service without depending on any
backend. optimizer-extension defines the extension declaration, authority model
and guarded host; optimizer-extension-examples holds independently authored
extensions, including deliberately hostile ones, and depends only on the
published APIs. optimizer-registry resolves a recorded extension identity into a
registration the executive accepts, refusing any claim it cannot check against the
extension's own declaration; it names no extension itself, so the concrete provider
table lives in the CLI. The CLI exposes validation, solving and GPU
discovery/ownership, the reproducible run surface and the registry surface;
optimizer-experiment owns run records, their provenance and the verification
comparison. Remaining numerical crates reserve ownership boundaries without solver
APIs. `schemas/`, `examples/`, `tests/`, and `tools/` provide executable contracts.
`docs/` is authoritative; `wiki/` provides navigation. Python SDK, CUDA kernels,
dynamically loaded native extensions, checkpoint restart and performance suites are
deferred, each with its blocker recorded in
[known failures](state/known-failures.md).

## License

Project code and small generated fixtures use the [MIT license](LICENSE).
HiGHS 1.11.0 is MIT licensed and is fetched and built from pinned, checksum
verified upstream source; it is not vendored into tracked source. Other external
datasets and native dependencies need their own license records before
introduction. No third-party benchmark dataset is bundled.
