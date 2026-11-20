# Billion-nonzero LP development on the Pro6000

Execution continuation under [SPEC-0046](../specifications/SPEC-0046-billion-lp.md),
2026-11-19–20. GPU preparation is implemented and CPU-tested, but device admission
and performance measurements are waiting for the Pro6000 to become idle. All six
billion-nonzero originals are ready; no billion-scale solve has run. Public
defaults and historical results remain unchanged.

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
