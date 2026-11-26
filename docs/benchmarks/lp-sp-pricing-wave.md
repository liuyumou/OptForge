# GPU preparation, rigorous checks and synchronized auxiliary searches

This follow-up retains the preceding [lean candidate evaluation](lp-sp-pricing-gpu.md) and adds solve-scoped preparation, rigorous interval/GMP decisions and synchronized auxiliary iteration. The final original-model certificates and independent 1e-9 checker remain unchanged.

See the [full evidence](lp-sp-pricing-wave-results.json), [all comparison cells](lp-sp-pricing-wave-comparison.csv), [interval argument](../../research/lp-sp-pricing/interval-notes.md), and [settled checkpoint](lp-sp-pricing-wave-checkpoint.json).

## Preparation diagnosis

The prior binary contains sm_75 code; the new build explicitly targets sm_120 and uses shared cudart. A controlled three-rotation diagnostic separates first-use CUDA initialization from matrix preparation. Its complete time includes two preparations and two 64-step proposals; warm timing uses the second preparation in the same process.

| Build | Cold preparation ms | Explicit runtime initialization ms | Warm preparation ms | Complete diagnostic ms |
| --- | ---: | ---: | ---: | ---: |
| old | 250.908 | 251.288 | 0.280 | 257.686 |
| aot-static | 246.214 | 242.916 | 0.274 | 252.807 |
| aot-shared | 241.895 | 241.283 | 0.240 | 246.066 |

The dominant first-use cost is runtime initialization. Native architecture selection helps modestly; it does not remove that cost. COPT keeps internal device preparation inside its opaque solve timer, so the separate COPT model-import/preparation field is not a directly comparable measure. No unmeasured COPT device-setup advantage is assumed.

## Implemented changes

- Start CUDA initialization concurrently with CPU geometry and market work. Record both initialization duration and exposed waiting time; all work remains inside cold end-to-end timing.
- Retain one stream, event pair and growing device arena across pricing queries. Upload matrix/control data once and zero numerical states on device, avoiding transfers of host-generated zeros.
- Advance all signed auxiliary objectives through common iteration checkpoints. Larger-matrix kernels reuse each coefficient and CSR index across four right-hand sides. Active indices remove resolved searches without rebuilding the CUDA graph.
- Pass contiguous native proposal buffers directly to a batched interval checker. Avoid Python list reconstruction and per-proposal rational-string conversion.
- Enclose original rational coefficients exactly and widen floating operations outward. Accept only proved quarter-threshold decisions; resolve uncertainty with the original GMP checker. Stop a dual residual scan as soon as its lower bound proves that proposal cannot certify the target.

Independent auxiliary searches share matrix work. Successive pricing rounds still depend on previous labels and wealth updates. The larger diagnostic matrices test auxiliary throughput only; they do not establish large original-LP scalability.

## Fixed-work iteration and host-check costs

Both implementations use the same diagonal FP64 PDHG equations, 256 target states and 256 steps. Medians use three rotated repetitions. The lean control processes four batches of 64; the wave candidate processes all 256 states together. Ratios use CUDA-event iteration time. The wave diagnostic reuses a packed host basis and session, while the control rebuilds its per-query context; the retained auxiliary complete_ns fields therefore have different preparation reuse and are not cold-preparation comparisons.

| Auxiliary | Format | Lean device ms | Wave device ms | Lean / wave |
| --- | --- | ---: | ---: | ---: | ---: |
| coupled-first | dense | 8.827 | 3.615 | 2.442× |
| coupled-first | CSR | 8.254 | 4.238 | 1.948× |
| coupled-optimum | dense | 16.611 | 13.573 | 1.224× |
| coupled-optimum | CSR | 13.365 | 11.214 | 1.192× |
| degenerate-optimum | dense | 34.567 | 31.652 | 1.092× |
| degenerate-optimum | CSR | 22.352 | 20.742 | 1.078× |
| dense-256 | dense | 80.955 | 78.148 | 1.036× |
| dense-256 | CSR | 124.282 | 83.146 | 1.495× |
| sparse-512 | dense | 251.726 | 249.090 | 1.011× |
| sparse-512 | CSR | 71.236 | 69.108 | 1.031× |

Host-check diagnostics use identical raw proposals and compare compact GMP decisions with interval/GMP decisions. Context preparation is excluded from this checker-only table and retained separately in complete solve costs.

| Auxiliary | GMP ms | Interval/GMP ms | Median paired speedup |
| --- | ---: | ---: | ---: |
| coupled-first | 2.542 | 0.199 | 12.749× |
| coupled-optimum | 50.862 | 2.230 | 22.810× |
| degenerate-optimum | 150.264 | 4.930 | 30.456× |

## Fresh original-LP comparison

Development selected a 1000-step ceiling by timely exact certificates and then capped cost. Seven fresh seed-99173 models cover all seven families. Four lanes and two cyclic rotations give 56 cold processes. Every lane has ten native seconds and fifteen process seconds. Complete cost includes common model encoding, process startup, all initialization and teardown, solving, output and the independent endpoint audits. Idle observation and resource settlement remain charged outside comparable cost.

| Lane | Timely exact | Timely strict 1e-9 | Vendor optimal | Total complete seconds | Median complete seconds |
| --- | ---: | ---: | ---: | ---: | ---: |
| cpu | 12/14 | 2/14 | — | 43.830 | 2.084 |
| lean | 12/14 | 2/14 | — | 49.291 | 2.561 |
| wave | 12/14 | 2/14 | — | 45.792 | 2.261 |
| copt_scale_off | 0/14 | 0/14 | 12 | 31.378 | 0.880 |

Totals and medians include unsuccessful attempts and do not measure equal certified work. COPT uses the retained scale-off GPU-PDLP configuration, not automatic defaults. Its numerical optimal status and strict independent acceptance remain distinct. A nonzero floating dual residual on free variables can prevent a finite rigorous bound without establishing that the vendor optimum is wrong.

| Tier | Comparator / wave | Paired models / repetitions | Median ratio | Range |
| --- | --- | ---: | ---: | ---: |
| exact | cpu / wave | 6 / 12 | 0.917× | 0.744–1.123× |
| exact | lean / wave | 6 / 12 | 1.132× | 1.051–1.216× |
| exact | copt_scale_off / wave | 0 / 0 | — | — |
| strict | cpu / wave | 1 / 2 | 0.761× | 0.744–0.777× |
| strict | lean / wave | 1 / 2 | 1.083× | 1.051–1.114× |
| strict | copt_scale_off / wave | 0 / 0 | — | — |

Only jointly timely accepted pairs receive ratios; values above one favor wave. All outcomes and unmatched certificates remain in the CSV. This small two-repetition cohort does not establish broad solver superiority.

The following totals are internal GPU diagnostics across the candidate runs. Exposed preparation includes waiting, conversion and upload; asynchronous initialization duration overlaps CPU work and is not additive with complete solve time.

| Lane | Exposed preparation s | Actual asynchronous initialization s | Host proposal checks s | Device iterations s | CPU auxiliary calls |
| --- | ---: | ---: | ---: | ---: | ---: |
| lean | 4.7515 | 0.0000 | 1.4027 | 0.2079 | 320 |
| wave | 1.8540 | 3.9294 | 0.1068 | 0.2772 | 320 |

The zero asynchronous-initialization entry for lean means it performs initialization synchronously inside preparation, not that its startup is free. The complete process stopwatch includes both implementations' startup work.

## Admission and retained failures

CPU tests cover exact rational enclosures, equality at the threshold, cancellation, subnormal values, box clipping, malformed inputs and non-default rounding. ASan/UBSan checks 128 native interval/GMP cases. GPU quality covers 54 configurations and 2,464 exact proposals, continued state, inactive searches, scalar equations and comparison with the preceding FP64 engine. All four CUDA sanitizer smoke checks and a cold asynchronous original-LP smoke solve pass.

The first GPU admission stopped during sanitizer finalization with a supervised “No such process” error after numerical quality and memcheck completed. Its failed receipt, empty cleanup and full 960 CPU / 240 GPU-second charge remain. The study-local process mapper now handles ProcessLookupError as well as FileNotFoundError for an already observed exiting process. Permission failures and foreign GPU processes still fail admission; the shared resource-critical files and limits remain exact. A fresh source-bound CPU gate passes before continuation of only the unfinished sanitizer work. The missing full traceback limits attribution of the original error to this exit-race explanation.

All earlier failures, source archives and numerical results remain. The final checkpoint records CPU/GPU usage, test results, source verification and exact process cleanup. Public defaults, literal-reference limitations and billion-case capacity refusals remain unchanged.
