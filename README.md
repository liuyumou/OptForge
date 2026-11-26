# AI Optimizer

AI Optimizer is a research project using the low-precision floating-point
capabilities of modern GPUs to accelerate linear programming (LP), with plans to
extend these techniques to other solver algorithms. We combine GPU computation
with independent validation and exact certification.

We implement key ideas from OpenAI's
[Strongly Polynomial Linear Programming](https://github.com/openai/math/blob/main/preprints/Strongly-polynomial-linear-programming-November-24-2026/paper.pdf)
with engineering optimizations for practical CPU/GPU execution. Our
[certified evaluations](docs/benchmarks/lp-sp-pricing-comprehensive.md) show faster
end-to-end solves than COPT on several tested synthetic LP families, including
dense-wide, square and unscaled tall problems, counting model preparation and
independent certification. These results use hybrid CPU/GPU paths with FP64
proposals; low-precision solver acceleration remains an active research direction.

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

## Certified LP benchmarks

Existing results for our engineering-optimized implementation of the paper's
ideas on synthetic dyadic LPs, using an Intel Xeon Platinum 8457C, an NVIDIA
RTX PRO 6000 Blackwell Server Edition, COPT 8.0.6 and four CPU slots.
Cells show **median complete seconds (timely certified runs / 3 attempts)**,
including model preparation, solving and independent certification. A dash
means no timely certified result; lower times are better.

| Family | Nonzeros | Ours | COPT GPU | COPT CPU auto |
| --- | ---: | ---: | ---: | ---: |
| Dense-wide | 1M | 1.527 (3/3) | 2.469 (3/3) | — (0/3) |
| Dense-wide | 4M | 3.281 (3/3) | 4.782 (3/3) | — (0/3) |
| Sparse-wide | 1M | 3.268 (3/3) | 3.819 (3/3) | — (0/3) |
| Mixed-square | 1M | 1.875 (3/3) | 2.786 (3/3) | 5.229 (3/3) |
| Dense-square | 4M | 5.186 (3/3) | 63.701 (1/3) | 35.161 (3/3) |
| Banded-square | 4M | 8.691 (3/3) | — (0/3) | — (0/3) |
| Irregular-square | 1M | 6.480 (3/3) | 16.250 (2/3) | — (0/3) |
| Scaled-square | 1M | 2.727 (3/3) | 23.552 (1/3) | — (0/3) |
| Mixed-rectangular | 1.5M | 2.493 (3/3) | 2.802 (3/3) | 13.659 (3/3) |
| Mixed-tall | 1M | 2.216 (3/3) | 2.369 (3/3) | 52.094 (1/3) |
| Mixed-tall | 4M | 3.742 (3/3) | 4.438 (3/3) | — (0/3) |
| Mixed-tall | 16M | 11.579 (3/3) | 14.765 (3/3) | — (0/3) |
| Mixed-scaled-tall | 1M | 2.770 (3/3) | 2.431 (3/3) | — (0/3) |
| Mixed-scaled-tall | 4M | 5.408 (3/3) | 4.446 (3/3) | — (0/3) |

COPT GPU uses PDLP with presolve and crossover disabled; COPT CPU uses its
automatic method. Medians cover each lane's timely certified runs, so rows with
different success counts do not represent matched speedups. The scaled-tall
rows are from the fresh evaluation; other rows retain their documented cohorts.
See the [full report](docs/benchmarks/lp-sp-pricing-comprehensive.md) for solver
settings, certificate definitions, individual timings and limitations.

## Project navigation

- [Comprehensive LP implementation and COPT performance report](docs/benchmarks/lp-sp-pricing-comprehensive.md)
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
