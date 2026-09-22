# ADR-0024: Throughput Review Corrections and Independent Variant Controls

Status: accepted by the maintainer's explicit request to fix the review findings,
2026-09-22. Scope: corrective GPUP-THROUGHPUT work under SPEC-0014.
Supersedes: none; corrects implementation and evidence under ADR-0023.

## Decision

All tuned outcomes, including cancellation and device failure, receive the same
versioned execution identity. Batch verification requires common method settings
and execution/code identity across attempted records, and refuses fallback or
missing tuned identity. Binary64 primal/dual comparisons preserve signed zero.
These repair existing requirements without changing the mathematical method,
record schema or valid historical record semantics.

A new frozen follow-up protocol, lp-throughput-controls-v1.json, uses the existing
protocol-v3 fields with one new explicit block kind, fresh-variant-single. This
kind materializes each selected variant using the Rust materializer before the
measured worker starts, then launches the ordinary solve entry point on those
exact bytes. The original fresh-variant kind retains its N=1-session meaning for
historical reconstruction. New analysis names the historical controls accurately
and compares the corrected controls to the retained variant session records.
It never overwrites the old analysis or claims a control that was not executed.

The follow-up contains the original block G's 48 cells: eight development witness
instances, variants 0 and 7, one repetition, tuned FP64 and both research modes,
tier 1e-9. Seeds, generator, method, tolerances, code objects, ordering and limits
remain the original protocol's. Materialization is CPU-only; every GPU attempt,
including failures, is reserved and charged through the existing supervisor.
No validation/held-out work, supported preset, warm start or adaptive recovery.

## Existing resource authority, no additional allowance

The new protocol uses prefix gpupt and the same category caps (study 2700 s,
acceptance 600 s, combined 3300 s), prior 6722-event ledger commitment and
3794.758955639 prior seconds. It retains source campaign lp-precision-v4,
additional_gpu_seconds 3600 and cumulative ceiling 8102.574545061 s. Those are
the already accepted ADR-0023 ceiling authority, not a second addition. The
new protocol names this decision, which explicitly preserves that authority.
Admission includes all previous gpupt study/acceptance charges.

At selection, 8178 events and 6951.059845871 seconds are preserved, SHA-256
`dd957404ed65763775afba63bc11f8b03ffa9c64dcad19112f76fc9b1f5f32f6`.
Only 82.070540459 study seconds and 61.628569309 acceptance seconds remain.
Exhaustion records missing evidence, never another allowance. CPU validation is
bounded by four hours and four build jobs. No old protocol, archive or ledger
prefix may be rewritten.

## Acceptance

CPU tests cover all outcome identities, mixed method/code refusals, fallback and
missing-identity refusals, signed-zero comparison and the actual fresh-control
command route. Scoped GPU acceptance checks cancellation evidence and session
identity without changing kernels; existing sanitizer receipts remain historical.
All admitted fresh controls are independently verified and compared by binary64
bits to the retained session evidence. Reports separate old N=1-session controls
from ordinary single-solve controls and retain missing comparisons. Full pinned
native tools/check.sh passes before measurement and on final source.
