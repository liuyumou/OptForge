# SPEC-0025: Persistent multi-FP4 CPU contract

Status: accepted CPU specification; device arithmetic unadmitted
Owner: numerical backend and CUDA runtime
Last reviewed: 2026-11-11
Last reviewed commit: bootstrap
Decision: [ADR-0056](../decisions/ADR-0056-fp4-executable-contract.md)
Implementation: [numerical contract](../../tools/lp_fp4_contract.py), [proposal contract](../../tools/lp_fp4_protocol.py)
Acceptance: [CPU tests](../../tests/integration/test_lp_fp4_contract.py), [delivery](../benchmarks/lp-fp4-spec-gpup-fp4-spec.md)

## Purpose and scope

Specify approximate persistent FP4 iterations under original-model FP64 residual
checks and the unchanged 1e-9 final certificate. This slice implements CPU
oracles, strict artifact validation and cost admission. It implements neither an
LP solver nor a GPU executor. Passing these contracts authorizes no experiment
and establishes neither convergence nor performance. The historical native
control remains supported.

## Representation

1. Components MUST use E2M1 magnitudes `0, 1/2, 1, 3/2, 2, 3, 4, 6` with bit 3
   as sign. Working zero MUST be positive zero; original model bytes remain
   untouched. Two codes occupy each byte, earlier value in the low nibble; an
   unused final high nibble MUST be zero. A block has 1–1024 values and exactly
   2, 4 or 8 planes. Each plane has one integer binary exponent in [-48, 48].
2. The CPU encoder MUST greedily encode the residual, choosing the smallest
   exponent covering its largest magnitude with `6 * 2^e`. Exponents smaller
   than -48 clamp to -48; values exceeding `6 * 2^48` refuse. Nearest rounding
   ties choose the even magnitude code. Residuals are computed exactly; a reduced
   nonnegative rational records the maximum remaining absolute error. Tail
   underflow is charged to that error, never silently declared exact. This range
   deliberately does not represent arbitrary finite binary64 inputs.
3. Vector blocks MUST contain 32 padded values. Matrix blocks MUST be 32×32
   row-major tiles with one scale per tile per plane. Zero padding has no model
   semantics. Transpose preparation MUST permute the same codes and reuse their
   scales; independent transpose quantization is forbidden. Full original
   coefficients, sparse indices and dimensions remain separately retained.
4. The initial representation has no compensation sidecar. Low components MUST
   survive until an explicitly bounded rounding/truncation operation. Ordinary
   updates MUST NOT reconstruct a full FP64 vector or product buffer. Local
   combination, reduction, scalar operations, normalization and re-encoding are
   permitted only with declared error and charged cost. Adding a sidecar or
   expanding the exponent range requires a versioned variant.

## Products, updates and error envelopes

5. The proposed instruction is block-scaled `mma.sync.aligned.m16n8k64`,
   `.kind::mxf4`, `.scale_vec::2X`, E2M1 operands, UE8M0 scales and FP32
   accumulators, under a legal SM120 architecture/family target. The first
   mapping uses a 32-term contraction and zero-pads the other half of K64.
   Physical padding and single-RHS occupancy MUST be counted. Each component
   pair and 32-term group starts with zero accumulation; cross-group combination
   has a separate error term. No pair may be omitted without bounding it.
6. The CPU oracle proves the *mathematical* group is a multiple of
   `2^(e_A+e_x-2)` with integer magnitude at most 4608. The selected exponents
   keep these groups within finite normal FP32 range (apart from exact zero).
   This does not establish an instruction error bound. The pinned PTX ISA
   leaves relevant accumulation/rounding/subnormal behavior unspecified;
   actual emitted instructions, device behavior and an applicable arithmetic
   bound MUST be admitted before GPU iterations. An RN dot-product formula
   alone is insufficient. [CUDA 13.0 PTX ISA](https://docs.nvidia.com/cuda/archive/13.0.0/parallel-thread-execution/index.html#warp-level-matrix-instructions-mma)
7. With the original scaled operator A, its stored approximation H and an
   iterate enclosure `||x-x_hat||_inf <= E_x`, products MUST bound
   `||Ax-p||_inf <= ||A-H||_inf ||x_hat||_inf + ||A||_inf E_x + E_compute`.
   Transpose uses its own row-sum norm/error, derived from the same H. Scalar
   coefficient/objective rounding, MMA, group combination, projection decisions,
   normalization, encoding, discarded pairs and cross-window accumulation MUST
   all be included. Infinity norm matrix errors are row sums, not the largest
   individual coefficient error.
8. The reference transition MUST preserve the native dependency order:
   `A^T y -> projected u -> bar = 2u-x -> A bar -> dual prox v -> Halpern blend`.
   Extrapolation uses u before the blend. For positive steps tau and sigma,
   primal projection and `v = raw-clamp(raw,-sigma*upper,-sigma*lower)` are
   nonexpansive. The implemented recurrence propagates E_x/E_y through these
   operations, both anchors and all named local errors. Its comparison is to
   the mathematical map with the *same* coefficients/controller choices, not
   to the entire native solver trajectory. Original-unit errors MUST include
   the inverse scaling factors.
9. Projection MUST compare an enclosure of the combined expansion to the
   bounds. Componentwise clipping is forbidden. A decision straddling a bound
   returns `ambiguous`; the future executor MUST refine or fall back. Fixed
   bounds may collapse an enclosure. One-sided infinities are represented by
   absent lower/upper bounds; NaN and explicit infinite numeric values refuse.

## Observation, recovery and controller state

10. The cumulative original-unit relative error guard is `1e-7` for primal and
    dual enclosures, normalized by `max(1, ||snapshot||_inf)`. This is a research
    guard, not a final certificate tolerance. V1 takes the maximum of each prior
    E_x/E_y and its new recurrence bound; observation MUST NOT reduce these
    conservative cumulative enclosures. FP64 snapshot rounding MUST be added
    to the observation error.
    Over-budget/nonfinite/ambiguous states refuse. Future escalation proceeds
    2 -> 4 -> 8 components -> native, charging conversion and attempted work;
    the CPU contract does not implement those conversions.
11. Audit windows MUST end by 200 updates and at any earlier controller boundary.
    An accepted observation returns the candidate component state unchanged.
    The CPU transaction helper only checks the declared enclosure and transaction;
    it cannot prove that an executor supplied every local error term, and it
    cannot certify optimality or replace an independent original-model checker.
    Anchors and controller fields MUST remain unchanged before observation,
    apart from iteration counters. The unchanged controller observes snapshots and may update its own fields
    or restart anchors through an explicit transition. Three consecutive audits
    without a 10% reduction in the controller's normalized residual trigger
    escalation. Certified completion takes precedence over this progress rule.
12. Checkpoints MUST include x, y, extrapolation, both restart anchors, every
    packed plane/scale, representation and accumulated error bounds, all native
    controller scalars/counters, dimensions, model/operator/settings identities,
    and generation. Controller scalars use exact binary64 bit strings. Restoring
    MUST be transactional, identity-checked and deep-copy all numerical state.
    A fresh generation invalidates stale submissions. Physical work and deadlines
    live outside rollback state and MUST remain monotone. The helpers reject
    shape mismatch, stale generation and audit windows exceeding 200 updates.

## Cost and resource admission

13. The [frozen proposal](../../benchmarks/configs/lp-fp4-proposal-v1.json) MUST
    bind the eight retained development models and source receipts. It includes
    native, four-component FP8, two-component FP16 and FP4 with 2, 4 and 8 components.
    Their approximations MUST meet the same error/audit/certificate policy; no
    control is yet numerically admitted. FP8 uses E4M3 and FP16 uses IEEE binary16;
    detailed hardware mapping belongs to prototype admission.
14. All 192 proposed cells (eight models, six lanes, three cold repetitions and
    one prepared batch of three fresh solves) and 288 endpoints MUST remain
    visible, including known uncertified mixed-model endpoints. Prepared solves
    share immutable preparation only. No scientific retry or selective removal
    of a failed model is allowed. Measured retention requires unchanged certified
    coverage, strict original-model certificates, at least 1.10× cold geometric
    mean speedup and no certified model-median regression. This is a prospective
    FP4 criterion, not a redefinition of RESIDENT2.
15. Cost review MUST use disjoint full-delivery phases and same-lifecycle native
    control rows. The optimistic removable fraction is at most the entire native
    phase; failing 1.10× even at that bound rejects the speed claim for that row.
    Otherwise missing component profiles return `needs_profile`. A profile-based
    forecast includes pair-product work, achieved throughput and all incremental
    packing, scale/reduction, state I/O, audit, fallback, launch and scratch costs.
    It MUST use the worst bound over its declared intervals. Forecast admission
    does not imply hardware admission, execution authorization or certification.
16. Packed plane payload is `ceil(n/2)*k` bytes and scale metadata is `k` bytes
    per block. Report padding, both operator orientations, indices, original FP64
    matrix, residual checks, temporary buffers and component-state copies as
    well. Pair products cost k_A*k_x, before physical tensor padding; four by
    four costs sixteen products, eight by eight sixty-four. Do not call this
    compression without accounting for all retained storage.
17. The resource proposal MUST enumerate whole-job CPU/GPU reservations, four
    CPU slots, one GPU lease, sampled host/device limits and cleanup allowance.
    Proposed prototype and study allocations are separate and non-executable.
    Failed/unsettled jobs retain full charges; historical accounts remain closed.
    No held-out access, old numerical rerun or GPUP-9 release follows this slice.

The proposed prototype pilot uses development irregular-2048 and dense_block-1024,
six lanes and cold/prepared lifecycles (24 jobs). Twelve additional diagnostic
jobs cover these two models, three FP4 component counts and unfused versus
per-update-reconstructed variants, in the prepared lifecycle. Each diagnostic
uses the matching persistent/fused pilot as its control. These comparisons
isolate fusion/persistence costs; they do not qualify the diagnostic variants as
the requested fast path. Prototype admission totals 19040 CPU / 1560 GPU seconds;
the separately proposed full study totals 55760 CPU / 13440 GPU seconds. Neither
is an allocation for this CPU-only task.

The cold statistic is the median of three complete deliveries per model/lane,
followed by the geometric mean of native/candidate ratios over models with
certified coverage. Publish every individual delivery, range, model median,
coverage count and failure; three repetitions provide a screening statistic, not
a confidence claim about small differences. Report prepared batch total,
preparation cost and per-fresh-solve cost separately. No retained RESIDENT2 timing
serves as the eventual measured control; the future study requires fresh matched
native cells. The current retained timings provide only a feasibility bound.

## Interfaces and validation

`tools/lp_fp4_protocol.py --proposal PATH [--cost-output PATH]` validates strict
schemas, finite values, frozen roster/settings, source hashes, Cartesian coverage,
resource arithmetic and retained control evidence. It emits a non-executable
contract verdict and optionally the source-bound cost review. The checkpoint,
proposal and cost schemas use version 1 and reject unknown fields. Rational
strings are reduced and bounded to prevent unbounded parsing. No input may select
an executable or request a device launch.

CPU tests independently exercise codebook/ties/padding, greedy residual tails,
transpose identity, exact product bounds, projection kinks, error recurrence,
audit persistence, cancellation/rollback, malformed artifacts, resource arithmetic
and pessimistic cost forecasting. Device differential checks, actual instruction
inspection, four sanitizers, fused/unfused profiling, iteration inflation and
measured latency remain GPUP-FP4-PROTO / GPUP-TENSOR2 work.
