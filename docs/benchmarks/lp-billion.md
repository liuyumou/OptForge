# Billion-nonzero LP development on the Pro6000

The authorized billion-nonzero comparison is complete: eighteen project runs and
3 supported COPT GPU attempts (0 returned responses), preserving strict original-model 1e-9 checking.
Three project runs and 0 COPT runs certify; all limits and capacity refusals
remain visible. FP4 accelerates coupled device advancement but does not reduce
its complete cost. See [full results](#approved-recovery-and-billion-execution),
[phase timings](lp-billion-full-phases.csv) and [compact evidence](lp-billion-full-results.json).
Updated 2026-11-21 under [SPEC-0046](../specifications/SPEC-0046-billion-lp.md).
Historical checkpoints below retain their original scope and failures.

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
complete paired transcript comparison at 32 GiB / 600 seconds. A later source
review corrects its description of endpoint expansion: the campaign comparator
already compares exact content-addressed manifests without expanding vectors.
The small-fixture admission comparator does unpack arrays. This correction is
recorded prospectively in [amendment 22](../specifications/SPEC-0046-amendment-22.md);
the original protocol, resource receipts and numerical results remain intact.
Neither comparison replaces the independent original scalar checker.

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

## Indexed preparation packing

The next candidate, image-v5, reduces host work that remains after GPU scaling
and norm estimation. Under [amendment 22](../specifications/SPEC-0046-amendment-22.md),
the isolated array executor appends qualifying tiles in canonical sorted order
and uses direct indices when constructing both packed orientations. It reuses
touched-column scratch between row groups. The encoder, fragment layouts,
exponents, coverage and residual order remain exact.

When no tile qualifies, the previous implementation still built complete residual
copies for both orientations before the caller discarded the packed operator.
The candidate validates every original-transpose coefficient and then returns
without constructing those unused residual arrays. It retains this validation
even on the empty-tile path. Legacy packing interfaces and public defaults remain
unchanged. The conservative capacity allowance also remains unchanged; eliminated
transient work does not automatically reduce the declared memory requirement.

New timing partitions expose engine construction, borrowed-operator construction,
packing and control initialization. Their integer nanosecond sum must exactly
match the existing preparation interval. Input hashing/loading stays separate
and remains included in fresh-process and complete cost. The engine interval
includes GPU preparation and its transfers; the GPU's existing internal timings
remain available separately.

CPU acceptance passes 53 isolated Rust tests, formatting, Clippy and release/CUDA
builds. Complete packed representations match the retained original packer across
one to four components, both fragment layouts, rectangular tails and the parallel
packing threshold. A corrupted transpose still refuses when no tile qualifies.
Fresh operational CPU acceptance passes 75 supervisor and 25 resource/evidence
tests, including a regression that timing-only fields cannot hide numerical changes.

### Operational interruption retained

The first six-minute idle window passes, but operational GPU v11 stops after about
15 seconds with `lost_coordinator_heartbeat`. It uses the prior image-v2; no
candidate GPU work starts. Its eight new and eight reference response files,
source bindings, ownership trace, empty cleanup and full 480 CPU / 120 GPU-second
charge remain. All three retained process identities are subsequently absent.
No cause or GPU-memory owner is inferred.

[Amendment 23](../specifications/SPEC-0046-amendment-23.md) prospectively requires
fresh operational v12 with unchanged limits and a new sustained-idle observation.
The second observation records a brief 8.506 GiB / 99% utilization burst while
no GPU job from this task is active. It ends without a passing idle span, and the
explicit observed-idle guard prevents admission. A separate third observation
retains that history and requires its own complete idle result. The failed
operational reservation is not repeated, and no scientific cell has been retried.

The third six-minute observation passes at the original idle baseline. Operational
GPU v12 nevertheless stops after about 18 seconds with the same heartbeat reason,
retaining nineteen partial new response files, empty cleanup and another full
480 CPU / 120 GPU seconds. Neither operational run reaches image-v5 admission.
The repeated supervision failure remains unresolved; no timeout, ownership guard
or certificate requirement is weakened. All candidate GPU comparisons, sanitizers
and full-solve timing cohorts remain pending.

### CPU-only packing diagnostic

[Amendment 24](../specifications/SPEC-0046-amendment-24.md) permits a separate
CPU-only diagnostic while GPU readmission remains incomplete. It links the same
candidate library and prepares each of the six retained 64 M original models with
the unchanged CPU engine. Both packers receive those exact same scaled arrays.
One paired measurement per input alternates reference-first and candidate-first
order. The reference includes destruction of the unused zero-tile residuals,
as image-v4 does. Input loading, engine construction and operator setup are timed
separately from packing. The diagnostic executes no LP solve and creates no CUDA
context. All packed fields, including FP64 bit patterns, are compared when tiles
qualify; both paths must return no packed operator otherwise.

### Allocation and component encoding refinements

The first diagnostic retains all six image-v5 responses, including a coupled
regression from 3.858 to 3.994 seconds. Its intermediate Rust library was bound
at a mutable Cargo target path and was overwritten by the next quality build
before archival. [Amendment 26](../specifications/SPEC-0046-amendment-26.md) preserves
this missing binding explicitly and excludes all six timings. The measured
executable, source snapshots, exact results and full resource charges remain.
Subsequent diagnostic builds copy both linked libraries into immutable evidence
before compilation and measurement.

[Amendment 25](../specifications/SPEC-0046-amendment-25.md) introduces image-v6:
it uses tile values as exact quantization scratch, releases them before orientation
construction, and preallocates output arrays using verified counts. All six fresh
CPU pairs are exact and have durable linker artifacts. Five zero-tile cases improve,
but coupled regresses from 3.619 to 3.841 seconds (0.942x); this valid regression
remains in the report and evidence.

The next proposal in [amendment 27](../specifications/SPEC-0046-amendment-27.md)
uses explicit SIMD encoding. Its first quality reservation stops with incomplete
cleanup and a receipt-finalization timeout during directory fsync. The original
receipt and full 1200 CPU-second charge remain; a subsequent independent check
finds all five retained process identities absent, as recorded by
[amendment 28](../specifications/SPEC-0046-amendment-28.md). The fresh quality attempt
then reaches compilation and refuses unsafe Rust under the existing crate lint,
retaining another full 1200 CPU seconds and empty cleanup.

The final image-v7 follows [amendment 29](../specifications/SPEC-0046-amendment-29.md):
safe, portable branchless threshold comparisons and exact binary64 bit construction
replace the component quantizer branches and decoder table. Maximum reduction,
exponent selection, component order and separate FP64 arithmetic remain exact.
There is no unsafe code, target-feature dispatch or measured SIMD instruction claim.
The original encoder remains the independent reference.

Fresh quality acceptance passes all 54 isolated Rust tests, formatting, Clippy
and release/CUDA compilation. New coverage compares codes, exponents and every
residual bit across adjacent rounding thresholds, signed zeros, scales and vector
tails. Fresh operational CPU acceptance passes the original 75 supervisor and 25
resource/evidence tests. No GPU candidate admission or full-solve measurement is
inferred from these CPU results.

### Final packing-stage results

The [compact packing receipt](lp-billion-packing-results.json) binds the final
image, all three diagnostic cohorts, current source verification, explicit
exclusions, failed charges and fresh host-capacity observation. All six final
pairs are exact and have complete supervision with empty cleanup and zero GPU
charge. Times below are the packing stage on 64 M original-nonzero inputs.

| Family | Original packing seconds | Image-v7 packing seconds | Ratio | Time reduction |
| --- | ---: | ---: | ---: | ---: |
| irregular | 5.529 | 3.182 | 1.737 | 42.4% |
| wide | 5.726 | 3.734 | 1.533 | 34.8% |
| tall | 5.183 | 2.730 | 1.898 | 47.3% |
| coupled blocks | 3.693 | 3.362 | 1.099 | 9.0% |
| ill scaled | 5.443 | 3.110 | 1.750 | 42.9% |
| degenerate | 4.673 | 2.515 | 1.858 | 46.2% |

The median per-case ratio is 1.744x, with a median
packing-time reduction of 42.6%.
Coupled contains 62,500 eligible FP4 tiles and improves by 9.0%; the other five
models have no eligible tiles. These single paired stage observations use
alternating order and do not establish repeatability, full preparation gains,
GPU execution gains or certified total-solve benefit. Input, engine and operator
costs remain in the raw results and supervised process costs. No stage timing
is substituted for a complete solve measurement.

All 296 current numerical source bindings verify. Of the 293 image-v4 bindings,
289 stay exact and four isolated implementation/test files change; three new
files contain the packer, component encoder and standalone diagnostic. Both CUDA
binaries and all six original budget/idle/supervisor/placement source bindings
remain exact. Public defaults, strict original-model 1e-9 certificates and
control100/certificate500 remain unchanged.

### Remaining admission and resource state

Image-v7 has never executed on the GPU. Its preparation comparisons, continuations,
four full sanitizer suites and fresh 64/256/512 M full-solve comparisons remain
pending. Image-v5/v6 GPU cells were also never attempted. Investigate the repeated
operational supervision interruptions before fresh operational GPU v15; then
require a new complete observed-idle result, fresh final proof and every original
gate. Plans v15/v16 preserve both cleanup dispositions and the CPU-only job scope.
`tools/lp_billion_packing_cpu_v3.py` is complete; no diagnostic cell should repeat.
The future GPU continuation is `tools/lp_billion_packing_continue.py`.

The post-run snapshot sees 52.026 GiB host MemAvailable and
5.131 GiB device usage, failing the instantaneous idle gate. No owner
is inferred. None of eighteen prospective billion-scale cells fits current host
headroom: declarations still require 55–106 GiB including physical headroom, with
72 GiB for actual-FP4 coupled. The six original billion-nonzero inputs remain ready,
but zero billion-scale solves have run and the final cohort remains unfrozen.
Retain the full FP4 objective and prospective common 500-update ceiling up to 5000
once full solve/audit/storage and physical capacity permit.

The full-solve capacity record is unchanged at 38 cells / 37 responses / 35 eligible
timings / one old missing response. The separate CPU diagnostic record has eighteen
responses, twelve eligible stage timings and six explicit first-cohort exclusions.
Seventeen failed reservations retain full 36000 CPU / 1800 GPU seconds. The latest
quality-v3 false-cleanup receipt remains alongside its independent five-identity
cleanup proof. All later completed cleanup is empty; no reservation is active.
Old portable catalogs remain unchanged. New source-bound receipts supplement them;
no fresh full portable replay or resolution of the missing first-cohort library
is claimed. No total allocation or phase cap changes.

Open settled checkpoint including final documentation: 110219.293992796 CPU /
6952.970278844 GPU seconds. The separate 240000 CPU / 30000 GPU allocation
remains open, and the earlier general allocation is unchanged. All 326 documentation
pages and their local links validate. Commit locally only; no public adoption,
confirmation or publication is released.

## Billion-scale component timings and installed COPT

The next billion-scale comparison has a prospective roster of all six original
one-billion-nonzero models and five lanes: native, FP32, FP4x2, COPT CPU auto and
COPT GPU PDLP. **No billion-scale solve or COPT performance comparison has run.**
The roster remains unfrozen. The final capacity observation has 60.45 GiB host RAM
available and an instantaneously idle Pro6000 at its usual baseline. Only two of
our eighteen prospective lanes fit host headroom; the coupled FP4 lane requires
72 GiB and the full project roster requires up to 106 GiB. COPT's billion-scale
peak memory and native API GPU ownership remain unadmitted. Array storage lower
bounds do not constitute peak-memory admission. No GPU job starts in this update.

Opt-in timing image-v8 adds twenty exclusive host-wall phases. Their sum must equal
the recorded solver interval exactly. The outer ledger adds original input loading,
profile finalization, process startup/serialization/cleanup, response persistence
and independent final checking, with every residual exposed. Existing preparation
and GPU preparation details remain nested and are never summed twice. Both scaling
and spectral preparation already synchronize their streams; device advance already
waits for its flag read. These are host-wall costs including launch and completion
overhead, not kernel-active durations. All timer overhead remains included.

| Cost | Project solver | Installed COPT native API |
| --- | --- | --- |
| Original input | Chunk hashing, validation and original-model construction, including transpose | Chunk hashing and validation into preallocated arrays |
| Preparation | Engine, operator, FP4 packing, initial control and device setup; nested scaling and spectral/norm/step estimation | Library/environment, configuration, CSR-to-CSC conversion, model import and input release |
| Iteration/control | Device advance, endpoint download, checkpoint, original-model control, restart/weight control, upload and recovery | Native solve call; internal presolve, scaling and iteration costs remain opaque |
| Assessment/output | Unscale, strict certificate, certificate reuse, witness output and response assembly | Endpoint extraction and bounded binary output; vendor status does not certify an endpoint |
| Complete cost | Fresh solver process, response persistence and independent final check | Same complete-cost definition; installation hash work is separately exposed |

Original input construction and solver preparation must both be visible when
comparing preparation costs: the two imports place sparse transposition in different
phases. COPT's reported `SolvingTime` is nested within its opaque solve call and
must not be added again. Log delivery is not an internal phase timer. Offline
intermediate audits remain separate from complete single-solve cost. Update counts
and vendor iterations are different units. Common wall allowances and the largest
common project update ceiling in 500-update increments up to 5000 still require
prospective full solve/check/audit/storage reservations before the final freeze.

The `/root/copt80` installation is COPT 8.0.6. Its direct C API adapter avoids a
Python object per coefficient: it preallocates each binary array, verifies bounded
chunks, converts canonical CSR to CSC and extracts primal/dual arrays directly.
Native sparse, bound and objective arrays are checked bitwise on small admission
models; objective senses and offsets also roundtrip exactly. Finite values colliding with COPT's infinity sentinel are
refused. Native parameter types come from the installed header; every configured
value is read back. The current small CPU admission uses four threads, CPU auto,
`MatrixTol=0`, feasibility/duality tolerances `1e-9` and a **soft** 12000 MB vendor
memory limit. That value is not a billion-scale allowance or a hard enclosure.
The native GPU adapter path fails closed pending its own resource admission.
Library/header hashes and Python/NumPy/SciPy versions are retained without copying
license material.

CPU admission completes twelve cases. Nine returned endpoints—including both
objective senses, free/fixed/ranged/empty geometry and all six generated small
families—pass the unchanged independent original-model `1e-9` checker. Infeasible,
unbounded and preparation-deadline cases retain their distinct outcomes. Preparation
counts against the common solver wall budget; a deadline exhausted during import
prevents a solve call. These are adapter checks, not performance comparisons or
billion-scale measurements. No construction witness enters a solve.

Image-v8 passes 57 isolated Rust tests, formatting, Clippy, release compilation and
CUDA compilation. All 36 final billion resource/evidence/timing tests pass, including
native `MemLimit` typing, corrupted chunks, accounting gaps and certificate fields
that must survive numerical transcript comparison. Of 297 numerical bindings,
293 remain exact from image-v7, three existing files gain timing instrumentation
and one timer module is added. Both CUDA binaries and all six budget, idle,
supervisor and placement sources remain exact. Strict certificates, numerical
arithmetic, public defaults and control100/certificate500 remain unchanged.
Image-v8 has not executed on the GPU; exact continuation and all four sanitizer
gates remain mandatory before scientific use.

Four new failed admissions retain their complete sources and charges: two builds
stop on resource-sampling durations above one second, default Python lacks SciPy,
and the first native COPT adapter sends `MemLimit` through the integer API. All
cleanup is empty. The failed builds retain full 1200 CPU seconds each; the Python
and COPT failures retain 180 and 480 CPU seconds. Existing three-plus-one CPU
placement alone did not resolve sampling. Fresh serialized Cargo compilation
passes the full quality suite without changing the one-second or 100 ms checks.
Fresh contracts use the already installed COPT Python environment; corrected
native parameter typing passes all twelve cases. No failed reservation or attempted
scientific cell is repeated or overwritten. The record now retains 21 failed
reservations charged 39060 CPU / 1800 GPU seconds in total.

The separate 240000 CPU / 30000 GPU allocation remains open with unchanged phase
caps and physical limits. Previous full-solve capacity counts remain 38 cells,
37 responses, 35 eligible timings and one missing response; the eighteen prior
CPU packing responses retain twelve eligible timings and six exclusions. Old
portable catalogs remain unchanged; no fresh full portable replay is claimed.
Container-only, idle/ownership and physical-headroom rules remain in force.

[Compact timing/COPT results](lp-billion-timing-copt-results.json) bind the large
local evidence at `/storage/ai-optimizer-billion-v1/timing-copt-delivery-v1.json`,
`copt-native-cpu-v2/result.json`, `billion-comparison-plan-v1.json` and
`billion-host-availability-v5.json`. The final settled ledger is retained as
`timing-settled-checkpoint-v1.json`. Protocol and dispositions:
[amendment 30](../specifications/SPEC-0046-amendment-30.md),
[31](../specifications/SPEC-0046-amendment-31.md),
[32](../specifications/SPEC-0046-amendment-32.md),
[33](../specifications/SPEC-0046-amendment-33.md) and
[34](../specifications/SPEC-0046-amendment-34.md) and
[35](../specifications/SPEC-0046-amendment-35.md).
The [final supplemental checkpoint](lp-billion-timing-copt-checkpoint.json) binds
the corrected 36-test harness admission and fully settled allocation totals.


## Bounded preparation storage and peak memory

The opt-in image-v9 reduces the conservative coupled billion-scale host
requirement from **72 to 68 GiB**, including the unchanged 8 GiB internal allowance
and 4 GiB physical headroom. This is a prospective full-solve requirement, not a
measured full-solve peak. The initially derived 60 GiB estimate omitted the CPU
fallback's construction transient and is explicitly superseded. The earlier
72 GiB declaration remains historical; future reference admission would also need
the complete fallback and repaired-witness accounting.

The packer uses two ordered sparse passes, exact-length final arrays and a bounded
256-tile work batch. It no longer retains all dense tile coefficients/codes,
per-nonzero coverage flags or lists of half tiles. Both orientations retain the
same coefficient bits, fragment order and original transpose validation. FP32
proposal uploads reuse at most 32 MiB of conversion scratch. The checked offset
copy synchronizes before its borrowed host slice is reused. After synchronous
device upload, host packed arrays are released before creating controller,
checkpoint, residual and certificate workspace. All upload and lifetime overhead
remains inside the recorded phase and complete costs.

The unchanged CPU fallback sets the coupled conservative peak: it briefly retains
the prepared scaled matrices while cloning them into the engine. Its streamed Pock work
and spectral scratch are now explicit in the bound. This remaining cost
also means that less packing residency need not reduce a CPU preparation's overall
high-water RSS. No strict-checker arrays, original FP64 coefficients, arithmetic,
certificate criteria, public defaults or control100/certificate500 policy change.

| Billion original-nonzero family, FP4x2 | Previous declaration, GiB | Corrected candidate, GiB | Candidate limiting stage |
| --- | ---: | ---: | --- |
| irregular | 85 | 76 | CPU engine construction |
| wide | 106 | 107 | solve and certificate |
| tall | 81 | 72 | CPU engine construction |
| coupled blocks | 72 | 68 | CPU engine construction |
| ill scaled | 85 | 76 | CPU engine construction |
| degenerate | 85 | 76 | CPU engine construction |

All entries include physical headroom. Wide increases because repaired-dual witness
storage is now explicit; no improvement is claimed for it. Device reservations
are unchanged. These bounds apply to the frozen native/FP32/compact-FP4x2 settings,
not arbitrary component counts or representations.

### Fresh-process CPU measurements

The protocol freezes reference/candidate CPU preparations on all six 64 M models
and coupled 256 M, plus one candidate-only billion preparation. Every implementation
runs in a fresh process. Reference packing source is byte-identical to image-v8;
engine/scaling/norm preparation is shared and unchanged. Complete packed-array
SHA-256 values include integer arrays, FP64 bits, metadata and both orientations.
Input, engine, operator, packing, digest and process costs remain separately visible.
Digesting uses bounded scratch and is excluded from preparation but included in the
process cost. VmHWM is a per-process high-water mark; sampled aggregate RSS is
retained separately and is not an exact aggregate peak.

The coupled 64 M candidate retains a complete raw response, but its final bound
assertion fails because the first formula omitted two terminal residual offsets:
eight bytes. Its full 960 CPU-second reservation, sources, raw values and empty
cleanup remain. Its performance is excluded and the cell never repeats. The
corrected formula includes all terminal entries. Seven initial attempts and eight
never-attempted tail cells retain disjoint identities. Before the billion cell could
start, an additive disposition corrects its CPU host reserve from 56 to 64 GiB.
The original freeze and provisional bounds remain intact.

CPU acceptance passes 58 isolated Rust tests, including exact representation
comparisons across worker batches, plus the offset-copy overflow/range test.
Formatting, Clippy and release/CUDA compilation pass. Fresh operational CPU v17
passes 75 original supervisor tests and 42 resource/evidence/timing/memory tests.
Numerical image-v9 and its diagnostic executable are unchanged by the accounting
corrections. Exact GPU continuations, chunk-upload exercise and all four complete
sanitizer suites remain mandatory before full solves; image-v9 has not run on GPU.

The [compact memory results](lp-billion-bounded-memory-results.json) bind each
response, timing exclusion, source manifest and complete charge. Protocol and
additive dispositions are [amendment 36](../specifications/SPEC-0046-amendment-36.md),
[37](../specifications/SPEC-0046-amendment-37.md) and
[38](../specifications/SPEC-0046-amendment-38.md) and
[39](../specifications/SPEC-0046-amendment-39.md). Formula 5 retained an unnecessarily
loose public-Pock term-graph upper bound; final formula 6 uses the isolated streamed
implementation. Every original reservation remains unchanged.

### Measured results and remaining limits

All seven paired packed-array hashes match, including the retained failed raw
candidate. Fourteen reservations pass; that one candidate retains its exclusion.
The six eligible performance pairs comprise five 64 M families and coupled 256 M.
No attempted cell repeats.

| Model | Reference peak RSS, GiB | Candidate peak RSS, GiB | Reference packing, s | Candidate packing, s |
| --- | ---: | ---: | ---: | ---: |
| 256m coupled blocks | 14.040 | 14.040 | 14.430 | 15.484 |
| 64m coupled blocks | 3.512 | 3.512 | 3.302 | excluded |
| 64m degenerate | 4.026 | 4.027 | 2.474 | 2.449 |
| 64m ill scaled | 4.026 | 4.026 | 3.038 | 3.039 |
| 64m irregular | 4.026 | 4.026 | 3.056 | 2.955 |
| 64m tall | 3.725 | 3.725 | 2.585 | 2.734 |
| 64m wide | 5.251 | 5.251 | 3.663 | 3.396 |

Overall CPU high-water RSS is essentially unchanged: engine construction peaks
before packing. At 256 M, resident RSS immediately after packing falls from
12.898 to 12.133 GiB
(5.9%), but packing time regresses by
7.3% and complete CPU preparation
regresses from 68.769 to 72.756 seconds.
Both observations remain eligible. These are single observations and do not
establish a repeatable speedup, GPU upload performance or certified solve benefit.

The candidate-only preparation of **1,000,000,000 original nonzeros** completes,
with 976,564 canonical FP4 tiles and 750 million eligible nonzeros. It uses
54.806 GiB per-process peak RSS and
54.898 GiB sampled aggregate peak RSS within its
64 GiB host reservation. The final packed arrays occupy 7.734 GiB;
resident RSS after packing is 47.155 GiB. Its
complete packed hash is retained. There is no reference billion preparation and
no paired billion memory or speedup claim.

| Billion CPU preparation component | Seconds |
| --- | ---: |
| Original input loading, hashing and transpose | 108.361 |
| CPU engine: scaling, norms and step estimation | 271.795 |
| Borrowed operator validation | 7.130 |
| Bounded FP4 packing | 72.607 |
| Complete preparation (engine + operator + packing) | 351.532 |
| Full packed-array fingerprint | 15.193 |
| Process bookkeeping, memory samples, serialization and teardown residual | 2.706 |
| Fresh process total | 477.791 |

The preparation subtotal is nested; do not add it to its three components. This
run creates no CUDA context and executes no LP updates or certificates. It is a
full-size preparation diagnostic, **not a billion-scale LP solve**. Strict checker
sources remain unchanged; new device behavior still requires its mandatory gates.

All 299 current numerical bindings verify: 291 of image-v8's 297 stay exact,
six isolated implementation/test/boundary files change, and two files add the
retained reference and diagnostic. Both CUDA binaries and all six original
budget/idle/supervisor/placement bindings remain exact. Final capacity contracts
pass all 42 tests after the source-specific correction. Twenty-two failed
reservations retain full 40020 CPU / 1800 GPU seconds. New cleanup is empty,
including the failed assertion; all owned diagnostic process identities are gone.

The post-run snapshot has 176.460 GiB host MemAvailable,
so all eighteen prospective project cells fit their current host declarations.
The GPU is instantaneously idle at 0.750 GiB; this is not a
five-minute observed-idle admission. Image-v9 exact GPU continuations, chunk-copy
exercise and four sanitizers remain pending. All six original billion LP inputs
remain ready. The full thirty-cell project/COPT comparison remains unfrozen;
COPT GPU ownership and billion-scale peak admission are still required. Zero
billion LP solves have run. Fresh complete GPU admission reservations must fit
the remaining phase budgets before execution; no phase cap is changed here.

The original full-solve capacity counts remain 38/37/35 with one missing response;
the eighteen older CPU packing responses retain twelve eligible timings and six
exclusions. Existing portable catalogs are unchanged and no new full portable
replay is claimed. The separate 240000 CPU / 30000 GPU allocation remains open,
with unchanged physical guards and the earlier general allocation unchanged.
Large evidence is local under `/storage/ai-optimizer-billion-v1`; commit locally
only, with no public adoption or publication.

Open settled checkpoint: 119590.941904424 CPU / 6952.970278844 GPU seconds.
All 336 documentation pages and local links validate.
Final settled evidence: `bounded-memory-settled-checkpoint-v1.json`.

## GPU admission and COPT capacity interruption

Image-v9's device validation is now complete. Operational CPU v18 passes 75
supervisor and 42 resource tests; the later complete-harness v2 passes 45 Python
contracts and builds the standalone chunk-copy diagnostic. A retained earlier
compiler-path failure has its full 480 CPU-second charge. A six-minute idle
observation precedes operational GPU v16. The candidate then passes 66 bitwise
preparation comparisons, 60 exact solve continuations, and complete memcheck,
racecheck, initcheck and synccheck suites. Each sanitizer covers eight preparation
cases, including the explicit host fallback, and twenty continuations. Full
racecheck keeps twenty deep-norm power iterations and charges 405.777 GPU seconds.
The separate copy diagnostic transfers 16,777,233 float elements in three chunks,
including a seventeen-element final chunk, and verifies every bit. It exercises
the admitted bounded upload boundary on the real device.

Both CUDA binaries and all 298 numerical files in the image-v9 build binding stay
exact. Two supplemental diagnostics bring current numerical source bindings to
300. Public defaults, solver arithmetic, strict original-model 1e-9 certificates,
control100/certificate500 and GPU ownership/idle guards remain unchanged. Only
allocation phase constants changed in the common module, under amendment 40;
the other five guard implementations remain exact. These device admissions are
correctness results, not billion-scale total-time measurements.

The new native COPT adapter binds the installed 8.0.6 libraries, four threads,
original binary arrays and strict independent checker. GPU PDLP uses the inherited
pinned lease, method 6, no crossover and PDLPTol=1e-12, with actual GPU log and
owned-process evidence. CPU auto remains separate. Full admission v1 stops when
a small ill-scaled GPU solve times out without an endpoint; its harness wrongly
required an endpoint. Preserve its full 960 CPU / 240 GPU-second failure. Corrected
admission v2 records all 24 small outcomes, independently checks all seventeen
returned endpoints and accepts all seventeen at the unchanged strict tolerance.
The ill-scaled timeout is retained without certification.

The prospective COPT capacity roster starts at 64 million original nonzeros:

| Family/lane | Fresh process plus final check (s) | Process peak RSS (GiB) | Outcome |
| --- | ---: | ---: | --- |
| Coupled / CPU auto | 47.483 | 6.644 | Time limit, no endpoint |
| Coupled / actual GPU PDLP | 53.145 | 6.743 | Time limit, no endpoint |
| Degenerate / GPU PDLP | Excluded | Not a completed peak estimate | Reservation overrun; missing response |

Both completed cells have no final-check cost because COPT returns no solution.
Their requested common solver wall is thirty seconds after original input loading,
including model conversion/import. The vendor memory ceiling is soft, and internal
solver phases remain opaque. No vendor status substitutes for strict certification.

I assigned a 100-second process reservation to each 64 M capacity cell. That was
insufficient for the degenerate GPU initialization path: COPT had printed its GPU
PDLP start but returned neither an iteration result nor an endpoint before the
supervisor terminated the owned process family. The receipt retains
400.620150944 CPU / 100 GPU seconds, `overrun=true`, and `cleanup_empty=false` at
settlement. Subsequent PID/start-time inspection verifies all recorded identities
are gone; that supplemental proof never rewrites the original receipt. The latest
read-only sample is zero utilization and 0.750 GiB device usage. No GPU reset,
configuration change, host access or other-job signal occurs.

The unchanged budget guard closes execution on this overrun. The remaining nine
64 M cells, all 256/512 M COPT capacity cells, and the complete billion-scale roster
remain unattempted. The interrupted cell must never be retried. A proposed tail
uses larger reservations only for never-started cells. Any unsupported lane remains
visible; successful capacity or ownership cannot be inferred from the missing
response.

The [recovery proposal](../specifications/SPEC-0046-amendment-43.md) awaits explicit
user authorization. It requests cumulative totals of 320000 CPU / 35000 GPU seconds,
compared with the existing 240000 / 30000, plus a source-bound readmission for this
one retained overrun after fresh operational checks. Physical limits and strict
certificates remain unchanged. The full-roster worksheet reserves 173000 additional
CPU / 21450 GPU seconds for thirty 600-second-wall solves and their complete
independent audits at a common 500-update ceiling; larger ceilings are rejected
prospectively under that proposal. These are reservation ceilings, not measured
solve times or a guarantee of convergence. No allocation extension or readmission
has yet been applied.

New draft audit tooling preserves distinct final/intermediate endpoints after
checkpoint restoration, checks repaired-dual bindings, and reuses proofs only for
identical model/settings/endpoint identities. Its five new regression tests have
not run because resource execution is closed. It is not admitted for science.
No fresh full portable replay or documentation-suite pass is claimed.

The [compact checkpoint](lp-billion-completion-status.json) binds detailed evidence
at `/storage/ai-optimizer-billion-v1/complete-device-checkpoint-v1.json`. There are
25 retained failed reservations with 41860.620150944 CPU / 2140 GPU seconds. Settled
usage is 126194.902614812 CPU / 8047.349848722 GPU seconds. No reservation is active;
the allocation ledger remains open while its execution guard is closed. The earlier
general allocation remains unchanged. No result is published or adopted publicly.

## Approved recovery and billion execution

The approved continuation is complete. All eighteen supported project runs on six
connected LPs with **one billion original matrix nonzeros each** return results,
and every final/intermediate assessment passes independent agreement checking.
Three runs certify: all three tall-family lanes. The other fifteen retain their
update-limit or deadline outcomes. The original twelve default-COPT billion slots
remain unsupported. A separate COPT GPU PDLP configuration with Presolve=0 attempts
3 supported billion runs and returns 0 responses; 0 pass the same strict certificate.
All six slots of that supplemental roster remain visible below.

The user's explicit approval and [amendment 44](../specifications/SPEC-0046-amendment-44.md)
authorize cumulative 320000 CPU / 35000 GPU seconds and recovery of only the exact
recorded overrun. Fresh operational CPU v20 passes 75 supervisor / 59 resource
tests; a six-minute idle window and GPU v17's sixty exact continuations pass.
The failed stale-allocation CPU v19 test retains its full 720 CPU-second charge.
The original COPT overrun and all other failed reservations retain their full
charges and sources. No attempted scientific cell repeats. Four CPU slots,
128 GiB sampled aggregate host RSS, 80 GiB owned device buffers, 400 GiB owned
storage, physical headroom and every idle/ownership guard remain unchanged.
All work and read-only ownership inspection remain inside the container.

The [full-run protocol](../specifications/SPEC-0046-amendment-46.md) prospectively
selects 1000 updates as the largest common 500-update increment fitting all
supported solve, strict final/intermediate audit and endpoint/repaired-witness
storage reservations. Control100/certificate500 and normalized original-model
1e-9 criteria stay exact. The requested solver allowance is 600 seconds after
original loading; mandatory final checks and opaque vendor calls can overshoot.
Actual elapsed costs, including overshoots, appear below. A valid proof arriving
after a deadline never regrades that outcome as a certified solve.

### Full project results

`native` means GPU FP64. Every lane uses admitted image-v9 GPU preparation.
Solver preparation below sums engine, operator, packing and initial control;
it excludes original input/transpose and device setup, which are separate phases.
Complete cost includes the fresh process and a cold independent final proof.
Additional distinct intermediate proofs are retained as offline audit cost.

| Family | Lane | Accepted updates | Outcome | Solver preparation (s) | Complete cost (s) | Solver peak RSS (GiB) |
| --- | --- | ---: | --- | ---: | ---: | ---: |
| irregular | native | 1000 | limit | 45.338 | 975.699 | 58.571 |
| irregular | fp32 | 1000 | limit | 48.482 | 904.558 | 58.571 |
| irregular | fp4x2 | 1000 | deadline | 118.434 | 973.036 | 58.575 |
| wide | fp32 | 700 | deadline | 63.254 | 1303.536 | 93.643 |
| wide | fp4x2 | 500 | deadline | 148.698 | 1159.189 | 93.656 |
| wide | native | 700 | deadline | 69.554 | 1171.363 | 93.643 |
| tall | fp4x2 | 1000 | certified | 107.482 | 865.903 | 50.387 |
| tall | native | 1000 | certified | 38.760 | 761.347 | 50.387 |
| tall | fp32 | 1000 | certified | 39.111 | 734.962 | 50.362 |
| coupled_blocks | native | 1000 | limit | 31.844 | 502.028 | 42.767 |
| coupled_blocks | fp32 | 1000 | limit | 35.243 | 461.850 | 42.767 |
| coupled_blocks | fp4x2 | 1000 | limit | 112.173 | 511.561 | 47.193 |
| ill_scaled | native | 1000 | limit | 43.927 | 966.265 | 58.587 |
| ill_scaled | fp32 | 1000 | limit | 43.654 | 917.496 | 58.597 |
| ill_scaled | fp4x2 | 1000 | deadline | 119.476 | 985.309 | 58.601 |
| degenerate | native | 1000 | limit | 41.587 | 918.601 | 58.574 |
| degenerate | fp32 | 1000 | limit | 41.882 | 840.538 | 58.574 |
| degenerate | fp4x2 | 1000 | limit | 108.754 | 900.003 | 58.578 |

Only coupled_blocks performs actual FP4 arithmetic: 75% of accepted product work.
The other FP4x2 requests select FP32 because they have no eligible canonical tiles.
Wide native/FP32 accept 700 updates after 800 physical attempts; wide FP4x2 accepts
500 after 600 physical attempts. Those deadline comparisons have different work
and cannot be described as equal-work speedups. All returned endpoint checks,
including rejected and deadline endpoints, remain in the compact evidence.

### Where the coupled solve spends its time

All three coupled runs accept 1000 updates and remain uncertified. Their complete
exclusive phase accounting is:

| Exclusive phase | GPU FP64/native (s) | FP32 (s) | FP4x2 (s) |
| --- | ---: | ---: | ---: |
| Original input and transpose | 108.633 | 64.196 | 64.286 |
| GPU-backed preparation engine | 22.179 | 22.681 | 23.010 |
| Operator and initial control | 9.664 | 12.561 | 14.369 |
| FP4 packing | 0.000 | 0.000 | 74.794 |
| Device setup | 6.410 | 11.901 | 9.617 |
| Device advance | 39.700 | 32.119 | 8.182 |
| Original-model control | 53.615 | 53.923 | 52.762 |
| Restart/weight control | 34.057 | 34.338 | 33.806 |
| Internal strict certification | 81.102 | 82.198 | 82.005 |
| Cold independent final proof | 132.452 | 132.253 | 132.836 |
| All other measured phases | 14.214 | 15.678 | 15.894 |
| **Complete cost** | **502.028** | **461.850** | **511.561** |

FP4 device advancement is 4.85x faster than GPU FP64 and 3.93x faster than FP32.
However, packing costs 74.794 seconds, exceeding the 23.937 seconds saved against
FP32 advancement. Complete FP4 cost is 511.561 seconds versus 461.850 for FP32
and 502.028 for GPU FP64. Thus this run does **not** establish a total-solve FP4
benefit. Input timing also varies: 108.633 / 64.196 / 64.286 seconds for native,
FP32 and FP4; these are fresh processes without flushed caches, with one rotated
repetition. No broad repeatable superiority is claimed.

The FP4 preparation engine itself is 23.010 seconds. Its nested GPU telemetry
records 0.429 seconds of scaling, 0.680 of spectral products, 5.632 of setup and
10.901 of download. These are subintervals, not extra costs to add to the table;
remaining engine work is included in its total. Twenty power iterations remain.
Zero-eligible FP4 requests also incur packing: irregular 74.153 seconds, wide
78.331 and tall 67.921. Avoiding that unnecessary packing and reducing actual
FP4 packing, original-model control and repeated assessment are measured next
targets; no unvalidated numerical change is adopted in this completed cohort.

`input_hash_validation` includes chunk reading/hashing/decoding, canonical
validation **and original CSR-to-CSC construction**. It is not pure disk I/O.
Device advancement is wall time around GPU work, not kernel-active time. All
exclusive phases, including checkpointing, uploads/downloads, witness output,
teardown and process/response overhead, are in the [phase CSV](lp-billion-full-phases.csv).
The [compact JSON](lp-billion-full-results.json) retains nested preparation
telemetry, physical/accepted work, proofs, capacity refusals and comparisons.

### Installed COPT comparison

The original automatic-presolve COPT CPU-auto and GPU-PDLP baseline remains
capacity-unsupported in all twelve billion slots. Its completed capacity responses
have zero optimization iterations; three 256 M cells and one 512 M cell retain
owned-child interruptions. The nine never-started 64 M tail cells complete.
Setup-only responses cannot establish full optimization workspace, and several
memory forecasts exceed the admitted limits. These are capacity dispositions,
not measured billion-scale timings or evidence that project solves beat COPT.
See [amendment 48](../specifications/SPEC-0046-amendment-48.md).

The separately identified [Presolve=0 variant](../specifications/SPEC-0046-amendment-49.md)
uses the same installed COPT 8.0.6 in `/root/copt80`, four threads, GPU PDLP,
MatrixTol=0, FeasTol=DualTol=1e-9, PDLPTol=1e-12 and no crossover. Its unchanged
48000 MB vendor memory setting is soft; measured process and device memory guards
remain authoritative. Nine contracts and twelve small admission cases pass,
including eight independently certified optima. It then attempts all ten frozen
64/256/512 M capacity cells before freezing its separate six-slot billion roster.
Every smaller observed path must demonstrate optimization workspace and fit the
prospective growth/headroom forecast. Missing, interrupted and setup-only paths
remain disqualifying; forecasts are empirical, not hard bounds on vendor internals.

| Family | Outcome | PDLP iterations | Strict certificate | Complete cost (s) | Solver peak RSS (GiB) |
| --- | --- | ---: | --- | ---: | ---: |
| irregular | Unsupported: missing/interrupted/unconfirmed optimization workspace | — | No | — | — |
| wide | Unsupported: host forecast exceeds 128 GiB; device forecast exceeds 80 GiB | — | No | — | — |
| tall | Attempted; missing response | — | No | Excluded | Missing |
| coupled_blocks | Unsupported: missing/interrupted/unconfirmed optimization workspace | — | No | — | — |
| ill_scaled | Attempted; missing response | — | No | Excluded | 59.068 (partial) |
| degenerate | Attempted; missing response | — | No | Excluded | 69.703 (partial) |

The tall COPT attempt stops without a response or a retained process HWM. Its
original settlement records cleanup_incomplete with no overrun and retains the full
3600 CPU / 900 GPU-second charge. Subsequent exact PID/start-time checks prove all
four owned identities gone; the GPU returns to the idle baseline. [Amendment 50](../specifications/SPEC-0046-amendment-50.md)
uses the existing non-overrun cleanup/readmission path, fresh CPU v21, a complete
idle window and GPU v18 before the two untouched cells. It does not retry tall or
change its failure. The original guardian receipt overwrites the preceding stop
trigger, so the underlying cause is unresolved. Partial sampled memory cannot
serve as a completed optimizer-workspace measurement. Ill-scaled and degenerate
both reach their owned-child cutoffs without responses. Each retains the full
3600 CPU / 900 GPU seconds and settles with empty cleanup and no overrun. Failed attempts have no complete-cost
timing or recovered phase profile. The CSV retains observed child/reservation
durations where available and marks interrupted process memory as partial.

COPT's iteration count is not directly comparable with project updates. The
same requested 600-second solver allowance and original-model certificate criteria
apply, but project runs also have the common 1000-update ceiling. A time limit
without an endpoint has no independent final-proof cost and cannot establish a
certified-solve speedup. Vendor internal preprocessing and execution are opaque;
the CSV separates measurable input, adapter CSC/import, the vendor call, extraction,
teardown and final checking. Adapter preparation is not all vendor preparation.

### Memory, validation and retention

Project solver process peaks range from 42.767 to 93.656 GiB. These kernel-
recorded process HWMs differ from the sampled aggregate owned-process peak, which
includes coordination, and from the separately measured independent audit peak.
All three measures and the sampled owned GPU peak appear in the phase CSV.
Memory limits and strict checks were preserved; the bounded representation now
permits these full billion-nonzero runs. This cohort has no paired old-image
billion solve, so it does not establish a before/after billion-scale memory or
GPU-preparation speedup. Earlier paired preparation results retain their own scope.

Image-v9's 66 bitwise preparation comparisons, sixty exact solve continuations,
all four complete sanitizers, and bounded-copy diagnostic remain applicable.
Numerical Rust/CUDA, both CUDA binaries, all 300 numerical source bindings and
public defaults stay exact. Full-run contract tests and three real strict-checker
replays admit the deadline-aware independent auditor. Final harness, documentation,
source-binding and owned-process verification are recorded in the final checkpoint.
The prior portable catalog remains unchanged; no new full portable replay is claimed.

Large evidence remains local under `/storage/ai-optimizer-billion-v1`, including
`full-billion-v1/freeze.json`, `copt-nopresolve-1b-v1/freeze.json`, complete raw
responses and strict final/intermediate audits. All failures, missing responses,
unsupported slots and regressions remain visible. The approved allocation stays
open, and the earlier general allocation stays unchanged. Local commit only;
no public adoption, confirmation or publication is released.

Open settled allocation: 235329.259157332 CPU / 26771.899422302 GPU seconds within 320000 / 35000. No reservation is active. 88 billion-harness tests and 347 documentation pages/local links pass. All 300 numerical bindings remain exact. 34 failed reservations retain full 61060.620150944 CPU / 6520.000000000 GPU seconds. Final settled evidence: `full-billion-settled-checkpoint-v1.json`; compact checkpoint: `docs/benchmarks/lp-billion-full-checkpoint.json`.


## GPU FP4 packing and zero-eligible fast path

The opt-in image-v10 array executor moves structural eligibility counting,
coefficient-domain and exact transpose validation, residual extraction and normal
E2M1 encoding to a separate GPU module. It returns before allocating packing
fragments or residual arrays when no tile qualifies. The redundant CPU coefficient
scan is deferred to the GPU validator only for this opt-in path. Host work retains
sorted canonical metadata and offsets; a bounded structural-hash overflow explicitly
uses the exact CPU packer. Both matrix orientations retain identical packed bits.
The first implementation downloads canonical Packed and uses the unchanged device
initializer, so these transfers and context costs remain in measured total time.

Public defaults, the original FP64 preparation and solve CUDA modules, strict
original-model 1e-9 certification, control100/certificate500 and all resource guards
remain unchanged. The exact storage inventory now uses a source-bound native
counter to stay within the same supervision limit as the evidence tree grows;
it still traverses every file, deduplicates hardlinks and excludes symlinks and
directories. Independent recompilation, legacy-counter comparisons and fresh
CPU/GPU operational gates admit that resource change. CPU acceptance passes 60 isolated Rust tests,
formatting, Clippy, release and CUDA compilation. Device admission passes
81 bitwise packing comparisons,
6 malformed-input rejections,
60 exact solve continuations and
130 independent strict scalar checks.
All four complete sanitizers cover the packing suite and twenty solve continuations
each. The new exponent batches include subnormals, the exponent clamp and neighbors
of powers of two and six. Unchanged preparation kernels retain their prior complete
admission, including the original twenty deep-norm iterations.

The fresh six-family paired 64 M cohort uses 100 updates and rotated version order.
Its descriptive preparation / complete-cost median ratios are
1.844x / 1.106x.
All failed, regressing and uncertified outcomes remain in the compact results.

| Family | Packing before / after (s) | Preparation before / after (s) | Complete before / after (s) | Updates before / after | Certified before / after |
| --- | ---: | ---: | ---: | ---: | --- |
| irregular | 3.118 / 0.533 | 5.926 / 3.225 | 32.038 / 29.381 | 100 / 100 | False / False |
| wide | 3.585 / 0.543 | 8.084 / 4.521 | 49.432 / 44.826 | 100 / 100 | False / False |
| tall | 2.825 / 0.525 | 5.418 / 2.928 | 26.023 / 23.428 | 100 / 100 | False / False |
| coupled_blocks | 3.559 / 0.900 | 5.881 / 3.069 | 21.831 / 19.472 | 100 / 100 | False / False |
| ill_scaled | 3.097 / 0.513 | 5.897 / 3.037 | 31.885 / 28.759 | 100 / 100 | False / False |
| degenerate | 2.430 / 0.527 | 5.167 / 3.116 | 29.065 / 27.417 | 100 / 100 | False / False |

The six new one-billion-original-nonzero solves use the retained 1000-update ceiling,
600-second requested solver allowance and strict independent final/intermediate
checks. Their image-v9 controls are historical runs: these are descriptive
comparisons across runs, with no randomized paired billion-trial claim. Deadline or
update-count differences remain explicit. The descriptive preparation / complete
median ratios are 2.473x /
1.035x, with 1 jointly
certified pairs. Uncertified bounded runs do not establish certified-solve speedup.

| Family | Packing before / after (s) | Preparation before / after (s) | Complete before / after (s) | Updates before / after | Certified before / after |
| --- | ---: | ---: | ---: | ---: | --- |
| irregular | 74.153 / 8.098 | 118.434 / 47.749 | 973.036 / 955.000 | 1000 / 1000 | False / False |
| wide | 78.331 / 8.244 | 148.698 / 67.644 | 1159.189 / 1248.923 | 500 / 700 | False / False |
| tall | 67.921 / 5.930 | 107.482 / 40.709 | 865.903 / 787.538 | 1000 / 1000 | True / True |
| coupled_blocks | 74.794 / 11.391 | 112.173 / 38.368 | 511.561 / 486.850 | 1000 / 1000 | False / False |
| ill_scaled | 75.038 / 8.145 | 119.476 / 48.449 | 985.309 / 977.887 | 1000 / 1000 | False / False |
| degenerate | 61.494 / 6.486 | 108.754 / 46.492 | 900.003 / 838.991 | 1000 / 1000 | False / False |

The 5 equal-update historical pairs have descriptive preparation / complete-cost median ratios of 2.480x / 1.051x. 3 retain exact full numerical transcripts. Equal update counts do not by themselves establish certification or remove cross-run input/cache variability.

The other two equal-update records, irregular and ill-scaled, differ only in
terminal status: the historical deadline becomes an iteration limit. Their
numerical fields remain exact, while the original full-transcript flags remain
false. The wide case completes 700 updates versus 500 and retains its total-time
regression; its ratio is an unequal-work observation.

The new billion coupled run accepts 75.0% FP4 product work. Its largest complete-cost intervals are `independent_final_check` (135.728 s), `input_hash_validation` (112.880 s), `strict_certificate` (80.523 s), `original_model_control` (52.785 s). These retained intervals identify the remaining costs after GPU packing.

| Billion family | Solver peak host RSS before / after (GiB) | Sampled aggregate host RSS after (GiB) | Sampled owned GPU peak after (GiB) |
| --- | ---: | ---: | ---: |
| irregular | 58.575 / 58.569 | 58.660 | 39.836 |
| wide | 93.656 / 93.643 | 93.734 | 55.414 |
| tall | 50.387 / 50.364 | 50.456 | 35.934 |
| coupled_blocks | 47.193 / 47.188 | 47.279 | 31.039 |
| ill_scaled | 58.601 / 58.587 | 58.679 | 39.836 |
| degenerate | 58.578 / 58.572 | 58.663 | 39.836 |

Solver peak RSS comes from the dedicated child's high-water mark; aggregate host
and owned device peaks are sampled separately and are not added to that value.
The conservative pre-allocation bounds and physical host headroom remain enforced.

Complete cost includes the fresh solver process, response persistence and cold
independent final proof. Additional distinct intermediate proofs are reported as
separate offline audit costs. Input includes chunk reading, hashing, canonical
validation and original CSR-to-CSC construction. Every exclusive phase sums exactly
to complete cost; nested GPU packing metrics are not added a second time. GPU
advancement and packing metrics are host elapsed intervals, not kernel-active times.
Caches were not flushed. All family/lane limitations and actual FP4 work shares
remain visible; zero-eligible requests execute the established FP32 fallback.
Broad repeatable FP4 certified-solve superiority remains unestablished.

The allocation remains open at 320000 CPU / 35000 GPU seconds. Two explicit user
approvals transfer phase capacity within those totals. Retain every failed build,
CPU admission and sealing charge, and the excluded v6 source snapshot. The failed
seal's artifacts are admitted only by a separate read-only source/binary audit;
its original resource failure is unchanged. No attempted scientific cell repeats.
Container-only execution, idle/ownership checks, four CPU slots, 128 GiB host,
80 GiB owned GPU and 400 GiB storage caps remain unchanged. Commit locally only;
no public adoption, confirmation or fresh full portable replay is claimed.

Open settled allocation: 280670.141791928 CPU / 31576.271121081 GPU seconds within 320000 / 35000. No reservation is active. 101 harness tests and 363 documentation pages/local links pass. 303 current numerical bindings verify; 295 prior bindings remain exact, with five scoped integration changes and their original source copies retained. 46 failed reservations retain 72780.620150944 CPU / 6520.000000000 GPU seconds. Evidence: `gpu-pack-settled-checkpoint-v1.json`; compact checkpoint: `docs/benchmarks/lp-billion-gpu-packing-checkpoint.json`.

Final verification v1 passes 101 harness tests, then fails on two relative links
in the new state handoff. Its full 720 CPU-second charge and original output remain.
The corrected links and supplementary status-field comparison are checked by a
fresh verification v2; no scientific measurement repeats. See
[amendment 66](../specifications/SPEC-0046-amendment-66.md).

[Compact GPU packing results](lp-billion-gpu-packing-results.json) and
[all exclusive phase timings](lp-billion-gpu-packing-phases.csv) retain raw receipt,
source, proof and memory bindings. Large evidence stays under
`/storage/ai-optimizer-billion-v1/gpu-pack-64m-v1` and `gpu-pack-1b-v1`.


## GPU assessment and control with strict CPU acceptance

Opt-in image-v11 reuses the resident scaled matrices for exact-tree projected
residual products and GPU restart-movement norms. It preserves the original
1024-leaf arithmetic tree, signed-zero behavior and FP64 operations; long matrix
lines explicitly retain CPU control. The scalar square roots and log/exp weight
recurrence remain on the CPU. Reused device scratch and removed idle product
workers avoid another scaled matrix or persistent vector allocation.

Original-order primal feasibility now runs across GPU rows using original
coefficients and bounds. Original CSR indices are borrowed; original coefficients
and bounds occupy additional device memory, and bounded uploads use at most
8 MiB of new host scratch. The unchanged CPU dual-bound enclosure and gap
arithmetic remain authoritative. Every potentially accepting assessment must also
pass the original CPU feasibility check and identical objective bits before it
can grant a strict original-model 1e-9 certificate. GPU residuals never substitute
for that proof. Every final and intermediate claim receives independent CPU
checking after the measured solve.

Public defaults, original solve/preparation/packing CUDA binaries, control100,
certificate500 and recovery semantics remain unchanged. Native quality passes
61 isolated Rust tests, formatting, Clippy, release and CUDA
compilation. Device admission passes 33 bitwise residual
comparisons, 3 explicit long-line fallbacks,
36 exact movement-norm comparisons,
180 original-feasibility comparisons and
78 malformed-input rejections. Deep reductions exceed
1024 squared vector entries. The 60 exact continuations cover
native, FP32, FP4x1, FP4x2, recovery and cancellation, with
130 independent scalar checks.
All four complete sanitizers cover the diagnostic and twenty continuations each.

The fresh rotated six-family 64 M cohort retains 100 updates per cell and exact
full numerical transcripts. Descriptive median ratios (before / after) are
13.843x control, 1.107x assessment,
1.109x fresh process and 1.060x complete cost.
The preparation ratio is 1.153x. All regressions
and uncertified endpoints remain in the results.

| Family | Control before / after (s) | Assessment before / after (s) | Fresh process before / after (s) | Complete before / after (s) | Updates before / after | Certified before / after |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| irregular | 0.916 / 0.070 | 5.462 / 4.878 | 17.300 / 15.897 | 28.514 / 27.521 | 100 / 100 | False / False |
| wide | 1.825 / 0.175 | 10.412 / 9.535 | 27.262 / 24.308 | 44.606 / 41.086 | 100 / 100 | False / False |
| tall | 0.795 / 0.043 | 4.051 / 3.481 | 13.995 / 12.342 | 23.168 / 21.824 | 100 / 100 | False / False |
| coupled_blocks | 0.496 / 0.018 | 2.983 / 2.736 | 11.241 / 10.289 | 18.611 / 18.013 | 100 / 100 | False / False |
| ill_scaled | 1.025 / 0.076 | 5.457 / 4.937 | 17.649 / 15.596 | 29.317 / 26.823 | 100 / 100 | False / False |
| degenerate | 0.973 / 0.068 | 5.573 / 5.024 | 16.398 / 14.946 | 26.870 / 25.387 | 100 / 100 | False / False |

Six new full LP attempts each contain one billion original matrix nonzeros.
5 return endpoints; the wide cell is interrupted without a response and
is never retried. All returned endpoints pass independent audits. They retain
the 1000-update ceiling and requested 600-second solver allowance. Their v10
controls are historical runs, so the comparison is descriptive rather than a
randomized paired billion-scale experiment. Before / after median ratios are
24.997x control, 1.200x assessment,
1.472x fresh process and 1.321x complete cost.
Different deadline/update work is explicit. Uncertified bounded runs cannot
establish certified-solve speedups.

| Family | Control before / after (s) | Assessment before / after (s) | Fresh process before / after (s) | Complete before / after (s) | Updates before / after | Certified before / after |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| irregular | 176.346 / 7.055 | 168.234 / 136.195 | 720.953 / 470.595 | 955.000 / 697.770 | 1000 / 1000 | False / False |
| wide | unavailable | unavailable | unavailable | unavailable | 700 / None | False / False |
| tall | 199.044 / 8.008 | 92.514 / 85.905 | 585.335 / 356.309 | 787.538 / 562.932 | 1000 / 1000 | True / True |
| coupled_blocks | 86.531 / 2.284 | 80.523 / 67.101 | 351.121 / 239.641 | 486.850 / 371.999 | 1000 / 1000 | False / False |
| ill_scaled | 186.507 / 7.085 | 174.849 / 143.087 | 743.834 / 505.490 | 977.887 / 740.026 | 1000 / 1000 | False / False |
| degenerate | 172.213 / 7.743 | 172.502 / 148.255 | 618.694 / 464.934 | 838.991 / 682.020 | 1000 / 1000 | False / False |

The 5 equal-update historical pairs have a descriptive complete-cost median ratio of 1.321x; 5 have identical full transcripts. Equal update counts do not remove deadline classification or cross-run timing variability.

Jointly certified historical comparisons: tall: 787.538 to 562.932 s complete (1.399x), 1000 / 1000 updates.

The coupled billion case accepts 75.0% FP4 product work. Its largest remaining intervals are `independent_final_check` (132.358 s), `input_hash_validation` (100.017 s), `strict_certificate` (67.101 s), `preparation_engine` (21.953 s).

| Billion family | Preparation before / after (s) | Device setup before / after (s) | Solver peak host RSS before / after (GiB) | Sampled owned GPU peak after (GiB) |
| --- | ---: | ---: | ---: | ---: |
| irregular | 47.749 / 39.079 | 12.980 / 17.930 | 58.569 / 56.357 | 49.154 |
| tall | 40.709 / 32.409 | 11.323 / 13.127 | 50.364 / 48.875 | 44.553 |
| coupled_blocks | 38.368 / 34.485 | 8.550 / 11.992 | 47.188 / 47.196 | 38.959 |
| ill_scaled | 48.449 / 37.126 | 13.000 / 16.694 | 58.587 / 56.388 | 49.154 |
| degenerate | 46.492 / 34.866 | 13.900 / 16.938 | 58.572 / 56.363 | 49.154 |

Control combines `original_model_control` and `restart_weight_control`;
assessment is `strict_certificate`. Preparation includes initial control;
device setup is reported separately. Fresh process includes original input
reading/hashing/validation, CSR-to-CSC construction, solver execution and response
persistence. Complete cost additionally includes the cold independent final
original-model proof. Additional intermediate audits remain separately reported
offline costs. Every exclusive phase sums exactly to complete cost; nested timing
metrics are not counted twice. These are host elapsed intervals, not kernel-active
times. Caches were not flushed. The CSV retains all phases and observed peaks.

Device memory rises to hold the original feasibility arrays. Peak host RSS is the
solver child's high-water mark; sampled aggregate host/device peaks are distinct
measurements. Conservative capacity bounds, 4 GiB physical host headroom and all
ownership/idle checks remain enforced. The five zero-eligible families use their
established FP32 fallback; the coupled family retains actual FP4 work. Broad FP4
certified-solve superiority remains unestablished.

The user explicitly extends the open allocation to 370000 CPU / 44000 GPU seconds,
with CPU phase caps 10000/26000/58000/162000/113000/1000 and GPU caps 10000/34000.
The original recovery and both packing-transfer approvals remain required. Preserve
all failures and full charges, including CPU-v27's obsolete totals assertion and
quality-v1's formatting failure and quality-v2's diagnostic settings compile error.
No attempted scientific cell is retried. Four CPU
slots, 128 GiB host, 80 GiB owned GPU, 400 GiB storage, one-second supervision and
all 100 ms advisories stay unchanged. Remain container-only; no reset, host escape,
other-job signal or owner inference. Commit locally only, with no public adoption
or fresh full portable replay claim. The earlier general allocation is unchanged.

The wide attempt retains its full 5000 CPU / 1250 GPU-second charge and original
incomplete cleanup receipt. A later exact-identity check confirms all owned
processes gone, with no new signal; fresh CPU v29 / GPU v23 and a complete idle
window admit only the four untouched cells. The original interruption reason
was overwritten by the cleanup result and remains undetermined.

At the user's explicit request, obsolete large chunks are deleted after dependent
solves/audits finish. Source compaction verifies and archives 151015
older loose files, and new reservations share immutable source objects. Together
these actions release 145.070 GiB of allocated disk blocks. All small timing,
certificate, source-binding and failure records remain. Historical raw-data replay
requires regenerating deleted chunks; restoring source archives alone is insufficient.
The numerical certificates were checked before deletion and are not reclassified.

Final verification v1 passes 109 harness tests and 373 documentation pages, then
stops on the earlier 64 M report's source reference. Its full 960 CPU-second charge
is retained. Fresh verification v2 checks that exact historical reporting source
through its own reservation snapshot, without rewriting the report or repeating
scientific measurements. See [amendment 77](../specifications/SPEC-0046-amendment-77.md).

Open settled allocation: 314228.458381384 CPU / 35557.827345976 GPU seconds within 370000 / 44000. No reservation is active. 109 harness tests and 374 documentation pages/local links pass. 306 current numerical bindings verify; 296 prior bindings remain exact, with seven scoped integration changes and their original source copies retained. 51 failed reservations retain 84260.620150944 CPU / 7770.000000000 GPU seconds. Evidence: `gpu-control-settled-checkpoint-v1.json`; compact checkpoint: `docs/benchmarks/lp-billion-gpu-control-checkpoint.json`.

[Compact assessment/control results](lp-billion-gpu-control-results.json) and
[every exclusive timing phase](lp-billion-gpu-control-phases.csv) retain source,
resource, proof and memory bindings. Large evidence remains under
`/storage/ai-optimizer-billion-v1/gpu-control-64m-v1` and `gpu-control-1b-v1`.

## COPT startup diagnosis and fair comparison plan

The three original billion-nonzero COPT attempts entered `COPT_SolveLp`, printed
the original problem dimensions, and never logged GPU PDLP startup. Their sampled
owned GPU peak was only 0.537 GiB, consistent with a CUDA context. This points to
work before GPU optimization; the vendor's opaque internals prevent attributing
the entire delay to a specific operation. The original missing responses,
unknown tall interruption trigger, cleanup receipts and full charges remain.

An isolated adapter now durably journals every measured phase, including entry
and return from the vendor solve call. A bounded watcher invokes `COPT_Interrupt`
only on its own live problem at the common deadline, and joins before teardown.
Outer ownership and hard process supervision remain unchanged. Small GPU import,
endpoint and interruption admission passes on 24 fixtures/configurations. Every
available endpoint is independently checked on the unchanged original model at
1e-9. Installed COPT 8.0.6 and all project numerical sources remain unchanged.

Twelve prespecified, rotated 64 M diagnostics compare automatic scaling and
dualization with either or both disabled. Presolve remains zero, MatrixTol zero,
FeasTol/DualTol 1e-9 and PDLPTol 1e-12. Each receives 90 seconds after original
input loading, including adapter preparation. All twelve processes return
normally and receive their independent audit disposition: four coupled optima
certify; eight irregular/ill-scaled cases return an interrupted status without an
endpoint. A logged objective or residual is not a certificate.

| COPT setting | Irregular first iteration (s) | Ill-scaled first iteration (s) | Timely strict optima |
| --- | ---: | ---: | ---: |
| Automatic scaling and dualization | 41.72 | 41.55 | 1/3 |
| Scaling off | 27.84 | 27.81 | 1/3 |
| Dualization off | 41.48 | 41.83 | 1/3 |
| Both off | 27.34 | 28.22 | 1/3 |

The coupled 64 M diagnostic costs separate the native solver timer, full solver
process and external validation. All four coupled endpoints pass the unchanged
independent original-model 1e-9 checker.

| COPT setting | Native solver (s) | Solver process (s) | External final proof (s) | Process + final proof (s) |
| --- | ---: | ---: | ---: | ---: |
| Automatic scaling and dualization | 34.174 | 36.414 | 7.323 | 43.737 |
| Scaling off | 23.887 | 26.149 | 7.382 | 33.530 |
| Dualization off | 34.193 | 36.462 | 7.314 | 43.776 |
| Both off | 24.103 | 26.349 | 7.295 | 33.645 |

First-iteration times are vendor log values, rounded to 0.01 seconds, measured
inside its solve call. They exclude adapter preparation and are not kernel time.
Complete cost includes fresh input/process cost and cold independent final proof.
Scaling off reduces coupled complete cost by 23.3% (1.304x). Disabling dualization
alone gives no meaningful observed improvement. These are one-repetition startup
diagnostics, not a comparison against our solver.

The scaling tradeoff is substantial. On ill-scaled input, the vendor-reported
relative primal infeasibility / gap at interruption changes from
1.87e-6 / 3.57e-3 with automatic scaling to 4.45e-4 / 3.91e-1 with scaling off.
The irregular case also remains unresolved. These opaque vendor diagnostics
describe convergence only; they do not substitute for the original-model proof.
The prespecified coverage-then-complete-cost rule selects Scaling=0 with automatic
Dualize for the next experimental cohort, retaining these regressions. No public
default changes and no general recommendation to disable scaling follow.

The user explicitly approves 570000 CPU / 68000 GPU seconds under
[amendment 79](../specifications/SPEC-0046-amendment-79.md), applied through
[amendment 80](../specifications/SPEC-0046-amendment-80.md). All previous approvals,
failures, physical limits, container restrictions and strict checks remain.
Fresh CPU v30 / GPU v24 operational admission precedes selected-configuration
64/256/512 M capacity checks. Missing or setup-only capacity paths cannot admit a
billion slot. The full six-family, two-solver roster retains unsupported cases.

### Separate solver timing and independent validation

At the user's request, solver performance and independent validation are reported
separately. Solver process time is the primary performance view; process plus
external final proof is the additional independently verified end-to-end view.
The original selection rule and recorded results remain unchanged. The separate
process-time view does not reselect the COPT configuration or relax acceptance.

| Reported cost | Scope | Saved field |
| --- | --- | --- |
| Solver process | Original input reading, hashing, validation and conversion; preparation; optimization; all built-in stopping/certificate checks; output, transport and teardown | `fresh_process_ns` |
| External final proof | Separate frozen checker, including fresh original input loading, one final endpoint assessment and checker teardown | `final_check_ns` |
| Process + final proof | Solver process plus external final proof; a certified total only when the endpoint passes and the solve meets its deadline | `complete_ns` |
| External intermediate audit | Additional independent checks of saved intermediate endpoints, outside both headline timings | `offline_audit_ns` |

Our solver's built-in original-model feasibility and dual/gap checks are part of
solver process time. The independent final proof repeats endpoint validation in a
separate process; it is a benchmark audit, not another solver iteration. Both
solvers use the same external original-model 1e-9 acceptance check. Excluding its
runtime from the primary performance column never excludes the check itself:
only jointly timely, externally certified endpoints support either process-time
or verified-total speed ratios. Bounded unsuccessful runs retain their costs but
are not successful time-to-solution measurements. Native solver timers remain
supplementary because input/conversion boundaries differ between adapters.

For the same eligible pair, report `COPT fresh_process_ns / project
fresh_process_ns` separately from `COPT complete_ns / project complete_ns`.
Neither denominator includes the additional external intermediate audits.
The two components sum exactly in integer nanoseconds; displayed rounded values
can differ in the last decimal. No solver rerun is needed to show this split.

### Interim comparison snapshot: 2026-11-22 04:24 UTC

The selected-configuration capacity checks are complete. These COPT measurements
are not matched comparisons against our solver. All unsuccessful cases remain
visible; a dash for proof means no endpoint was available to check, rather than
a zero-cost successful proof.

| Original nonzeros | Family | COPT process (s) | External final proof (s) | Process + final proof (s) | Strict result |
| --- | --- | ---: | ---: | ---: | --- |
| 64 M | irregular | 93.105 | — | 93.105 | Interrupted; no endpoint |
| 64 M | coupled_blocks | 26.149 | 7.382 | 33.530 | Timely certificate |
| 64 M | ill_scaled | 93.140 | — | 93.140 | Interrupted; no endpoint |
| 64 M | wide | 82.773 | 16.655 | 99.428 | Timely certificate |
| 64 M | tall | 36.662 | 9.346 | 46.008 | Timely certificate |
| 64 M | degenerate | 54.788 | 10.504 | 65.292 | Timely certificate |
| 256 M | coupled_blocks | 116.820 | 30.521 | 147.341 | Timely certificate |
| 256 M | irregular | 311.080 | — | 311.080 | Interrupted; no endpoint |
| 512 M | coupled_blocks | 256.605 | 64.014 | 320.619 | Timely certificate |
| 512 M | irregular | 622.749 | — | 622.749 | Interrupted; no endpoint |

The frozen billion-scale cohort contains eleven admitted attempts and one
unsupported COPT-wide slot. At this snapshot only our irregular solve has
returned. Its independent final endpoint check rejects the endpoint; all ten
final/intermediate assessments have been audited and the audit has settled with
clean cleanup and no overrun. The matching COPT run has started, but no new
billion-scale COPT response or completed pair is available.

| Billion family / solver | Solver process (s) | External final proof (s) | Process + final proof (s) | Strict result |
| --- | ---: | ---: | ---: | --- |
| irregular / project | 1371.863 | 233.773 | 1605.636 | Deadline; final endpoint rejected |
| irregular / COPT | Running | Pending | Pending | Pending |

The project's additional external intermediate audits cost 1197.984 s, excluded
from both process time and process plus final proof. The 1605.636 s total is the
cost of this unsuccessful bounded run and its final validation, not a certified
time to solution.

The project irregular preparation is 35.347 s, and its native solver elapsed
time is 1271.867 s under the requested 1200-second window. It accepts 4400 updates
and uses the established FP32 fallback because no tiles qualify for FP4. The
native elapsed time exceeds the requested window; neither the returned endpoint
nor a partial audit is counted as a timely certificate. No billion-scale speed
ratio is available. The remaining family slots are pending, except COPT-wide,
whose empirical memory forecasts exceed the unchanged limits.

This is a timestamped reporting view of existing evidence, not a new experiment
or a replacement for the frozen full-cohort results. Small source records remain
under `/storage/ai-optimizer-billion-v1`: `copt-diagnostic-results-v1.json`,
`copt-fair-capacity-v1.json`, `copt-fair-1b-v1/freeze.json`, and
`copt-fair-1b-v1-irregular-project/{response,result}.json`. The final rejection is
also recorded in `copt-fair-1b-v1-irregular-project-full-audit/stdout.jsonl`;
settled proof timings and full endpoint coverage are in that directory's
`result.json`.


### Historical interim results at the user-requested pause

At this historical checkpoint, the user explicitly stopped monitoring and further
evaluation. The owned monitor was canceled, its continuation exited, and no
reservation remained active. GPU v25 and seven frozen LP attempts were untouched.
The later explicit resumption and final outcomes are recorded below.
The canceled observation retains empty cleanup, no overrun, and its full reserved
charge. This is an incomplete comparison, not a final benchmark release.

| Billion-nonzero problem / solver | Solver seconds | Fresh process seconds | Complete seconds | Outcome |
| --- | ---: | ---: | ---: | --- |
| irregular / project | 1271.867 | 1371.863 | 1605.636 | Deadline; final endpoint fails strict proof |
| irregular / COPT | 1206.119 | 1244.889 | 1244.889 | Interrupted; no solution endpoint |
| tall / project | 247.003 | 342.833 | unavailable | Strict final proof accepted; all three assessment claims independently covered |
| wide / project | unavailable | unavailable | unavailable | Missing response after recorded lost_coordinator_heartbeat |
| wide / COPT | not attempted | not attempted | not attempted | Capacity forecast exceeds the unchanged limits |

Complete cost includes input, all solver work, output/teardown, and a cold
independent final proof when an endpoint exists. The irregular project final
proof costs 233.773 seconds; its additional offline intermediate audit costs
1197.984 seconds. Tall's original audit loses its cold-proof timing during an
interruption. The missing intermediate proof subsequently completes, but that
reservation also fails supervision finalization. A separately supervised read-only
seal validates both raw proofs, exact original bindings, and all three assessment
claims without numerical recomputation. Both failures retain full charges. Tall's
observed solver/process times remain valid observations; its complete-cost timing
and certified-time ratio are excluded. Both returned project runs use FP32
fallback, with zero accepted FP4 work.

COPT reaches logged GPU PDLP iterations on the billion irregular model only after
roughly 1060 seconds of supervised activity. It completes 1560 iterations before
interruption; logged relative primal infeasibility is 1.83e-6 and relative gap is
3.98e-5, and HasLpSol is false. Earlier billion attempts never logged GPU PDLP
startup before ending. These observations establish substantial startup cost,
without identifying undocumented vendor internals. A normal interrupted response
without an endpoint is distinct from an earlier missing response file.

Selected COPT configuration on coupled-block models produces independently
accepted strict original-model 1e-9 solutions at the admitted smaller scales:

| Original nonzeros | Solver seconds | Complete seconds |
| --- | ---: | ---: |
| 64 million | 23.887 | 33.530 |
| 256 million | 109.228 | 147.341 |
| 512 million | 241.402 | 320.619 |

At 64 million, disabling scaling reduces coupled complete cost from 43.737 to
33.530 seconds (23.3%), but worsens ill-scaled convergence in the retained pilots.
No jointly certified billion-scale total-time comparison is established so far.
The remaining attempts are tall COPT and both lanes for coupled_blocks,
ill_scaled and degenerate. Strict certificates, original inputs, public defaults,
physical limits and all failure charges remain unchanged.

[Paused checkpoint and exact evidence bindings](lp-billion-copt-fair-paused.json)
retain the current results. Settled allocation is 376690.813581624 CPU /
42877.640387647 GPU seconds within 570000 / 68000, with no active reservation.
Latest CPU admission passes 75 supervisor and 122 billion-harness tests. Final
comparison verification has not run; no fresh complete replay or final result is
claimed.

### Billion-scale comparison

All eleven admitted attempts are now retained, alongside the unsupported COPT-wide
slot. COPT strictly certifies tall and coupled-block LPs. The project tall endpoint
also passes strict independent checking, but its complete-cost timing is missing.
No pair supports a certified complete-time ratio. The final resumption returns
two COPT deadlines without endpoints and one interrupted project attempt without
a response. Strict original-model 1e-9 acceptance is unchanged throughout.

Historical cells retain their 1200-second native / 1800-second outer allowances. The first three resumed attempts use 2100/2700 seconds; the coupled project attempt rejects this unsupported native setting before solving. The final four untouched ill-scaled/degenerate cells use the sealed executable’s maximum supported 1800-second native allowance, with the enlarged 2700-second outer reserve and separate audits. Both lanes in these two pairs have equal limits. The tall pair spans different allowances and receives no time ratio. All six original billion-nonzero families and both lane slots remain visible. The project uses unchanged image-v11 with a 10000-update safety cap, control100/certificate500 and strict original-model 1e-9 acceptance. COPT 8.0.6 uses GPU PDLP, Presolve=0, Scaling=0, automatic Dualize, MatrixTol=0, FeasTol/DualTol=1e-9 and PDLPTol=1e-12.

| Family | Project complete (s) | COPT complete (s) | Eligible timely strict project / COPT | COPT / project certified-time ratio |
| --- | ---: | ---: | --- | ---: |
| irregular | 1605.636 | 1244.889 | False / False | — |
| wide | — | — | False / False | — |
| tall | — | 1408.580 | False / True | — |
| coupled_blocks | — | 857.414 | False / True | — |
| ill_scaled | 2236.278 | 1886.239 | False / False | — |
| degenerate | — | 1863.704 | False / False | — |

Complete cost includes original input validation/conversion, all preparation, execution, output/teardown and the cold independent final proof. The CSV retains every exclusive phase. Additional independent intermediate audits are recorded separately. Native solver timers have different input/conversion boundaries, so their raw elapsed values are not used as end-to-end speedups. Only jointly timely, strictly certified pairs with equal requested allowances receive a solve-time ratio; other displayed costs are the costs of the recorded bounded outcomes.

| Family / lane | Outcome | Strict endpoint accepted | Solver elapsed (s) | Fresh process (s) | Offline intermediate audit (s) | Actual FP4 work |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| irregular / fp4x2 | deadline | False | 1271.867 | 1371.863 | 1197.984 | 0.0% |
| irregular / copt-gpu-pdlp | interrupted | no endpoint | 1206.119 | 1244.889 | 0.000 | — |
| wide / copt-gpu-pdlp | unsupported_capacity | — | — | — | — | — |
| wide / fp4x2 | missing response; recorded lost_coordinator_heartbeat | — | — | — | — | — |
| tall / fp4x2 | certified | True | 247.003 | 342.833 | — | 0.0% |
| tall / copt-gpu-pdlp | vendor optimal | True | 1042.017 | 1155.914 | 0.000 | — |
| coupled_blocks / copt-gpu-pdlp | vendor optimal | True | 649.036 | 679.335 | 0.000 | — |
| coupled_blocks / fp4x2 | missing response; recorded command_failed: invalid solver settings | — | — | — | — | — |
| ill_scaled / fp4x2 | deadline | False | 1875.828 | 1977.391 | 1981.486 | 0.0% |
| ill_scaled / copt-gpu-pdlp | interrupted | no endpoint | 1807.569 | 1886.239 | 0.000 | — |
| degenerate / copt-gpu-pdlp | interrupted | no endpoint | 1805.864 | 1863.704 | 0.000 | — |
| degenerate / fp4x2 | missing response; recorded cleanup_incomplete | — | — | — | — | — |

The tall / fp4x2 endpoint passes strict independent verification, but its complete-cost timing is excluded: interrupted original audit did not retain cold final-proof timing. The retained completed proof and supplemental missing-proof check cover every assessment. Its observed solver and fresh-process times remain above; no replacement cold-final timing or certified-time ratio is reported. Supplemental verification took 236.160 seconds; the original failure retains its full charge.

The supplemental numerical check also completed before a refused supervision receipt. A separately supervised read-only seal validates both retained proof outputs and their exact bindings. Both failed audit charges remain; the seal performs no LP update or numerical proof recomputation.

Every unavailable response and capacity refusal remains in the compact evidence. A recorded supervision stop identifies the retained receipt; it does not establish the underlying numerical or system cause. Missing responses have no eligible solve-time measurement and are never retried. The project requests FP4; ineligible tiles use the established FP32 fallback, and actual accepted FP4 work is reported above. The vendor soft MemLimit stays at its admitted 48000 MB setting, alongside the common physical 128 GiB host / 80 GiB owned GPU limits. Empirical capacity forecasts are not hard vendor enclosures. Construction witnesses and warm starts are never supplied. At most one rotated pair per family and unflushed caches limit timing inference; this does not establish broad FP4 or general COPT superiority.

[Compact diagnosis, capacity and full results](lp-billion-copt-fair-results.json) and [exclusive complete-cost phases](lp-billion-copt-fair-phases.csv) retain all outcomes. Completed large input/endpoint chunks are deleted after dependent audits; raw replay requires regeneration. All small results, phase journals, exact sources and failure charges remain.

The untouched ill-scaled and degenerate COPT cells use a smaller 120 GiB per-job host RSS stop, with the unchanged additional 4 GiB physical headroom and global 128 GiB cap. This exceeds their already padded empirical forecasts of about 110.1 GiB by almost 10 GiB. The native MemLimit and all numerical settings remain unchanged; the forecast is not a hard vendor enclosure. Audited ill-scaled project endpoint objects were deleted before the COPT lane while preserving all original model objects and small proof evidence.

Degenerate input generation was interrupted before either LP started. Its original cleanup-incomplete receipt and full 3600 CPU-second charge remain. A separate check finds all four recorded owned identities absent; additional CPU/GPU admission and a fresh sustained idle/RAM window precede recovery under a new input identity. Existing chunks and the regenerated model are checked against the original hashes. Neither scientific cell is repeated, and no resource or certificate guard is relaxed.

The final degenerate project attempt stops after 1367.952 supervised active seconds with no response and a cleanup-incomplete receipt. Its preceding stop trigger is unavailable. All four recorded owned identities are independently absent afterward. The full 10800 CPU / 2700 GPU-second charge remains; no complete solve timing or certificate is assigned, and the attempt is never repeated. The original audit records a missing response with zero endpoint claims. All admitted LP identities are now attempted; missing or uncertified outcomes remain part of the comparison. Remaining obsolete large objects, including partial failed-attempt data, are removed after the full audit dispositions, with a retained size inventory.

The final cleanup's first check incorrectly required the original tall audit to
pass, stopping before deletion and retaining its full 480 CPU-second charge.
The corrected cleanup validates the already admitted tall proof seal and all
other audit dispositions. This resumption releases 47.009 GiB of obsolete large
data while retaining small results, proofs, source bindings and failures.

The final timing table uses complete process boundaries: ill-scaled COPT costs
1886.239276306 seconds and degenerate COPT 1863.704107960 seconds. Earlier progress
notes and amendment 90 quote adapter-profile totals (1885.924168562 and
1863.368695828 seconds); those exclude process startup and response transport and
must not be treated as complete costs.

Final verification passes 136 harness tests and 387 documentation pages, resolves
637 retained evidence references and confirms all 306 numerical bindings. All
1995 recorded owned identities are gone. The [settled checkpoint](lp-billion-copt-fair-checkpoint.json)
records 459659.784173452 CPU / 55943.714704332 GPU seconds within the approved
570000 / 68000 limits, with no active reservation or monitor. All 63 failed
reservations retain their full charges. No fresh portable raw-data replay is claimed.
