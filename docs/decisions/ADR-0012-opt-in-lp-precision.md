# ADR-0012: Opt-In LP Precision with Independent Host Authority

Status: accepted (design decision; implementation pending)
Owner: numerical backend
Introduced: GPU LP precision research, GPUP-0
Last reviewed commit: bootstrap (first commit containing this document)
Supersedes: ADR-0010's blanket FP64-only scope and shared CPU/device reduction assumption only for the future SPEC-0012 backend; all legacy backend rules remain in force
Superseded by: none

## Context

The user approved a staged FP32-to-FP8 study including Tensor Core execution,
configurable numerical audits, and high-precision recovery. The target is certified
single-solve latency, not a particular arithmetic format. The existing
[ADR-0010](ADR-0010-certified-gpu-lp.md) deliberately excludes mixed precision and
[SPEC-0011](../specifications/SPEC-0011-gpu-lp-backend.md) requirements 5-8 and 27
fix FP64 arithmetic and a shared reduction tree. Those rules remain appropriate for
the existing control implementation and must not silently change.

Host certification is structurally independent of iteration arithmetic: it consumes
untrusted multipliers and the original model. That separation permits investigating
lower-precision proposal generation; it does not prove any implementation correct.
Inspection found a cancellation defect in the current certifier, recorded in
[known failures](../../state/known-failures.md#lp-certification-can-lose-the-roundoff-allowance-at-zero-reduced-cost).
Repairing that defect is a prerequisite, including a review of objective/gap
arithmetic. FP64 alone is not an error bound.

## Decision

Permit an opt-in experimental LP backend under
[SPEC-0012](../specifications/SPEC-0012-mixed-precision-lp.md), after its specification
is accepted and its prerequisite repair passes. Preserve the existing `cuda-lp`
FP64 path and default pinned HiGHS backend. Acceptance of this ADR records the
research direction; it does not claim the draft interface or any kernel exists.

For the new backend only, permit recorded storage, product, accumulation, and state
precisions to differ. Preserve original FP64 model coefficients for independent
host validation and conservative certification. Device residuals, audit results,
or a low-precision draft cannot establish bounds or mathematical termination.
Do not loosen caller accuracy to make a candidate faster.

For that backend only, replace the shared CPU/device reduction-tree requirement
with an explicitly recorded kernel arithmetic contract, numerical differential
checks, and bitwise repeatability for fixed inputs, device, code object, settings,
and seeds. Cross-device and CPU/device bitwise equality are not claimed for Tensor
Core arithmetic. Same-device repeatability is retained, not waived. A candidate
that fails it cannot become a supported preset without a new decision and contract.
Keep deterministic outer reductions; do not introduce floating-point atomic
accumulation as an unnoticed implementation detail.

Keep a matched FP64 control and ablate algorithm/controller changes separately.
Treat audits as diagnostics and recovery mechanisms, not certificates. Snapshot all
state that affects continuation and account for rejected work. Numerical recovery
on a healthy device does not authorize continued use of a poisoned CUDA context.
The pinned HiGHS adapter remains the authoritative backend fallback; an FP64 replay
inside the experimental algorithm is numerical recovery, not that fallback.

[ADR-0009](ADR-0009-cuda-driver-boundary.md) remains in force: custom kernels through
the existing driver boundary, no added CUDA runtime or vendor math-library
dependency, no third unsafe crate, and no toolkit requirement for ordinary builds.
The exact integer scheduling evaluator is outside this decision.

## Alternatives

Keep only FP64: a necessary control, but it cannot answer the approved precision
research question. Replace the legacy backend in place: rejected because it would
mix numerical-contract changes with performance comparisons. Require CPU bitwise
identity for Tensor Core products: rejected for the experimental backend because
its different arithmetic must instead be explicitly tested. Drop determinism:
rejected; same-device reproducibility remains an acceptance condition.

## Consequences

Precision settings and records require explicit versioned contracts. FP64 recovery
and certification may dominate latency; memory compression or Tensor Cores may
lose after setup, padding, or extra iterations. All are measured outcomes, not
reasons to weaken correctness. The final arithmetic recipe remains undecided
until the study in [ADR-0013](ADR-0013-lp-precision-study.md).

## Implementation and tests

Implementation is pending GPUP-1 through GPUP-8 of the
[roadmap](../plans/gpu-lp-precision-roadmap.md). SPEC-0012 maps intended requirements
to planned tests. Slice 0 validates documentation only. Existing SPEC-0011 tests
remain intact; new numerical, recovery, and device gates must pass before support
is claimed. This accepted record is superseded by a new ADR if the decision changes.
