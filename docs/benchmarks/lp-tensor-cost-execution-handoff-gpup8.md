# GPUP-8 cost continuation: execution handoff

Current stop: the authorized recovery reached the native command, which passed
Rust/native and dependencies but failed one of 401 Python tests on historical
registration scope. Its final resource packet was also truncated at 64 KiB.
The full 2200 native CPU seconds are charged and v6 is settled/failed; reporting
is exhausted. The [separate receipt](data/tensor-cost/native-transport-refusal.json)
and [proposed transfer/recovery](../plans/lp-tensor-cost-transport-recovery.md)
supersede the earlier pending recovery below. Repairs are prepared but unrun.
No full native pass, GPU reservation or device execution is claimed.

The explicitly authorized workspace-read retry succeeded. The current stop is a
later development integration run's guardian deadline, not the earlier command
tool interruption. The 160-CPU-second reservation supplied only 38 seconds of work
after margins. Cleanup is verified empty and the full reservation remains charged.
The current resource-v5 journal stays failed pending explicit recovery approval.
The separate [refusal receipt](data/tensor-cost/development-watchdog-refusal.json)
records all remaining stage allowances and the 23020.213097770-second CPU upper
accounting. No full native gate or device identity has run. New study tooling is
still unaccepted. Do not rerun the bootstrap or any attempted study identity.

The user-authorized corrected bootstrap passes. Final CPU admission and resource
checks support proceeding to the remaining ADR-0044 gates; GPUP-8 is incomplete.

Retained acceptance evidence:

- `data/tensor-cost/resource-admission-v3.json`: all 22 supervisor checks pass.
- `data/tensor-cost/cpu-admission-v2.json`: all 12 required dense trajectories
  pass; useful integer and floating component windows admit on both dense models.
- `data/tensor-cost/norm-proof-v2.json`: independent interval-Gram checks and
  canonical preparation comparisons pass.
- `data/tensor-cost/proofs-v2.json`: independent component arithmetic checks pass.
- `data/tensor-cost/instruction-admission.json`: actual SM120 Tensor instructions,
  at most 88 registers, zero spills. Compilation is not device acceptance.

All prior failed attempts and charges remain retained. The active CPU journal is
`artifacts/gpup-tensor-cost-v1/cpu-journal-resource-v3.json`. Do not rerun the
bootstrap or reset charges. No GPU execution or reservation has occurred in this
continuation. GPU completion, useful certified Tensor solves and a
multiplicity-adjusted total-latency gain remain unestablished.

Remaining work is the frozen device harness and full native acceptance, device
correctness acceptance, 16 profiles, the frozen forecast, and the conditional
60-timing study. Follow ADR-0044's existing stop conditions and resource ceilings.
No study retry, device substitution, additional allocation or GPUP-9 follows.

On 2026-10-23 the command tool's default sandbox could not start because user
namespaces are unavailable. Automatic approval review of an in-container read
timed out, and its permitted retry also timed out before execution. This tool
interruption is separate from the passing supervisor admission. No workload was
released by either command. Resume after container command execution is restored
or another retry is explicitly authorized.
