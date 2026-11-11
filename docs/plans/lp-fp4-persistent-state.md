# Persistent multi-FP4 iterations: feasibility and proposed gates

Status: amended design, 2026-11-11; independent GPU pilot next; future 1e-7/1e-9 final tiers; old prototype attempt closed
Owner: numerical backend and CUDA runtime
Last reviewed commit: 59ae62d872b30885a57e02412b1f44478769ef16
Decision: [ADR-0055](../decisions/ADR-0055-persistent-fp4-direction.md), [ADR-0058 amendment](../decisions/ADR-0058-fp4-gpu-exploration-quality-tiers.md)
Implementation: [SPEC-0025](../specifications/SPEC-0025-persistent-fp4-contract.md); [roadmap](gpu-lp-precision-roadmap.md#persistent-multi-fp4-direction-2026-11-11), [backlog](../../state/backlog.yaml)
Acceptance: [CPU contract delivery](../benchmarks/lp-fp4-spec-gpup-fp4-spec.md); device gates below

Implementation update (2026-11-11): the CPU contract is now
[SPEC-0025](../specifications/SPEC-0025-persistent-fp4-contract.md), accepted under
[ADR-0056](../decisions/ADR-0056-fp4-executable-contract.md). Its
[delivery report](../benchmarks/lp-fp4-spec-gpup-fp4-spec.md) contains executable
oracles, strict validation, the frozen comparison/resource proposal and retained
cost bounds. The subsequent [prototype attempt](../benchmarks/lp-fp4-proto-gpup-fp4-proto.md)
qualifies no lane: nine error-guard and three metadata refusals among twelve CPU
cells. No observation boundary or device stage was reached. A separate local
error-budget correction has primitive tests only. That v1 attempt remains closed.
The user-authorized ADR-0058 amendment now makes FP4-GPU-PILOT next, independent
of CPU recovery and the failed 600-update gate. Correct primitives and device
safety precede exploratory profiling; solver integration and complete-cost
admission precede certified comparison. This document plans those experiments;
their concrete protocols/resources are prepared when their tasks begin.

## Assessment and user-selected semantics

This is a worthwhile bounded research direction. The user explicitly accepts
approximate inner iterations with original-model FP64 residual checks. They now
also accept a separately labeled 1e-7 final certificate if FP4 is sufficiently
faster; 1e-9 remains the strict final tier. A short FP4 expansion therefore need not emulate
every binary64 operation or preserve the native trajectory. Its component count
must follow an error/cost contract, not the assumption that four FP4 bits supply
four useful significand bits or that several components automatically equal FP64.

The principal opportunity is removing repeated full-vector reconstruction and
encoding while fusing the surrounding work. Changing only the Tensor instruction
format would leave the earlier bottleneck in place. In the retained expanded
INT8 profile, reconstruction took 3.906 s, vector updates 0.844 s and the Tensor
main product 0.0677 s. These are instrumented observations, not a performance
forecast for this design. [Retained diagnosis](../benchmarks/lp-system-diagnosis-2026-11-10.md#latest-measured-bottleneck)

## Hardware and research evidence

E2M1 has a sign, two exponent bits and one fraction bit, with maximum magnitude
six. NVFP4 combines it with an E4M3 scale per 16 elements and a global FP32 scale;
MXFP4 uses a different block/scale contract. Neither scale convention supplies
full FP64 range or precision automatically. Specify the actual representation,
including exponent metadata and outlier treatment. [NVIDIA format description](https://docs.nvidia.com/deeplearning/transformer-engine/features/low_precision_training/nvfp4/nvfp4.html)

The CUDA 13.0 PTX ISA exposes block-scaled E2M1 `mma.sync` with FP32 accumulators
for the RTX Blackwell instruction family. It leaves accumulation order, rounding
and subnormal handling unspecified for these alternate floating types. Pin the
compiler, legal architecture-specific/family target and emitted instructions;
the repository's existing `sm_120` build does not admit a new FP4 opcode. Do not
substitute an SM100 `tcgen05` example for an SM120 implementation or infer exact
dot products from FP32 accumulation. [Versioned PTX ISA](https://docs.nvidia.com/cuda/archive/13.0.0/parallel-thread-execution/index.html#warp-level-matrix-instructions-mma)

A 2026 preprint demonstrates base-13 E2M1 component products and FP4 Ozaki
schemes on RTX PRO 6000 Blackwell. Its fused implementation is competitive with
FP8 DGEMM emulation at large sizes, but still reconstructs outputs. Its dense
matrix-matrix workload and timings excluding host/device transfer do not establish
sparse LP iteration performance or persistent-state correctness. It is evidence
that multi-FP4 products are practical, not an acceptance receipt for this design.
[Hayashi et al., arXiv:2608.06812v1](https://arxiv.org/html/2608.06812v1)

## What reconstruction-free means

The proposed fast path keeps primal, dual, extrapolated state and restart anchors
as scaled component arrays across ordinary inner updates. It has no full FP64
state reconstruction/re-encoding pass per update and no separate full FP64
product buffer between a product and its fused update. Necessary partial
reduction buffers remain explicit and charged.

FP32 accumulators, bounded local component combination, normalization, carry or
residual handling, comparisons and FP4 re-encoding remain necessary work. Count
them explicitly. Collapsing every expansion into one FP32 scalar and then splitting
it again loses information; it is a distinct approximation with an error bound,
not a way to preserve arbitrary expansion precision. A persistent compensation
sidecar, if needed, is a separately named variant with charged bytes and operations.

FP64 snapshots are allowed at the existing 200-update host controller boundaries,
final export and explicit escalation. On an accepted observation, retain the
component state rather than replace it with an FP64 reference iterate. Snapshot
rounding must be covered by the audit contract. This changes the historical
reference-adoption policy and requires a new numerical specification; it is not
an edit to [ADR-0046](../decisions/ADR-0046-expanded-audit-window-state.md).

## Proposed representation and update path

Write the approximate matrix and state conceptually as
`A_hat = sum_i S_A,i * Q_A,i` and `x_hat = sum_j S_x,j * q_x,j`, with FP4 component
arrays and explicit block/plane scales. Retain the original matrix separately.
Scale notation is schematic: block indices and shared contraction-axis scales
must be defined before factoring them through a matrix product. Prefer a
power-of-two plane hierarchy as the first design to analyze; NVFP4 residual planes
and base-13 limbs are alternatives with different conversion/normalization costs.

1. Prepare immutable matrix components once per declared lifecycle, including
   both operator orientations and sparse-tail routing. `A*x` and `A^T*y` must
   use a consistent approximate operator, or explicitly bound their adjoint
   mismatch; independently quantizing the two orientations can change it.
2. Compute selected component-pair products in Tensor tiles with bounded FP32
   accumulator groups. Preserve significant low groups until their combination
   or truncation is covered by the contract. FP4 operands do not require FP4
   accumulators. Arbitrary coefficients, step sizes and Halpern weights also
   need a declared representation and error cost. The error argument must cover
   the admitted MMA semantics; do not assume a round-to-nearest accumulation
   model where the ISA leaves it unspecified.
3. Fuse product completion, scalar update, projection decision, normalization,
   error/sticky-status update and encoding of the next component state where
   dependencies permit. Keep unavoidable inter-tile reduction buffers explicit.
   Packed FP4 writes need non-overlapping ownership and sanitizer coverage.
4. Preserve the dependency `A^T*y -> new x/extrapolation -> A*x_bar -> new y`.
   Start with separate ordered primal and dual phases. A single persistent
   kernel across arbitrary matrix-wide updates would need a valid grid-wide
   synchronization/residency design; a block barrier is insufficient. Fusion is
   not permission to omit the reduction or consume an incomplete vector.
5. Use observation-only FP64 snapshots for the original-model controller and
   residuals at 200 updates. Define how restarts encode anchors, change scales
   and reset error metadata without silently replacing all component state.
   Checkpoints include every component, scale, compensation/error field and
   controller/generation value. Refusal/cancellation restores the whole checkpoint;
   explicit native conversion/replay and all attempted work remain charged.

## Numerical issues that decide feasibility

Projection does not distribute over components. For example, components `1` and
`-0.5` represent `0.5`; clamping each to `[0,1]` and adding produces `1`, whereas
clamping their sum produces `0.5`. Compare the combined value or a sound interval
with the bounds. An ambiguous boundary needs more component inspection, a charged
higher-precision exceptional path or escalation. Preserve symbolic infinities.

Cancellation, large dynamic ranges, shared-scale outliers and tiny updates can
erase progress even when each product appears accurate. Specify rescaling,
normalization frequency, tail accumulation, nonfinite/underflow refusal and an
error-feedback policy. A fixed low-precision operator can converge to the wrong
problem; periodic original-model residual checks must drive explicit correction,
component escalation or native recovery. A strict final certificate alone does
not establish convergence of the approximate iteration or justify unchecked
cross-window error growth.

Under ADR-0058, a bounded GPU pilot may measure empirical local/trajectory error
before a full trajectory enclosure is available. It must label that limitation
and cannot claim solver qualification from kernel measurements. CPU recovery may
select a proved coupled bound or a separately specified operational residual
guard; the latter claims no rigorous iterate-error enclosure. Integration must
validate its progress, refusal and recovery behavior, with independent final
checking as the certificate authority. This avoids making the failed monotone
bound a universal prerequisite for learning about the hardware.

As one accounting identity, if `A = A_hat + E_A`, `x = x_hat + e_x`, and the
computed product is `p = A_hat*x_hat + e_compute`, a compatible norm gives
`||A*x - p|| <= ||E_A||*||x_hat|| + ||A||*||e_x|| + ||e_compute||`.
The specification must cover scale quantization, omitted pairs, accumulation,
normalization, projection, scalar coefficients and cross-window propagation in
these errors. This identity is not a convergence theorem or a selected budget.

Use an independent high-precision/exact CPU oracle for primitive cases and long
trajectories: alternating cancellation, tiny progress near active bounds,
outliers, underflow, finite/infinite bound combinations, restarts, rollback and escalation.
For a solver cohort, test the actual returned FP64 snapshot independently at its
declared 1e-7 or 1e-9 final tier, using the same original-model feasibility/gap and
bound-authority rules with explicit absolute/relative target tolerances. This
final tolerance is unrelated to the old 1e-7 inner-error guard. The mixed-65536
bound-authority refusal remains unresolved and cannot be counted as a speed win.

## Work, memory and useful Tensor utilization

With `k_A` matrix planes and `k_x` vector planes, a direct full expansion requires
`k_A*k_x` logical component products: four by four gives 16, eight by eight gives
64. Fusion removes some launches and intermediate writes; it does not eliminate
those products. Truncating pair groups requires an explicit error enclosure.
An illustrative CPU design grid can compare 2, 4 and 8 planes without claiming
any fixed number of accurate bits; the actual grid is frozen by the future spec.

Packed components alone cost `k/2` bytes per scalar, before scales, padding,
indices, scratch, checkpoints and any FP32 compensation. Four planes therefore
cost two bytes and eight planes four bytes before overhead. Count the retained
original FP64 matrix and both orientations as well. A storage saving is not a
memory-bandwidth saving unless the executed access pattern realizes it.

Compare against a matched FP8/FP16 component design as well as native FP64, at
matched error/progress requirements. For illustration, if FP4 needs four planes
per operand where FP8 needs two and hardware FP4 throughput is twice FP8, full
pair expansion has a compute-only speed ratio of `2 * 4/16 = 0.5` before other
costs. This is a conditional calculation, not a measured precision equivalence.

Start with dense-block coverage large enough to amortize layout work. A single
LP matrix-vector product has little reuse across right-hand sides, unlike a large
GEMM; include tile padding, sparse tails and unused output columns. Component
planes may fill spare columns but remain charged component work. Independent
LP batches are a separate throughput cohort; sequential iterates are dependent
and cannot be counted as independent right-hand sides.

Profile logical useful products, physical MMA operations, encoding/normalization,
exceptional paths, audit/correction, launches, copies/bytes, register use, spills
and occupancy. Compare whole fused iterations before a solve campaign. Use
[ADR-0054's complete-cost model](../decisions/ADR-0054-resident2-cost-priorities.md),
including changed iteration counts and cold preparation/checker cost. Require the
prospective TENSOR2 complete-path screening before its campaign; it does not
block the exploratory pilot that supplies missing measurements. The initial
retention target is at least 1.10x cold model-median geometric-mean speedup, no
certified model-median regression and no loss of coverage against a native
control targeting the same final tolerance. Report uncertainty and all failed
rows. Kernel throughput or prepared throughput alone cannot satisfy this target;
FP4 at 1e-7 versus FP64 at 1e-9 is a separate quality/time tradeoff.

## Roadmap and stop decisions

| Stage | Deliverable | Gate before proceeding |
| --- | --- | --- |
| **GPUP-FP4-SPEC**, complete, CPU-only | SPEC-0025 implements the representation/error/transaction/cost contract and frozen proposal | 32 focused CPU contracts and full native gate pass; no actual MMA or forecast admission |
| **GPUP-FP4-PROTO**, incomplete, CPU attempt closed | Independent reference and component trajectories implemented; twelve-cell admission qualifies no lane | Nine guard/three metadata refusals; no 200-update observation; actual instructions, device implementation, sanitizers and profiles unexecuted |
| **GPUP-FP4-GPU-PILOT**, next ready | Actual FP4 products and fused persistent iterations, bounded empirical errors and profiles; matched controls and ablations | Concrete protocol/resources; CPU primitive and actual-instruction/device/sanitizer admission; independent of the failed 600-update trajectory gate and full-solve forecast |
| **GPUP-FP4-RECOVERY-SPEC**, independently ready, CPU-only | Correct local budgets and specify an enclosure or explicit operational residual guard, precision and recovery | Versioned numerical contract; separate proved bounds from empirical progress; original-model FP64 checks and declared final-quality tier |
| **GPUP-FP4-INTEGRATE**, after both paths | Implement and validate the new solver policy and device candidate | Nontrivial trajectories, full checkpoint/recovery/cancellation and final endpoint admission; 1e-7 success need not also reach 1e-9 |
| **GPUP-TENSOR2**, conditional study | New frozen matched native/FP8/FP16/FP4 cohorts at explicit 1e-7 and 1e-9 final tiers | Integration and complete-cost gates; same-tolerance controls, latency/coverage/uncertainty rules, full costs/failures; old strict 192-cell proposal remains exact |

The user prioritizes the FP4 feasibility contract ahead of generic MIXED2 work.
MIXED2 remains a simpler alternative and is not a prerequisite for FP4 planning.
DELIVERY2 remains available when delivery overhead offers the better cost case.
No held-out access, GPUP-8 retry, GPUP-9 release or supported preset follows.
This review allocates no CPU/GPU resources to future arithmetic tests, device
prototypes or studies; each needs a concrete separately accepted envelope.
