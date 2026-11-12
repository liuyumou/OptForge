# AI Optimizer

A Rust-first research project for mathematical optimization and scheduling with
selective GPU acceleration. **C6 is implemented under SPEC-0010 and SPEC-0011**:
a search can evaluate integer schedules on a GPU, and a first-order LP backend
runs on the host or device with host-side validation and certification.

As of 2026-11-11, **GPUP-8 is implemented experimentally but incomplete**.
Its corrected proof and device acceptance pass; six small profiles complete,
then the first large BF16 profile times out. No certified latency gain or supported
precision preset is established, and GPUP-9 remains gated. The
[system diagnosis](docs/benchmarks/lp-system-diagnosis-2026-11-10.md) identifies
expanded reconstruction and state-update costs as the dominant current bottleneck.
The [revised roadmap](docs/plans/gpu-lp-precision-roadmap.md#current-plan-2026-11-10)
now prioritizes [persistent multi-FP4 iterations](docs/plans/lp-fp4-persistent-state.md):
approximate inner iterations and fused kernels. The
[new planning amendment](docs/decisions/ADR-0058-fp4-gpu-exploration-quality-tiers.md)
admits independent device exploration after the failed long CPU trajectory gate.
The [FP4 GPU pilot](docs/benchmarks/lp-fp4-gpu-pilot.md) now completes all 216
profile cells after corrected arithmetic and four-sanitizer admission. This
candidate is slower than native FP64 in the bounded grid; no solver preset is
selected. CPU numerical recovery is next ready. Future certified
comparisons have explicit 1e-7 and strict 1e-9 tiers, with same-tolerance controls
and complete-solve speed/coverage criteria; current solver defaults stay unchanged.
[SPEC-0025](docs/specifications/SPEC-0025-persistent-fp4-contract.md) implements
the CPU numerical/transaction/cost contract; its
[report](docs/benchmarks/lp-fp4-spec-gpup-fp4-spec.md) records the frozen proposal
and retained-data feasibility bounds. The
[FP4-PROTO CPU attempt](docs/benchmarks/lp-fp4-proto-gpup-fp4-proto.md) qualifies
none of twelve cells: nine error-guard and three metadata refusals. That v1
attempt remains closed; the independent GPU pilot preserves its sources,
criteria and charges. Full prototype acceptance and certified-solver speedup
remain unestablished.
[cuOpt setup](docs/operations/cuopt.md) is isolated and optional;
Gurobi remains unavailable and was excluded from the baseline.

[GPUP-BASELINE](docs/benchmarks/lp-external-baseline-native-return.md) is complete
under the user's amended comparison policy: all 240 planned cells have settled
attempts, 198 meet their comparison policy and 135 certify strictly.
For cuOpt, 90/96 native returns pass its explicit error/status policy, while
24/96 meet the independent certificate. Limits, native errors, outer failures
and numerical discrepancies remain visible. This is not a quality-matched
performance claim. Total baseline GPU charge is 3091.996 / 3600 seconds.
[SPEC-0023](docs/specifications/SPEC-0023-baseline-native-return.md) records the
cuOpt policy, and SPEC-0022's strict mathematical checker remains unchanged.

[GPUP-RESIDENT2](docs/benchmarks/lp-resident2-gpup-resident2.md) is complete as a
bounded negative result: certified coverage is preserved, but complete latency
fails the retention gate. Keep the native control. The new FP4 pilot and numerical
recovery lead to integration before a certified study; MIXED2 and DELIVERY2
remain alternatives.

The earlier research slices provide the following foundation.
Slice 1 repairs a [certification defect](state/known-failures.md#lp-certification-can-lose-the-roundoff-allowance-at-zero-reduced-cost)
and the objective/gap checks. Slice 2 adds the [bounded LP study harness](docs/benchmarks/lp-precision-study.md),
with independent endpoints, frozen workloads and a [measured baseline report](docs/benchmarks/lp-baseline-gpup2.md).
The shared resumable FP64 controller and subsequent explicit tuned/precision
slices are implemented, with their evidence linked from the roadmap.
GPUP-THROUGHPUT, opt-in repeated-solve throughput sessions, is complete under
[SPEC-0014](docs/specifications/SPEC-0014-lp-repeated-solve-throughput.md) and
[ADR-0023](docs/decisions/ADR-0023-repeated-solve-throughput.md), both accepted
2026-09-20; its [report](docs/benchmarks/lp-repeated-solve-throughput.md) verifies
687 of 705 attempts with 4785/4785 batch solves bitwise identical to fresh singles.
Explicit FP32 execution and GPUP-6 adaptive audit/recovery policies are
implemented experimentally; the [adaptive report](docs/benchmarks/lp-adaptive-gpup6.md)
records acceptance and incomplete comparison coverage. No supported precision
recipe is selected. The [2026-10-12 design](docs/plans/lp-precision-architecture-2026-10-12.md)
now separates exact compact storage, accurate expansion arithmetic, residual-driven
refinement and assessment costs. GPUP-REP CPU contract validation is complete under accepted ADR-0034 and the
bounded CPU subset of SPEC-0020. Its exact codec, binary64/expansion reference
semantics and layout receipts remain CPU reference tools.
[GPUP-EXEC](docs/benchmarks/lp-exact-executor-gpup-exec.md) adds the separate
bounded exact-dot executor under ADR-0035: 108 retained attempts, 94 verified
endpoints and explicit range/coverage limits, with no fresh-solve speedup or preset.
[GPUP-STATE](docs/benchmarks/lp-expansion-state-gpup-state.md) closes with a
resource admission refusal under ADR-0036: its first full-range exact-bin
primitive exceeds the register/spill gate in both expansion formats. PR 19's
full-range compact FMA passes at 40 registers and zero spills, resolving that
scalar obstacle. It passes 6170 device cases, four scoped sanitizers and 36
independently verified primitive timings on RTX PRO 6000 Blackwell. The original
busy-device refusal is retained; total charge is 30.114068273 GPU seconds. No
full controller or solver performance benefit is admitted.
[GPUP-REFINE](docs/benchmarks/lp-refinement-gpup-refine.md),
[GPUP-ASSESS](docs/benchmarks/lp-assessment-scheduling-gpup-assess.md),
[GPUP-7](docs/benchmarks/lp-quantization-gpup7.md) and
[GPUP-7R](docs/benchmarks/lp-quant-resident-gpup7r.md) have since completed their
bounded investigations, with negative results and coverage limits retained.

The [COPT comparison and component report](docs/benchmarks/lp-copt-comparison.md)
now covers all 1140 planned attempts through 65536 rows. It identifies evidence
size, host preparation/checks and adaptive recovery costs as future directions;
coverage gaps remain, and no winner or preset is selected.

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
- [Current system diagnosis and cuOpt/COPT/Gurobi comparison](docs/benchmarks/lp-system-diagnosis-2026-11-10.md)
- [Certified-performance design decision](docs/decisions/ADR-0047-certified-performance-roadmap.md)
- [Optional cuOpt installation and acceptance status](docs/operations/cuopt.md)
- [Precision architecture and component motivations](docs/plans/lp-precision-architecture-2026-10-12.md)
- [Accepted CPU reference and bounded exact sparse-product executor](docs/specifications/SPEC-0020-lp-expansion-arithmetic.md)
- [GPUP-EXEC exact executor, costs and retained failures](docs/benchmarks/lp-exact-executor-gpup-exec.md)
- [GPUP-STATE original refusal and compact FMA challenge](docs/benchmarks/lp-expansion-state-gpup-state.md)
- [Correction LP, anchors and assessment contract](docs/specifications/SPEC-0021-lp-refinement.md)
- [Component and combination experiment design](docs/benchmarks/lp-precision-design-experiments.md)
- [FP64-pipe root cause of the FP32 component slowdown](docs/benchmarks/lp-fp64-pipe-root-cause.md)
- [GPUP-5C guards, fusion, double-float, tiers and corpus report](docs/benchmarks/lp-fp64-pipe-gpup5c.md)
- [Accepted mixed-precision LP contract](docs/specifications/SPEC-0012-mixed-precision-lp.md)
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
a device dependency; optimizer-lp-cuda owns the device backend. Quantized/FP8 and
Tensor LP candidates exist as research implementations, with no supported precision
preset. Python SDK, dynamically loaded native extensions, persistent checkpoint
restart and broader performance suites remain planned, with limits recorded in
[known failures](state/known-failures.md).

## License

Project code and small generated fixtures use the [MIT license](LICENSE).
HiGHS 1.11.0 is MIT licensed and is fetched and built from pinned, checksum
verified upstream source; it is not vendored into tracked source. Other external
datasets and native dependencies need their own license records before
introduction. No third-party benchmark dataset is bundled.
