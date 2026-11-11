# FP4 optimization: GPUP-FP4-FAST

The separate [SPEC-0028](../specifications/SPEC-0028-fp4-fast.md) /
[ADR-0060](../decisions/ADR-0060-fp4-fast.md) implementation completes all 288
frozen cold batch cells and 2016 fresh prepared windows. Every optimized endpoint
matches its lane's retained implementation in state, component codes, exponents
and update flags. FP4 CUDA time improves **4.16–7.81×**
across the 24 model-size/component combinations; their geometric mean is
**5.27×**. These are bounded inner-iteration measurements, not certified
LP solve times. No supported solver preset is selected.

## Measured performance

Each entry is the median of three process medians, each containing seven fresh
32-update windows. Times below are CUDA event microseconds, including any host
submission gap between the events. “Native ratio” uses
the faster of the retained and cached FP64 controls, so a number below one means
FP4 is still slower. Full samples and observed three-process ranges are in the
[machine result](data/fp4-fast-result-v1.json). Three cold repetitions do not
establish a universal speedup or a tight population confidence interval.

| Coefficients | Variables | FP4 components | Legacy µs | Optimized µs | Same-lane speedup | Native ratio | Iterate error |
|---|---:|---:|---:|---:|---:|---:|---:|
| dyadic | 2048 | 2 | 475.78 | 92.86 | 5.12× | 1.52× | 0.0981 |
| dyadic | 2048 | 4 | 962.30 | 173.79 | 5.54× | 0.81× | 0.000701 |
| dyadic | 2048 | 8 | 2185.41 | 321.70 | 6.79× | 0.44× | 1.11e-07 |
| dyadic | 131072 | 2 | 992.70 | 185.86 | 5.34× | 4.50× | 0.0981 |
| dyadic | 131072 | 4 | 2197.73 | 389.76 | 5.64× | 2.15× | 0.000701 |
| dyadic | 131072 | 8 | 5414.53 | 693.31 | 7.81× | 1.21× | 1.11e-07 |
| rich | 2048 | 2 | 474.72 | 93.34 | 5.09× | 1.51× | 0.0675 |
| rich | 2048 | 4 | 958.11 | 193.76 | 4.94× | 0.73× | 0.000578 |
| rich | 2048 | 8 | 2180.74 | 501.38 | 4.35× | 0.28× | 9.66e-08 |
| rich | 131072 | 2 | 986.21 | 186.46 | 5.29× | 4.49× | 0.0675 |
| rich | 131072 | 4 | 2188.03 | 468.83 | 4.67× | 1.79× | 0.000578 |
| rich | 131072 | 8 | 5419.49 | 1302.85 | 4.16× | 0.64× | 9.66e-08 |

The rich family has binary64 coefficients that keep the later matrix components
active. Its inclusion prevents the zero-plane optimization from being evaluated
only on the pilot's exactly dyadic matrices. Both families consist of independent
32-by-32 blocks; this is not a coupled sparse LP benchmark. Iterate error compares
against an independent original-A FP64 recurrence. The nonzero primal residuals
remain reported; neither quantity is a final certificate.

Prepared wall time includes a fresh device checkpoint reset, export and an
original-A residual observation. Cold input-to-export time covers preparation,
binary serialization and process delivery of **seven windows**, rather than a
single solve. Independent reference construction/check costs are reported
separately. Context creation, export/checking and model delivery can dominate
these short windows, so the kernel ratios must not be presented as cold solver
speedups. The worker reuses immutable model preparation and its CUDA context
across fresh windows; it retains complete checkpoint/cancellation semantics.

## What changed and why

- Replaced the linear scale search with exponent extraction and a bounded test.
  Native warp reductions replace the five-stage maximum shuffle tree.
- Used native E2M1 conversion, preserving the low FP32 component's rounding
  decision at every midpoint; simplified exact component subtraction and packing.
- Skipped exact-zero matrix planes, prepared matrix fragments once, and used
  MMA columns for different components of the same RHS. An eight-component
  vector now uses all eight columns instead of discarding seven.
- Added aligned vector loads. Retained and diagnosed a CUDA 13 FP16 extraction
  failure: generated PTX read 32 bits at `base + 2*lane`. The first volatile-word
  workaround failed; an explicit 16-bit shared-memory load passed admission.
- Vectorized host preparation while preserving the rational oracle's codes and
  scales; replaced large JSON arrays with bounded lossless binary transport.
- Reused event objects and restored prepared checkpoints on the device. Fresh
  prepared windows have zero host checkpoint-copy bytes. Full exports and
  original-A observations remain charged.

Shared and register matrix-cache variants remain recorded. They are not uniformly
faster: the eight-component register cache increased register pressure and lost
performance. The cached FP64 control is also not uniformly faster. The final
comparison retains both native controls and matched optimized FP8/FP16 controls.
FP16 remains an important alternative when its arithmetic/quality contract fits.

## Bottleneck evidence

The original slowdown was predominantly representation/encoding and work
organization. It was not a PCIe transfer in every persistent update: the original
persistent window already had one launch and no per-update host copies.
The completed ablations isolate scale/encoding, zero products, matrix packing,
column utilization, caching and the final hardware-encoding step.

Device-clock instrumentation of the intermediate candidate attributed roughly
70–73% of small-workload cycles to reconstruction, projection and re-encoding;
the rest was mostly the two component products. Instrumentation changes the
compiled kernel and adds clock instructions, so these are scoped phase
observations, not hardware-stall percentages for the final image. Nsight Compute
refused counter access with `ERR_NVGPUCTRPERM`; that failure is retained. No host
security setting or driver was changed.

The original 1–64-warp workloads underfilled this GPU. Larger workloads improve
throughput utilization, while single-RHS Tensor arithmetic and component
normalization still impose limits. FP4 hardware throughput does not automatically
translate to solver throughput. The final timing table shows both wins and
remaining losses against native arithmetic.

## Host preparation

Fresh-cache measurements reproduce exactly the original prepared requests for
64 blocks. These timings cover host preparation only, separately from GPU and
context costs. The [host receipt](data/fp4-fast-host-preparation-v1.json) retains
all three repetitions and both implementations.

| Lane | Rational preparation ms | Vectorized preparation ms | Speedup |
|---|---:|---:|---:|
| FP64 ×1 | 14.613 | 2.297 | 6.4× |
| FP8 ×4 | 1479.500 | 14.821 | 99.8× |
| FP16 ×2 | 465.445 | 7.699 | 60.5× |
| FP4 ×2 | 1073.028 | 9.997 | 107.3× |
| FP4 ×4 | 2083.546 | 12.834 | 162.3× |
| FP4 ×8 | 4105.613 | 18.114 | 226.7× |

## Acceptance and retained history

Acceptance includes 60 independent rational product cases, 72 rich-trajectory /
midpoint comparisons, 42 execution/rollback cases, and 24 paths under each of
memcheck, racecheck, initcheck and synccheck. Sanitizer requests include two fresh
windows and therefore exercise device checkpoint restoration. All four report
zero errors; racecheck also reports zero warnings. A supplemental
[36-case projection-boundary suite](data/fp4-fast-projection-boundaries-v1.json)
checks clipping at ±1 with low-component perturbations and nonzero checkpoint resets.

The full repository gate passes 638 Rust tests, 593 Python tests, replay,
dependency/artifact checks, documentation and smoke. The updated isolated runtime
passes four Rust tests and Clippy; seven focused Python tests cover the final
preparation, transport and reference paths. The complete software/device evidence
is in the [acceptance record](data/fp4-fast-acceptance-v1.json).

The completed pilot's three manifests and original sources/results remain exact.
Development source snapshots, images, partial outputs and failures remain
versioned. Four earlier executors were reconstructed byte-for-byte from frozen
sources and archived, without rerunning scientific cells; the explicit archive
bridge preserves their original hashes. The [evidence record](data/fp4-fast-evidence-v1.json)
contains that bridge, compiler/device identities and all retained failures.

| Retained failed attempt | Charged CPU seconds | Charged GPU seconds |
|---|---:|---:|
| aligned-word-diagnosis-v6 | 240.000 | 60.000 |
| counters-v1 | 720.000 | 180.000 |
| cpu-v1 | 1200.000 | 0.000 |
| final-cleanup-v1 | 480.000 | 0.000 |
| hardware-v5 | 1200.000 | 300.000 |
| primitives-v6 | 720.000 | 180.000 |
| vector-load-diagnosis-v5 | 240.000 | 60.000 |

The final staged-diff check initially refused seven whitespace-only lines in the
frozen CUDA source. The [exact-hash exception](data/fp4-fast-hygiene-v1.json)
preserves those measured bytes and checks every other file/rule normally. The
failed cleanup reservation remains fully charged.

The independent ceiling is 128000 CPU / 18000 GPU seconds, with all failed
reservations retained. [Final accounting](data/fp4-fast-final-accounting-v1.json) reports
phase totals and every reservation/settlement. The earlier
[reporting snapshot](data/fp4-fast-accounting-v1.json) remains exact.
Final closed charge: **13029.974968908 / 128000 CPU seconds** and
**2013.455708259 / 18000 GPU seconds**. All supervisor cleanup receipts are empty. Historical funds
remain closed and were not reused. No frozen timing cell was retried.

Certified integration still requires the recovery-policy contract, nontrivial
long trajectories, original-model audits and independent final 1e-7/1e-9 checking.
The old FP4-PROTO and GPUP-8 remain incomplete and GPUP-9 remains gated. Delivery
is a local commit only; no push or publication.
