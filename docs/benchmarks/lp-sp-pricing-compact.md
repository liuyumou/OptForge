# Compact geometry and bounded GPU searches

The opt-in compact path implements lazy exact fallback, tiled products and checks, bounded synchronized batches, and implicit paired bases. It removes the old dimension-only rejection for the three original million-nonzero LPs. All three reach their 20-second deadline in CPU geometry construction before an auxiliary query; none returns a certificate. Memory admission and complete-solve performance are separate outcomes.

See the [complete evidence](lp-sp-pricing-compact-results.json), [auxiliary CSV](lp-sp-pricing-compact-auxiliary.csv), [settled checkpoint](lp-sp-pricing-compact-checkpoint.json), [prospective plan](../plans/lp-sp-pricing.md#compact-geometry-and-bounded-gpu-execution), and [historical COPT/million study](lp-sp-pricing-million.md).

## Implementation

The isolated entry point is `tools/lp_sp_pricing_compact_run.py MODEL OUTPUT`. It accepts the canonical rational model or portable CSR input; `--cpu` disables GPU proposals and `--serial` disables cross-batch overlap. Run it through the existing study reservation wrapper with a fresh identity. Existing solver defaults and historical numerical sources are unchanged.

- CPU constraints and exact tableaus are allocated only if GPU proposals leave labels unresolved. The existing one-million-cell fallback/recovery limit still applies.
- Sparse RREF factors represent the positive space; its orthogonal complement `[-R^T I]` and paired identity blocks are generated on demand. Exact calibration and recovery use sparse products. Actual elimination fill, bit growth and deadlines remain bounded.
- Each GPU batch holds at most 32 searches in this configuration. Searches advance in common PDHG steps and reuse coefficients across four right-hand sides. Numerical state is capped at 256 MiB; the selected device tile cache is 64 MiB.
- Matrices beyond the tile cache use two pinned upload slots, two copy streams and explicit events. One producer prepares the next tile. At most one host proof overlaps the next GPU batch; redundant work already launched is recorded.
- Streamed rigorous interval checks use bounded coefficient/check caches of 32 MiB each. Uncertain proposals use exact rational products; only proved labels are accepted. Original endpoint checks remain independent and strict at 1e-9.

## Auxiliary completion and memory

The frozen seed-122009 roster contains 18 cold processes and 64 FP64 steps per launched batch. Dense-million has 1,000,000 nonzeros. Diagonal-million has 1,000,000 positions but only 500 nonzeros. Factor-128m has 128,000,000 positions, 4000 stored positive-factor entries and 8000 paired nonzeros. Every returned label is checked against an independent exact structural witness or a dense common positive witness.

| Case | Lane | Complete / slots | Cold process s | Process HWM MiB | Numerical device MiB | Resident searches |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| dense-million | compact-pipeline | 2 / 2 | 5.774 | 292.5 | 25.93 | 32 |
| dense-million | compact-serial | 2 / 2 | 5.773 | 292.0 | 25.93 | 32 |
| dense-million | compact-stream | 2 / 2 | 10.882 | 286.5 | 2.99 | 32 |
| dense-million | wave | 2 / 2 | 5.347 | 410.2 | 76.33 | 2000 |
| diagonal-million | compact-pipeline | 2 / 2 | 0.940 | 157.4 | 3.00 | 32 |
| diagonal-million | compact-serial | 2 / 2 | 1.192 | 157.4 | 3.00 | 32 |
| diagonal-million | wave | 2 / 2 | 2.468 | 291.3 | 53.45 | 2000 |
| factor-128m | compact-pipeline | 2 / 2 | 30.049 | 255.5 | 17.59 | 32 |
| factor-128m | compact-serial | 2 / 2 | 49.423 | 253.6 | 17.59 | 32 |

Values are medians of two repetitions. Cold process time includes fixture generation, initialization, upload, iterations, label checks, teardown and publication. It is auxiliary label-completion time, not original-LP solution time. The previous wave control constructs its packed basis/checker directly and does not construct a CPU fallback tableau. Lazy fallback savings are therefore not credited to this timing comparison.

Numerical device memory counts the wave arena or compact state, cache and two staging buffers. It excludes CUDA context/library/graph allocations; this is an allocation calculation, not a sampled whole-device peak. Process HWM is measured separately and includes input/factors, caches and runtime. Old wave is unsupported for factor-128m and is not run there.

| Case | Baseline / pipeline | Matched cold-time ratio |
| --- | --- | ---: |
| dense-million | wave / compact-pipeline | 0.926× |
| dense-million | compact-serial / compact-pipeline | 1.001× |
| dense-million | compact-stream / compact-pipeline | 1.888× |
| diagonal-million | wave / compact-pipeline | 2.624× |
| diagonal-million | compact-serial / compact-pipeline | 1.269× |
| factor-128m | compact-serial / compact-pipeline | 1.645× |

Ratios above one favor the pipeline. These are time-to-label-completion comparisons with unequal work: wave advances all targets, while compact prunes between batches; pipelining can launch one redundant batch. Actual advanced and checked counts remain in the JSON/CSV. Dense forced streaming retains the same bounded state but repeats transfers; the cached path is faster. No kernel-only speedup is inferred from advancement timers that include transfer/stream waits.

## Original million-nonzero attempts

These are the exact three previously unsupported inputs, seed 121951, one attempt each. The new path receives 20 native seconds and 30 process seconds. The preceding dimension-only refusals and COPT results remain historical; no COPT solve is repeated.

| Model | Result | Native s | Process HWM MiB | Queries | Strict certificate |
| --- | --- | ---: | ---: | ---: | --- |
| dense | resource_limit: deadline | 20.084 | 257.6 | 0 | False |
| tall | resource_limit: deadline | 20.087 | 267.5 | 0 | False |
| sparse | resource_limit: deadline | 20.076 | 258.5 | 0 | False |

All three stay near 258–268 MiB process HWM during their bounded attempts. This is not a forecast of full-solve memory: sparse exact elimination may fill and rational numerators/denominators grow. The recorded `geometry_and_experts` phase includes sparse row reduction, initial calibration bounds and expert setup; the existing phase timer does not isolate those substeps. No query is reached, so GPU auxiliary acceleration cannot improve these observed attempts. Fraction-free/modular exact elimination or a further implicit calibration design would need separate implementation and numerical admission.

## Fresh end-to-end checks

Seed 122011 supplies coupled, dense and degenerate models with eight columns and sixteen rows. Four lanes, two cyclic repetitions and identical 10/15-second native/process allowances give 24 cold cells. Complete cost includes model encoding, cold process startup and preparation, solve/check/recovery, teardown and the external exact plus strict endpoint audit.

| Lane | Slots | Timely exact | Timely strict | Total complete s |
| --- | ---: | ---: | ---: | ---: |
| wave | 6 | 6 | 0 | 13.210 |
| compact-cpu | 6 | 6 | 0 | 11.511 |
| compact-serial | 6 | 6 | 0 | 14.317 |
| compact-pipeline | 6 | 6 | 0 | 13.758 |

| Tier | Baseline / pipeline | Jointly timely repetitions | Median complete ratio |
| --- | --- | ---: | ---: |
| exact | wave / compact-pipeline | 6 | 0.958× |
| exact | compact-cpu / compact-pipeline | 6 | 0.829× |
| exact | compact-serial / compact-pipeline | 6 | 1.042× |
| strict | wave / compact-pipeline | 0 | — |
| strict | compact-cpu / compact-pipeline | 0 | — |
| strict | compact-serial / compact-pipeline | 0 | — |

All 24 endpoints pass the independent exact rational original-model verifier. The unchanged floating endpoint checker reports primal feasibility but no finite dual bound for these free-variable models, so strict acceptance is 0/24. Exact and strict tiers are kept separate; no strict ratio is available.

Uncertified, failed or late outcomes stay visible and are excluded from certified ratios. These few synthetic models do not establish broad superiority or a COPT speedup. The practical candidate has no strongly polynomial complexity claim.

## Validation and accounting

Final numerical admission covers 24 GPU configurations, 116 exact proposals, independent scalar equations, serial/pipeline equivalence, cached/forced-streaming dense/CSR paths, and all four CUDA sanitizers. Native ASan/UBSan covers 64 cases. Eleven compact integration tests cover sparse RREF/complements, calibration equivalence, lazy fallback and its refusal, bounded caches, interval/exact agreement, and original optimal/infeasible/unbounded certificates.

The final study suite and documentation receipt are bound in the settled checkpoint. The initial CPU admission test-import error retains its full 960 CPU-second charge. All preceding failures, source snapshots, budgets and resource guards remain. This study uses four slots, a 16-GiB sampled host reservation, fresh 30-second GPU idle checks and the existing 240000 CPU / 30000 GPU-second allocation. All scientific cells are attempted once.
