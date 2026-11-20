# Billion-nonzero LP development on the Pro6000

Execution continuation under [SPEC-0046](../specifications/SPEC-0046-billion-lp.md),
2026-11-19–20. Image-v4 removes duplicate host operator arrays while preserving
strict certificates and both CUDA binaries. All ten new 64/256/512 M capacity
runs have exact numerical transcripts and complete independent audits. Sampled
peak host RSS falls by roughly 25%; descriptive complete-cost speedups over
GPU-preparation image-v3 are 1.075x / 1.052x / 1.050x. These remain uncertified
100-update measurements. Zero billion-scale solves have run: two native/FP32
cells now fit current host headroom, but the FP4 lanes and full roster do not.
See the [latest memory results](#borrowed-host-matrix-storage).

## Scope and implementation

The approved target is one billion **original matrix nonzeros** in each connected
LP. It is not an arithmetic-operation count or a collection of independent small
problems. Six generated structural families cover irregular, wide, tall, coupled,
ill-scaled and degenerate geometry. Each original has its own coefficient stream,
explicitly verified connectivity backbone and separate strict construction
certificate. Construction witnesses are never passed to a solve.

The opt-in `lp-billion-lowbit` crate derives from scale-image-v14 and preserves the
fast-image-v10 CUDA image. Canonical CSR arrays replace per-term model documents
and compression triples. The reader hashes all input chunks, checks canonical
positions and builds the exact original transpose. Original arrays and endpoint
witnesses use immutable content-addressed chunks of at most 32 MiB, with small
JSON manifests. No full endpoint JSON vector or second full-size archive is needed.

Preparation uses bounded per-line scratch and retains the original reduction
tree. Control reuses the already-owned checkpoint for exact restoration comparison.
Full checkpoint recovery, 100-update control and 500-update certificate cadence
remain. Device construction checks actual buffer accounting and physical fragment
and launch-index arithmetic before creating a CUDA context.

Image-v1 uses the original serial certificate. Image-v2 partitions independent
certificate contributions among at most four scoped workers and joins them in
canonical order before the unchanged final outward reduction. There is no retained
per-coefficient geometry or endpoint-answer cache. The external scalar checker
continues to use the original certification implementation and strict 1e-9 criteria.

## Cost and claim boundaries

The primary complete cost is fresh-process elapsed time plus independent final
original-model checking. It includes input hashing/parsing, preparation, packing,
transfers, execution, control, internal certification, response transport and owned
teardown. Generation and construction checking are separately timed, as are audits
of intermediate assessments. The assessment partition also includes continuation,
control and device reset; it is not an isolated certificate or control timer.

These are descriptive development measurements with one rotated repetition per
configuration. Fresh processes do not imply flushed caches. Shared host/device
variability remains possible. Faster limit or deadline runs do not establish
certified-solve benefit. Requested FP4 configurations with no eligible canonical
tiles select FP32 and are reported separately from actual FP4 work.

## Exact certificate comparison at 64 million nonzeros

Both six-case, 100-update cohorts complete with exact non-timing numerical
transcripts. Every final and intermediate assessment agrees with the independent
original serial checker. All are uncertified iteration-limit endpoints; these
measure capacity and equal-work overhead, not convergence.

| Family | v1/v2 assessment | v1/v2 process | v1/v2 complete cost | v2 complete seconds |
| --- | ---: | ---: | ---: | ---: |
| Irregular | 1.850 | 1.163 | 1.105 | 56.710 |
| Wide | 1.613 | 1.129 | 1.093 | 86.489 |
| Tall | 2.025 | 1.155 | 1.122 | 46.379 |
| Coupled | 2.208 | 1.196 | 1.147 | 34.010 |
| Ill-scaled | 1.871 | 1.218 | 1.173 | 54.361 |
| Degenerate | 1.848 | 1.206 | 1.175 | 50.872 |
| Descriptive median | 1.861 | 1.179 | 1.134 | — |

The coupled case uses actual FP4 for 75% of accepted product nonzeros, with no
recovery. The other five cases have no eligible tiles and select FP32. The paired
overhead result is shared host improvement and does not establish incremental
FP4 superiority over native or FP32.

## Capacity interruption and prospective readmission

The first 128 M irregular cell stops during host preparation without a response
or observed CUDA context. The final resource reason is `cleanup_incomplete`; the
earlier initiating reason is not retained separately. Preserve the missing cell,
its original false cleanup receipt, active journal and full 1920 CPU / 480 GPU
seconds. A later observation verifies every recorded process identity absent and
the GPU idle. It does not reconstruct historical supervision.

[Amendment 3](../specifications/SPEC-0046-amendment-3.md) admits a complete storage
scan using fewer metadata calls, with unchanged limits and cadence. Fresh
operational acceptance passes 75 original supervisor tests, 11 resource tests and
60 exact GPU continuations. Only the never-started coupled 128 M cell continues;
it completes 100 updates in 55.181 process seconds, with 75% accepted FP4 work and
exact independent assessment. No attempted scientific cell is repeated.

## GPU preparation candidate

[Amendment 5](../specifications/SPEC-0046-amendment-5.md) implements the user's
request for GPU scaling, norm estimation and step-size estimation. The isolated
candidate adds exact-order FP64 Ruiz/Pock-Chambolle scaling, scaled coefficient
construction, power products, recursive vector norms, normalization and step
calculation. The complete preparation interval includes transfers and both context
creation and teardown. Its temporary GPU buffers are released before solve buffers
are allocated. The existing solve CUDA image stays byte-identical.

Original matrix authority, strict CPU certificates and independent scalar checking
remain unchanged. The candidate explicitly falls back for empty geometry, lines
longer than 1024 terms, Pock exponents outside 0/1, or invalid GPU intermediates.
The request flag is opt-in. CPU acceptance passes 51 isolated Rust tests, Clippy,
release compilation and compilation of the separate CUDA module. Device exactness,
all four sanitizer suites and end-to-end timing remain pending; no GPU preparation
speedup is established by compilation or host tests.

## Unattributed GPU memory

The idle inventory exposed approximately 10 GiB of device usage without a listed
compute, graphics or MPS owner. The installed NVML header confirms the queried
process structure layout; driver-reserved memory explains only about 637 MiB.
The cause remains unknown. The device is not considered available solely because
instantaneous utilization is zero, and no unrelated process or device is reset.

[Amendment 7](../specifications/SPEC-0046-amendment-7.md) adds a fixed 2 GiB ceiling
on total memory minus attributed process memory, including driver usage. Process
inventories bracket the memory query to account for context transitions. An audit
of retained capacity traces excludes both 512 M image-v2 timings: all their samples
exceed the ceiling. Original successful resource receipts, full charges and
responses remain intact, and numerical assessment continues independently. Earlier
observations retain their existing status; sampled telemetry cannot rule out all
smaller unlisted activity. No affected scientific cell is retried.

[Amendment 8](../specifications/SPEC-0046-amendment-8.md) permits only the six named
CPU input-construction jobs after fresh CPU resource acceptance while GPU admission
waits. It does not permit GPU execution on the occupied device. The billion-nonzero
solve cohort and GPU preparation performance claim remain unfinished.

Operational GPU v7 began after the original idle-memory level returned, then
stopped after 35 seconds when unattributed memory reappeared. The guard reports
that reason explicitly and verifies empty cleanup. Its full 480 CPU / 120 GPU
seconds and partial admission responses remain; the preparation module had not
started. [Amendment 9](../specifications/SPEC-0046-amendment-9.md) requires five
minutes of observed idle availability before fresh operational GPU v8. This is
an operational admission failure, with no repeated scientific measurement.

Both 512 M responses now pass independent final/intermediate checking, while their
timings remain ineligible. All six originals contain exactly one billion nonzeros
and pass strict construction checks. Construction witnesses remain separate from
solver inputs; these are not billion-scale solve results.
[Amendment 10](../specifications/SPEC-0046-amendment-10.md) includes a possible
repaired certificate dual in complete endpoint-storage reservations. Before any
billion-scale solve, the common iteration ceiling will be chosen within the full
roster's memory, storage and time allowance, retaining the unchanged certificate.

## Ready billion-nonzero originals

| Family | Rows | Columns | Original nonzeros | Canonical FP4-covered nonzeros |
| --- | ---: | ---: | ---: | ---: |
| Irregular | 62,500,000 | 62,500,000 | 1,000,000,000 | 0 |
| Wide | 62,500,000 | 250,000,000 | 1,000,000,000 | 0 |
| Tall | 62,500,000 | 15,625,000 | 1,000,000,000 | 0 |
| Coupled blocks | 15,625,000 | 15,625,024 | 1,000,000,000 | 750,000,000 |
| Ill-scaled | 62,500,000 | 62,500,000 | 1,000,000,000 | 0 |
| Degenerate | 62,500,000 | 62,500,000 | 1,000,000,000 | 0 |

Each family has its own generated coefficient stream and a verified connectivity
backbone. The coupled original has 976564 eligible tiles. The other families
remain necessary sparse coverage; requesting FP4 on these inputs selects FP32.
The six supervised generation/construction-check jobs consume 11517.112111744
CPU seconds and zero GPU seconds, with empty cleanup. Full native, FP32 and FP4x2
solves, their strict final/intermediate checks and total-time comparisons remain
pending.

## Validation checkpoint

The retained capacity ladder has 18 frozen cells, 17 responses, 15 eligible timings
and one missing response. Every completed cell stops at its 100-update limit
without certification; none establishes successful-solve benefit. Both 256 M cells
and both timing-excluded 512 M cells have independent final and intermediate
checks. The original 128 M interruption is retained without retry.

Native acceptance passes 638 Rust and 835 Python tests. Images v1/v2 each pass
60 exact GPU continuation comparisons and four 20-case sanitizer suites; these
admissions do not cover the new preparation module. The GPU preparation candidate
passes 51 isolated Rust tests, formatting, Clippy, release compilation and CUDA
compilation. The current continuation/resource/evidence harness passes 21 tests. The
unchanged original supervisor passes 75 contract tests in operational CPU v7.
The checkpoint verifies 293 numerical source bindings, both older image bindings,
all six original construction certificates and all retained capacity audits.

Seven failed reservations retain their complete sources and 26400 CPU / 600 GPU
seconds: two early build/sealing failures, one native-memory refusal, the 128 M
interruption, one preparation compile precheck, operational GPU v7, and one
portable catalog failure. The catalog's overly broad lock-file filter omitted
retained `Cargo.lock` files; their original bytes remain intact. The corrected
filter excludes only the live root allocation locks and has a regression test.
The failed catalog and full 7200 CPU-second charge remain. Every
later completed job has empty cleanup. The original false 128 M cleanup receipt
is preserved alongside its separate later proof that the owned identities ended.

The guarded continuation is `python3 -B tools/lp_billion_prepare_continue.py`.
It first requires five minutes of observed idle availability, then performs fresh
operational admission, bitwise preparation comparisons, four sanitizers and the
new capacity cohorts. It refuses to repeat failed or unsettled reservations.
No detached GPU job is scheduled while availability is unknown. Final billion-scale
limits must be frozen separately after these stages pass and their costs settle.

The [source-bound checkpoint](lp-billion-checkpoint.json) and
[64 M comparison](lp-billion-64m-results.json) retain the detailed measurements and
missingness. The [evidence receipt](lp-billion-evidence.json) binds the local catalog,
relocated replay, acceptance and resource receipts. Corrected portable replay
verifies 33729 files, 49158 references and 3364 array references, including 458
array-form response records and 1123 assessment records referencing 49 distinct
chunked witnesses. It reads from a relocated hardlinked root without accessing
the original repository. Hashing covers 122725480889 bytes; the temporary root is
removed afterward. This is integrity validation, separate from the numerical
scalar audits. Later compact administrative receipts supplement the catalog.

At the delivery checkpoint the device reports approximately 78 GiB used and 99%
utilization. GPU preparation exactness, sanitizer acceptance, capacity measurements
and all billion-scale solves remain pending. Compilation and construction checks
do not establish a reduction in preparation or complete solve time.

## Resources and retained evidence

The separate allocation is 240000 CPU / 30000 GPU seconds, four CPU slots,
128 GiB sampled aggregate RSS, 80 GiB owned device buffers and 400 GiB owned storage
under `/storage/ai-optimizer-billion-v1`. The one-second supervisor and every
100 ms advisory remain. Sampled RSS is not a hard peak enclosure. GPU charges use
the pinned job's elapsed reservation time, including host work, rather than active
kernel time. Failed reservations retain their entire charge and sources.

Only UUID `GPU-6721b13a-30f9-83ec-dace-ba2d9738556f`, the RTX PRO 6000 Blackwell
Server Edition, may execute GPU jobs. Three idle observations precede each lease;
compute, graphics and MPS ownership are continuously checked. Foreign use or failed
telemetry stops only this job's processes. Live host/device/storage headroom is
required in addition to the declared ceilings.

The earlier general allocation remains unchanged and open at
222683.436386676 CPU / 29019.968674596 GPU seconds. New results supplement the full
historical public/lower-scale roster and capacity refusals. Large evidence stays
local; public adoption, publication and confirmation are separate decisions.

The new allocation's open settled checkpoint is 61442.317804716 CPU /
2870.821030734 GPU seconds, including every full failed reservation. No reservation
is active, and the temporary replay root is removed. Documentation validation
passes 307 pages with local links and anchors checked. This checkpoint leaves the
GPU-dependent work pending; it does not close the allocation or establish a speedup.

## Container-only memory investigation

The user requests investigating unattributed memory, specifically checking whether
our earlier program retained it. The user explicitly prohibits leaving the
container. The [diagnostic and process-audit receipt](lp-billion-ownership.json)
records read-only checks; no CUDA context, device reset, configuration change or
signal to another process is used.

Six observations spanning five minutes within a six-minute diagnostic window show
10.542 GiB total usage and zero instantaneous utilization. NVML memory v2 separates
10651566080 allocated bytes (9.920 GiB) from 667877376 reserved bytes (0.622 GiB),
agreeing with memory v1's total. Driver reservation alone does not explain the
excess. All nine compute/graphics/MPS process queries across legacy, v2 and v3
return success with empty lists; `pmon` also shows no process. MIG and virtualization
are disabled. The NVIDIA driver library is loaded from its system path;
there is no `LD_PRELOAD` interposition in the inspected environment.

The container marker is present, PID 1 is `entrypoint.sh`, and the visible procfs
has 35 processes during the recorded scan. None holds an NVIDIA or DRM device
handle; no process-directory read is denied. The NVIDIA driver client list is not
exposed. Kernel-log access is denied, and the container journal has no kernel
entries. No host namespace, host filesystem or SSH access is attempted.
Linux procfs visibility follows PID namespaces, so this scan cannot identify an
owner outside the visible namespace. This is a visibility limit, not proof of a
particular external owner. See the [Linux PID namespace documentation](https://man7.org/linux/man-pages/man7/pid_namespaces.7.html)
and [NVIDIA's process-visibility guidance](https://docs.nvidia.com/health-validation/operating/integration#process-and-filesystem-exposure).

The leak audit examines 2056 retained resource receipts across the experiment
allocations and matches 191104 distinct recorded PID/start-time identities against
current procfs. None survives. It preserves the original false-cleanup 128 M
receipt and verifies its later cleanup evidence separately. The CUDA wrapper uses
owned buffers, streams and contexts with free/destroy calls on drop. Historical
successful execution does not establish that every destructor returned success;
source inspection alone is not proof against a driver leak.

The memory timeline provides stronger evidence about the large runs: the recorded
128 M interruption remains at 804978688 bytes (0.750 GiB), and the device returns
to that same baseline after both 512 M runs and before operational GPU v7. Thus
the current excess was not continuously retained from those large experiments.
The final interrupted v7 admission has 42 raw array responses, with at most
1901420 declared solver-buffer bytes (1.81 MiB), plus unquantified context/module
overhead. All its recorded identities have ended. After this last GPU reservation,
observed usage varies from 8.888 to 77.825 GiB with utilization reaching 99%, while
our subsequent jobs are CPU-only. This does not establish an external owner, but
it is evidence against a surviving ordinary solver allocation causing all current
usage.

No surviving solver process or inherited visible GPU handle is found. A
driver-level orphan allocation cannot be conclusively excluded with the available
container-only telemetry. Process inventories are also empty in retained traces
during our own GPU runs, so those inventories cannot independently attribute
allocations. The fixed 2 GiB unexplained-memory limit remains unchanged; empty
inventories and zero instantaneous utilization do not waive it. GPU preparation
validation, new timing comparisons and all billion-scale solves remain pending.
The new preparation CUDA module has still never executed. Both diagnostic jobs
finish with empty cleanup and zero GPU charge; their CPU charges are recorded in
the linked receipt. No failed or scientific measurement is repeated.

A subsequent supervised six-minute idle-confirmation window starts at the original
0.750 GiB baseline, rises to 5.584 GiB, returns to 0.750 GiB, then reaches 65.451 GiB
and 70% utilization. No solver or preparation GPU job starts anywhere in this
investigation; operational GPU v8 remains unattempted. These release/reallocation
cycles further argue against memory continuously retained by our earlier solver
processes. They do not identify the unseen owner or conclusively diagnose a driver
fault. The required uninterrupted five-minute idle window never passes. An
additional process-detail API also returns empty inventories for raw modes 0–2;
raw mode 3 is explicitly rejected as an invalid argument and is not counted as an
empty inventory.

All three supervised diagnostic/observation jobs finish with empty cleanup and
zero GPU charge. The allocation remains open at 64401.039603840 CPU /
2870.821030734 GPU seconds, including the documentation check; no reservation is
active. The current metadata supplements the earlier portable catalog. The
scientific inputs, binaries, strict certificate checks and historical results are
unchanged, and there is still no GPU preparation performance result or billion-scale
solve result to report.

## GPU preparation device validation

This section retains the earlier partial checkpoint; the next section records
completion and subsequent measurements.

The [compact admission receipt](lp-billion-preparation-admission.json) binds the
completed checks, all three GPU interruptions, partial observations and current
source checkpoint. The earlier portable catalog remains unchanged; these new
source-bound local receipts supplement it.

After the user reports that the Pro6000 appears idle, a new observed window reaches
six uninterrupted minutes at 804978688 bytes (0.750 GiB) and zero utilization. A
fresh final observation and the normal three-sample preflight also pass.
Operational GPU v8 then completes all 60 exact continuation checks. Unlike the
earlier empty inventories, retained telemetry now identifies owned GPU processes
in 55 of its 169 samples and 100 of the subsequent numerical admission's 295
samples. This confirms attribution during these jobs; it does not explain why
earlier inventories were empty or identify the earlier unattributed owner.

A read-only NVML client stays open across the observation/admission handoff.
No persistence setting, CUDA context, driver configuration or host-namespace access
is used by this monitor. NVIDIA documents transient driver-initialization work,
including ECC scrubbing, but that is only a possible explanation for some brief
activity; it does not explain or attribute the large historical allocations. See
[NVIDIA driver lifecycle documentation](https://docs.nvidia.com/deploy/driver-persistence/latest/overview.html).
Every original idle and ownership guard remains active.

The unchanged image-v3 preparation module executes for the first time:

| Check | Completed result |
| --- | --- |
| Full preparation comparison | 66 bitwise matches: 57 actual FP64 GPU preparations and nine explicit host fallbacks |
| Solve continuation comparison | 60 exact continuations, including recovery/cancellation; 130 independent strict scalar checks |
| Complete memcheck admission | Seven GPU preparation cases, one exact host fallback, 20 solve continuations and 60 independent strict scalar checks |
| Racecheck | Incomplete; partial results retained |
| Initcheck and synccheck | Not started |
| New 64/256/512 M timing cohorts | Not started |
| Billion-nonzero LP solves | Zero |

The first memcheck reservation invokes the sanitizer on the 1025-term CPU fallback.
Its exact raw response reports zero allocated device bytes, but the sanitizer exits
because the target makes no CUDA call. Six preceding GPU cases have zero errors.
The corrected harness checks the fallback normally and keeps fatal instrumentation
for every actual GPU case. The complete fresh memcheck v4 suite passes; the failed
v3 receipt and full charge remain. [Amendment 11](../specifications/SPEC-0046-amendment-11.md)
records the correction without changing numerical code or certificate criteria.

Racecheck v3 reaches 17182568448 sampled host bytes during the recursive-norm
fixture and is stopped at its 16 GiB reservation. Its partial log is not a completed
check. [Amendment 12](../specifications/SPEC-0046-amendment-12.md) introduces three
analysis workers, stream synchronization after at most eight launches and a 64 GiB
host reservation within the existing 128 GiB allocation. It retains all kernels,
fixtures and fatal errors. Racecheck v4 completes two small preparations, then the
unchanged ownership guard stops it as unattributed memory exceeds 2 GiB. The last
retained owned process accounts for only 32 MiB while total usage exceeds 2.2 GiB;
later read-only telemetry reaches 5.390 GiB with no listed process. No external
owner or driver fault is inferred from that visibility gap.

All three interrupted admissions have empty cleanup and retain full additional
2880 CPU / 720 GPU-second charges. At this point the allocation retains ten failed
reservations totaling 29280 CPU / 1320 GPU seconds. No scientific cell starts or
repeats. [Amendment 13](../specifications/SPEC-0046-amendment-13.md) prospectively
transfers unused phase capacity within the unchanged 240000 CPU / 30000 GPU totals:
CPU implementation/admission become 6000/16000 seconds, and GPU
admission/development become 3000/27000. Other phase ceilings and physical limits
stay unchanged. Fresh operational CPU v8 passes 75 original supervisor tests and
22 resource/evidence tests. Operational GPU v9 requires another uninterrupted
five-minute idle window before the remaining sanitizer admissions or scientific
work. Strict original-model certificates remain unchanged; no preparation or total
solve speedup is yet measured.

The subsequent CPU-only idle-confirmation v5 stops after approximately 300 seconds
with `lost_coordinator_heartbeat`. Its five retained diagnostic samples show
5.390–5.597 GiB used, no listed owner and zero instantaneous utilization; all fail
the fixed memory guard. Its final result is missing and is not reconstructed.
Empty owned-process cleanup and the full 1920 CPU / zero GPU-second charge are
retained. The monitor closes without starting operational GPU v9. This brings the
allocation to eleven failed reservations retaining 31200 CPU / 1320 GPU seconds.
[Amendment 14](../specifications/SPEC-0046-amendment-14.md) requires fresh CPU
acceptance before the pending GPU admission. Operational CPU v9 passes all 75
original supervisor and 22 resource/evidence tests. A fresh observation still
fails at 5.836 GiB unattributed usage.

The final evidence check verifies all 293 numerical source bindings, the completed
admissions' scalar comparisons, and that none of the 72 retained process identities
from the three interrupted GPU admissions survives. It preserves all previous
17 capacity responses, 15 eligible timings and the missing 128 M cell. No new
scientific timing or billion-scale solve is reported. The allocation remains open
at 75147.503818756 CPU / 3764.416660567 GPU seconds including final documentation.
All 311 documentation pages and their local links validate; no reservation is
active.

## GPU preparation timings and host memory

The [compact results receipt](lp-billion-gpu-preparation-results.json) binds the
complete admission, paired measurements, independent audits and final capacity
snapshot. The user authorizes use of the full Pro6000. All work stays inside the
container, on the pinned UUID, with the original idle/ownership guards, strict
certificates and existing resource ceilings. No device reset, configuration change,
host access or signal to another job occurs.

Idle-confirmation v6 observes seven samples across six minutes at the original
0.750 GiB baseline and zero utilization. Operational GPU v9 passes 60 exact
continuations. The image-v3 numerical preparation comparison retains 66 bitwise
matches and 60 exact solve continuations. Memcheck v4, racecheck v6, initcheck v3
and synccheck v3 now all pass: each covers seven actual GPU preparations, one
explicit host fallback and 20 solve continuations, with independent strict scalar
checking. The recursive-norm case retains its original 20 power iterations; no
fixture, kernel or hazard coverage is removed. All 293 numerical source bindings
remain exact. The solve CUDA image, numerical Rust, public defaults, 100-update
control and 500-update certification are unchanged.

Before any v3 scientific cell starts, a harness regression exposes a loop-variable
shadowing error that could overwrite cohort-qualified cell identities.
[Amendment 15](../specifications/SPEC-0046-amendment-15.md) corrects that orchestration
error; the fresh harness v6 passes all 22 resource/evidence tests including exact
cell-identity assertions. No attempted scientific cell is repeated.

The proposed 64 GiB racecheck host declaration fails physical preflight before a
reservation exists. [Amendment 16](../specifications/SPEC-0046-amendment-16.md)
prospectively declares 56 GiB with unchanged headroom and sampled-RSS limits.
Racecheck v5 then reaches its 240-second CPU wall guard in the deep-norm case;
its partial results, empty cleanup and full 960 CPU / 240 GPU seconds remain.
[Amendment 17](../specifications/SPEC-0046-amendment-17.md) authorizes a fresh
600-second admission reservation. Complete racecheck v6 takes 430.933 charged GPU
seconds and passes all original checks. The failed v5 run remains a failed run.

Every new 64/256/512 M response agrees exactly with its image-v2 numerical
transcript, excluding timing/allocation fields, and every final/intermediate
assessment is independently checked against the original model. All ten endpoints
reach the 100-update limit without certification. Ratios below are v2/v3; above
one means faster with GPU preparation. Complete cost includes the fresh solve
process and independent final original-model check.

| Nonzeros | Family | Preparation | Assessment | Process | Complete cost | v3 complete seconds |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 64M | irregular | 3.034 | 0.924 | 1.506 | 1.338 | 42.385 |
| 64M | wide | 3.890 | 0.925 | 1.652 | 1.399 | 61.813 |
| 64M | tall | 2.769 | 0.907 | 1.484 | 1.286 | 36.061 |
| 64M | coupled blocks | 2.458 | 0.967 | 1.382 | 1.219 | 27.889 |
| 64M | ill scaled | 2.983 | 0.943 | 1.531 | 1.300 | 41.824 |
| 64M | degenerate | 2.811 | 0.951 | 1.470 | 1.266 | 40.198 |
| 64M | Descriptive median | 2.897 | 0.934 | 1.495 | 1.293 | — |
| 256M | irregular | 4.043 | 0.947 | 1.887 | 1.476 | 194.067 |
| 256M | coupled blocks | 2.760 | 0.947 | 1.484 | 1.307 | 110.362 |
| 256M | Descriptive median | 3.401 | 0.947 | 1.686 | 1.392 | — |

The separate cohort medians are descriptive and are not cumulative speedups.
Assessment regresses in every eligible pair; those costs remain included. The
coupled cases execute 75% of accepted product nonzeros through actual FP4, with
complete-cost speedups of 1.219x at 64 M and 1.307x at 256 M. Other families have
no eligible canonical FP4 tiles and select FP32. These shared preparation gains
do not establish broad FP4 superiority or certified full-solve benefit.

The two new 512 M runs have valid absolute timings. Both older 512 M timings remain
excluded by their original ownership dispositions, so no paired timing ratio or
speedup is reported for this scale:

| 512 M family | v3 preparation seconds | v3 process seconds | v3 complete seconds |
| --- | ---: | ---: | ---: |
| Irregular | 92.272 | 262.952 | 406.709 |
| Coupled blocks | 58.147 | 154.080 | 237.678 |

The initial 256 M independent-audit host preflight refuses before creating a
reservation. [Amendment 18](../specifications/SPEC-0046-amendment-18.md) declares
32/40 GiB for the never-started 256/512 M audits, based on earlier same-checker
peaks of 8.751/17.392 GiB. The full unchanged independent audits then pass. Their
900/1800-second time reservations, physical headroom and sampled-RSS stops stay
intact; no solve declaration or certificate criterion changes.

### Billion-scale host capacity

The retained post-run snapshot finds the GPU idle at 0.750 GiB, but only
62.364 GiB of host MemAvailable. All eighteen prospective native/FP32/FP4x2 cells
fit device capacity. None fits host headroom: the smallest declaration requires
79 GiB including the mandatory 4 GiB headroom, and the widest requires 130 GiB.
Full GPU access does not supply the missing host RAM. No other job or shared
memory is disturbed, and no billion-scale scientific cell starts or is frozen.

All six one-billion-original-nonzero inputs remain ready. Once physical host
capacity permits the roster, prospectively select the largest common 500-update
ceiling up to 5000 that fits complete solve, intermediate/final audit and endpoint
storage reservations, including possible repaired dual witnesses. Keep strict
1e-9 criteria, control100/certificate500, all eighteen native/FP32/FP4x2 cells and
all historical failures/missingness. `tools/lp_billion_prepare_continue.py` has
completed its preparation admissions and ten capacity cells; the final billion
cohort needs its own freeze and execution, not a repeat of these measurements.

### Updated evidence and resources

The checkpoint retains 28 frozen capacity cells, 27 responses, 25 eligible timings
and the original missing 128 M response. All twelve failed reservations preserve
full charges totaling 32160 CPU / 1560 GPU seconds. New completed reservations
have empty cleanup and no overrun; no reservation is active. The original 128 M
false-cleanup receipt and later independent cleanup proof both remain intact.
The earlier relocated portable catalog remains unchanged; the new source-bound
admission, comparison, audit and capacity receipts supplement it. No new full
portable replay is claimed.

Open settled checkpoint including final documentation: 86933.674672092 CPU /
5341.824658053 GPU seconds of the unchanged 240000 CPU / 30000 GPU allocation.
All 315 documentation pages and their local links validate. The earlier general
allocation remains unchanged. Results and changes are committed
locally only; no public adoption, confirmation or publication is released.

## Borrowed host matrix storage

The [compact memory receipt](lp-billion-memory-results.json) binds the admitted
image-v4, complete sanitizer suites, ten paired runs, independent audits, numerical
source comparisons and fresh physical-capacity snapshot. This follows the user's
request to reduce host memory; it does not reduce numerical precision.

The billion-scale executor previously cloned both orientations' canonical u32
indices and scaled FP64 coefficients into its operator while the original arrays
remained alive. It now borrows those immutable slices through Rust lifetimes;
compact u32 offsets stay owned. Legacy constructors still own their data, and
packing residuals remain owned. The original model, scaled engine values, CPU
control and strict certificate checks retain their existing arithmetic and order.
The existing `operator_storage_bytes` response field describes logical referenced
storage, so it remains numerically unchanged; sampled process RSS measures the
physical reduction.

At one billion nonzeros, the eliminated arrays contain 24 billion bytes
(22.352 GiB). Their former capacity allowance was 24 GiB. The versioned admission
formula subtracts only that copy allowance and preserves every other allocator,
context, I/O, state, packing and certificate allowance, including mandatory
4 GiB physical headroom. The change and validation are prospective under
[amendment 19](../specifications/SPEC-0046-amendment-19.md).

### Validation and resource handling

All 52 isolated Rust tests, formatting, Clippy and release/CUDA builds pass. The
new regression checks actual shared pointers, exact products and complete FP4
packing for rectangular matrices with empty terminal axes and component counts
one through four. Fresh operational CPU acceptance passes 75 original supervisor
and 24 resource/evidence tests, including numeric readmission ordering and the
versioned memory allowance. A fresh six-minute idle window precedes operational
GPU v10, which passes 60 original-image continuations.

Image-v4 then passes 66 exact preparation comparisons, 60 exact solve continuations
and 130 independent scalar checks. Memcheck, racecheck, initcheck and synccheck each
pass eight preparation cases (seven GPU and one explicit host fallback), 20 solve
continuations and 60 independent strict scalar checks. Racecheck retains the full
recursive-norm fixture and its original 20 power iterations. Its actual peak RSS
is 7.817 GiB and its GPU charge is 389.945 seconds. All completed new reservations
have empty cleanup and no overrun.

The first compile reservation fails because an existing mutation test needs the
explicit owned-write API for the new storage type. Its source and full 480 CPU /
zero GPU-second charge remain; the corrected complete acceptance has a fresh job
identity. Later, the proposed 56 GiB racecheck declaration fails physical preflight
before any racecheck reservation exists. Based on the previous complete same-suite
7.604 GiB peak, [amendment 20](../specifications/SPEC-0046-amendment-20.md) prospectively
declares 32 GiB with unchanged checks, 600-second ceiling and physical headroom.
No failed reservation or scientific cell is repeated.

[Amendment 21](../specifications/SPEC-0046-amendment-21.md) separately reserves each
complete paired transcript comparison at 32 GiB / 600 seconds. Its existing
endpoint expansion and numerical comparison remain unchanged. The final metadata
audit also verifies exact content-addressed endpoint manifests without expanding
another set of Python vectors. Neither step replaces the independent original
scalar checker.

Both preparation and solve CUDA binaries remain byte-identical. Of the 293 prior
numerical source bindings, 289 remain exact; the four changed files are the
operator representation, billion executor call site, packing storage adapter and
existing/new regression tests. All original retained source bytes verify. Public
sources/defaults, strict original-model 1e-9 criteria, control100/certificate500,
GPU idle/ownership guards and container-only access remain unchanged.

### Measured memory and complete cost

Every final/intermediate assessment is independently checked, and all ten full
image-v3/v4 numerical transcripts agree exactly. All are uncertified 100-update
limit endpoints. Memory below is supervised sampled aggregate peak host RSS.
Complete cost includes the fresh process and independent final original-model
check. Ratios are v3/v4; values above one mean faster with borrowed storage.

| Nonzeros | Family | v3 peak GiB | v4 peak GiB | Complete-cost ratio | v4 complete seconds |
| --- | --- | ---: | ---: | ---: | ---: |
| 64M | irregular | 6.074 | 4.631 | 1.044 | 40.599 |
| 64M | wide | 7.721 | 6.292 | 1.096 | 56.388 |
| 64M | tall | 5.811 | 4.066 | 1.112 | 32.416 |
| 64M | coupled blocks | 5.355 | 3.898 | 1.053 | 26.489 |
| 64M | ill scaled | 5.975 | 4.630 | 1.045 | 40.005 |
| 64M | degenerate | 6.068 | 4.354 | 1.100 | 36.544 |
| 256M | irregular | 23.690 | 17.983 | 1.041 | 186.480 |
| 256M | coupled blocks | 20.853 | 15.222 | 1.063 | 103.823 |
| 512M | irregular | 47.209 | 35.777 | 1.018 | 399.487 |
| 512M | coupled blocks | 41.642 | 30.260 | 1.082 | 219.753 |

| Cohort | Median RSS reduction | Preparation ratio | Assessment ratio | Complete-cost ratio |
| --- | ---: | ---: | ---: | ---: |
| 64M | 25.5% | 1.130 | 1.024 | 1.075 |
| 256M | 25.5% | 1.167 | 1.012 | 1.052 |
| 512M | 25.8% | 1.115 | 0.960 | 1.050 |

These separate descriptive medians are not cumulative speedups. All complete-cost
pairs improve, but the 64 M coupled assessment and both 512 M assessments regress;
retain those observations and their full costs. The valid 512 M comparisons use
image-v3 controls. The earlier image-v2 512 M ownership exclusions remain intact.
Coupled cases still execute 75% of accepted product nonzeros through FP4; other
families select FP32. These results establish reduced memory for this implementation,
not certified convergence or broad FP4 superiority.

### Revised billion-scale headroom

The new post-run snapshot finds the GPU idle at its 0.750 GiB baseline and
60.781 GiB of host MemAvailable. The smallest native/FP32 coupled declaration falls
from 75 to 51 GiB, or 79 to 55 GiB with physical headroom. The widest declaration
falls from 126 to 102 GiB, or 130 to 106 GiB with headroom. Actual-FP4 coupled
needs 68 GiB plus headroom. Exactly two of eighteen prospective cells now fit
host capacity: native and FP32 coupled. No FP4 lane fits, and all fit GPU capacity.

No billion-scale cell is frozen or attempted. Preserve the full eighteen-lane
objective and six ready one-billion-original-nonzero inputs. Final execution still
requires sufficient physical host memory and a prospective largest common
500-update ceiling up to 5000 that fits complete solve/audit/storage reservations,
including repaired dual witnesses. Do not substitute the two fitting native/FP32
cells for the FP4 objective or weaken certificates or resource guards.

### Updated allocation and evidence

The unchanged totals are 240000 CPU / 30000 GPU seconds. Amendment 19 transfers
unused development capacity prospectively: CPU admission/development become
28000/118000; GPU admission/development become 5500/24500. Other phase caps and
all physical ceilings remain unchanged. Operational readmission v10 binds the
transfer, with numeric version ordering so v10 follows v9.

The combined capacity record retains 38 cells, 37 responses, 35 eligible timings
and the original missing 128 M response. Thirteen failed reservations retain full
32640 CPU / 1560 GPU seconds. No new failed scientific cell is introduced. The
original false-cleanup receipt and its later independent proof both remain.
Earlier portable catalogs and their replay results remain unchanged; the new
source-bound receipts supplement them, with no new full portable replay claimed.

Open settled checkpoint including final documentation: 98505.269208520 CPU /
6712.970278844 GPU seconds. The allocation remains open and no reservation is active.
All 318 documentation pages and their local links validate. The earlier general
allocation remains unchanged. Commit locally only; no public
adoption, confirmation or publication is released.
