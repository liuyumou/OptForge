# MIXED2 prepared attribution and GPU storage pilot

The bounded pilot completes under [SPEC-0037](../specifications/SPEC-0037-mixed2-pilot.md)
and [ADR-0070](../decisions/ADR-0070-mixed2-pilot.md). The 1.10x target is now
a provisional adoption criterion requiring workload-value and sample-size
justification before later confirmation. A useful, safe diagnostic pilot does
not require an assumed 1.10x win. All historical criteria and results remain exact.

**Do not integrate this product/guard implementation into a mixed solver.**
FP32 storage is approximately tied at dense128/256 and loses at dense512
(0.876x native product throughput). Including the dense conservative guard
gives only 0.350–0.429x native product throughput across the measured shapes.
This negative result does not depend on choosing 1.10x instead of parity.
Separately, profiling inflates dense complete time by 7.7–9.2x; the actual
uninstrumented matrix fraction remains inconclusive. Both findings are retained.

## Prepared native attribution

All 192 prepared sessions / 576 solves complete across twelve families at the
strict 1e-9 tier: 528 independently checked certificates and 48 intentional
unbounded-direction refusals. Every endpoint, audit, certificate, checkpoint,
recovery and unit of physical work matches the retained original, including
signed zeros. Both variants use the same checker, batching and setup overlap.

| Family | Control complete ms | Control GPU ms | Profile complete / control | Instrumented matrix union ms | Instrumented outer event ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| coupled-equality | 1.495 | 0.449 | 1.036x | 0.000 | 0.000 |
| coupled-inequality | 1.472 | 0.451 | 1.013x | 0.000 | 0.000 |
| dense-generic-128 | 5.221 | 2.963 | 9.173x | 1.365 | 4.854 |
| dense-generic-256 | 8.594 | 3.728 | 7.982x | 2.489 | 6.120 |
| dense-generic-512 | 14.151 | 5.361 | 7.708x | 4.792 | 8.035 |
| dense-rich-65 | 5.764 | 3.380 | 8.466x | 1.213 | 5.301 |
| fixed-active-bounds | 1.473 | 0.451 | 1.002x | 0.000 | 0.000 |
| ill-scaled-coupled | 1.490 | 0.451 | 0.984x | 0.000 | 0.000 |
| ill-scaled-generic-128 | 5.639 | 2.972 | 8.461x | 1.364 | 4.905 |
| infinite-bound-refusal | 0.718 | 0.000 | 0.881x | 0.000 | 0.000 |
| irregular-tail-33 | 1.379 | 0.453 | 1.024x | 0.000 | 0.000 |
| ranged-one-sided | 1.434 | 0.452 | 1.009x | 0.000 | 0.000 |

Each entry is the median of eight block values; within a session complete
and event costs are means of all three fresh solves. Profile matrix costs
are interval unions across concurrently active CTAs, divided by three solves.
The machine record retains all eight values, ranges, setup, teardown and
separate CUDA kernel events/CTA unions. Zeros on sparse nativefast paths mean
**unattributed**, not free matrix work. Instrumentation adds per-launch events,
timestamp stores, readback and durable diagnostic logging. Its measured
disturbance prevents interpreting these matrix durations as exact durations
of the uninstrumented control. No subtraction claims to remove that bias.
Compiler resource reports show 39 registers and 2048 bytes shared memory
for both native kernels, with no spills. That observation does not rule out
instruction/scheduling perturbation. Both product kernels use 40 registers
and 2048 bytes shared memory; the guard uses 40 registers and 4096 bytes.
The control is this new package’s wrapper around retained native kernels;
its timings are not interchangeable with historical DELIVERY4 samples.

The device global timer is a target-specific facility intended for NVIDIA
tools; its semantics are not a portable timing guarantee.
[PTX documentation](https://docs.nvidia.com/cuda/parallel-thread-execution/index.html#special-registers-globaltimer-globaltimer-lo-globaltimer-hi).
The product timer probes retain every timestamp. Their minimum positive
read-to-read spacing is 32 ns in every family/direction summary; this is
an observed spacing, not a guaranteed hardware resolution.
Software spans omit scheduling outside their first/last CTA and are not
interchangeable with enclosing CUDA events or complete delivery.

## FP32 storage products and conservative guard

The independent 192-cell product cohort uses original unscaled matrices,
both directions, fixed generic nonzero vectors and 128 launches per cell.
FP64 and FP32 storage use identical FP64 FMA/reduction schedules. These
product kernels differ from the retained solver’s separate multiply/add
schedule; this microprobe is not a drop-in solver comparison.

| Family / direction | FP64 μs | FP32 μs | Guard μs | FP64 / FP32 | FP64 / (FP32 + guard) |
| --- | ---: | ---: | ---: | ---: | ---: |
| dense-generic-128 / A | 6.180 | 6.182 | 8.242 | 1.000x | 0.428x |
| dense-generic-128 / transpose | 6.184 | 6.185 | 8.243 | 1.001x | 0.429x |
| dense-generic-256 / A | 8.244 | 8.246 | 14.384 | 1.000x | 0.364x |
| dense-generic-256 / transpose | 8.245 | 8.246 | 14.384 | 1.000x | 0.364x |
| dense-generic-512 / A | 14.389 | 16.420 | 24.629 | 0.876x | 0.351x |
| dense-generic-512 / transpose | 14.388 | 16.422 | 24.634 | 0.876x | 0.350x |
| irregular-tail-33 / A | 4.134 | 4.137 | 6.189 | 1.000x | 0.400x |
| irregular-tail-33 / transpose | 4.130 | 4.133 | 6.191 | 0.999x | 0.400x |

Costs divide the measured stream-batch event by 128; host launch gaps remain
inside that boundary. Marginal medians do not add; ratios are formed within
each block first. These are descriptive observations, not simultaneous
confidence bounds, statistical power or retained solver speedups.

The guard encloses representation error plus FP64 FMA/tree rounding and
subnormal allowances using upward arithmetic. Independent rational original
dots check 14864 study outputs; independent rational FMA
schedule replay checks both product outputs, including padding. Admission
also covers FP32 subnormals, binary64 underflow, cancellation and edge shapes.
There is no approximate final certificate or FP32 iterative state.

| Family / direction | All representations μs | FP32 allocation/upload μs | Error allocation/upload μs | Output readback μs |
| --- | ---: | ---: | ---: | ---: |
| dense-generic-128 / A | 488.3 | 34.6 | 53.7 | 10.5 |
| dense-generic-128 / transpose | 485.4 | 34.9 | 52.1 | 10.4 |
| dense-generic-256 / A | 2000.2 | 90.7 | 240.6 | 10.5 |
| dense-generic-256 / transpose | 2050.4 | 92.6 | 248.0 | 10.7 |
| dense-generic-512 / A | 13559.2 | 431.9 | 701.9 | 11.2 |
| dense-generic-512 / transpose | 13240.1 | 414.6 | 698.2 | 11.2 |
| irregular-tail-33 / A | 73.9 | 24.4 | 38.6 | 10.0 |
| irregular-tail-33 / transpose | 72.2 | 25.1 | 39.8 | 10.0 |

Representation timing constructs FP64, FP32 and error arrays together;
the incremental CPU packing cost versus an existing native representation
is not identified. CPU oracle time is measured separately and excluded from
that representation span. Transfer spans include allocation and synchronization.
With retained FP64 coefficients, both-direction FP32 storage plus a dense
FP64 error array raises coefficient-buffer storage to 2.5 times native alone.
These costs must be amortized explicitly; 128 launches are not 128 solves.
The machine record includes 1/128/4096-product scenarios with and without
per-product host readback. They charge all measured representation work and
FP32/error allocation/upload once, and product plus guard on every call.
That is a conservative assignment of packing cost, not an identified
incremental cost. The resident case excludes an unimplemented device policy.
These are conditional product scenarios, not LP-solver forecasts.

## Implications and limits

Whole-event 2x/removal forecasts remain optimistic sensitivity cases in the
[machine analysis](data/mixed2-pilot-analysis-v1.json). They assume unchanged
work and zero added cost; actual matrix-only complete benefit is not identified
by disturbed software profiling. Prepared sessions are appropriate for further
cost questions; the historical 1.010266x ideal cold upper bound remains exact.
Separate lifecycle forecasts amortize measured setup/teardown over 1, 3 and
100 native solves while hypothetically halving all GPU event time. They keep
the zero-added-cost assumption explicit and do not identify matrix-only gains.
The prior measured context costs and unresolved outer latency remain in the
[MIXED2 CPU report](lp-mixed2.md) and [DELIVERY4 report](lp-delivery4.md).

Useful mixed windows, convergence, work amplification, rollback/correction
cost and final full-solver performance remain unmeasured. Eight ordered blocks
on a shared device do not establish independent production performance.
No family is removed, no public default is selected and GPUP-8 stays incomplete.
A later numerical solver study needs its own cost case, fixed useful-work
criteria, resource manifest and workload-value/sample-size justification.
Priorities from this pilot are a less intrusive attribution method and a
cheaper guard/representation design with a measured component benefit.
Cached coefficient-error norms with vector norms are a possible cheaper but
looser enclosure to investigate, not an admitted implementation or speed claim.
No full-solver confirmation is justified by these product results.

## Reproduction and acceptance

`python3 -B tools/lp_mixed2_pilot_analysis.py verify` reproduces all cells,
numeric checks and summaries from the [portable archive](data/mixed2-pilot-records-v1.json.gz).
Replay requires Python and repository validation dependencies, but no CUDA,
executable or original artifacts tree. Admission evidence and exact source
bindings are in [acceptance](data/mixed2-pilot-acceptance-v1.json).

The new image passes memcheck, racecheck, initcheck and synccheck, with
nonzero error exits enforced. These are scoped admission runs, not a guarantee
for untested inputs. [Compute Sanitizer documentation](https://docs.nvidia.com/compute-sanitizer/ComputeSanitizer/index.html).
The repository gate passes 638 Rust / 694 Python tests, native replay, dependency,
artifact, documentation and smoke checks. The isolated crate passes 30 Rust
tests; 204 fresh CPU assessments reproduce 102 retained serial endpoints,
48 representation comparisons and 21 process/configuration cases.

The independent allocation is 48000 CPU / 2400 GPU seconds, with four CPUs,
16 GiB sampled RSS, a pinned shared GPU lease and the unchanged supervisor.
All failed reservations, source versions and cleanup are retained in
[accounting](data/mixed2-pilot-accounting-v1.json). No historical budget transfer,
scientific retry, public default, follow-on solver allocation or GPUP-9 release.
Three development failures retain full charges: an ambiguous Rust buffer
element type (1440 CPU seconds), the expected pre-CUDA missing-model exit
misclassified as a missing sanitizer summary (600 CPU / 150 GPU seconds),
and a reporting-script bracket typo (360 CPU seconds). Corrected versions
pass. The sanitizer exception is exact and limited to that pre-CUDA refusal;
it does not waive any executed kernel check. No scientific cell was retried.
Commit locally only.

Closed charge: **7288.301963996 CPU / 553.262778531 GPU seconds**, including 128 closing CPU seconds; 3 failed reservations retained. All cleanup is empty.

Final preservation: 1862 historical files and all prior backlog entries remain exact; isolated portable replay passed.
