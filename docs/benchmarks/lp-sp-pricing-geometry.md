# Exact geometry acceleration and fresh million-scale COPT comparison

The new opt-in candidate combines native exact row reduction, a GPU exact modular full-space proof, and numerical factor proposals that can skip pricing only after exact original-model certification. The last path is a practical certified presolve; success there does not demonstrate completion of the paper pricing algorithm.

See the [results](lp-sp-pricing-geometry-results.json), [all comparison cells](lp-sp-pricing-geometry-comparison.csv), [settled checkpoint](lp-sp-pricing-geometry-checkpoint.json), and [preceding compact path](lp-sp-pricing-compact.md). The isolated entry point is `tools/lp_sp_pricing_geometry_run.py MODEL OUTPUT`; `--no-presolve` retains pricing construction, and `--cpu` disables the modular GPU proof and GPU auxiliary proposals. All runs require the unchanged study reservation wrapper.

## Diagnosis

Fresh seed-122101 million-nonzero profiles all stop in `slack_rref`, before calibration, expert construction or a GPU query. Each eight-second instrumented attempt makes about 18 million Python calls. Fraction construction, multiplication/subtraction, negation of one million input entries, and per-scalar resource checks dominate. GCD and rational bit growth are also real costs; sparse storage alone does not remove them. cProfile overhead prevents interpreting these eight-second traces as uninstrumented throughput.

The native sparse GMP backend avoids Python arithmetic objects and scalar callbacks inside elimination. It retains rational arithmetic, actual fill/bit/deadline limits and independent output comparisons. The bounded integer certificate kernel proves original primal feasibility, dual nonnegativity, exact dual equations and zero gap; its input/range guards keep every signed 128-bit intermediate below overflow. Unsupported ranges fall back, rather than weakening proof.

Dense square factor proposals use LAPACK LU; sparse square proposals use SuperLU with the same factorization for primal and transposed dual solves. Rectangular proposals use bounded LSMR. A fixed dyadic quantization ladder is followed by exact checking. Floating residual screens can reject a proposal but cannot accept one. The unchanged supervisor supplies single-thread BLAS; model loading and factorization are timed.

## Matched exact CPU geometry

Fresh small development matrices have identical exact RREF outputs. Times include Python/native marshaling and output reconstruction. Operation counters use different update units, so they are not fixed-work throughput counters. There is one diagnostic repetition.

| Case | Fraction implementation s | Native GMP s | Speedup |
| --- | ---: | ---: | ---: |
| dense | 0.509 | 0.130 | 3.929× |
| sparse | 1.196 | 0.331 | 3.618× |
| tall | 1.027 | 0.190 | 5.414× |

## Exact GPU geometry

The GPU computes over the prime 65521 using bounded unsigned integer multiplication and reduction. Full modular column rank proves full rational rank because every input denominator is invertible modulo that prime. Only then may the full-space identity replace rational elimination. Rank deficiency modulo this prime is inconclusive and falls back to exact GMP. No floating pivot threshold, probabilistic rank acceptance or rounded basis is used.

The kernel visits only the active trailing matrix with a two-dimensional launch, eliminating unused threads and per-element integer division. Geometry matrix storage is capped at one GiB and released before auxiliary work. Rank timings below include rational-to-field packing, transfer and per-call teardown, but exclude fixture generation. The first GPU call includes CUDA initialization; the second reuses the initialized context in the same process. CPU attempts have five-second work windows; GPU proofs have 45 seconds. They are capacity/completion diagnostics, not equal-deadline speedup ratios.

| Matrix | Path | Result | Full space proved | Complete diagnostic s |
| --- | --- | --- | --- | ---: |
| dense | fraction | resource_limit | False | 5.002 |
| dense | native | resource_limit | False | 5.049 |
| dense | gpu-rank | completed | True | 1.990 |
| sparse | fraction | resource_limit | False | 5.001 |
| sparse | native | resource_limit | False | 5.050 |
| sparse | gpu-rank | completed | True | 2.314 |

CPU/GPU modular results agree on ten small configurations, including row swaps and deficient matrices. All four CUDA sanitizers pass. Large rank diagnostics use that admitted exact kernel; no completed large CPU rank comparison is claimed when the CPU attempt times out.

## Fresh million-nonzero comparison

Seed 122141 supplies dense 1000×1000, tall 4000×1000 (250 entries per row), and sparse 8000×8000 (125 per row) models, each with exactly one million nonzeros. Unlike the preceding uniform-witness cohort, primal coordinates and positive dual weights vary. All rows are active at the planted optimum, and coefficients/witnesses are short dyadic rationals. This structure can favor certified reconstruction; broader LP superiority is not established. Construction certificates pass the unchanged strict checker and are never passed to a solver.

Each lane gets 30 native seconds and a 45-second process allowance. The six primary cold attempts use alternating candidate/COPT order. The `copt` lane is the retained scale-off GPU-PDLP configuration. Three supplemental `copt-auto` cells use automatic CPU LP-method selection with default presolve/scaling/dualization/crossover, four threads, common 1e-9 tolerances and unchanged original coefficients. Their exact returned parameter defaults are retained. This stronger supplemental control was frozen after the primary roster and its first candidate timing were visible; the candidate was not retuned or repeated.

Complete cost includes common model encoding, process startup, input validation, import/CSR conversion, factorization or GPU preparation, solve, internal exact proof where used, output, teardown, and a cold independent original-model 1e-9 endpoint check. GPU idle observation and resource settlement are separately charged. COPT internal GPU setup remains inside its opaque solve call.

| Model | Lane | Result | Route | Native s | Complete s | Timely strict |
| --- | --- | --- | --- | ---: | ---: | --- |
| dense | candidate | certificate_returned | exact_certified_factor_presolve | 0.116 | 0.653 | True |
| dense | copt | 10 | COPT | 30.034 | 30.618 | False |
| tall | copt | 1 | COPT | 0.625 | 1.244 | False |
| tall | candidate | resource_limit | native_compact_pricing | 30.163 | 30.610 | False |
| sparse | candidate | certificate_returned | exact_certified_factor_presolve | 0.668 | 1.250 | True |
| sparse | copt | 10 | COPT | 30.033 | 30.560 | False |
| dense | copt-auto | 1 | COPT automatic CPU | 2.934 | 3.609 | False |
| tall | copt-auto | 1 | COPT automatic CPU | 20.494 | 21.172 | False |
| sparse | copt-auto | 8 | COPT automatic CPU | 36.958 | 37.581 | False |

| Model | COPT configuration | Jointly timely strict | COPT / candidate complete ratio |
| --- | --- | --- | ---: |
| dense | copt | False | — |
| dense | copt-auto | False | — |
| tall | copt | False | — |
| tall | copt-auto | False | — |
| sparse | copt | False | — |
| sparse | copt-auto | False | — |

Ratios are reported only for jointly timely strict-certified endpoints. Vendor numerical optimality, an exact native certificate, and independent strict acceptance remain separate fields. A failure to obtain a finite strict dual bound is not a proof that a vendor numerical optimum is wrong. Deadlines and missing endpoints remain visible; no ratio is inferred from unequal or unsuccessful work.

In this roster, the candidate strictly certifies dense and sparse through CPU presolve. Tall remains a geometry deadline. GPU-PDLP COPT returns numerical optimality only on tall; automatic CPU COPT returns numerical optimality on dense and tall. Their floating endpoints have no finite strict dual bound. Automatic COPT sparse returns after 36.958 native seconds despite a requested 30-second limit and owned interruption; it remains late and has no endpoint. Its process stays within the separate 45-second outer allowance. All nine dispositions remain in the table.

The raw phase evidence identifies whether a candidate returns through certified presolve or enters pricing geometry. A successful CPU presolve does not initialize CUDA, and its GPU preparation cost is zero because no GPU work is needed. This is visible in the route, not hidden outside the stopwatch. GPU rank acceleration is evaluated separately.

## Validation and limitations

Eight new integration tests cover native/reference RREF, augmented inconsistency, resource refusals, modular rank semantics, exact certificate checks against an independent rational verifier, malformed/overflow inputs, nonuniform proposal recovery, and original optimal/infeasible/unbounded pricing outcomes. Native ASan/UBSan additionally covers 64 certificate cases and 64 RREF lifetime cases plus malformed/fill/overflow refusals. The final suite and document build are recorded in the settled checkpoint.

The first CPU admission retains its full 720 CPU-second failure charge for an unavailable optional thread-control import; the dependency was removed. The first successful GPU kernel and its source/binary receipts remain historical after the trailing-matrix optimization and fresh admission. No scientific identity is repeated. All resource caps, failures, original numerical/checker sources and public defaults remain unchanged.

One repetition, three synthetic all-active models, short dyadic certificates and unflushed caches limit generalization. Tall rectangular problems can still need expensive exact elimination and dense rational fill. The fast factor path is optional and falls back when it cannot prove an endpoint; it is not a complete LP algorithm by itself.
