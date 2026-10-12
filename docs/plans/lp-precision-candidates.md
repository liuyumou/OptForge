# LP Precision Candidate Register

Status: research candidates, updated 2026-10-12. No supported preset. Preserve the
[rounding analysis](../benchmarks/lp-fp32-rounding-analysis.md) and
[measured latency diagnosis](../benchmarks/lp-fp32-slowdown-diagnosis.md).
The [2026-09-30 research review](lp-low-precision-research-2026-09-30.md)
preserves the evidence, equations, primary sources, hardware qualifications and
proposed experiments behind the current hypotheses. It is non-normative research,
not an accepted numerical contract, implementation order, GPU allowance or preset.
The [2026-10-12 architecture](lp-precision-architecture-2026-10-12.md) now adds
component IDs, low-level layouts, proofs and motivation, with the accepted CPU subset
of [SPEC-0020](../specifications/SPEC-0020-lp-expansion-arithmetic.md) and draft
[SPEC-0021](../specifications/SPEC-0021-lp-refinement.md). Its
[experiment design](../benchmarks/lp-precision-design-experiments.md) isolates
components and interactions. GPUP-REP CPU validation is complete under ADR-0034; GPUP-EXEC is next. No GPU
behavior or allowance follows. All proposals retain
original-model 1e-9 acceptance.

## Completed investigations and remaining limits

| Investigation | Evidence | Remaining limit |
| --- | --- | --- |
| Exact power-of-two and factored scaling, GPUP-5B | [Matched study](../benchmarks/lp-exact-components-gpup5b.md) restores 27/36 timing coverage versus 12/36 for ordinary scaled FP32 storage; simple original coefficients become inexact after non-dyadic scaling. | Original-corpus exact representability is not a general LP property; changed scaling affects convergence and setup. No supported latency recipe. |
| Scalar component sparse products, GPUP-5B | Three components preserve input information, but measured cross-products with per-nonzero FP64 compensated recombination lose badly on sm_120; [root cause](../benchmarks/lp-fp64-pipe-root-cause.md). | Deprioritize that measured implementation. This does not rule out Tensor Core/integer emulation that amortizes recombination across a dense dot product or tile. |
| Double-float FP32 pairs, GPUP-5C | [Charged study](../benchmarks/lp-fp64-pipe-gpup5c.md) measures 100.3 us/update on dense_block-65536 versus 111.8 for integer-guard FP64; inner sparse arithmetic avoids FP64. | Product underflow loses scheduling coverage; scale policy and endpoint coverage remain unresolved. Early standalone microbenchmark gains are separately labeled, not certified solve gains. |
| Integer-pipe guards and two-launch fusion, GPUP-5C | Bitwise FP64 endpoint equivalence; integer guards help at scale and fusion helps launch-bound cases. | Fusion's vector-update tail can lose at scale. These research kernels are separate from the precision image used by adaptive solves; migration needs its own identity and gates. |
| Explicit tolerance tiers, GPUP-5C | FP32 storage coverage improves from 12/36 at 1e-9 to 24/36 at 1e-6 and 30/36 at 1e-4. | Looser acceptance does not answer the current unchanged-1e-9 objective. Existing opt-in tiers and defaults stay unchanged. |
| Original-operator audits, rollback and promotion, GPUP-6 | [Adaptive study](../benchmarks/lp-adaptive-gpup6.md) recovers FP64 coverage on available cells, with complete charged rollback/replay. | Missing evidence remains visible. Last-update audits are not residual-driven outer refinement; [latest convergence study](../benchmarks/lp-convergence.md) retains substantial reference/recovery costs and no preset. |
| Larger development corpus, GPUP-5C | Frozen lp-manifest-v2 extension reaches 65536 rows, including an FP32-inexact mixed family. | Latest mixed-65536 primary samples remain uncertified. Larger or new instances need their own frozen development decision; no held-out tuning. |
| Repeated-solve context reuse, GPUP-THROUGHPUT | Complete under [SPEC-0014](../specifications/SPEC-0014-lp-repeated-solve-throughput.md)/[ADR-0023](../decisions/ADR-0023-repeated-solve-throughput.md); [report](../benchmarks/lp-repeated-solve-throughput.md) and [host-input follow-up](../benchmarks/lp-throughput-host-input.md) retain successes and large-session gaps. | Separate throughput endpoint; never substitute amortized batch time for fresh-single latency. Adaptive sessions and full MILP search remain separate contracts. |

## New representation and state candidates

| ID | Candidate / motivation | Admission and rejection gate |
| --- | --- | --- |
| R1 | Exact compact h/l/q/exponent encoding; normalized binary64 leaves q in [-8,8], so scaled FP16/FP8/INT8 tails suffice. Original bits with integer decoding are the eight-byte control. | CPU codec accepted under ADR-0034 with complete payload/layout receipts; raw FP16 tails fail. Device decode cost and total traffic remain GPUP-EXEC questions. |
| R2 / S | Symbolically scaled arithmetic and persistent accurate state across updates, reductions and controller operations. | CPU 64-bit-significand primitive semantics are accepted. Device implementation and full persistent-state replay remain gated; current pair kernels still return to FP64 state. |
| N | Stable support-function proximal map, scaled norms and residual-aware objective/gap formulas. | Exact-real identities plus rounded edge cases; preserve residual terms and final host authority. |

## Current research hypotheses

The six main directions below are proposals, not implemented wins or claims of
inventing their underlying numerical techniques. Their detailed derivations,
failure conditions and falsifiable experiments live in the
[research review](lp-low-precision-research-2026-09-30.md). Their order here does not
approve behavior; the roadmap and ADR-0033 now own the revised planning priority.

| Candidate | Question and mechanism | Prerequisite / rejection gate |
| --- | --- | --- |
| True outer LP refinement with anchored products | Solve scaled correction problems from original-model residuals; use accurate anchor products plus low-precision products of small changes so matrix bias acts on the change. | Full primal/dual/bound transformation, original-operator residual refresh, contraction evidence, consistent transpose, step assumptions and complete refresh/inner-solve costs. One corrected last step is not equivalent. |
| Lean precision executor | Carry proven integer guards and suitable launch schedules into dedicated low-precision kernels; avoid per-nonzero FP64 conversion/recombination and repeated dispatch/allocation. | Matched numerical controls and SASS inspection, new execution identity, unchanged guard meaning, cancellation and sanitizers; compare with both precision FP64 and tuned FP64. |
| Scaled double-float | Add exact power-of-two vector/block exponents to FP32 pairs to address observed product underflow while keeping the sparse loop off the FP64 pipe. | Range/error analysis across cancellation and decaying iterates, guarded exceptional paths, checkpointed scale state and complete split/metadata costs. Pair storage is not a bandwidth compression claim. |
| Selective activity-error budgets | Bound operator-tail activity and arithmetic error in original units; retain cheap arithmetic where it fits the budget, refine sensitive rows/blocks or explicit outliers. | Conservative row and transpose error bounds, dynamic vector envelopes, canonical operator mapping, metadata admission and final host certification; no silent coefficient pruning. |
| Active-face polishing and preconditioning | Use low precision to discover likely active constraints, then solve a smaller accurate correction problem; consider low-precision blocks as preconditioners rather than the final operator. | Degeneracy/rank handling, reversible working-set expansion, original-model checks over every row, fallback and full factorization/setup accounting. No basis, active-set or linear-system guarantee is assumed for arbitrary LPs. |
| Layout-appropriate Tensor Core/integer emulation | Test real dense subblocks or an accurate dense correction/preconditioner; amortize component recombination per output rather than per sparse nonzero. | Actual sm_120 instruction support, represented-operand equivalence, accumulation/range/repeatability analysis, single-RHS packing/padding costs and untouched sparse remainder. Dense GEMM literature is not sparse SpMV speed evidence. |

Additional hypotheses are subordinate experiments, not implicit additions to the
GPUP-7 contract:

| Candidate | Question and prerequisites |
| --- | --- |
| Assessment scheduling | Can a cheap progress signal avoid futile full host assessments while retaining mandatory final certification and all required recovery? Requires a separate accepted stopping/assessment contract, paired convergence/coverage checks and explicit saved/added work. |
| Reliable updates, compensated state and error feedback | Can retained update residuals or periodic recentering prevent small changes from disappearing? Requires error analysis, full checkpoint/replay state and comparison with FP64 masters; it does not by itself repair a once-rounded matrix. |
| Better preconditioning | Can stronger or precision-aware scaling reduce work enough to repay its setup? Keep operator bias and step-size effects separate; charge construction, conditioning estimates and changed iteration counts. Exact power-of-two scaling was already tested. |
| Sparse integer limbs | Could bounded integer dot products avoid FP64 without dense packing? Requires overflow/carry proofs, measured integer instruction and metadata cost, and an accurate original-model outer path; not a consequence of advertised Tensor Core throughput. |
| Stochastic rounding | May change accumulation bias or stagnation; one randomized matrix conversion still freezes a perturbed operator. Requires seeded replay, consistent transpose and variance/error analysis. |
| Block scaling, compressed exponents and adaptive component counts | Could reduce tail/metadata traffic or bound omitted component activity cheaply? Requires range proofs, exact exceptions, admitted memory and measured preparation/refresh cost. |
| Genuine independent right-hand sides and MILP batching | Could amortize matrix packing across distinct searches, nodes or correction systems? Requires actual independent work and separate throughput/MILP authority; sequential PDHG iterates are not independent columns. |

Primary starting points: [accurate sums and products](https://www.tuhh.de/ti3/paper/rump/OgRuOi04a.pdf),
[stochastic rounding analysis](https://eprints.maths.manchester.ac.uk/2763/),
[Ozaki accuracy extensions](https://arxiv.org/abs/2511.13778), and
[NVIDIA emulation documentation](https://docs.nvidia.com/cuda/cublas/index.html#floating-point-emulation).
The review links additional primary literature and records its applicability
limits. No literature result substitutes for certified local end-to-end evidence.

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
