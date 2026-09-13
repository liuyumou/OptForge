# ADR-0009: CUDA Driver API as a Second Unsafe Boundary

Status: accepted
Owner: heterogeneous computation
Introduced: C6
Last reviewed commit: pending
Supersedes: ADR-0003's single-unsafe-boundary scope and ADR-0001's CUDA deferral; ADR-0001 through ADR-0008 otherwise remain in force

## Context

C6 requires running kernels. Every route to a GPU — the driver API, the runtime API,
`cudarc`, `cust`, NVML, or a hand-written boundary to an `nvcc`-compiled object —
requires `unsafe`, and the workspace sets `unsafe_code = "forbid"` with ADR-0003
permitting a single exception inside `optimizer-highs`. That prohibition is not
incidental. It has been treated as a blocker three separate times rather than
crossed: C3 specified a versioned C boundary without implementing it, C8 declined to
load dynamically distributed native components, and C9's Python SDK is recorded as
blocked because pyo3 needs a boundary ADR-0003 does not permit. Crossing it now is
the decision this record exists to make, and it should be crossed once, narrowly, and
in a place that does not weaken any of the three earlier refusals.

The constraint is structural rather than stylistic: a workspace-level `forbid` cannot
be relaxed by an inner crate, so any crate containing `unsafe` must decline to inherit
the workspace lints and restate them locally.

The hardware is three compute-capability-12.0 Blackwell devices. That capability
runs FP64 at one sixty-fourth of FP32, provides no tensor memory, and accepts
thread-block-cluster directives while `cluster.sync` degenerates to a no-op. A
dependency that assumes data-center Blackwell would therefore compile and silently
misbehave here, which raises the cost of taking one.

## Decision

**`optimizer-cuda-sys` owns the only new unsafe boundary, and it owns nothing else.**
A new crate declares `unsafe_code = "allow"` with `unsafe_op_in_unsafe_fn = "deny"`
locally rather than inheriting the workspace lints, exactly as `optimizer-highs`
does and for the same reason. It contains the foreign declarations, the RAII
wrappers, and nothing about optimization, schedules or models. `optimizer-cuda` keeps
`unsafe_code = "forbid"` and keeps discovery and the lease, so the crate that every
GPU consumer already depends on does not become unsafe. Every other runtime crate is
untouched.

**Resolve the driver library at runtime with `dlopen`, and link no NVIDIA code at
all.** The crate opens `libcuda.so.1` through `libc::dlopen` and resolves each entry
point with `dlsym`. `libc` is already in the lockfile transitively, so this adds no
third-party crate to a workspace that has eighteen and a `deny.toml` setting
`multiple-versions = "deny"`. Three consequences follow and each of them is the
reason for the choice rather than a side effect. An ordinary `cargo build` needs
neither the CUDA toolkit nor its driver stub, so CPU CI is unaffected. A host with no
driver produces a typed runtime error instead of a link failure, which is what makes
SPEC-0010 requirement 37 achievable rather than aspirational. And no NVIDIA library
is linked or redistributed, so the project's license record gains one build-time
tool and no runtime obligation.

**Use the driver API only: no runtime API, no cuBLAS, no cuSPARSE, no cuSOLVER.**
The driver API is the smaller and more explicit surface, it does not require the
toolkit at runtime, and it makes context and module lifetime ours rather than
implicit. Declining the math libraries costs us tuned kernels we would otherwise get
for free, and buys three things worth more here: control of reduction order, which is
what SPEC-0010 requirement 31 and SPEC-0011's determinism rule depend on; freedom from
a proprietary redistribution question; and the ability to tune for compute capability
12.0 rather than for the data-center part those libraries are optimized around.

**Write no dependency on `cudarc`, `cust`, `bindgen` or a `-sys` generator.** The
declarations are written by hand. The surface is roughly twenty entry points, it
changes rarely, and every one of them is a function this project calls deliberately.
A generator would import a large API we do not use, and a wrapper crate would import
a dependency tree that `deny.toml` would then have to adjudicate on every update.

**Map `CUresult` exhaustively with no catch-all arm.** This is SPEC-0002's
status-mapping rule applied to a second foreign boundary, and it exists for the same
reason: a CUDA upgrade that introduces a status must fail to compile rather than
silently classify a new failure as an old one.

**Build code objects out of tracked source, exactly as the pinned HiGHS library is
built.** `tools/setup_cuda.sh` invokes `nvcc -arch=sm_120` and writes a cubin and a
PTX file per kernel into `target/native/cuda/`. The build script probes for them and
sets `cfg(cuda_native)` only when they are present, warning and degrading to a build
that exposes the same API and reports an unsupported device backend. `nvcc` is
therefore a provisioning dependency, not a build dependency, which is the property
that keeps the existing CPU gate and CPU CI working unchanged on machines that have
never had a toolkit installed.

**Ship PTX beside every cubin.** The cubin is the compute-capability-12.0 fast path
and avoids driver compilation at load. The PTX is what lets a later capability load
at all. An earlier capability is refused rather than silently run, under SPEC-0010
requirement 4.

**This record authorizes a boundary, not an authority.** Nothing here grants a device
the ability to state a bound, a status or a proof. SPEC-0010 requirement 34 keeps
every device-produced candidate subject to `Model::evaluate`, which is the same rule
that governs the existing native backend's output.

## Alternatives

**An out-of-process CUDA C++ helper spoken to over pipes.** This is the project's
established escape hatch — C9's acceptance line names "a subprocess boundary needing
none" — and it would keep `unsafe_code = "forbid"` everywhere outside
`optimizer-highs`. Rejected because it moves the unsafe code rather than removing it:
the helper is C++, which has no such prohibition to begin with, so the safety gained
is bookkeeping. It also adds process spawn and serialization to every batch, which
caps the achievable crossover and would make a measured negative result unattributable
between the device and the transport.

**Depend on `cudarc` or `cust`.** Both are permissively licensed and both are
well-maintained. Rejected because they bring dependency trees into a workspace with
eighteen third-party crates and `multiple-versions = "deny"`, and because their
abstractions assume a device model we would then have to inspect anyway to satisfy
SPEC-0010's determinism and residency requirements. Reconsider if the hand-written
surface grows past what one file can hold.

**Link the driver stub at build time instead of `dlopen`.** Simpler code. Rejected
because it makes the CUDA toolkit a build dependency of the workspace, which breaks
the property that an ordinary `cargo build` works on a machine with no toolkit, and
turns an absent driver into a link error rather than the typed, recordable failure
SPEC-0010 requires.

**Use the runtime API and the math libraries.** Fastest route to a working PDLP.
Rejected for this slice because reduction order inside a vendor library is not ours to
fix, and SPEC-0010 requirement 31 makes bitwise reproducibility on one device a
contract rather than a nicety. Revisit only with a decision record that says what
determinism claim is being given up.

**Relax the workspace `forbid` to `deny` and allow locally where needed.** Rejected
outright. It would convert a structural boundary into a per-site judgement call, and
the value of the current arrangement is precisely that a crate must declare itself
unsafe in its manifest, where a reviewer sees it.

## Consequences

The workspace now has two unsafe boundaries instead of one, and the architecture
document's statement that `optimizer-highs` is the only such crate becomes false and
must be corrected rather than left as a stale claim.

Costs and limits, each recorded rather than absorbed:

- A device fault is outside the C3 extension host's containment claim, which covers
  panics only. A device-backed extension can therefore take down the process in ways a
  CPU extension cannot, and no memory budget is enforced per device consumer.
- `dlsym` returns an untyped pointer and the correctness of every signature is a
  human claim, not a compiler-checked one. This is the same class of risk the HiGHS
  header boundary carries, but without a header to check against; the mitigation is
  that the surface is small, hand-written, and exercised by the device suite.
- Sanitizer coverage for the new boundary requires a device, so it can only run on the
  labeled runner. That runner is not provisioned today, and until it is, device
  sanitizer coverage is uncovered and must be recorded as such rather than assumed.
- `nvcc` is a provisioning dependency under the CUDA Toolkit licence. No NVIDIA code
  is linked or redistributed, but the generated code objects are build outputs of a
  proprietary compiler and stay outside tracked source for the same reason the pinned
  HiGHS build does.
- The three earlier refusals are unchanged and must stay unchanged. This record does
  not authorize dynamically loaded native extensions, a pyo3 boundary, or a second
  process-isolation story; each still needs its own record.

Follow-up work, each needing its own contract: device-side containment or process
isolation for device-backed extensions, per-device memory budgeting, multi-device
residency, and whether the host lock should shard per device.

## Implementation and Tests

This record is accepted before its implementation, as ADR-0004 through ADR-0008 each
were.

Implementation: [SPEC-0010](../specifications/SPEC-0010-heterogeneous-computation.md)
in a new `optimizer-cuda-sys` crate, kernels under `cuda/`, provisioning in
`tools/setup_cuda.sh`, residency and selection in `optimizer-cuda`, and the device
surface in `optimizer-cli`.

Acceptance evidence is SPEC-0010's mapped tests plus a complete
`bash tools/check.sh` with native acceptance covered on a host with no device, which
is what establishes that the boundary is optional, and the device suite under
`tools/gpu_job.sh` on hardware, which is what establishes that it works.
