# SPEC-0026: Persistent FP4 prototype numerical admission

Status: accepted for GPUP-FP4-PROTO, 2026-11-11
Owner: numerical backend and CUDA runtime
Last reviewed commit: bootstrap
Decision: [ADR-0057](../decisions/ADR-0057-fp4-prototype-admission.md)
Implementation: [reference](../../tools/lp_fp4_reference.py), [admission](../../tools/lp_fp4_admission.py)
Tests: [CPU contracts](../../tests/integration/test_lp_fp4_reference.py)
Parent contract: [SPEC-0025](SPEC-0025-persistent-fp4-contract.md)

## Scope and numerical authority

1. The prototype MUST preserve SPEC-0025's components, exponent range, tile
   layout, projection refusal, monotone 1e-7 original-unit relative enclosure,
   200-update observations and unchanged original-model 1e-9 final certificate.
   CPU trajectory agreement or a software test pass MUST NOT imply certification.
2. The independent reference MUST directly evaluate original-coefficient rational
   PDHG steps with the same frozen binary64 step/blend coefficients. It MUST NOT
   call the component product or enclosure recurrence. Extrapolation precedes
   Halpern blending. The component path MUST keep packed x/y/bar/anchors across
   updates and accepted observations, with no reference-iterate adoption.
3. The CPU oracle models local arithmetic as correctly rounded FP32 head plus
   correctly rounded FP32 residual. Every local truncation MUST be measured
   exactly against its rational input and included in the recurrence. This is
   an arithmetic specification, not proof that a two-FP32 CUDA implementation
   produces those values. No hidden FP64 full-state/product buffer is permitted
   in the prospective device implementation; rational temporaries are confined
   to this CPU oracle. Actual fusion/rounding remains a subsequent gate.
4. Matrix preparation MUST encode each 32×32 tile once and transpose its codes.
   Products MUST enumerate every component pair in nonzero tiles with 32 active
   contraction positions, preserving zero padding and charging the K64 physical
   expansion. Exact pair groups MUST be checked against the mathematical group
   bound. Each cross-group accumulation rounds to the local FP32 pair and charges
   its exact error. No operator error, low component or zero-padded work may be
   silently discarded.
5. The primal scalar stage MUST bound the error of the entire projected update
   against the exact local map; extrapolation includes its arithmetic and state
   encoding error. The dual prox stage and Halpern blends MUST similarly account
   for all local arithmetic and encoding. The forward-product term MUST include
   the stored extrapolated-state error. Enclosure metadata MAY round upward to
   binary64 after each update to bound metadata size; downward rounding is
   forbidden. Actual oracle error MUST remain inside the propagated enclosure.

## Transaction and recovery

6. Every attempted update MUST be counted, including projection/error refusals.
   Partial state MUST NOT be adopted. Observation guards apply by the next
   200-update boundary and may refuse earlier; the implementation MUST record
   the first violating update and component/coordinate. The independent reference
   is diagnostic only and MUST NOT correct the component trajectory.
7. Accepted observations MUST preserve component/scaling/error bytes. Checkpoints
   MUST restore all state and controller fields. Cancellation or refusal restores
   the last accepted checkpoint and advances generation; physical work/deadlines
   remain unchanged. A source-bound disposition MUST identify 2 -> 4 -> 8 ->
   native escalation eligibility without pretending that a metadata recommendation
   is an executed recovery or independent certificate.

## Frozen CPU admission

8. Qualification fixtures MUST include scalar equality, a coupled 2×2 equality,
   a 4×4 diagonally dominant equality and a bounded 2×2 ranged-row LP, with known
   finite bounds and nonzero iterates/products. Values and settings are fixed in
   the versioned manifest before execution. Each of 2/4/8 component counts owes
   all four fixtures at 600 updates (three observations). A lane qualifies only
   if all its cells retain the fast path, preserve observations, enclose every
   independently computed iterate error and produce nonzero useful products.
9. Qualification MUST NOT demand bitwise/native-trajectory identity or actual
   convergence at 600 updates. It tests persistent arithmetic feasibility under
   the accepted guard. Conversely, exact-reference agreement by itself MUST NOT
   override an enclosure/projection refusal. All twelve cells remain reported,
   including first refusal, attempted/completed work and unrealized observations.
10. Safety tests MUST independently cover rounding ties/subnormals/overflow,
    matrix transpose/partial tiles, independent short trajectories, signed-zero
    controller state, cancellation, rollback, malformed/frozen manifests and
    nonfinite/scaling/projection refusals. They MUST separate expected refusal
    from qualification. The formal source-bound admission runs once after these
    software tests; no scientific automatic retry follows a negative result.

## Conditional device and profile gates

11. At least one CPU-qualified component lane and full CPU/native integration
    MUST precede device implementation/admission. The package MUST then freeze
    compiler/image/architecture/device, actual FP4 MMA and its applicable error
    bounds before iteration execution. Differential, failure/cancellation and
    four zero-error sanitizer checks precede profiles. Unsupported instruction
    semantics, numerical refusal or resource failure closes later execution.
12. The unchanged SPEC-0025 proposal retains 24 pilot cells and twelve diagnostic
    cells. The report MUST list them as unexecuted if admission stops, including
    native/FP8/FP16 comparisons. No cost forecast, speedup or TENSOR2 release may
    be inferred from the CPU oracle. Actual endpoint certification remains the
    original independent checker, with original coefficients and 1e-9 tolerance.

## Resources and compatibility

The independent CPU/GPU limits and failure accounting are in ADR-0057. The new
module/manifest/results are additive. Existing SPEC-0025 implementation, frozen
proposal, numerical sources, old accepted evidence and ledgers remain exact.
No CPU oracle is exposed as a public solver backend. JSON inputs reject duplicate
keys/nonfinite values and bind the exact contract, fixtures and source files.
