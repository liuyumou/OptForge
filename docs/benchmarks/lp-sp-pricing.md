# Pricing LP: implementation and completed evaluation

Date: 2026-11-25.

**The CPU bottleneck is substantially reduced. The complete frozen comparison is measured; broad end-to-end superiority is not established.**

The [reference integration](../../research/lp-sp-pricing/python/sp_pricing/reference.py) connects symbolic log compression, calibration, implicit expert cells, rational ellipsoid optimization, recursive prices and sequential circuit recovery. Component tests pass; no complete literal paper run fits the admitted resource limits. The practical variant has exact original-model certificates and does not inherit the paper’s strongly polynomial guarantee.

See the [plan](../plans/lp-sp-pricing.md), [implementation](../../research/lp-sp-pricing/README.md), [compact evidence](lp-sp-pricing-results.json), and [all confirmation rows](lp-sp-pricing-confirmation.csv).

## CPU cost and implementation changes

Profiles showed that repeated Fraction operations while evaluating experts consumed about 85–90% of the profiled small solves. Shared integer denominators remove that work. An exact signed-network flow formulation replaces the finite market’s repeated LP cuts; exact flow balance and primal–dual objective equality check every market optimum. Residual-potential constraints recover lexicographic prices. This practical flow oracle is not presented as a strongly polynomial replacement for the reference ellipsoid.

The next bottleneck was auxiliary LP work. A persistent GMP tableau now reuses its basis across objectives and stops immediately on an exact positive-label witness. Native exact elimination, sparse proof products and the calibration’s proved quadratic-error bound reduce preparation and checking. Negative labels still require an exact bound or an exactly checked opposite-slot witness. Final original-model acceptance is unchanged.

| Development version | Original 14 cases certified | Capped total seconds |
| --- | ---: | ---: |
| cpu-ladder-v1 | 7/14 | 88.190 |
| cpu-ladder-v2 | 9/14 | 78.075 |
| cpu-ladder-v3 | 13/14 | 47.282 |
| cpu-ladder-v4 | 13/14 | 27.055 |
| gpu-ladder-v1 | 7/14 | 88.094 |
| gpu-ladder-v2 | 13/14 | 52.228 |

The table is a separate-seed development series, with one diagnostic measurement per version and a ten-second cap per case. It is not a randomized solver comparison. The final 21-case selection chose CPU over GPU by the frozen rule: maximize timely exact certificates, then minimize capped complete cost.

The held-out attempt timings locate the remaining bottleneck. Median phase shares include interrupted work and describe cost, not convergence:

| Size | Market share | Auxiliary-label share | Calibration share | Median completed queries |
| --- | ---: | ---: | ---: | ---: |
| small | 8.4% | 75.5% | 10.8% | 2 |
| medium | 1.8% | 91.7% | 5.4% | 0 |

## Frozen original-LP comparison

All 28 original models and 252 lane/repetition slots remain visible. Seven families, 16/64 variables, two held-out seeds and three repetitions compare the practical candidate, unchanged image-v11 and COPT scale-off GPU PDLP. Native windows are 10/30 seconds; process windows are 30/60 seconds. Ratios require both endpoints to pass the unchanged original-model 1e-9 checker before their deadlines. Exact rational acceptance is additionally reported for the candidate.

| Lane | Attempted / slots | Timely strict certificates | Late strict certificates |
| --- | ---: | ---: | ---: |
| practical | 78/84 | 6 | 0 |
| retained_image_v11 | 84/84 | 3 | 0 |
| copt_scale_off | 84/84 | 0 | 0 |

Against retained_image_v11: 3 jointly timely certified repetitions, covering 1 models with all three repetitions. The median baseline/candidate complete-cost ratio is 0.763x on those repetitions. The candidate takes about 1.31 times the baseline's complete cost.

Against copt_scale_off: 0 jointly timely certified repetitions, covering 0 models with all three repetitions. No ratio is defined.

Vendor status and strict certificate acceptance are separate. On these free-variable models, a nonzero floating dual stationarity residual can prevent a finite rigorous bound. A reported optimal status is retained even when the unchanged checker cannot certify it; this does not establish that the vendor optimum is wrong.

| Lane | Endpoints independently assessed | Primal feasible | No finite strict dual bound |
| --- | ---: | ---: | ---: |
| practical | 6 | 6 | 0 |
| retained_image_v11 | 84 | 78 | 81 |
| copt_scale_off | 72 | 72 | 72 |

Complete cost includes common model encoding, a fresh solver process, output transport and all mandatory independent endpoint audits. GPU idle observation and resource finalization are outside the comparable window but remain charged to the allocation. COPT import/preparation and its opaque solve call are separately retained.

A campaign output-parent error consumed six failed solve reservations before any LP in those families started. Every full charge remains. Recovery uses only untouched cells, with identical numerical sources, models and process windows. To stay within the unchanged phase allocation, the six recovered families execute CPU candidates and GPU baselines in separate blocks. They retain three repetitions and per-lane order, but lose the original cross-lane interleaving. The degenerate family retains the original rotation. All timing ratios are therefore descriptive; unflushed caches and unmatched certificates further limit generalization.

## GPU findings and scale limits

Dense and CSR GPU products share one matrix across batches of 1/8/32/64 independent states, now searching both signed slots. Exact checks accept witnesses and bounds; unresolved coordinates escalate and fall back to exact CPU work. Final admission passes 224 configuration checks and all four CUDA sanitizers. Both native CPU components pass ASan/UBSan and independent differential tests. The 35 mathematical/component tests include symbolic compression restarts, grouped cell sums, actual grouped-market optimization, ellipsoid feasibility/lexicographic recovery and sequential circuits.

The earlier 167/168 completed batching cells remain historical throughput evidence, including the incomplete cell that was never retried. The FP64 width-64 diagnostic measured 37.6x dense and 43.7x CSR proposal throughput versus sequential proposals. That structured resident-matrix diagnostic excludes exact checking and is not an original-LP speedup. FP4 uses simulated E2M1 components on CUDA cores; packed FP4 and tensor-core throughput are not claimed.

Both proposed original billion-nonzero LPs remain unsupported before generation. Explicit mixed-optimality bases and their transposes alone require about 804 GB for the dense case and 800 TB for the sparse case. Original sparsity does not prevent null-space fill. The held-out practical capacity refusals are also retained, alongside baseline measurements on those models.

## Evidence and resources

All failed reservations keep their full charges and original receipts. The baseline adapter failures exposed a missing model identity and a missing verified lease handoff; their failures remain, and admission subsequently sealed the exact endpoint conventions using retained development proofs. The original project numerical sources, scientific identities and public defaults are unchanged. No historical billion experiment was repeated.

The [settled checkpoint](lp-sp-pricing-checkpoint.json) records final allocation use, failures and cleanup identities. The earlier prototype report and compact receipts are preserved under the new report’s artifact directory.
