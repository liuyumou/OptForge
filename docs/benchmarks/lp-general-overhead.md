# FP4 surrounding-work optimization

Status: optimized image admitted; descriptive development under SPEC-0045 / ADR-0079.
The objective remains a broadly useful single-solve LP solver with meaningful
FP4 acceleration and strict original-model certificates.

## Change and exactness

`fast-image-v10` keeps the Tensor Core product and its reduction order. The
combined kernel gathers reduced outputs into one contiguous warp before FP64
projection, state writes and vector encoding. This removes the former sparse
active-lane projection, a shared-memory handoff and a block barrier. The split
path similarly projects the gathered outputs directly in the encoding layout.
Normal-E2M1 decoding constructs exact binary32 bits instead of indexing a table.
No lower precision is introduced into solver state or certificate authority.

The native and FP32 machine instructions, all four tensor-product kernels and
the 32-lane split kernel remain exactly unchanged: 13 compiled kernel bodies.
All 477 ordinary, boundary and split admission responses match the previous
image exactly after excluding timing and allocated-byte fields. Canonical JSON
comparison preserves signed-zero distinctions. Admission includes independent
decoded products, strict certificates, complete recovery and cancellation, and
all four sanitizers on every changed projection/encoding path. The historical
local-bound backend and public defaults remain unchanged.

## Matched fixed-work development

The frozen pilot has six models, six configurations and four interleaved repeats:
144 cells, each with exactly 500 physical updates. All 48 old/new FP4 transcript
pairs are exact. No pilot solve certifies at 500 updates, so these are execution
measurements, not certified-solve speedups. Ratios below are medians of matched
old/new pairs; times are configuration medians in milliseconds.

| Model | Previous combined FP4x2 | Optimized combined FP4x2 | Execution ratio | Current FP32 | Current split FP4x2 |
| --- | ---: | ---: | ---: | ---: | ---: |
| dense257 | 7.401 | 6.381 | 1.160 | 5.346 | 10.484 |
| dense_blocks16385 | 12.128 | 7.123 | 1.702 | 10.078 | 11.202 |
| dense1025 | 12.021 | 10.520 | 1.143 | 6.426 | 11.519 |

The block-sparse combined path is about 1.415x faster than current FP32 execution.
The other two tiled cases still lose to FP32. Split execution improves 1.084x on
the block-sparse case and is essentially unchanged on the other two. The three
untiled pilot models remain in coverage and contribute zero actual FP4 work.
Matched complete-process ratios for the three combined cases are 0.997, 1.028
and 1.015. Preparation, original-model control/checking and process lifecycle
therefore still dilute arithmetic gains. Four timing repeats quantify local
variability, not independent LP families or population significance.

## Why fusion was slower

Fusion combines launches, but also combines their scheduling constraints. The
old implementation projected with sparse active lanes and handed the outputs
through shared memory before encoding. The new mapping removes that cost. It
now beats the split schedule on all three tiled pilot fixtures; fusion is not
intrinsically slower.

A separate structural limitation remains: dense1025 combined execution exposes
only 16/33 output CTAs, whereas the split product exposes 256 tile CTAs on the
188-SM device. A fused block serializes more tensor work and fixes the same block
layout for tensor products, sparse reduction, projection and encoding. A split
schedule can choose each grid independently, but pays more launches and gaps.
Grid counts bound available block parallelism; hardware occupancy is not measured.
Twelve new timelines retain 36 exact before/trace/after transcripts. The table
shows instrumented microseconds per update (active kernels / within-window gaps):

| Model | FP32 | Combined FP4x2 | Split FP4x2 |
| --- | ---: | ---: | ---: |
| dense257 | 7.412 / 4.848 | 9.658 / 3.577 | 11.986 / 8.474 |
| dense_blocks16385 | 15.386 / 3.031 | 9.966 / 2.326 | 12.577 / 7.893 |
| dense1025 | 9.950 / 2.415 | 18.651 / 1.868 | 13.759 / 8.735 |

Dense1025 combined execution still has more active time than split, but fewer
gaps now make its total lower. Its 16/33 CTAs remain a structural limitation.
The split tensor-product median stays 1.888 microseconds; projection/encoding
medians are 3.808 and 6.176 microseconds. The block-sparse combined directions
fall to 4.864 and 5.120 microseconds per launch. Register metadata remains
26/product, 40/split-step and 48/combined, with zero reported local-memory bytes;
this does not prove a register-pressure or occupancy cause. Profiling changes
execution time by approximately 0.985–1.193x relative to bracketing controls.
Hardware counters remain unavailable. Timeline durations are kept separate from
uninstrumented complete-solve costs.

## Broad single-solve results

The original 176-cell manifest stops in group 16 at its undersized 180-second
resource reservation. It retains 135 responses; its eighth group-16 cell
(FP32, 1e-9) has no endpoint. Seven completed group-16 responses remain, with
all seven timings excluded because their lifecycle job failed. The five
never-started groups run once under a separate source-bound tail manifest,
retaining 40 more responses. No attempted cell is repeated and the original
41 missing response locations are not rewritten. Consolidated distinct-attempt
coverage is 175/176 responses and 168 eligible complete-process timings, across
all 22 models and both strict tiers. The sole interrupted endpoint stays missing.

| Configuration | Certified / 44 planned | Native / candidate complete-cost median | FP32 / candidate complete-cost median |
| --- | ---: | ---: | ---: |
| Native | 20 | 1.000 | — |
| FP32 | 20 | 1.003 | 1.000 |
| Combined FP4x2 | 20 | 1.000 | 0.992 |
| Split FP4x2 | 20 | 0.990 | 0.988 |

Ratios use the 20 jointly certified, fully supervised pairs; values above one
favor the candidate. There is one observation per model/tier/configuration.
Combined and split FP4x2 retain 24.131% and 24.132% accepted FP4 product
shares across their full rosters, including unsuccessful solves; original-reference
work is separate. These small complete-cost differences do not establish statistical superiority
or a population regression. Missingness and shared-device/host timing variability
remain visible. The numerical optimization changes no convergence criterion.

The block-sparse combined FP4 run at 1e-7 accepts 20,000 FP4 updates, reaches its
iteration limit and spends 0.289 seconds in execution versus 3.819 seconds in
assessment, plus 0.329 seconds in preparation. The faster update therefore does
not resolve the general solver's convergence or original-model control/check
cost. Further work should reduce those common costs and preserve tile parallelism
while reducing launch gaps. No model-identity dispatch, prepared-workflow
restriction or native-fallback completion claim is introduced.

## Resources and retained failures

All work uses the existing allocation, four CPU slots, sampled 16 GiB RSS,
12 GiB owned device buffers, pinned shared lease and unchanged one-second
supervision, retaining all 100 ms advisories. Prospectively move 2000 unspent
GPU seconds from development to admission: 8000 admission / 10000 development /
10000 confirmation / 2000 reporting, still 30000 total. CPU caps are unchanged.
Operational receipt v2 binds the revised accounting/readmission sources after
39 supervisor contracts and a supervised CPU workload. Receipt v1 remains exact;
this does not repair any historical missing supervision or scientific cells.

Four failed reservations remain. Two administrative defects are: the initial sanitizer harness has a syntax
error before CUDA execution (880 CPU / 220 GPU seconds charged), and the first
pilot report attempts to overwrite an immutable output (240 CPU seconds charged).
A third failure is the broad group-16 reservation (720 CPU / 180 GPU seconds),
which was sized for four solves although each group has eight plus independent
checking. A fourth is the 90-second offline analysis reservation (360 CPU seconds);
parsing the retained 3.38 GB of response JSON, plus raw copies, needs more time.
Its completed partial summaries remain, and a separate offline reporting identity
has a 600-second reservation. Total failed charges are 2200 CPU / 400 GPU seconds.
All source versions and partial files remain. Corrected admission/reporting use
new identities; no scientific cell is retried. A CLI version-option mismatch also
refuses before reservation and is corrected before operational receipt v2 is
composed. Both successful operational probe versions remain retained.

Large evidence stays local. Compact results and validation receipts are tracked.
This continuation changes no public default, establishes no broad superiority,
and freezes no confirmation or publication decision.


## Delivery evidence

Final native acceptance passes 638 Rust and 821 Python tests, documentation and
smoke; the isolated crate passes 18 Rust tests. The source-bound image admission,
477 exact response comparisons, four scoped sanitizer tools and 36 exact profile
transcripts remain separately bound. [Compact results](lp-general-overhead-results.json)
and [timeline results](lp-general-overhead-profile-results.json) retain all
measurements, negative findings and explicit missingness. Portable delta evidence
and final resource validation are retained locally under `fast-overhead-delivery-v1`.


Portable replay passes from an extracted root: 26632 files, 319 retained study
responses, 281 admission solves, 328 product probes / 21524 outputs, and 5796
assessments / 3209 distinct serial witnesses. The original 41 absent response
locations remain explicit; 40 belong to never-started groups covered once in
the separate tail, leaving one genuinely missing endpoint. The archive verifies
113490 prior file bindings exactly. Its 1.748 GB compressed payload stays local;
the tracked primary results are 0.689 MB. Cleanup is empty. The
[delivery receipt](lp-general-overhead-validation.json) binds sources, resources,
all four failed reservations and portable results. The allocation remains open.

Settled open-allocation checkpoint: 108845.598964180 CPU / 12326.763290488 GPU seconds.
