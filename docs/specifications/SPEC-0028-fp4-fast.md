# SPEC-0028: FP4 inner-kernel optimization

Status: implementation authorized by the user's FP4 performance request.

## Scope and numerical authority

Optimize the bounded single-RHS recurrence from [SPEC-0027](SPEC-0027-fp4-gpu-pilot.md)
in a separate research package. Persistent state remains packed E2M1 components;
local update arithmetic remains FP32 pairs. Original-A FP64 observations are
reported, not called certificates or proved enclosures. No public solver defaults
change. Complete certified LP integration still needs its numerical recovery policy.

The initial ablations are unchanged legacy, constant-time encoding, exact-zero
matrix-plane pruning, prepared instruction fragments, and using MMA columns for
different state components. Column utilization must not introduce additional RHSs
or change component accumulation order. Test codes, exponents and exports against
the legacy path, plus independent rational products and original-A trajectories.
Any numerical difference requires an explicit versioned disposition, never silent
relaxation. Fast host preparation must match the rational oracle in its admitted
input domain; refuse unsupported ranges instead of silently rounding the model.

## Resources and iteration

This is a new allocation, not a transfer from the completed pilot: 128000 CPU
seconds (implementation 24000 including 512 preparation, native 16000, acceptance
32000, study 48000, reporting 6400, cleanup 1600); 18000 GPU seconds (acceptance
7200, study 10800). Four CPU slots, one inherited shared GPU lease on the pilot's
pinned SM120 device, 16 GiB sampled host RSS, 12 GiB device buffers. Whole-job
reservations precede execution through the unchanged `lp_cpu_admission.py`.
Failed jobs retain their full reservation; unsettled jobs and overruns close
admission. Every development attempt snapshots its sources. The user's request
authorizes ordinary development fixes and new versioned experiments within this
allocation. No historical result is retried or overwritten.

## Acceptance and measurements

CPU tests cover nearest-even boundaries, scale extremes, packing, transpose and
component-column layouts. Device checks cover both products, padded dimensions,
all supported lanes, 1/8/32-update windows, cancellation and exact checkpoint
rollback. Four separate zero-error sanitizer passes admit the final candidate.
Register counts, spills, compiler flags and actual E2M1 instructions are retained.

Exploratory timings may guide development and remain labeled as such. Freeze
the final source/image identities and ordered cell list before its formal run;
do not retry timing cells automatically. Include 1, 64, 512 and 4096 independent
32-by-32 blocks, matched native/FP16/FP8 controls and FP4 x2/x4/x8, with repeated
fresh-state prepared windows. Report medians and dispersion, measured preparation,
serialization, context, transfer, iteration, export and checking costs. Kernel
latency and full cold delivery remain separate. Use component columns to improve
single-RHS arithmetic, not to inflate useful work. Report remaining limitations
and retain the native control regardless of the outcome.

Local commit after delivery; no publication or GPUP-9 execution is authorized.

## Final comparison protocol

The final grid has 288 cold process cells: two coefficient families (retained
32-by-32 dyadic pattern and deterministic rich binary64 coefficients), four block
counts, six lanes, two implementations per lane and three cold repetitions.
SHA-256 ordering with seed `120428` is fixed by `lp_fp4_fast_study.py`. Every
process prepares one immutable model and executes seven fresh 32-update windows;
all seven are reported. The native pair is retained versus register-cached FP64;
the low-precision pairs are retained versus hardware encoding. Neither native
variant may be silently discarded from the results.

Hardware encoding uses native E2M1 conversion, adjusting exactly represented
midpoints according to the low FP32 component before conversion. Native integer
warp maxima replace the shuffle tree. Aligned vector loads read prepared matrix
fragments. FP16 extraction explicitly uses a half-width shared-memory load,
following a retained CUDA 13 misaligned extraction diagnostic. CPU vectorized
preparation and bounded little-endian transport preserve original binary64
coefficients. All selected paths require fresh four-sanitizer admission.

`cold_input_to_export` includes request preparation, input serialization and
worker process delivery for the seven-window batch; it is not single-solve
latency. It excludes the experiment's independent reference
construction/check and any final certificate, which this experiment does not
produce. Those reference/check costs are separately reported. Prepared window
cost includes a complete device-to-device checkpoint reset, iteration, export
and the executor's original-A
residual observation. A model/family's independent original-A reference may be
cached across lanes; its first construction cost remains visible. Report each
process's median and all samples, then the median and range of the three process
medians. The small number of cold repetitions limits statistical generalization.

The two implementations must produce identical endpoint state, codes, exponents
and physical-update flags for each lane. Original-A FP64 iterate error is reported
for every endpoint; the native reference comparison must be within `1e-14`.
These are empirical bounded-window criteria, not final solver certification.
