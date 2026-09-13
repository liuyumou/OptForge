# SPEC-0006: GPU Discovery and Exclusive Ownership

Status: accepted
Scope: GPU ownership
Owner: optimizer-cuda
Introduced: M0
Last reviewed commit: f7505c7 (requirement 1a and the probe interface; the rest is unchanged from the initial commit containing this file)
Supersedes: none
Amended by: [SPEC-0010](SPEC-0010-heterogeneous-computation.md) requirement 1, which adds requirement 1a below
Implementation: [Rust library](../../crates/optimizer-cuda/src/lib.rs), [CLI](../../crates/optimizer-cli/src/main.rs), [wrapper](../../tools/gpu_job.sh)
Tests: [process contracts](../../crates/optimizer-cli/tests/cli.rs), library unit tests

## Purpose

Discover physical devices and establish cooperative exclusive ownership before
kernels exist. No CUDA context, kernel, scheduler, or device reset is implemented
here; SPEC-0010 owns all of those and reuses this contract's lease unchanged.

Earlier revisions of this document deferred that work to a milestone named M5. The
roadmap later renamed it C6, and the references below are updated rather than left
to be decoded, because a contract that defers to a milestone name nothing else uses
is a contract a reader cannot follow.

## Terminology

A lease is an OS advisory exclusive file lock. A host lock is the shared inode used
by all project checkouts and all GPU models. A simulation holds that lease only.

## Requirements

1. Discovery MUST query UUID, name, and memory MiB without launching kernels.
1a. Discovery MUST also report the driver version. SPEC-0007 requirement 9 requires
   a GPU record to identify its driver, and nothing produced that field until
   SPEC-0010 needed it; this requirement is added there rather than here, and is
   restated here so the inventory contract is readable in one place.
2. Discovery MUST sort devices by UUID and reject malformed or duplicate rows.
3. Missing tooling, no devices, nonzero command exit, or a five-second deadline MUST produce unavailable with a reason.
4. Discovery MUST report all physical devices returned by management tooling, including the three known host devices when present.
5. All project GPU jobs MUST acquire the same host lock before using any GPU.
6. The lock MUST permit at most one cooperating holder across device selections.
7. A lease MUST release on handle drop, normal process exit, cancellation, or process death.
8. A waiter MUST stop on cancellation or expiry of its timeout.
9. A cancelled waiter MUST NOT release another process's lease.
10. Recovery MUST NOT unlink or replace the lock file.
11. SIGINT or SIGTERM in the simulated CLI MUST release ownership and exit 130.
12. The GPU runner MUST serialize jobs through both CI concurrency and the host lock.
13. A GPU job MUST select one physical UUID and MUST remain a foreground job while its lease is held.

## Interfaces

optimizer gpu discover [--dry-run] writes one JSON discovery object and exits 0
for both available and unavailable states. A discovery failure is explicit data.

optimizer gpu lease --simulate-ms N [--timeout-ms N] accepts integers 0..60000
milliseconds. Timeout defaults to 5000 ms. Duplicate, missing, unknown, negative,
or out-of-range arguments exit 2. Waiting, acquisition, and release emit JSON lines with
event and simulated=true. An acquisition timeout exits 2.

optimizer gpu probe --device GPU-<uuid> [--lease acquire|inherited] [--timeout-ms N]
creates a context on one named device and writes one JSON report, or exits 2 with a
diagnostic and no report. It is the first command that takes the lease for real work
rather than for a simulation, and SPEC-0010 requirements 3, 4 and 9 govern what it
reports. Because the lock permits one holder across device selections, it names
exactly one UUID; there is no probe-everything form.

GpuLease::acquire(path, timeout, cancelled) returns ownership or io::Error.
Ownership::acquire_or_inherit adds the case the wrapper creates: it accepts a lease
an ancestor holds rather than blocking on it. A child that acquired under
tools/gpu_job.sh would wait on its own parent until the wrapper's 300-second
timeout, which is a real deadlock rather than an anticipated one.
AI_OPTIMIZER_GPU_LOCK overrides /tmp/ai-optimizer-gpu.lock for a host deployment.
Tests use private temporary lock paths; real jobs on one host MUST agree on one path.
The shell wrapper waits up to 300 seconds and exports CUDA_VISIBLE_DEVICES.

## State and invariants

Unlocked -> waiting -> owned -> unlocked. Cancellation can terminate waiting or
owned. The file persists; ownership is attached to the open file description.
No objective arithmetic or numerical tolerance applies. Inventory memory uses
positive u64 MiB; invalid/overflowing numbers are rejected, never wrapped.

## Errors and recovery

Discovery reports unavailable for command, parse, or driver failures. Lock-open
and lock-I/O errors propagate; no fallback to unlocked GPU execution is allowed.
Kernel and device-reset recovery belong to SPEC-0010. OS lock release handles dead
owners.

## Compatibility and versioning

Linux flock interoperability is required and tested. Other platforms are not
supported in M0. nvidia-smi's documented CSV format is parsed with a CSV library.

## Security and resource limits

The lock path and parent directory MUST be trusted and shared by participating
runner accounts. Advisory locking is cooperative, not protection against malicious
users. Do not detach children or close inherited wrapper lock descriptors.
Discovery has a five-second subprocess deadline and piped output; a producer
that fills its pipe is killed at the deadline. Simulation never exceeds 60 seconds
of requested hold plus 60 seconds of requested wait, excluding OS scheduling delay.
Polling uses 10 ms intervals; exact deadline precision is not guaranteed.

## Examples

See [GPU operations](../operations/gpu.md) for discovery, simulation, and wrapper commands.

## Acceptance tests

Requirements 1-4: inventory parser tests, absent_management_tool_is_explicitly_unavailable,
and hardware discovery evidence in task state.
Requirements 5-10: exclusive_lease_times_out_and_serializes_waiters,
normal_exit_and_process_death_release_the_same_lock_inode,
cancellation_while_waiting_does_not_release_another_jobs_lease.
Requirements 11-12: signal process tests and shell_runner_and_rust_use_the_same_host_lock.
Requirement 13: wrapper/runner configuration; real CUDA enforcement belongs to
SPEC-0010 requirements 2 to 4, which read the selected UUID back from the driver.

## Open questions

Multi-user host lock provisioning depends on deployment. Detached worker process
trees still require their own contract. Kernel cancellation semantics are settled
by SPEC-0010 requirements 27 and 28, which bound cancellation latency by one
launch chunk and order lease release after context destruction.
