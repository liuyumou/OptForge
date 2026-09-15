# ADR-0015: Supplement the LP Baseline with Bounded Diagnostics

Status: accepted under the maintainer's instruction to measure and diagnose the slow GPU study
Owner: numerical backend and experiment tooling
Introduced: GPUP-2 diagnostic follow-up
Last reviewed commit: bootstrap (first commit containing this document)
Supersedes: none; supplements ADR-0014 without changing its frozen baseline
Superseded by: none

## Decision

Preserve the complete gpup-baseline-v1 grid, model/config hashes, trials, raw bundle
and historical ledger snapshot. Add explicitly diagnostic development measurements
under identity gpup2-diagnosis-v1; they cannot enter baseline medians or coverage.
Use the same original models, solver seed 17, one CPU core/thread, 1e-9 tolerances,
check interval 200 and published settings. The original solve implementation,
controller, preconditioner, kernels and certification remain unchanged.

Freeze seven supplementary GPU jobs before launch:

- One ordinary profiled solve each of small-4, irregular-256 and irregular-2048,
  with the original 50,000-iteration limit.
- One untraced and one Nsight Systems CUDA API/kernel trace each of small-4 and
  irregular-2048, explicitly limited to 200 iterations for bounded trace size.
  These short runs diagnose startup and kernel overhead; they are not solve-to-
  tolerance performance samples. All endpoints retain independent verification.

No warmups or retries. Job IDs include the diagnostic identity and purpose.
An attempted job is never silently repeated. Profiling overhead is part of the
charged job; traced latency is not an estimate of uninstrumented solve latency.
Use the installed Nsight Systems version with CPU sampling/context-switch tracing
disabled; inaccessible hardware counters remain unavailable.

Use GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48, the shared host lease, prelaunch activity
checks, ten-second soft deadline, two-second cleanup, 8 GiB RSS/device-buffer limits
and bounded output. Reserve 13 seconds before every job. The seven complete
reservations require at most 91 seconds; supplementary study cap is 120 seconds.
Append their reservations/settlements to the existing canonical baseline campaign
ledger under its unchanged campaign hash and baseline phase. This explicitly
extends the permitted ledger job identities, not the frozen baseline trial grid.
Keep its original output binding; a supplementary artifact directory is not a new
budget authority. Preserve 173.148261443 seconds of prior spending and all existing
phase/total limits. The new artifact bundle snapshots the cumulative ledger and
links the historical baseline snapshot. No budget reset, borrowing, device change
or unrecorded rerun is permitted.

CPU diagnostics use archived endpoints: component microbenchmarks on small-4,
irregular-256, irregular-2048 and dense_block-1024; and 50,000-step host replay of
the GPU's fixed anchors/weight on irregular-256 and scaling-64. Replay calls the
existing Engine::step_once and checks the final primal/dual against recorded GPU
bits. It is a differential diagnostic, not the GPUP-3 controller or a backend.
Fixed dyadic reduction fixtures compare existing tree/sequential operation costs
without changing numerical authority. Profile Python validation and reporting
separately from solver latency. Archive source/binary/profiler identities and raw
results; expose missing traces or failed comparisons rather than imputing results.

## Acceptance and handoff

Run the full pinned-native gate for committed diagnostic tooling. Check host replay
agreement, independently verified endpoints, trace operation counts, unchanged raw
baseline hashes, cumulative budget accounting and documentation links. The report
must separate measured facts from inferred optimization opportunities. Any solver,
certification or controller optimization remains a later bounded implementation
with its numerical acceptance requirements; this diagnostic selects no preset.
