# ADR-0061: Select an explicit operational FP4 recovery policy

Status: accepted CPU contract, 2026-11-11
Owner: numerical backend and experiment tooling
Implementation: [SPEC-0029](../specifications/SPEC-0029-fp4-recovery-policy.md)
Acceptance: [delivery](../benchmarks/lp-fp4-recovery-spec.md)

The user requests GPUP-FP4-RECOVERY-SPEC after the completed GPU pilot and FP4
optimization. ADR-0058 explicitly permits either a proved coupled enclosure or
an operational residual policy whose authority remains independent endpoint
certification. The retained scalar example shows how absolute-error propagation
can lose stabilizing primal/dual coupling. It does not supply a general bound
for projected, rounded, adaptive LP iterations.

Select `fp4-operational-recovery-v1`. Keep exact compatible local rounding and
encoding accounting, and label empirical device terms explicitly. Observe
original-model primal/dual fixed-point and feasibility residuals by 200 updates;
restore and monotonically promote on unsafe arithmetic, growth or three stalled
audits. Precision progresses 2 -> 4 -> 8 -> native, with all attempted costs kept.
Native handoff, cancellation and certified completion close the FP4 path.
Full checkpoints include controller and progress state; physical budgets never
roll back. A zero residual without an independent certificate still stagnates.

This is a separate policy, not a correction that passes the old refused grid.
No global trajectory bound or convergence guarantee is asserted. An exact
local triangle inequality and a scoped two-dimensional contraction identity
are independently tested; neither grants a general device arithmetic theorem.
The checker must still read the original model and conservatively assess
feasibility, finite dual bound and gap at an explicit 1e-7 or 1e-9 tier.
The new receipt validator checks interface consistency; actual independent
certificate execution and tolerance-parameterized adapter are integration work.

Measured FP4 x2 work is cheap but inaccurate; x8 is more accurate yet loses
against native on rich coefficients. Adaptive starting precision is a bounded
hypothesis to test, with native/FP8/FP16 controls and all normalization, audit,
conversion and recovery costs. No preset or complete-solve performance claim
follows from the earlier 4.16–7.81x same-lane kernel improvement.

Deliver CPU oracle/schema/tests, an immutable policy, 96-cell integration
proposal and complete resource accounting. The independent current allocation
is 16000 CPU / zero GPU; the future 51760 CPU / 5880 GPU package is only a
proposal. GPUP-FP4-INTEGRATE becomes ready when these contracts pass; its new
executable/device admission remains mandatory before TENSOR2. Preserve all old
source bytes, outcomes and closed charges. Local commit only; no publication.
