# SPEC-0029: FP4 operational recovery contract

Status: CPU contract implemented; solver/device integration unexecuted
Owner: numerical backend and experiment tooling
Date: 2026-11-11
Decision: [ADR-0061](../decisions/ADR-0061-fp4-operational-recovery.md)
Implementation: [CPU oracle](../../tools/lp_fp4_recovery_contract.py), [frozen policy](../../benchmarks/configs/lp-fp4-recovery-v1.json)
Acceptance: [contract tests](../../tests/integration/test_lp_fp4_recovery_contract.py), [delivery](../benchmarks/lp-fp4-recovery-spec.md)

## Authority and scope

This is the new `fp4-operational-recovery-v1` path permitted by
[ADR-0058](../decisions/ADR-0058-fp4-gpu-exploration-quality-tiers.md). It selects
an **operational residual guard**, not a proved enclosure of the distance to an
exact/native trajectory. Its correctness authority is an independent final
original-model checker. It establishes neither convergence nor a certified
solver speedup. CPU contract tests are not a rerun of the twelve refused
SPEC-0026 cells. Those cells, sources, charges and closed budgets remain exact.

The old monotone enclosure is not reset or quietly weakened. The new policy
has a separate identity, schema and checkpoint type. The optimized
[SPEC-0028 candidate](SPEC-0028-fp4-fast.md) remains empirical device evidence;
its independent-block, 32-update results do not admit coupled LP trajectories.
Public solver defaults, bound/gap/refusal mathematics and old strict certificates
remain unchanged. The CPU oracle implements policy decisions, arithmetic
contracts and adversarial synthetic events, not a solver or a certificate issuer.

## Why the old bound is not reused

The [retained diagnosis](../benchmarks/lp-fp4-proto-gpup-fp4-proto.md) identifies
three rounding/encoding metadata refusals and nine cumulative-bound refusals.
Separate local budgets repair the former. They do not repair the latter.

For the scalar equality, interior primal projection and steps 1/4, the local
signed map before Halpern weighting is
`M = [[1, 1/4], [-1/4, 7/8]]`. Let `P = [[1, 1/4], [1/4, 1]]`.
Direct rational multiplication gives
`P - M^T P M = [[1/16, 1/64], [1/64, 1/16]]`.
Both P and this difference are positive definite, so this particular linear map
contracts in its P norm. The old independent absolute recurrence
`[[1, 1/4], [3/4, 9/8]]` instead maps `[1,2]` to `(3/2)[1,2]`.
The CPU test verifies both identities exactly.

This scoped calculation explains lost coupling. It is not a general proof for
active projections, sparse coupled models, adaptive steps, anchors or device
rounding. Such a proof would require a common metric for the relevant maps and
certified forcing terms. No such theorem is claimed by this delivery; the
explicit operational alternative avoids treating observed errors as enclosures.

## Compatible local budgets

1. Preserve the E2M1 codebook, shared A/transpose quantization, scale limits,
   32-value vectors, padding and exact binary64 original model from SPEC-0025.
   Persistent updates use components and declared local FP32-pair arithmetic.
   Full original-unit FP64 snapshots occur at audits/recovery, not every update.
2. For a local ideal value z, pair-rounded q and encoded value h, store
   `e_pair >= ||z-q||` and `e_encode >= ||q-h||` separately. Charge
   `e_local = e_pair + e_encode >= ||z-h||`; cancellation may never reduce the
   stored encoding remainder. The exact CPU oracle covers all padded blocks,
   underflow and each component count. Conversion never erases prior uncertainty.
3. For the **stored** input h and original operator A, product accounting is
   `||A h - computed||_inf <= ||A-H||_inf ||h||_inf + e_instruction + e_combine + e_discarded`.
   Use row-sum errors separately for A and A-transpose from the same H. This
   equation contains no unknown error relative to a true trajectory. Nonzero
   omitted pairs require a bound; exact-zero planes may contribute zero.
4. Every complete update declares operator, instruction, combination, scalar,
   projection, encoding and discarded-work terms. Combination includes all
   local pair rounding; scalar includes coefficient/step/Halpern rounding.
   Include anchors, both products, extrapolation and both blends. Map each term
   through downstream **local** operations and inverse scaling before summing;
   for example extrapolation amplifies the primal term by two. These gains
   bound operations within the current update, not across its whole history.
5. For x and y separately, divide the summed original-unit local error by
   `max(1, ||current original-unit snapshot||_inf)`, fixed at the last audit.
   Compare it to `max(target_tolerance, min(1, last_audit_rho))/64`.
   This dimensionless **per-update operational allowance** tightens as progress
   improves. It is not the final tolerance, a cumulative error budget, or a
   sufficient condition for convergence. A missed, unknown, nonfinite or
   over-budget term causes recovery. Keep cumulative local sums as diagnostics
   without labeling them a global trajectory enclosure.
6. Preserve each term's evidence authority. CPU rational bounds are
   `exact-local-only`; empirical device differential estimates are
   `device-observed`. Passing a device differential or this allowance proves
   no instruction error bound. Integration must identify the method/source for
   every estimate, including an observed instruction contribution; unknown
   cannot be silently replaced with zero. An actual arithmetic proof would be
   a separately admitted policy version.
7. Project the combined expansion, never individual components. Use a local
   enclosure for the comparison of that approximate input with an exact bound;
   a straddling/unsupported decision must refine locally or emit
   `projection_ambiguous`. Empirical product error is not a rigorous interval
   around the exact-A iterate. Fixed and one-sided bounds remain explicit; NaN,
   overflow and explicit infinite numeric values refuse. Null represents an
   absent bound. Snapshot rounding is reported separately in original units,
   never subtracted from local history or mistaken for a reset to exact state.

## Audit metric and deterministic decisions

Use original model coefficients and original-unit x/y, with minimization
convention `s = c - A^T y`. Max models must use the existing canonical mapping;
the independent endpoint checker still reads the original objective/offset.
Let `b = A x`, and let Pi denote projection onto the specified box.

| Observed quantity | Numerator | Denominator |
| --- | --- | --- |
| Row violation | `||b - Pi_[L,U](b)||_inf` | Sy |
| Column violation | `||x - Pi_[l,u](x)||_inf` | Sx |
| Primal fixed-point defect | `||x - Pi_[l,u](x-s)||_inf` | Sx |
| Dual fixed-point defect | `||b + Pi_[-U,-L](y-b)||_inf` | Sy |

`Sx = max(1, ||x||_inf, ||s||_inf, magnitudes of finite column bounds)`;
`Sy = max(1, ||y||_inf, ||b||_inf, magnitudes of finite row bounds)`.
An empty set of finite bounds contributes zero. Rho is the maximum of all four
quantities. Both primal feasibility and dual/complementarity behavior matter.
This is a dimensionless operational diagnostic with state-dependent scaling;
even rho=0 is not a conservative gap/bound certificate. The exact rational CPU
oracle is independent of component storage and limited to 64-by-64 fixtures.
Integration implements finite FP64 audits for actual model sizes and compares
their results to the oracle, including rounding and unscaling.

An initial original-A observation seeds the residual and normalization scales.
Audit after at most 200 accepted logical updates and at every earlier native
controller boundary. Each fused submission contains at most 32 updates and is
clipped to the next audit/controller boundary and remaining physical budget.
At 192 updates the next submission is at most eight; at 200 it is zero until
audited. Submission identity includes generation. The host must bound queued
work as well: at most one such submission may be in flight. Cancellation latency
is bounded by that submission plus synchronization/cleanup, not a promised time.

Apply the following priority order after synchronization:

1. Reject stale identities, invalid counters or an overdue audit as protocol
   errors. Cancellation, deadline or physical-budget exhaustion restores the
   last accepted checkpoint and stops. They do not start an unbudgeted fallback.
2. A failed independent audit stops with restoration. Nonfinite state, excessive
   local error or unresolved projection causes restoration and promotion.
   These failures may also be reported immediately within a window through the
   same recovery transition; no need to wait for a 200-update audit.
3. A source- and endpoint-bound independent certificate at the requested tier
   finishes the solve. It takes precedence over the following progress tests,
   but never over cancellation, unsafe state or identity errors.
4. If `rho_new > 2*max(rho_previous,target_tolerance)`, reject this window and
   restore/promote. Equality at the growth threshold does not trigger recovery.
5. Otherwise count an audit as progress only if the previous rho is positive
   and the new rho is at most 90% of it. Reset consecutive stalls on progress;
   three consecutive other audits restore/promote. Zero residual with a refused
   certificate still counts as stagnation. Non-stalling finite observations
   adopt the candidate unchanged as the next complete checkpoint.

These ratios are fixed operational choices, not tuned convergence constants.
They require validation during integration; any later change has a new policy
identity, source-bound tests and separately frozen evidence.

## Precision, recovery and complete checkpoints

Default start is FP4 x2, then x4, x8, then native. Integration also compares
starts at x4/x8 and matched native/FP8/FP16 controls. The retained FAST results
motivate trying cheap early work: two components are faster but inaccurate;
eight components are substantially more accurate yet still slower than native
on rich coefficients. No component count is justified by final tolerance alone.

Promotion restores the last accepted complete checkpoint and converts **all**
x, y, extrapolated state and both anchors. The CPU oracle requires identical
decoded values when adding components; it retains old local representation
bounds. Promotion does not recover information previously discarded. Advance
generation once per recovery, reject stale submissions, reset only progress
stall metadata and preserve controller scalars/counters exactly. Rebuild both
operator orientations consistently from original coefficients at the new
precision and record their new operator identity. Do not silently restart anchors.
The pure conversion helper does not prepare/rebind the device operator; that is
an explicit integration transaction before execution can resume.

There is at most one promotion attempt to each higher precision; no downgrade
or return to FP4 after native handoff. A failed conversion goes directly to native
restoration. Eight-component failure likewise selects native. Native recovery
starts from an independently audited original-unit export of the accepted
checkpoint; if it cannot be represented safely, start from the original native
initialization. Explicit native initialization/restart resets native controller
fields according to its own contract and records that transition. There is no
claim of native trajectory equivalence. Original physical iteration/deadline
limits and all charges survive both warm recovery and cold native restart.
Native failure/limit is final; no automatic second solve or scientific retry.

The [new checkpoint schema](../../schemas/lp-fp4-recovery-checkpoint-v1.schema.json)
retains every plane/scale, all five vectors, local representation bounds, model/
operator/settings/proposal identities, dimensions, generation and exact binary64
controller bit strings. It expressly labels the error authority
`local-representation-only`. A full recovery bundle pairs that payload with the
Monitor's policy hash, tier, residual, stalls, precision and mode, binding the
payload hash and all counters. Keep physical work/time/cost outside rollback.
Restoration deep-copies all state and increments generation. Audits do not
rewrite components, anchors, local errors or policy history to manufacture
precision. An explicit controller transition may subsequently update anchors;
store the full post-transition checkpoint and matching monitor atomically.

## Independent endpoint checking and all costs

The checker adapter is future integration work. It must call the existing
original-model feasibility evaluation, conservative dual-bound construction and
gap assessment with explicit absolute/relative 1e-7 or 1e-9 tolerances. Preserve
all finite-bound refusal, repair, objective direction/offset, normalization and
nonfinite rules. Public defaults stay at 1e-9. A certificate at one tier does not
authorize a pass at the other; separate evidence records bind each assessment.

The CPU receipt validator binds model bytes, **exported endpoint bytes** (distinct
from the full checkpoint), checker source identity and exact tier/tolerances;
it requires eligible transport, primal feasibility, finite bound, closed gap,
acceptance and no refusal. This validates a receipt's interface only. Integration
must actually execute the independent checker, verify source and artifact hashes,
and store its full receipt; a caller-supplied success flag is not evidence.
Check at every audit/end when an endpoint is available. Record an earliest
crossing only when checked there, including its export/check cost.

Charge disjoint prepare, transport, iteration, audit, conversion, rollback,
native recovery, export and checker times. Preparation includes both operator
orientations, packing/scales, original model retention and initialization.
Iteration includes component products, normalization, projection and re-encoding;
report subphase instrumentation separately without adding it twice. Include
failed/rejected updates, native restart, cold context cost and checkpoint copies.
Report logical and physical updates separately. No subtraction for rollback.
Prepared solves reuse only immutable data and begin with fresh numerical state.

The executable cost helper sums all phases and evaluates a row against 1.10x;
it cannot establish cohort retention. TENSOR2 still needs same-tier native
controls, >=1.10x cold model-median geometric mean, no certified median regression
or coverage loss and uncertainty. Current short-window kernel times cannot
supply an unmeasured solve forecast or audit/recovery cost.

## Integration proposal and this task's resources

The frozen policy enumerates 96 **proposed**, non-executable fixed-work diagnostic
cells: eight fixture families x six lanes x two final tiers. Coupled equality,
inequality, ranged/one-sided, fixed/active-bound, ill-scaled coupled, irregular
33-tail, rich 65-dimension and infinite-bound-refusal families must get exact
versioned generators/model hashes during integration. Include nonzero starts,
active projection changes and genuine cross-tile coupling; repeated independent
blocks do not satisfy that coverage. Each diagnostic targets 600 physical updates
and observations by 200/400/600, including useful FP4 work and any recovery.
These are fixed-work diagnostics, not time-to-solution measurements: retain all
checked crossings but do not terminate the diagnostic based on a certificate.
Production solve policy consumes a valid certificate immediately. Early safety
stops remain visible and cannot be relabeled as 600-update passes.

Twelve separately enumerated safety cases cover stale generation, three
cancellation boundaries, deadline, nonfinite/local/projection errors, growth,
stagnation, conversion refusal and checker bound refusal. New CPU admission,
source/device freeze and primitive differential checks precede device trajectories;
four scoped sanitizers cover changed code, both orientations and recovery state.
The FP8/FP16 controls require their own compatible primitive/policy admission.
The integration implementer freezes exact settings, source/image bindings,
cell order, per-case limits and resource package before any job. This proposal
does not execute them or reopen the old twelve-cell admission or 192-cell study.

| Proposed integration work | Jobs | CPU seconds each | GPU seconds each |
| --- | ---: | ---: | ---: |
| Implementation/preparation | 1 | 16000 | 0 |
| CPU/native contracts | 1 | 8000 | 0 |
| Primitive admission | 1 | 480 | 120 |
| Safety cases | 12 | 240 | 60 |
| Sanitizers | 4 | 720 | 180 |
| Fixed-work trajectories | 96 | 180 | 45 |
| Reporting | 1 | 3200 | 0 |
| Cleanup | 1 | 1040 | 0 |
| **Total proposed** | | **51760** | **5880** |

Integration proposal: four CPU slots, one shared GPU lease, 16 GiB sampled host
RSS, 12 GiB device buffers; whole-job reservations must fit, failed/unsettled
jobs remain charged. These are proposals, not allocations or claims that each
deadline will suffice. A newly selected package must cover the frozen jobs.

**This CPU-only task** has a separate 16000 CPU / zero GPU allocation:
4096 implementation (including 256 conservative preparation/packaging seconds),
8000 software acceptance, 3000 reporting and 904 cleanup. Four CPU slots and
6 GiB sampled RSS apply through the unchanged in-container supervisor. No
historical resources transfer. Run focused/neighboring CPU contracts, repository
Python integration, schema/artifact/docs checks, exact history preservation and
cleanup. No numerical/device job, old qualification retry, checker/default change,
held-out access or publication. Commit locally after acceptance. Native control
remains supported; GPUP-FP4-INTEGRATE becomes next ready, old FP4-PROTO and GPUP-8
stay incomplete, and GPUP-9 remains gated.
