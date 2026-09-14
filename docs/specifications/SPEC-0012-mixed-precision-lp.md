# SPEC-0012: Experimental Mixed-Precision LP Backend

Status: draft; not implemented or selectable
Scope: opt-in LP arithmetic, resumable control, numerical audits, and recovery
Owner: numerical backend
Introduced: GPU LP precision research, GPUP-0
Last reviewed commit: bootstrap (first commit containing this document)
Supersedes: none while draft; ADR-0012 defines the intended exception to SPEC-0011 requirements 5-8 and 27 for the new backend only
Implementation: pending GPUP-1 and GPUP-3 through GPUP-8
Tests: planned requirement mapping below; no new runtime coverage in slice 0

## Purpose

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

Planned selection: `cuda-lp-quantized`, opt-in through the existing solve surface.
This name is reserved by the draft, not accepted by the current CLI. The Backend
trait remains the runtime boundary. Its capability declaration needs an explicit
mixed-arithmetic representation rather than falsely reporting F64-only execution.

A separate versioned precision-settings document will accompany the existing LP
method settings. It records allowed/forced precision modes, matrix/vector format,
scale and block policy, rounding/seed, sparse or hybrid execution, tile-density
policy, audit interval, primal/dual update tolerances, recovery ladder,
clean-window/demotion policy, and work/memory/time limits. All consequential
settings are explicit. Unsupported combinations fail validation; no final preset
or runtime schema is shipped by this draft.

New records distinguish requested and executed backends/modes and retain config
and code-object identities, transitions/reasons, accepted/rejected/audit counts,
termination, and host validation/certification. Existing records remain readable.
Exact schema versions, enum wire values, and comparison rules must be finalized
with migration fixtures before GPUP-5 exposes the interface; adding fields silently
to strict existing schemas is not compatible.

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

Accept this draft before introducing the behavior it owns. ADR-0012 permits the
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
Executable CLI/JSON examples will accompany the accepted interface, rather than
showing a command that does not work in slice 0.

## Acceptance tests

All tests below are planned, not yet implemented. Each implementing slice must
replace planned labels with named tests/evidence; numerical tests use independent
oracles or able-to-fail injections rather than mirroring the implementation.

| Requirements | Planned assertion | Slice |
| --- | --- | --- |
| 1-5 | Exact binary64-coefficient rational oracle; cancellation/sign/infinite-bound fixtures; wrong device output cannot strengthen a bound; objective/gap sense checks. | GPUP-1, GPUP-5 |
| 6-8 | Capability refusal, unchanged default/legacy fixtures, settings/schema parity, old-record reading and migration. | GPUP-5 |
| 9-11 | Full trajectory, restart, controller-history, and checkpoint/replay comparisons against the matched reference. | GPUP-3, GPUP-6 |
| 12-15 | Allocation/transfer instrumentation, recorded arithmetic, same-device repeatability, conservative operator/step checks. | GPUP-4, GPUP-5, GPUP-8 |
| 16-21 | Quantizer boundary/tie/subnormal/overflow fixtures; transpose reconstruction equality; seeded retry equality; original high-precision operands retained. | GPUP-7 |
| 22-23 | Single-RHS padding/cost accounting; sparse/Tensor equivalence; unsupported hardware/layout checks. | GPUP-8 |
| 24-29 | Interval-1 and sampled audits; corrupted updates/guards; whole-window restore; reference endpoint adoption; charged work; sticky and hysteretic recovery. | GPUP-6, GPUP-7 |
| 30-33 | Exhausted ladder, time/work limit and cancellation injections; poisoned-context refusal; recorded pinned-backend fallback. | GPUP-6, GPUP-8 |
| 34-37 | Unsafe/dependency checks, toolkit/device-free build, lease exclusion, full native gate and relevant sanitizers. | Every implementation slice |
| 38 | Preset-to-frozen-experiment provenance; no preset/default emitted from an incomplete study. | GPUP-10 |

## Open questions

The fastest format, scale, block size, state precision, and recovery policy are
hypotheses to resolve experimentally, not missing defaults to invent during coding.
Exact wire schemas, memory/work-limit precedence, supported-format tables, and
rounding/scale corner-case algorithms must be completed before the corresponding
runtime slice. GPUP-1 must settle the numerical certification argument first.
This draft does not assert a PDHG convergence theorem for stochastic rounding or
low-precision operators, or support for unmeasured Tensor Core instructions.
