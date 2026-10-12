# Low-precision LP performance research at 1e-9

Status: research analysis and proposed experiments; no accepted numerical behavior
or supported preset. Saved at the user's request on 2026-09-30.
Owner: numerical backend and experiment tooling.
Repository reviewed: `5a37bb460c52f4c50e0d0861a1265c8ce8ada9c8`, following
GPUP-CONVERGENCE. Historical measurements retain their own recorded revisions.
Implementation status: none of the new adaptations in this note is implemented by
this documentation change. Existing techniques are identified separately below.

This note preserves the analysis and proposals from the 2026-09-30 discussion of
why low precision has not consistently beaten FP64 at the project's original-model
1e-9 tolerances. It records mechanisms, equations, hardware constraints, evidence,
failure criteria and a proposed experimental sequence for later sessions.

The strongest numerical proposal is an outer LP refinement method: compute
accurate original-model residuals, solve scaled corrections cheaply, and update
accurate master iterates. Combine it with a lean precision executor and explicit
range control. This gives FP16 and FP8 a useful role without requiring every
operation or working value to carry the final solution's accuracy. It is a
hypothesis for this solver, not a demonstrated performance result.

Start with the [roadmap](gpu-lp-precision-roadmap.md),
[candidate register](lp-precision-candidates.md),
[latest convergence study](../benchmarks/lp-convergence.md),
[known failures](../../state/known-failures.md) and
[backlog](../../state/backlog.yaml). GPUP-7's bounded quantization/FP8 interface and
resource contract remains the next implementation prerequisite. This note does
not reorder that backlog or accept outer refinement, polishing, an assessment
policy, a new library boundary, or a new GPU allowance.

## Evidence that constrains the proposals

Keep four categories separate: repository measurements, established external
techniques, algebraic deductions, and unmeasured project adaptations. A method can
have a sound numerical motivation and still lose on total certified latency.

| Observation | Evidence and scope | Consequence for further work |
| --- | --- | --- |
| Matrix conversion changes the problem seen by iterations. | The [rounding analysis](../benchmarks/lp-fp32-rounding-analysis.md) finds all 166292 original coefficients in the original development corpus exactly representable in FP32, but only 18 remain exact after its non-dyadic scaling and FP32 conversion. | Control the represented-operator error; changing accumulation alone cannot recover missing coefficients. This exactness result does not cover arbitrary LPs or the later mixed family. |
| Some represented solutions violate the original model. | Irregular-2048 row 805 exceeds its original allowance by 34.2 times while satisfying the implied represented-operator allowance; dense_block-1024 row 798 exceeds its original allowance by 15.8 times. | These witnesses establish material operator bias on those cases. Other failed endpoints also have large represented residuals; not every failure is a rounding floor. |
| Cheaper FP32 proposals can produce much more unsuccessful work. | In the [convergence study](../benchmarks/lp-convergence.md), irregular-32768's 2000-allowance profiles record 114.627 microseconds per FP32 proposal versus 127.539 for precision FP64. The separate full profiles use 40464 FP32 proposals without certification versus 1600 for precision FP64. | The 10.1 percent scoped saving does not establish a certified speedup. The full FP32 endpoint records a product-loss guard; representation, accumulation and restart dynamics were not individually isolated. |
| Executor choice is material. | Tuned FP64 takes 34.955 microseconds per proposal in the same scoped profile comparison, much less than the generic precision executor. | Compare both an algorithmically matched FP64 control and the best existing tuned FP64 endpoint. These host envelopes are not GPU kernel busy times. |
| Scalar component recombination reintroduces expensive FP64 work. | The [FP64-pipe diagnosis](../benchmarks/lp-fp64-pipe-root-cause.md) counts about 140 FP64-pipe instructions per nonzero in the three-component cross-product kernel, mostly compensation, plus conversions. No project kernel there uses Tensor Cores. | Lower-width components do not accelerate a loop dominated by FP64 recombination. Hardware counters were denied; attribution rests on instruction inspection and timing. |
| Integer guards and fusion already work in their measured scopes. | [GPUP-5C](../benchmarks/lp-fp64-pipe-gpup5c.md) preserves endpoint bits for its integer-guard and fused FP64 modes. Integer guards reduce dense_block-65536 equal-work update cost from 230.8 to 111.8 microseconds; fusion reduces original-corpus update medians from 21.2 to 12.1 microseconds. | Reuse the demonstrated techniques, but do not present them as new inventions or assume the fused schedule wins at every size. |
| Double-float is a credible arithmetic lead with range failures. | GPUP-5C measures 100.3 microseconds per update for double-float on dense_block-65536 versus 111.8 for integer-guarded FP64. Scheduling cases lose coverage on nonzero-to-zero product guards. | Investigate range scaling and exceptions before abandoning FP32-pair arithmetic. A faster update is not a certified-solve win. |
| Existing correction and recovery are different from outer LP refinement. | [GPUP-5](../benchmarks/lp-fp32-rounding-analysis.md) replaces one final update. [GPUP-6](../benchmarks/lp-adaptive-gpup6.md) audits a window's final update, adopts a reference endpoint on a pass, and rolls back/replays on a failure. | Neither implements the residual-driven correction LP proposed here. Sampled update agreement does not prove final convergence. |
| Adaptive recovery restores available coverage at substantial cost. | Irregular-32768 fresh certified medians are 2.6467 seconds for tuned FP64, 3.1568 for precision FP64, 3.7328 for adaptive FP64, 3.9947 for sticky recovery and 4.9922 for gradual demotion. Sticky promotion occurs at logical step 192; gradual recovery adds rejected/replayed proposals and probes. | Adding more audits or promotion alone repeats an already expensive strategy. Preserve these outcomes as controls. |
| Successful solves can be dominated by host work. | One full tuned irregular-32768 profile records 2.6659 seconds process time, 0.0489 device envelope, 0.4741 preparation and 0.7856 original-model certification/assessments. | Removing the entire device envelope with other work unchanged gives only 2.6659 / (2.6659 - 0.0489), approximately 1.019 times. This is a scoped Amdahl calculation, not a universal GPU limit. |
| Unsuccessful work also amplifies host checks. | The full accumulation-FP32 profile spends 15.0272 seconds in certification/assessments within a 25.5201-second process. | Reduce unsuccessful iterations and consider a separately specified assessment schedule, while retaining full acceptance checks. |

The latest study retains 176 attempts, verifies 174 endpoints and certifies
87/104 primary timings. Two dense-65536 accumulation-FP32 timings have no endpoint;
all mixed-65536 primary samples remain uncertified. Verification of an unsuccessful
endpoint is not successful certification. No method in this note fills those gaps.

The root-cause note's standalone microbenchmarks are explicitly labeled
**uncharged diagnostics**, with later charged GPUP-5C acceptance measurements
reported separately. Do not relabel those historical experiments or pool the two
sets. The note estimates only about 1.7-2.6 times ideal sparse FP32 kernel gain at
scale because bytes and launches limit the workload; the nominal 64-times FP32 to
FP64 arithmetic ratio is not a solver-speed prediction.

There is a historical reporting inconsistency to preserve visibly: GPUP-5C's
finding prose says double-float certifies 27/36 at 1e-9, while its explicit coverage
table says **24/36**, consistent with the additional scheduling failures described
beneath it. Use the table when summarizing that report; recheck primary artifacts
before making any formal correction. This note does not rewrite archived evidence.

## Hardware interpretation and available bypasses

The relevant target is RTX Blackwell GB202, `sm_120`, rather than a generic
Blackwell family label. NVIDIA's [RTX Blackwell whitepaper](https://images.nvidia.com/aem-dam/Solutions/geforce/blackwell/nvidia-rtx-blackwell-gpu-architecture.pdf)
reports two FP64 units per SM and FP64 peak throughput at 1/64 of FP32. The
repository's instruction evidence explains why double comparisons, conversions
and compensated recombination can dominate ostensibly low-precision kernels.

A useful kernel goal is to remove per-nonzero FP64 work from the bulk loop and
charge any accurate reconstruction per output, per refresh or per exceptional
block. That is a design target, not a proof that all remaining work will be fast.
Sparse gathers, indices, extra components, launch floors and vector updates remain.

SM120 uses warp-level `mma.sync` paths for relevant narrow matrix operations.
SM100 `tcgen05`/Tensor Memory examples cannot be transplanted unchanged.
[PTX MMA documentation](https://docs.nvidia.com/cuda/parallel-thread-execution/#warp-level-matrix-instructions-mma)
and [CUTLASS SM120 functionality](https://github.com/NVIDIA/cutlass/blob/main/media/docs/cpp/blackwell_functionality.md#blackwell-sm120-gemms)
identify the instruction and layout restrictions; CUTLASS documents TN layout and
no multicast for its SM120 path. FP16/FP8 inputs can use FP32 accumulation, but
Tensor-Core accumulation order, rounding and subnormal behavior must not be
assumed identical to a scalar FP32 reduction. Check numerical error and
same-device reproducibility under the explicit execution identity.

The supported library and hardware claims below were reviewed on 2026-09-30.
Recheck versions before provisioning or accepting an implementation; no toolkit,
library, instruction or boundary change is authorized by recording the ideas.

## Proposal 1 Outer LP refinement and anchored products

### Correction problem

The established [LP iterative-refinement method](https://optimization-online.org/wp-content/uploads/2015/06/4948.pdf)
transforms an LP into successive correction problems using accurate residuals and
scaling. For the illustrative standard form, write the transformation as follows:

```text
Original: minimize c^T x, subject to A x = b and x >= l.
Accurate master state: x0, y0.
rp = b - A x0
rd = c - A^T y0

Correction: minimize (Delta_d rd)^T d,
            subject to A d = Delta_p rp,
                       d >= Delta_p (l - x0).

After an approximate primal/dual correction (d, yhat):
x_new = x0 + d / Delta_p
y_new = y0 + yhat / Delta_d
```

Positive scales preserve the transformation; scales greater than one magnify
errors before the correction solve. The published convergence argument requires bounded primal, dual and
complementarity errors from its approximate LP oracle. It does not establish that
an arbitrary quantized PDHG implementation supplies that oracle. General row and
upper bounds need explicit transformed semantics.

**Proposed project adaptation:** compute residual data from the original FP64
model, use separate power-of-two `Delta_p` and `Delta_d`, solve most of the
correction in FP32 initially, and retain FP64 master updates. Test FP16/FP8 only
after measuring correction quality. Scale choice, correction budgets and progress
rules need a new bounded contract; none is a hidden default here.

This changes the role of low precision: an inner solver should produce a useful
correction at modest accuracy. Accurate outer updates and refreshed original-model
residuals carry the improvement to the final acceptance conditions. Do not assume
that using high-precision residuals alone ensures contraction.

### Anchored operator evaluation

The following algebra explains the proposed implementation mechanism. Let
`Ahat = A + E`, use an accurate anchor product `p0 = A x0`, and set
`delta = x - x0`. Evaluate the moving part cheaply:

```text
q = p0 + Ahat delta
q - A x = E delta                         (exact algebra)
```

Ordinary application of `Ahat` to the whole state has error `E x`; anchoring changes
that term to `E delta`. Apply the corresponding construction to the dual product
using its own accurate anchor `A^T y0`. In finite precision, add the anchor-product
error, low-product/reduction error and master/update error. Computing `delta` by
subtracting two nearly equal low-precision states can lose the benefit; maintain a
correction representation directly where practical.

A second algebraic view makes the contraction requirement concrete. If the inner
primal correction satisfies `Ahat d = Delta_p rp + eta`, then before residual and
update rounding:

```text
b - A (x0 + d / Delta_p) = (E d - eta) / Delta_p
abs(rp_new) <= (abs(E) abs(d) + abs(eta)) / Delta_p
```

This does not guarantee a small `d`, small `eta`, dual progress or complementarity.
It identifies quantities that a proposed inner solve must control. In particular,
near-singular geometry can require large motion even when the current residual is
small. Repeatedly increasing `Delta_p` does not by itself solve that difficulty.

### Proposed progress and recovery policy

At outer boundaries, recompute the existing original-model primal, dual and gap
conditions. A candidate policy can normalize those conditions into a fixed merit
and require a prespecified contraction factor `q < 1`, or an accepted final
certificate. The merit, normalization, contraction factor and observation schedule
must be frozen before trials. Individual metrics need not all decrease at each
step; no particular merit or factor is selected here. An unavailable conservative
dual bound cannot be treated as zero gap.

When the policy rejects progress, charge the attempted correction, then raise
precision, revise a declared scaling choice, refresh the anchor or terminate at
the budget. This safeguard is not a convergence theorem. Preserve cancellation,
full checkpoint semantics and all physical work, including failed corrections.

Failure and rejection cases include:

- Quantization changes rank or the important active face; low-precision correction
  residuals are small while original-model dual or gap progress stalls.
- Shifted inactive bounds become huge after scaling and overflow FP16/FP8;
  clipping or treating a large finite bound as infinity would change the problem.
- Tiny corrections disappear in master updates, projections, extrapolation,
  averages or restart anchors.
- Corrections remain large, reanchoring becomes frequent, or accurate residual work
  costs as much as the FP64 method.
- Total certified latency or coverage is worse after charging preparation,
  transfers, recovery, outer work and certification.

## Proposal 2 A lean executor for the active precision path

Integer-pipe guards and launch fusion are **implemented GPUP-5C techniques**. The
new work proposed here is their integration into a purpose-built precision
executor, followed by comparison against current adaptive and fixed controls.
The [adaptive host-cost repair](../benchmarks/lp-adaptive-host-cost.md) explicitly
left kernels unchanged and binds the precision image rather than the tuned image.
The [precision kernel](../../cuda/lp_pdhg_precision/lp_pdhg_precision.cu) still
contains generic casts and double-valued checks; the integer guard helpers are in
the separate [research image](../../cuda/lp_pdhg_research/lp_pdhg_research.cu).

Specialize storage, products, accumulation and update paths. Split or convert a
vector once per update rather than once per nonzero. Keep buffers resident, collect
range flags with cheap integer operations, and perform only the accurate boundary
work required by the declared numerical method. Inspect SASS for residual double
arithmetic, comparisons and conversions rather than inferring execution precision
from buffer types or API names.

Fusion is a measured tradeoff: GPUP-5C's fused update warp serializes vector work
at scale. Compare separate and fused schedules with numerical policy fixed;
never assume a two-launch schedule wins universally. Graphs or persistent kernels
are secondary possibilities requiring explicit driver-boundary wrappers,
cancellation and resource limits. Historical microbenchmarks are not authorization
or sufficient evidence for either implementation.

Acceptance should distinguish equal-work execution savings, algorithmically
matched FP64 comparisons and total certified latency versus tuned FP64. Reduced
launch cost does not repair matrix bias or extra iterations.

## Proposal 3 Scaled double-float with range exceptions

FP32 pairs provide roughly 48 significant bits under suitable range assumptions,
not the full FP64 exponent range or a universal FP64 error bound. The existing
pair path's observed nonzero-product underflow is the concrete target.

```text
v = 2^e (v_hi + v_lo), with FP32 components and explicit exponent metadata.
```

Start with per-vector power-of-two scaling. If one exponent cannot cover the
range, investigate blocks or exponent buckets with a high-precision exception
path. Fuse vector normalization with updates when it saves work, and keep exponent
handling outside the per-nonzero product loop where possible. Scaling must preserve
small significant terms rather than disable the loss guard.

Maintain compatible matrix, vector and transpose representations, and specify
range handling for products, partial sums, final reconstruction and cancellation.
Large exponent differences can erase a term during alignment even if each stored
operand is nonzero; preserving operands alone is insufficient. High-precision
exceptions must receive undamaged operands.

The pair format uses about eight bytes per value before metadata, so its expected
benefit is arithmetic and guard cost rather than automatic bandwidth reduction.
Measure scheduling decay, extreme exponents, subnormals, near-cancelling sums and
the later mixed-coefficient family. Reject the design if range metadata,
normalization, extra launches or widespread exceptions erase the gains. This work
can supply reusable range machinery for FP16/FP8 even if pairs do not win overall.

## Proposal 4 Select precision by activity-error budgets

Retain one canonical quantized matrix and explicit coefficient-error information.
Share quantized values, promoted blocks and exceptions between `A` and `A^T`.
Independent rowwise and columnwise quantization can create incompatible operators,
including when a hardware block-scaling format encourages different layouts.

For an anchored correction, a proposed inexpensive bound is:

```text
abs(E delta)_i <= sum_B norm1(E_iB) * normInf(delta_B)
```

Precompute coefficient-error summaries; update block vector bounds during vector
work. Use corresponding column summaries for transpose products. Those inequalities
can guide which rows, blocks or outliers need more precision. A fixed conservative
bound on block norms may save scans, but may also be too pessimistic to be useful.

The budget must be expressed consistently with original units and current
progress. Persistent nonzero approximation errors can leave an accuracy floor;
tighten budgets with progress or shrinking corrections rather than infer arbitrary
convergence from a fixed error bound. If coefficient-error summaries or block
norms control arithmetic admission, construct them with conservative rounding or
validated enclosures: an ordinary floating-point sum is not automatically an
upper bound. Add allowances for quantization, product/reduction rounding, anchor
error, scaling and state updates. The inequality bounds operator error; it does
not by itself bound final feasibility, certified gap or accumulated iteration
error. Host certification stays authoritative.

Group ordinary and exceptional work to avoid divergence at every nonzero. Lower
precision on most values with a small accurate residual/exception path could beat
blanket component expansion. However, an operator tail that touches nearly every
nonzero every iteration recreates GPUP-5B's traffic and recombination problem.
Dynamic representation changes also need step-size/norm validation and checkpoint
semantics under SPEC-0012.

Failure criteria: excessive exceptions, loose bounds, expensive norm scans,
metadata larger than storage savings, expensive sparse tails, orientation mismatch,
or original-model progress that fails despite locally acceptable arithmetic.

## Proposal 5 Active-face discovery and accurate polishing

Use low-precision iterations to propose likely binding constraints and variable
bounds. Construct a reduced primal-dual correction or basis system, solve for a
more accurate candidate, then check every original constraint, reduced cost and
certified gap. Incorrect active sets cause rejection or an explicitly specified
expansion/crossover; guessed inactive rows never acquire pruning authority.

This is a different algorithmic use of low precision: discover useful structure
before asking for the final digits. Near-degeneracy can make active-set discovery
unstable, and the reduced system can be singular, ill-conditioned or nearly as
large as the original problem. Include rank checks, fill/memory limits, wrong-face
recovery and full-cost comparisons. Preserve finite/infinite-bound and objective
sense semantics.

A larger extension is low-precision block factorization or preconditioning,
Krylov correction solves and accurate residual/master updates. FP8 may first be
useful in an approximate inverse or preconditioner: errors weaken the direction,
while accurate residuals continue to define the target. Do not allow a compressed
preconditioner to become the authoritative model.

[Haidar et al.](https://www.netlib.org/utk/people/JackDongarra/PAPERS/mixed-rs-2020.pdf)
demonstrate mixed-precision Tensor-Core factorization and iterative refinement for
linear systems, including GMRES-based correction and range management. Their
results depend on conditioning and correction quality. They do not establish a
performance or convergence guarantee for this project's LP KKT systems or sparse
single-vector workload.

Investigate block-Jacobi or problem-structured correction preconditioners only
when setup and application can pay for themselves. Assess them by certified work
times per-work cost, not solely by preservation of coefficient representability.
Normal-equation constructions may worsen conditioning; dense factors may exceed
memory. A regularized inner problem is another hypothesis, but an outer method
must remove its bias before original-model acceptance. No silent objective
regularization is permitted.

## Proposal 6 Tensor Core and integer emulation on suitable work

Current [cuBLAS floating-point emulation documentation](https://docs.nvidia.com/cuda/cublas/#floating-point-emulation)
lists FP64 fixed-point emulation on compute capabilities including 12.x from
CUDA 13.0 Update 2. Dynamic mantissa control targets native-FP64 accuracy and may
fall back; fixed control trades accuracy for cost. Its BF16x9 support table lists
10.0/10.3, not 12.x. Explicit workspace matters for cost and reproducibility;
record actual execution and fallback. These are library capabilities, not a
sparse-LP speed result or permission to add a runtime dependency.

This deserves a separate comparator from GPUP-5B's scalar cross-products. Fast
integer matrix products can amortize reconstruction over outputs instead of
performing FP64 compensation repeatedly per nonzero. [Ozaki-II](https://arxiv.org/abs/2504.08009)
uses an integer modular construction with the Chinese Remainder Theorem and
reports GEMM emulation experiments. It offers a different design from ordinary
quadratic slice cross-products; its GEMM results do not demonstrate sparse GEMV
speed or original-model LP convergence.

Candidate workloads are naturally dense subblocks, reduced-system factorizations,
or true independent vectors sharing a matrix. Preserve all irregular tails in
SIMT kernels when exploring hybrid execution. First measure block occupancy,
common-column structure, packing, padding, index bytes, metadata, scale application,
outer reductions and preparation on CPU. The corpus's average of 18-33 nonzeros
per row does not by itself imply suitable dense tiles.

A more speculative single-solve idea is to put independent expansion components
of the same vector into matrix-multiply columns, allowing multiple useful partial
products per tile. This adds expansion and reconstruction work and may still leave
most lanes empty. It needs an operation/byte model before a GPU prototype; no
performance benefit or novelty is claimed.

True multiple-right-hand-side work may arise from independent correction
directions or compatible LPs sharing `A`. Future MILP node relaxations could supply
such batches while keeping separate bounds, projections, stopping and host
certification. Consecutive dependent PDHG iterations cannot simply become GEMM
columns. Node batching is a separate throughput/search contract; a batch's
amortized time never substitutes for fresh single-solve latency. Structured 2:4
Tensor-Core sparsity does not authorize pruning arbitrary LP coefficients.

A high-risk sparse alternative is block-scaled integer limbs and INT32 partial
sums, potentially using [PTX dp4a](https://docs.nvidia.com/cuda/parallel-thread-execution/#integer-arithmetic-instructions-dp4a).
Prove accumulator bounds and prevent overflow; quantify reconstruction, exponent,
limb and gather costs. Integer-heavy coefficient structure might help, but decision
vectors are not generally integers. Do not infer suitability merely from integer
model coefficients, or claim a measured win for this proposal.

## Supporting mechanisms and ideas to avoid repeating

Reliable residual refresh, accurate master states and retained update residuals
can support the correction design. A compensated high/low state may keep small
updates from disappearing. Refresh triggers based on progress or error estimates
are hypotheses requiring explicit limits and replay behavior; importing a Krylov
reliable-update policy unchanged into projected LP iterations is unjustified.

Stochastic rounding may reduce systematic accumulation or update effects, but a
single stochastic matrix conversion still freezes one perturbed operator.
Resampling requires consistent transpose values, seeds and rollback semantics.
Neither stochastic rounding nor compensated state alone repairs matrix bias.

Exact power-of-two scaling is a valuable matched control because it preserved the
original development coefficients' FP32 representability. GPUP-5B already tested
it; changed conditioning, transformed bounds/objectives and non-FP32-exact mixed
models remain relevant. Do not present scaling alone as a newly demonstrated
solution to all low-precision failures.

Do not repeat blanket component splitting with per-nonzero FP64 recombination,
more iterations on the same biased operator, or more frequent full reference
audits as if their costs had not been measured. Wider-exponent formats address
range but do not automatically provide enough significand accuracy. Tolerance
relaxation was studied under separate explicit tiers and does not meet this
request's unchanged 1e-9 goal.

## Host assessments and total-cost limits

The Amdahl calculation above means a large solver improvement on that successful
profile requires fewer iterations, cheaper preparation/controller work, or fewer
unproductive original-model assessments in addition to faster arithmetic.
Repeated-solve context reuse and the primary-context experiment already have
separate reports; neither establishes a new fresh-solve arithmetic win.

A proposed assessment policy could use cheap progress indicators to schedule
expensive host assessments and perform full checks at outer refinement boundaries.
Device indicators would have scheduling authority only. Every accepted candidate
or bound still needs the existing original-model validation/certification. Sparse
assessment schedules may delay detection of success or failure; a represented
residual can also be misleading. Specify those effects and charge all work.

This is a new assessment-policy proposal, not an instruction to bypass existing
mandatory audits. Until a separate contract accepts a change, existing audit,
rollback and publication rules remain in force. Cancellation and resource limits
must remain responsive between assessment points.

## Proposed experiment sequence and stop criteria

The sequence below is research advice to inform contract design, not a new
`next_ready_task` or frozen benchmark grid. Execute one accepted bounded slice at
a time. Executor repair and outer refinement can be separate ablations, so a
hardware improvement does not conceal a numerical regression.

| Stage | Work and controls | Advance only if |
| --- | --- | --- |
| CPU feasibility | Analyze archived witnesses; distinguish represented and original residuals; estimate correction scales, operator-tail bounds, exponent ranges and tile occupancy. Retain original and exact-scaling controls. | The proposed representation preserves necessary data and has a plausible cost/error advantage on more than an easy exact-coefficient family. |
| Executor and range repair | Compare lean FP32 execution and scaled double-float with unchanged numerical policies, matched FP64 and tuned FP64. Test range exceptions before broad timing. | Required correctness gates pass, observed range failures are handled explicitly, and equal-work savings survive preparation and exception costs. |
| FP32 outer refinement | Compare ordinary versus anchored/scaled correction work; keep matrix and state precision choices explicit. Freeze outer contraction/recovery rules and charge accurate residuals. | Original-model primal/dual/gap progress is sufficient, coverage is retained, and total certified latency improves in the intended scope. |
| FP16 correction oracle | Quantize matrix first; compare vector quantization separately. Add canonical block scales, FP32 accumulation and accurate master updates. | Correction quality and range behavior justify the extra setup, refresh and recovery work. |
| FP8 and selective exceptions | Test E4M3/E5M2 or supported block-scaled formats under explicit interfaces; compare preconditioner-only use with correction-operator use. | Error budgets remain useful, exceptions stay economical and final original-model coverage does not regress unacceptably under the predeclared selection policy. |
| Structural and Tensor-Core work | Investigate active-face polish, dense blocks, integer emulation or actual independent RHS work only where CPU layout/cost evidence supports it. | Factor/packing/padding/reconstruction costs are included and the correct latency or separately labeled throughput endpoint wins. |

No contraction factor, block size, refresh interval, exception fraction, random
seed or promotion threshold is chosen by this note. Freeze such choices before
comparative trials; do not infer defaults from the illustrative equations.

Use existing diagnostic families deliberately: irregular-2048 for recorded matrix
bias, irregular-32768 for work amplification, scheduling cases for decaying-product
range loss, dense_block-65536 for scale, and mixed-65536 for heterogeneous
coefficients and unresolved convergence. They are already inspected development
cases, not held-out validation. Include exact-rational small cases, cancellation,
subnormal/outlier cases, finite/infinite bounds and both objective senses. New
corpora or changed splits require their own recorded protocol.

Report certified success coverage, all failed/interrupted attempts, paired
fresh-process time, proposals/logical progress, original residual contraction,
outer corrections, audit/probe/replay work, exception density, preparation,
transfers, packing, scales, memory and final certification. Distinguish kernel
busy time from host submission/synchronization envelopes and repeated assessment
cost from final endpoint checks. Keep a matched executor control and tuned FP64;
record warm-resident diagnostics separately from the primary fresh endpoint.

## Contract and resource handoff

Before new numerical behavior, define the represented operator and transpose;
storage/product/accumulation/state/correction precision; scaling and nonzero-loss
handling; step-size validation; complete anchor/correction/restart/checkpoint
state; progress and recovery semantics; determinism and random seeds; failure
classification; budget charging; and original-model authority. Outer refinement,
polishing, persistent work, MILP integration and library dependencies can require
separate specifications or boundary decisions rather than being implicit GPUP-7
features. Ordinary builds must retain the no-toolkit/no-device contract.

Host certification in `optimizer-lp` remains authoritative. A low-precision
iterate, active-set guess, Tensor-Core result, small device residual or successful
audit is not a proof. Preserve the exact-rational regressions, unsafe boundaries,
legacy defaults, records/replay and unsupported-model refusals.

This review and its documentation ran no GPU workload and add no allowance.
Carry forward 17115.274617853 / 18002.574545061 cumulative GPU seconds, every phase
cap, and the 16134-event ledger SHA-256
`60649d29992d21508e60aa60f3e334e9ac18fe3254525ec38cc0eef298e84823` with all earlier
prefixes intact. The arithmetic difference between ceiling and consumption is not
a free reservation: any job still needs a fitting accepted task/phase budget and
the shared host lease. Historical racecheck, large-session and mixed-model gaps
remain open.

## Source map and interpretation limits

Repository reports linked above are the authority for project measurements.
External primary sources identify mechanisms and hardware capabilities, not
performance predictions for this solver. Links were reviewed during the
2026-09-30 discussion; current documentation may change and must be pinned or
rechecked for an implementation study.

| Source | Use in this note |
| --- | --- |
| [Gleixner, Steffy and Wolter, Iterative Refinement for Linear Programming](https://optimization-online.org/wp-content/uploads/2015/06/4948.pdf) | Established correction-LP transformation and the need for an adequate approximate oracle. The anchored quantized executor and its proposed gates are project adaptations. |
| [Haidar et al., mixed-precision Tensor-Core iterative refinement](https://www.netlib.org/utk/people/JackDongarra/PAPERS/mixed-rs-2020.pdf) | Linear-system refinement, low-precision factors, GMRES and range control as a foundation for a possible polishing/preconditioner path. |
| [NVIDIA RTX Blackwell architecture](https://images.nvidia.com/aem-dam/Solutions/geforce/blackwell/nvidia-rtx-blackwell-gpu-architecture.pdf) | RTX FP64 throughput constraints, distinct from datacenter assumptions. |
| [NVIDIA PTX ISA](https://docs.nvidia.com/cuda/parallel-thread-execution/) and [CUTLASS Blackwell functionality](https://github.com/NVIDIA/cutlass/blob/main/media/docs/cpp/blackwell_functionality.md) | Actual instruction, layout, accumulation and integer-dot mechanisms to verify for SM120. |
| [cuBLAS floating-point emulation](https://docs.nvidia.com/cuda/cublas/#floating-point-emulation) | Supported fixed-point emulation, accuracy/fallback/workspace controls and architecture-specific availability. |
| [Ozaki-II](https://arxiv.org/abs/2504.08009) | Integer modular GEMM emulation as an alternative to scalar slice recombination; no sparse-LP conclusion. |
| [Accurate sums and products](https://www.tuhh.de/ti3/paper/rump/OgRuOi04a.pdf) and [stochastic rounding analysis](https://eprints.maths.manchester.ac.uk/2763/) | Existing candidate-register foundations for compensation and rounding; range and operator-bias caveats still apply. |

Additional literature leads from the review, to read in detail before using their
theorems or numerical settings in a contract: [inexact primal-dual analysis](https://link.springer.com/article/10.1007/s10589-020-00186-y),
[PDHG identification and local convergence](https://arxiv.org/abs/2307.03664),
[three-precision linear-system refinement](https://eprints.maths.manchester.ac.uk/2629/1/cahi18.pdf),
and [GPU reliable updates](https://arxiv.org/abs/0911.3191).
These leads are not evidence that the proposed LP adaptations already converge.

Two comparison cautions are worth carrying forward. Published feasibility-polish
experiments can use a much looser gap criterion than their feasibility criterion;
check all metrics in the [PDLP paper](https://arxiv.org/html/2501.07018v1) before
claiming agreement with this project's full 1e-9 target. Also, documented
[cuOpt precision settings](https://docs.nvidia.com/cuopt/user-guide/latest/convex-settings.html#pdlp-precision)
include a `mixed (2)` mode with FP64 vectors/compute and compressed FP32 matrix
storage, separately from its full-FP32 `single (0)` mode. The mixed mode is a
useful storage comparison, not evidence that its bulk arithmetic bypasses the
SM120 FP64 pipe. Neither source establishes a performance result for this project.
