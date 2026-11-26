# Million-scale pricing experiments

The original-LP cohort contains three matrices with exactly **1,000,000 nonzeros** each. The current candidate cannot execute them: its original explicit-geometry guard rejects all three before numerical work. COPT is attempted on all three with two cold repetitions. Separate auxiliary experiments measure the admitted GPU kernels at their one-million-coefficient capacity.

See the [complete results](lp-sp-pricing-million-results.json), [auxiliary table](lp-sp-pricing-million-auxiliary.csv), [settled checkpoint](lp-sp-pricing-million-checkpoint.json), and [previous small-LP comparison](lp-sp-pricing-wave-policy.md).

## Original LPs

The fresh seed is 121951. Coefficients and construction certificates are exact dyadic values; each planted optimum passes the unchanged independent original-model 1e-9 checker before the comparison. Construction witnesses are never passed to COPT. All variables are free. The retained COPT scale-off GPU-PDLP configuration receives 30 native seconds and a 45-second outer process allowance. This is not automatic COPT configuration.

| Model | Rows | Columns | Nonzeros | Initial geometry entries / cap | Paired basis entries / cap |
| --- | ---: | ---: | ---: | ---: | ---: |
| dense | 1000 | 1000 | 1000000 | 1002001 / 100000 | 2004002 / 1000000 |
| tall | 4000 | 1000 | 1000000 | 4005001 / 100000 | 32016002 / 1000000 |
| sparse | 8000 | 8000 | 1000000 | 64016001 / 100000 | 128032002 / 1000000 |

CPU and opportunistic-GPU candidate slots remain visible as unsupported capacity. The preflight calls the actual unchanged guard with dimension-only inputs; it neither constructs an invalid dense input nor changes admission limits. No candidate solve time or candidate/COPT speedup is reported.

| Model / repetition | COPT status | GPU startup logged | Timely strict acceptance | Native s | Complete s |
| --- | ---: | --- | --- | ---: | ---: |
| dense / 0 | 10 | True | False | 30.035 | 30.604 |
| tall / 0 | 1 | True | False | 0.586 | 1.236 |
| sparse / 0 | 10 | True | False | 30.034 | 30.603 |
| tall / 1 | 1 | True | False | 0.621 | 1.235 |
| sparse / 1 | 10 | True | False | 30.033 | 30.603 |
| dense / 1 | 10 | True | False | 30.035 | 30.604 |

Complete time includes original encoding, cold process startup, import/CSR-to-CSC conversion, internal GPU setup and solve, teardown, output and the independent endpoint audit. Construction-certificate validation and resource monitoring are separately charged. Vendor status 1 means numerical optimality; independent strict acceptance is reported separately. Internal device preparation remains inside the opaque COPT solve call.

## Auxiliary throughput

Fresh synthetic bounded auxiliary LPs use one million coefficient positions. Dense-square (1000×1000) and dense-wide (500×2000) contain one million nonzeros. Sparse-wide (500×2000) contains **16,000 nonzeros**, not one million. These matrices are not original-LP calibrated bases and have no opposite-slot separation assumption.

Each cold process constructs the same rational input and runs 128 FP64 PDHG steps. Widths are 64, 256 and 1000 distinct signed objectives. Lean runs active batches of at most 64; wave advances all states at common steps. Three alternating repetitions cover both dense and CSR storage. CUDA-event time excludes setup and transfers. Cold auxiliary process time includes generation, preparation, execution, downloads, teardown and state-file publication; it excludes subsequent checking and is not complete original-LP solve time.

| Case / storage | Searches | Lean device ms | Wave device ms | Device speedup | Lean cold s | Wave cold s | Cold speedup |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| dense-square / dense | 64 | 77.527 | 58.901 | 1.316× | 1.166 | 1.766 | 0.660× |
| dense-square / dense | 256 | 310.038 | 228.271 | 1.358× | 1.466 | 1.866 | 0.765× |
| dense-square / dense | 1000 | 1211.508 | 881.909 | 1.374× | 2.417 | 2.568 | 0.923× |
| dense-square / csr | 64 | 77.860 | 59.262 | 1.314× | 1.215 | 1.817 | 0.669× |
| dense-square / csr | 256 | 312.101 | 229.273 | 1.361× | 1.466 | 1.916 | 0.765× |
| dense-square / csr | 1000 | 1220.457 | 887.826 | 1.375× | 2.417 | 2.617 | 0.924× |
| dense-wide / dense | 64 | 79.760 | 60.839 | 1.311× | 1.165 | 1.716 | 0.679× |
| dense-wide / dense | 256 | 319.696 | 238.101 | 1.343× | 1.466 | 1.916 | 0.765× |
| dense-wide / dense | 1000 | 1250.000 | 924.471 | 1.352× | 2.467 | 2.667 | 0.925× |
| dense-wide / csr | 64 | 80.190 | 63.532 | 1.262× | 1.215 | 1.716 | 0.688× |
| dense-wide / csr | 256 | 321.056 | 239.639 | 1.340× | 1.466 | 1.916 | 0.765× |
| dense-wide / csr | 1000 | 1254.955 | 927.884 | 1.352× | 2.517 | 2.668 | 0.944× |
| sparse-wide / dense | 64 | 79.877 | 60.871 | 1.312× | 1.166 | 1.616 | 0.721× |
| sparse-wide / dense | 256 | 319.702 | 238.133 | 1.343× | 1.416 | 1.817 | 0.779× |
| sparse-wide / dense | 1000 | 1249.623 | 924.343 | 1.352× | 2.467 | 2.567 | 0.961× |
| sparse-wide / csr | 64 | 14.457 | 14.947 | 0.968× | 1.116 | 1.566 | 0.712× |
| sparse-wide / csr | 256 | 57.707 | 56.645 | 1.019× | 1.166 | 1.616 | 0.721× |
| sparse-wide / csr | 1000 | 225.698 | 219.063 | 1.030× | 1.416 | 1.816 | 0.780× |

Ratios are medians of matched repetitions; values above one favor wave. The CSV also retains preparation times. Failed or missing cells remain in the evidence and never become successful pairs.

## Host checks and numerical audit

The audit compares every returned primal and dual state between paired implementations at normalized tolerance 1e-12. Two objectives per matrix/storage pair also use independent NumPy equations at 1e-10. These are numerical implementation comparisons, not certificate tolerances.

Four evenly spaced proposals from every paired wave cell receive interval/GMP checking, with identical inputs and resolution order. All interval decisions must be established by GMP. Context construction is shared and excluded from checker-only timings; original rational threshold tests remain exact. The final endpoint checker remains at 1e-9.

| Case | Check batches | GMP ms | Interval/GMP ms | Speedup | Same label coverage | GMP fallbacks |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| dense-square | 18 | 900.631 | 117.946 | 7.675× | True | 0 |
| dense-wide | 18 | 404.340 | 55.624 | 7.268× | True | 0 |
| sparse-wide | 18 | 3.257 | 0.469 | 6.965× | True | 0 |

Audited auxiliary pairs: 54/54; failed cells: 0. Independent scalar comparisons: 12; sampled proposal slots: 216.

This study does not demonstrate million-scale complete-solve capability for the candidate. The next original-LP scaling barrier is explicit rational geometry and the mixed optimality reduction, which can become dense even for sparse original input. Increasing a GPU batch cap alone cannot resolve it. All numerical source hashes, prior failures and study budgets remain unchanged.
