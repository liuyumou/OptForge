# ADR-0063: Correct state encoding and amortize FP4 delivery

Date: 2026-11-11
Status: accepted for implementation under the user's acceleration request

The [integration diagnosis](../benchmarks/lp-fp4-integrate-diagnosis.md) identifies
avoidable repeated model/evidence construction, state encoding losses, expensive
late precision changes and a slope-based stagnation false positive. A dense
kernel win is already present, but it does not overcome complete delivery costs.

Implement [SPEC-0031](../specifications/SPEC-0031-fp4-corrected-acceleration.md) in
a new `research/lp-fp4-accel` package. Retain FP4 tensor products with explicitly
charged FP32-pair correction terms and checkpoints, independent original-model
checking, row equilibration and error-aware precision control. Reuse immutable
preparation and move the solve loop into the resident native service. Optimize
the matched native control as well; select no preset without complete-cost evidence.

This version changes representation/controller semantics and therefore is not an
amendment of the closed integration results. Local empirical arithmetic guards
remain operational, not trajectory proofs. Larger dense tests must exercise
generic solution values. Retain every failed development attempt and freeze
formal execution only after CPU/device/sanitizer admission. The independent
160000 CPU / 24000 GPU allocation releases this new work without historical
transfers. No public solver default, final checker mathematics or older budget
changes. Local delivery only; GPUP-8 remains incomplete and GPUP-9 gated.
