# Exact independent checking — GPUP-FP4-CHECKER

Status: implementation and frozen comparison complete; dense prepared gains, no broad cold retention
Date: 2026-11-12
Contract: [SPEC-0032](../specifications/SPEC-0032-exact-checker-acceleration.md)
Decision: [ADR-0064](../decisions/ADR-0064-exact-checker-acceleration.md)
Prior results: [FP4 acceleration](lp-fp4-accel.md)

## Why cold retention failed

The prior criterion required at least 1.10x cold model-median geometric mean,
no certified model-median regression and no coverage loss. The old strict FP4
ratio was 0.986329x, with a 0.974610–1.010632 bootstrap interval. Its bounded
coverage passed; its latency criterion did not. The interval includes parity,
so this does not establish that every small cold regression is intrinsic.

Dense512 saves only about 0.9 ms of GPU work, whereas complete cold execution
costs roughly 700 ms. Even eliminating its entire roughly 5 ms native GPU phase
cannot deliver a 10% cold gain. This is a limit on this particular accelerated
fraction, not a fundamental limit on FP4. In the new cohort, optimized strict
dense512 cold medians are 715.665 ms native and 719.063 ms FP4. Their recorded
session setup medians are about 583 ms. That phase includes original-model
preparation, CUDA context/module/stream creation and independent checker startup.
The remaining complete boundary also includes process startup/exit and durable
response/log delivery; it is not all assigned to any one unprofiled component.
Cold is distinct from repeated solves in an already prepared service.

The broad grid also includes small sparse and irregular problems. A dense tensor
matrix-vector implementation pays encoding, component products, FP32-pair state
updates, guards and multiple launches; the sparse native path has much less work.
A favorable dense case cannot offset these broad costs under a no-regression rule.

## Whether FP4 iterations are slower

Both dense lanes take the same 200 physical updates. These are prepared medians
with the optimized checker at strict 1e-9, on the same admitted Blackwell image:

| Dense size | Native GPU ms | FP4 GPU ms | Native / FP4 microseconds per update |
|---|---:|---:|---:|
| 128 | 2.885 | 3.422 | 14.427 / 17.108 |
| 256 | 3.714 | 3.503 | 18.569 / 17.513 |
| 512 | 5.388 | 4.458 | 26.941 / 22.289 |

These CUDA event times include stream submission gaps, not just instruction
throughput. FP4 is slower per update at 128, slightly faster at 256, and about
1.21x faster at 512. The old small coupled-equality example takes about 16.9 us
per FP4 update versus 2.22 us native. It compares the explicitly selected grid
FP4 lane with nativefast's sparse fused lane; forcing a tensor path on that model
is not beneficial. Other families can also perform additional physical work:
two-component starts promote on local guards, while the generic dense 128/256/512
cases all have matched update counts and no recovery.

This implementation uses multiple E2M1 components and component cross-products,
encoding/decoding, power-of-two scaling, compensated FP32-pair updates, local
guards and original-A FP64 reference products once per at-most-32-update window.
It is not a single FP4 operation replacing a single FP64 operation. The grid
candidate launches separate x/y/guard kernels for ordering; nativefast uses a
simpler fused sparse path where appropriate. Larger dense work amortizes these
costs. The evidence therefore points to algorithm/work mapping and delivery costs;
it does not identify a malfunctioning GPU or an FP4 hardware throughput ceiling.

## Checker improvements and exact authority

The former original-model feasibility evaluator binary-searches variable IDs for
every coefficient at every assessment. Cache those immutable indices once. At
65536 or more nonzeros, evaluate independent rows with four CPU workers and join
in original order. Preserve every product, sequential sum/magnitude operation,
finite check, signed-zero normalization, full report field and first error.

Dual checking caches odd integer coefficient significands/exponents, decomposes
repaired multipliers once, reuses one scratch vector per worker and reduces it in
place using the original segment tree and padding additions. A proved integer
representability predicate replaces decomposition of each rounded product; zero,
subnormal, overflow and refusal cases retain the original decisions. Final gap
assessment and original feasibility/bound/refusal criteria remain unchanged.
The checker is still an independent CPU process bound to original model and
endpoint bytes. No answer cache or approximate certificate is introduced.

The final CPU-only profile interleaves baseline and optimized assessments of all
102 retained unique endpoints, 20 repetitions each. Median-of-endpoint-medians
for accepted strict dense512 assessments:

| CPU checker component | Baseline ms | Optimized ms |
|---|---:|---:|
| Original-model feasibility/objective | 3.883 | 0.367 |
| Conservative dual certification | 3.354 | 2.269 |
| Complete assessment | 7.399 | 2.916 |

The complete CPU assessment improves **2.54x**. This microprofile excludes checker
process transport; the complete solve comparison below measures its actual effect.

## New matched complete-cost comparison

All 960 frozen cells complete: twelve original models, two arithmetic lanes, two
checker implementations, two final tiers, cold/prepared and five repetitions.
All eleven bounded families certify at both tiers (880 certificates); 80
intentional unbounded-direction cases refuse. All audits, terminal endpoints,
certificate fields, checkpoints, recovery decisions and physical work match their
retained originals exactly, apart from executable identity and measured times.
The original binary is the control. Device image and numerical controller remain
unchanged. This is a new checker comparison; no old scientific cell is retried.

Strict dense512 prepared medians in this matched cohort:

| Metric | Original checker | Optimized checker |
|---|---:|---:|
| FP4 checker phase | 9.851 ms | 6.433 ms |
| FP4 complete prepared solve | 19.203 ms | 15.924 ms |
| Native complete prepared solve | 20.217 ms | 16.527 ms |

FP4 complete latency improves **1.206x (17.1% reduction)**; the paired-bootstrap
95% speedup interval is 1.138–1.366x. Both arithmetic lanes benefit. With the new
checker, FP4's observed complete median is 3.8% faster than native, but the
corresponding interval is 0.975–1.117x and includes parity. This is a promising
bounded dense result, not a reliable broad FP4 performance advantage.

The broad strict prepared FP4 checker-improvement geometric mean is 1.0522x
(1.0351–1.0692x). Native's broad prepared ratio is 1.0007x (0.9733–1.0432x), with
small-model median regressions; do not generalize the dense checker win to all
models or promote a public native preset from this experiment.

| Optimized FP4 versus optimized native, cold | Geometric mean | 95% interval |
|---|---:|---:|
| Final 1e-7 | 0.999376x | 0.978417–1.007011x |
| Final 1e-9 | 0.993444x | 0.978079–1.004726x |

Neither tier meets the unchanged broad retention criterion. All uncertainty
uses 2000 within-model paired bootstrap resamples of five trials. Dense intervals
use seed 320065; full-grid intervals use 320064. Models are constructed development
families bounded to 512 rows/columns, not a held-out production population.

The remaining dense prepared costs include 6.43 ms of checker round-trip work,
4.46 ms GPU time, original-model audits and evidence export/delivery. Further
checker work should target conservative dual reduction and process transport;
cold improvement requires measured setup/teardown work. More GPU arithmetic
speed alone has little influence on the current cold endpoint. Sparse native
remains appropriate for these small sparse inputs. No public preset changes.

## Acceptance, preserved failures and resources

Twenty-one isolated Rust tests cover 500000 full-bit-pattern product pairs plus
169 edge pairs, 2880 complete feasibility/error comparisons, 720 complete cached
certificate comparisons, original rational fixtures and reduction-tree/refusal
cases. Four Python contracts cover scientific drift detection, checker executable
binding, terminal eligibility, invalid endpoints and closed-budget admission.
The original core/LP gate passes 18 + 45 Rust tests. All 102 retained endpoints
match their original serial certificates; 32 new device integration cells pass.
The unchanged device source/image reuses its exact prior four-sanitizer admission.
No new GPU arithmetic or sanitizer execution is claimed.

The initial build fails on an isolated profiling-module import; the next build
passes. A later combined job passes arithmetic tests but Clippy refuses an
integer-comparison style; a separate equivalent-comparison correction passes lint
and release build. Both failed jobs retain full 720 CPU-second reservations,
exact sources and logs. All later scientific cells complete without retry.

The separate ceiling is 24000 CPU / 1200 GPU seconds, with no historical funds
transferred. Final accounting includes all failures, 256 preparation seconds and
64 closing-administration CPU seconds. Sources, raw measurements, checkpoints,
images, supervisor logs and cleanup remain in `artifacts/gpup-fp4-checker-v1`.
The public solver/checker and all historical numerical source bytes are preserved.
GPUP-8 remains incomplete, TENSOR2 conditional and GPUP-9 gated. Commit locally;
no push/publication.

Machine evidence: [all measurements, profiles, bindings and decisions](data/fp4-checker-result-v1.json).

Final allocation closed: **3105.019900448 CPU seconds** and
**216.672767949 GPU seconds**, including both failed reservations. All supervisor
and guardian cleanup is empty. Exact preservation covers 1636 historical files.
[Acceptance](data/fp4-checker-acceptance-v1.json),
[historical-file bindings](data/fp4-checker-history-v1.json), and
[closed accounting](data/fp4-checker-accounting-v1.json).
