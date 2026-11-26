# Factorized tall geometry and exact certificate evaluation

The opt-in tall presolve avoids the rational slack-space RREF. It proposes a solution using resident GPU projections and proves an implicit exact dual correction against every original constraint. Public solver defaults and the previous numerical sources remain unchanged.

[All 108 holdout/control outcomes](lp-sp-pricing-factor-comparison.csv), [full results and phase evidence](lp-sp-pricing-factor-results.json), [preceding scale study](lp-sp-pricing-scale.md).

## Exact geometry bottleneck

The old rectangular least-squares presolve fits inactive inequalities as equalities. When its exact primal reconstruction fails, the fallback constructs an (n+1) by (m+1) slack-space matrix and performs GMP Gauss–Jordan reduction. Normalizing pivots and eliminating each new pivot from previous rows cause rational bit growth, fill and repeated map/allocation work. The earlier implicit null-space representation is built after that reduction, so it cannot remove this bottleneck.

Fresh scaling diagnostics show 330-bit intermediate rationals and 932,733 counted operations for a 64-column fixture; its exact RREF takes 1.755 seconds. The 128- and 256-column reductions hit their eight-second limits. Native failure does not return internal counters, so missing counters are not zero work. The factorized alternatives certify all five diagnostic sizes. Geometry-only and complete-solve timings are distinct quantities.

## Implemented paths

For eligible tall shapes (m >= 2n, n <= 4096, mn <= 2^27), the new numerical proposal factors G=AᵀA once. ADMM projection batches keep A, G and state on the GPU. The separately implemented precomputed representation stores A G⁻¹ and removes triangular solves from each iteration, at the cost of another mn FP64 entries. Both representations are proposals; neither accepts a certificate. Shapes outside this dispatch retain the previous solver.

The finite development selection tried both representations and penalty multipliers 1, 4, 16 and 64 on separate inputs at three scales. It wrote all 24 results and an exploratory choice, but final resource supervision failed with coordinator_lost. Its full 2400 CPU / 600 GPU-second charge remains; cleanup is empty, no overrun is recorded, and the preceding cause is unknown. A separately supervised read-only seal preserves the completed records without regrading supervision or repeating solves. Sweep timings are excluded from performance evidence. The retained hypothesis is **factor, multiplier 16**; independent untouched holdouts evaluate it. Those fifteen models use different seeds and additionally test row-scaled tall and dense square cases.

The optimized common postprocessor directly proposes an implicit tall certificate, avoids the unsuccessful short-dual ladder, and leaves inverse-bound acceptance to the independent checker once. Two numerical dual-refinement steps reduce the residual before the dyadic base is checked; they carry no acceptance authority. Small inverse proposals remain on CPU: the cold 2000-column microbenchmark takes 0.509 seconds on CPU versus 0.657 seconds on GPU. Larger inverse proposals use GPU. The independent checker uses three integer-scan workers while the parent evaluates the inverse enclosure; all partial products are combined with unbounded integers.

## Certificate definition and authority

Let x be an exactly feasible dyadic primal point and y₀ a nonnegative dyadic dual base supported only on exactly active rows. Choose n active rows with positive y₀ and let B contain those rows of A. The certificate defines δ by Bᵀδ=c−Aᵀy₀ and y=y₀+Eδ. It does not store enormous rational inverse entries.

An approximate inverse R is untrusted evidence. The CPU checker bounds q=‖I−RBᵀ‖∞ using an independent FP64 product, a conservative γ_(2n+1) roundoff allowance and underflow allowance. If q<1, B is nonsingular and ‖(Bᵀ)⁻¹‖∞≤‖R‖∞/(1−q). Exact integer residuals then bound ‖δ‖∞. If this bound is at most the smallest selected y₀, the corrected dual is nonnegative. Exact stationarity and support on active rows imply exact zero gap.

All primal inequalities, active support and residuals are checked on the complete original CSR with arbitrary-precision integers. The enclosure assumes standard IEEE FP64 BLAS arithmetic; non-nearest CPU rounding is rejected. Small exact-Fraction products and solves cross-check the bound. This is a separate implicit exact-certificate tier. A raw floating endpoint can fail the unchanged 1e-9 checker while its explicitly defined corrected dual has an exact proof; those outcomes are never conflated.

Every accepted implicit holdout/control endpoint also receives a negative-dual and zero-inverse corruption challenge: **114 checks on 57 certificates**. Zero-inverse challenges retain complete original-matrix traversal.

## Comparison design

The primary study freezes fifteen models (three seeds, five families), 45 main solver slots and 15 controls. Tall sizes are 4000×1000 / 1M NNZ, 8000×2000 / 4M NNZ and 16000×4000 / 16M NNZ, with 20% inactive rows. Square controls are dense 2000×2000 / 4M NNZ and row-scaled sparse 8000×8000 / 1M NNZ. The follow-up has fifteen fresh models and 48 slots, including row-scaled mixed-active 4M tall and dense 4M square cases. Three additional GPU COPT controls preserve installed default Scaling on the row-scaled tall models, with otherwise identical PDLP settings. All inputs are synthetic signed dyadics; planted construction witnesses are independently checked but never supplied to solvers.

Each solver receives a 60-second native allowance and a 90-second process allowance. The primary GPU control uses inherited scale-off COPT PDLP settings except PDLPTol=1e-9, matching the required raw tolerance. The inherited PDLPTol=1e-12 control remains on the first seed at every tall size. COPT automatic CPU settings remain unchanged. All candidates and vendor endpoints receive the same postprocessor within their cohort. COPT is configured for four CPU threads; candidate BLAS is one thread and the optimized independent checker uses the four reserved CPU slots.

Complete times below include common model encoding, cold process startup, input/hash checks, all CPU/GPU preparation, solving, teardown, the unchanged raw strict audit, common reconstruction and a cold full independent proof. COPT internal GPU preparation remains in its solve call. Idle admission, resource settlement and extra corruption challenges are excluded from performance times and retained in total resource accounting. Unsuccessful timings remain in the CSV and never become certified speedup ratios.

## Primary results

| Family | Candidate certified / 3 | Candidate complete seconds: median (range) | GPU COPT eligible pairs / 3 | CPU COPT eligible pairs / 3 |
| --- | ---: | ---: | ---: | ---: |
| mixed-tall-1m | 3/3 | 3.240 (3.216–3.265) | 3/3 | 1/3 |
| mixed-tall-4m | 3/3 | 8.191 (7.990–8.484) | 3/3 | 0/3 |
| mixed-tall-16m | 3/3 | 35.839 (34.696–36.947) | 3/3 | 0/3 |
| dense-4m | 3/3 | 4.772 (4.659–5.025) | 3/3 | 3/3 |
| sparse-scaled-1m | 3/3 | 2.685 (2.683–2.694) | 0/3 | 0/3 |

The first-seed CPU controls isolate the projection cost. Their shared final proof policy is unchanged; at 4000 columns it may use a GPU inverse proposal even when the solver projection runs on CPU.

| Tall family | GPU numerical projection seconds | CPU numerical projection seconds | CPU exact certificate | Previous path solve seconds / outcome |
| --- | ---: | ---: | --- | --- |
| mixed-tall-1m | 0.959 | 2.583 | True | 60.239 / resource_limit |
| mixed-tall-4m | 1.730 | 15.602 | True | 60.564 / resource_limit |
| mixed-tall-16m | 7.451 | 68.249 | False | 62.621 / resource_limit |

Previous-path deadlines are unsuccessful outcomes, not measured speedup denominators.

## Fresh optimized holdout

| Family | Optimized complete seconds | Factor control complete seconds | COPT GPU complete seconds | Eligible COPT pairs / 3 | Median COPT / optimized |
| --- | ---: | ---: | ---: | ---: | ---: |
| mixed-tall-1m | 2.479 (2.379–2.584) | 2.730 (2.729–2.986) | 2.582 (2.481–2.635) | 3/3 | 1.020× |
| mixed-tall-4m | 4.989 (4.877–5.292) | 5.843 (5.789–5.878) | 5.188 (5.028–5.289) | 3/3 | 1.031× |
| mixed-tall-16m | 16.401 (16.199–17.519) | 19.954 (19.909–22.115) | 17.451 (17.158–19.426) | 3/3 | 1.077× |
| mixed-scaled-tall-4m | 10.297 (10.292–11.310) | 11.263 (11.263–11.263) | 5.637 (5.488–6.000) | 3/3 | 0.533× |
| dense-4m | 4.911 (4.708–5.321) | 4.810 (4.808–5.220) | 18.154 (15.228–21.080) | 2/3 | 3.670× |

Cold independent CPU checker controls use identical certificates; exact residuals and acceptance decisions agree, and both inverse enclosures validate:

| Nonzeros | Parallel complete seconds | Serial complete seconds | Serial / parallel |
| ---: | ---: | ---: | ---: |
| 1,000,000 | 0.566 | 0.915 | 1.618× |
| 4,000,000 | 1.370 | 2.818 | 2.056× |
| 16,000,000 | 4.725 | 11.229 | 2.376× |

These are one-time, later serial controls without cache flushing. Their extra audit costs remain in resource accounting and do not replace the original measured pipeline.


Default-scaling COPT GPU controls on the scaled tall family:

| Seed | Both exact and timely | Optimized complete seconds | Default-scaling COPT complete seconds | COPT / optimized |
| ---: | --- | ---: | ---: | ---: |
| 124401 | False | 11.310 | 4.028 | — |
| 124421 | False | 10.297 | 3.670 | — |
| 124439 | False | 10.292 | 3.769 | — |

The primary cohort has 16/30 eligible candidate–COPT pairs; the fresh optimized cohort has 14/15 eligible optimized–COPT pairs. Counts refer to their own prospective common exact-certificate pipelines, not raw endpoint acceptance or pooled timing repetitions.

All 6 square old/new controls have identical exact certificates: True. The median new/old native-time ratio is 1.005; the complete-time ratio is 1.000. Single timings have noise; individual ratios and regressions remain in the full results. Wide dispatch is unchanged but has no fresh timing measurement here.

## Limits and reproduction

These results establish performance and exact proof validity for the represented synthetic inputs. They do not establish broad LP superiority, infeasible/unbounded-case coverage for the new tall presolve, or completion of the paper’s strongly-polynomial algorithm. The three seeds are descriptive samples, not a broad workload distribution. Ill-conditioned or unsupported implicit reconstructions can remain inconclusive.

The optimized numerical entry point is `tools/lp_sp_pricing_transform_run.py MODEL OUTPUT --representation factor --rho-multiplier 16`. The common postprocessor is `tools/lp_sp_pricing_transform_endpoint.py`; independent acceptance is `tools/lp_sp_pricing_factor_parallel_proof.py`. Run GPU commands only with an appropriate fresh admitted resource reservation. Frozen plans, source hashes, exact parameters, all outcomes and every original failure charge remain in the local evidence.

The two-hour deadline and unchanged 240000 CPU / 30000 GPU-second total ceilings govern this study. Final tests, all CUDA sanitizer receipts, settlement and owned-process absence are recorded in the compact checkpoint. No historical scientific cell was repeated.
