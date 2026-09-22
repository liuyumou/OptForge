# AI Optimizer

A Rust-first research project for mathematical optimization and scheduling with
selective GPU acceleration. **C6 is implemented under SPEC-0010 and SPEC-0011**:
a search can evaluate integer schedules on a GPU, and a first-order LP backend
runs on the host or device with host-side validation and certification. The next
prioritized work is the [GPU LP precision roadmap](docs/plans/gpu-lp-precision-roadmap.md).
Slice 1 repairs a [certification defect](state/known-failures.md#lp-certification-can-lose-the-roundoff-allowance-at-zero-reduced-cost)
and the objective/gap checks. Slice 2 adds the [bounded LP study harness](docs/benchmarks/lp-precision-study.md),
with independent endpoints, frozen workloads and a [measured baseline report](docs/benchmarks/lp-baseline-gpup2.md).
Slice 3, the shared resumable FP64 controller, is next.
GPUP-THROUGHPUT, opt-in repeated-solve throughput sessions, is complete under
[SPEC-0014](docs/specifications/SPEC-0014-lp-repeated-solve-throughput.md) and
[ADR-0023](docs/decisions/ADR-0023-repeated-solve-throughput.md), both accepted
2026-09-20; its [report](docs/benchmarks/lp-repeated-solve-throughput.md) verifies
687 of 705 attempts with 4785/4785 batch solves bitwise identical to fresh singles.
Mixed precision and performance recipes are not implemented yet.

The project validates original
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
- [LP certification arithmetic and limits](docs/architecture/lp-certification.md)
- [GPU LP performance roadmap and slices](docs/plans/gpu-lp-precision-roadmap.md)
- [FP64-pipe root cause of the FP32 component slowdown](docs/benchmarks/lp-fp64-pipe-root-cause.md)
- [GPUP-5C guards, fusion, double-float, tiers and corpus report](docs/benchmarks/lp-fp64-pipe-gpup5c.md)
- [Mixed-precision LP draft](docs/specifications/SPEC-0012-mixed-precision-lp.md)
- [Accepted LP experiment protocol](docs/specifications/SPEC-0013-lp-precision-experiments.md)
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
that contract against the pinned CPU HiGHS build. It and optimizer-cuda-sys are
the only crates permitted to contain unsafe code. optimizer-solver owns the
branch-and-bound executive and consumes the solve contract as a relaxation service without depending on any
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
optimizer-cuda-sys owns the CUDA driver boundary and optimizer-cuda owns discovery,
the host lease, device selection and residency; `cuda/` holds the kernels, built out
of tracked source by `tools/setup_cuda.sh`. `docs/` is authoritative; `wiki/`
provides navigation. optimizer-lp owns the host LP method and certification without
a device dependency; optimizer-lp-cuda owns the device backend. Python SDK,
mixed-precision LP, dynamically loaded native extensions, checkpoint restart and
performance suites remain planned, with limits recorded in
[known failures](state/known-failures.md).

## License

Project code and small generated fixtures use the [MIT license](LICENSE).
HiGHS 1.11.0 is MIT licensed and is fetched and built from pinned, checksum
verified upstream source; it is not vendored into tracked source. Other external
datasets and native dependencies need their own license records before
introduction. No third-party benchmark dataset is bundled.
