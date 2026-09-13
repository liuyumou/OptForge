# SPEC-0010: Heterogeneous Computation and Batched Device Evaluation

Status: accepted
Scope: optimizer-cuda-sys device boundary, optimizer-cuda selection and residency, the batched schedule evaluator, and the optimizer-cli device surface
Owner: heterogeneous computation
Introduced: C6
Last reviewed commit: 391edeb
Supersedes: none; amends SPEC-0006 requirement 1 and SPEC-0009 requirement 9
Implementation: [driver boundary](../../crates/optimizer-cuda-sys/src/lib.rs), [status mapping](../../crates/optimizer-cuda-sys/src/status.rs), [residency and admissibility](../../crates/optimizer-cuda/src/schedule.rs), [lease ownership](../../crates/optimizer-cuda/src/lib.rs), [kernels](../../cuda/schedule_eval/schedule_eval.cu), [provisioning](../../tools/setup_cuda.sh), [build probe](../../crates/optimizer-cuda/build.rs)
Tests: [device contracts](../../crates/optimizer-cuda/tests/device.rs), [admissibility and status unit tests](../../crates/optimizer-cuda/src/schedule.rs)
Implemented: requirements 2 to 4, 7 to 21 and 23 to 39 in part; see [known failures](../../state/known-failures.md) for the requirements this slice does not yet reach

## Purpose

Make every property of running work on a device explicit before a kernel exists, and
then establish one measured workload against a tuned CPU baseline. The properties
this contract fixes are device selection, lease ownership, residency, batching,
transfer-inclusive timing, arithmetic width, equivalence, fallback, cancellation,
reset recovery and determinism.

The workload is batched permutation evaluation for the C5 flow shop. It is chosen
because its arithmetic is integer, which makes CPU/GPU equivalence an exact identity
rather than a tolerance, and because it reaches the engine through a seam that
already carries no mathematical authority.

Excluded: GPU linear programming and any capability or device concept on the
backend contract (SPEC-0011); multi-device and multi-GPU algorithms (deferred in
[backlog](../../state/backlog.yaml), and SPEC-0006 requirement 6 permits one holder
per host); dynamically loaded native extensions (ADR-0003, ADR-0008); tensor-core
and thread-block-cluster programming (unavailable or silently degenerate at compute
capability 12.0); device-side branch-and-bound orchestration (SPEC-0003 requirement
23 fixes the node loop as sequential); learned or adaptive device selection (C7);
non-NVIDIA devices and non-Linux hosts (SPEC-0006 compatibility).

## Terminology

A *device* is one physical GPU identified by its driver-reported UUID. A *context*
is a CUDA driver context bound to exactly one device. A *residency* is the period
during which instance-invariant data stays in device memory and is reused across
calls; it begins with an upload and ends when its owner is dropped. A *batch* is a
set of independent evaluations submitted in one call. The *host* is the Rust process
that owns the context. A *code object* is a cubin compiled for a specific compute
capability, or PTX the driver compiles at load time. *Equivalence* is agreement
between a device result and the CPU result that the same specification defines as
authoritative. A *fallback* is the execution of the CPU path after the device path
declined or failed, producing the result the device path would have produced. An
*availability failure* is a device failure attributable to the environment: an absent
driver, a missing code object, an unsupported compute capability, an allocation
failure, a launch failure, or a lease that could not be taken. A *disagreement* is a
device result that differs from the CPU result; it is a numerical failure and is not
an availability failure.

## Requirements

### Inventory and device selection

1. Discovery MUST report the driver version in addition to the UUID, name and memory
   MiB that SPEC-0006 requirement 1 already fixes. This amends that requirement as
   requirement 1a rather than replacing it, because
   [SPEC-0007](SPEC-0007-artifacts.md) requirement 9 requires a GPU record to
   identify its driver and nothing has ever produced that field.
2. A device workload MUST name exactly one physical UUID. An enumeration index MUST
   NOT be accepted in its place, because `CUDA_VISIBLE_DEVICES` renumbers devices and
   an index therefore names different hardware in different processes.
3. The engine MUST read the selected device's UUID back from the driver and MUST
   refuse to proceed when it differs from the requested one. A record MUST NOT be
   able to claim a device the run did not use.
4. The engine MUST refuse a device for which it has neither a matching cubin nor
   loadable PTX, and MUST report the compute capability it found and the code objects
   it holds. Silently running nothing is forbidden.
5. There MUST be no default device. A configuration that does not name one runs on
   the CPU, and no measurement, heuristic or availability check MUST promote it to a
   device.
6. A CPU record MUST NOT claim device execution and a device record MUST identify the
   selected UUID, name and driver, matching SPEC-0007 requirement 9.

### Lease and ownership

7. A device workload MUST hold the SPEC-0006 host lease for the entire lifetime of
   its context, not merely for the duration of a launch.
8. The engine MUST accept an inherited lease and MUST NOT acquire the host lock a
   second time when one is inherited. `tools/gpu_job.sh` already holds the lock for
   its child, so acquiring again would self-deadlock until the wrapper's 300-second
   timeout; that deadlock is the reason this requirement exists rather than a
   hypothetical.
9. The engine MUST refuse to create a context when it neither inherited nor acquired
   the lease. No configuration, flag or environment variable MUST permit unleased
   device execution, matching SPEC-0006's rule that no fallback to unlocked GPU
   execution is allowed.
10. Lease release MUST follow context destruction. Releasing first would let a second
    holder create a context while the first still owns device memory.
11. Recovery MUST NOT unlink or replace the lock file, restating SPEC-0006
    requirement 10 for the kernel path it was written to anticipate.

### Arithmetic width and exactness

12. Integer device evaluation MUST use exact 32-bit unsigned accumulators and MUST
    NOT wrap, saturate or clamp, matching SPEC-0008 requirement 9's treatment of the
    CPU recurrence.
13. The host MUST refuse device dispatch when the instance's own makespan bound — the
    sum of all its processing times, which
    [the recurrence](../../crates/optimizer-schedule/src/evaluate.rs) already bounds
    every makespan by — exceeds `u32::MAX`, and MUST fall back to the CPU path. The
    check MUST be made from the instance, never from a result.
14. The equivalence tolerance for integer device evaluation MUST be exactly zero. A
    device makespan that differs from
    `optimizer_schedule::evaluate::makespan` by any amount is a disagreement.
15. This specification MUST NOT admit floating-point device arithmetic. A device path
    whose result is inexact belongs to SPEC-0011 and carries that specification's
    status and authority rules.

### Residency and batching

16. Instance-invariant data MUST be uploaded once per residency and reused across
    calls. Re-uploading it per call is a defect, not a performance characteristic.
17. Batch size MUST be an explicit parameter of the device interface. It MUST NOT be
    inferred from device memory, occupancy or any measurement, because an inferred
    batch size would make the amount of work per call depend on the machine and
    SPEC-0004 already forbids machine-dependent budgets for the same reason.
18. A device call MUST NOT transfer data a previous call in the same residency
    already placed.
19. Device memory MUST be released when its residency is dropped, including when the
    drop is caused by an unwind.

### Timing and measurement

20. A recorded device timing MUST be end-to-end, including context creation, module
    load, every transfer and every synchronization, per
    [the benchmark protocol](../benchmarks/protocol.md).
21. Kernel-only timings MAY supplement a full timing and MUST NOT replace one. Any
    reported comparison MUST name the CPU baseline it was taken against and MUST
    report the repeat-measurement noise floor beside it.
22. CPU MUST remain the default below the measured crossover. The crossover MUST be a
    recorded measurement on named hardware, never a constant chosen in advance.

### Fallback

23. Every device path MUST have a CPU path that produces an identical result, and
    that CPU path MUST be the one this project already treats as authoritative rather
    than a second implementation written to match the kernel.
24. An availability failure MUST fall back to the CPU path and MUST be recorded as a
    typed diagnostic.
25. A disagreement MUST NOT fall back silently. It is a numerical failure and MUST be
    surfaced, because a fallback that hides a wrong kernel would convert a correctness
    defect into a performance characteristic.
26. A fallback MUST NOT change a search's outcome, proven optimum, dual bound,
    forfeiture state or either prune counter.

### Cancellation and recovery

27. Device work MUST be launched in bounded chunks with a host-side cancellation
    check between them, so that cancellation latency is bounded by one chunk rather
    than by the whole batch.
28. Cancellation MUST destroy the context and release the lease, in that order.
29. A context left in a sticky error state MUST be destroyed and rebuilt, or the
    workload MUST fall back to CPU for the remainder of that run. Continuing to launch
    into a sticky context is forbidden.
30. A device reset, removal or fault MUST NOT be reported as a solver outcome. It is
    an availability failure under requirement 24.

### Determinism

31. A device result MUST be bitwise reproducible for a fixed input on a fixed device
    and a fixed code object.
32. Cross-device bitwise reproducibility MUST NOT be claimed. The
    [implementation plan](../../implementation-plan.md) already distinguishes
    reproducible experimental conclusions from identical execution traces, and this
    requirement is where that distinction becomes testable.

### Authority

33. A device result MUST NOT become a bound, a termination status or a proof claim.
34. Every device-produced candidate MUST be validated by `Model::evaluate` against
    the original model before publication, matching SPEC-0002's rule for backend
    output. A wrong kernel MUST therefore produce a recorded refusal, never a wrong
    answer.
35. A GPU hardware requirement in a registry entry MUST resolve only when a device is
    selected and the lease is held, and MUST otherwise be refused with a reason
    distinguishable from every other refusal. This narrows SPEC-0009 requirement 9's
    unconditional refusal; SPEC-0009 requirement 14a continues to govern, because the
    refusal is still decided before the provider is consulted.
36. This specification MUST NOT record a performance, runtime or solution-quality
    claim, and a measured crossover MUST NOT be described as evidence that device
    execution improves a search.

### Build and platform

37. A build without CUDA code objects MUST expose the same API and MUST report an
    explicit unsupported device backend, matching ADR-0003's rule for a build without
    the pinned HiGHS library.
38. `nvcc` MUST NOT be a dependency of an ordinary `cargo build`. Code objects are
    provisioned out of tracked source, as the pinned native library already is.
39. Unsafe code MUST be confined to the single new boundary ADR-0009 authorizes.
    Every other runtime crate MUST retain `unsafe_code = "forbid"`.

### Documents

40. The search configuration MUST carry the selected device, so that a device run is
    re-executable from its record alone under SPEC-0005. A device recorded only in
    provenance would describe a run that verification could not repeat.
41. The new search configuration, search record and run record versions MUST each
    have a JSON Schema, and that schema and the Rust parser MUST accept the same
    documents. Neither MUST be laxer than the other, matching SPEC-0009 requirement
    26 and SPEC-0005 requirement 20. A version mismatch MUST be refused rather than
    migrated.

## Interfaces

```bash
optimizer gpu discover [--dry-run]
optimizer gpu probe --device GPU-<uuid> [--lease inherited|acquire]
optimizer schedule improve --instance <path> --device GPU-<uuid> --batch <n>
bash tools/setup_cuda.sh
bash tools/gpu_job.sh GPU-<uuid> <command>
```

`optimizer gpu probe` creates a context on the named device and reports the
driver-read UUID, compute capability, streaming multiprocessor count, free and total
memory, the loaded code object kind, and whether the lease was inherited or acquired.
It exits 0 on success, 2 on a refused or mismatched device, and 130 on cancellation,
matching the existing CLI exit contract.

`--lease inherited` asserts that an ancestor holds the host lock; `tools/gpu_job.sh`
sets the corresponding marker for its child. `--lease acquire` is the default and
takes the lock itself. Neither MUST be inferred.

`optimizer-cuda-sys` exposes `Context`, `Module`, `Stream` and `DeviceBuffer<T>` as
owned values whose `Drop` releases the corresponding driver resource. Every raw
driver handle stays private to that crate, matching the rule that keeps native HiGHS
handles inside `optimizer-highs`. Driver status is mapped exhaustively with no
catch-all arm, so a CUDA upgrade fails to compile rather than silently
mis-classifying an outcome, matching SPEC-0002's treatment of the 18 native model
statuses.

`optimizer-cuda` exposes the residency and the batched evaluator:

```rust
ScheduleResidency::open(context, instance) -> Result<Self, DeviceError>
ScheduleResidency::makespans(&self, sequences: &[u16], batch: usize, cancel: &CancellationToken)
    -> Result<Vec<u32>, DeviceError>
```

`sequences` is `batch * jobs` entries in permutation order. The instance's processing
times are uploaded by `open` and are not re-sent by `makespans`, which is requirement
16 expressed in the signature rather than only in prose.

Configuration reaches these through a new top-level `device` field on the search
configuration, taking `"cpu"` or a UUID under the pattern
`^(cpu|GPU-[A-Za-z0-9-]+)$` that
[the benchmark run configuration](../../schemas/run-config-v1.schema.json) already
fixes for the same purpose. The field is one value for the whole search rather than
one per component: SPEC-0006 requirement 6 permits at most one lease holder across
device selections, so a single search cannot use two devices, and a per-component
device would be a configuration that can express something the lease forbids.

## State and Invariants

A residency progresses `absent -> leased -> context -> resident -> released`. Every
transition is explicit and each failure returns to `absent` after releasing whatever
was taken, in reverse order of acquisition. There is no state in which a context
exists without a lease, which is requirement 9.

Integer evaluation is exact: accumulators are `u32`, the operations are `max` and
addition, and the reachable range is bounded by the instance's own sum of processing
times, which requirement 13 checks before dispatch. No tolerance applies, no rounding
mode is selected, and no value is clamped. This is why requirement 14 can set the
equivalence tolerance to zero rather than to a small constant.

Determinism follows from the arithmetic rather than from scheduling: integer `max`
and addition are associative and commutative, so no reduction order changes a result.
That property is specific to this workload and does not extend to SPEC-0011.

Compute capability 12.0 bounds the implementation in four ways, each recorded because
a reader checking these numbers on other Blackwell hardware would find different
ones. Shared memory is at most 99 KB per thread block, which is what makes `u32`
tables fit where `u64` tables would not. At most 48 warps are resident per
multiprocessor, against a 64K register file, so full occupancy requires no more than
42 registers per thread. Integer and floating-point instructions issue on one shared
pipeline, so integer code runs at the full lane rate. Thread block clusters are
accepted by the assembler while `cluster.sync` degenerates to a no-op, so no kernel
may depend on cluster cooperation; this is a silent-failure mode, which is why it is
stated as an invariant rather than left to a comment.

## Errors and Recovery

An availability failure returns a typed device error, falls back, and records a
diagnostic naming which failure occurred. A disagreement returns a numerical failure
and does not fall back. An overflow-bound refusal under requirement 13 is an
unsupported input, not a failure: it is expected, it falls back, and it is recorded.

Cancellation returns promptly at the next chunk boundary, destroys the context and
releases the lease. A sticky context is destroyed and rebuilt once; a second sticky
failure in the same run disables the device path for that run rather than looping.

Lock-open and lock-I/O errors propagate, and no path admits unleased execution.
Recovery never unlinks the lock file.

## Compatibility and Versioning

Three schemas gain a version. The search configuration gains a top-level `device`
field, so `search-config-v3` replaces version 2; the search record embeds its
configuration as `options`, so `search-record-v3` replaces version 2; and the run
record embeds the search record, so `run-record-v2` replaces version 1. Version
mismatches are rejected rather than migrated, matching SPEC-0004's treatment of
version-1 search documents. Each new schema and its Rust parser MUST accept exactly
the same documents, neither laxer than the other, matching SPEC-0009 requirement 26
and SPEC-0005 requirement 20.

The solve configuration does **not** gain a device and stays at version 1. A
relaxation runs on the search's device, because SPEC-0006 requirement 6 permits one
lease holder across device selections and a per-solve device could therefore express
a configuration the lease forbids. Confining device selection to one field also keeps
SPEC-0005's field-by-field verification meaningful: `device` is compared as part of
`options`, and a record cannot verify against a run that used different hardware.

The run record's `hardware` block already carries `gpu_uuid`, `gpu_name` and
`driver` as nullable fields, specified by SPEC-0007 requirement 9 before any producer
for them existed; this contract supplies the producer and adds no field there.

SPEC-0006 requirement 1 gains requirement 1a for the driver version. SPEC-0009
requirement 9's unconditional refusal of a GPU hardware requirement is narrowed by
requirement 35 here; SPEC-0009 requirement 14a is unchanged, because the refusal is
still decided before construction.

Linux x86-64 only, as SPEC-0006 already fixes. Code objects are built for compute
capability 12.0 with PTX alongside, so a later capability loads by driver compilation
rather than failing; an earlier capability is refused under requirement 4.

## Security and Resource Limits

The host lock's trust boundary is unchanged from SPEC-0006: advisory locking is
cooperative and is not protection against an uncooperative process. Device memory is
bounded by an explicit allocation whose failure is an availability failure, never an
abort. Batch size is caller-supplied and bounded, so a single call cannot request
unbounded device memory. A kernel launch is bounded in work per chunk so that
cancellation latency is bounded; unbounded kernels are forbidden by requirement 27.

Device faults are outside the C3 extension host's containment claim, which covers
panics only. A device-backed extension therefore cannot be contained the way a
CPU extension is, and that limit is recorded rather than implied.

## Examples

See [GPU operations](../operations/gpu.md) for discovery, probing, the wrapper and
the provisioning script.

## Acceptance Tests

Requirements 1-6: discovery reports four fields and refuses a malformed or duplicate
row as before; a probe round-trips the driver-read UUID; a probe naming a UUID the
host does not have, and a probe whose driver-read UUID differs from the requested
one, are each refused separately, so requirement 3 is shown to be able to fail rather
than only to pass; a configuration naming no device produces a record whose three GPU
fields are null.

Requirements 7-11: a context cannot be created without a lease; an inherited lease is
used rather than re-acquired, asserted by running the CLI under `tools/gpu_job.sh` and
showing it completes rather than timing out, which is the deadlock requirement 8
exists to prevent; cancellation and process death each release the same lock inode,
extending the existing SPEC-0006 process tests to a real context.

Requirements 12-15: the device makespan equals
`optimizer_schedule::evaluate::makespan` exactly over the tiny exhaustive grid and
over every instance in both frozen manifests, with the assertion written as equality
rather than as a tolerance; an instance whose sum of processing times exceeds
`u32::MAX` is refused to the device and falls back, asserted positively by checking
that the fallback fired and that the result is still correct, so the test cannot pass
because nothing was dispatched.

Requirements 16-19: a residency uploads once, asserted against a transfer counter
rather than against elapsed time; a second call in the same residency transfers only
its sequences; dropping a residency during an unwind releases its device memory.

Requirements 20-22: the crossover report is end-to-end and transfer-inclusive, taken
as the minimum of three runs after a warmup, and carries a noise-floor row from an
identical binary. The report MUST show the device losing on the 20x5 instances; a
report that does not is evidence the measurement is wrong rather than evidence the
device is fast.

Requirements 23-26: with every device-produced proposal refused, the outcome, proven
optimum, dual bound, forfeiture state and both prune counters are identical to the
producer-free run, which itself agrees with the CPU path, and each such test asserts
the producer was actually invoked first so that none can pass vacuously. This is the
C3 and C5 invariance form applied to a device. A forced availability failure produces
the same conclusion as the device path, differing only in the recorded diagnostic.

Requirements 27-32: cancellation mid-batch returns within one chunk and releases the
lease; a deliberately faulted launch leaves the context sticky, and the next call is
shown to rebuild rather than to launch again; repeating a device search on one device
produces a record that `optimizer verify` accepts on every compared field, differing
only in measured elapsed time.

Requirements 33-36: a kernel mutated to return a better makespan than the recurrence
allows has its candidate refused by `Model::evaluate` and recorded, and the search's
proven optimum does not move; a registry entry requiring a GPU resolves with a device
selected and is refused without one, with the two refusals distinguishable, and the
existing pre-construction assertion against the provider's construction counter is
retained.

Requirements 37-39: a build with no code objects present compiles, exposes the same
API, and reports an unsupported device backend; `cargo build --workspace
--all-features` succeeds on a host with no `nvcc` and no device;
`cargo clippy --workspace --all-targets -- -D warnings` continues to enforce
`unsafe_code = "forbid"` on every crate except the one ADR-0009 names.

Requirements 40-41: a device search writes a record that verifies by re-execution,
and a record whose `device` alone is mutated fails verification naming that field, so
the device is shown to be compared rather than nominally present. A version-2 search
configuration and a version-1 run record are each refused rather than migrated, in
both the Rust parser and the schema, and the two are asserted to refuse the same
documents.

Device-dependent tests report an explicit skip when no device or no code object is
present, so a missing device is never counted as coverage, matching how
native-dependent tests already report a skip when the pinned library is absent. The
complete `bash tools/check.sh` gate with native acceptance covered, plus the device
suite on the labeled runner, is required before this slice is complete.

## Open Questions

Whether device execution improves any search is a hypothesis and is deliberately
unmeasured by this contract; the crossover is a property of two implementations on
one host, not a property of the engine. Whether the tuned CPU baseline closes the gap
entirely is open, and closing it would be a valid recorded negative result under
Stage 4 rather than a failure of this specification.

Per-device memory budgeting, multi-device residency and device-side node
orchestration each need their own contract. Containment of a device fault is not
solved here and is not claimed: the C3 host contains panics, and a device fault is
not a panic.

Whether the shared host lock should shard per device is deployment policy. SPEC-0006
requirement 6 permits one holder across device selections, so the three host devices
cannot be used concurrently by this project even though the hardware would allow it.
