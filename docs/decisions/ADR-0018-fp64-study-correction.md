# ADR-0018: Preserve Failed Launches and Repeat the FP64 Study

Status: accepted implementation repair within the authorized GPUP-4 budget, 2026-09-15
Owner: numerical backend and experiment tooling
Introduced: GPUP-4 acceptance review
Supersedes: ADR-0017's single 320-attempt campaign extent only
Superseded by: none

## Evidence and decision

The original gpup4-tuned-fp64-v1 round completed all 320 attempts. A file-copy
mistake removed the archived reference executable's execute permission. Its first
24 timing attempts exited before solving. Restoring mode 0755 preserved the exact
archived bytes and enabled its remaining attempts. No failed attempt was retried
or overwritten. All raw stderr, worker, trial and ledger records are retained.
The round remains interim: eight instances lack a paired matched baseline.
It consumed 219094449232 additional GPU nanoseconds, bringing the canonical ledger
to 665082495136 ns. The first-round snapshot SHA-256 is
41e9bb277d23c35bec059fda85081d5da2337ccbe88faab0dba6e73660b98697.

Freeze one separate correction round, gpup4-tuned-fp64-correction-v1, before its
trials. Its eight configurations, all 12 development inputs, all three repetitions,
four profile inputs, ordering, seeds, targets, controller, deadlines, cleanup,
CPU affinity, 8 GiB limits and RTX 5090 UUID are identical. Repeat the complete
320-attempt schedule (280 GPU), including successful configurations; do not select
repeats by numerical result. Analyze the rounds separately, never pool or replace
first-round observations. If this correction is incomplete, retain interim status.
No further correction round is authorized by this decision.

The original configuration and artifacts remain immutable. The v3 campaign schema
admits exactly these two identities; the coordinator verifies that their protocol
objects differ only in identity. The correction archives its own source and current
executable. The original 722e0b0 matched executable and code object remain the
reference. Preflight execute permission before any reservation, and preserve modes
when archiving executables. The code object has not changed.

Final runtime review corrects observed peak buffer bytes when a stop or failure
occurs before all working allocations, caches launch configurations alongside the
kernel handles, and refuses executor/residency setting mismatches. These repairs
must pass the full native and device/sanitizer gates before the correction is
measured. They do not change iteration arithmetic or the shared controller.

## Budget and acceptance

This adds no GPU allowance. Both rounds and all failed launches consume ADR-0017's
same 900 additional seconds: original 445988045904 ns plus at most 900000000000 ns,
maximum cumulative 1345988045904 ns. Keep the original authority, output binding,
1800-second baseline phase and 28800-second campaign. Require full reservations;
exhaustion yields an interim handoff. Acceptance retains its separate limits.

Preserve first-round evidence and report its setup failure. Use only correction
round pairs for the final GPUP-4 latency comparison. A provisional control still
requires preserved certification coverage and paired end-to-end improvement;
otherwise retain matched FP64. No seed, numerical threshold, default, precision,
held-out experiment, external publication or additional budget is introduced.
