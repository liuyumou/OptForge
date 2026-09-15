# ADR-0016: Matched FP64 Control and Measured Overhead Repairs

Status: accepted by the maintainer's implementation instruction, 2026-09-15
Owner: numerical backend and experiment tooling
Introduced: GPUP-3 and bounded GPUP-2 follow-ups
Supersedes: none; supplements ADR-0012, ADR-0014 and ADR-0015
Superseded by: none

## Decision

Deliver schema/activity repair, bit-preserving host certification optimization,
then GPUP-3 as sequential bounded changes. Preserve legacy cuda-lp control and
host trajectories. Accept SPEC-0012 for shared in-memory FP64 continuation now;
later precision, audit/recovery and persistent checkpoint interfaces remain pending.
Expose cuda-lp-matched explicitly; no default or legacy backend replacement.
Use shared host restart/weight decisions and unchanged GPU kernels. Checkpoints
contain all continuation state; physical work and elapsed deadlines never roll back.
Original-model evaluation, outward certification and conservative gap assessment
remain mandatory. Preserve candidate/dual assessment alignment at partial limits.

Specialize only outward reduction: retain the 1,024-element partition, meaningful
addition order, signed-zero semantics, enclosure/rounded bits and refusal behavior.
Keep a literal padded differential oracle and independent exact-rational regressions.
Do not reduce certification frequency or omit independent final checks.

Compile one immutable strict schema snapshot/registry per process and cache its
validators. Validate every document and cross-document identity/hash rule. New
processes observe schema changes; explicit fresh registries support isolated tests.
Record the schema snapshot hash in new study provenance. Existing version-1 schemas
and artifacts stay unchanged. Campaign/trial v2 describe binary selection and GPU
admission; endpoint v2 adds matched controller/work evidence. Solve records retain
their format, and legacy endpoint v1 remains readable and emitted by legacy solves.

Before reserving a GPU trial, wait for zero utilization and no compute processes
on the selected UUID: 250 ms polling, at most 300 seconds, cancellable. Missing or
malformed telemetry pauses. Do not assume a positive sample belongs to this study.
Recheck under the shared lease for at most three seconds. Persistent activity
retains a blocked attempt and pauses. Reserve 16 seconds per GPU attempt (3 admission,
10 solve, 2 cleanup, 1 supervisor overhead). Charge all lease-held time; separate
activity, lease queue and fresh solve-process timings. Never silently repeat an attempt.

## Frozen supplementary study

Identity: gpup3-matched-fp64-v1. Compare reference e415918 cuda-lp, current cuda-lp,
current cuda-lp-matched and current host-lp, each with separately hashed binaries.
Use all 12 frozen development instances, three timing repetitions. One separate
profile per configuration on small-4, irregular-256, irregular-2048 and
dense_block-1024. No warmups, retries, validation or held-out solves. Keep the
ADR-0014 model hashes, settings, 1e-9 targets, seeds 17/17001/17002, one CPU thread,
50,000 iterations, check interval 200, 10+2-second deadline and 8 GiB limits.
Use 10,000 paired bootstrap resamples and 95% intervals with failure coverage.
Reference/current legacy isolates certification; current legacy/matched isolates
controller behavior. Measure schema overhead independently of solver latency.

Allocate at most 600 additional GPU study seconds. Extend the existing canonical
budget ledger under its unchanged baseline authority/hash, as in ADR-0015, using
distinct gpup3-prefixed job identities and separately hashed supplementary protocol.
Carry forward 194.142866023 seconds; never reset consumption or overwrite the
original output binding. Preserve cumulative 900, baseline phase 1,800, total
28,800 and all other phase allocations. Device:
GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48. Acceptance is separately capped at 60 CPU
wall minutes/four build jobs and 30 GPU minutes, sequential with CPU gates.

## Acceptance

Full native tools/check.sh; strict/cached schemas, activity/lease/deadline/crash
simulations; bitwise padded/rational numerical tests; full controller trajectories,
checkpoint/history/cancellation/work tests; corrupted evidence and both senses;
regular device suites and relevant new tests under all four sanitizers. Report
hashes, reproduction, measured gains and limitations. An incomplete study is interim;
an unfinished gate never advances the backlog. Commit accepted bounded work locally.
