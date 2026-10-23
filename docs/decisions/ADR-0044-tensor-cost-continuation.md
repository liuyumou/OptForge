# ADR-0044: Bounded Tensor cost and CPU admission continuation

Status: proposed, 2026-10-23; implementation and new GPU cells require acceptance.
Owner: numerical backend and experiment tooling.
Introduced: GPUP-8 latency follow-up.
Last reviewed commit: bootstrap (parent 6521c3a).
Supersedes: ADR-0043 only for a separate future continuation; history unchanged.
Superseded by: none.

## Context

The user requests a diagnosis and bounded completion plan, including a CPU
admission repair. [The CPU-only diagnosis](../benchmarks/lp-tensor-latency-diagnosis.md)
finds useful Tensor solves but no latency gain: INT8 is 0.614776/10.390881 seconds
against tuned FP64's 0.462114/6.331022. Most of the gap also occurs with
policy-matched FP64. Conservative step restriction, generic preparation and host
reference audits dominate the actionable large-model costs. The previous CPU
admission/build overlap has no aggregate concurrency/RSS receipt.

This proposal adds no resources. It is a bounded attempt to satisfy the existing
completion criteria, not a promise of a speedup or permission to continue after
a failed gate. Acceptance must explicitly include the prospective disposition
of the historical CPU resource limitation described below.

## Decision: one fixed package, in dependency order

Use separate identity `lp-tensor-cost-v1`, campaign `gpup-tensor-cost-v1`, new
request/evidence schemas, sources, CPU cohort, executable, image, workers and
reports. Freeze the numerical implementation, controls, resource limits, seeds,
complete roster and order before any device identity. Historical sources/images,
workers/payloads/reports and all 17362 ledger events remain byte-identical.

### 1. Repair CPU resource admission before preparation

Implement one task coordinator with a project-wide exclusive admission lock.
Every compiler, proof, admission process, verifier, check, GPU worker and reporting
child of this continuation runs beneath it. A second coordinator refuses or
waits without starting work. Child launches require atomic weighted slot and
memory reservations; no two top-level phases overlap. A four-job build owns
all four work slots; an admission pool may own at most four single-thread slots.
Explicitly configure Cargo/CMake/test/Rayon/BLAS/OpenMP/nvcc worker counts;
descendants inherit CPU affinity and the task enclosure. Coordinator/monitor
CPU and RSS are included even though they are not additional work slots.

Preflight requires a delegated cgroup v2 task subtree: inherited cpuset of at
most four CPUs, CPU quota at most four cores, `memory.max=8589934592`, no swap
escape, complete descendant membership and authoritative aggregate `cpu.stat`
and memory-peak/event accounting. Work-slot limits are enforced separately;
CPU quota alone does not stop eight queued workers. Put every child into the
enclosure before allowing it to execute. Use an atomic start handshake, durable
reservation journal and retained per-stage receipts. The current container's
cgroup controls are read-only, so delegated containment must be provisioned and
validated by the host before this stage can pass. Do not silently fall back to
the existing per-tree sampler. If delegation is unavailable, retain a CPU
admission refusal and stop before preparation/device reservations.

Reserve each stage's CPU time against the **remaining cumulative** cap before
launch, including final acceptance/reporting reserves. Poll aggregate CPU usage
and process-tree RSS at most 10 ms apart; retain aggregate memory peak and OOM
events. Stop below the CPU cap with a margin covering four cores times the
sampling/termination bound; include that margin in the stage reservation.
Freeze/kill and reap the whole enclosure on limit, cancellation, lost monitor or
coordinator failure. If accounting is incomplete, charge the full reservation
and refuse subsequent work. Require an empty enclosure before releasing slots.
Never reset the ledger or infer completion from child exit alone.

CPU-only tests cover concurrent coordinators, a build plus admission request,
grandchildren/thread-spawned children, cumulative exhaustion across sequential
jobs, memory-limit events, failed entry/telemetry, SIGTERM/SIGKILL, orphan cleanup
and stale reservation recovery. Receipts bind source, command, executable,
configured/peak work slots, aggregate CPU delta, memory peak/events and status.
No missing aggregate observation can be recorded as passed. These tests and the
delegation preflight spend only the CPU reservation below, zero GPU seconds.

### 2. Remove shared costs without relaxing numerical budgets

Implement the following fixed package; do not conduct a parameter sweep.

1. **Compact fresh preparation.** Construct immutable Tensor metadata directly
   from the canonical scaled CSR/CSC input. Reuse indices within this solve;
   compute coefficient enclosures and tile groups once, eliminating the full
   generic quantization object followed by duplicate Tensor construction.
   Compare canonical indices, represented coefficients, bounds, promotion masks
   and replay inputs bitwise against ADR-0043. No cross-solve cache or session.
2. **Tighter certified norm.** For a matrix whose selected 32x32 tiles are
   disjoint in block rows and block columns, write its represented target as
   `M = D + R`. Bound each dense block with an outward interval Gram matrix:
   `||D_b||_2 <= sqrt(max_i sum_j |(D_b^T D_b)_ij|)` using interval absolute
   upper endpoints and upward sums/square roots. Then
   `N_M = max_b N_b + sqrt(||R||_1 ||R||_infinity)` bounds the full represented
   matrix. Build a nonnegative coefficient-error envelope E covering both the
   exactly scaled original matrix and the native FP64 matrix relative to M;
   `N = N_M + sqrt(||E||_1 ||E||_infinity)` bounds all three target operators.
   Include rounding, subnormal and overflow cases explicitly. Use the smaller
   of this proved bound and the existing proved bound; otherwise fall back to
   the latter. Step is at most both the original engine step and downward
   `0.9/N`. No power-iteration estimate alone can authorize a larger step.
   Admission depends on layout, never model name. Cap Gram work at 2048 blocks
   and 67108864 scalar product terms per model; stream one block at a time.
   Include its full setup time in every solve. Prove the corrected product is
   M*x plus the existing bounded arithmetic error before using this norm.
3. **Equivalent device reference audit.** Compute the final pre-window FP64
   reference update on the device in the exact host oracle's multiplication,
   serial sum, projection and update order; prohibit contraction/reassociation.
   Keep resident FP64 state and the 32-update audit/adoption schedule. Compare
   reference and candidate in the same original-unit 1e-7 absolute/relative
   budget, with checked finite/range behavior and conservative decision bounds.
   Preserve whole-window rollback, charged reference work/replay, uniform sticky
   promotion, cancellation and checkpoint/session ownership. Validate all audit
   decisions and adopted binary64 endpoints against the independent CPU oracle.
   Final 1e-9 original-model certification remains freshly executed on the host
   at the existing 200-update boundaries and at delivery. Report device audit
   work and transfers separately from useful Tensor work.

Keep ADR-0043's exact x=x0+xr split, 56-bit component products, deterministic
FP64 residual correction and original-unit error enclosures. No component
truncation, residual omission, tolerance change, delayed assessment, refinement,
FP8, stochastic rounding, Tensor-only certification or public default is allowed.
Do not add speculative kernel fusion/graph/session work to this bounded package.

### 3. CPU admission, then device correctness, then cost admission

Before any device reservation, pass independent Fraction/integer tests of the
unchanged component arithmetic, new norm enclosure and layout/transposition;
compare compact preparation against the historical oracle on all eight inherited
models. Preserve all refused shapes/numerical cases. Require complete useful
400-update trajectories on both dense models for INT8/FP16/BF16/SIMT, plus matched
controls; exact host comparisons cover controller, reference adoption, failure,
promotion and whole-window replay. No successful short trajectory implies a
certified full solve. Charge all CPU preparation and verification.

Pass the full pinned-native `bash tools/check.sh` before freezing device work.
The new image must show actual IMMA/HMMA, at most 128 registers and zero spills.
Device acceptance retains all 66 ordinary tests, at least the existing 280
product pairs (augmented for the norm/audit path), five controller comparisons,
twelve actual-model fixed-work/replay pairs and all four scoped sanitizers.
CPU admission and resource receipts must bind the exact source/executable/image.
If any reservation or validation fails, preserve the attempted identity and
stop; no retry, alternate source cohort, device substitution or replacement cell.

Run the 16 frozen diagnostic profiles below before primary timings. Collect
disjoint host phases and scoped CUDA-event durations for norm/packing, MMA,
reconstruction/correction, native remainder, guards, updates and reference audit.
Instrumentation overhead is charged and excluded from primary timing kernels.
Actual unchanged tuned diagnostics must use its own CLI/backend and packing path.
That backend stops at a certificate even in profile mode: its two diagnostics
therefore measure time-to-certificate with raw phase instrumentation, and must
certify. The other ten primary profiles and four ablations require exactly 2000
logical updates. Use policy-matched FP64 for equal-work attribution; do not call
the tuned diagnostics 2000-update comparisons or substitute the research wrapper.

Freeze a conservative cost forecast before reading these new profiles: for each
candidate, add measured preparation/context/upload, cumulative per-boundary solve
cost through its first fresh host certificate, measured final host certificate,
and the largest measured producer tail/output cost across the profiles. No
overlapping envelope may be counted twice or negative residual cost admitted.
Continue to timings only if all required profiles complete and verify, each
arithmetic family has useful work on both models, and at least one Tensor forecast
is <=90% of the retained tuned median on one of the two models. The forecast is
an early resource-saving screen, not evidence of a speedup. If no certificate
occurs by 2000 updates, that candidate has no admissible forecast. Do not change
source, thresholds, configurations or roster after examining the profiles.

## Frozen comparison and GPU reservations

Keep the inherited two dense models, eight-model CPU cohort, six configurations
(INT8, FP16, BF16, represented SIMT, policy-matched FP64, unchanged tuned FP64),
five fresh-process repetitions, ordering seed 17001, and all six predeclared
Tensor-vs-tuned comparisons. The matched controls use the new norm/audit policy.
Pair each candidate with the unchanged tuned repetition of the same model.
BF16 remains in the family and multiplicity even if INT8/FP16 appear promising.

| Phase and cells | Per-job solve deadline + overhead | Maximum GPU s |
| --- | --- | ---: |
| 60 primary timings: 6 configurations x 2 models x 5 | 5+6 s at 1024; 16+6 s at 65536 | 990 |
| 12 primary profiles: 5 research configurations x 2 models at 2000 updates; 2 actual tuned time-to-certificate profiles | 6+6 s at 1024; 18+6 s at 65536 | 216 |
| 4 ablations: INT8/FP16 at 65536, one retaining old norm and one retaining host audit | 20+6 s, forced 2000 updates | 104 |
| 66 ordinary device tests, one job | 60+6 s | 66 |
| New project differentials/replay, one job | 180+6 s | 186 |
| memcheck / racecheck / initcheck / synccheck | 40+6 / 100+6 / 40+6 / 40+6 s | 244 |
| **Total** | Screening 990; ablations 320; repeatability 496 | **1806** |

The six seconds cover admission, teardown and accounting overhead under the
existing allocator. Reserve full per-job caps, even if observations suggest
shorter runs. Actual leased time settles each reservation; failed telemetry
charges the full reservation. No additional microbenchmark cells are allowed;
product diagnostics are part of the project correctness job. There are 76 study
cells and six acceptance jobs, each attempted at most once. The shortened
deadlines belong solely to this new protocol and leave old cells unchanged.

Starting task charges in screening/ablations/repeatability are respectively
415.105235119 / 90.046073299 / 319.962723857 GPU seconds. Remaining allocations
are 1184.894764881 / 459.953926701 / 530.037276143 seconds. The proposal fits each
without transfers, leaves 368.885967725 task seconds unreserved, and cannot
exceed task total 2631.114032275 / 3000 or campaign 23990.699888064 /
25202.574545061. Keep the independent 28800-second ceiling and campaign phase
caps 1800/11800/8100/5300/9000 unchanged. Device remains exclusively
`GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48` under shared host admission.

## CPU and memory reservation

After charging the diagnosis 400 CPU seconds, prior conservative accounting is
19534.822845162 / 21600. Reserve at most **2050 additional CPU seconds**:

| Stage, including its children | CPU s cap |
| --- | ---: |
| Resource coordinator/preflight/tests and incremental compilation | 250 |
| Independent proofs, compact-layout comparison and eight-model CPU admission | 550 |
| Pre-device and final full pinned-native acceptance | 550 |
| All leased GPU-worker CPU, monitoring and independent endpoint verification | 550 |
| Report, preservation checks and local delivery | 100 |
| Supervisor/termination accounting margin | 50 |
| **Total** | **2050** |

Each stage cap is a hard reservation, not a predicted success time. No borrowing
across stage caps is implicit. Freeze CPU stage order, commands, pool widths and
limits before execution. Before starting another stage, reserve all remaining
mandatory acceptance/delivery work as well. If actual code or proof work cannot
fit, stop on CPU with no study attempt. In particular the earlier conservative
`8 x leased wall time` estimate would consume too much CPU allowance here;
complete aggregate CPU accounting is essential, not optional bookkeeping.

Maximum cumulative CPU accounting would be 21584.822845162 / 21600 seconds.
Keep four aggregate work slots, 8 GiB aggregate RSS, 2 GiB preparation, 1 GiB
device buffers and 32 GiB combined artifacts. Every new process and retained
artifact counts, including refusals and monitoring. No old reserves are reclaimed.

## Completion, refusal and historical resource disposition

Completion requires all new software/numerical/device/resource gates; useful
INT8 and at least one FP16/BF16 nontrivial certified solve; all five repetitions
certifying with no coverage loss against tuned on either timing model; and at
least one paired **total-latency** bootstrap speedup interval excluding one after
Bonferroni adjustment across six comparisons at 95% family confidence, 10000
resamples, seed 17002. Independently verify every retained endpoint, including
failed or interrupted records when available. Native promotion, residual-only
work, host-only initial certificates, microbenchmarks and forecasts cannot win.

Retain the original unrecorded concurrency/RSS overlap as **not certified**.
Passing new source-bound preparation and the complete eight-model CPU cohort
under the repaired coordinator supplies prospective admission for this new
implementation only. Acceptance of this ADR authorizes that remedial disposition
for completion; it does not assert historical compliance or alter old reports.
If the new resource cohort cannot certify, GPUP-8 remains incomplete regardless
of a latency result. A refusal or no gain ends this bounded experiment; leftover
time does not authorize another version, new cells, retries, GPUP-9 or presets.

## Alternatives and consequences

MMA-only tuning has little measured large-model headroom. Reusing preparation
across solves would change the endpoint. Copying tuned's step or deleting audits
would weaken the accepted numerical contract. Removing BF16 after observing its
cost would change the predeclared comparison family. Additional assessment
scheduling or refinement would expand the interaction contract and scarce CPU
work. These are outside this proposal.

The fixed package has a plausible path to a win by removing shared overhead and
reducing work amplification, but the new Gram bound has setup cost and may still
restrict the step; a serial device reference audit may also be expensive. The
CPU and cost gates deliberately permit a documented refusal. No guaranteed
GPUP-8 completion is inferred from the remaining GPU allowance.

## Implementation and acceptance artifacts

Likely implementation: a shared CPU admission coordinator with CPU-only failure
tests; isolated `tensor_cost` host/CUDA/experiment modules and image; strict new
request/evidence/protocol schemas; source-bound proof/admission/worker/report
tools; separate `artifacts/gpup-tensor-cost-v1` and
`docs/benchmarks/data/tensor-cost`. Keep source bridges for registration-only
changes and source-only portability tests. Full `tools/check.sh` includes every
CPU/native/dependency/replay/docs/smoke command. Preserve the exact ledger prefix
SHA-256 `e1766490f8de2affa14f4f950afed18be7f69531c3c28eedfd74539fcc0d9db5`,
including the 17200/17132 prefixes and every historical source/image/worker/report.
Local commit follows applicable acceptance; publication and merge remain outside
this task. This proposed ADR reserves nothing until explicitly accepted.
