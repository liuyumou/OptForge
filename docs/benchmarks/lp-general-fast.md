# General low-bit LP: specialized FP4 search proposals

This is an additive development record under
[SPEC-0045](../specifications/SPEC-0045-general-lowbit-lp.md) and
[ADR-0079](../decisions/ADR-0079-general-lowbit-lp.md). The objective remains a
broadly useful LP solver with faster ordinary single solves through low-bit
arithmetic, including FP4. Historical results and criteria in the
[Tensor Core report](lp-general-tensor.md) remain unchanged. This development
does not establish broad adoption or release a public default.

## Design

The opt-in `gpu-fast` executor treats approximate products as search proposals.
It keeps FP64 iterates, original-operator references, host residual/restart
control, complete checkpoint recovery, physical-work charges, and strict
original-model certificates. It removes the local outward-bound calculation
from this executor; `gpu-tensor` retains that implementation as a control.
Proposal probes explicitly say `enclosed: false`.

In the split schedule, each warp computes one 16-by-32 half tile, exposing the reduction dimension to
the device. Component counts are compile-time specializations. Each lane
reconstructs only its own component columns, followed by a four-lane reduction.
The sparse projection kernel specializes native FP64, actual FP32, and FP4
tile-plus-FP32-remainder paths and selects 1/4/8/32 lanes from work per output.
Fusing vector encoding into projection reduces split FP4's ordinary update from six
launches to four where the row shape permits it. The final combined schedule
uses two launches; native and FP32 also use two.
There is no numerical atomic accumulation or model-identity dispatch.

No-tile FP4 requests explicitly select FP32 and contribute zero FP4 work.
Original matrices, both packed orientations, reference and cached-delta vectors,
and split-schedule tile partials remain in the memory accounting. One/two/four FP4 components mean multiple
four-bit operands, not four total coefficient bits including all retained data.

## Measured optimization sequence

The first admitted version is `fast-image-v3`. Its matched 96-cell fixed-work
pilot covers six dense, block-sparse, irregular, rectangular and public LP
models, two counterbalanced repetitions, eight execution configurations, and
500 physical updates per cell. These are development costs, not certified-solve
speedups. Full fresh-process cost includes preparation and owned teardown.

Compared with the previous FP4x4 implementation, FP4x4 execution falls from
32.04 to 12.57 ms on dense257, 77.20 to 15.64 ms on dense1025, and approximately
92.56 to 12.21 ms on dense_blocks16385 (paired-repeat medians, rounded).
The equally specialized native kernel is faster too: the corresponding execution
medians are approximately 5.36, 8.88 and 11.19 ms. Shared improvements therefore
do not establish an FP4 advantage.

Nine timelines, each bracketed by uninstrumented runs, preserve all 27 numerical
transcripts exactly. On dense1025, FP4x2 multiplication takes approximately
1.86 microseconds per launch, while projection/encoding takes 9.76 microseconds.
The step kernel contains the correctly rounded FP64 division used by the dual
projection. The next candidate removes it by projecting in positively scaled
coordinates. This changes floating-point evaluation and requires new numerical
admission; strict certificate authority is unchanged.

Preparation also replaces repeated per-nonzero tree lookups with a linear
transpose/coverage permutation, verifies the untiled original coefficients too,
uses equivalent nearest-even quantization thresholds, and hoists component
power-of-two scales. An independent boundary test preserves normal-E2M1 ties.
The initial build of this candidate failed Clippy's iterator lint; its full
reservation and sources are retained before the corrected candidate.

`fast-image-v5` passes the same independent arithmetic/solve admission and four
sanitizers. Its second 96-cell fixed-work pilot retains mixed performance:
packing improves, but FP4 execution does not reliably improve. The division
instruction sequence disappears from SASS; that does not prove it was the main
latency cause. On dense1025, the new trace separates the two FP4x2 projection
launches at approximately 4.67 and 14.37 microseconds. An average-based eight-lane
choice leaves a long untiled column on the critical path.

The following combined candidate gives every sparse remainder row a full warp.
Each CTA covers 32 outputs, with four warps per half tile reducing the tensor
column dimension. It combines products, remainder, projection and optional
encoding in one launch per direction and omits the unused global partial buffer.
The changed FP32 reduction order has its own independent oracle; the split
implementation remains selectable. This is a general sparse-shape implementation,
not a dispatch by benchmark name.

The first combined candidate, `fast-image-v7`, is a retained negative version.
It serializes four full-warp row reductions/projections in every CTA, including
short rows. Its FP4x2 block-sparse launch medians are approximately 21.25 and
28.22 microseconds, versus 7.39 and 8.86 for the new native control in that trace.
`fast-image-v8` adapts each four-row group to eight lanes unless a remainder row
has more than 64 entries, retains forced full-warp reduction as an explicit
control, and projects all 32 outputs in parallel. Its FP4x2 kernel's SASS listing
shrinks from 12,581 to 3,701 lines; neither version has observed LDL/STL spill
instructions. These static observations are not measured occupancy.

The third pilot also encounters a materially different shared-device period:
unchanged native controls and context costs become more variable. A separately
budgeted observation launches no solver or CUDA work and records 20 management
samples with 47–99% device utilization; the process query exposes no owner.
This establishes activity during that observation, not its owner or a causal
explanation for every historical timing difference. All third-pilot observations
remain. Later comparisons must be interpreted as shared-device development,
without an uncontended-performance or broad-superiority claim.

The final candidate, `fast-image-v9`, caches the FP32 vector difference once
per element at reset/projection, rather than repeating FP64 subtraction and
conversion for every remainder nonzero. The native FP64 product is unchanged.
All 444 main admission responses match the preceding image exactly after
excluding timing and allocated-byte fields, including signed-zero JSON
representations. This establishes arithmetic preservation on the admitted cases;
its performance effect is measured in the next complete development pilot.

Hardware performance counters remain unavailable from the earlier diagnostic.
Timelines are instrumented observations, not measured occupancy or independent
instruction-level causal effects. The pinned device's physical UUID is verified
through the CUDA-ordinal mapping.

## Evidence and status

Large raw evidence stays local under `artifacts/gpup-general-v1/fast-*`; compact
[complete results](lp-general-fast-results.json), [final timeline summaries](lp-general-fast-profile-results.json)
and the [validation receipt](lp-general-fast-validation.json) accompany delivery. Each candidate has separate
CPU arithmetic checks, source/image admission, all four sanitizers and prospective
development identities. Failed cells are retained without scientific retry.

## Final fixed-work pilot

`fast-pilot-v5` completes 108/108 supervised cells: six unchanged models, nine
configurations, two counterbalanced repetitions and exactly 500 physical updates
per cell. The following execution medians are milliseconds, not certified-solve
speedups. Old controls use the archived, unchanged tensor executor and image.

| Model | Old native | Old FP4x4 | New native | New FP32 | New FP4x1 | New FP4x2 | New FP4x4 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| dense257 | 9.537 | 32.146 | 6.387 | 5.354 | 6.396 | 7.442 | 7.974 |
| dense_blocks16385 | 72.227 | 92.824 | 10.464 | 10.149 | 11.190 | 12.167 | 12.164 |
| dense1025 | 15.747 | 77.127 | 9.493 | 6.425 | 9.495 | 12.549 | 15.644 |

Final FP4x4 execution is 4.03–7.63 times faster than the old implementation on
these fixtures. Native improves too, by 1.49–6.90 times. Complete-process FP4x4
medians improve only approximately 1.015, 1.182 and 1.171 times respectively;
setup, preparation, checking and teardown remain in that denominator. Two
repetitions on a shared device do not establish population performance.

Combined versus split FP4x2 is mixed: 7.442 versus 10.482 ms on dense257,
12.167 versus 12.170 ms on dense_blocks16385, and 12.549 versus 11.529 ms on
dense1025. Fused encoding helps compared with its explicit unfused control,
whose corresponding execution medians are 9.444, 15.282 and 13.613 ms. Fewer
launches are therefore useful but do not by themselves select the best schedule
for every sparse shape. All irregular, rectangular and public-model observations
remain in the compact results, including zero-tile cases that execute FP32.

The cached-delta version's dense1025 FP32 execution median is 6.425 ms versus
9.508 ms in the preceding pilot. This is a source-version development observation,
with exact admitted arithmetic equivalence but different measurement periods;
it is not an isolated causal estimate under controlled device load.

## Final broad comparison and diagnosis

`fast-broad-v2` completes all 176 supervised cells: the unchanged 22-model
roster, both 1e-7 and 1e-9 tiers, and four global precision configurations.
Both FP4 configurations use the combined schedule. These are single-solve
development observations, with one timing per model/tier/configuration.

| Configuration | Certified / 44 | Iteration limit | Deadline | Native / candidate median complete cost | FP32 / candidate median complete cost | Actual FP4 share of accepted product work |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Native | 20 | 24 | 0 | 1.000 | — | 0% |
| FP32 | 20 | 23 | 1 | 1.038 | 1.000 | 0% |
| FP4x1 | 21 | 23 | 0 | 1.023 | 0.990 | 5.013% |
| FP4x2 | 20 | 24 | 0 | 1.017 | 0.985 | 24.131% |

Ratios use only the 20 jointly certified cases, with values above one favoring
the candidate. The FP4 contribution denominator covers accepted product work
across the complete roster, including unsuccessful solves; original-reference
work is reported separately. Rejected attempts retain their physical cost.
There are 14 jointly certified cases with actual FP4 work. FP4x1 is nominally
faster than native in 8/14 and FP32 in 5/14; FP4x2 is faster in 6/14 against
either control. These small single-pair differences are not significance or
adoption passes. Model/tier cells are not independent problem groups.

FP4x1's additional certificate is public `israel` at 1e-7. It accepts 500 FP4
updates, rejects the next 100, promotes, and accepts 18,500 native updates.
That is a useful retained trajectory observation, but not evidence of sustained
FP4 execution or a general convergence improvement. There are 18 promotions in
the FP4x1 lane, versus 10 for FP4x2 and 12 for FP32. Lower per-update component
cost does not automatically yield lower certified-solve cost.

The broad objective therefore remains open. The redesigned FP4 no longer loses
every certified comparison with native in this cohort, but both FP4 policies
remain slightly slower than FP32 at the descriptive median. Native itself still
fails to certify 24/44 cases within the development allowance. Convergence and
control/check costs are substantial general-solver problems, not reasons to
exclude difficult sparse LPs from evaluation.

For example, large irregular native runs at the two tiers take 30.032 and
16.533 seconds, with assessment costs of 25.397 and 12.901 seconds and execution
costs of 1.773 and 1.032 seconds. Neither certifies. This large variation in
otherwise comparable work prevents attributing all complete-time differences
to arithmetic. One FP32 case reaches its deadline and remains unsuccessful.
All negative and censored outcomes stay in the result ledger.

A second bounded observation immediately after the broad cohort launches no
CUDA workload and records 0% GPU utilization in all 20 management samples,
with no exposed process owner. This describes that observation period only;
it neither establishes uncontended cohort execution nor erases the earlier
47–99% idle-period activity.

Twelve final timelines cover native, FP32, combined FP4x2 and split FP4x2 on
three larger tiled fixtures. Each is bracketed by uninstrumented controls;
all 36 transcripts match their frozen pilot references. The following are
instrumented microseconds per update, averaged over 500 updates. Active time
sums update kernels; gaps are measured within the five 100-update windows.

| Model | FP32 active / gaps | Combined FP4x2 active / gaps | Split FP4x2 active / gaps |
| --- | ---: | ---: | ---: |
| dense257 | 7.450 / 4.809 | 11.142 / 3.178 | 12.900 / 7.570 |
| dense_blocks16385 | 15.338 / 3.080 | 18.530 / 3.971 | 14.753 / 7.750 |
| dense1025 | 9.961 / 2.350 | 19.985 / 4.558 | 14.660 / 7.847 |

Split FP4x2 tile-product launch medians are only 1.824–1.920 microseconds.
The implementation still performs matrix-vector work with an `m16n8k32` MMA:
only K component columns contribute, while K coefficient components require
K MMA instructions. Thus FP4x2 performs 16 times the dense scalar-product
count before sparse padding, with four useful component-dot terms. This is
static work accounting, not a measured throughput ratio or a four-bit-total-
storage claim. High advertised tensor throughput does not translate directly
into useful LP updates.
On dense1025 the two sparse projection/encoding launch medians are 4.576 and
6.336 microseconds. The actual MMA product is no longer the dominant launch.
Split execution exposes 256 tile-product CTAs there; combined execution exposes
only 16/33 CTAs in its two directions on 188 SMs. Those grid sizes bound the
available block parallelism; hardware occupancy is not measured. Combining
work saves launches while lengthening kernels and restricting tile parallelism.

Dense_blocks16385 shows the complementary problem: split FP4 has slightly less
active update-kernel time than FP32, but its extra launch gaps consume that
advantage. Combined FP4 removes approximately half the gaps but increases active
time. Both paths report zero local-memory bytes in these traces; register counts
are 26 for the tile product, 40 for the sparse step and 48 for combined FP4.
These are kernel metadata, not evidence that register pressure has no effect.
Profiler execution ratios range from approximately 0.999 to 1.194 against the
bracketing controls, so timeline durations remain separate from complete costs.

The next general implementation targets follow from these results: distribute
tensor reduction work without forcing all projection work into a small grid;
reduce launch gaps while preserving that parallelism; move frequent original-A
progress/reference work closer to the device; and improve the shared sparse
solver's convergence/preconditioning/restart behavior on the unsuccessful LPs.
Any schedule or precision policy should use measured sparse structure and
progress, not model identity. It must still demonstrate incremental value over
the improved FP32 path and retain the whole broad roster, ordinary single solves,
meaningful accepted FP4 contribution and strict original-model certificates.

## Admission, preservation and resources

The final image is `fast-image-v9`, bound by `fast-admission-v5`. Native
acceptance passes 638 repository Rust and 820 Python tests, replay, dependency
checks, documentation and smoke. The isolated candidate passes 18 Rust tests,
10 Python contracts, Clippy, independent packing and decoded arithmetic checks.
Its main device suite covers 13,824 product outputs, 156 solves and 36 exact
fused/unfused pairs. Additional boundary checks cover 1,540 outputs and seven
solves, including empty rows; split-path checks cover 18 solves and eight
fused/unfused pairs. Main, boundary and split suites all pass memcheck,
racecheck, initcheck and synccheck. The final cached-delta equivalence proof
compares all 444 main admission responses with the preceding image.

Six failed development/admission/reporting reservations retain their source snapshots
and full 3,660 CPU / 90 GPU seconds: three build/lint corrections, one smoke
request without the required GPU lease, the undersized supplemental racecheck
reservation, and an export-script import error. The racecheck attempt retains 12 responses and is not a
complete sanitizer proof. A separately identified unchanged 18-case admission
suite completes racecheck in 127.644 seconds under its prospective 180-second
reservation, with zero reported hazards. No frozen scientific cell is retried.

Large source snapshots and raw responses stay local. The portable delta archive
stores identical bytes once by content hash, with logical paths preserved in its
manifest. An extracted-root replay independently decodes proposals and invokes
the unchanged original serial certificate checker; identical offline witnesses
are deduplicated, without solver answer reuse. Compact results and acceptance
receipts belong in Git. The archive preserves 114,046 logical files
(12,581,367,496 bytes) as 14,920 unique objects (10,743,208,688 bytes), compressed
to 3,248,953,494 bytes across 103 bounded parts. It verifies 82,240 prior archived
scientific files and 207 earlier diagnostic bindings unchanged. This remains a
local research archive; no multi-gigabyte evidence blob is committed. Extracted-
root replay passes all 114,046 byte files, 800 development cells, 1,779 admission
solves, 2,616 probes / 137,676 product outputs, and 14,102 final/intermediate
assessments (3,798 distinct serial witnesses). No new development cells are
missing. Historical missingness remains unchanged. Final validation verifies all
17 numerical source bindings, full failure charges and empty process cleanup.
The settled open allocation checkpoint is **95645.880891480 CPU /
10887.964566891 GPU seconds**, including all earlier charges. The final
documentation/link gate passes; the validation receipt binds both closing jobs.

The existing 240,000 CPU / 30,000 GPU-second allocation remains open. Four CPU
slots, 16 GiB sampled RSS, 12 GiB device buffers, one pinned shared lease, the
one-second supervisor and all 100 ms advisories remain unchanged. Sampled RSS
does not enclose the hard peak. Earlier failures, missing coverage, allocations,
results and criteria remain exact. No confirmation is frozen; public defaults
and publication remain separate.
