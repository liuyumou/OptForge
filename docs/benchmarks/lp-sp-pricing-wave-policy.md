# Avoiding CPU waits for GPU initialization

This final policy refinement retains the [synchronized-search and COPT comparison](lp-sp-pricing-wave.md). CUDA initialization still takes real time. While it is unfinished, the candidate now performs the current query with the existing exact CPU oracle. Later queries use the admitted synchronized GPU backend once it is ready.

No GPU labels are guessed. Failed initialization remains an error. Final teardown waits for and releases an unused session, so initialization is never hidden outside the complete process stopwatch. The admitted CUDA, interval and GMP numerical sources remain byte-for-byte unchanged.

See the [complete evidence](lp-sp-pricing-wave-policy-results.json), [all cells](lp-sp-pricing-wave-policy-comparison.csv), and [settled checkpoint](lp-sp-pricing-wave-policy-checkpoint.json).

## Development selection

The earlier held-out cohort exposed a remaining first-query wait. That cohort stays unchanged. The policy was then evaluated on development seed 73011 using seven models, both startup policies, alternating order and fresh processes. Selection maximizes timely exact certificates and then minimizes capped cold-process cost.

| Policy | Timely exact certificates | Capped process seconds |
| --- | ---: | ---: |
| wave | 6/7 | 23.358 |
| opportunistic | 6/7 | 22.302 |

Selected policy: **opportunistic**.

## Fresh confirmation

A new seed, 111359, supplies seven original models across the seven families. CPU, the preceding wave policy and the opportunistic policy each have two cyclic repetitions: 42 cold processes. Native/process windows remain ten/fifteen seconds. Complete cost includes common input encoding, startup, initialization, solve, output, teardown and independent exact plus unchanged 1e-9 audits.

| Lane | Timely exact | Timely strict 1e-9 | Total complete seconds |
| --- | ---: | ---: | ---: |
| cpu | 12/14 | 2/14 | 43.665 |
| wave | 12/14 | 2/14 | 47.036 |
| opportunistic | 12/14 | 2/14 | 44.943 |

Totals retain unsuccessful attempts and are not equal-certified-work comparisons. Ratios below use only jointly timely accepted pairs. Values above one favor the opportunistic policy.

| Tier | Comparator / opportunistic | Paired models / repetitions | Median ratio | Range |
| --- | --- | ---: | ---: | ---: |
| exact | cpu / opportunistic | 6 / 12 | 0.958× | 0.868–0.980× |
| exact | wave / opportunistic | 6 / 12 | 1.084× | 1.055–1.271× |
| strict | cpu / opportunistic | 1 / 2 | 0.898× | 0.868–0.928× |
| strict | wave / opportunistic | 1 / 2 | 1.264× | 1.257–1.271× |

## Preparation and checking

These totals distinguish exposed waiting from actual initialization work. Initialization overlaps CPU work, so the columns are not additive parts of complete time.

| Policy | Initialization duration s | Waiting s | Exposed preparation s | Host checks s | CPU queries during initialization |
| --- | ---: | ---: | ---: | ---: | ---: |
| wave | 4.5914 | 2.4277 | 2.5576 | 0.1616 | 0 |
| opportunistic | 4.1128 | 0.0001 | 0.0916 | 0.0953 | 18 |

The policy can perform more CPU auxiliary work in exchange for avoiding a startup wait. It does not eliminate the CUDA context cost, guarantee full GPU occupancy, or make the exact CPU fallback parallel. The preceding report retains the 12–30× fixed-input host-check gains, varying synchronized-kernel gains and the direct COPT comparison. This new cohort has no COPT lane, so no transitive COPT speedup is claimed.

Both cohorts are small generated problems with two repetitions and unflushed caches. All deadlines, unmatched certificates and regressions remain. Literal-reference and billion-case limitations are unchanged. CPU tests cover nonblocking dispatch, ready-future dispatch, error propagation and cleanup of unused sessions. The final checkpoint records the full test count, document verification, source bindings, retained failures and resource settlement.
