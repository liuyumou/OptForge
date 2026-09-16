# LP Precision Candidate Register

Status: research candidates, 2026-09-16. No supported preset. Preserve the
[rounding analysis](../benchmarks/lp-fp32-rounding-analysis.md) and
[measured latency diagnosis](../benchmarks/lp-fp32-slowdown-diagnosis.md).
GPUP-5B investigates exact scaling and fixed two/three-component sparse products
first under [ADR-0021](../decisions/ADR-0021-exact-scaling-components.md).

| Candidate | Evidence or question | Prerequisite / activation gate |
| --- | --- | --- |
| Exact power-of-two and factored scaling | Original coefficients are FP32-exact; scaled conversion creates bias. | GPUP-5B matched scaling controls, exact range checks, original-model coverage and total latency. |
| Fixed component sparse products | Three components reproduce the sampled scaled matrix exactly; extra arithmetic/storage may dominate. | GPUP-5B CPU/device arithmetic, exponent handling, packing-inclusive solves. |
| Adaptive component counts | Can row-tail bounds and vector norms bound discarded activity cheaply? | Accepted policy, product/reduction bounds, original-operator audits, complete work accounting; no silent truncation. |
| Stochastic rounding | May avoid biased accumulation/stagnation; a once-rounded matrix remains perturbed. | Seeded replay, consistent A/transpose, variance/error analysis and a separately frozen experiment. |
| Compensated working state / error feedback | Can retained update residuals prevent small updates disappearing? | Independent error analysis, complete checkpoint state, comparison with FP64 masters. |
| Original-operator audits, refinement, rollback, promotion | One corrected final step did not recover coverage. | GPUP-6 bounded interface, fault injection, charged replay, cancellation and promotion/demotion rules. |
| Ozaki/Tensor Core FP16/BF16/FP8/integer components | Dense GEMM results motivate investigation, but sparse single-RHS economics remain unknown. | Actual-device instruction support, error bounds, explicit FMA/reduction policy, padding/packing-inclusive sparse comparison. |
| Block scaling / compressed exponents / exact outliers | Could reduce per-value exponent and component traffic. | Canonical transpose mapping, range/outlier proofs, metadata admission and measured total costs. |
| Specialized kernels / fusion / cached handles / buffer reuse | Generic kernels and host synchronization are measured or inspected costs. | Hold numerical policy fixed; new execution identity; cancellation/guard/sanitizer gates. |
| Larger sparse or block-structured instances | Current matrices do not establish hardware-scale benefits. | Explicit frozen development extension; retain existing seeds/splits and account for exploration budget. |
| Repeated-solve context reuse | Context setup dominates short solves. | Separate throughput objective and protocol; never substitute it for current single-solve latency. |

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
