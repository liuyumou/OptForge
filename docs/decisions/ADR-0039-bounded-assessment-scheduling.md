# ADR-0039: Bounded original-model assessment scheduling

Status: accepted bounded implementation contract; CPU admission passed, 2026-10-22
Owner: numerical backend
Introduced: GPUP-ASSESS
Last reviewed commit: bootstrap
Superseded by: none

## Decision

Accept the bounded assessment subset of SPEC-0021 requirements 12–20 after CPU
common-trajectory admission. Cheap indicators have scheduling authority only;
original-model host feasibility, certification and conservative gap remain the
sole publication authority. A negative result is a valid bounded outcome.

Use tuned FP64 and the existing accumulation-FP32 configuration: FP32 coefficients,
operands, products and accumulation, with FP64 updates/state and no correction
interval. Preserve original preparation, recurrence, guards, controller and
200-update restart/weight boundaries. Reuse unchanged CUDA images and executors.
No adaptive/refinement integration, promotion, recovery, sessions or preset.

The fixed_200 control assesses every 200-update boundary. The bounded_800 policy
also assesses the first boundary. At each boundary sample scaled primal and dual
movement against the preceding sample. For each coordinate let
s=max(1,abs(current),abs(previous)) and use abs(current/s-previous/s); take the
maximum. Division before subtraction prevents overflow for finite inputs.
Request assessment when a positive last-assessed indicator falls by a factor
of at least two, or 800 updates have elapsed since assessment. A zero reference
uses the spacing rule; an invalid indicator forces assessment. Underflow or a
misleading zero cannot certify or infer convergence. A partial final interval is
always assessed on a safe current endpoint; do not silently return a stale point.
Freshly reassess the published final witness even when it was just checked.

Diagnostic trajectories continue after certification solely to compare schedules
on common states. Record saved checks, delayed discovery, missed transient success
and censored horizons. No delay bound follows for a transient certifiable point.
CPU and profile estimates are separate from actual fresh-process timing.

Scheduler snapshots include prior vectors/sample index, last assessment/reference,
policy and immutable-engine identity with the full controller checkpoint. Logical
state restores together; physical work, actual checks and deadlines never roll
back. Cancellation, deadline and device/numerical failure keep their stop reason;
final certification cannot start recovery or turn an interruption into success.

## Interface and admission

Add feature-gated lp-assess-v1 requests/evidence and lp_precision_assess
solve|verify|replay|trace-cpu|replay-trace. Bind model/settings, source, executable,
CUDA image and selected/executed device; record logical/physical work, scheduling,
controller checks, host assessments, failure and costs separately. Old formats,
selectors, defaults and unsafe boundaries remain unchanged; no toolkit is needed
by ordinary builds. CPU trace/replay and verification require no device.

CPU admission uses both arithmetic modes and the eight frozen GPUP-EXEC models,
up to 4000 updates or first numerical refusal. Independently replay both policies
and freshly assess every boundary; preserve the unchanged proposal/controller
trajectory. Expected arithmetic refusals remain evidence. A contract mismatch
blocks dependent execution with its counterexample and no GPU claim.

CPU admission passes all 16 4000-update trajectories in 545.510899 CPU seconds,
with 493043712 bytes maximum child RSS and zero GPU work. The reviewed
[receipt](../benchmarks/data/assess/cpu-admission.json) includes mandatory final
assessment in discovery accounting and preserves the original trajectory archive.

## Resource authority

Allocate 2300 seconds inside the unchanged 21602.574545061-second cumulative
ceiling: 1300 screening timing, 450 ablation profiles and 550 repeatability
acceptance. Preserve phase caps baseline/screening/ablations/repeatability/finalists
1800/9500/7650/4450/9000 and the overall 28800 seconds.
Prior charge is 19207.265220123 seconds and the 16684-event prefix SHA-256 is
e83d07792fb0775fc26d8d2cca8a2411f59fcbc94f742cafd8f6b844ffb60535.

Freeze two arithmetic modes by two policies on small-4, irregular-2048,
irregular-32768 and mixed-65536 with three timing repetitions. Preserve seed 17,
1e-9 tolerances, numerical settings and 50000-update work limits; deadlines are
10 seconds on development and 30 on extension models. Twelve 2000-update
profiles use irregular-2048, irregular-32768 and mixed-65536 at 30 seconds.
Order seed 17001 and analysis seed 17002 remain. Deadline+6 reservations total
1248 timing, 432 profiles and 516 acceptance (two 120-second and four 60-second
jobs). Every failed/refused attempt is charged and identities never retry.
Use only GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48, selected-device admission and
the shared host lease; no device substitution. CPU cap 21600 seconds/four jobs,
host RSS 8 GiB, device buffers 1 GiB, new artifacts 32 GiB. Admit vector/snapshot
and bounded trace storage before allocation. Unused resources reserve nothing.

## Acceptance

Independent CPU policy replay and original-model assessments; deceptive/zero
indicators, subnormals, finite-range motion, transient success, partial limits,
checkpoint identity/restoration, cancellation/deadline and guard paths; strict
corruption/missing-witness tests; historical replay and certifier regressions.
Run full pinned-native tools/check.sh, 66 ordinary device tests, six fixed-work
policy pairs with twelve same-device replays on small-4/irregular-256/scheduling,
and memcheck/racecheck/initcheck/synccheck. Freeze exact sources, executables,
images and requests before GPU attempts; preserve every outcome and total cost.
Record report/evidence, known limitations and a local commit before GPUP-7 handoff.
