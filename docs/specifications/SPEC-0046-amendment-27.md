# SPEC-0046 amendment 27: exact SIMD proposal encoding

The allocation-refined image-v6 CPU cohort completes all six pairs with exact
packed results and durable linker artifacts. Retain its full roster, including
the actual-FP4 coupled regression: 3.619 to 3.841 seconds. Do not generalize the
five zero-tile gains to FP4 preparation or certified total solve time.

Image-v7 adds an isolated, runtime-selected AVX2 encoder on x86-64 with a portable
scalar fallback. Each SIMD lane performs the original FP64 multiplication and
residual subtraction separately, without FMA or reduction reordering. Ordered
threshold comparisons reproduce the original tie decisions. Integer construction
of binary64 bits reproduces the existing normal-E2M1 decoder. Maximum reduction,
exponent selection and component order stay scalar and exact. New tests compare
codes, exponents and every residual bit against the unchanged original encoder,
including adjacent threshold values, signed zeros, scales and vector tails.

Require a fresh full 54-test quality build before sealing image-v7. The separate
third CPU diagnostic cohort uses the same six original 64 M inputs, alternating
order, immutable source/library/executable bindings and original resource ceilings.
These are fresh cells for a distinct implementation, never retries of earlier
cells. Keep both preceding cohorts, their regressions, the first cohort's explicit
missing-library exclusion and every charge. All results remain stage diagnostics;
full GPU preparation and total solve gains are unmeasured.

Operational v15 permits only the six named new CPU development jobs after fresh
CPU acceptance. Supersede only never-started operational GPU v14; retain failed
v11/v12 and never-started v13 in their original plans. GPU image-v5/v6 checks and
science have never started. Future GPU validation targets image-v7 and still
requires the explicit idle-result gate, five-minute proof, operational admission,
exact preparation/continuation checks and all four complete sanitizers. Do not
retry the repeated operational failure without investigating supervision.

No numerical CUDA, strict certificate, public default, supervisor threshold,
ownership guard, capacity formula, phase cap or total allocation changes. All work
stays container-only, without resets, shared-memory clearing or other-job signals.
