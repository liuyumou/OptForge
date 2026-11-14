# SPEC-0034: Independent delivery mechanisms and scoped confirmation

Status: implementation, 2026-11-12
Decision: [ADR-0067](../decisions/ADR-0067-delivery3.md)
Prospective protocol: [DELIVERY3](../plans/lp-delivery3.md)

## Execution contract

Create an isolated lp-delivery3 executor. Immutable process configuration selects
control, batching only, startup overlap only, or both. Default to the control;
reject unknown values and conflicting historical overrides. Apply each setting
equally to nativefast/gridfp4x2 and both final tiers. The numerical state machine,
original-model checker and device image remain exact imports from prior work.
Preserve exact endpoint serialization, signed zeros, bounded frames, fresh checks,
receipt bindings, poisoned failed connections, EOF and owned startup cleanup.

Optional diagnostic instrumentation records parent setup intervals, checker
startup/decode/assessment/output durations and parent request/response durations.
Streaming serialization and writing remain one inseparable measured span in the
unbuffered control; do not invent a decomposition. Child durations and parent
intervals are overlapping views, not quantities to sum into complete time.
Uninstrumented timing determines candidate selection and confirmation.

CPU admission includes every retained serial endpoint, four configurations,
configuration errors, malformed/truncated inputs and fresh checker lifecycle.
Run the full native gate and isolated package checks. Device admission covers all
four configurations and instrumentation, exact numerical comparisons, complete
checkpoint/cancellation/recovery and startup failure cleanup. Reuse sanitizer
admission only for the exact unchanged device image and source bindings.

## Diagnostic and confirmation manifests

Freeze two separate diagnostic cohorts: two instrumented blocks (256 lifecycle
cells) and four uninstrumented blocks (512 cells), four families from the plan,
four configurations, both lanes/tiers and cold/prepared. Prepared cells contain
three fresh solves. Randomize within recorded balanced blocks. Keep profile
results separate from the uninstrumented selection data.

For cold selection, choose the variant with the highest dense512 geometric mean
of paired complete-time ratios over all blocks, lanes and tiers, requiring at
least 1.01x; otherwise choose control. For prepared selection, require at least
1.02x over all four diagnostic families and no diagnostic family/lane/tier median
increase beyond max(2%, 0.10 ms); otherwise choose control. Use variant order
control, batch, overlap, combined for exact ties. These exploratory rules select
one configuration per lifecycle; they do not establish retention.

Freeze the chosen candidates, full schedule and reducer before confirmation.
Use the plan's 32 blocks / 6144 lifecycle cells, including 9216 prepared solves
and 3072 cold solves. Each block contains 192 cells and runs under its own
whole-job reservation. A started block/cell cannot be rerun. Admission checks
sources, disjoint identities, exact historical numerical evidence and matched
control/candidate results. All 96 declared metrics use simultaneous 95% median
intervals (ranks 6 and 27 with 32 blocks); target >=1.10x, per-family allowance
max(2%, 0.10 ms), and explicit unsupported/inconclusive outcomes. Refusals remain
in coverage; every bounded family must certify. Record environment/device state
at block boundaries and label limitations of independence and generalization.

## Independent resource allocation

CPU ceiling 64000 seconds: implementation 10000 (512 conservative preparation),
native acceptance 12000, device/CPU acceptance 6000, diagnosis 8000,
confirmation 24000, reporting 3000, cleanup 1000. GPU ceiling 7800 seconds:
acceptance 600, diagnosis 1200, confirmation 6000. Four CPU slots, 16 GiB sampled
RSS and at most 12 GiB device buffers, one pinned shared GPU lease, unchanged
in-container supervisor. Confirmation reserves at most 32 whole 180-second GPU /
720-second CPU blocks (5760 GPU / 23040 CPU), leaving phase headroom. Diagnosis
reserves six whole 180-second blocks (1080 GPU / 4320 CPU); admission fits its
separate phase. Full failed/unsettled jobs remain charged, with archived source
versions. No historical transfer or automatic frozen scientific retry.

Artifacts: artifacts/gpup-delivery3-v1. Preserve prior files except current
navigation/handoffs. Report all variants, failures, coverage and per-route
retention. Public defaults and TENSOR2's separate criterion remain unchanged.
Commit locally after delivery; no push, publication or GPUP-9 release.
