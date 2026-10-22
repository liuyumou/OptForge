# ADR-0038: Selected-device activity telemetry

Status: accepted operational repair within GPUP-REFINE, 2026-10-22
Owner: experiment supervision
Introduced: GPUP-REFINE continuation
Last reviewed commit: bootstrap
Supersedes: the global process-query implementation, not the idle-device policy

## Context and decision

ADR-0037's first regular acceptance identity was refused before child/context
launch. The selected RTX 5090 reported zero utilization, but the global process
query returned `N/A` process data for an unselected PRO 6000. The existing reader
validated every global row before selecting the requested UUID, so unrelated
unavailable telemetry prevented admission. An exact selected-UUID process query
succeeds and returns an empty process list. The raw queries and failed worker
remain in artifacts/gpup-refine-v1, with all frozen source and binaries intact.

Scope the process query to the same selected UUID as the utilization query.
Retain strict parsing of every returned row, valid positive PIDs, zero utilization
and no selected-device processes. Unavailable/malformed selected-device telemetry
still refuses. Keep the same shared host lease, admission deadline, cancellation
and no-concurrent-device policy. This repairs evidence acquisition; it does not
ignore malformed rows, relax an idle threshold or authorize another device.

## Preserved refusal and continuation authority

The original gpup-refine-v1-accept-regular identity remains activity_blocked,
with no child return code, zero child elapsed time and zero sampled child RSS.
Its charge is 0.125948387 seconds. All 108 v1 primary cells and six other
acceptance gates remain unexecuted, with no retries or relabeling.
The exact 16454-event ledger SHA-256 is
900bbaed980f273db069819028e48ee8c896024e4492ade21382199b78ae8e6e;
cumulative consumption is 17665.672031998 seconds. Preserve the original
16452-event prefix 24949150272600fe58364f25ebbf7bf892f7454da342edc268d50684568c5f18.

Freeze a separately identified gpup-refine-v2 continuation on the same
GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48 after the repaired exact-source full
native gate. No numerical worker, kernel, model, seed, tolerance, roster,
controller parameter or deadline changes. All Rust/CUDA sources and executable/
image bytes remain identical. Changes to existing files are limited to the
activity reader, cohort budget/report binding, their CPU regression tests and
active-task documentation; the new protocol/schema/decision record the repair.

The user-approved 3600-second task allocation and cumulative/phase ceilings do
not increase. Give v2 integer caps timing 2300, profiles 450 and acceptance 849,
combined 3599 seconds. Including the original charge stays below 3600 overall
and 850 acceptance seconds. The remaining fractional headroom is not reserved.
Worst-case initial v2 reservations remain 2256/432/762 seconds, inside all caps.
Every primary identity is new and unattempted; none is a numerical retry.
Retain all failed gates and raw evidence alongside the continuation result.

## Acceptance

CPU regressions require both management queries to name the selected UUID and
still reject unavailable selected utilization, malformed rows and invalid PIDs.
Preserve the first worker/request/source/charge bindings and independently verify
both historical prefixes. Freeze the unchanged executables and images with the
new source archive; then require all 66 regular tests, refinement differentials,
replays and four scoped sanitizers before any primary trial. Report the original
refusal and continuation separately, with their combined GPU consumption.
