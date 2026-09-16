# Experimental Tuned FP64 LP Execution

Purpose: describe the GPUP-4 execution contract and its comparison controls.
Owner: numerical backend. Status: implemented; native/device acceptance and correction study passed.
Contract: [SPEC-0012](../specifications/SPEC-0012-mixed-precision-lp.md) and
[ADR-0017](../decisions/ADR-0017-tuned-fp64.md).

## Explicit selection

The experimental cuda-lp-tuned backend requires the ordinary LP method settings
and a version-1 execution document. No execution settings are defaulted. Existing
highs, host-lp, cuda-lp and cuda-lp-matched retain their contracts. FP32, quantization,
Tensor Cores, adaptive recovery and supported presets are later slices.

```sh
bash tools/setup_cuda.sh --tuned-only
bash tools/gpu_job.sh GPU-UUID target/release/optimizer solve \
  --backend cuda-lp-tuned --device GPU-UUID \
  --model examples/lp-model-v1.json --config examples/solve-config-v1.json \
  --lp-settings examples/lp-settings-v1.json \
  --lp-execution examples/lp-execution-v1.json --lp-evidence /tmp/tuned-endpoint.json
```

The example execution document is an explicit experimental configuration, not a
recommended recipe. Replace GPU-UUID with the selected device's actual UUID.
Provisioning is separate from ordinary Cargo builds. --tuned-only preserves all
existing kernel objects; full provisioning can change binary identity even for
unchanged source. Archive the actual reference code objects for comparisons.

## Arithmetic and ownership

The original FP64 model, scaled coefficients, preconditioning, step calculation,
shared host restart/weight controller, assessment intervals and conservative
certification are unchanged. Only iteration products use the selected reduction.
warp32-v1 accumulates each lane's entries at stride 32, starting from +0.0, then
combines lanes with offsets 16,8,4,2,1. Every active warp participates with the full
mask, following [NVIDIA's participation rules](https://docs.nvidia.com/cuda/cuda-programming-guide/05-appendices/cpp-language-extensions.html).
Products and additions round separately. This is a different deterministic
operation order; equality with legacy trajectories is not promised.

Both orientations use the existing CSR/CSC coefficients. Two-kernel fusion computes
the transpose product, primal projection, extrapolation and primal Halpern update,
then the row product, dual projection and dual Halpern update. Extrapolation reads
the old primal value before its replacement. Within one reduction mode, fused and
separate execution must produce identical vectors.

Invariant buffers and the module belong to one residency. Cached function handles
borrow that module. Resident working buffers persist through host checks; per-check
allocation remains an ablation. Necessary uploads initialize complete state, update
restart anchors and reload complete state after restoration. The controller's
non-rollback generation invalidates device state even when restored iteration and
restart indices equal an earlier index. Callers of TunedExecutor must pass that
generation and the controller's current restart count.

The host still reads both vectors at every assessment. Synchronized execution
chunks contain at most 64 steps, preserving bounded cancellation and actual work
accounting. Numerical state may roll back; physical iterations and deadlines do not.
A poisoned context cannot be reused. Only pinned HiGHS is a backend fallback.

## Records and measurements

Execution settings v1 select allocation, uploads, reduction and fusion. Necessary
uploads require resident allocation. Solve-record v3 embeds these settings and the
SHA-256 of the exact code bytes loaded. Tuned endpoint v3 records requested execution
and actual counters even on fallback. Existing solve-record v2 and endpoint v1/v2
schemas and emitted shapes stay unchanged. Replaying a tuned record checks the
installed code object against its recorded identity before device execution.

Counters record successful allocations and their cumulative bytes, successful
copy calls/bytes, successful synchronizations and submitted kernels. Admission and
peak LP-buffer bytes include zero-length padding and the selected scratch buffers;
driver/context memory is excluded. Faults can make completed physical work
unavailable without erasing submitted launches or successful earlier allocations.

Primary evidence measures a fresh solve process, including setup, transfers,
controller work, host checks, final independent assessment, output and teardown.
Separate profiles measure component costs. Allocation/transfer counters explain
those costs; a kernel improvement alone is not a single-solve speedup claim.

## Acceptance and reproduction

The original frozen [GPUP-4 configuration](../../benchmarks/configs/lp-tuned-v3.json) compares
six tuned execution settings, archived matched FP64 and current host LP across the
unchanged development manifests. Run tools/benchmark_lp_tuned.py --dry-run to
inspect the 320-attempt schedule; the coordinator enforces the original canonical
ledger plus ADR-0017's explicit cumulative extension. tools/report_lp_tuned.py
verifies raw identities, independent endpoints, pairing and charged work.
[ADR-0018](../decisions/ADR-0018-fp64-study-correction.md) preserves the first round's
reference launch failures and freezes one complete correction, with no extra GPU
allowance. Use --campaign benchmarks/configs/lp-tuned-correction-v3.json and
--output artifacts/gpup4-tuned-fp64-correction-v1 for its coordinator, then the same
--campaign and --input artifacts/gpup4-tuned-fp64-correction-v1 for its report.
Preflight execute permission and preserve modes when archiving executable files.
Both rounds retain the exact 622-event pre-GPUP-4 ledger prefix by SHA-256.

CPU acceptance is bash tools/check.sh with pinned native HiGHS. Device acceptance
uses tools/lp_tuned_gpu_check.sh under tools/gpu_job.sh. Independent rational dot
fixtures, full trajectories, restarts/restoration, cancellation, memory refusal,
objective senses, schema corruption, fallback and replay are separate obligations.
No validation/held-out solve or default promotion occurs in this slice.

Device acceptance uses an RTX PRO 6000 Blackwell (sm_120) for sanitizer headroom;
all regular device cases also passed on the frozen RTX 5090. The RTX 5090 had only
797 MiB free and could not allocate sanitizer instrumentation. All four scoped
tools passed on the compatible device without reducing their checks. Benchmark
measurements retain the original RTX 5090 and record its memory/activity telemetry.

The [reviewed GPUP-4 report](../benchmarks/lp-tuned-fp64-gpup4.md) preserves both
rounds and all failures. Matched FP64 remains the general reference. Fused warp32
is a provisional development comparison only on the three named instances whose
coverage and paired evidence support it; no preset or dispatch is introduced.
