# LP preparation and control overhead

Development continuation under [SPEC-0045](../specifications/SPEC-0045-general-lowbit-lp.md),
2026-11-19. Public defaults and the fast-image-v10 CUDA image remain unchanged.

The changes reduce shared overhead, but broad FP4 complete-solve superiority
remains unestablished. The first implementation reduces the jointly certified
lower-scale complete-cost median by about 2.8%. The final indexed constructor
adds about 2.4% at lower scale and 1.6% on the limited 16 M extension, measured
in separate paired cohorts. Coarser control increases work and regresses total
time, so the 100-update cadence is retained. All five cohorts complete 150/150
measurements; failures and uncertified outcomes remain visible below.

## Implementation

Scale-image-v12 gathers original FP64 products directly into the original
1024-leaf reduction tree. Short segments retain signed-zero normalization;
nonfinite products retain the full original fallback. This removes the separate
product-vector construction, finite scan and scratch copy. The prior rejected
in-place reduction implementation remains historical and is not reused.

Spectral preparation and control use bounded scoped workers: three helpers plus
the calling thread, under the same four-slot allocation and existing CPU
placement. Matrix storage is borrowed. Input, output, partial-reduction and
projection buffers are reused within one solve. Workers are parked between
products and joined before the call returns. There is no cross-solve answer or
prepared-model cache. Complete process costs include worker shutdown.

Independent canonical FP4 tiles are quantized in parallel when at least 128
tiles exist. Row and column fragment construction can also run concurrently.
Canonical order, component encoding, sparse remainders, both orientations and
tail dimensions remain exact. No new matrix padding is introduced.

## Protocol

The first frozen cohort compares scale-image-v12 with scale-image-v9 on all six
connected 1 M structural families (seed 831001) and public square31/scpm1.
Native, FP32 and FP4x2 each run in fresh processes, once per version and model,
in rotated order. Requests use 20000 updates, strict 1e-9 certificates every
500 updates, control every 100 updates and a 15-second internal solve limit.
There are 48 planned cells. Deadline differences remain explicit. Equal-work
claims require exact numerical transcripts.

The primary complete cost includes process startup, preparation, device setup,
execution, control, strict certification, response transport, independent final
original-model checking and owned teardown. Intermediate-history audits and
compression are separately measured and charged. The assessment partition also
contains certificate work, continuation and device reset; it is not an isolated
control timer. Individual changes have no separate causal timing attribution.

The second cohort evaluates the existing opt-in 500-update control setting,
aligned with certificate checks, on the same eight models and three lanes.
This is a numerical configuration experiment: restart timing and work may change.
Strict certificate criteria and the CUDA image do not change. The comparison
against the preceding 100-update cohort is noncontemporaneous; comparisons among
native, FP32 and FP4 in this new cohort share its timing environment. Neither
cohort is confirmation or a universal FP4 performance claim.

## Implementation-only results

The [complete comparison](lp-general-prep-control-results.json) retains 48/48
measurements. Each version/lane certifies the same five of eight models.
All 21 pairs without deadlines have exact complete numerical transcripts;
446 common intermediate assessments match across all 24 pairs. All six scpm1
observations hit the 15-second solver deadline without certification; their
unequal-work timings do not establish successful-solve gains.

Across the 21 exact pairs, descriptive old/new medians are 1.058 for preparation,
1.075 for assessment, 1.006 for execution and 1.030 for complete cost. Preparation
and assessment therefore fall about 5.5% and 7.0%. Among the 15 jointly certified
pairs, the complete-cost median is 1.029, or about 2.8% less time.

The coupled FP4 solve falls from 1.377 to 1.335 seconds, with the same 2500
updates and 75% accepted FP4 product work. Its preparation falls from 312 to
274 ms and assessment from 285 to 271 ms. The candidate native solve takes
1.331 seconds: the implementation changes alone do not establish an incremental
FP4 complete-time advantage on this case. Other certified FP4-configured
families have no eligible tensor work. The public and ill-scaled nonconvergence
outcomes remain explicit.

## Control-cadence results at 1 M / public scale

The [separate control cohort](lp-general-prep-control-control-results.json)
completes 24/24 cells. Both settings certify 15/24 cells, the same five models
per lane. Among jointly certified observations, the descriptive 100/500-update
complete-cost median is 0.928: the 500-update setting is about 7.7% slower.
This comparison uses successive cohorts, so its timing contrasts remain
noncontemporaneous development evidence.

| Family / model | Median 100/500 complete-cost ratio | Accepted updates, 100 → 500 |
| --- | ---: | --- |
| Irregular | 1.206 | 19000 → 17500 |
| Wide | 0.820 | 1500 → 3000 |
| Tall | 0.893 | 1000 → 2500 |
| Coupled | 0.946 | 2500 → 4000; FP4 → 4500 |
| Ill-scaled, uncertified | 1.117 | 20000 → 20000 |
| Degenerate | 0.960 | 2000 → 3000 |
| square31, uncertified | 1.250 | 20000 → 20000 |
| scpm1, all deadlines | 0.972 | Unequal work, no successful-solve claim |

Ratios above one favor the 500-update setting. Fewer control evaluations often
come with more updates and more certificate snapshots. The coupled FP4 solve is
essentially flat (1.335 → 1.340 seconds), while native rises from 1.331 to 1.461.
Thus the within-500-update FP4/native ratio is not an improvement over the faster
100-update native configuration. No default cadence change is justified by this
cohort. Faster uncertified limit runs remain separate from successful-solve value.

## Scale extension protocol

The frozen 16 M extension includes seed 831001 of both capacity-admitted
families, tall and coupled. It runs all three lanes with v9/100-update control,
v12/100-update control and v12/500-update control: 18 contemporaneous cells.
Each has a 20000-update cap, 500-update certificates and a 30-second solver limit.
Full memory allowances, including output and independent history checking, are
13.88 GiB for tall and 7.46 GiB for coupled, below the unchanged admitted bounds.
These are preflight allowances, not measured hard peak enclosures.

The twelve historically unsupported models and four other capacity-admitted
models not measured in this extension remain explicit in its freeze. This
limited scale diagnosis supplements the full eight-model lower-scale comparison.

All [18 measurements](lp-general-prep-control-large-results.json) complete with
strict certificates. The six v9/v12 source pairs retain exact transcripts and
have a descriptive complete-cost median of 1.011, about 1.1% less time. The
coupled FP4 solve falls from 20.074 to 19.785 seconds, but v12 native takes
19.814 seconds: their complete times are effectively tied despite FP4 execution
taking 0.313 seconds versus native's 1.664 seconds. Coupled FP4 preparation still
takes 6.382 seconds and its assessment partition 5.698 seconds.

The [contemporaneous control comparison](lp-general-prep-control-large-control-results.json)
also certifies all six pairs. Its 100/500-update complete-cost median is 0.933,
about 7.1% more time with the coarser setting. Coupled FP4 rises to 20.660 seconds
and 4500 updates, from 19.785 seconds and 2500 updates. The small implementation
gain and negative cadence result are retained; neither establishes meaningful
incremental FP4 complete-time superiority.

## Final indexed preparation candidate

Scale-image-v14 additionally uses a checked direct variable-ID lookup when
building the original sparse program and deriving implied bounds. Arbitrary IDs
retain binary lookup. Sparse compression, arithmetic order, geometry, objectives,
bounds, error behavior and the 100-update control cadence remain unchanged.

The constructor lives in an isolated host crate. Its program-construction source
is a bound derivative; other host modules are reused by explicit source paths.
All public source files remain byte-exact. The first indexed candidate's additive
public-file method passed isolated arithmetic but failed historical whole-file
preservation checks. Its failed native gate and 2800 CPU-second charge are
retained, the public file was restored exactly, and none of those checks changed.

The final eight-model comparison freezes v12 versus v14 at 100-update control,
500-update certificates, 20000 updates and 10-second solve limits. It retains all
48 model/lane/version cells and makes no claim from deadline-limited unequal
work. The final scale comparison passes full remaining-capacity preflight and
uses the same two 16 M representatives, all three lanes and 30-second limits.

The [final lower-scale comparison](lp-general-prep-control-indexed-results.json)
completes 48/48 measurements. Each version/lane again certifies five of eight
models. All 18 pairs without deadlines retain exact full numerical transcripts;
410 common intermediate assessments match across all 24 pairs. Both public
models reach the shorter 10-second limit without certificates; these six pairs
remain excluded from successful-solve and equal-work timing claims.

Across the 18 exact pairs, descriptive v12/v14 medians are 1.073 for preparation,
1.001 for assessment and 1.023 for complete cost. Preparation falls about 6.8%;
the 15 jointly certified pairs take about 2.4% less complete time (ratio 1.024).
The wide and ill-scaled family medians regress slightly, to ratios 0.992 and
0.993; the latter family remains uncertified. These results are retained.

The paired coupled FP4 solve takes 1.255 → 1.225 seconds, with preparation
255 → 239 ms, unchanged 2500 updates and 75% accepted FP4 product work. In this
cohort v14 native and FP32 take 1.313 and 1.260 seconds. These individual
observations favor FP4, but one rotated repetition on one coupled construction
does not establish repeatable broad value. The earlier v9/v12 and current
v12/v14 cohorts are separate; their median gains must not be multiplied into
a claimed cumulative speedup.

The [final 16 M comparison](lp-general-prep-control-indexed-large-results.json)
completes 12/12 measurements, all certified. All six v12/v14 pairs retain exact
transcripts and 21 common assessments. Descriptive preparation and complete-cost
ratios are 1.055 and 1.016, about 5.2% and 1.6% less time. Coupled FP32 regresses
slightly (19.891 → 19.917 seconds); the other five pairs improve.

| Coupled case | Previous FP4 total | Final FP4 total | Final native total | Final FP32 total |
| --- | ---: | ---: | ---: | ---: |
| 1 M | 1.255 s | 1.225 s | 1.313 s | 1.260 s |
| 16 M | 19.650 s | 19.263 s | 20.119 s | 19.917 s |

Both final FP4 cases retain 2500 updates and 75% accepted FP4 product work. At
16 M, FP4 execution is 0.314 seconds versus native's 1.666, while complete time
is only 4.3% lower. FP4 preparation is 6.102 seconds, assessment 5.571 and
independent final checking 4.334; together these account for about 83% of total
time. The indexed candidate's coupled FP4 preparation reduction itself is only
0.052 seconds. Other cost partitions fluctuate too; the complete difference
cannot be attributed solely to that constructor. Original-model host products,
assessment, input/output work and general convergence remain important targets.
The tall family contributes no FP4 product work. The twelve capacity refusals,
four other unmeasured admitted models and full lower-scale roster remain explicit.

## Acceptance and preservation

The first source passes 39 isolated Rust tests; the final isolated indexed source
passes 40, including dense, sparse and maximum-u32 IDs, both objective senses
and exact discrete-model refusals. Each passes 17 related Python tests,
24 compact/JSON equivalence comparisons, 32 original host preparation/product
probes and 60 cached-checker endpoint comparisons. New probes cover every short
reduction size, segment boundaries, cancellation, signed zero, subnormals,
nonfinite products, changed/repeated weights, both packing orientations, tails,
all component counts and both fragment formats.

Each admitted image passes all 60 exact GPU continuation/recovery/cancellation
comparisons. Memcheck, racecheck, initcheck and synccheck each pass the existing
20-case scoped suite for each image.
The final isolated source has fresh full acceptance: 638 Rust / 827 Python tests,
committed-record replay, documentation and historical preservation checks.
Historical source, results, public defaults and CUDA remain unchanged.
The original full lower-scale rosters and 16 M capacity refusals
remain applicable; one generated model per family does not establish broad
generalization, and fresh processes do not imply flushed caches.

The missing-toolchain-wrapper reservation, subsequent lint-only build failure
and rejected additive public-file candidate retain source snapshots and full
1800 / 1200 / 2800 CPU-second charges, zero GPU. No scientific cohort cell ran
in these reservations. Corrected admission uses fresh identities; no attempted
scientific cell is retried. Both operational readmission probes pass the same
39 supervision contracts with unchanged enforcement.

The first packaging reservation also fails before writing archive parts because
of an incorrect path-construction expression. Its sources and full 2400
CPU-second charge remain retained. Corrected packaging uses a new identity and
does not rerun any scientific measurement. The four failed reservations retain
8200 CPU seconds in total, zero GPU.

## Reproduction and resources

`tools/lp_general_prep_control.py` implements source-bound device admission,
frozen requests, the separate control-cadence admission and complete reports.
`tools/lp_general_scale_bench.py campaign` runs the frozen cohorts through the
existing supervisor and pinned lease. `tools/lp_general_prep_control_archive.py`
packages local evidence and runs the original serial checker from an extracted
root. Large evidence stays local; compact results are tracked.

The independent 240000 CPU / 30000 GPU-second allocation remains open. Unspent
phase capacity was prospectively moved to the final development/native work:
CPU caps are implementation 20000, native 35000, admission 48000, development
92000, confirmation 0, reporting 41000 and cleanup 4000 seconds; GPU caps are
admission 8150, development 21850, confirmation/reporting 0. Operational receipts
v7/v8 bind the changes without revising any prior charge. Four CPU slots,
16 GiB sampled RSS, 12 GiB owned device buffers, one-second supervision and all
100 ms advisories remain unchanged. Public adoption and publication remain separate.

## Portable delivery

The corrected local archive contains 25843 files in 26 parts (2254045872
compressed bytes). It verifies all 19520 checked scientific file bindings from
the previous host-cost delivery. Earlier preservation receipts remain retained;
this is a delta verification, not a fresh direct rehash of every ancestor archive.
All five cohorts, admitted and rejected sources, failure receipts and original
inputs are retained. Packaging and closing receipts are bound separately from
the archived report version in the final delivery validation.

Extracted-root replay passes all 150 campaign responses, 302 admission responses
and 3294 assessments, including 846 distinct original serial witnesses. There
are no missing, partial or raw-only responses in this delivery. The 69 chunked
streams reconstruct all 4107248883 original bytes exactly. Public defaults and
scientific criteria remain unchanged; broad repeatable FP4 value remains open.

[Delivery validation](lp-general-prep-control-validation.json) binds the final
source, image, imports, resource settlements, archive, replay and closing checks.

Open settled checkpoint: 222683.436386676 CPU / 29019.968674596 GPU seconds.
