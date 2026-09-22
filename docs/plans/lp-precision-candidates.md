# LP Precision Candidate Register

Status: research candidates, updated 2026-09-19. No supported preset. Preserve the
[rounding analysis](../benchmarks/lp-fp32-rounding-analysis.md) and
[measured latency diagnosis](../benchmarks/lp-fp32-slowdown-diagnosis.md).
GPUP-5B investigated exact scaling and fixed two/three-component sparse products
under [ADR-0021](../decisions/ADR-0021-exact-scaling-components.md). The
[FP64-pipe root-cause note](../benchmarks/lp-fp64-pipe-root-cause.md) closes the
component cross-product line and GPUP-5C acts on the rows marked below under
[ADR-0022](../decisions/ADR-0022-fp64-pipe-execution-and-tolerance-tiers.md).

| Candidate | Evidence or question | Prerequisite / activation gate |
| --- | --- | --- |
| Exact power-of-two and factored scaling | Original coefficients are FP32-exact; scaled conversion creates bias. | GPUP-5B matched scaling controls, exact range checks, original-model coverage and total latency. |
| Fixed component sparse products | Closed: three components are exact but every recombination runs on the 1/64-rate FP64 pipe; 2.7x slower with no route to acceleration on sm_120. | Retained as accuracy references only. |
| Double-float FP32 pairs (GPUP-5C) | 48-bit significand, one multiply plus three FMAs, error-free FP32 sums, no FP64 in the loop; 1.3-1.4x over FP64 at scale in the uncharged microbenchmark. | ADR-0022 `doublefloat-fp32`: pair oracle, rational fixtures, bitwise device differential, charged study. |
| Integer-pipe guards and fused two-launch schedule (GPUP-5C) | Guard compares and six launches per proposal dominate the research executor; both are removable without changing arithmetic. | ADR-0022 `intguard-fp64`/`fused-fp64`: identical endpoints to the FP64 control, charged study. |
| Tolerance tiers (GPUP-5C) | FP32 storage failures sit far above the 1e-9 per-row allowance; published PDLP defaults are 1e-4. | ADR-0022 explicit per-request tiers 1e-6/1e-4 under a new identity; 1e-9 default unchanged. |
| Adaptive component counts | Can row-tail bounds and vector norms bound discarded activity cheaply? | Accepted policy, product/reduction bounds, original-operator audits, complete work accounting; no silent truncation. |
| Stochastic rounding | May avoid biased accumulation/stagnation; a once-rounded matrix remains perturbed. | Seeded replay, consistent A/transpose, variance/error analysis and a separately frozen experiment. |
| Compensated working state / error feedback | Can retained update residuals prevent small updates disappearing? | Independent error analysis, complete checkpoint state, comparison with FP64 masters. |
| Original-operator audits, refinement, rollback, promotion | One corrected final step did not recover coverage. | GPUP-6 bounded interface, fault injection, charged replay, cancellation and promotion/demotion rules. |
| Ozaki/Tensor Core FP16/BF16/FP8/integer components | Deprioritized: any FP64 recombination pays the 1/64 rate, BF16/FP8 parts convert to FP32 before multiplying, and 18-33 nonzeros per row give no dense tile; FP8 slicing needs about 14 slices for 53 bits. | Only with an FP32-only recombination and a block-dense workload; padding/packing-inclusive comparison. |
| Block scaling / compressed exponents / exact outliers | Could reduce per-value exponent and component traffic. | Canonical transpose mapping, range/outlier proofs, metadata admission and measured total costs. |
| Specialized kernels / fusion / cached handles / buffer reuse | Generic kernels and host synchronization are measured or inspected costs. | Hold numerical policy fixed; new execution identity; cancellation/guard/sanitizer gates. |
| Larger sparse or block-structured instances | The twelve development instances are launch-bound (about 4 us per SpMV against a 2 us floor). | GPUP-5C freezes a development extension up to 65536 rows plus a `mixed` family under lp-manifest-v2; larger sizes need their own decision. |
| Repeated-solve context reuse | Context creation is 208 ms of a 512 ms certified solve on irregular-2048, the largest single cost. | Separate throughput objective and protocol; never substitute it for current single-solve latency. Now being implemented as GPUP-THROUGHPUT under [SPEC-0014](../specifications/SPEC-0014-lp-repeated-solve-throughput.md) and [ADR-0023](../decisions/ADR-0023-repeated-solve-throughput.md), both accepted 2026-09-20 after the GPUP-5C report showed host phases exceed kernel time at 65536 rows. |

Primary starting points: [accurate sums and products](https://www.tuhh.de/ti3/paper/rump/OgRuOi04a.pdf),
[stochastic rounding analysis](https://eprints.maths.manchester.ac.uk/2763/),
[Ozaki accuracy extensions](https://arxiv.org/abs/2511.13778), and
[NVIDIA emulation documentation](https://docs.nvidia.com/cuda/cublas/index.html#floating-point-emulation).
Potential variants are hypotheses, not implemented wins or claims of novelty.

## GPUP-5B observations to carry forward

The [exact-scaling/component report](../benchmarks/lp-exact-components-gpup5b.md)
restores 27/36 timing coverage with both exact and two-component approximate modes,
versus 12/36 for scaled FP32 storage. This prioritizes original-operator error
control; it does not select a supported arithmetic policy. The prototype splits
vector operands per nonzero, stores an exponent per coefficient and repeats
preconditioning/norm setup for explicit scaling. These are concrete optimization
candidates: cache vector expansions, pack exponents by row/block, specialize or
fuse without changing arithmetic, and reuse already computed host preparation.
Each requires its own matched comparison and complete setup/memory accounting.
The three-component cross-product profile is slower than reconstructing operands
for native FP64 multiplication. Future Tensor Core work must address the sparse
layout and extra products, not extrapolate dense GEMM throughput to these runs.
