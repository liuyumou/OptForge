# SPEC-0021: Residual-driven LP refinement and controlled inexact products

Status: accepted ADR-0037 refinement, ADR-0039 assessment and ADR-0040 direct matrix-selectivity subsets; combined extensions remain draft
Scope: research LP correction, anchored products, selective precision and assessment
Owner: numerical backend
Introduced: GPUP-DESIGN, 2026-10-12
Last reviewed commit: bootstrap
Supersedes: none; legacy SPEC-0012 audits/recovery and ADR-0010 authority remain
Implementation: refinement modules plus optimizer-lp::assess, optimizer-lp-cuda::assess and optimizer-experiment::lp_assess
Tests: independent GPUP-REFINE rational/endpoint oracles, host/device fault and replay tests; acceptance map below

## Accepted subset (2026-10-22)

[ADR-0037](../decisions/ADR-0037-bounded-lp-refinement.md) freezes the user-accepted
FP64-outer, FP32-products-only subset, merit/error/progress parameters, recovery
and resource allocation. CPU proof/oracle admission precedes dependent runtime
work. A reproduced numerical admission refusal is a valid bounded outcome;
full expansion masters and selective precision within refinement remain draft. Assessment scheduling
is separately accepted under ADR-0039 below.

The [implemented evaluation](../benchmarks/lp-refinement-gpup-refine.md) retains
108 attempts, 48 independently verified endpoints and 30/96 certified timings,
with no sparse-product benefit or supported preset. The accepted ADR fixes the
parameters and projected-stationarity choice that the broader design below
describes as proposed/unset. That proposed wording applies to independently gated
extensions; it does not unset this accepted subset. ADR-0038 repairs selected-device
activity telemetry without changing the method. Full native, device, replay and
four scoped sanitizer acceptance pass; complete expansion state and requirements
12–14's assessment policy are outside ADR-0037 and are implemented separately
under ADR-0039 below.

## Purpose and terminology

Accelerate convergence to the original LP using inexpensive inner work while
accurately maintaining residuals, iterates and decisions. This is a new method,
not a silent change to GPUP-6's last-window audit/replay. Native FP64 and accepted
expansion arithmetic are alternative accurate outer paths. Neither is required
for every inner operation. See the
[component rationale](../plans/lp-precision-architecture-2026-10-12.md) and
[experiment design](../benchmarks/lp-precision-design-experiments.md).

The original problem is min c^T x + c0 subject to lr <= A x <= ur and
lx <= x <= ux. Canonicalize maximization by negating both objective coefficients
and offset, preserving the existing publication mapping. Infinity is a bound tag.
Introduce activity z and define

~~~text
v = (x,z); B = [A,-I]; b = 0; g = (c,0)
Bv = b; (lx,lr) <= v <= (ux,ur).
~~~

This equality-plus-box problem is exactly equivalent to the original LP. The
identity block is applied implicitly; it need not be stored. Equality or one-sided
rows and free/fixed variables fit the same formulation. An already accepted
alternative equality representation may use nonzero b with the same derivation.

## Correction problem and exact identities

For anchor v0 and equality multiplier y0, using the Lagrangian convention
L(v,y) = g^T v + y^T(b-Bv), compute original-operator residuals

~~~text
rp = b - Bv0
rd = g - B^T y0
Delta_p > 0, Delta_d > 0 (exact powers of two)
minimize (Delta_d * rd)^T d
subject to B d = Delta_p * rp
           Delta_p*(l-v0) <= d <= Delta_p*(u-v0).
v_next = v0 + d/Delta_p
y_next = y0 + w/Delta_d
~~~

Here w is the equality multiplier of the correction problem under the same sign
convention. The dual scaling follows from
Delta_d*rd - B^T w = Delta_d*(g-B^T y_next). Bound multipliers scale by the same
Delta_d. Bound shifts/scales are exact real definitions, not permission to
materialize an unrepresentable endpoint. For an exactly feasible correction,

~~~text
original objective(v_next) = g^T v0 + c0 + y0^T rp
                            + correction objective(d)/(Delta_p*Delta_d).
~~~

Final objective/gap/certification still use the original model. Rounded correction
objectives or this identity without its feasibility condition are not certificates.
The activity-variable dimension and extra state/projections count in costs.

For an inner operator Bhat=B+E, suppose Bhat*d=Delta_p*rp+eta. Then, before update
roundoff, the new original equality residual is

~~~text
b - B(v0 + d/Delta_p) = (E*d - eta)/Delta_p.
~~~

Thus small inner residual alone does not guarantee outer progress. The budget
must also bound E*d, anchor/residual error and master-update error. Scaling cannot
remove arbitrary conditioning or make an inaccurate oracle accurate by itself.

## Anchored products and selective precision

Maintain deltas directly, rather than subtracting two nearby rounded states:

~~~text
v = v_anchor + delta_v
Bv approximately p_anchor + Bhat*delta_v, where p_anchor = B*v_anchor
y = y_anchor + delta_y
B^T y approximately q_anchor + Bhat^T*delta_y, where q_anchor = B^T*y_anchor.
~~~

Accurate anchor products make the representation error E*delta_v rather than
E*v; the transpose needs the same protection. Refresh anchors on a bounded error
or drift condition, or at an outer correction boundary. Refresh cost, lost work
and checkpoint state are observable. Exact power-of-two scaling helps range; it
does not by itself establish a safe step size for a changing approximate operator.

For blocks J of coefficients in row i, an admissible tail bound includes

~~~text
abs((E*delta_v)_i) <= sum_J ||E[i,J]||_1 * ||delta_v[J]||_infinity.
~~~

Use conservative summaries with their own rounding bounds, and an analogous bound
for the transpose. Add product, reduction, anchor, state and scaling errors. Map
back into original units before comparing to the forcing budget. A relative error
divided by an almost-zero activity is not the admission criterion. Promotion of
outliers/blocks updates one canonical operator and its transpose map atomically at
an admitted checkpoint; stale norms, decoded vectors or summaries are invalid.

## Requirements

1. A method MUST name the original model, canonicalization, equality/box transform,
   all scaling maps and the primal/dual publication mapping.
2. The correction builder MUST preserve the objective and feasible set under that
   mapping, including ranged/equality/one-sided rows, free/fixed variables,
   finite/infinite bounds, maximization and objective offsets.
3. The method MUST compute residual anchors with a declared accurate original
   operator and explicit absolute error bounds; rounded-operator residuals alone
   are insufficient.
4. The inner solver MUST expose achieved primal, dual/stationarity and bound or
   complementarity error information needed by the outer progress test.
5. Inner feasibility, small iterate change or success for Bhat MUST NOT be
   interpreted as original optimality, infeasibility or unboundedness.
6. The outer controller MUST freeze a quantitative progress/forcing rule, norm
   scaling, accepted error budgets and maximum failed corrections before trials.
7. Every approximate product MUST fit a conservative absolute error budget that
   includes representation, arithmetic, reduction, scaling, anchor and state error.
8. Both product orientations MUST use the same canonical represented coefficients
   and valid norm/step-size assumptions at each operator generation.
9. Anchored execution MUST maintain deltas, anchor products, scale and refresh
   generations as live checkpointed state.
10. A precision or scale change MUST invalidate or rebuild all affected norms,
    bounds, compensation and cached decompositions before dependent work.
11. A stable-formula variant MUST record exact-real equivalence, finite-range
    behavior, rounding changes and boundary decisions under its own identity.
12. An assessment policy MUST distinguish cheap scheduling indicators from an
    original-model assessment and mandatory final certification.
13. Delayed assessment MUST count the added iterations and delayed discovery of
    success, as well as the saved assessment work, in total latency.
14. Every published candidate/bound and successful endpoint MUST pass the existing
    original-model host authority at the requested unchanged tolerances.
15. Recovery MUST be explicit, budgeted and replayable, including failed windows,
    refreshes, correction solves, promotions and any return to native FP64.
16. Exceeding a range/error/work limit MUST produce a named refusal or limit,
    rather than silently weakening tolerance, clipping bounds or resetting budgets.
17. The method MUST preserve finite/infinite bound semantics and check exponent,
    dimension and memory arithmetic before allocating or applying a transform.
18. A snapshot MUST contain complete inner/outer/controller/assessment state and
    cumulative charged work sufficient for deterministic same-device replay.
19. No experiment MUST change the meaning of old SPEC-0012 audits, identities,
    defaults or records; the new method requires new settings and evidence versions.
20. Before behavior, each slice MUST accept a bounded interface, stopping/recovery
    policy, proof/error obligations, resource caps and mapped acceptance cases.

## Progress controller design

A proposed flow is: accurate original residual refresh; choose representable power-
of-two correction scales; admit operator/error budgets; solve the correction to a
bounded inner target; update accurate masters; recompute original progress; accept
or charge a failed correction and refine precision/scale under a finite policy.
An accepted variant may use anchors inside each inner solve. Native FP64 outer
masters provide a control before combining with SPEC-0020 expansion masters.

Use a normalized original KKT merit for progress, without treating it as a proof of
optimality. With bound multipliers mu_l, mu_u >= 0 on finite bounds, include

~~~text
equality residual:      b-Bv
stationarity residual:  g-B^T y-mu_l+mu_u
bound violation:       max(l-v,0), max(v-u,0), only finite endpoints
complementarity:       mu_l*(v-l), mu_u*(u-v), only finite endpoints.
~~~

Freeze the norm and per-block denominators before trials. Terms for absent bounds
are omitted with multiplier fixed to zero. A missing or infinite certified gap is
not a zero gap and cannot trigger successful termination. If an inner method does
not provide bound multipliers, the contract must derive valid candidates or define
an equivalent projected-stationarity measure; neither is assumed implemented.
For active fixed variables, split bound multipliers with a documented deterministic
convention so merit and replay are well-defined.

The contract to be accepted must choose a finite contraction factor rho in (0,1),
an absolute floor consistent with the final tolerance, error allocation fractions,
refresh limits and a correction-work cap. An example form is
merit_next <= rho*merit_anchor above the floor, with conservative uncertainty on
both sides and explicit handling below the floor. These are **unset proposed
parameters**, not defaults to be guessed by an implementation. A slice must
justify their values analytically and freeze them before measuring performance.
No general convergence guarantee follows until the inner oracle assumptions and
error sequence satisfy a suitable theorem. Empirical contraction is separately
reported and may fail on ill-conditioned or degenerate LPs.

## Interfaces, state and assessment

Proposed internal objects (not yet APIs) are OriginalEqualityBox, AccurateAnchor,
CorrectionProblem, OperatorErrorBudget, InnerResult and OuterProgress. Each binds
the original model identity, operator generation, scales and arithmetic policy.
CorrectionProblem uses an implicit activity identity, explicit bound tags and
absolute error units; InnerResult includes the achieved error estimates and work,
not merely a success flag. OuterProgress binds independent recomputation and the
chosen accept/refresh/promote/terminate decision.

State includes v/y and multipliers, deltas, primal/dual anchors, both correction
scales, all inner PDHG state, norm estimates, original-unit error summaries,
restart/weight state, compensation, operator generation, assessment schedule,
checkpoint and work counters. A correction boundary does not erase charged work.
Recenter/restart transfers all components with a specified rounding policy.

The assessment experiment compares a fixed inherited schedule with a new,
bounded trigger schedule. Cheap estimates can request an assessment or defer an
optional one; they cannot issue a certified bound. Mandatory final certification
always remains. Required adaptive audits in existing modes are unchanged; any
new schedule affecting them needs an explicitly accepted new method contract.
Successful termination at a work/time limit still needs the same authority.

## Errors, compatibility and resources

Reject unsupported transform/range/memory before device work. Distinguish an
inner limit, failed progress, inadmissible operator, numerical exception,
cancellation and certification rejection. Preserve evidence for each, including
partial work and every attempted fallback. Do not infer infeasibility from an
unreliable correction solve. Native fallback outside a frozen recovery policy is
not allowed. A cancelled outer solve must not launch another correction.

Keep all existing algorithms and record versions unchanged. A new opt-in identity
will bind the method, representation, forcing schedule, controller, kernel image
and assessment policy. Evidence must distinguish an inner update, an outer
correction, an anchor refresh and a certification; their counts are not comparable
as a single unnamed iteration count. Ordinary no-toolkit builds remain valid.

Admit transformed dimension n+m, nnz(B)=nnz(A)+m logically, both orientations,
master/delta/anchor/checkpoint vectors, error summaries and worst-case promotion
storage. Measure preparation and all refresh traffic. Freeze byte/time/iteration
caps and GPU reservations per slice. This draft admits no jobs or extra campaign
allowance, and does not authorize an external solver/library boundary.

## Examples and acceptance tests

For min x with 0 <= x <= 1, replacing c by c-A^T*y0 with A=1, y0=2 changes the
minimizer to x=1. With activity z and B=[1,-1], rd=(-1,2), equality x=z makes the
cost x again. The CPU design artifact exercises this counterexample, objective
and dual scaling, both signs, and the E*d correction residual identity.

| Requirements | Required assertion / gate |
| --- | --- |
| 1-2 | Exact rational forward/reverse feasibility, cost/offset and dual stationarity maps for tiny general LPs; exhaustive vertices where finite; ranged-row counterexample; free, fixed, one-sided, equality and maximizing fixtures. |
| 3-8 | Independent residual/error envelopes for cancellation and extreme scales, canonical transpose inner-product identity, known safe norm/step bounds, forced operator-tail budget refusal. |
| 6, 15-16 | Controlled inaccurate oracle causes promotion or bounded failure; contraction stalls cannot claim success; failed corrections and replay remain charged. |
| 9-10, 17-18 | Round-trip all anchors/deltas/scales/caches; stale-generation rejection; overflow/memory/alias/cancellation fault injection and deterministic recovery. |
| 11 | Rational proximal/gap identities plus rounded boundary and infinite-bound tests; old versus changed-trajectory claims correctly labeled. |
| 12-14 | Deliberately misleading cheap indicators never publish bounds; final certifier rejects perturbed-model solutions; paired assessment scheduling and delayed-success accounting. |
| 19-20 | Accepted new version/resource contract; historical replay and exact certifier regressions; full pinned-native gate; device differentials, repeatability and four scoped sanitizers when kernels change. |

## Open questions

Close the bounded-accuracy inner oracle assumptions, select/justify the progress
norm and parameter values, prove safe handling of changing represented operators,
and define precise interfaces and evidence. Determine whether added activity
variables, refreshes and metadata repay their costs. Full expansion masters,
selective blocks and assessment scheduling are independently gated extensions;
a contract may accept a smaller valid native-FP64-outer refinement slice first.

## Accepted bounded assessment subset (2026-10-22)

[ADR-0039](../decisions/ADR-0039-bounded-assessment-scheduling.md) accepts
requirements 12–20 for research-only fixed_200/bounded_800 scheduling on tuned
FP64 and existing accumulation FP32 after independent CPU common-trajectory
admission. Every 200-update numerical controller check remains; cheap normalized
movement only schedules original-model assessments, at most 800 updates apart.
The current safe final witness receives fresh host certification, including partial
intervals; cancellation, deadlines and failures retain their termination reason.
Complete scheduler/controller checkpoints belong to the originating session and
preserve charged work and deadlines, including rejection by a fresh session on
the same immutable engine.
The lp-assess-v1 interface and resource allocation are frozen in ADR-0039; legacy
records/defaults/audits are unchanged. Full native, strict evidence, device
differentials/replays and scoped sanitizer acceptance pass. The
[assessment report](../benchmarks/lp-assessment-scheduling-gpup-assess.md) retains
all 60 attempts, 57 verified endpoints and 24/48 certified timings. Cheap
indicators never publish a bound; every endpoint uses original-model authority.
Six common-trajectory profile pairs match bitwise. CPU-only review strengthens
signed-zero replay and rejects unverified profile comparisons, with exact source
bridges preserving the original workers/report and all twelve retained replays.
PR review adds regressions for cross-session checkpoint transfer, inconsistent
failure metadata, overflowing counters and interrupted profile horizons. Partial
profiles remain evidence with unavailable trajectory comparisons. Exact source
receipts preserve the measured execution loop and original-model authority;
review adds no GPU execution or revised-executable timing claim.

## GPUP-7 accepted bounded matrix-only contract

[ADR-0040](../decisions/ADR-0040-bounded-matrix-quantization.md) accepts the
user-approved matrix-only uniform/selective FP16/E4M3/E5M2 subset. Canonical
sparse 32-by-32 tiles, direct binary64 nearest-even conversion, conservative
original-unit local product budgets, common safe norm envelope, sticky promotion
and charged whole-window replay are isolated under lp-quant-v1. FP64 state,
32-update audits and each 200-update controller/assessment boundary remain.
Independent host certification at unchanged 1e-9 tolerances is authoritative.
Vector quantization, stochastic rounding, Tensor Cores, combined refinement or
assessment policies, sessions and supported presets remain separate extensions.
Acceptance maps format/range/transpose/bounds to the quant CPU contracts and
independent Fraction oracle; recovery to checkpoint/fault/limit regressions;
execution to quant_device differentials, replay and four scoped sanitizers;
authority and identity to strict lp-quant-v1 endpoint verification.

## GPUP-7R accepted resident subset (2026-10-22)

[ADR-0041](../decisions/ADR-0041-resident-matrix-quantization.md) accepts only
SPEC-0012 requirements 9–21 and 24–38 and SPEC-0021 requirements 7–10 and 14–20
as narrowed by the [resident plan](../plans/lp-quant-resident-follow-up.md).
The new research-only lp-quant-resident-v1 interface supersedes executor placement,
reduction layout, bound construction and diagnostic horizons for this interface
alone. Existing lp-quant-v1 and tuned numerical bodies, identities and evidence
remain unchanged. No other draft extension becomes accepted.

1. The executor MUST retain FP64 working vectors/updates on-device and canonical
   coefficient IDs in compact oriented sparse segments. Segmented low groups use
   serial RN32 products/sums followed by serial RN64 group combination. The FP64
   policy bridge uses the unchanged tuned warp32 tree and duplicate guarded reads.
   Guard arithmetic identity is global-then-coordinate-successor-rn-v1; the two
   tree identities are segmented-serial-fp32-fp64-v1 and tuned-warp32-v1.
2. Nonnegative bound add/multiply/divide MUST advance the RN64 result one positive
   representable value, with exact-zero shortcuts. This encloses the exact result,
   including gradual underflow. Coefficient summaries include exact-real original
   diagonal preconditioning error. Detailed bounds add coefficient/conversion
   errors, gamma(group length + 1) multiplication/reduction allowances, native
   outer-tree allowances, their propagation, subnormal and original-unit unscaling
   allowances. Nonfinite values fail admission. Coarse alpha/beta/tiny constants
   use the same outward operations and are generation-bound. No cancellation
   credit, saturation, nonzero deletion, contraction or arithmetic FTZ is allowed.
3. The runner MUST submit at most 32 proposals between host observations, cut at
   each 200-update controller boundary, audit with the host FP64 reference and
   adopt its endpoint. Failure restores the complete window/controller snapshot;
   started/rejected/replayed proposals, audits, uncertain and predicated work stay
   charged. Immutable operator origin, unique generation token, promotion state
   and originating session bind every cache/checkpoint. No demotion is permitted.
4. Strict evidence MUST distinguish fresh solves, exact logical-horizon profiles
   and independent-product diagnostics. Profiles retain the first timely host
   certification iteration while continuing to exactly 2000 logical updates, with
   a separate 50000 total charged-update limit. Interrupted/failed/incomplete or
   unverified horizons are ineligible for comparisons. Original tuned profiles use
   its exact kernels/controller with forced continuation; its primary timings use
   the unchanged CLI. Every endpoint receives fresh original-model certification.
5. Reporting MUST retain every frozen cell, CPU refusal, failed attempt and full
   fresh-process cost. Low/native coefficient operations, duplicate bridge guard
   products, coarse/detailed decisions, promotion fractions, window state uploads,
   transfers and audits are separate counters. Guard-only diagnostics include
   product reads/range checks and overlap fused work; intervals are not additive.
   Unguarded product diagnostics have no solve or certificate authority.

Acceptance mapping: optimizer-lp quant_resident.rs and tests/quant_resident.rs
cover origin/generation validation, failure at every window position, restoration,
audit adoption, promotion, cancellation/deadlines and invalid-device work charging.
The isolated experiment module covers strict parsing, oversized counters, fresh
original assessment and signed-zero replay. The integer/Fraction interpreter in
tools/lp_quant_resident_oracle.py independently models the RN24/RN53 and outward
programs, including the bridge tree and original-unit bounds; the inherited codec
oracle enumerates formats and adjacent rounding boundaries. quant_resident_device
covers both orientations, partial/full masks, subnormal coefficients/operands,
range failures and resident/controller equivalence. The full pinned-native gate,
ordinary device suite, fixed-work endpoint/replay pairs and four scoped sanitizers
are required. Toolkit provisioning remains separate from ordinary builds.

The frozen [protocol](../../benchmarks/configs/lp-quant-resident-v1.json) allocates
3600 GPU seconds from existing authority with zero ceiling increase, binds the
17036-event prefix and selected UUID, and retains CPU useful-low refusals without
replacement. Results belong in the [separate report](../benchmarks/lp-quant-resident-gpup7r.md).

The completed resident evaluation certifies 36/108 planned timing cells, with
78 quantized timing/profile CPU refusals, three complete FP64 logical horizons
and 21 verified operator endpoints. Full native/device/replay/sanitizer gates pass;
all 313 LP and 21 operator endpoints freshly verify. No useful quantized solve
benefit or supported preset follows; the remaining extensions stay gated.

The [quantization PR review](../benchmarks/lp-quant-pr-review.md) adds CPU-only
regressions for immutable prepared operators, atomic invalid-ID refusal, bounded
device-window counters, canonical JSON shapes, promotion history, physical
accounting and completed-worker profile eligibility. These strengthen the accepted
resident subset; arithmetic budgets, kernels, original-model certification and
the remaining gated extensions are unchanged. Historical measured cohorts and
their evidence are preserved separately from the rebuilt host verifier.
