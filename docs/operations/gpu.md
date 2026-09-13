# GPU Operations

Purpose: enforce one active project GPU job on a host. Scope: Linux and cooperative
jobs under a trusted runner account.

## Discovery

```bash
cargo run -p optimizer-cli -- gpu discover --dry-run
```

This queries nvidia-smi only; no lease or CUDA context is needed. The current
development host was observed with these identities (availability may change):

| UUID | Model |
| --- | --- |
| GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48 | NVIDIA GeForce RTX 5090 |
| GPU-c62a3b14-42bb-3c9b-c2b2-3374726b1a02 | NVIDIA GeForce RTX 5090 |
| GPU-6721b13a-30f9-83ec-dace-ba2d9738556f | NVIDIA RTX PRO 6000 Blackwell Server Edition |

These are observations, not required devices on other hosts or claimed benchmark
results. The [contract](../specifications/SPEC-0006-gpu-lease.md) accepts any valid
inventory, sorted by UUID.

## Simulated ownership

```bash
cargo run -p optimizer-cli -- gpu lease --simulate-ms 500 --timeout-ms 5000
```

Events report waiting, acquisition, and release as JSON lines. SIGINT/SIGTERM cancels with
exit 130. No device is touched. A held lease releases on normal exit, cancellation,
or process death; do not remove the lock file.

## Device work

```bash
bash tools/setup_cuda.sh                      # nvcc -> target/native/cuda
bash tools/gpu_job.sh GPU-<uuid> bash tools/gpu_check.sh
```

`gpu_check.sh` runs the device suite and then `compute-sanitizer` with memcheck,
racecheck, initcheck and synccheck. It refuses to run without an inherited lease
rather than taking one itself, so it cannot be invoked outside the wrapper that
names a single device, and it reports loudly rather than silently passing when
`compute-sanitizer` is absent.

Device tests are opt-in. Without `AI_OPTIMIZER_GPU=1` they report an explicit skip,
so `bash tools/check.sh` stays CPU-only even on a host that has a device; a suite
that silently took the host lease would contend on a lock that permits one holder
for the whole host. The wrapper exports `AI_OPTIMIZER_GPU_LEASE=inherited`, which is
how a child knows not to acquire the lock its parent already holds.

## Real jobs

```bash
bash tools/gpu_job.sh GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48 nvidia-smi -L
```

The wrapper sets CUDA_VISIBLE_DEVICES to one UUID and takes the same flock lock
as Rust. nvidia-smi itself lists physical inventory irrespective of CUDA visibility.
All GPU consumers on a host MUST use the same absolute AI_OPTIMIZER_GPU_LOCK
(default /tmp/ai-optimizer-gpu.lock), including other checkouts and device models.
Provision a persistent, trusted shared lock path for multiple runner accounts.
Never unlink/replace that file while jobs may be active. A lock is not a sandbox:
uncooperative processes can bypass it. GPU commands must remain foreground and
must not close the inherited lock descriptor or escape into detached workers.
Do not nest the wrapper around a command that acquires the lease again.

CI uses both a repository-wide concurrency group and the host file lock. Only
trusted manual workflows use the self-hosted runner; fork PRs receive CPU checks.
A host administrator must apply the wrapper to all project GPU jobs. Container
jobs must bind-mount the same host lock file. GPU compiler and sanitizer installation
belongs only on the labeled runner, and is required there by
[SPEC-0010](../specifications/SPEC-0010-heterogeneous-computation.md), which
introduces kernels. The runner is not provisioned yet; see
[known failures](../../state/known-failures.md).
