# GPUP-FP4-GPU-PILOT: actual FP4 products and persistent updates

Status: bounded empirical pilot complete, 2026-11-11; this candidate has no measured FP4 performance advantage.

All **216 profile cells** complete after arithmetic, transactional and four-sanitizer
admission. Keep the native control. All matched FP4 cold and iteration medians are
slower in this grid; no solver preset or certified speed claim is selected.
[Full results and repetition ranges](data/fp4-gpu-pilot-result-v3.json),
[source/compiler/gate evidence](data/fp4-gpu-pilot-evidence-v3.json), and
[delivery accounting](data/fp4-gpu-pilot-accounting-v3.json) retain every cell and charge.
[Final delivery acceptance](data/fp4-gpu-pilot-acceptance-v3.json) passes source,
resource, dependency, artifact, syntax, documentation and staged-diff checks.

Contract: [SPEC-0027](../specifications/SPEC-0027-fp4-gpu-pilot.md) /
[ADR-0059](../decisions/ADR-0059-fp4-gpu-pilot.md), under the independent device
path in [ADR-0058](../decisions/ADR-0058-fp4-gpu-exploration-quality-tiers.md).
The [packing recovery](../plans/lp-fp4-gpu-pilot-packing-recovery.md) and
[synchronization recovery](../plans/lp-fp4-gpu-pilot-synchronization-recovery.md)
have explicit user releases. Earlier failed attempts and charges remain exact.

## Implementation and scope

The isolated [research package](../../research/lp-fp4-gpu-pilot/README.md) adds a
safe Rust executor over the existing CUDA driver boundary and separately provisioned
CUDA kernels. The active candidate is [pilot_v3.cu](../../research/lp-fp4-gpu-pilot/cuda/pilot_v3.cu),
with actual E2M1 MMA, packed persistent state, power-of-two component scales,
local FP32-pair accumulation, projection and normalization. All component cross-products
are evaluated. Matrix and transpose use the same stored coefficients. Ordinary
component updates do not reconstruct the whole state in FP64 or return it to the host.

The workload is deliberately bounded: one dense 32-variable block, one irregular
29-variable block padded to 32, and 64 distinct dense blocks totaling 2048
variables. Blocks have no coupling. Every MMA has one useful RHS and seven zero
output columns. Persistent execution is legal because each warp owns an independent
block; this implementation cannot be substituted into a general coupled sparse LP.

The six lanes are native FP64, four E4M3 components, two binary16 components, and
two/four/eight E2M1 components. Split, fused, persistent and explicit FP64-roundtrip
variants perform the same ordered primal/projection/extrapolation/dual recurrence.
The independent host oracle observes original-A iterate differences at 1, 8 and
32 updates and original-A primal residuals at export. These quantities are neither
proved error enclosures nor LP certificates. No 600-update qualification or favorable
solver forecast is required for this empirical pilot.

## Measurement boundaries

The frozen grid contains three workloads, six lanes, four variants and three
repetitions: 216 cells. Each performs 32 physical updates. Hash-derived within-batch execution
order, workloads and numerical criteria stay fixed through the separately released
source corrections. No profile cell may be retried or omitted from coverage.

The reported cold proxy is exact-rational Python matrix preparation plus worker
process wall time. It includes context/module loading, device allocation/upload,
checkpoint capture, iteration, export, original-A residual observation and durable
worker output. It excludes coordinator request serialization, postprocess host
reference comparisons and protocol receipt writes. There is no independent endpoint
certification in this pilot, so this is not complete time-to-certificate. Python
preparation is an independent oracle implementation, not an optimized production encoder.

Iteration wall time covers submission, event setup and synchronization after all
32 updates. CUDA event span includes host submission gaps and, for the roundtrip
variant, device idle periods during host copies. Neither is isolated kernel busy
time. The worker reports disjoint context, upload/checkpoint, iteration, export
and audit phases; process startup/parsing/output/teardown is additional cold work.
Phase medians need not sum to the median total. Three repetitions give observed
ranges, not a confidence interval or an established performance ranking.

All variants count total and iteration launches/copies/bytes, device buffers,
component pairs, vector normalizations, projection coordinates, padded MMA FLOPs
and useful original-matrix FLOPs. Component lanes incur K-squared products per
matrix/vector operation, plus one-eighth RHS utilization and irregular padding.
The roundtrip ablation adds full-state export/copy/re-encoding every update.

## Results

For the 2048-variable persistent workload, FP4 with two/four/eight components takes
503.451 / 988.228 / 2213.443 microseconds per 32 updates, versus 175.686 for native
FP64. The corresponding control/candidate iteration ratios are 0.348963 /
0.177779 / 0.079372. These measurements include all update and encoding work.
FP8 and FP16 controls are also slower than native here. Three repetitions do not
establish results outside these bounded workloads.

Persistent observations below include all three workloads. Iteration ranges are
observed minima/maxima. Cold ranges and all 72 workload/lane/variant summaries
are in the machine results. No endpoint is certified.

| Workload | Lane | Iteration median (µs) | Observed range (µs) | Cold median (ms) | Maximum iterate difference |
| --- | --- | ---: | --- | ---: | ---: |
| dense-32 | FP64 | 171.949 | 171.658–181.215 | 338.136 | 0 |
| dense-32 | FP8 ×4 | 728.645 | 728.374–729.333 | 429.734 | 1.25648e-06 |
| dense-32 | FP16 ×2 | 320.216 | 318.680–321.767 | 371.040 | 1.14424e-07 |
| dense-32 | FP4 ×2 | 500.526 | 499.501–501.275 | 400.962 | 0.0678984 |
| dense-32 | FP4 ×4 | 984.998 | 984.920–991.439 | 458.249 | 0.000517592 |
| dense-32 | FP4 ×8 | 2208.523 | 2206.919–2219.396 | 569.726 | 6.97188e-08 |
| irregular-29 | FP64 | 173.162 | 171.830–173.266 | 328.058 | 0 |
| irregular-29 | FP8 ×4 | 724.613 | 724.474–727.258 | 420.116 | 1.90306e-06 |
| irregular-29 | FP16 ×2 | 316.727 | 315.672–317.593 | 358.438 | 1.29615e-07 |
| irregular-29 | FP4 ×2 | 499.314 | 496.816–499.588 | 394.958 | 0.0784782 |
| irregular-29 | FP4 ×4 | 982.424 | 981.315–983.586 | 461.555 | 0.000508893 |
| irregular-29 | FP4 ×8 | 2203.540 | 2203.478–2203.830 | 579.956 | 7.4789e-08 |
| dense-2048 | FP64 | 175.686 | 175.335–177.931 | 390.597 | 0 |
| dense-2048 | FP8 ×4 | 735.426 | 731.615–740.843 | 1957.815 | 2.01741e-06 |
| dense-2048 | FP16 ×2 | 324.179 | 323.969–324.548 | 861.614 | 3.12058e-07 |
| dense-2048 | FP4 ×2 | 503.451 | 503.124–504.007 | 1459.215 | 0.0980738 |
| dense-2048 | FP4 ×4 | 988.228 | 987.189–989.544 | 2515.382 | 0.000701405 |
| dense-2048 | FP4 ×8 | 2213.443 | 2211.484–2214.020 | 4539.978 | 1.11199e-07 |

The eight-component FP4 maximum difference is about 7.0e-8 / 7.5e-8 / 1.1e-7
across the three workloads. These are 32-update iterate differences, not final
1e-7 certificates. Original-A primal residuals remain about 0.485 / 0.255 / 0.584;
there is no feasibility, dual-bound, gap or convergence conclusion. Two/four
components have much larger observed errors. Error and latency both matter.

Fusion and persistence reduce overhead for every lane, but their benefit also
applies to native FP64. The explicit roundtrip is expensive. Dense-2048 iteration
medians, in microseconds per 32 updates:

| Lane | Split | Fused | Persistent | Roundtrip |
| --- | ---: | ---: | ---: | ---: |
| FP64 | 552.509 | 288.939 | 175.686 | 2426.230 |
| FP8 ×4 | 1239.306 | 865.265 | 735.426 | 3335.056 |
| FP16 ×2 | 880.320 | 449.533 | 324.179 | 2745.534 |
| FP4 ×2 | 814.396 | 616.025 | 503.451 | 3013.461 |
| FP4 ×4 | 1461.070 | 1116.145 | 988.228 | 4003.115 |
| FP4 ×8 | 2713.278 | 2360.458 | 2213.443 | 5767.468 |

Iteration launches are 128 / 32 / 1 / 96 for split / fused / persistent /
roundtrip. Ordinary variants have zero iteration host copies; roundtrip has 64,
transferring 3,145,728 bytes on dense-2048. Upload/checkpoint/export costs are
reported separately and remain in the cold proxy. Exact rational CPU preparation
largely determines the component lanes' cold costs; the iteration result is also
unfavorable, independently of that preparation overhead.

Compiler resources for v3 are below. Every kernel has zero stack and spill bytes;
SASS contains actual E2M1 QMMA instructions. Warp barriers do not consume a named
CTA barrier resource, so ptxas's zero named-barrier count is not absence of syncwarp.

| Lane | Registers/thread | Static shared bytes/block | Component pairs/product |
| --- | ---: | ---: | ---: |
| FP64 | 38 | 1024 | 1 |
| FP8 ×4 | 72 | 692 | 16 |
| FP16 ×2 | 48 | 668 | 4 |
| FP4 ×2 | 56 | 380 | 4 |
| FP4 ×4 | 72 | 500 | 16 |
| FP4 ×8 | 64 | 740 | 64 |

This grid does not support moving this implementation directly into a faster
certified solver. The component cross-products, packing/normalization and low
single-RHS utilization need a materially better cost case before such a claim.
The safety-admitted implementation and complete profiles remain useful evidence
for the separately planned numerical recovery and integration work.

## Retained failures

V1 stores E2M1 in the low nibble of instruction bytes instead of bits 5:2. Thirty
control primitives pass; the first FP4 case fails with maximum product difference
1.31915283203125. [The retained diagnosis](data/fp4-gpu-pilot-diagnosis-v1.json)
records all 31 attempts, 29 unexecuted primitives and zero profiles. A failed
CPU diagnosis initially assumed noncanonical padding was ignored; its full charge
also remains. Four corrected CPU packing tests and compilation precede the user
release for v2; the two fragment-expansion sites are the only packing changes.

V2 passes corrected FP4 primitives, 90 trajectory/transaction cases and all
24 memcheck paths. Racecheck passes four native paths and refuses FP8 split
updates: 128 warning-severity shared-memory hazards, 100 displayed, exit 86.
[The race diagnosis](data/fp4-gpu-pilot-race-diagnosis-v2.json) preserves every
attempt and the full 960 CPU / 240 GPU reservation. Zero error-severity reports
does not satisfy the zero-hazard gate. No profile ran from v1 or v2.

V3 adds one full-warp barrier before encoding overwrites the shared codes/scales
read by other lanes. CPU source audit verifies the exact one-barrier delta and
unchanged native FP64 SASS; compiler output retains PTX, cubin, SASS and resource
reports. The native passes are reused with explicit hashes; changed component
paths receive fresh checks under new identities. No original refusal is relabeled.

Software preparation also retains a Rust launch-argument compilation failure,
a missing-CMake launcher, and a full-gate attempt that passed Rust/native checks
but failed on Python environment and historical source-roster assumptions. The
new kernel was moved into the isolated research package through an exact-byte
path bridge. No historical numerical source, fixture, roster or result changed.

## Acceptance and accounting

Composite CPU/native acceptance passes 638 workspace Rust tests, three isolated
research Rust tests, 583 Python tests, replay, pinned native/dependency/artifact
checks and CPU smoke. Four additional corrected ISA packing tests pass. The
original nine-test suite is preserved with its mistaken low-nibble assumption;
the separate corrected tests and actual device differential supersede that
assumption. The failed full-gate charges remain; its passed Rust/native stages
were reused when the Python environment and source path were corrected.

V3 admission covers 60 primitives (50 new component / 10 retained native),
90 trajectory/transaction cases (75 new / 15 retained), and 24 paths for each
of memcheck, racecheck, initcheck and synccheck. Memcheck/racecheck each reuse
four unchanged native paths; initcheck/synccheck are entirely new. All final
sanitizer paths have zero reported errors/hazards. Cancellation tests include
prelaunch and bounded-window cancellation; sticky fault injection restores the
complete logical checkpoint while preserving physical work accounting. This is
scoped pilot safety coverage, not general solver recovery qualification.

All three manifests and **1246 pre-existing source/evidence files** are checked
for exact preservation. Source, binary, compiler/device, input/output and raw log
hashes bind the delivered results. No legacy numerical source, checker default,
scientific ledger or closed allocation changes. The active coordinator is
[study v3](../../tools/lp_fp4_gpu_study_v3.py); reporting never reruns a cell.

The independent task ceiling is 72000 CPU / 9600 GPU seconds. GPU charge is
**953.281143916 seconds**: acceptance 723.193855166 and study 230.087288750,
including the full 300-second packing failure and 240-second racecheck failure.
All nine profile batches settle successfully; none is retried. CPU phase caps
are implementation 16000, native 24000, acceptance 16000, study 8000, reporting
6400 and cleanup 1600. The native cap includes an explicitly recorded 8000-second
implementation-time amendment; no historical funds are transferred. Failed CPU
reservations total 18560 seconds, including both GPU-admission failures.

Four CPU slots, one shared GPU lease, sampled aggregate host RSS at 16 GiB and
explicit device buffers capped at 12 GiB apply. The unchanged supervisor's
coordinator and guardian cleanup receipts are empty. Sampling is not a hard
cgroup memory guarantee. Delivery accounting includes its active reporting
reservation conservatively. [Final closed accounting](data/fp4-gpu-pilot-final-accounting-v3.json)
settles **21522.216081528 CPU / 953.281143916 GPU seconds**, including preparation
and every failed charge. All reservations are settled and cleanup is empty.
Final documentation acceptance covers 207 pages and internal links. Only sources, protocol and evidence summaries are
committed; vendor environments and generated GPU binaries remain local.

## Handoff

GPUP-FP4-GPU-PILOT is complete as a bounded negative performance result.
The native public solver and original-model certification mathematics/defaults
remain unchanged. GPUP-FP4-RECOVERY-SPEC remains independently ready. Integration
still needs a versioned error/recovery policy, nontrivial coupled trajectories,
200-update original-A FP64 audits, complete checkpoints and independent endpoint
checking at the declared final tier. GPUP-FP4-PROTO and GPUP-8 stay incomplete;
GPUP-9 stays gated. No solver preset or certified performance claim follows here.
