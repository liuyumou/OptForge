# SPEC-0032: Exact independent checker acceleration

Status: implemented; exact admission and all 960 comparison cells complete
Delivery: [measured report](../benchmarks/lp-fp4-checker.md)
Date: 2026-11-11
Decision: [ADR-0064](../decisions/ADR-0064-exact-checker-acceleration.md)

The user requests continued independent-checker optimization and explanation of
FP4 iteration versus complete cold costs. This separate task preserves every
closed FP4-ACCEL source, result, failure, allocation and certificate criterion.

## Arithmetic and authority

Use a separate `research/lp-fp4-checker` package. Original-model candidate
feasibility retains term order, sequential product/sum/magnitude arithmetic,
finite-intermediate rejection, signed-zero normalization, bound tolerances,
objective offset and first-error order. Cache immutable variable-ID-to-coordinate
lookups once. Do not replace these sums with tensor arithmetic or reassociate them.

Conservative dual certification retains exact product classification, outward
bounds, original segment/reduction order, row repair, first refusal and original
objective-sense mapping. Any optimized primitive must agree bit-for-bit with the
original for normal/subnormal values, signed zeros, overflow and refusal, with
independent rational fixtures retained. Final gap assessment remains the original
function. Full reports and errors must match the original feasibility evaluator.
CPU checking remains a separate process without a CUDA context. Its model,
endpoint and executable identities remain bound into receipts. Both final tiers
remain explicitly 1e-7 and 1e-9. The supported public checker/default is unchanged.

Reuse the admitted FP4-ACCEL device image, controller, model preparation and
kernel sources verbatim. CPU-only changes do not re-open device arithmetic
qualification or historical sanitizer runs. Preserve the original CPU authority
as the differential oracle. No unverified cache of endpoint answers is permitted.

## Admission and measurements

First profile baseline and candidate CPU phases on retained endpoints. Require
exact feasibility reports/errors and dual certificate bits/refusals across
adversarial generated cases and every one of the 102 retained unique audit/final
endpoints. Run isolated Rust tests/lint and transport binding/failure checks.
New development versions may be corrected with exact failed sources and charges.

After CPU admission, freeze a new complete-cost cohort using all twelve existing
original model bytes, nativefast and gridfp4x2, both final tiers, original and
optimized checker, cold and prepared lifecycles, five repetitions: 960 cells.
Alternate baseline/candidate order; use EOF delivery, include process startup,
preparation, checker work, durable response/log output and exit for cold. Prepared
startup is separately recorded. All endpoint/certificate fields except executable
identity must match the corresponding frozen old endpoint; physical work and
recovery decisions must remain unchanged. Check all audits, not only terminal
candidates. Do not retry a failed scientific cell. Report full coverage, medians,
paired bootstrap uncertainty, per-update GPU work and checker cost separately.
The existing broad 1.10x cold/no-model-regression/no-coverage-loss gate is unchanged;
a checker speedup does not by itself establish general FP4 superiority.

## Independent resources

New allocation: 24000 CPU / conditional 1200 GPU seconds. CPU phases:
implementation 8000 (including 256 preparation), acceptance 6000, study 6000,
reporting 3000, cleanup 1000. GPU acceptance 300 / study 900. Four CPU slots,
one pinned shared GPU lease, 16 GiB sampled RSS / 12 GiB device buffers, unchanged
in-container supervisor and exclusive full-job reservations. Failed/unsettled
jobs retain full charges. Separate artifacts: `artifacts/gpup-fp4-checker-v1`.
No historical transfers, GPUP-8 retry, GPUP-9 release or public default change.
Commit locally after acceptance; no push/publication.

## Exact implementation refinements

Independent rows with at least 65536 total nonzeros may run on four CPU workers;
join in original row order so reports and the first error stay identical. Dual
columns retain four-worker scheduling with one reused scratch vector per worker.
The outward tree is reduced in place: each segment is consumed before its result
is compacted into the completed prefix; padding adds +0 to all three components.
No floating addition, segment offset or rounding decision changes.

Cache each finite coefficient's odd integer significand and exponent, and each
repaired multiplier's decomposition once per assessment. The exact nonzero product
is an odd positive integer p times 2^e. It is representable as finite binary64 iff
p has at most 53 bits, e >= -1074, and e + bit_length(p) <= 1024. This is equivalent
to the original comparison with the rounded product's decomposition. Zero and
nonfinite checks precede this predicate. Inexact products retain the same adjacent
bounds. Test this predicate against original product bits/refusals across 500000
full-bit-pattern pairs, explicit edge cases and complete certificate differentials.
