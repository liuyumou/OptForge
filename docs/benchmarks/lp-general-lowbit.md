# General low-bit LP development

Status: active engineering; no broad performance or adoption claim.
Contract: [SPEC-0045](../specifications/SPEC-0045-general-lowbit-lp.md).
Direction: [ADR-0079](../decisions/ADR-0079-general-lowbit-lp.md).

The objective is a broadly useful LP solver whose performance improves through
low-bit arithmetic, including FP4. Fresh single solves remain primary. Prepared
sessions are an additional endpoint. General improvement requires independently
sampled LP structure, conditioning, sizes and accuracy tiers, plus demonstrable
accepted low-bit contribution; a workflow-specific configuration is insufficient.

## Additive interpretation of GPUP-9

The old study and decisions remain exact. The review found its scaling factor
numerically inactive. Generator-v2 sets diagonal coefficients in
[1-18/(73n),1+18/(73n)], with n>=33; all off-diagonals are smaller, including the
0.5 cyclic addition. Thus every row maximum is between 0.992528 and 1.007472.
The implemented exponent -round(log2(maximum)) is zero and every scale is one.
The 72 scaled/unscaled screening session pairs / 288 response pairs have identical
terminal states, checkpoint states, physical/logical work, final lanes and
certificates. Timing contrasts cannot demonstrate a numerical scaling effect.
There were four distinct numerical configurations, despite eight option labels.

The largest possible off-diagonal row sum remains at least 0.253424 below the
smallest diagonal magnitude, so the square equality operators are nonsingular.
Their constraints essentially fix the primal solution; bound/inequality choices
and degeneracy in general LPs were not represented. One operator per family/split
does not turn repeated timings into independent problem samples. These limits do
not invalidate the retained certificates or justify regrading any old criterion.

## Current implementation

The isolated Rust crate reuses the original sparse model, row/column preconditioner
and PDHG step. Its FP64 controller derives from the original restart/weight/
checkpoint implementation with explicit source provenance. Both CSR orientations refer to one
canonical FP4 representation. Storage is linear in nonzeros and dimensions, with
explicit accounting for original data, indices, mapping, codes and scale metadata.
The CPU reference admits rectangular matrices beyond the old 2048 limit and has
normal E2M1 one/two-component and FP32 controls. This is not yet a GPU speed claim.

A new opt-in projected-step residual includes bound complementarity. The old
controller diagnostic can be zero at a feasible bounded point with a nonzero
objective step. New control uses the projected residual consistently for restart
anchors and progress; existing callers retain their original diagnostic and
behavior; the experimental diagnostic lives entirely in the research crate.
Neither diagnostic has certificate authority.

## Development and validation log

The first CPU reservation failed because the provisioned Cargo directory was
absent from PATH. The second exposed that the controller's existing diagnostic was
private. Both exact versions and full 1200 CPU-second reservations are retained.
CPU-contracts-v3 passed six contracts, including 32769-column rectangular storage,
canonical transpose, exact shared native control, rollback/physical accounting,
cancellation and invalid input refusal. CPU-contracts-v9 passes seven Rust tests,
Clippy/dependency checks, 384 exact-rational requests / 12992 products, and 144
original construction assessments across 72 independently generated development
LPs. All 144 agree with the retained original serial checker. Four public LP
conversions (afiro, adlittle, israel, 25fv47) match native HiGHS MPS roundtrips
exactly. All are development-only; no holdout has been inspected.

The first full native gate passed Rust tests but failed three historical Python
source-binding checks after core API extensions. Those exact failures retain the
full 9600 CPU-second charge. The core sources were restored exactly, and the new
controller moved into the isolated research crate. The corrected native-v2 gate
passes 638 repository Rust / 816 Python tests, documentation, committed replay
and smoke. Earlier development lint/format failures also retain full reservations
and source snapshots.

CPU-contracts-v11 passes nine isolated Rust and six Python contracts, dependency/
Clippy checks, and fresh construction/public-input verification. Its 384 ordinary
product requests cover 12992 outputs; long-row tests add 16400 outputs. The same
29392 product outputs pass independent exact-rational checking on the GPU.
Device-v2 passes 72 fixed-update, recovery, cancellation, positive-certificate,
zero-row and large-dimension cases, with original serial checking. All four
sanitizer suites, including the long-row suites, passed. A preparation-only
comparison preserved all 72 numerical/accepted-work transcripts exactly.

Before timing, native and FP32 preparation were strengthened: each omits
unreachable lower-precision representations. Native no longer pays FP4 packing,
FP32 conversion, transpose mapping or coefficient guard computation; FP32 omits
FP4 packing. Input bytes are released after validation and hashing. No earlier
timing is regraded. The corrected version passed admission before timing.

## First broad development pilot

The frozen first pilot completed all 128 fresh-process cells: smallest/largest
instances from six generated families, all four public LPs, native/FP32/FP4x1/
FP4x2, and 1e-7/1e-9. Each format certified only 9 of 32 model/tier cases at the
2000-update ceiling. All public cases remained uncertified. Every intermediate
assessment and final endpoint was independently checked; failures remain in the
denominator. One observation per cell is diagnostic, not inferential evidence.

| Initial format | Certified cases | Accepted native updates | Accepted FP32 updates | Accepted FP4 updates |
| --- | ---: | ---: | ---: | ---: |
| native | 9/32 | 54500 | 0 | 0 |
| FP32 | 9/32 | 7936 | 46500 | 0 |
| FP4x1 | 9/32 | 7808 | 44192 | 1700 |
| FP4x2 | 9/32 | 7872 | 44496 | 1700 |

All accepted FP4 work occurred in the small irregular instance. Rejected work is
reported separately and cannot establish low-bit contribution. Median completion
times over all outcomes were 384.82, 390.72, 396.55 and 391.84 ms respectively;
these include uncertified limits and are **not time-to-certified-solution**.
There were 27 eligible individual comparisons, with no statistical value test.
This result does not satisfy the project's broad performance objective.

The single-thread pinned HiGHS reference returned optimal status on all 16 models.
The original checker certified all 12 generated endpoints at both tiers but
refused all four public endpoints too. This identifies a certificate limitation
in addition to the iterative solver's convergence limitations. The initial
external-control command incorrectly requested three unsupported threads; all 16
process refusals remain, and an append-only correction charges its full 1200 CPU
second reservation. No old receipt was edited.

## General corrections and diagnosis

Independent first-window trajectory/product replay found premature guard failure
in six of seven inspected cases. The old rule capped a dimensioned projected
displacement at 1, then multiplied by state magnitude. For example, initial
residuals were 15.49 for afiro and 44.91 for the ill-scaled fixture, yet both had
a 0.125 local budget. The prospective rule compares displacement with one eighth
of the original projected displacement, preserving state units. Exact rational
checks also show that global increment maxima times row L1 norms can be very
conservative: the ill-scaled diagnostic bound was 0.9993 against actual error
0.000297. Better bounds remain a general optimization target.

The certificate path now derives missing finite bounds from original rows, using
outward arithmetic and explicit implication proofs. It leaves the numerical
program unchanged. Independent exact-rational verification checks every
implication; the unchanged checker evaluates the equivalent model's dual bound,
while the original model remains primal-feasibility authority. Unproved infinite
directions remain infinite. This addresses three public HiGHS endpoints directly.
The remaining 25fv47 failure was a reduced cost about -1.6e-16. A generic proposal
limited to near-zero reduced costs repairs it; the unchanged checker must accept
the actual retained repaired dual. It does not change numerical continuation.

CPU-contracts-v14 passes 12 isolated Rust and eight Python contracts, Clippy,
140 independent model/proof checks, all 32 external endpoint/tier assessments,
29392 exact product outputs, 144 construction certificates and four native public
input roundtrips. A lint failure remains fully charged. Earlier device admission
caught a zero-operator guard refusal: generic underflow allowances were positive
for an exactly empty dot product. The kernel now returns the exact zero product
and zero bound for empty rows; the failed version and full charge remain.

The extended comparison includes the entire original roster and six
larger independent generated instances: 1025 dense columns; 16385 dense-block;
32769 ill-scaled/degenerate; and 65537 irregular/rectangular. All twelve large
construction certificates pass at both tiers. Compact generated inputs remain
local with source, seed and hash bindings. The frozen common limits are 20000
updates, checks every 500 updates, and 30 seconds, with all four precisions and
both accuracy tiers. No holdout has been generated or inspected.

## Extended development results and interruption

The campaign retains 137 of 176 responses: 136 in 17 fully settled model groups
and one in the interrupted eighteenth group. Its remaining 39 cells are missing.
The process tree and original command session disappeared without a final
supervisor receipt. The cause is unknown. Recorded process identities and their
sessions are absent, all three locks are free, and the device has no compute
processes. These observations establish current cleanup, not past supervision.
The frozen campaign is stopped; no existing cell was retried. Its missingness
may be informative, and no complete-cohort inference is made.

The interrupted job retains the original reservation, active journal, source
snapshot, complete first response and every intermediate file. Its conservative
charge is 4053.285828748 CPU / 1013.321457187 GPU seconds, covering the whole
journal-start-to-observed-empty interval. This exceeds the 1920 / 480 reservation
and is an upper charge, not measured compute usage. No historical resource
enclosure is reconstructed. The hash-bound disposition permits CPU validation,
reporting and implementation; GPU/scientific work requires operational readmission.

| Initial format | Certified / planned | Responses with complete supervision | Accepted FP4 updates | Median eligible native/candidate ratio |
| --- | ---: | ---: | ---: | ---: |
| native | 18/44 | 34/44 | 0 | 1 |
| FP32 | 18/44 | 34/44 | 0 | 0.8440 |
| FP4x1 | 18/44 | 34/44 | 2000 | 0.8493 |
| FP4x2 | 18/44 | 34/44 | 2000 | 0.8435 |

Each ratio column uses the 18 individually certified matched observations only;
the coverage columns retain all planned cases. These conditional descriptive
ratios are not population speedups or formal value decisions. Each candidate is
faster in only two of those 18 pairs. All unsuccessful, missing and partial cases,
individual effects and cost partitions remain in the
[compact result record](lp-general-lowbit-results.json).

The solver now certifies afiro and adlittle at both tiers. Israel, 25fv47 and all
observed generated sparse instances with at least 4097 columns still reach the
20000-update ceiling. Separately, all four public HiGHS endpoints certify with
the new proof path: certificate support and iterative convergence are different
limitations. Extending the iteration limit and changing the check cadence also
changed the experiment; improved coverage cannot be attributed solely to the
guard or certificate corrections.

No FP4x1 update survives acceptance. Both FP4 starts accept 2000 FP4x2 updates,
only on the small irregular and ill-scaled models. This is about 0.48% of their
accepted updates, and only 0.0017% of their accepted nonzero product work. Most
runs promote within the first window. Native fallback is useful for correctness,
but does not satisfy the low-bit performance objective.

The phase measurements also explain why individual total-time gains are not
enough. On strict dense33, native takes 443.742 ms versus FP4x2's 409.062 ms, yet
numerical execution rises from 29.588 to 79.879 ms; device setup falls from
322.005 to 236.775 ms. One observation cannot identify the cause of that setup
difference or establish an arithmetic gain. On irregular65537, both versions
remain uncertified: native completes in 16.355 s and FP4x2 in 22.933 s, with
execution 4.619 versus 10.698 s and assessment 7.710 versus 8.108 s.

Reducing assessment frequency is also not a free host optimization. The shared
controller performs restart feedback at those boundaries. Strict native dense33
and dense257 require 700/1100 updates in the check-100 pilot but 2500/3000 in the
check-500 experiment. This version comparison is diagnostic, with other changes
present, and it motivates separating control feedback from expensive certificate
checks before another matched study.

## Engineering priorities retained by this result

1. Reestablish durable operational completion and source-bound admission before
   another GPU experiment. Preserve this interruption and missing cells exactly.
2. Improve the shared general method's convergence, including independent cheap
   restart/progress feedback and strict certificate cadence. Keep native and
   FP32 controls equally strong; include public inequalities, degeneracy and
   ill-scaled problems throughout development.
3. Replace overly conservative global-max guard estimates with admitted local
   bounds and state-dependent reference/precision decisions. Measure accepted
   nonzero low-bit work and every rejected/reference/fallback cost. A policy
   that almost immediately promotes everywhere is not a useful FP4 method.
4. Reduce the low-bit execution overhead and admit actual FP4 arithmetic where
   appropriate for general operator structure. The present sparse kernel decodes
   E2M1 storage and computes FP32 SIMT products; it does not use FP4 Tensor Cores.
   Sparse/dense-block handling must follow matrix structure, never fixture IDs.
5. Reevaluate the broad development population before freezing a powered unseen
   confirmation. Keep single-solve cost primary, original-model accuracy strict,
   and breadth, substantial FP4 contribution and tail/nonregression gates intact.

These are continuing implementation requirements. The negative pilot does not
complete the broad performance objective or justify a workflow-specific product.

## Delivery validation

The final native-v3 gate passes 638 Rust tests (637 workspace/doc tests and one
Rust test invoked by the Python gate), 819 Python tests, formatting, Clippy,
dependency checks, committed replay, documentation and smoke. The isolated
candidate's 12 Rust contracts and nine Python general-program contracts pass.
Its admitted image has 72 device cases, 29392 independent rational product
outputs and all four scoped sanitizer suites. The implication path additionally
passes 140 independent proof checks and all 32 external endpoint/tier certificates.

The first portable packaging attempt hit the unchanged 512 MiB per-file limit.
Its partial archive, exact sources, error log and full 3600 CPU-second charge
remain local. Packaging now uses independently hashed parts with at most 128 MiB
of raw evidence per part. This changes packaging only; it does not raise the
supervisor's file limit or change any scientific response.

The replacement archive passes: 43484 exact files, 4857558154 raw bytes and
1156248782 compressed bytes in 42 parts, each below 44 MiB. Isolated replay from
the extracted root independently checks all 265 retained responses / 5833
assessments and all four public-input conversions. It preserves 39 missing
cells; 264 responses have complete campaign supervision receipts. Byte retention
and numerical replay do not repair the interrupted group's resource record.

The local bundle includes all settled earlier failure receipts and source
versions. Its own packaging/replay receipts follow the archive boundary and are
bound separately in the [delivery validation record](lp-general-lowbit-validation.json).
The failed packaging container is also retained locally with a hash in the new
manifest. No large matrix, endpoint stream, binary or archive is committed to Git.

Exact preservation covers all 2286 baseline tracked files: 2282 unchanged, with
only additive current handoffs and explicitly recorded backlog routing in four
navigation files. Earlier task text, scientific records, runtime sources and
public defaults remain exact.

The open allocation checkpoint is 40002.661693116 CPU / 2623.360765263 GPU
seconds out of the independent 240000 / 30000 ceilings, including the 512 / 128
CPU preparation/closing reserves. All ten refused reservations retain their
full charges and sources; the failed external-reference children additionally
retain their append-only full-reservation adjustment. The interruption charge
conservatively exceeds its reservation as described above. Current cleanup is
empty; sampled RSS is not a hard peak-memory enclosure. Confirmation has no
charges or frozen cohort. Earlier allocations remain closed.

Receipts and immutable source snapshots: artifacts/gpup-general-v1. Allocation
and broad objective remain open; this is an engineering checkpoint, not adoption.


## Actual Tensor Core continuation

The separately admitted [actual FP4 Tensor Core continuation](lp-general-tensor.md)
retains the original pilot and interruption unchanged. Its complete ablation and
full-solve development cohorts diagnose useful FP4 work, local guards and complete
cost on the broad roster. Numerical admission and substantial FP4 contribution do
not establish a speed advantage; the general low-bit objective remains active.
