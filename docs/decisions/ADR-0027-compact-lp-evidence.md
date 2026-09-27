# ADR-0027: Compact Study LP Evidence

Status: accepted by the maintainer on 2026-09-27 before implementation.
Scope: GPUP-EVIDENCE under SPEC-0015 and SPEC-0013; gpup-evidence-v1.

## Decision

Implement the user-approved compact study-only envelope in SPEC-0015. Omit only
recomputable validation details, retain their nullable SHA-256 and the original
endpoint/payload identity, reconstruct and independently verify on the host.
Compact solve prints an assessment instead of duplicating a full record on stdout.
Ordinary solve, legacy defaults, numerical algorithms and code objects are unchanged.
Add study verify/replay support and explicit verified transcode without solving.

CPU validation comes first. Use retained complete witnesses and explicitly synthetic
canonical-zero candidate/dual, work-limited codec fixtures for missing full-witness
extensions. Synthetic fixtures are not solver results. Measure sizes, writes and
independent verification on all four extension models; compact full witnesses must
fit the unchanged 32 MiB cap. Preserve original files and derive separate artifacts.

## Frozen live comparison

Twenty-four fresh timings: the four unchanged development extensions, tuned FP64,
legacy versus compact-v1 output, three repetitions. Use the COPT study's tuned
resident/necessary/warp32_v1/separate execution, original method settings, seed 17,
threads one and CPU affinity [0], all tolerances 1e-9, 50000 updates, 30-second
solve deadline, two-second cleanup, 8 GiB host/device bounds and 32 MiB output cap.
Model/evidence reads explicitly allow 128 MiB; independent CPU verification is
bounded at 120 seconds. Blocked format order uses seed 17001. Paired median ratios
and 95% bootstrap intervals use seed 17002 and 10000 resamples. No retry, relaxed
limit, historical timing replacement, external solver study or held-out evaluation.

Regular device acceptance and fixed-work legacy/compact pairs cover tuned FP64,
fixed FP32 accumulation and gradual adaptive recovery on small-4 and irregular-2048,
including compact replay. Compare numerical bits excluding timing/profile observations.
Existing sanitizer receipts cover only unchanged kernels; retain the tuned_cases gap.
Freeze source, schema snapshot, binary and all four discovery/execution code images
before admission. Independently verify every retained complete endpoint.

## Authority and budgets

Starting charge 14766435441716 ns; 15340 events; prefix SHA-256
5cf76ffbea09e21fdf21692c4030f8176ae5ef7f481c2e5c6e83fe302371b51b.
Preserve ADR-0026's cumulative ceiling 18002574545061 ns, the original 28800-second
campaign cap, every phase cap and the original campaign/output binding. Additional
allowance is zero. Allocate timing 900 seconds in ablations and acceptance 300
seconds in repeatability, combined 1200 seconds; no cross-category borrowing.
Each timing reserves 30 + 2 + 4 = 36 seconds, 864 for all 24 attempts. Admission
reserves full bounds; uncertain/failed work is charged and all identities retained.
Use the shared host lock for every device job. Four build jobs and at most four
CPU-hours for build, validation and analysis, with measured receipts and CPU-only
worker costs separate from GPU lease time.

## Acceptance and handoff

Run the full pinned-native gate, strict codec/CLI/schema/authority checks, the CPU
size/write/verification study and applicable device checks before reporting results.
Keep coverage, certified success and latency eligibility separate. A timeout or
numerical rejection can verify but cannot become certified completion. Retain
partial files, all failed attempts and paired-comparison gaps. No latency gain or
universal 65536-row convergence is required for accepting the representation.
Document outcome, consumption and limitations; commit locally after acceptance,
then select GPUP-HOST. No push or external publication is authorized by this task.
