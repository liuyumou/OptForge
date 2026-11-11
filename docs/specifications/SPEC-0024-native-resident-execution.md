# SPEC-0024: Matched resident native FP64 execution

Status: accepted for the user-requested GPUP-RESIDENT2 implementation, 2026-11-11
Scope: research feature only; no public backend or default change
Owner: CUDA runtime and experiment tooling
Introduced: GPUP-RESIDENT2
Last reviewed commit: 4e62cab04ca2236d419c2deea4063a42a4f519ef
Implementation: [runtime](../../crates/optimizer-lp-cuda/src/resident2.rs), [study](../../tools/lp_resident2_study.py)
Tests: [CPU contracts](../../tests/integration/test_lp_resident2.py), runtime CPU/device tests
Decision: [ADR-0053](../decisions/ADR-0053-native-resident-execution.md)

## Purpose

Attribute complete delivery costs before evaluating bounded resident submission.
Native FP64 arithmetic and original-model host certification remain authoritative.
This task does not reopen GPUP-8 or release GPUP-9.

## Requirements

1. The driver MUST record disjoint monotonic host phases: read/conversion, immutable preparation,
   device context/import, native solve (including required controller assessments),
   endpoint export, independent checking, and durable output. Nested native costs
   are diagnostic subsets, never added again to total. Parent process elapsed
   includes startup, teardown and output; unattributed residual stays visible.
2. Cold workers MUST construct all state anew. Prepared workers reuse only immutable
   model/preconditioner and device invariant residency; each solve starts from
   projected zero with fresh controller, working buffers and certification. Report
   amortized prepared throughput separately from cold latency. No warm iterates.
3. The experiment MUST use a separate source/image and explicit `control`/`resident` mode. Both use
   warp32 fused native FP64 arithmetic, exact original matrix and coefficients,
   original host restart/weight logic and 200-update checks. No tolerance change.
4. The executor MUST precompute at most 200 pairs of binary64 Halpern coefficients using the exact
   control expressions. Upload once per bounded window; step/weight is unchanged
   within the window. Reject nonfinite/nonpositive steps, overflow and bad shapes.
5. The executor MUST submit at most 200 updates before observation, polling cancellation every 64
   submissions and before/after readback. Kernel work is ordered on one stream.
   Observation copies synchronize already required work; timing adds no device
   synchronization. Cancellation latency is bounded by one 200-update window,
   not a wall-time promise; the supervisor enforces absolute job deadlines.
6. Per-coordinate sticky integer flags MUST latch nonfinite intermediates. One lane
   owns each flag; no floating atomic accumulation. A flagged coordinate is
   predicated and no nonfinite candidate is committed. Read all flags and both
   vectors into scratch; adopt only a wholly finite, unflagged window. On refusal
   the entire host checkpoint remains exact, cached device state is invalidated,
   and attempted updates/launches remain charged. Device faults poison residency.
7. No invalid, cancelled, failed or incomplete endpoint MUST count as a speed win.
   Native normal limits can export actual finite candidates; export success does
   not imply certification. Independent checks still use the original 1e-9
   authority. Never invent finite bounds for unbounded variables.
8. The coordinator MUST freeze input/source/image/device/affinity/settings and complete paired roster
   before study. Include every timeout/refusal/failed coverage cell. Compare only
   same lifecycle, same transport and certified outcomes. A retained optimization
   requires improved total latency without lost certified coverage; otherwise
   keep only a clearly experimental negative result, never select a preset.

## Interfaces and state

Feature-gated `resident2::{PreparedModel, ResidentSession, Mode}` owns immutable
preparation and one imported matrix. `solve` returns untrusted original-unit
primal/dual vectors plus counters; the worker exports them to the existing
solver-neutral independent checker. The versioned envelope identifies the new
execution even though arithmetic/controller implementations are reused.
Historical solve-record readers and numerical sources remain unchanged.

## Resources and failure policy

The user's implementation request and additional-time permission fund a separate
bounded task: 32000 CPU seconds and 1800 GPU seconds; four CPU slots, one shared
lease, 16 GiB sampled host RSS, 12 GiB admitted device buffers. CPU allocations:
implementation 8000 (including 128 preparation), native 8000, acceptance 4000,
study 8000, reporting 3200, cleanup 800. GPU: acceptance 600, study 1200.
Use the unchanged in-container supervisor and exclusive per-job reservations.
Failed/unsettled jobs keep full reservations; an overrun closes execution.
Historical caps/charges stay closed. No installation or host configuration change.
Development corrections retain failed sources/logs. No scientific cell retry.

## Acceptance

CPU coefficient/index/shape tests and phase/pair eligibility regressions; full
native integration gate; new device differential boundary/restart tests,
cancellation/refusal/rollback tests and memcheck/racecheck/initcheck/synccheck;
frozen paired cold/prepared development study, independent certificates, total
cost/coverage decision, immutable source bridge and final resource/cleanup receipt.
A blocked or negative result remains explicit and does not pass a performance gate.
