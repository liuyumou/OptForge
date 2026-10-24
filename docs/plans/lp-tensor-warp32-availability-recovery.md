# Accepted GPUP-8 availability-test recovery

Status: explicitly approved by the user on 2026-10-24. This is one bounded
recovery after the retained [availability stop](../benchmarks/lp-tensor-warp32-availability-gpup8.md),
not an automatic retry. Prior failures, charges, sources and receipts remain exact.

## Resource amendment

Add 1240 CPU seconds: 1200 native and 40 reporting. The cumulative ceiling is
37140 CPU seconds. Continuation allocations including prior charges are:

| Stage | CPU seconds |
| --- | ---: |
| Implementation | 258 |
| Proofs/admission | 800 |
| Native | 3600 |
| Workers and verification | 2052 |
| Reporting | 230 |
| Termination margin | 400 |
| Total | 7340 |

The separate [authorization](../benchmarks/data/tensor-warp32/availability-recovery-authorization-v1.json)
records the increase without rewriting the earlier ADR or frozen scientific
protocol. Its historical 6100 CPU field remains part of that immutable protocol;
the new journal governs prospective resource admission. Active journal:
artifacts/gpup-tensor-warp32-v1/cpu-journal-availability-recovery-v9.json.
Every prior charge carries forward. No implicit transfer or reclamation of
failed reservations is allowed. The unchanged supervisor charges four times
wall time, or the full reservation on failure, under its existing memory policy.

## Exact correction and evidence bridge

Change only the CUDA-sys test module: load/symbol/initialization errors imply
unavailability, while a version-query error can follow successful initialization.
Keep the existing supported-driver requirement on successful queries. Add mocked
positive and negative cases and include actual error details in the assertion.
Production driver bytes before the final cfg(test) module remain byte-identical.

The existing CPU evidence hashes whole source files, including tests. A separate
[bridge](../benchmarks/data/tensor-warp32/prerequisite-source-bridge.json) retains
exact before/after files and checks identical production bytes. It accepts only
this test-only change; any other numerical-source difference still refuses.
Historical CPU payloads are neither normalized nor re-signed. The historical PR
reader follows the additional explicit bridge. The verification-cache helper,
production binaries, images and numerical bodies stay unchanged.

## One gate and conditional continuation

The separate native entry preserves PATH, hides CUDA, runs every command in
tools/check.sh and compiles the four device test suites without running them.
Reserve 1200 native CPU seconds once, with a distinct native-acceptance-v3 receipt.
A full pass is required before freezing any study or reserving GPU work.

On success, the separate worker entry selects the active journal at runtime and
runs the existing frozen sequence under the 2052 worker CPU seconds. GPU limits
remain 790 total: 290 acceptance, 200 profiles/ablations, 300 primary timings.
Preserve all six acceptance jobs, 76 study cells, per-job reservations, complete
horizons, gain forecast, resource-fit estimate and independent verification.
The tighter CPU envelope may refuse even when GPU budget remains.

All [ADR-0045 completion and stop criteria](../decisions/ADR-0045-warp32-tensor-reference-recovery.md)
remain exact: useful INT8 and floating Tensor solves, original-model 1e-9
certification, 1e-7 local budgets, charged replay, five certified repetitions
without coverage loss and multiplicity-adjusted total-latency gain. A real
failure ends this recovery. No bootstrap rerun, host/container change, supervisor
change, second image, automatic retry, GPUP-9, publication or merge is authorized.

Execution disposition (2026-10-24): availability tests and all check.sh commands
pass, but the supervisor deadline prevents completed device inventory. Retain
the full 1200-CPU-second charge and exact passing source archive. No GPU work
or retry follows. See the [separate recovery report](../benchmarks/lp-tensor-warp32-availability-recovery-gpup8.md).
