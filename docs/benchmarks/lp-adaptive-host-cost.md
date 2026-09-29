# GPUP-ADAPTIVE-COST: shared preparation and host copy cleanup

Status: implemented and accepted, 2026-09-29, under
[SPEC-0017](../specifications/SPEC-0017-lp-adaptive-host-cost.md) and
[ADR-0029](../decisions/ADR-0029-adaptive-host-cost.md).
Study identity: `gpup-adaptive-cost-v1`, development only.

## Result and boundary

All **32/32 admitted attempts** independently verify with both archived executables;
all **24/24 primary timings** certify. All **16/16 timing/profile pairs** preserve
numerical and work digests. Twelve additional 200-update old/new pairs and twelve
baseline replays match bitwise; both binaries independently accept all 36 endpoints.

A full gradual ladder constructs two represented operators rather than five and
performs four conservative norm passes rather than ten. Direct ladders already
construct two. Successful immutable operators share Arc ownership by matrix width;
failed representations retain their individual rung entries. The conservative
common step is computed after all distinct representations have been prepared.
Audits stream the same original-unit component comparisons, removing six temporary
vectors. Probes borrow state except for working_fp32, whose clone and narrowing
remain intact. FP64 reference and sparse-product arithmetic are unchanged.

Only `optimizer-lp`'s adaptive runtime changes. A source audit confirms 255 prior
runtime/schema/protocol/manifest/kernel-source/decision files are byte-identical.
No numerical setting, kernel, algorithm identity, evidence version, solver default,
checkpoint, residency or certification rule changes. There is no cross-solve reuse,
adaptive session, arithmetic tuning or supported preset.

## Frozen protocol and reproduction

[Protocol](../../benchmarks/configs/lp-adaptive-cost-v1.json),
[analysis](data/adaptive-cost/adaptive-cost-analysis.json),
[all trial rows](data/adaptive-cost/adaptive-cost-trials.csv),
[provenance catalog](data/adaptive-cost/adaptive-cost-provenance.json) and
[resource receipts](data/adaptive-cost/adaptive-cost-resources.json) retain outcomes
and hashes. Baseline revision: `5b9a9d083b27547e8bcb3ee4c9d265dde1a40bbb`.
Both source archives, executables, schema identities and all four required CUDA
images are retained before admission. Adaptive requests bind the precision image,
not the tuned-FP64 image. Historical archives remain unchanged.

Sticky direct `[accumulation_fp32, fp64]` and gradual five-rung demotion policies
use audit interval 32 and primal/dual/relative audit tolerances 1e-7. Gradual demotion
requires four clean windows and margin 0.25. Each executable/policy/instance cell
has three fresh timing repetitions; eight separate profiles run each cell once.
All GPUP-HOST method settings remain: seed 17, one thread, affinity [0], final
1e-9 tolerances, 50000 physical updates, 30-second solves and two-second cleanup,
resident/necessary/warp32_v1/separate execution and compact-v1 evidence. Device:
`GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48`. Host/device bounds 8 GiB, per-file output
32 MiB, model reads 128 MiB, independent verifier timeout 120 seconds. Order seed
18001; paired bootstrap uses seed 18002, 10000 resamples and 95% intervals.

```sh
python3 tools/benchmark_lp_adaptive_cost.py --dry-run
python3 tools/report_lp_adaptive_cost.py
```

The report command is CPU-only and reads the retained ledger without appending or
repairing it. Device execution requires exact-source native/device receipts and
remaining reservations. Raw files remain under `artifacts/gpup-adaptive-cost-v1`,
`artifacts/gpup-adaptive-cost-baseline` and `artifacts/gpup-adaptive-cost-acceptance`.
Attempted study identities cannot rerun.

## Certified fresh-process latency

The process envelope includes input, fresh setup, solving, certification and
endpoint output. Independent verification is outside that envelope. Ratios are
medians of paired baseline/repaired ratios, not ratios of the displayed medians.
No failed pair is omitted or imputed; this study has no failed GPU attempt.

| Instance / policy | Baseline median s | Repaired median s | Paired ratio [95% interval] | Certified baseline + repaired |
| --- | ---: | ---: | ---: | --- |
| small-4 / direct | 0.359968 | 0.465978 | 0.7652 [0.7336, 0.8291] | 3/3 + 3/3 |
| irregular-32768 / direct | 3.983400 | 3.879348 | 1.0312 [0.9743, 1.0317] | 3/3 + 3/3 |
| small-4 / gradual | 0.341465 | 0.352317 | 0.9495 [0.9424, 1.0417] | 3/3 + 3/3 |
| irregular-32768 / gradual | 5.686729 | 5.026288 | 1.1250 [1.1248, 1.1329] | 3/3 + 3/3 |

Gradual irregular-32768 has a paired ratio of 1.1250 [1.1248, 1.1329], while small-4 direct **regresses**, with baseline/repaired ratio 0.7652 [0.7336, 0.8291]. The other two intervals span one. The small direct regression is retained; its cause is not established by one profile or three repetitions. No trial retries or tuning follow.

Three development repetitions support only these scoped observations. Profiles are
not primary timings, and a faster preparation phase does not imply universal solve
speedup. No configuration, audit frequency or recovery policy is selected as a preset.

## Preparation, required arithmetic and work

Each timing/profile comparison preserves proposals, audits, probes, replay,
transitions, controller state and numerical endpoints. Fixed-work acceptance holds
physical budget at 200; the profile pairs additionally retain identical actual
proposal mixtures. Peak RSS is sampled aggregate process-tree memory, not an
exact allocation trace. Norm counts include original and represented bounds.

| Profile | Operator / norm calls | Proposals / audits / probes / replay | Peak RSS MiB |
| --- | ---: | ---: | ---: |
| small-4 / direct / repaired | 2 / 4 | 200 / 7 / 0 / 0 | 110.80 |
| small-4 / direct / baseline | 2 / 4 | 200 / 7 / 0 / 0 | 110.50 |
| small-4 / gradual / baseline | 5 / 10 | 200 / 7 / 0 / 0 | 110.26 |
| small-4 / gradual / repaired | 2 / 4 | 200 / 7 / 0 / 0 | 110.79 |
| irregular-32768 / direct / repaired | 2 / 4 | 1608 / 57 / 0 / 8 | 229.65 |
| irregular-32768 / direct / baseline | 2 / 4 | 1608 / 57 / 0 / 8 | 229.88 |
| irregular-32768 / gradual / repaired | 2 / 4 | 2536 / 89 / 18 / 136 | 230.17 |
| irregular-32768 / gradual / baseline | 5 / 10 | 2536 / 89 / 18 / 136 | 257.38 |

The following groups sum disjoint **exclusive** scope times in milliseconds.
Preparation includes the ladder subtree; reference includes the FP64 reference
subtree; probe arithmetic contains only sparse-update arithmetic within the mirror.
Comparison contains original-unit audit comparison scopes (including probes).
These columns omit other process work and must not be interpreted as total latency.
A zero copy scope on the baseline means that scope was not instrumented there;
the independent legacy test retains its unconditional copy. New copy counters
count vector elements only when the repaired probe actually clones working state.

| Profile | Preparation ms | Reference FP64 ms | Audit comparison ms | Probe arithmetic ms | Instrumented copy/narrow ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| small-4 / direct / repaired | 0.011 | 0.012 | 0.001 | 0.000 | 0.000 |
| small-4 / direct / baseline | 0.011 | 0.011 | 0.002 | 0.000 | 0.000 |
| small-4 / gradual / baseline | 0.017 | 0.011 | 0.002 | 0.000 | 0.000 |
| small-4 / gradual / repaired | 0.010 | 0.011 | 0.001 | 0.000 | 0.000 |
| irregular-32768 / direct / repaired | 475.212 | 492.726 | 17.689 | 0.000 | 0.000 |
| irregular-32768 / direct / baseline | 469.719 | 484.774 | 27.048 | 0.000 | 0.000 |
| irregular-32768 / gradual / repaired | 479.114 | 762.272 | 31.463 | 181.494 | 0.000 |
| irregular-32768 / gradual / baseline | 1158.268 | 749.088 | 50.278 | 186.307 | 0.000 |

Original-model candidate, dual-certificate and gap assessments remain fresh and
counted in the raw profiles. Checkpoint copying remains measured but unchanged.
Reference arithmetic is a retained cost, not preparation eliminated by sharing.

## Acceptance, resources and limitations

Full pinned-native `bash tools/check.sh` passes, including independent exact-rational
regressions, lint, schemas/provenance, record replay, documentation and smoke.
All 55 regular device tests and memcheck/racecheck/initcheck/synccheck on the adaptive
scope pass. This does not close the historical tuned_cases racecheck gap.
All sixteen valid ladders match legacy construction; host differentials cover
conversion failures, zero/subnormal matrices, signed zero, audit boundaries,
nonfinite values, shapes and working-state narrowing. Existing injected rollback,
charged replay/probe, deadline, cancellation, exhaustion and device-fault gates pass.

The source-only budget/provenance suite passes without campaign artifacts. An initial
identity test depended on generated model inputs; it now uses a committed fixture.
The first native gate caught a test-only Clippy redundant guard. Failed and corrected
CPU receipts are retained. No failed GPU identity or retry occurred. Native acceptance
is never substituted by AI_OPTIMIZER_SKIP_NATIVE=1.

Task GPU charge: **201.890184622 seconds**: timing
62.784243449/1000, profiles 20.927881994/300,
acceptance 118.178059179/500; combined cap 1800.
Cumulative charge: **15407.672759957 / 18002.574545061 seconds**. Additional allowance: zero.
All jobs use the shared host lease and conservative admission; all phase caps hold.
The **15528-event** ledger SHA-256 is
`cb0dc57f9f92546f4cc2d93b0de3c8556d6b24517f71b7a6efaa91fa96afedb6`. Its 15452-event prefix remains
`90dab78c269b74f511416ddd73cf05e123555ae006b9ad75fc896933a35f9cd2`.
Four build jobs and a four-CPU-hour ceiling apply; measured receipts are linked above.

This comparison covers small-4 and irregular-32768 only. Existing mixed-65536
limits, large-session coverage gaps and the old tuned_cases racecheck receipt stay
open. COPT internals, fresh setup diagnosis, optional COPT adapter construction,
convergence mixtures and quantization remain separate tasks. Handoff: GPUP-SETUP;
no work on that task or external publication is included.
