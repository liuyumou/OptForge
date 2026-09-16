# Agent Instructions

Implement one dependency-ready bounded task at a time. Follow
[CONTRIBUTING.md](CONTRIBUTING.md), accepted specifications, and ADRs.
Update state/active-task.md before work and record acceptance evidence afterward.
Read state/known-failures.md before implementing related behavior.

M1, C1, C2, C3, C4, C5, C6 and C8 are complete and specified. C6 was heterogeneous
computation and GPU feasibility, specified as
[SPEC-0010](docs/specifications/SPEC-0010-heterogeneous-computation.md) for device
selection, residency, batching, arithmetic width, fallback, cancellation, recovery and
the batched integer schedule evaluator, and
[SPEC-0011](docs/specifications/SPEC-0011-gpu-lp-backend.md) for the GPU linear
programming backend. Both are implemented with evidence: a search can register a
device-backed candidate producer and re-execute from the record it writes, and
`optimizer solve --backend host-lp|cuda-lp` runs a first-order linear programming
method whose dual bound comes only from a host-side certification. The next capability
is C7, adaptive portfolios, which has no specification yet and needs one before any
behavior. The user has prioritized the separate
[GPU LP precision research track](docs/plans/gpu-lp-precision-roadmap.md) before C7;
follow `next_ready_task` in state/backlog.yaml and implement one GPUP slice at a time.
SPEC-0013 is accepted and GPUP-2 implements the bounded LP study and baseline report.
SPEC-0012 is accepted for implemented GPUP-3 shared resumable FP64 control. The
opt-in cuda-lp-matched backend and measured overhead repairs preserve legacy cuda-lp.
GPUP-4 adds explicit experimental cuda-lp-tuned under ADR-0017, with the preserved
first round and complete ADR-0018 correction documented in
[the report](docs/benchmarks/lp-tuned-fp64-gpup4.md). Matched remains the general
reference; scoped provisional fusion results are not supported presets. GPUP-5
is next and requires its precision interfaces before behavior. Read the
[GPUP-5 interface handoff](docs/plans/gpup5-interface-handoff.md): preserve existing
identities/replay and resolve one versioned experimental precision interface before
adding another backend name. This is a recommendation awaiting contract acceptance.
Later precision requirements remain pending. Carry forward 902.574545061 campaign GPU seconds,
including the earlier 445.988045904 and GPUP-4's 456.586499157; never reset the
ledger or archived evidence. GPUP-4's cumulative ceiling was 1345.988045904 seconds.
GPUP-1 repairs certification and objective/gap arithmetic; preserve its independent
exact-rational regressions before introducing lower precision. The initial
experiment campaign is capped at eight GPU-hours. Repeated-solve throughput
and full MILP search performance are separate future directions.
Unsafe CUDA code is permitted only inside optimizer-cuda-sys under
[ADR-0009](docs/decisions/ADR-0009-cuda-driver-boundary.md), which amends ADR-0003's
single-boundary rule; optimizer-cuda keeps the prohibition and keeps discovery and the
lease. A device never holds mathematical authority:
[ADR-0010](docs/decisions/ADR-0010-certified-gpu-lp.md) requires every bound to come
from a host-side certification that does not assume the device computed correctly.
`optimizer-lp` holds that certification and the method, takes no device dependency, and
is the oracle the kernels are differentially checked against; `optimizer-lp-cuda`
depends on it and never the reverse. Neither is a fallback: a fallback is the pinned
HiGHS adapter, because SPEC-0010 requirement 23 requires one to be the implementation
the project already treats as authoritative.
The C8 local extension registry is implemented under SPEC-0009 and ADR-0008;
it resolves a named extension identity to an extension this build provides and
deliberately does not load dynamically distributed native components, which would
need a boundary ADR-0009 does not authorize either. The Python SDK (C9) and the
comparative experiment runner (C10) are unspecified, and
[known failures](state/known-failures.md) records each blocker along with the C8
requirements whose acceptance tests are thinner than SPEC-0009 describes. Later
SDK and comparative-runner APIs require their own specifications and
acceptance gates; do not introduce them without one.
Use Rust for runtime work; Python under tools/ is build and validation tooling,
not the SDK. Native HiGHS code is permitted only inside optimizer-highs behind its
private ownership boundary, with the pinned 1.11.0 CPU contract, and CUDA driver
calls only inside optimizer-cuda-sys. Those two crates declare their own lints
because a workspace-level unsafe prohibition cannot be relaxed per crate; every
other runtime crate keeps the prohibition, and no third boundary is authorized.

Run bash tools/check.sh for acceptance; it requires the pinned native HiGHS build.
AI_OPTIMIZER_SKIP_NATIVE=1 skips it and reports uncovered native acceptance, which
must never be recorded as a full gate pass. Discovering GPUs does not authorize a
kernel workload; all actual project GPU jobs require the shared host lock, and the
lock permits one holder across device selections, so two devices are never used at
once. nvcc is a provisioning dependency, never a build dependency: an ordinary
cargo build must keep working on a host with no toolkit and no device.
Do not change experiment seeds, thresholds, splits, or defaults silently.
Do not publish, push, or configure external hosting without authorization.
