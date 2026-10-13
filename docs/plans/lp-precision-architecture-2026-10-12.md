# Precision architecture: motivations, designs and open obligations

Status: proposed numerical designs; planning order accepted by ADR-0033
Owner: numerical backend and experiment tooling
Introduced: GPUP-DESIGN, 2026-10-12
Last reviewed commit: bootstrap
Implementation: existing studies and the bounded GPUP-EXEC exact-dot subset; remaining designs below are not implemented
Tests: CPU design examples; future gates in the experiment design

## Goal and reading order

Accelerate a solve of the original binary64 LP to its requested feasibility and
certified-gap tolerances. The primary comparison remains fresh-process total
latency at unchanged 1e-9 acceptance, including preparation, recovery and final
host certification. Other tolerance tiers and repeated-solve throughput retain
separate labels. High accuracy need not require native FP64 at every operation.

Read this rationale with [SPEC-0020](../specifications/SPEC-0020-lp-expansion-arithmetic.md)
for exact encoding/arithmetic obligations, [SPEC-0021](../specifications/SPEC-0021-lp-refinement.md)
for the proposed LP transformations, and the
[experiment design](../benchmarks/lp-precision-design-experiments.md) for selection
and rejection rules. The [roadmap](gpu-lp-precision-roadmap.md) and
[backlog](../../state/backlog.yaml) own order. The
[2026-09-30 review](lp-low-precision-research-2026-09-30.md) remains an unchanged
historical research artifact; this document resolves and extends its proposals.

## GPUP-EXEC implementation update (2026-10-13)

The [bounded executor report](../benchmarks/lp-exact-executor-gpup-exec.md) closes
one R1/R2/X subset under ADR-0035: canonical binary64 bits and integer exact dots
inside a proven exponent window, with cached and uncached vectors. The 108-attempt
study retains 94 verified endpoints and all 27 cache-equivalence pairs. It finds
explicit range refusals and no total-cost improvement over tuned FP64. Full
expansion state, the alternative compact tails and SPEC-0021 methods remain
proposals with their own acceptance obligations. GPUP-STATE is next.

## Implemented foundation and evidence that motivates change

The runtime already includes validated models, pinned HiGHS 1.11.0, an owned
branch-and-bound executive, scheduling, extension/replay infrastructure, and CPU
and CUDA first-order LP methods with independent host certification. The GPU LP
track has matched and tuned FP64 controls, explicit FP32 experiments, exact-scaling
and component products, integer guards/fusion/double-float research, adaptive
rollback/promotion, sessions and host/evidence/setup investigations. C7 portfolios,
C9 SDK and C10 general comparative APIs remain unspecified.

| Observation | Consequence for design |
| --- | --- |
| [GPUP-5B](../benchmarks/lp-exact-components-gpup5b.md): exact/factored scaling and component modes restore 27/36 timing coverage versus 12/36 for ordinary scaled FP32 storage; component cross-products are slower. | Separate operator fidelity from product accuracy and from executor cost. Exactness of simple original coefficients does not survive arbitrary scaling. |
| The [FP64-pipe diagnosis](../benchmarks/lp-fp64-pipe-root-cause.md) finds FP64 recombination, conversions and reduction in the three-component sparse loop. Hardware counters were denied; attribution uses generated instructions and timing. | A three-float input is not evidence of FP32-only arithmetic. Inspect actual instruction paths and amortize conversion/recombination per vector or output. |
| [GPUP-5C](../benchmarks/lp-fp64-pipe-gpup5c.md): integer guards preserve FP64 behavior; double-float is fast at scale but underflows on scheduling LPs. | Preserve guard semantics; design exponent handling before claiming general double-float coverage. The report's 1e-9 table gives 24/36 double-float coverage; its inconsistent 27/36 prose is not used here. |
| [Convergence study](../benchmarks/lp-convergence.md): on irregular-32768, accumulation FP32 takes 114.627 microseconds/proposal versus precision FP64's 127.539, but 40464 proposals do not certify where FP64 certifies after 1600. Tuned FP64 is 34.955 microseconds/proposal. | Compare both accuracy and work with the strong tuned control, not only the slower precision executor. Per-proposal speed is insufficient. |
| On that scoped tuned profile, the device host envelope is 0.0489 of 2.6659 seconds; preparation is 0.4741 and repeated/final certification 0.7856. | Eliminating that entire envelope would yield only about 1.019x total speedup there. Host checks and preparation need separate, measured designs. These figures are not GPU-busy counter measurements. |
| [Sessions](../benchmarks/lp-repeated-solve-throughput.md) reach 26.6x amortized throughput on one small N=32 case; [setup](../benchmarks/lp-fresh-setup.md) and [COPT adapter](../benchmarks/lp-copt-adapter.md) changes do not give general fresh-process gains. | Do not transfer a throughput or loading claim to fresh-solve latency. Retain negative results and large-case timeouts. |

Existing component products do not maintain expansions throughout the algorithm.
[Parts3](../../crates/optimizer-lp/src/research.rs) stores three FP32 components
and an i32 exponent: 16 bytes per value. The
[research kernel](../../cuda/lp_pdhg_research/lp_pdhg_research.cu) splits vector
operands within sparse products and uses FP64 recombination/reduction. The
pair-product mode still returns to FP64 state. Neither has tested a complete
expansion-state solver, nor the proposed compact tail encoding.

## Which components are sensitive, and why

Quantization affects a method through different mechanisms: a persistent change
to the problem data, roundoff in one operation, loss of a small state update,
or an incorrect control decision. Condition numbers and cancellation determine
amplification. An operation's name or nominal precision alone does not.

| Common method | Sensitive components and mathematical reason | Candidate redesign; unavoidable obligation |
| --- | --- | --- |
| Restarted PDHG / PDLP | Ax-b, c-A-transpose-y, gap and restart statistics subtract similar quantities; tiny updates can disappear. A fixed rounded A changes the limiting problem. Step control depends on operator norms. | Anchor original products, solve corrections, compensate state, and bound inexact products. Check the original residual and safe step assumptions. Projection onto a fixed box is nonexpansive; identifying its active face can still be unstable near a boundary. |
| Revised simplex | An ill-conditioned basis amplifies solve errors; reduced-cost and ratio-test signs near zero choose discrete pivots. Degeneracy magnifies decision sensitivity. | Low-precision factorization/pricing can propose work; accurate residual refinement and verified pivot/feasibility tests protect decisions. This project has no owned simplex basis implementation to optimize yet. |
| Primal-dual interior point | KKT solves become difficult as complementarity variables separate in scale; positivity and fraction-to-boundary tests are sensitive. Normal equations can square conditioning. | Low-precision factors as preconditioners, accurate KKT residuals and Krylov correction; preserve positivity and complementarity tests. Consider augmented systems/regularization only with a bias-removal contract. A separate solver design is required. |
| ADMM / operator splitting | Inexact fixed linear solves and accumulated dual updates can set a residual floor; final active-set polishing may be ill-conditioned. | Reuse a low-precision factor with accurate residuals; apply guarded polishing. For LPs, convergence speed and polishing success are unproven and must repay setup. |
| All methods | Large dot products/reductions, cancellation in objective/gap, comparisons at a tolerance, stopping, and final certificate arithmetic. | Use a specified accurate accumulator and stable identities where needed. Arithmetic cannot remove intrinsic ill-conditioning or make an unchecked surrogate certificate valid. |

The residual components in the second column should receive precision according
to an absolute error budget in original model units. Relative error of a nearly
zero residual is not a useful admission test. Expensive accurate arithmetic can
be concentrated in these components; bulk products can be cheaper if their error
is controlled. No general theorem says that all coefficients or all iterations
need one precision.

## Component catalogue

The IDs below are experiment factors, not runtime options. Each row records a
reason to act, a proposed implementation and a result that would stop it.

| ID / component | Motivation and implementation approach | Required evidence / stop condition |
| --- | --- | --- |
| R1 exact compact storage | Two FP32 terms leave a very small integer tail after binary normalization. Store that tail plus an explicit exponent, or retain the original eight-byte bit pattern and decode with integer instructions. See SPEC-0020's proof and layouts. | Exact bit round trips, signed zero/range coverage, transpose identity; count metadata, alignment and decoding. Reject a bandwidth claim if measured total traffic rises. |
| R2 scaled accurate arithmetic | Unscaled FP32 pairs underflow; exact input storage alone does not preserve operations. Use normalized expansion arithmetic with symbolic exponents, error-free transforms where valid, and explicit rounding or error bounds. | Product/reduction/division/comparison contracts against an independent integer/rational oracle. Reject silent flush-to-zero, exponent clipping or unbounded discarded terms. |
| X lean executor | The measured implementation splits per nonzero and repeatedly enters the FP64 pipe. Cache vector decompositions once per iterate, use a canonical matrix with a transpose map, renormalize per output, and carry proven integer guards/fusion into a separate image. | Same-arithmetic control, static instruction audit, register/spill/traffic accounting and sanitizer gates. Reject a faster inner loop that loses total time to preparation. |
| S persistent accurate state | Small updates can vanish even with an exact matrix. Keep primal/dual/master/average/restart state and control scalars in the specified arithmetic; compare compensation/error feedback with a full expansion. | Complete operation inventory, checkpoint/replay and range tests. A FP32 working vector with occasional FP64 correction is the existing control, not this experiment. |
| N stable numerical formulas | Cancellation or premature division can create avoidable error in proximal maps, norms and gap calculations. Use piecewise support-function proximal maps, scaled norms and residual-aware gap identities. | Exact-real algebraic equivalence plus rounded boundary/adversarial tests. A numerically different recurrence has its own identity; never assert old bitwise equivalence without evidence. |
| F outer LP refinement | GPUP-6 audits repair windows, not the residual of a complete correction LP. Scale the original primal/dual residual into an inner solve, then update accurate masters. | Correct general ranged-row transformation, error-budgeted progress, original final certificate, charged unsuccessful corrections. Reject noncontracting cases without silently increasing budgets. |
| A anchored products | A rounded matrix introduces E times the full iterate. Use accurate anchor products and an approximate operator on directly maintained small changes, making the bias E times the change. | Both operator orientations, maintained deltas, full refresh cost and measured residual contraction. Refresh when drift/error limits require it; cancellation from subtracting rounded iterates defeats the design. |
| Q selective precision | Most row/block activities may fit a small error budget while a few dominate error. Bound tail activity and promote those blocks or retain outlier values exactly. | Conservative row/transpose bounds, shared operator identity, safe norms and memory admission. Reject dense exception tables or bound computation that costs more than accurate products. |
| H assessment scheduling | Failed FP32 work can spend more on repeated host assessments than on kernels. Use cheap indicators to schedule expensive assessments under a new method contract. | Paired same-proposal schedule controls, latency/coverage and delayed-success accounting. Original final certification and required recovery remain charged and authoritative. |
| P scaling / preconditioning / polishing | Fewer iterations may matter more than faster products. Test precision-aware scaling or low-precision preconditioners; use a tentative active face to propose accurate correction work. | Separate conditioning from representation bias; validate full-model rows, rank and degeneracy. Active-set errors are reversible; reject if factors/setup/expansion of the working set erase savings. |
| T Tensor Core or integer dot products | Dense blocks may amortize emulation/recombination per output. Use actual dense tiles, correction factors or independent right-hand sides; sparse integer limbs need bounded carries. | Actual sm_120 shapes/accumulator behavior, occupancy/padding/packing and overflow proofs. A sparse single-vector product is not dense GEMM, and successive iterates are not independent columns. |
| Z stochastic rounding | Unbiased local rounding may reduce stagnation in some recurrences. Retain seeded generator/counter state and compare with deterministic compensation. | A sampled matrix still has fixed model bias. Require repeated seeds, variance, canonical transpose and a separate budget; defer until deterministic sources of error are understood. |

R1/R2/X/S address representation and arithmetic; F/A/Q address error propagation;
N/H/P address sensitive formulas and work. They can be combined. In particular,
accurate expansion masters plus low-precision anchored correction products are
compatible: master accuracy and inner product accuracy serve different purposes.
Their combined memory and control overhead may still lose to tuned FP64.

## Compact representations: what the bytes mean

For finite nonzero binary64 x, normalize x = 2^e m with 0.5 <= abs(m) < 1.
With round-to-nearest-even FP32 h and l, SPEC-0020 proves

~~~text
h = RN32(m); l = RN32(m-h)
m = h + l + q * 2^-53, where integer q is in [-8,8].
~~~

The exponent spans -1073 through 1024. Thus a small tail is sufficient to encode
an original binary64 value exactly, including its subnormal range. An **unscaled**
FP16 tail is not sufficient: these tails can be much smaller than 2^-24. Store q
in FP16/FP8/INT8 with its implicit 2^-53 weight, or use a BF16 tail whose exponent
range covers this normalized residual. This is a mathematical storage statement,
not an assertion that any hardware FP8 operation computes the complete value.

| Candidate layout | Bytes/value before indices, tags, exceptions or padding | Meaning |
| --- | --- | --- |
| Original binary64 bits, integer decoding | 8 | Full original precision/range; no native FP64 instruction is required merely to load its bits. |
| Two FP32 components, unscaled | 8 | Roughly 48 significant bits under suitable normalization; not an exact general binary64 encoding and not its exponent range. |
| Existing three FP32 + i32 exponent | 16 | Current Parts3 ABI, not a 12-byte stored matrix. |
| Two FP32 + scaled FP16 tail + i16 exponent | 12 | Exact finite-input codec under this normalization; an i32 exponent instead normally restores 16-byte struct size. |
| Two FP32 + BF16 tail + i16 exponent | 12 | BF16 may represent the raw normalized tail; it is not automatically a convenient accumulator. |
| Two FP32 + INT8 or scaled FP8 tail + i16 exponent, separate arrays | 11 | Same exact tail information; a conventional aligned struct is normally 12 bytes. |
| One FP32 + three weighted FP16 chunks + i16 exponent | 12 | A fixed unsigned significand-chunk encoding has enough capacity for 53 bits; sign/weights/canonical mapping must be specified. It is a different codec and arithmetic design. |
| Five weighted FP16 chunks + i16 exponent | 12 | 55 significand bits of chunk capacity; may suit FP16 product hardware, but expands the number of cross-products. Capacity is not arithmetic accuracy. |
| Shared block exponent with exact exceptions | Data-dependent | Count headers, padding, exception maps and alignment. Full-range arbitrary blocks may fall back to individual exponents. |

Exact storage of an already-rounded preconditioned matrix preserves the rounded
matrix, not the original operator. Keep original coefficients with exact/symbolic
scaling, or include earlier scaling error in the product budget. A compact codec
cannot restore information lost before it receives its input.

A tail needs 17 possible signed values, hence at least five bits if independently
coded; standard FP8 wastes some codes but could simplify a hardware path. Packed
five-bit tails complicate access. Arbitrary binary64 inputs cannot all be stored
losslessly in a fixed-width format below eight bytes per value. Distributional
compression and shared exponents require an explicit admission/exception design.
Extra stored bytes and compiler register spills are different costs. An FP16 or
INT8 field can save global-memory bytes while still consuming a full register or
conversion temporary. Measure register allocation, local-memory spills and
occupancy alongside packed bytes; compact storage does not establish compact
execution state.

Three components of an arbitrary intermediate expansion need not satisfy this
five-bit tail bound. A product of two 53-bit significands may require 106 bits
before rounding: storage precision is not an arithmetic guarantee.

The [CPU artifact](data/lp-precision-design-examples.json) records examples,
layout sizes, exact identities and counterexamples. Its
[validator](../../tools/check_lp_precision_design.py) uses rational arithmetic;
the finite sample is supporting evidence, not the proof or GPU acceptance.

## Low-level architecture and sensitive formulas

Separate cold matrix encoding from per-iteration state arithmetic. Use canonical
coefficient identifiers for CSR and its transpose; independently requantizing a
second copy can destroy adjoint consistency. Keep exponent handling symbolic until
it is safe to materialize a value. For example, reconstructing 2^1024 as FP64 or
FP32 before multiplying a normalized mantissa overflows unnecessarily.

The operator path should decode each reused vector once, apply all admitted
component products with an explicit reduction order, and normalize at the output.
No native FP64 inner-loop claim is accepted from source types alone: inspect
loads, conversions, divisions, guards and generated code. Recomputing coefficients
or throwing away low components on every iteration defeats the storage design.
Small accurate control operations can remain host FP64 in one separately named
hybrid candidate; an entirely expansion-based inner controller must include them
in its primitive audit.

The support-function proximal map for an interval admits the exact-real identity

~~~text
prox_(sigma * support_[l,u])(z) =
    z - sigma*l   if z < sigma*l,
    0            if sigma*l <= z <= sigma*u,
    z - sigma*u  if z > sigma*u.
~~~

This avoids forming z/sigma and subtracting nearly equal values in the interior.
Infinite bounds and overflowing scaled endpoints need symbolic branches; changing
rounding changes a trajectory even though the real formulas agree. Likewise, for
standard-form LP residuals rp=b-Ax and rd=c-A^T y-s,

~~~text
c^T x - b^T y = x^T s + x^T rd - y^T rp.
~~~

Using only complementarity x^T s silently drops residual terms. These formulas
are proposed improvements to iterates/indicators, not replacements for the
conservative original-model certifier. Norms need scaled accumulation, and
objective cancellation still needs an absolute error allowance.

## Algorithm redesign and authority

SPEC-0021 transforms ranged rows to equalities with explicit activity variables
before deriving a correction LP. Merely replacing c with c-A^T y for inequality
rows can change the minimizer: on 0 <= x <= 1, minimizing x has minimizer 0,
whereas using y=2 produces cost -x and minimizer 1. The activity variable carries
the compensating cost and makes the transformed problem equivalent.

Approximate inner solves need quantitative residual/optimality budgets. LP
refinement literature often assumes a bounded-accuracy LP oracle; this project's
first-order solver has not yet established that assumption. Inexact PDHG theorems
also impose conditions on errors and step sizes. Neither is a theorem for arbitrary
FP8 iterations. Finite-budget experiments must include failure to contract.

It is feasible in principle to keep low-precision expansions through every inner
iteration and never reconstruct a native FP64 number there. It is also feasible
to combine that with refinement and selective low-precision products. It is not
sound to infer original-model feasibility or a bound solely from a rounded
surrogate's stopping test. Exact-encoding products with rigorous error bounds
could check the original model without native FP64, but replacing the currently
accepted independent host certification is a different, unapproved project.

## Hardware and alternative-solver admission

SM120 is not SM100. The [CUTLASS architecture documentation](https://docs.nvidia.com/cutlass/latest/media/docs/cpp/blackwell_functionality.html)
describes distinct instruction families and supported tile/layout combinations.
Record the actual GPU, toolkit, generated instruction family and accumulator
semantics before admission. Dense low-precision peak throughput predicts neither
sparse SpMV throughput nor end-to-end solver latency.

[NVIDIA's cuBLAS emulation documentation](https://docs.nvidia.com/cuda/cublas/index.html#floating-point-emulation)
is a candidate implementation reference, not a dependency approved here. Record
its version, architecture support, selected mantissa/algorithm and fallback path
if a future study uses it; dynamic emulation may fall back to native arithmetic.
No library claim establishes this project's range or reproducibility contract.
Direct integer limbs need overflow/carry bounds for each dot length and each
recombination. Sequential iterates cannot be batched as independent right-hand
sides. Actual independent solves belong to the separate throughput contract.

Simplex, interior-point and ADMM routes are conditional research branches. The
first pilot must be CPU mathematical validation of an admitted linear-system or
active-face subproblem, followed by setup-inclusive comparison with the existing
solver. A new owned solver, external library or unsafe boundary needs its own
accepted specification/ADR. These branches do not block a good PDHG recipe.

## Primary numerical references and applicability

- [Ogita, Rump and Oishi, accurate sums and dot products](https://www.tuhh.de/ti3/paper/rump/OgRuOi04a.pdf): error-free transforms and accurate accumulation; implement their stated rounding/range assumptions.
- [Joldes et al., expansion arithmetic](https://perso.ens-lyon.fr/jean-michel.muller/07118139.pdf) and [CAMPARY](https://homepages.laas.fr/mmjoldes/campary/): algorithms and error analysis for expansion operations; not a proof that arbitrary mixed-format tuples obey IEEE binary64 semantics.
- [Gleixner, Steffy and Wolter, LP iterative refinement](https://optimization-online.org/wp-content/uploads/2015/06/4948.pdf): scaled primal/dual correction with a suitably accurate oracle; applicability to our first-order oracle must be established.
- [Rasch and Chambolle, inexact primal-dual algorithms](https://arxiv.org/abs/1803.10576): convergence with controlled inexactness; errors require a contract, not an unspecified quantizer.
- [PDLP](https://arxiv.org/abs/2501.07018): a practical first-order LP reference for scaling, restarts and control; our implementation/evidence remains separately identified.
- [Cornelis and Vanroose, mixed-precision interior point](https://arxiv.org/abs/2105.01333): a conditional alternative for linear-system work, not an already implemented backend.
- [OSQP solver documentation](https://osqp.org/docs/solver/index.html): factor reuse and polishing as design references; no general LP speed claim follows.
- [NVIDIA floating-point guide](https://docs.nvidia.com/cuda/floating-point/index.html): FMA, rounding and execution details that must be checked in the generated kernels.

Sources were reviewed on 2026-10-12. New derivations, engineering choices and
admission gates above are project proposals. They do not inherit correctness or
performance guarantees simply by citing these sources.
