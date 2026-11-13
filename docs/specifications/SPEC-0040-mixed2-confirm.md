# SPEC-0040: Complete independent MIXED2 confirmation

The user's instruction to complete confirmation authorizes reliability correction,
admission and a new independent cohort under [ADR-0073](../decisions/ADR-0073-mixed2-confirm.md).
SPEC-0038/0039 incomplete cohorts, failures, sources and closed allocations remain
exact. No old cell is retried, replaced, pooled or retrospectively regraded.

## Supervision and admission

Investigate guardian observation latency separately from actual sampling gaps.
The historical supervisor checks its local receive timeout before draining queued
control messages. Reproduce a guardian scheduling pause while the coordinator
continues sampling, and distinguish a paused/dead coordinator. A separate version
may correct this ordering using validated monotonic sample timestamps; preserve
the original source. Keep the 100 ms sampling/freshness limit, independent death
checks, wall deadline, four-CPU charge, memory/affinity checks, immutable failures
and complete descendant cleanup. A delayed observer must never turn a genuinely
stale, discontinuous or malformed heartbeat stream into a pass. Record control
observation gaps separately. Admission includes fault injection, old/new behavior,
resource contracts and full CPU/native acceptance before device execution.

Publish the sample-start timestamp at the start of its scan. Sending it after the
scan can make two valid scans appear stale even when their start-to-start cadence
is below 100 ms. Admit this boundary with controlled 60 ms scans; retain the
earlier implementation and every refusal. Require scan work itself to finish
within 100 ms, including the terminal scan, as well as the existing cadence and
guardian freshness checks. A progress notification cannot authorize successful
completion before resource checks and the bound terminal receipt. Keep other
coordinator resource, cadence, deadline and cleanup logic exact. Controlled
reproduction does not establish the cause of uninstrumented historical failures.

The numerical Rust executable, CUDA image, scenario models and request transport
remain the admitted SPEC-0039 versions. Bind and reuse their CPU/device and four
sanitizer admissions only while their source/image identities remain exact.
Perform fresh original-checker/scenario lifecycle smoke under the corrected
supervisor and a full-size resource pilot before freezing scientific timings.
Successful probes establish tested behavior, not a historical root cause or a
universal availability guarantee. No public default or production-readiness claim.

## Independent confirmation

Freeze 32 balanced randomized paired blocks with seed 400073, four families
(generic/coupled dense1024/2048), two final tiers (1e-7/1e-9), two lanes
(native window32, FP4x2 window16), fixed maximum-200 audits. Each fresh session
cycles the same four independently checked RHS/objective scenarios eight times.
The primary endpoint includes all parsing/cache/checker/representation setup,
switching, 32 certified solves, durable responses, EOF and destruction. Persistent
state resets each solve; this is a constructed reuse stream, not a warm start or
production trace. Both lanes receive identical orchestration and placement.

All 512 sessions / 16384 solves are planned in advance. No scientific retry,
selective exclusion or outcome-dependent stopping. A scientific failure stays
visible and suppresses the complete-coverage decision; untouched cells may run
only under the unchanged freeze and valid resource admission. Source or supervisor
changes after freeze require a separate version and never repair this cohort.

Reuse the exact SPEC-0039 arithmetic: eight block-paired session ratios and eight
absolute savings, exact median rank intervals with Bonferroni alpha 0.05/16.
A scoped benefit requires complete coverage, every original-model certificate,
ratio lower bound above parity and savings lower bound above 10 ms/session.
1.10x remains a separate provisional comparison, never automatic adoption.
Retain first-16, order splits, all block/environment observations and complete
cost partitions. Shared-device independence assumptions remain explicit.

## Independent resources and delivery

Initial independent ceiling: 80000 CPU / 9000 GPU seconds. A prospective CPU-only
admission extension adds 10000 native CPU seconds after two notification-freshness
refusals, giving a final 90000 CPU / 9000 GPU ceiling. Preserve the original
manifest versions and both full failed charges; no closed historical allocation
is reopened or transferred. The extension is for completing this user's requested
confirmation after diagnosis and new placement admission, not scientific retries.
CPU phases: implementation 10000 (512 preparation), diagnosis 8000, native 20000, acceptance 6000,
confirmation 28800, reporting 14000, cleanup 3200 (128 closing administration).
GPU phases: diagnosis 400, acceptance 1200, confirmation 7400. Each frozen block
reserves at most 220 GPU / 880 CPU seconds; all 32 fit. Four CPU slots, 16 GiB
sampled aggregate RSS, at most 12 GiB owned device buffers, one pinned shared GPU
lease. Receipts: `artifacts/gpup-mixed2-confirm-v1`. Charge failed reservations in
full, preserve every source version, and never transfer historical funding.

Deliver the actual complete/incomplete result, uncertainty, supported diagnosis
and limitations, independent serial reassessment of retained endpoints/audits,
portable evidence/replay, native acceptance, exact historical preservation and
local commit. No push, public preset, GPUP-8 completion or GPUP-9 release.
