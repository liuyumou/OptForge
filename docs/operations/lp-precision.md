# Experimental FP32 LP execution

GPUP-5 implements the bounded [ADR-0019](../decisions/ADR-0019-fp32-lp-comparisons.md)
contract on cuda-lp-tuned. Existing backend selections and absent precision settings
keep their original arithmetic and replay formats. These are experimental choices,
not supported presets. Adaptive audits and recovery remain GPUP-6.

## Explicit invocation

Use lp-execution-v1 with resident allocation, necessary uploads, warp32_v1 and
separate fusion. The older example enables fusion and must not be reused unchanged.
The method, execution and precision settings are separate required documents.

```bash
bash tools/gpu_job.sh GPU-UUID target/release/optimizer solve \
  --backend cuda-lp-tuned --device GPU-UUID \
  --model examples/lp-model-v1.json --config examples/solve-config-v1.json \
  --lp-settings examples/lp-settings-v1.json \
  --lp-execution examples/lp-precision-execution-v1.json \
  --lp-precision examples/lp-working-fp32-correction32-v1.json \
  --lp-evidence /tmp/precision-endpoint.json
```

The precision document declares matrix, product operand, product, accumulation,
working-state and update widths, nearest-even rounding and correction interval.
Null explicitly disables correction; FP32 working state requires correction.
All five supported width combinations use FP64 vector updates and control.
One converted row representation supplies the transpose. Range guards precede
projection and stop with numerical_failure; they do not invoke adaptive recovery.
Original-model host certification remains mandatory.

A correction recomputes the scheduled last step in original-operator FP64 from
saved pre-step state, adopts that endpoint, and charges both proposal and reference
work. It is not an audit or a verification of the preceding window. Corrected
endpoints retain FP64 values for checks; continuation explicitly rounds FP32 state.
The conservative operator-step policy has its own FP64 comparison. Same-device
repeatability does not assert cross-device or CPU/device equality as a public rule.

Precision solves emit solve-record v4 and endpoint v4; the absent-setting path keeps
v3. Old v2 records and endpoint v1/v2/v3 remain readable. Replay requires the exact
recorded precision object, settings and provisioned code-object hash. Ordinary
Cargo builds neither invoke nvcc nor require a GPU. Provision kernels explicitly
with tools/setup_cuda.sh.

## COPT and study reproduction

Run `python3 tools/setup_copt.py --installation /root/copt80` to copy the bundled
8.0.6 Python 3.11 bindings into an ignored environment. Licenses stay in the existing
installation. This is optional study tooling, not a runtime dependency or SDK.
Inputs with nonzero coefficients at or below COPT's 1e-10 input threshold or finite
bounds beyond its infinity sentinel are refused to preserve the original model.
The worker uses CPU/GPU PDLP with explicit parameters and independently checked
original-model witnesses. GPU confirmation requires a PDLP GPU-start log; discovery
or a requested GPUMode is insufficient. Presolve-only or CPU fallback runs are not
GPU successes. COPT exposes no native PDLP iteration-limit/seed parameter; the hard
wall limit remains, excess reported iterations are work-limited, and this mismatch
is recorded in every witness.

After the full pinned-native and separately leased device/sanitizer gates, freeze
all source/binary/library/code hashes in the version-4 campaign. Run
`python3 tools/benchmark_lp_precision.py --dry-run` to validate 480 planned attempts,
then omit --dry-run to execute them. The original campaign ledger and output binding
remain authoritative. New work uses the screening allocation and the exact
4502.574545061-second cumulative ceiling. Do not repair or reset evidence on resume.
`python3 tools/report_lp_precision.py` independently verifies evidence and reports
paired certified latency, coverage, work and costs. Failed, unsupported and timed-out
attempts remain in coverage denominators. No held-out evaluation occurs in GPUP-5.

The [completed GPUP-5 report](../benchmarks/lp-fp32-gpup5.md) retains all 480
attempts and explains the lower-precision coverage losses. Its ignored source
archive/binary are the measured implementation. Final import-range hardening and
additional device boundary acceptance do not change the frozen inputs or kernels.
