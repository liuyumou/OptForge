# ADR-0032: Convergence and Work-Amplification Diagnosis

Status: accepted by the maintainer on 2026-09-30 before implementation.
Scope: GPUP-CONVERGENCE, development-only study under SPEC-0013.

## Decision

Freeze gpup-convergence-v1 with 176 attempts. Preserve runtime arithmetic,
controller, code objects, solver defaults and all historical protocols/evidence.
Use the ADR-0026 settings for tuned FP64, precision FP64, accumulation FP32,
adaptive FP64, sticky accumulation-to-FP64 and gradual working-state demotion,
plus fresh COPT CPU/GPU PDLP through the unchanged scalar wrapper. No implicit
tuning, tolerance relaxation, new numerical mode or supported preset is authorized.

Timing: three repetitions for small-4, irregular-2048, irregular-32768 and
dense_block-65536 (96); one for mixed-65536 (8). Bounded profiles: six project
configurations on small-4, irregular-2048, irregular-32768 and mixed-65536 at
200 and 2000 physical updates (48). Full profiles: all eight configurations on
irregular-32768, dense_block-65536 and mixed-65536 (24). Run timing repetition
zero, bounded profiles, full profiles, then timing repetitions one and two.
Deterministically order configurations using seed 17001 in each model/block.

Use unchanged development manifests, seed 17, one solver thread, 1e-9 final
absolute/relative tolerances, check interval 200, 50000 full-run work limit,
10-second ordinary / 30-second extension deadlines and two-second cleanup.
Only bounded diagnostics replace both recorded work limits with 200 or 2000.
Stopping, guards, audits, rollback and charged probes remain active. Equal
allowances need not execute equal work. COPT native counts are not project updates;
its unavailable hard PDLP iteration/seed controls remain explicit.

## Evidence and reporting

Use compact-v1 project endpoints and unchanged external v2 evidence. Freeze
source, release binary, schema snapshot, model/request/effective configuration,
all four discovery/execution images and existing COPT environment identities.
Never archive licenses. No graph-node traces or hardware counter changes.
Fresh process launch through certification/output is primary latency. Profiles
and short work remain diagnostics. Verify every complete endpoint against the
original model; verification of a failed outcome does not make it a timing success.
Retain partial bytes, interruptions, unknown metrics and every admitted identity;
never retry admitted study attempts. Recover conservatively without success promotion.

Report physical work as proposals + reference audits + demotion probes for adaptive
runs. Rejected/replayed proposals overlap proposals and are not additional work.
Keep per-rung counts, logical progress, step/bounds, restarts and assessments.
Separate preparation, reference arithmetic, audit comparisons, probes, device work,
certification/output and unattributed residuals. Do not double-count nested wall
scopes or combine host wall time with device activity. Normalize only matching
recorded units, with zero/missing denominators unavailable. Historical evidence
is separately labeled. Paired certified timing ratios use seed 17002, 10000
bootstrap resamples and 95% intervals; a single pair has no interval.

## Resources

No added allowance. Timing cap 800 GPU seconds in ablations; profiles 800 and
acceptance 300 in repeatability; combined 1900, no borrowing. Preserve all original
phase caps, 28800-second campaign authority and cumulative ceiling 18002574545061 ns.
Carry 15804186067059 consumed ns and all 15776 events, SHA-256
2b99b615dc77da07fb078e1cefc188d2131db5ca671fe9b86f989a6d660606f0.
Chain the prior adapter protocol without rewriting its authority or output binding.
Complete reservations include supervisor/admission/cleanup; stop exhausted categories
and report unattempted cells. Every GPU job holds the shared host lease, sequentially.
Use four build jobs, 14400 CPU seconds, 8 GiB host/device limits, 128 MiB model limit,
32 MiB per-file output and 120 seconds per independent verification.

## Acceptance and handoff

Require exact-source full pinned-native tools/check.sh before GPU admission and
at completion. Source-only tests cover schedule/configuration substitution,
compact/external checks, work/nested costs, chained phase/cumulative caps,
ledger prefixes, partial recovery and no retry. Run existing regular device tests;
six project configurations on irregular-256 and irregular-32768 at 2000 updates
with profile off/on and replay (12 pairs, 12 replays). Acceptance deadlines are
30 seconds, separate from primary timing. Require COPT CPU/GPU min/max with
profile off/on (8 endpoints), offset preservation and original-model certification.
Carry sanitizer evidence only for unchanged runtime/kernel bytes; historical
racecheck/session/mixed-model limitations remain visible.

Produce independent JSON/CSV and static work/cost figures, distinguish measurements
from hypotheses, and give bounded GPUP-7 implications without implementing it.
A resource stop or solver failure is a retained diagnosis, not permission to widen
limits. Update evidence/state and commit locally; no push or external publication.
