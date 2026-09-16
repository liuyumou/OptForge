# ADR-0020: Diagnose FP32 LP Latency Without Changing the Solver

Status: accepted under the maintainer's explicit request to carefully measure and investigate FP32 latency.
Scope: GPUP-5 diagnostic follow-up; supplements ADR-0019, no GPUP-6 behavior.

## Decision

Preserve the complete gpup5-fp32-v1 study, its 480 attempts, numerical settings,
code objects and archived source. Add gpup5-diagnosis-v1 diagnostic evidence only.
No runtime arithmetic, controller, guards, tolerances or defaults are changed.
A short-run timing is never substituted for time to an independently certified
solution. No supported preset is selected.

Freeze 213 diagnostic GPU jobs before execution:

- Seven randomized repetitions on each of small-4, irregular-256, irregular-2048
  and dense_block-1024, for existing tuned FP64 and the six precision configurations:
  196 untraced, profiled short runs. Use order seed 17001 and the original method,
  solve seed 17, one CPU thread/core, 1e-9 targets and check interval 200.
- Stop at 200 proposed updates: a physical limit of 200 without correction or
  206 with correction every 32 steps. Both method and solve work limits explicitly
  record this diagnostic change. A range stop remains a failure, never filled in.
- One Nsight Systems CUDA trace on small-4 and irregular-2048 for all seven modes:
  14 traced companions, with CPU sampling/context switches disabled.
- Three Nsight Compute attempts on irregular-2048 (precision FP64, FP32 products,
  FP32 accumulation), selecting two sparse kernels after twenty matching launches.
  Disable profiler clock control and cache flushing. Collect launch, compute,
  memory and speed-of-light sections. Unavailable counters
  or permission failures remain explicit failures; no policy/configuration change
  is authorized to obtain counters. Profiler replay is diagnostic work, not a solver
  iteration or valid primary timing sample.

Use the same RTX 5090 UUID, quiet-device checks and shared host-wide lease for all
jobs. Untraced/Nsight Systems deadlines remain ten seconds plus two-second cleanup;
Nsight Compute gets thirty seconds plus two-second cleanup. All use 8 GiB RSS and
LP buffer limits and bounded raw output. Reserve sixteen or thirty-six seconds
respectively, including lease admission. No retries or warmup solves. Keep
process outcomes, original-model endpoint verification, hashes, telemetry and
profiler identity. Trace launch counts must agree with endpoint counters.

Charge all GPU diagnostics to the original campaign ledger and screening phase.
Preserve the entire 2862-event prefix with SHA-256
66d8c2b0ee24ce050ee051c6dbea2184361abe2c2fc4a57b8ee202c001479ff0 and
1324210639253 charged nanoseconds. This follow-up admits at most 300 additional
seconds, inside the already authorized cumulative 4502574545061-nanosecond ceiling
and unchanged global/phase caps. A cap stops the diagnostic with incomplete
coverage; it does not grant another allowance. Preserve original output binding.
Historical reporting uses its archived ledger prefix, not later diagnostic charges.
No earlier report, snapshot, raw file or accepted hash is rewritten.

CPU-only inspection uses the original twelve development models and archived
endpoints. Export exact binary64 preconditioner/scaled/represented values through
existing Rust APIs. Compare original and represented row activities using Python
exact rational arithmetic, with the original host allowance; this is a numerical
error diagnostic, not a new represented-model certificate. Inspect provisioned
PTX/SASS and profiler observations without introducing another runtime boundary.
Use four build jobs and a two-hour CPU validation ceiling.

## Acceptance and report

Full pinned-native tools/check.sh for diagnostic tooling; exact historical hashes
and ledger prefix; independently verified short endpoints; operation-count checks
against traces; preservation of unsuccessful outcomes and unavailable metrics.
Separate convergence/work amplification, equal-update host/kernel costs, correction,
startup and representation bias. Distinguish measured facts from optimization
hypotheses. Runtime repairs or adaptive recovery require a later accepted slice.
