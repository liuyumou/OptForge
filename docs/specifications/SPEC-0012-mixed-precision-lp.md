# SPEC-0012: Experimental Mixed-Precision LP Backend

Status: accepted; GPUP-3/4/5/6 implemented and measured; later quantization and Tensor Core precision pending
Scope: opt-in LP arithmetic, resumable control, numerical audits, and recovery
Owner: numerical backend
Introduced: GPU LP precision research, GPUP-0
Last reviewed commit: 62516e8cef59104442fa359a2e2440af8a59f033 (companion-design navigation, 2026-10-12)
Supersedes: ADR-0012 defines the intended exception to SPEC-0011 requirements 5-8 and 27 for the new backend only
Implementation: shared FP64 control, matched/tuned CUDA, fixed FP32 correction and explicit GPUP-6 adaptive audits/recovery; GPUP-7/8 pending
Tests: continuation, bitwise trajectory, exact-rational, endpoint, native and scoped device gates; mapping below

## Proposed companion designs (2026-10-12)

The [precision architecture](../plans/lp-precision-architecture-2026-10-12.md)
separates exact storage, arithmetic, method and original-model authority.
[SPEC-0020](SPEC-0020-lp-expansion-arithmetic.md) covers compact representations
(with the bounded CPU subset now accepted under ADR-0034) and proposed persistent
accurate state; draft [SPEC-0021](SPEC-0021-lp-refinement.md) covers
correction LPs, anchors, selective error budgets and assessment policy. They do
not relax this specification's accepted audits/recovery or exclusions. Their new
behavior needs separately accepted bounded contracts and identities. Planning-only
ADR-0033 placed GPUP-REP CPU validation first. That task is now complete;
GPUP-EXEC is next, with no GPU reservation or preset implied.

## GPUP-6 accepted bounded contract

The maintainer accepted [ADR-0025](../decisions/ADR-0025-adaptive-precision-recovery.md)
on 2026-09-26 before implementation. It binds requirements 24-33 to explicit
lp-adaptive-v1 settings, five ordered FP32/FP64 rungs, complete-window rollback,
charged reference audits and demotion probes, version-5 evidence and replay.
Audit settings are independent of final certification tolerances. In-memory
checkpoint restoration never restores physical work or deadlines. The frozen
2376-attempt comparison and separately charged acceptance retain every previous
ledger prefix and campaign/phase cap. Implementation and correctness acceptance
are complete; the [report](../benchmarks/lp-adaptive-gpup6.md) retains incomplete
comparison coverage and all failures. No supported preset is selected.

The host adaptive fault-injection suite covers full restoration after restart and
weight decisions, original-unit reference adoption, intermediate/sticky promotion,
charged demotion probes, unavailable preparation/runtime rungs, cancellation,
deadlines, physical-work exhaustion and terminal FP64 failure. Device adaptive_
tests compare both objective senses and working-state rounding across windows,
controller checks and restored residency. Strict v5 mutation tests cover policy,
method/code identity, transitions, work counters and independently recomputed
assessments. CLI checks cover replay, exclusive flags and pinned fallback. All
four adaptive sanitizer scopes and the full pinned-native gate pass. The
original GPUP-1 exact-rational and legacy-record regressions remain in that gate.

## Purpose

Accepted by the maintainer on 2026-09-15. GPUP-3 implements shared resumable FP64
control and explicit `cuda-lp-matched` using existing kernels, settings and host
mathematical authority. Requirements 9-11 apply to in-memory FP64 checkpoints now;
precision/audit/random state applies when introduced in GPUP-5 through GPUP-8.
GPUP-5 adds explicit precision settings and fixed correction under ADR-0019.
GPUP-6 implements in-memory adaptive recovery under ADR-0025. Persistent
checkpoints, quantization and presets remain pending. [ADR-0016](../decisions/ADR-0016-matched-fp64.md) freezes this slice.

Define an experimental route from FP64 through FP32 to FP8 and Tensor Core LP
iteration without giving the device mathematical authority. Optimize certified
single-solve latency according to [SPEC-0013](SPEC-0013-lp-precision-experiments.md).
The [roadmap](../plans/gpu-lp-precision-roadmap.md) defines the implementation order;
[ADR-0012](../decisions/ADR-0012-opt-in-lp-precision.md) records the numerical decision.

Excluded: integer arithmetic changes in the schedule evaluator, full MILP backend
integration, cross-node reuse, batched independent solves, C7 portfolios, C9 SDK,
C10 general experiment APIs, FP4, and error-feedback algorithms. Existing `highs`,
`host-lp`, and `cuda-lp` behavior remains under its current contracts, except for
separately tested correctness repairs.

## Terminology

The *original model* is the immutable binary64 coefficient/bound/objective data.
The *working operator* is the preconditioned, possibly quantized representation
used to propose iterates. A *numerical audit* compares an update with an FP64
reference; it is not certification. A *window* starts from a checkpoint and ends
at an audit. *Promotion* retries at a more accurate configured arithmetic mode;
*demotion* permits a later window at a less accurate mode. *Backend fallback* is
execution by the pinned HiGHS adapter, distinct from FP64 numerical recovery.

## Requirements

### Authority and compatibility

1. The experimental backend MUST remain unavailable until the certification repair
   in GPUP-1 passes independent exact-arithmetic regression tests.
2. The backend MUST retain the original FP64 model for host validation and certification.
3. Every published candidate MUST pass the existing original-model validation contract.
4. Every published bound MUST come from conservative host certification that treats
   device output as untrusted and accounts for rounding, uncertain signs, and infinite bounds.
5. Mathematical termination MUST use the host-validated candidate and certified bound
   under the caller's recorded tolerances, never device residuals or audit agreement.
6. The backend MUST refuse unsupported problem classes, including discrete models,
   before iteration, under the capability contract.
7. Existing solver defaults and legacy arithmetic/determinism contracts MUST remain unchanged.
8. New precision settings and records MUST use explicit versioned interfaces with
   compatibility and migration tests before public exposure.

### Reference and execution

9. An experimental host/reference controller and its device counterpart MUST share
   continuation semantics for restarts, weights, anchors, budgets, and cancellation.
10. Comparisons of arithmetic modes MUST use an algorithmically matched FP64 control.
11. Each continuation checkpoint MUST capture every state component that can affect
    later iterates, control decisions, precision selection, and random rounding.
12. Iteration buffers SHOULD remain resident between checks when this reduces measured
    single-solve latency within the configured memory bound.
13. Each arithmetic mode MUST state its storage, product, accumulation, update, and
    correction precisions and its reduction/contraction behavior.
14. A supported mode MUST be bitwise reproducible for fixed input, device, code object,
    configuration, and seeds, without claiming CPU/device or cross-device bitwise equality.
15. Operator changes MUST update or conservatively validate step-size assumptions
    against both the original scaled operator and the represented working operator.

### Quantization

16. Both multiplication orientations MUST represent the same canonical quantized
    matrix, including promoted blocks or coefficient residuals.
17. Quantization MUST preserve the original coefficients outside the working representation.
18. Conversion and product guards MUST detect non-finite values, clipping, and nonzero
    values lost to zero before a projection or later finite result can conceal them.
19. Zero blocks, subnormals, outliers, scale overflow/underflow, and unsupported formats
    MUST have explicit tested handling rather than implicit saturation or coefficient deletion.
20. Rounding and scale choices MUST be deterministic under the recorded inputs and seeds,
    including retry and rollback behavior for stochastic rounding.
21. Selective higher-precision work MUST use operands appropriate to its precision
    rather than reusing already-damaged low-precision vector data.
22. Tensor Core execution MUST operate on the actual single-right-hand-side workload,
    with padding, packing, scale application, and outer reduction explicitly accounted for.
23. Unsupported hardware instructions or layouts MUST be refused or handled through
    the recorded execution policy, never assumed available from the Blackwell family name.

### Audits and recovery

24. The audit interval and update-error tolerances MUST be caller-supplied, recorded,
    and independent of final feasibility and gap tolerances.
25. A full audit MUST recompute the final update of the window in FP64 from its saved
    pre-step state and compare both primal and dual updates in declared units.
26. A passing audit MUST adopt the reference-corrected endpoint before continuation,
    without claiming to have verified the intervening trajectory.
27. A failed audit or range guard MUST restore the complete window-start checkpoint
    before replay at the next configured higher precision.
28. Every replay and FP64 reference update MUST count against recorded work and time
    budgets, with accepted, rejected, and audit work separately observable.
29. Demotion MUST require a configured clean-window count and a stricter acceptance
    margin than promotion, with an option to remain at the promoted precision.
30. Exhaustion of the precision ladder or budgets MUST terminate without manufacturing
    an infeasibility, unboundedness, or optimality claim.
31. Numerical recovery MUST preserve cancellation responsiveness and previously
    validated results under the existing solve contract.
32. Poisoned CUDA context handling MUST follow the existing device-failure policy
    rather than attempting numerical replay in that context.
33. Backend fallback MUST use pinned HiGHS and record requested and executed backends.

### Ownership and acceptance

34. Runtime implementation MUST preserve the Rust crate dependency and unsafe
    boundaries, with host certification in optimizer-lp and no device dependency there.
35. Ordinary builds MUST require neither a CUDA toolkit nor a device.
36. All project GPU execution MUST hold the shared host lease on one device.
37. Each implementation slice MUST pass the full native CPU gate and relevant device
    and sanitizer checks before its acceptance is recorded.
38. Supported precision presets MUST be backed by SPEC-0013 evidence; experimental
    grid values MUST NOT silently become defaults.

## Interfaces

GPUP-5 accepts explicit `--lp-precision` on `cuda-lp-tuned` alongside method and
execution settings, under ADR-0019. The [interface handoff](../plans/gpup5-interface-handoff.md)
is resolved. The originally proposed cuda-lp-quantized name remains reserved and
unavailable. The Backend trait remains the runtime boundary. Capability schema 2
explicitly declares mixed binary32/binary64 arithmetic; existing FP64 declarations
retain schema 1.

The strict lp-precision-v1 document records matrix, product operand, product,
accumulation, working-state and update widths, nearest-even rounding and a fixed
correction interval (or explicit null). GPUP-5 only accepts resident/necessary/
warp32_v1/separate execution and the combinations in ADR-0019. Unsupported fields,
versions and combinations fail before allocation. Absent precision settings retain
existing emission and behavior. No supported preset is shipped.

Precision solve records/endpoints and study campaign/trials use schema 4. They
retain requested/executed arithmetic and code identity, conversion/range diagnostics,
physical proposals/rejections/corrections, discrepancy, work, memory/transfers,
termination and original-model host assessment. Existing strict schemas and readers
remain intact. External COPT witness/endpoint-v1 is a separate study-only format.

Later quantization, scale/block policies, stochastic rounding, sparse/hybrid tile
policies, adaptive audits, primal/dual error thresholds, recovery ladders and guarded
demotion require their own accepted versioned settings. Their checkpoint/history
requirements below are pending those slices, not implied by fixed correction.

## State and invariants

Checkpoints include x/y, anchors, restart counters, accepted iteration indices,
step/weight parameters, controller integral/error history, audit/demotion history,
rounding state, and logical work counters. Immutable matrices can be referenced;
window-local buffers must be recoverable. Wall time and physical work counters do
not roll back. Cancellation is checked during bounded execution/replay chunks.

The initial audit uses componentwise comparisons in original model units, with
separate absolute tolerances for primal and dual vectors and recorded relative
tolerances. For a component, compare `abs(low - reference)` with
`absolute + relative * max(abs(pre_step), abs(reference))`. Any non-finite
intermediate fails. Preconditioning transformations used for the comparison must
be included in the numerical review. Interval 1 is full per-step reference work;
longer intervals sample local update error and do not bound accumulated history.

An audit at FP64 still cannot prove a floating-point computation exact. The final
certificate uses outward arithmetic on original data. Where uncertainty and an
infinite variable bound prevent a finite conservative result, no finite bound is
published. The implementation review must include minimization/maximization sign
conversion and objective/gap rounding, not only reduced costs.

Canonical tile sizes 16, 32, and 64 and audit intervals 1, 8, 32, and 128 belong to
the initial experiment grid, not hidden defaults. Begin with nearest-even,
maximum-based scaling and explicit promotion; compare alternate policies under
SPEC-0013. Independent orientation-specific scaling is not implicitly MXFP8-safe
for the algorithm: the represented operator relationship is the requirement.

## Errors and recovery

Malformed/missing settings, unsupported combinations, out-of-capability inputs,
allocation failures, range-guard events, cancellation, and device faults carry
distinct diagnostics. Preserve the existing distinction between failure to open
a requested device and an availability failure after opening. Numerical promotion
requires a healthy context. A limited or failed relaxation grants no new pruning
permission under SPEC-0003. A missing certificate is not infeasibility.

## Compatibility and versioning

This specification is accepted. GPUP-3 exposes only the FP64 contract below. ADR-0012 permits the
new opt-in contract without changing legacy FP64 tests. Record breaking changes
with new schemas and explicit migration notes. Same-device reproducibility is
part of the new contract; a method that cannot satisfy it stays unsupported until
a separate accepted decision changes that requirement.

## Security and resource limits

Validate dimensions and byte sizes with checked arithmetic before allocation,
including quantized metadata, dense-tile padding, residuals, and checkpoints.
All buffers together must fit the recorded memory limit. Numerical retries cannot
extend user time/work budgets. Device jobs are serialized host-wide; no new vendor
library, dynamic plugin, multi-GPU path, or unsafe boundary is authorized.

## Examples

An interval-1 FP32 test proposes one update, checks it against the FP64 reference,
and retains the corrected endpoint if it passes. A failed check restores the
checkpoint and retries in FP64, counting both attempts and the audit work.

An interval-32 FP8 test that passes its final-update audit has corrected that
endpoint; it has not proved that 32 earlier updates match an FP64 trajectory.
The independent final host checks still decide its candidate and bound claims.
These precision examples remain prospective. The implemented FP64 CLI and evidence
interfaces are documented below and in the study operations guide.

## Acceptance tests

GPUP-1's existing-backend prerequisite is implemented with
[exact certificate/gap regressions](../../crates/optimizer-lp/tests/certification.rs)
and the [numerical argument](../architecture/lp-certification.md). The mixed-precision
acceptance below remains planned. Each implementing slice must replace planned
labels with named tests/evidence; numerical tests use independent oracles or
able-to-fail injections rather than mirroring the implementation.

| Requirements | Assertion and implementation status | Slice |
| --- | --- | --- |
| 1-5 | Exact binary64-coefficient rational oracle; cancellation/sign/infinite-bound fixtures; wrong device output cannot strengthen a bound; objective/gap sense checks. | GPUP-1, GPUP-5 |
| 6-8 | Capability refusal, unchanged default/legacy fixtures, settings/schema parity, old-record reading and migration. | GPUP-5 |
| 9-11 | Implemented FP64: shared_controller_matches_literal_legacy_whole_trajectories, checkpoints_restore_all_history_but_never_work_or_deadlines, matched_control device tests. GPUP-6 adaptive fault injection restores complete window numerical/policy history. | GPUP-3 and GPUP-6 complete; persistent/random quantization state pending |
| 12-15 | Allocation/transfer instrumentation, recorded arithmetic, same-device repeatability, conservative operator/step checks. | GPUP-4, GPUP-5, GPUP-8 |
| 16-21 | Quantizer boundary/tie/subnormal/overflow fixtures; transpose reconstruction equality; seeded retry equality; original high-precision operands retained. | GPUP-7 |
| 22-23 | Single-RHS padding/cost accounting; sparse/Tensor equivalence; unsupported hardware/layout checks. | GPUP-8 |
| 24-29 | Interval-1 and sampled audits; corrupted updates/guards; whole-window restore; reference endpoint adoption; charged work; sticky and hysteretic recovery. | GPUP-6 complete for FP32/FP64; GPUP-7 quantization pending |
| 30-33 | Exhausted ladder, time/work limit and cancellation injections; poisoned-context refusal; recorded pinned-backend fallback. | GPUP-6 complete for FP32/FP64; GPUP-8 hardware modes pending |
| 34-37 | GPUP-3 passed unsafe/dependency checks, ordinary build, lease tests, full pinned-native gate and all four scoped sanitizers; repeat for each later slice. | Every implementation slice |
| 38 | Preset-to-frozen-experiment provenance; no preset/default emitted from an incomplete study. | GPUP-10 |

## Open questions

The fastest format, scale, block size, state precision, and recovery policy are
hypotheses to resolve experimentally, not missing defaults to invent during coding.
Exact wire schemas, memory/work-limit precedence, supported-format tables, and
rounding/scale corner-case algorithms must be completed before the corresponding
runtime slice. GPUP-1 supplies the conservative certification prerequisite; its
limits remain part of future performance comparisons.
This specification does not assert a PDHG convergence theorem for stochastic rounding or
low-precision operators, or support for unmeasured Tensor Core instructions.

## GPUP-3 FP64 interface and continuation contract

`optimizer solve --backend cuda-lp-matched` requires explicit LP settings and a
device, as for cuda-lp. Storage, products, accumulation and state remain FP64;
existing kernels/reduction order and no-contraction behavior remain unchanged.
The host controller computes the same restart/error/weight updates used by host-lp.
Legacy cuda-lp retains fixed anchors and weight. Host cancellation/callback ordering
remains unchanged; the matched host reference and device driver use bounded
64-step cancellation observations, without moving global check boundaries.

`Fp64Controller` holds scaled x/y, anchors, weight, integral/previous errors, anchor
and last-check errors, logical indices, restart count and processed check position.
Opaque in-memory checkpoints also bind the exact immutable Engine (model,
preconditioning/settings and step). Restore on a different engine is refused.
Physical steps, KKT work and absolute deadline are outside the checkpoint; rollback
never replenishes work or time. Device resumable advance returns completed vectors
and steps on healthy cancellation. A fault retains enqueued-kernel counts and
marks completed physical steps unavailable; native fallback cannot erase them.
The solve-options and LP iteration allowances both bound matched execution.

Assess before each controller update. On a limit between checks retain the last
assessed candidate and its dual; assess the final state if no previous assessment
exists. Retain the final independent checks. Endpoint-v2 carries controller/work
observations separately from unchanged legacy diagnostics/solve-record fields.
No controller observation grants mathematical authority.

Acceptance names: shared_controller_matches_literal_legacy_whole_trajectories;
checkpoints_restore_all_history_but_never_work_or_deadlines; matched_control device
cases; matched_evidence_roundtrips_without_changing_legacy_shape; matched_corruption
fixtures. The [reviewed GPUP-3 study](../benchmarks/lp-matched-fp64-gpup3.md)
records 160 attempts, full native acceptance, 38 regular device cases and five
cases under all four sanitizers. All 27 mutually certified host/matched endpoint
pairs agree bit for bit. Numerical limits remain in the report and known failures.

## GPUP-4 tuned FP64 contract

Accepted by the maintainer on 2026-09-15; runtime implemented, correction study verified and final acceptance passed.
[ADR-0017](../decisions/ADR-0017-tuned-fp64.md) freezes arithmetic and measurement.
Requirements 12-14 and 34-37 apply to this slice. The experimental backend is
cuda-lp-tuned; cuda-lp-matched retains its existing arithmetic. All storage,
products, accumulation and updates remain FP64. Only the iteration reduction may
change; original-model host authority and shared controller policy do not.

The required --lp-execution document uses schema_version 1, allocation
(per_check|resident), uploads (every_check|necessary), reduction
(legacy_1024|warp32_v1), and fusion (separate|primal_dual). Necessary uploads require
resident allocation. Unknown fields/values and unsupported versions are refused.
No execution defaults are supplied. Solve-record v3 carries lp_execution and the
actual code-object SHA-256. Endpoint v3 carries requested execution and execution
observations, even when pinned HiGHS executes after a device availability failure.
Version-2 solve records and version-1/2 endpoints retain their old wire shapes.

Resident state is scoped to one solve and immutable engine. Initialization and
checkpoint restoration upload complete state; restarts upload anchors. Physical
work and absolute deadlines never roll back. Every host assessment still receives
x/y; cancellation is observed at synchronized chunks of at most 64 steps. A fault
preserves enqueued launch counts and does not invent completed physical work.
All buffers, including empty padding and scratch, count toward admission and peak
memory. Counters report actual allocations, copy calls/bytes, synchronizations,
and launches. Profile phases cannot replace fresh-process latency.

warp32-v1 and two-kernel fusion follow ADR-0017's explicit operation order. Both
orientations use the unchanged canonical scaled coefficients. Bitwise tests compare
allocation/upload/fusion variants within one arithmetic mode. Warp arithmetic has
an independent Rust mirror and rational error checks; legacy whole-trajectory and
GPUP-1 exact-rational authority tests remain independent acceptance gates. Same
input/device/code/settings must reproduce bits. No validation or held-out tuning,
lower-precision interface, recovery policy, or supported preset is introduced.

Acceptance mapping:

- Requirements 7-8, 13-14: Fp64ExecutionSettings and solve/endpoint v3 migration,
  tuned_records_and_endpoints_are_versioned_and_strict and tuned_fault_fallback unit cases, TunedTests strict settings,
  unchanged legacy schema bytes, execution_enum_names_require_strings and CLI replay/altered-code rejection.
- Requirements 9-14, 28, 31-32: tuned_variants_match_complete_trajectories_and_restored_history,
  tuned_warp32_matches_independent_rational_products and
  tuned_cancellation_limits_memory_and_senses. Both vectors/anchors compare bits;
  independent Fraction fixtures check finite dot errors, device cases include
  overflow, cancellation, subnormals, padding and exact peak on early interruption.
- Requirements 33-37: pinned fallback/retained fault observations, device and
  admission integration cases, full native gate and all four scoped sanitizers
  through tools/lp_tuned_gpu_check.sh under the shared host lease.
- Measurement: TunedTests frozen protocol/allowance/crash/admission and immutable
  prior-ledger checks; tools/report_lp_tuned.py independently verifies endpoints,
  exact schedule, provenance and charged reservations. ADR-0018 retains the failed
  first round and freezes a separate correction under the same allowance. The
  [GPUP-4 report](../benchmarks/lp-tuned-fp64-gpup4.md) records evidence and limits.

No requirement concerning later precision/recovery or supported presets is marked
implemented by this FP64 slice.

## GPUP-5 accepted bounded contract

Accepted by the maintainer on 2026-09-16, before behavior.
[ADR-0019](../decisions/ADR-0019-fp32-lp-comparisons.md) defines the normative
precision combinations, fixed correction, versioned interfaces, external COPT
controls, frozen study and exact budgets. It supersedes the pending selector
recommendation: precision extends cuda-lp-tuned; absent settings retain old
behavior. Adaptive recovery and supported presets remain deferred. The
[GPUP-5 report](../benchmarks/lp-fp32-gpup5.md) records all 480 independently verified
endpoints, costs, failures and the exact 1324.210639253-second cumulative ledger.
Full native acceptance before measurement, final device/sanitizer evidence and
final-source acceptance are recorded in state/active-task.md.


GPUP-5 acceptance mapping (only bounded requirements, not GPUP-6 recovery):

- Requirements 1-8, 13-14, 33-37: unchanged exact-rational authority and historical
  trajectory/replay tests; lp_precision strict settings; precision solve/endpoint v4
  mutation tests; six CLI replay pairs and actual missing-code HiGHS fallback.
- Requirements 9-18, 28, 31-32: precision_modes_match_independent_steps_and_restore_residency,
  precision_long_sparse_reductions_and_guarded_operands, independent host rounding/
  product/canonical-transpose/operator-bound tests, and
  precision_device_preserves_subnormals_and_checks_loss_before_projection.
- Fixed correction: precision_interval_one_adopts_original_fp64_endpoint and
  precision_correction_work_cancellation_and_memory_are_bounded cover unconditional
  original-operator adoption, intervals 1/3/8/32/128, controller boundaries,
  FP32 restoration, cancellation, admission and exhausted physical work.
- Numerical versus availability failures: precision_range_failure_is_not_availability_fallback,
  retained fault diagnostics/unknown work and strict fallback endpoint checks.
  Six precision cases pass all four scoped CUDA sanitizers; regular device suites
  contain 47 cases. Details and logs are in the report/active task.

No adaptive audit, rollback, promotion/demotion, persistent precision checkpoint,
quantization or supported-preset requirement is marked implemented by this slice.

## GPUP-5B accepted bounded contract

Accepted on 2026-09-16 under [ADR-0021](../decisions/ADR-0021-exact-scaling-components.md).
Feature-gated explicit scaling and two/three-component sparse products use FP64
control and original-model certification. Strict research-v1 requests/evidence
are separate from runtime schemas and selectors. The frozen twelve-mode,
840-attempt development study charges all work to the preserved campaign ledger,
with 900 study/300 acceptance seconds inside existing ceilings. Numerical recovery
remains GPUP-6. The rounding investigation is reproduced before GPU measurements.


GPUP-5B implementation and acceptance mapping:

- Explicit scaling, component reconstruction, coefficient range, conservative step
  and canonical transpose: optimizer-lp research.rs and tests/research.rs.
  Independent rational products and sparse cancellation/reduction-boundary fixtures
  are checked by tools/lp_research_oracle.py and the Rust tests.
- Isolated resident execution: optimizer-lp-cuda research.rs and the separately
  provisioned cuda/lp_pdhg_research code object. No runtime selector or unsafe
  boundary is added. Ordinary builds remain toolkit-free.
- research_all_modes_match_independent_steps_across_controller_boundaries covers
  all nine new modes, checkpoint/controller transitions and truncation accounting.
  research_checkpoint_restore_and_exhausted_work_are_respected and
  research_memory_admission_precedes_allocations_and_faults_preserve_state cover
  admission, replay work and faults. Full-exponent device products cover subnormal
  retention, overflow and nonzero-to-zero loss before projection.
- Strict request/evidence, early cancellation, altered code identity, corrupted
  witnesses and mislabeled devices: optimizer-experiment lp_research tests.
  Assessment reuses original-model host validation/certification.
- The [report](../benchmarks/lp-exact-components-gpup5b.md) and active-task record
  bind exact measured identities, regular device and four sequential sanitizer
  gates, full native gates and retained failures. GPUP-1 certification regressions
  and existing FP64 trajectory/replay fixtures remain required and unchanged.

This slice implements fixed research modes only. No adaptive, quantization or
supported-preset requirement is marked complete by these observations.

## GPUP-5C accepted bounded contract

Accepted on 2026-09-19 under [ADR-0022](../decisions/ADR-0022-fp64-pipe-execution-and-tolerance-tiers.md),
following the [FP64-pipe root-cause note](../benchmarks/lp-fp64-pipe-root-cause.md).
Three further feature-gated research modes keep the shared FP64 controller, master
state, vector-update arithmetic, bounds, objective, guard semantics and original-model
certification: `intguard-fp64` (integer-pipe range guards), `fused-fp64` (sparse
product fused with its update and store, two launches per proposal) and
`doublefloat-fp32` (unevaluated FP32 pairs for coefficients and product operands,
no FP64 inside the sparse loop). Research-v2 requests/evidence record the
launch count per proposal and the fused execution setting; version 1 remains
valid only for the nine GPUP-5B modes. Explicit tolerance tiers are recorded per
request and never change the default 1e-9 or the certification arithmetic.

GPUP-5C implementation and acceptance mapping:

- Mode predicates, FP32 pair arithmetic, double-float admission/tail/bounds and the
  lane-strided pair oracle: optimizer-lp research.rs; tests/research.rs covers
  round trips, pair splitting, subnormal refusal and the independent rational
  double-float fixture generated by tools/lp_research_oracle.py.
- Kernels: cuda/lp_pdhg_research adds research_intguard64, research_fused_primal/dual_64
  and research_fused_primal/dual_df beside the unchanged nine entry points. The
  update helpers duplicate precision_primal/dual/store operation for operation so
  optimizer_lp::research::step remains the bitwise oracle.
- Executor: optimizer-lp-cuda research.rs allocates pair shadows, splits the dual on
  upload, and branches to the two-launch schedule; the six guard slots are unchanged.
- research_all_modes_match_independent_steps_across_controller_boundaries covers all
  twelve modes bitwise; research_intguard_fused_and_doublefloat_faults_are_reported_and_state_preserved
  and research_doublefloat_device_products_match_the_pair_oracle_and_flag_loss cover
  admission, faults, pair products and nonzero-to-zero loss.
- optimizer-experiment lp_research tests cover v1/v2 acceptance rules, fused
  launch counts and the fused execution setting.

No adaptive recovery, quantization, runtime tolerance change or supported preset is
marked implemented by this slice.

## GPUP-THROUGHPUT accepted bounded contract

Accepted on 2026-09-20 under [ADR-0023](../decisions/ADR-0023-repeated-solve-throughput.md),
[SPEC-0014](SPEC-0014-lp-repeated-solve-throughput.md) defines opt-in repeated-solve
sessions over a fixed matrix as an extension of this contract. Nothing in this
specification's numerical contract changes: every solve starts from a fresh
per-solve controller and the cold iterate, and original-model host certification
is unchanged. Amortized throughput is a separately labeled endpoint, never
substituted for fresh single-solve latency.
