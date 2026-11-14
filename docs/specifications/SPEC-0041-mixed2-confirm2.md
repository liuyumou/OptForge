# SPEC-0041: Complete MIXED2 confirmation after availability diagnosis

The user's active goal is to complete confirmation. An attempted but incomplete
cohort does not satisfy it. [ADR-0074](../decisions/ADR-0074-mixed2-confirm2.md)
authorizes continued diagnosis, necessary corrections and a fresh independent
confirmation after admission. Every earlier cohort, refusal, source version and
closed allocation remains exact; missing old cells are never repaired or pooled.

## Required end state

Complete a new, prospectively frozen 32-block balanced cohort: four families
(generic/coupled dense1024/2048), native window32 and FP4x2 window16, both original
1e-7/1e-9 tiers, four changing-model scenarios repeated eight times per session.
All 512 complete sessions / 16384 solves require original-model certification,
full setup/switch/delivery/EOF/destruction accounting, exact work/trajectory
comparison, and independent serial reassessment. A valid negative performance
result completes confirmation; missing coverage does not. Keep the unchanged
numerical executable/image and historical criterion. No public preset follows.

Use the exact SPEC-0039 statistical arithmetic: eight paired ratios and eight
absolute savings, Bonferroni alpha 0.05/16 exact median intervals; a scoped benefit
requires complete coverage, ratio lower bound above one and savings lower bound
above 10 ms/session. The separate 1.10x comparison is provisional. Preserve order,
first-16 sensitivity, shared-host/device assumptions and all unfavorable results.
Use seed 410074, chosen before any new scientific timing. Do not retry frozen cells.

## Availability diagnosis and admission

First distinguish scan time, timed pidfd wait, runnable delay and observer delay.
Use bounded in-memory phase records with monotonic and process CPU timestamps;
retain failed intervals and any capture limitations. Inspect cgroup quota/pressure
and per-CPU state as observations, not historical causal proof. Diagnostic tracing
must be absent from the final scientific configuration.

A correction must preserve four-CPU affinity/resource accounting, 16 GiB sampled
RSS, 12 GiB device buffers, independent death detection, cleanup, deadlines and
a finite sampling/freshness/scan-duration limit. The user explicitly permits
changing or waiving the old 100 ms limit if it is inappropriate. Adopt a
prospective one-second hard limit, with the 100 ms exceedances retained as
observations. CPU phase diagnostics and 39 refusal/cleanup contracts support this
finite operational choice; they do not prove a historical stall cause or future
availability. Keep the 5–10 ms sampling target and report actual gaps. The
[report](../benchmarks/lp-mixed2-confirm2.md) records the rationale and tradeoff. Sampled RSS cannot prove a
sub-sample peak at either threshold; retain that limitation and memory headroom.
Do not regrade old refusals or describe an actual delay as uninterrupted sampling. CPU placement or notification
changes require versioned fault contracts and source-bound native admission.
No host-wide scheduling settings or unrelated processes may be changed.

Admit correctness and operational behavior before freezing: existing supervision
contracts plus targeted reproduction/fault tests, full repository/native gate,
fresh exact device/scenario smoke and three full-size resource pilots.
Reuse existing numerical/device/four-sanitizer admissions only for exact unchanged
sources/images. Retain failures and full reservations. Successful short probes do
not prove future availability; ensure evidence is materially stronger than the
previous single passing pilot. Freeze execution, placement, criteria and sources
only afterward. A source change cannot repair a frozen scientific cohort.

## Independent resources and delivery

New independent ceiling: 96000 CPU / conditional 12000 GPU seconds; no historical
transfer. CPU phases: implementation 8000 (512 preparation), diagnosis 14000,
native 12000, acceptance 8000, confirmation 40000, reporting 12000, cleanup 2000
(128 closing administration). GPU phases: acceptance 1800, confirmation 10200.
Four CPU slots, one pinned shared GPU lease and the existing resource limits.
Reserve whole blocks prospectively, at most 300 GPU / 1200 CPU seconds each.
Receipts: `artifacts/gpup-mixed2-confirm2-v1`. Failed reservations retain their full
charge and immutable development sources. Old allocations stay closed.

Deliver diagnostic evidence and limitations, the complete confirmation result,
independent checking, portable records/replay, exact historical preservation,
final accounting and a local commit. Keep this goal active if coverage is still
incomplete. No push, public-default change, GPUP-8 completion or GPUP-9 release.
