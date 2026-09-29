# ADR-0029: Shared Adaptive Preparation and Host Copy Cleanup

Status: accepted by the maintainer on 2026-09-29 before implementation.
Scope: GPUP-ADAPTIVE-COST under SPEC-0017, SPEC-0012 and SPEC-0013.

## Decision

Share PrecisionOperator results by matrix width within one PreparedAdaptive,
using Arc for successful operators and retaining per-rung failures. Full ladders
prepare two operators rather than five. Keep PrecisionOperator::new unchanged.
Stream original-unit audits with identical expression/traversal order. Borrow
probe state except for working_fp32, whose clone/narrowing sequence is unchanged.
Do not alter reference arithmetic, checkpoints, charged recovery, code images,
certification, settings, versions, identities or defaults. No cross-solve reuse.

## Frozen comparison

Archive baseline 5b9a9d083b27547e8bcb3ee4c9d265dde1a40bbb and repaired source,
executables, schemas and all four discovery/execution code images. New strict
protocol identity: gpup-adaptive-cost-v1. Both binaries independently verify every
complete endpoint. Bind adaptive policy and precision code identity explicitly.

Two policies: sticky direct [accumulation_fp32, fp64] and gradual
[working_fp32, accumulation_fp32, products_fp32, storage_fp32, fp64] with demotion
after four clean windows at margin 0.25. Audit interval 32 and all three audit
tolerances 1e-7. Instances: small-4 and irregular-32768. Two binaries x two policies
x two instances x three repetitions gives 24 primary fresh timings; eight separate
profiles cover every combination once. Retain GPUP-HOST method settings and seed
17, one thread, affinity [0], final tolerances 1e-9, 50000 physical updates and
30-second deadlines. Execution is resident/necessary/warp32_v1/separate, evidence
compact-v1. Device GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48; 8 GiB host/device bounds,
32 MiB per-file output, 128 MiB model reads, 120-second independent CPU verification,
2-second cleanup, 10 ms RSS polling. Order seed 18001; 10000 bootstrap resamples,
seed 18002, 95% paired intervals. No speedup requirement or supported preset.

Fixed-work acceptance uses 200 physical updates on tuned FP64, fixed accumulation
FP32, adaptive FP64, direct sticky and gradual demotion for small-4/irregular-2048,
plus both study policies on irregular-32768: twelve old/new pairs and twelve
baseline replays with the repaired binary. Compare binary64 bits, recovery/work
and execution observations, excluding clocks/memory; verify with both binaries.
Keep failures and incomplete pairs; never retry study identities.

## Authority and acceptance

Initial charge 15205782575335 ns; 15452 events; prefix SHA-256
90dab78c269b74f511416ddd73cf05e123555ae006b9ad75fc896933a35f9cd2.
Preserve cumulative ceiling 18002574545061 ns, campaign 28800 seconds, every phase
cap and original output binding. Additional allowance zero. Timing 1000 seconds
in ablations, profiles 300 and acceptance 500 in repeatability; combined 1800.
No borrowing. Each timing/profile attempt reserves 36 seconds, totaling 864/288.
All device jobs use the shared host lease; missing/uncertain work is fully charged.
Stop at caps with explicit incomplete evidence. Four build jobs and four CPU-hours.

Require full pinned-native tools/check.sh before device admission; independent
legacy host differentials and exact-rational regressions; strict provenance and
clean-checkout synthetic-ledger gates; regular device acceptance and all four
adaptive sanitizers; fixed-work/replay equality and independent report. Report
certified latency/coverage, preparation/reference costs, work, memory and all gaps.
Preserve historical racecheck/session/large-model limitations. Record acceptance,
commit locally and hand off to GPUP-SETUP without beginning it. No push/publication.
