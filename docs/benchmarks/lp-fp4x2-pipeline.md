# FP4x2 PDLP component diagnosis and parallel assessment

The CPU follow-up improves certificate scheduling and removes redundant host
storage and serial waits in the original-array FP4x2 PDLP implementation. The
final CPU component comparison is **2.254x faster for long columns and 2.198x
for uneven columns**, with exact certificate bits. GPU correctness, complete
solver performance and default promotion remain pending. All five overhead
options default off. No GPU job or monitor ran in this continuation.

This extends [the initial overhead implementation](lp-fp4x2-overhead.md), commit
`0e59839`, under [amendment 95](../specifications/SPEC-0046-amendment-95.md).
All 472 protected PR #30, shared Rust and CUDA-interface sources remain exact,
as do the original preparation, packing, advancement and assessment kernels.
The pricing algorithm and public defaults are unchanged. Source preservation
establishes isolation, not a new pricing performance measurement.

## Where complete time goes

The diagnosis reads the retained, source-bound
[exclusive phase CSV](lp-billion-gpu-control-phases.csv). It does not repeat any
historical LP or infer GPU utilization from elapsed time. The image-v11 coupled
billion-nonzero run performed 75% accepted FP4 work, returned an **uncertified
iteration limit**, and cost 371.998892732 complete seconds:

| Component | Seconds | Complete share |
| --- | ---: | ---: |
| Independent cold final proof | 132.358 | 35.6% |
| Input hashing, validation and original CSR-to-CSC construction | 100.017 | 26.9% |
| In-solve strict certificates | 67.101 | 18.0% |
| Engine preparation | 21.953 | 5.9% |
| FP4 packing | 12.081 | 3.2% |
| Device setup | 11.992 | 3.2% |
| Device advancement | 8.190 | 2.2% |
| All other exclusive phases | 18.307 | 4.9% |

Input and the two proof phases account for 80.5% of this complete cost.
Advancement is measured host wall time, not kernel-active GPU time. The other
timing-eligible billion cases mainly use FP32 fallback; their cold proof shares
are 31.7–36.7% and strict certificate shares 15.3–21.7%. The 64M coupled case
similarly costs 18.013 seconds, including 7.724 cold proof, 3.611 input and 2.736
strict certificate seconds. These descriptive, unequal-work results do not
establish a new end-to-end speedup. The prior missing-wide response and every
uncertified outcome remain in the [original report](lp-billion.md).

## Component review and implementation

| Component | Decision and implementation |
| --- | --- |
| Input integrity and original sparse construction | Retain hash/domain validation and original CSR/CSC authority. These are substantial remaining costs; no unchecked model cache is introduced. |
| Preparation and packing | Preserve the earlier solve-owned resident-buffer transfer, packed-fragment reuse and zero-eligible fast path. Host mirrors, capacity checks, long-line fallbacks and original kernels remain. GPU admission is pending. |
| Device setup and advancement | Retain exact existing kernels, scratch initialization and recovery/reference behavior. No unmeasured kernel rewrite is included. |
| Control snapshots | New `host_state_reuse` refreshes all state fields with reusable vector capacity. Release snapshot capacity before final assessment. Rollback retains physical work, generation changes and the original deadline. |
| Endpoint downloads | Download directly into existing controller slices, removing temporary vectors and the following host copies. Preserve dimensions and existing synchronized device-copy semantics. |
| CPU dual proof | Partition heavy/skewed CSC work by nonzeros plus column count, keeping each column and its reduction order intact. Workers write disjoint canonical output slices; remove intermediate term copies and redundant initialization on reuse. |
| Balanced CPU proof | Call the complete, unchanged previous workspace routine. A structural selector uses weighted work only for sufficiently heavy few-column or uneven-column cases. Retain only the selected strategy's allocations. |
| Assessment concurrency | Run the original CPU dual proof while the caller performs GPU feasibility, original objective calculation and witness output on the same immutable snapshot. Reserve at most three proof workers plus the caller. CUDA stays on its context thread; join before acceptance or another PDLP update. |
| Feasibility and dual repair | Workspace-enabled CPU fallback uses work-weighted CSR partitions. Start it only after the dual team joins. Repair changes only the dual, so reuse the primal diagnostic, recompute the dual proof/gap, and retain original CPU confirmation before acceptance. |
| Endpoint publication | Reuse an already-published final witness only when the existing assessment identity permits final reuse. Deadline/cancellation/recovery tails remain conservative. Publish repaired dual output only after the snapshot writer joins. |
| Independent audits | Retain every required intermediate audit and independent cold final proof, including original-model strict 1e-9 acceptance. This remains the largest unoptimized component in the cited run. |

The selector is structural: use weighted columns when there are fewer than
4096 columns with at least 16384 estimated terms, or the largest uniform worker
partition exceeds 1.5 times average work. Small and single-worker cases retain
the previous routine. No family identity, certificate tolerance or benchmark
timing enters dispatch. Flags and prerequisites are documented in the
[executor README](../../research/lp-billion-lowbit/README.md).

## Correctness before measurement

Final source-bound CPU admission `fp4x2-pipeline-quality-v4` passes formatting,
**79 Rust tests**, Clippy with warnings denied and release builds. The scalar
certificate differential fixture now covers 720 cases at one, three and four
workspace workers: **2,160 exact comparisons**, including refusal, repair,
underflow and cancellation-sensitive reduction cases. Additional tests cover
ordered first refusal, overwriting scratch after failure, complete partition
coverage, bitwise checkpoint/restore including signed zero, stable allocations,
foreign-checkpoint rejection and unchanged consumed work/deadlines.

Assessment tests exercise caller-thread non-Send callbacks, CPU fallback,
repaired duals, false GPU acceptance rejection, errors and joined completion.
The final balanced implementation is byte-identical to the previous retained
workspace source. The benchmark fixture's previous workspace body is also
verified against that source. Strict original-model 1e-9 checks and default
control100/certificate500 remain unchanged.

The reporting gate additionally checks the source-only FP4x2 harness, all
documentation pages/local links and whitespace. Its exact logs and settlement
are retained under `fp4x2-pipeline-report-v1`.

## CPU comparison, including rejected implementations

Each comparison uses four fresh 1,048,576-nonzero shapes, three fresh seeds per
shape and six rotated repetitions per seed. Every returned certificate matches
the original bounded checker bit for bit. Reported ratios are the median of the
three seed medians of per-repetition old-time/new-time ratios. Values below one
regress. First calls include workspace allocation; later calls reuse capacity.
Caches are not flushed, and these are synthetic component measurements.

| Final v4 shape | Previous 4 / new 4 workers | Previous 4 / new 3 workers | Previous / new retained bytes (4 workers) |
| --- | ---: | ---: | ---: |
| Short columns | 1.060x | 0.927x | 3,999,616 / 3,999,616 |
| Balanced | 1.031x | 0.846x | 548,864 / 548,864 |
| Long columns | 2.254x | 2.163x | 753,664 / 661,552 |
| Uneven columns | 2.198x | 2.075x | 1,148,032 / 851,992 |

Balanced and short-column paths retain the old routine; their small median
differences are not evidence of an arithmetic speedup. One short-column seed
regresses to 0.927x. Three workers regress on both balanced shapes, so useful
GPU/output overlap must offset that loss before overlap can improve complete
solver time. Long/uneven retained capacity falls by 12.2%/25.8%, respectively;
this is workspace capacity, not total process memory.

| Retained comparison | Short | Balanced | Long | Uneven |
| --- | ---: | ---: | ---: | ---: |
| v1, comparison-context confound | 0.846x | 0.643x | 1.601x | 1.519x |
| v2, both implementations compiled together | 0.925x | 0.887x | 1.816x | 1.596x |
| v3, staging inside a combined routine | 0.858x | 0.673x | 1.613x | 1.610x |
| v4, complete previous routine on balanced work | 1.060x | 1.031x | 2.254x | 2.198x |

The first comparison compiled the baseline locally and the candidate through
the external library. It is retained with that confound and excluded from
promotion evidence. Subsequent comparisons compile both exact source bodies
in the same crate. v2/v3 regressions prompted the structural selection and full
balanced-routine restoration; none is hidden or relabeled. Different fresh
seeds and execution times also limit comparisons between versions.

[Compact evidence and all raw samples](lp-fp4x2-pipeline-results.json) preserve
all four comparisons, the complete diagnosis, source bindings, CPU quality
receipt, final sealed image and every completed reservation, including failures.

## Resource accounting and remaining GPU gate

Before the final reporting reservation, this continuation consumes
**2767.800319760 CPU seconds and zero GPU seconds**: 1829.215832516 implementation,
452.173957404 native, 72.068489824 CPU admission, 292.113949988 development and
122.228090028 reporting. Both initial compile failures retain their full
480-second charges, **960 CPU seconds total**. Every completed reservation has
empty cleanup and no overrun. The final reporting reservation is listed
separately in compact evidence until its settlement supplies the actual charge.

All work stays within the existing 570000 CPU / 68000 GPU totals, exact phase
caps, four slots and 16 GiB host reservation. Native headroom fell below the
minimum asynchronous reservation after three native gates; the prospective
final gate therefore uses the existing CPU admission phase. No historical
charge, phase cap or total was changed. Only this reporting job's generated
HTML is removed; all small evidence, images and failed attempts remain.

`image-fp4x2-pipeline-v2` binds final quality v4 and is labeled
**CPU_quality_only**. The earlier v1 seal binds quality v3 and remains historical.
The guarded future correctness action covers all **32 combinations** of the five
flags, exact continuations, recovery/deadlines, independent checks and four
sanitizers. It has not run and needs fresh sustained-idle/resource admission.
No GPU availability is inferred from old observations.

GPU correctness must precede complete-cost benchmarking and PR #30 performance
checks. The existing promotion rule still requires unchanged certificate
coverage, at least 5% median complete improvement, no family above 5% median
regression and no resource-limit regression across fresh, audited comparisons.
CPU component gains alone do not satisfy that rule; defaults remain unchanged.
