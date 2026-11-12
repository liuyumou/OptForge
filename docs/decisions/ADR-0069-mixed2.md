# ADR-0069: MIXED2 begins with an executable CPU contract and cost gate

Status: accepted for the user-requested bounded implementation, 2026-11-12.
Implementation: [SPEC-0036](../specifications/SPEC-0036-mixed2.md).

The current roadmap and ADR-0054 require complete-cost admission before device
work. DELIVERY4 measured substantial hash savings but only 1.0760–1.0869x dense
cold ratios, with no retained comparison. Context creation and destruction remain
large. DELIVERY3 prepared timing leaves a possible numerical opportunity, with
matrix-only attribution missing. These are observations, not a mixed-precision
speedup claim. Historical decisions and measurements stay exact.

Implement an isolated FP32-matrix/FP64-compute CPU reference, outward local product
bounds, transactional guard semantics and a source-bound retained-record forecast.
The original FP64 model and independent 1e-9 checker retain authority. Identity
scaling is explicit; FP32 state, approximate certificates and RESIDENT2 execution
are excluded. A local product enclosure is not a trajectory proof.

Freeze the cohorts, scenarios, latency/coverage/uncertainty rules and independent
16000 CPU / zero GPU allocation in SPEC-0036 before analysis. Do not infer actual
matrix speed from total GPU events. A negative upper bound closes that route; an
unresolved matrix fraction requires a separate attribution pilot. Neither outcome
authorizes CUDA or a new solver cohort. Preserve all failures and accounting,
report findings durably, and commit locally without publication.
