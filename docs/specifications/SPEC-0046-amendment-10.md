# SPEC-0046 amendment 10: complete certificate-witness storage

The endpoint allowance must include a possible repaired certificate dual in
addition to the original primal and dual. Prospective formula version 2 reserves
`(ceil(iterations / 500) + 2) * 8 * (columns + 2 * rows)` bytes per solve. It does
not assume that repaired vectors, final endpoints or different lanes deduplicate.
Workers also count the unique referenced endpoint chunks and check this bound.
The actual resource ceilings, numerical code, certificate cadence and criteria
remain unchanged. Preserve earlier formula-version-1 freezes and all their raw
observations; none of the inspected earlier responses used a repaired dual.

Before any billion-nonzero solve, freeze the largest common iteration ceiling in
500-update increments, at most the initial 5000, that fits the complete six-family,
three-lane endpoint reservation and remaining CPU/GPU allocation. Include fixed
inputs, previous evidence, build/storage headroom, fresh final checking and offline
assessment auditing. This resource decision must precede numerical observations
from the billion-scale solve cohort. Keep every family and lane, including any
capacity refusal; do not select based on convergence or timing success. Retain
100-update control, 500-update certificates and the strict 1e-9 original-model
check. A resource-limited iteration ceiling is not a relaxed certificate.
