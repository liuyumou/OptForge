# MIXED2 FP4 tensor implementation and larger-scale evaluation

Implemented the tensor-core approach in an isolated research executor under
[SPEC-0038](../specifications/SPEC-0038-mixed2-fp4.md) and
[ADR-0071](../decisions/ADR-0071-mixed2-fp4.md). FP4 computes matrix increments;
persistent state, original-matrix references, recovery and final authority
remain high precision. Public solver defaults are unchanged.

Available strict pairs with descriptive intervals above parity: dense-coupled-1024, dense-coupled-2048, dense-generic-1024, dense-generic-2048, dense-generic-512.
Available strict pairs with descriptive intervals below parity: coupled-equality, coupled-inequality, dense-generic-128, dense-generic-256, dense-rich-65, fixed-active-bounds, ill-scaled-coupled, ill-scaled-generic-128, irregular-tail-33, ranged-one-sided.
Retain native for small workloads; this does not support a broad FP4 replacement.

The planned 32-block confirmation is **incomplete**. It retains **1000 complete sessions / 6006 retained solve responses**:
**5634 original-model certificates and 372 intentional refusals**.
There are 6000 solves in completed sessions and 6 retained response files from an interrupted session whose teardown did not complete.
Block 26 of 32 was stopped for a lost coordinator heartbeat. The 25 prior and
six untouched later blocks completed; the failed block was never retried.
Its eight completed sessions and six further retained response files remain visible;
The six response files are complete and independently rechecked, but there is
no receipt proving their original delivery fsync/EOF boundary completed. The
raw machine ledger uses the term durable for retained files; it must not be
interpreted as a completed original delivery-time measurement.
23 later sessions in that failed block were not executed. The full frozen
coverage requirement fails, so no confirmation, retention or adoption pass is claimed.
The study includes sixteen families, both 1e-7 and 1e-9 tiers, and dense1024/2048
full solves. Dense2048 has 16 times as many coefficients as dense512.
The coupled large cases add a fixed 0.5 cyclic coupling and require longer
trajectories. Known primal/dual construction forms these models but never
initializes the solver. These constructed workloads do not establish
performance on arbitrary production LPs.

## Complete prepared performance

Table entries use every available complete pair (31 or 32 per family); each session has three
solves at each tier. Native uses 32-update windows; FP4 x2 uses 16-update
original-reference windows. Both use fixed maximum-200 audits, cached initial
observations and the same improved independent checker. Every output is
durable before its complete-time boundary. Setup, preparation, EOF, destruction
and log durability are additionally charged in measured six-solve sessions.
The session bookkeeping JSON is outside the delivered-solution boundary.

| Family | Tier | Pairs | Native ms | FP4 ms | Descriptive paired speedup [interval] | Saved ms | Native / FP4 updates |
| --- | --- | ---: | ---: | ---: | --- | ---: | --- |
| coupled-equality | 1e-7 | 31 | 3.310 | 4.957 | 0.665 [0.656, 0.694] | -1.667 | [200] / [200] |
| coupled-equality | 1e-9 | 31 | 3.220 | 4.916 | 0.654 [0.648, 0.665] | -1.701 | [200] / [200] |
| coupled-inequality | 1e-7 | 31 | 3.285 | 5.002 | 0.661 [0.649, 0.674] | -1.684 | [200] / [200] |
| coupled-inequality | 1e-9 | 31 | 3.225 | 4.923 | 0.656 [0.645, 0.662] | -1.695 | [200] / [200] |
| dense-coupled-1024 | 1e-7 | 32 | 93.141 | 83.336 | 1.127 [1.109, 1.156] | 10.049 | [600] / [600] |
| dense-coupled-1024 | 1e-9 | 32 | 122.389 | 109.434 | 1.122 [1.109, 1.164] | 12.871 | [800] / [800] |
| dense-coupled-2048 | 1e-7 | 31 | 291.786 | 268.197 | 1.102 [1.036, 1.131] | 23.429 | [600] / [600] |
| dense-coupled-2048 | 1e-9 | 31 | 389.835 | 357.475 | 1.109 [1.055, 1.136] | 31.906 | [800] / [800] |
| dense-generic-1024 | 1e-7 | 31 | 32.847 | 29.306 | 1.122 [1.066, 1.145] | 3.438 | [200] / [200] |
| dense-generic-1024 | 1e-9 | 31 | 31.331 | 28.316 | 1.130 [1.092, 1.168] | 3.255 | [200] / [200] |
| dense-generic-128 | 1e-7 | 31 | 4.598 | 6.092 | 0.755 [0.709, 0.792] | -1.502 | [200] / [200] |
| dense-generic-128 | 1e-9 | 31 | 4.528 | 6.016 | 0.756 [0.739, 0.781] | -1.454 | [200] / [200] |
| dense-generic-2048 | 1e-7 | 32 | 99.284 | 91.759 | 1.086 [1.033, 1.143] | 7.385 | [200] / [200] |
| dense-generic-2048 | 1e-9 | 32 | 98.111 | 89.813 | 1.120 [1.059, 1.151] | 8.565 | [200] / [200] |
| dense-generic-256 | 1e-7 | 31 | 7.037 | 7.666 | 0.923 [0.878, 0.968] | -0.608 | [200] / [200] |
| dense-generic-256 | 1e-9 | 31 | 6.918 | 7.495 | 0.912 [0.866, 0.962] | -0.659 | [200] / [200] |
| dense-generic-512 | 1e-7 | 31 | 14.169 | 12.941 | 1.109 [1.054, 1.148] | 1.380 | [200] / [200] |
| dense-generic-512 | 1e-9 | 31 | 13.591 | 11.938 | 1.100 [1.069, 1.160] | 1.191 | [200] / [200] |
| dense-rich-65 | 1e-7 | 31 | 3.920 | 6.318 | 0.624 [0.610, 0.633] | -2.382 | [200] / [205] |
| dense-rich-65 | 1e-9 | 31 | 7.383 | 11.543 | 0.642 [0.635, 0.652] | -4.114 | [400] / [405] |
| fixed-active-bounds | 1e-7 | 32 | 3.284 | 4.961 | 0.662 [0.655, 0.670] | -1.677 | [200] / [200] |
| fixed-active-bounds | 1e-9 | 32 | 3.225 | 4.905 | 0.657 [0.652, 0.664] | -1.680 | [200] / [200] |
| ill-scaled-coupled | 1e-7 | 31 | 3.289 | 4.974 | 0.663 [0.652, 0.682] | -1.673 | [200] / [200] |
| ill-scaled-coupled | 1e-9 | 31 | 3.244 | 4.921 | 0.658 [0.650, 0.668] | -1.680 | [200] / [200] |
| ill-scaled-generic-128 | 1e-7 | 31 | 4.608 | 6.109 | 0.757 [0.721, 0.798] | -1.484 | [200] / [200] |
| ill-scaled-generic-128 | 1e-9 | 31 | 4.582 | 5.916 | 0.769 [0.732, 0.805] | -1.376 | [200] / [200] |
| infinite-bound-refusal | 1e-7 | 31 | 0.389 | 0.407 | 0.966 [0.819, 1.061] | -0.014 | [0] / [0] |
| infinite-bound-refusal | 1e-9 | 31 | 0.298 | 0.302 | 0.984 [0.910, 1.078] | -0.004 | [0] / [0] |
| irregular-tail-33 | 1e-7 | 31 | 3.251 | 4.893 | 0.662 [0.654, 0.678] | -1.651 | [200] / [200] |
| irregular-tail-33 | 1e-9 | 31 | 3.199 | 4.852 | 0.657 [0.650, 0.667] | -1.681 | [200] / [200] |
| ranged-one-sided | 1e-7 | 32 | 3.286 | 4.965 | 0.664 [0.652, 0.671] | -1.674 | [200] / [200] |
| ranged-one-sided | 1e-9 | 32 | 3.226 | 4.915 | 0.658 [0.645, 0.671] | -1.680 | [200] / [200] |

Ratios are formed from the two within-session medians in each block, then
summarized across available pairs. Marginal table medians need not divide to the paired
ratio. Exact binomial order-statistic intervals use Bonferroni coverage over
32 family/tier ratios and 32 paired absolute savings (joint nominal >=95% only
under the statistical assumptions). Missingness is not proven independent of
cost. These are descriptive conditional intervals, not a successful frozen
confirmation or a correction for the interrupted block.
They assume independent session-level blocks; the shared GPU and temporal
conditions limit that assumption. Within-session repeats are not independent
samples. Planned order was exactly balanced 16/16; the incomplete block breaks
that balance for some families. No cell, refusal or outlier is silently
discarded and no scientific block is retried. Missing cells, first-16 sensitivity, pair-order
splits and every block value remain in the machine analysis. The provisional
1.10x target is not used to veto diagnostic evidence or claim adoption.

## GPU work and lifecycle value

| Strict dense family | Native GPU ms | FP4 GPU ms | Paired GPU speedup | Extra setup+teardown ms | Forecast break-even solves | Measured six-solve session ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| dense-coupled-1024 | 37.807 | 23.804 | 1.588 | 47.311 | 4 | 1.019 |
| dense-coupled-2048 | 70.551 | 37.352 | 1.889 | 187.302 | 6 | 0.997 |
| dense-generic-1024 | 9.450 | 5.949 | 1.588 | 46.338 | 15 | 0.976 |
| dense-generic-128 | 2.885 | 3.854 | 0.749 | -0.454 | None | 0.977 |
| dense-generic-2048 | 17.645 | 9.341 | 1.889 | 197.353 | 24 | 0.955 |
| dense-generic-256 | 3.706 | 3.926 | 0.944 | -1.636 | None | 0.994 |
| dense-generic-512 | 6.157 | 4.874 | 1.263 | 11.787 | 10 | 0.991 |
| dense-rich-65 | 5.758 | 8.714 | 0.661 | -4.013 | None | 0.955 |

GPU values are enclosing window events, including launches and host gaps,
not isolated tensor instruction throughput. Break-even divides median extra
setup/destruction by median per-solve savings, rounded upward. It is a
constant-cost amortization forecast, not a measured cold-solve result or a
guarantee for long sessions. Repeats reset the same model and initial state;
they do not measure changing right-hand sides or model streams. A useful
production reuse workload is unvalidated. The six-solve ratio is measured and includes both
tiers. Small shapes and short sessions can lose even where dense prepared
arithmetic wins; no universal preset or timing-selected route is selected.

## Retained diagnosis and optimizations

The first admitted FP64-reconstruction implementation lost at every measured
shape. Strict dense2048 complete medians were 104.154 ms native, 189.208 ms
x2 and 181.135 ms x4; GPU events were 17.801 / 37.895 / 93.926 ms. X2 needed
232 updates and two assessments while the controls needed 200 and one.
All original development records and failed versions remain preserved.

FP32 temporary reconstruction with an explicit outward rounding bound cut
tensor cost. FP32 vector proposals retain FP64 residual accounting; outward
FP32 maxima and cooperative warp gathering reduce guard overhead. Original
references and persistent arithmetic remain FP64. Independent row/column
parallelism, exact SHA-256 and bounded magnitude-ordered FastTwoSum improve
both controls while preserving the original checker bits and reduction tree.

The two-block window study showed x2/16 avoids the extra generic-dense
assessment observed at x2/32. The audit pilot then cached the immutable
initial observation and retained 200-update audits instead of shortening to
32 near convergence. Coupled1024 FP4 fell from about 172 to 80 ms, while
physical work increased from 720 to 800; native received the same changes.
This is a measured check-frequency tradeoff, not a relaxed final tolerance.

| Strict family / lane | Coarse timers ms | Timers removed ms | Median paired overhead ratio | Four observed ratios |
| --- | ---: | ---: | ---: | --- |
| dense-coupled-2048 / fp4x2 | 362.826 | 363.065 | 1.014 | 1.032, 0.996, 1.037, 0.991 |
| dense-coupled-2048 / native | 374.964 | 380.529 | 1.015 | 1.005, 0.938, 1.024, 1.054 |
| dense-generic-1024 / fp4x2 | 29.951 | 30.550 | 0.972 | 0.984, 1.005, 0.935, 0.959 |
| dense-generic-1024 / native | 34.053 | 32.748 | 1.038 | 1.021, 1.188, 1.004, 1.054 |
| dense-generic-128 / fp4x2 | 6.022 | 5.973 | 1.026 | 1.093, 0.994, 0.999, 1.053 |
| dense-generic-128 / native | 4.576 | 4.641 | 0.974 | 0.971, 0.956, 1.041, 0.976 |
| dense-generic-2048 / fp4x2 | 89.729 | 93.594 | 0.978 | 1.007, 0.940, 1.079, 0.950 |
| dense-generic-2048 / native | 98.877 | 98.972 | 0.986 | 1.001, 0.956, 1.031, 0.970 |
| dense-generic-512 / fp4x2 | 13.321 | 13.265 | 1.010 | 1.002, 1.026, 1.000, 1.018 |
| dense-generic-512 / native | 14.192 | 14.345 | 0.992 | 0.932, 1.011, 0.974, 1.026 |

The separate timer ablation preserves all 40 paired numerical transcripts
(endpoints, certificates, audits, checkpoints, recovery and physical work).
Only coarse phase clocks and run-window CUDA events are removed. Actual
stream synchronization, readbacks and deadline clocks remain. Four blocks
give descriptive disturbance evidence; variability prevents assigning every
difference to timers or treating phase spans as exact causal attribution.
The frozen confirmation executable is unchanged by this ablation.

The two 180-cell product studies retain both directions, both FP4 component
counts and guarded/unguarded ablations. Guard-free products are read-only
diagnostics and never enter a solver. Product events divide 128 launches and
retain host launch gaps; vector preparation, allocation and readback are
separate. All values and source identities are in the diagnostic archive.
An independent exact dyadic oracle checks all 95232 retained FP4 product outputs
against original coefficients and all 47616 native outputs against the original
eight-warp multiply/add tree, including the largest 2048 grids. These component
studies cannot substitute for complete certified solves.

## Numerical authority and limitations

Normal E2M1 components exclude subnormal codes 1/9. The admitted unscaled
32-term component dots are exactly representable quarter-integer FP32 sums.
The bounded codec and scale range prevent temporary overflow/underflow;
FP32 reconstruction error, vector residuals, matrix representation error and
FP64 reference/addition errors enter conservative outward local bounds.
Those bounds are local product enclosures, not a global trajectory proof.
Guard/progress failure restores the exact FP64 checkpoint and promotes
x2 to x4 to permanent native; physical work is never rolled back.
Confirmation recovery counts: `{'local_budget': 186}`. All recoveries and refusals remain visible.
Cancellation/deadlines precede certificate authority. The independent CPU
checker uses the original model at the requested tier, never FP4 data.
[NVIDIA PTX ISA](https://docs.nvidia.com/cuda/parallel-thread-execution/) and
[Ogita, Rump and Oishi (2005)](https://www.tuhh.de/ti3/paper/rump/OgRuOi05.pdf)
document the MMA arithmetic interface and error-free addition transformation.
Hardware assumptions remain explicit, tested and specific to this image.

Build v1 failed on a CUDA helper name (1440 CPU seconds); build v2 failed on
a debug interface signature (960 CPU seconds). Device v1 hit the inherited
128 MiB checker input cap on the 225 MiB dense2048 model (720 CPU / 180 GPU
seconds). The new explicit 384 MiB cap passed CPU admission before CUDA.
These failures, source versions and full charges remain preserved.

One development all-process racecheck run exited 11 without delivering its
certificate, reporting zero hazards; its full 960 CPU / 240 GPU reservation is
charged. Eight prospectively ordered old/new-image
probes did not reproduce it; its cause remains unassigned. Later admission
scopes instrumentation to the root CUDA executor. The separate checker has
CUDA visibility disabled and independent CPU admission. Four new scoped
passes do not prove the earlier exit fixed. This remains a reliability
limitation and prevents a production-readiness claim.

A separate CPU product oracle was stopped after a missed coordinator heartbeat
after checking dimensions through 512. Its full 960 CPU-second reservation
is retained. A new cooperative three-CPU validation launcher keeps the same
supervisor and limits; this is CPU acceptance, not a scientific timing retry.
The scheduling cause is unassigned. The same supervisor reason later stopped
scientific block 26, preserving its full 720 CPU / 180 GPU seconds. All
remaining untouched blocks retain the original image, source, settings and
order; the failed block stays incomplete and is never regraded.

Further useful work is representative sparse/batched production workloads,
remaining exact checker cost, setup amortization, and investigation of that
unexplained exit. No follow-on allocation, public default, GPUP-8 completion,
TENSOR2 pass or GPUP-9 release is implied. Historical results stay exact.

## Reproduction and acceptance

`python3 tools/lp_mixed2_fp4_analysis.py verify` reproduces every confirmation
available cell, explicit missing-cell ledger and all descriptive summaries
without CUDA or the original artifacts tree. Replay verifies stored response
bytes, coverage, work/cost arithmetic and summaries; original-model serial
recertification is the separate endpoint/audit acceptance described below.
Use `bash tools/check_mixed2_fp4_cpu.sh` for isolated CPU acceptance.
[Analysis](data/mixed2-fp4-analysis-v1.json),
[original confirmation responses](data/mixed2-fp4-records-v1.json),
[diagnosis](data/mixed2-fp4-diagnosis-v1.json),
[acceptance](data/mixed2-fp4-acceptance-v1.json) and
[allocation accounting](data/mixed2-fp4-accounting-v1.json) retain the evidence.
The independent envelope is 160000 CPU / 24000 GPU seconds, four CPU slots,
16 GiB sampled RSS and 12 GiB device buffers with one pinned shared lease.
The original supervisor is unchanged. All failed reservations are fully charged;
there is no historical budget transfer. Commit locally only.

## Guarded product diagnosis

| Generic dimension / forward product | Original guard x2 μs | Optimized guard x2 μs | Optimized native μs | Native / FP4 product ratio |
| --- | ---: | ---: | ---: | ---: |
| dense-generic-128 | 6.161 | 6.163 | 6.158 | 0.999 |
| dense-generic-256 | 8.212 | 6.163 | 8.357 | 1.356 |
| dense-generic-512 | 10.259 | 8.195 | 12.321 | 1.503 |
| dense-generic-1024 | 16.417 | 10.274 | 22.568 | 2.197 |
| dense-generic-2048 | 28.712 | 16.439 | 41.358 | 2.516 |

These are component diagnostics with fixed nonzero operands. The two versions
were measured at different times, so the before/after difference includes shared
environment variability; the contemporary native control is the stronger comparison.
Both directions and all guarded/unguarded block values remain in the diagnosis.

Final acceptance: 638 repository Rust / 700 Python tests; 27 isolated Rust tests; 204 original CPU admission assessments and 293 distinct original serial endpoint/audit reassessments. The current device suite has 130 cases and 2304 rational outputs; four scoped sanitizers each have 97 cases / 2304 outputs. All 22 process/configuration cases pass. Portable replay passes; 1900 historical files and all older backlog entries remain exact.

Allocation closed at 21920.478063592 CPU / 2888.679726775 GPU seconds, including 128 closing CPU seconds. 6 failed reservations and exact sources/logs are preserved; all cleanup is empty.

[Portable development, models, admissions and sources](data/mixed2-fp4-evidence-v1.json), [complete resource receipts](data/mixed2-fp4-resources-v1.json.gz).
