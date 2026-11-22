# Billion-scale LP PR integration

[PR #29](https://github.com/liuyumou/OptForge/pull/29) integrates fifteen commits
from `efc1d6e` through `334bb20` over main `1e15895`, preserving their ancestry.
Preparation, packing and control can dominate fast GPU updates; this work adds
exact host preparation/checker reuse, bounded array storage, optional GPU
preparation and FP4 packing, a zero-eligible packing path, and GPU control work.
The billion-scale executor remains isolated research code. Public solver defaults
and the original-model strict 1e-9 acceptance criteria remain unchanged.

## Review

The review covers immutable checker inputs, reduction order and signed-zero
behavior, dense-ID lookup fallback, interval arithmetic guards, sparse transpose
validation, checked allocation/copy bounds and CPU fallback domains. GPU
feasibility cannot grant acceptance alone: a potentially accepting endpoint also
requires original CPU feasibility, objective agreement, the CPU dual bound and
gap check. Checkpoint rollback and deadline status remain distinct from an
accepting proof produced after the deadline.

Resource review covers pinned ownership, aggregate memory, complete reservations,
real sampling during finalization, bounded publication, and preservation of
failed charges. The retained supervision failures remain limitations: some
missing responses have an unknown preceding trigger because cleanup overwrote
it. They are not successful solves or evidence of a vendor GPU memory failure.

The review fixes two CPU acceptance portability issues: SciPy 1.16.3, already
used by the admitted COPT environment, is now declared in the test requirements;
disk-inventory tests compile their own temporary binary and binding instead of
depending on private experiment files. Git attributes recognize all retained
phase CSVs as CRLF without rewriting their source-bound bytes. Numerical,
production resource-supervision and COPT adapter sources are unchanged by review.

## Evidence and limits

The [billion-scale report](lp-billion.md) retains all measured cohorts, phase
costs, failed/missing attempts and independent final/intermediate checks. The
[final COPT comparison](lp-billion-copt-fair-results.json) has twelve visible
roster slots and no jointly timely, strictly certified complete-time pair.
COPT strictly certifies tall in 1408.580 s and coupled in 857.414 s. Project tall
has an accepting proof but lacks valid complete timing; that ratio stays excluded.
Broad certified FP4 complete-solve superiority remains unestablished.

Earlier GPU admission and sanitizer results apply only to their exact source
bindings. This PR review performs CPU checks and source verification, without
repeating GPU work, experiments, or the deleted large-data replay. The original
settled scientific checkpoint remains unchanged at 459659.784173452 CPU /
55943.714704332 GPU seconds, including every failed reservation.

## Integration validation

The complete native gate passes 637 workspace Rust tests, one buffered-adapter
Rust test and 963 Python tests, format/Clippy/dependency checks, committed-record
replay, 388 documentation pages with local links, and smoke. After the final
fixture correction, all 963 Python tests pass again. Isolated acceptance passes
218 Rust tests, including both host LP dependencies and the device-free CUDA
copy-boundary test, plus format and Clippy.

All 136 new harness tests pass from a temporary source-only snapshot. Its test
interpreter refuses reads from private evidence and the COPT installation, and
refuses loading vendor/device libraries. The temporary source copy is deleted.
This is CPU test portability, not a replay of the deleted billion-scale data.

All 306 numerical bindings, eight admitted resource sources, six image files,
637 comparison references and 63 original failed reservations verify. All 2750
original files outside the nine scoped review edits remain unchanged; historical
handoff text is preserved. The [compact receipt](lp-billion-pr-validation.json)
binds the checks and added CPU charges under the existing reporting allocation.
No GPU seconds are added; all supervised PR work has empty cleanup and no overrun.

Five failed PR validations retain their full 19200 CPU-second charge: the
undeclared SciPy dependency, a missing Cargo cache selection, an incorrect
supplemental workspace selector, the remaining private inventory dependencies,
and an omitted tracked plan in the source-only snapshot. Their corrected checks
pass without regrading the failures. Integration stays below its 32000 CPU ceiling
and the existing 570000 CPU / 68000 GPU global limits.

The [initial hosted PR run](https://github.com/liuyumou/OptForge/actions/runs/45029602086)
reports `startup_failure` with zero jobs. The repository's documented local
CPU/docs/smoke fallback applies; local acceptance is not hosted success.
Protection configuration is neither changed nor bypassed. Final published-head
checks and the normal merge receipt are retained locally and reported on the PR.
