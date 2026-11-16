# SPEC-0045: General low-bit LP implementation and evaluation

Status: active under ADR-0079 and the user's 2026-11-16 execution instruction
Scope: shared sparse LP method, isolated low-bit execution, broad evaluation
Owner: LP backend
Implementation: research/lp-general-lowbit; tools/lp_general_*.py

## Objective and milestones

Deliver a broadly useful LP solver whose performance improves through low-bit
arithmetic, including FP4. Primary cost is a fresh-process single solve through
independently certified output, including preparation, transfers, numerical work,
rollback, checking and owned teardown. Report output availability and durable
research archive completion separately. Prepared solves are additional endpoints.
No family-ID dispatch or required request count defines the candidate.

1. Record the additive GPUP-9 review, effective-factor contracts, prospective
   architecture, development population, inference design and independent budget.
2. Reuse optimizer-lp's sparse original model, preconditioning and method through
   public interfaces. Derive an isolated controller from Fp64Controller with
   explicit source provenance. Add an isolated rectangular sparse operator
   and CPU oracle before any new device execution; preserve portable root builds.
3. Admit new device kernels, state-dependent precision/reference/assessment rules,
   exact recovery and complete resource/cost accounting. Optimize ordinary
   single-vector execution. Dense tensor tiles remain a candidate when measured
   costs justify them; low-bit sparse storage and arithmetic are also candidates.
4. Measure diverse development instances and matched component interactions.
   Separate shared algorithm/host gains from incremental low-bit gains. Compare
   strong native and FP32 controls and established external solver references.
5. Freeze one general policy and unseen grouped instances after power and budget
   preflight. Complete confirmation without retuning or selective omission.
6. Record positive, negative and inconclusive results and close resources. A valid
   negative experiment completes that experiment, not the broad performance goal.

## Numerical architecture

The original LinearProgram and Model are immutable certificate authority. Reuse
the main solver's row/column preconditioner, scaled operator, projected-zero start,
restart/primal-weight formulas and exact checkpoint ownership. The experimental
controller is an explicitly source-bound derivative: historical acceptance binds
the core controller's bytes, and private diagnostic/weight methods are not public
extension APIs. Preserve those core files exactly. The isolated crate reuses the
public Engine and original certificate APIs without changing historical executors
or public selectors. Check the copied control/formula boundary independently.
Working primal/dual state, anchors, controller and final certificate use FP64.

Store rectangular CSR/CSC by nonzero count. Never densify a whole sparse matrix or
pad it to max(rows,columns)^2. Any dense tiles have explicit costs and nonoverlap
maps. Preserve one canonical represented operator across transpose directions.
Count all original/reference, packed, fragment, index, scale and work buffers.
Original GPU data may remain necessary for periodic references; report its cost.

Investigate FP4 E2M1 one/two-component matrix representations, FP32 compressed
controls, and tensor increment products under original-A references. Normal E2M1
codes exclude subnormal codes 1/9 in tensor candidates. Local enclosures include
coefficient representation, vector conversion, accumulation, reference and final
addition errors. CPU outward bounds and independent rational product tests precede
device admission. Every dimension/exponent domain is explicit; extending 2048
requires rederiving applicable accumulation/range bounds, not changing a constant.

Local bounds protect proposals, not global trajectory or certificate claims.
Original residual/progress checks steer the method. A failed local, finite-domain,
or progress check restores all continuation state and promotes precision. Physical
work and elapsed cost never roll back. Cancellation/deadlines precede acceptance.
Final independent original-model feasibility and conservative gap checks remain
mandatory at 1e-7 and 1e-9. A separate unchanged serial checker verifies new
assessment implementations. No endpoint-answer memoization is permitted.

## Evaluation and gates

Development must include multiple independent rectangular/irregular sparse,
dense-block, inequality/active-bound, degenerate and ill-scaled operators, both
small controls and sizes exceeding the old cap. Add public LP instances with
source/license/hash bindings. Related transformations stay in a single split.
Previously inspected cases are development-only. Independent problem/source
groups are the unit for generalization; timing repeats measure timing variability.

Admission checks that scaling changes scales/operators on designated cases,
precision changes represented operands, sparsity selects the intended execution,
and fixed-work comparisons hold non-target controls constant. Inactive factors
are labeled as such, never interpreted as numerical effects. All failed, censored,
unsupported and fallback runs remain in coverage and cost results.

Separate correctness, research-development and broad-adoption decisions. A
development gain does not release a preset. Confirmation must predeclare a broad
effect estimand, stratum coverage/benefit and nonregression/tail criteria, substantial
accepted low-bit contribution, familywise false-positive control at .05, and a
power target of at least .90 at the smallest justified practical improvement.
Select sample counts from development variability and grouping before holdout,
with a complete reservation preflight. Do not lower the breadth or practical
target after viewing confirmation. Retain relative and absolute effects; a
uniform 10 ms floor across all latency scales is not automatically inherited.
The concrete confirmation roster, thresholds and analysis must be frozen in a
new manifest before confirmation starts; no confirmation is implied by a pilot.

## Independent resources

Agent-selected finite ceiling under the user's execution authorization: 240000
CPU seconds / 30000 GPU seconds. This is independent of all closed campaigns.

| Phase | CPU seconds | GPU seconds |
| --- | ---: | ---: |
| implementation (including 512 preparation administration) | 60000 | 0 |
| native acceptance | 24000 | 0 |
| admission | 48000 | 6000 |
| development | 48000 | 12000 |
| confirmation | 40000 | 10000 |
| reporting | 16000 | 2000 |
| cleanup (including 128 closing administration) | 4000 | 0 |

Receipts: artifacts/gpup-general-v1. Preserve the admitted one-second supervisor,
5–10 ms target and all 100 ms advisories; four CPU slots, 16 GiB sampled RSS,
12 GiB owned device buffers and one pinned host-wide shared GPU lease. Sampled
RSS is not a peak enclosure. Reserve four times the wall deadline for CPU and
the entire lease-held job lifecycle for GPU. Failed jobs retain full reservations
and exact sources. Never silently retry a scientific cell. Development corrections
receive new source-bound identities. Unsettled reservations, resource overruns,
loss of supervision or nonempty cleanup require disposition before further jobs.

New-device admission follows full native acceptance and CPU numerical contracts,
then differential products/updates, original certificates, recovery/cancellation,
and all four scoped sanitizers. Confirmation uses an admitted frozen candidate.
Preserve previous scientific files and prior handoff text exactly. Run the full
native acceptance gate for delivery, portable evidence checks and local commits.
No public defaults, push, hosting or publication are authorized.

## First sparse candidate and admission details

The first device candidate consumes packed normal E2M1 matrix components and
binary32 vector increments using explicit binary32 SIMT products/reductions.
It is not an FP4 Tensor Core implementation. Native FP64 and compressed FP32
controls use the same sparse geometry and solver controller. A gain over native
alone cannot establish an incremental benefit from the FP4 representation.
Native preparation constructs only original sparse data; it does not pack FP4,
convert FP32 coefficients or construct low-bit transpose IDs/guard metadata.
The FP32 control also skips FP4 packing. Promotion can access only representations
prepared for that executor. Transient input bytes are released after original
model parsing and hashing. These costs are compared prospectively in every lane.

Each orientation assigns one 32-lane warp per output. Lane-strided sums use a
fixed shuffle tree; no atomic accumulation is used. Matrix components share one
canonical nonzero index in both orientations. Dimensions are at most 2^20 and
nonzeros at most 2^26; finite scaled coefficients and probe/low-bit working
vectors have magnitude at most 2^40. Packing exponents lie in [-48,48]. All
original/reference and represented products therefore remain in finite FP32/64
ranges within the admitted domain. The CPU oracle and device use their own
explicit reduction orders; equality between unlike reductions is not assumed.
The validated original model rejects duplicate variable terms in a row, so each
row/column has at most 2^20 entries. Thus the FP32 gamma denominator stays
positive even at the admitted dimensional limit; the total-nonzero limit is not
mistakenly used as a per-row accumulation count.

For each row, the local bound sums a conservative native-reference error,
coefficient-error L1 times the true increment maximum, represented-coefficient
L1 times conversion error, and gamma(4*row_nnz+32,2^-24) times represented L1
times the rounded increment maximum. This operation count covers lane sums and
the shuffle tree for both components. It adds FP32 underflow allowance and FP64
subtraction/final-addition allowances. Host metadata and device arithmetic round
outward. Reference gamma uses a doubled FP64 unit roundoff and an absolute
product sum, with an underflow allowance. Independent exact rational products
and an explicit Python lane/tree update reference test these separate bounds
and numerical paths. These checks do not replace the analytic count/domain.

The opt-in projected-step residual addresses bound complementarity missing from
the existing diagnostic. It uses one original scaled PDHG map without Halpern
averaging, then takes the maximum absolute primal/dual displacement. It steers
restarts and guards, has no certificate authority, and preserves the legacy
diagnostic for existing callers. GPU proposals commit only at an original host
assessment boundary; a failed window restores all state at the preceding
boundary and promotes precision. All intervening work remains charged. CPU
window-oracle progress checks have finer cadence; performance comparisons use
the matched GPU controller in every precision lane. Deadlines are checked again
after assessment, before accepting a certificate.

## Prospective correction after the first development pilot

The first 128-cell pilot and all of its refusals remain exact. The next version
uses one eighth of the original projected displacement as its local displacement
budget. Both sides have state units; the former unit cap and multiplication by
state magnitude were dimensionally inconsistent. A zero or nonfinite residual
admits no inexact displacement. The same progress, rollback and final certificate
requirements remain. This policy is prospective development, not an old regrade.

All four public HiGHS optimal endpoints were refused by the old certificate path:
unbounded declared variable directions require a reduced-cost sign enclosure
that may fail near a zero reduced cost. Add a general implied-bound certificate
path, shared by every precision. Derive only previously infinite variable bounds
from original rows and already proved bounds, with outward binary64 arithmetic.
At most 16 sparse passes and two endpoints per variable bound preparation work.
Do not guess finite bounds or clip reduced costs. Leave unresolved directions
infinite. Numerical execution continues on the unchanged original program.

Emit the complete implication proof. An independent exact-rational verifier
checks each step against original coefficients and previously established bounds,
and rejects any other model modification. The unchanged serial checker evaluates
the equivalent tightened model for its dual bound and conservative gap; a separate
unchanged serial check of the original model remains primal-feasibility authority.
Compose those two checks only after verifying the equivalence proof. All bound
preparation and checking inside the solver count in single-solve cost. This is an
additive original-model proof, not relaxation of accuracy or use of an external
solver's optimal status as authority. Free or otherwise unresolved directions
still require further general certificate work; their refusals remain visible.

For an originally feasible endpoint whose bound is still unavailable, permit at
most four untrusted dual corrections. Restrict proposals to reduced costs within
64 machine epsilons times max(1, objective-coefficient magnitude plus absolute
product sum); this limits proposal size and is not certificate authority. Select
an eligible largest-magnitude coefficient deterministically, respect row signs,
and decline free-variable equalities or larger violations. Retain the actual
certificate dual separately from numerical continuation state. The unchanged
checker must certify that witness, and independent replay uses that exact witness.
All proposal and rejected checking costs remain in the assessment phase.

## Interrupted extended development campaign

The first 17 model groups settled. Group 18 lost its process tree and command
session without a final supervisor receipt; its first response survives. Stop
this frozen campaign, preserve all original files, and do not rerun its cells.
The cause is unassigned. An observed-empty cleanup check does not reconstruct
historical supervision, memory bounds or a successful group receipt.

Charge at least its full reservation and conservatively the whole interval from
the journal's start through independently observed empty cleanup. Record the
reservation excess explicitly; do not assert that this is measured compute time.
A hash-bound disposition may release CPU implementation, acceptance, reporting
and cleanup only. New GPU or scientific execution remains closed pending
operational readmission. Keep the one-second supervisor and every 100 ms
advisory unchanged. Publish explicit missing cells and distinguish retained
numerical endpoints from timings eligible under a complete resource receipt.

## Actual Tensor Core continuation (2026-11-16)

The user authorizes actual FP4 Tensor Core arithmetic and redesign of guards,
precision policy and mixed-precision machinery for general performance. This
prospective development keeps all earlier candidates and observations unchanged.
The new opt-in backend uses canonical 32-by-32 sparse blocks, admitting tiles by
their nonzero density alone. Remaining entries stay sparse. It never densifies a
whole operator. The represented transpose uses exactly the same coefficients.
Normal E2M1 matrix and vector components feed actual SM120 MMA instructions with
FP32 accumulation and FP64 solver state. Single-vector execution remains primary.

Investigate direct products without periodic original-A anchors. Tile-local
coefficient/vector error bounds replace global vector maxima. A local refusal
recomputes that output from original FP64 coefficients before projection; no
uncertified approximate row enters the state. This local proposal replacement
supersedes whole-solve promotion for these local refusals only. Global progress,
finite-state, cancellation and fault failures still restore the complete control
checkpoint. Physical attempted, rejected, exact and accepted nonzero work is
reported separately. A native replacement is never counted as FP4 work.

Control feedback and certificate assessment have separate cadences, shared by
native, FP32 and Tensor Core controls. Final certificates remain unchanged and
mandatory. Comparisons include preparation, packing, launch, correction and
checking; density thresholds and precision settings are development parameters,
not family identifiers. No new confirmation is frozen by this continuation.

Operational readmission requires a fresh CPU-only supervisor contract suite and
settled supervised workload probe, exact current supervisor/budget source
bindings, empty cleanup and the unchanged one-second bound. Its prospective
receipt explicitly names the interrupted disposition; it cannot reconstruct
historical supervision or repair the missing cells. GPU numerical admission then
requires current CPU/native acceptance, independent product/guard verification,
recovery tests and all four sanitizers before new development comparisons.
The existing independent allocation and phase ceilings remain unchanged.

The first actual tensor admission passes independent products, original serial
certificates, restoration and four sanitizers. Direct two-component products
still require frequent row replacements. The next development version admits
one through four normal-E2M1 components (reported explicitly; four FP4 components
are not a claim of four-bit total storage). Component dots contain 32 quarter-
integer products with absolute sum at most 1152, so unscaled MMA accumulation is
exact. Power-of-two scale sums remain in [-96,96]; scaled normal sums are finite.
Across tiles and component pairs, gamma(k*k*tile_count+1,2^-24) bounds FP32
accumulation. Tile coefficient-error L1, component L1, and vector-block actual
representation error are outward enclosures. Matrix sums include binary64
component/subtraction allowances; vector conversion includes its actual decoded
components and binary64 subtraction error. Independent rational checks verify
both transpose directions against original coefficients, not merely decoded data.

Compare direct products with control-boundary original-A references. The latter
quantizes only the current increment from its FP64 anchor and refreshes at control
boundaries, not every 16 updates. Sparse remainder products use the same increment;
all subtraction, original reference, accumulation and final-addition errors are
included. Native row replacement always recomputes the full original product.
The reference's 32-lane tree has at most ceil(row_nnz/32) accumulation depth plus
five shuffle levels; gamma(ceil(row_nnz/32)+8,2^-52) and a conservative underflow
allowance enclose it. Count references separately from useful tensor nonzeros.
Direct mode remains an ablation; no reference cost is hidden in native work.

Reuse a control merit only for the identical state and weight; a changed weight
requires fresh evaluation. Cache kernel handles within each launch window and
reuse an accepted final assessment without repeating the same certificate work.
These shared optimizations also apply to the new native and FP32 controls.

The optimized candidate packs two four-coefficient MMA byte fragments into one
32-bit nibble word, expanding only into registers. Expanded fragments remain a
matched layout ablation. A row-block histogram discovers eligible tiles in linear
sparse passes, avoiding a heap allocation for every occupied sparse block.
Operators with no eligible tiles select native execution explicitly and contribute
zero FP4 work; this does not count toward the low-bit objective. The FP32 control
stores actual binary32 coefficients in each orientation and retains original
coefficients only for references/correction. Its bound uses the actual lane/tree
accumulation depth. Tensor product launches expose one or four warps per block;
this changes occupancy, not arithmetic order. Both layouts and launch shapes need
numerical and sanitizer admission. Retain direct, two-component, expanded-layout
and four-warp diagnostic comparisons, then assess the common four-component policy
against native and FP32 on the whole 22-model development roster at both tiers.
