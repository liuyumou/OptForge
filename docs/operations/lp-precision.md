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

## Read-only latency diagnosis

The [FP32 diagnosis](../benchmarks/lp-fp32-slowdown-diagnosis.md) documents the
completed ADR-0020 diagnostic grid and separates equal-update timing from original
model convergence. `python3 tools/diagnose_lp_precision.py` prints its frozen scope;
--gpu uses the existing ledger/lease and requires the exact source's native receipt.
It will not silently resume with changed source. The completed 213 jobs need no rerun.
Use `python3 tools/analyze_lp_precision_diagnosis.py` for stored evidence and --cpu
for original-versus-represented row diagnostics, after building the read-only Rust
example lp_precision_diagnose in optimizer-experiment. Offline-import.json records
how the saved profiler streams were decoded without additional GPU work.

Historical reports now require their snapshot to be an intact settled prefix of
the active canonical ledger and calculate their own totals from that snapshot.
Later diagnostic spending remains charged to the active ledger. Do not reset either
artifact directory or ledger to work around a provenance mismatch.

## Isolated exact-scaling/component research

[ADR-0021](../decisions/ADR-0021-exact-scaling-components.md) defines GPUP-5B.
The precision-research feature enables the lp_precision_research example in
optimizer-experiment. It accepts `solve MODEL REQUEST EVIDENCE` and the CPU-only
`verify MODEL REQUEST EVIDENCE`; requests and evidence are strict research-v1
objects, independent of runtime backend settings. Request fields bind model,
source tree, executable, code object, device, method, limits, profile and mode.
Evidence retains original-model primal/dual witnesses, independently recomputed
assessment, executed device, proposals/physical work, arithmetic truncation,
packing time, bounds/step, memory, transfers and failures. Unknown physical work
is explicit after device failure; component operation counts then describe the
admitted proposals. No runtime backend selector enables this arithmetic.

Provision only the separate object with `bash tools/setup_cuda_research.sh`.
Do not rebuild historical code objects to reproduce this study. The frozen grid
is benchmarks/configs/lp-research-v1.json. tools/benchmark_lp_research.py requires
a matching full native gate receipt and uses the existing shared lease/ledger;
it refuses changed execution identities and stops before exceeding its budget.
Do not reset or repurpose the completed output directory for a new experiment.
Read-only `python3 tools/analyze_lp_research.py --decode-traces` verifies archived
endpoints, identities, history and budgets, and imports retained traces offline.
The [report](../benchmarks/lp-exact-components-gpup5b.md) defines the limits of the
results. CPU-only rounding/oracle reproduction uses tools/analyze_lp_rounding.py
and tools/lp_research_oracle.py. No supported preset or adaptive recovery is added.

## GPUP-5C: FP64-pipe execution modes, tiers and extension

[ADR-0022](../decisions/ADR-0022-fp64-pipe-execution-and-tolerance-tiers.md) acts on
the [root-cause note](../benchmarks/lp-fp64-pipe-root-cause.md). The same research
executable accepts research-v2 requests for `intguard-fp64`, `fused-fp64` and
`doublefloat-fp32`; version 1 requests remain valid for the nine GPUP-5B modes.
The frozen protocol is benchmarks/configs/lp-research-v2.json, passed to
`tools/benchmark_lp_research.py --protocol` and `tools/analyze_lp_research.py
--protocol`; omitting the flag keeps GPUP-5B behavior. It records explicit
tolerance tiers per configuration, a 30-second limit for the development
extension instances materialized by `python3 tools/lp_generate.py --extension`
under lp-manifest-v2, and its own identity prefix, caps and preserved ledger
prefix. `bash tools/setup_cuda_diagnostics.sh` builds the cuda/diagnostics
microbenchmarks; run them only through `tools/lp_research_budget.py --protocol
benchmarks/configs/lp-research-v2.json --id microbench-... --seconds ...` so the
time is charged. Their numbers are diagnostics, never solve-time evidence.
The [GPUP-5C report](../benchmarks/lp-fp64-pipe-gpup5c.md) defines the limits of
the results.

## GPUP-THROUGHPUT: repeated-solve sessions

[SPEC-0014](../specifications/SPEC-0014-lp-repeated-solve-throughput.md) and
[ADR-0023](../decisions/ADR-0023-repeated-solve-throughput.md), both accepted
2026-09-20, add opt-in repeated-solve sessions. The public path is the
`optimizer solve-batch` CLI command for cuda-lp-tuned; the research path adds
`batch` and `verify-batch` actions to the isolated research executable for the
intguard-fp64 and fused-fp64 modes only. A session fixes one matrix, objective
and row bounds, and every solve starts from a fresh controller and the cold
iterate with original-model host certification unchanged. Evidence is one
directory per batch with individually verifiable per-solve records; amortized
per-solve time is a separately labeled endpoint, never substituted for fresh
single-solve latency. The frozen protocol is benchmarks/configs/lp-throughput-v1.json;
its budget is 2700 study plus 600 acceptance seconds, 3300 combined, under identity
gpup-throughput-v1 within the raised 8102.574545061-second cumulative ceiling.
Existing commands, defaults, schemas and archived evidence are unchanged.
