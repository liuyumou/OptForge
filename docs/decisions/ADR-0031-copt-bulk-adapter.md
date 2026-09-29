# ADR-0031: COPT Bulk Construction Comparison

Status: accepted by the maintainer on 2026-09-29 before implementation.
Scope: SPEC-0019; gpup-copt-adapter-v1; development only.

Use a separate loadMatrix worker with exact CSC coefficients, explicit sense and
offset, canonical ID ordering/names and preserved import guards. Compare unchanged
scalar construction in the same new isolated Python 3.11 / NumPy 2.3.4 / SciPy
1.16.3 environment, with pinned COPT 8.0.6 bytes. No license is copied or archived.
External evidence v2, fresh original-model host certification, parameters and
historical wrappers/environments remain unchanged. No runtime/native boundary.

Freeze 72 timings: small-4, irregular-32768, dense_block-65536, mixed-65536;
three COPT methods (CPU default, CPU PDLP, GPU PDLP); scalar/bulk; three repeats.
Twelve profiles cover small-4 and dense_block-65536, all methods and adapters.
Timings precede profiles. Order seed 17001, bootstrap seed 17002, 10000 resamples
and 95% intervals. Solver seed 17, one thread, 1e-9 tolerances, 50000 aggregate
native iterations; unavailable COPT PDLP hard work/seed controls remain explicit.
Preserve per-model 10/30-second deadlines, two-second cleanup, 128 MiB model,
32 MiB output-file and 8 GiB host limits, and 120-second CPU verification bound.
Every fresh process includes imports and output; no cached assessment or session.

Resources: four build jobs, four CPU-hours; timings 900 GPU seconds in ablations,
profiles 200 and acceptance 400 in repeatability; combined 1500 with no borrowing.
No added allowance. Carry 15632281207415 / 18002574545061 GPU nanoseconds,
15606 ledger events and SHA-256
ad3d84354f0b74ae62fcc019ee4dcbf29b0a3251d066f1e0f2df11ccb107230b.
Preserve all prior prefixes, phase caps and original output binding. Reserve full
worker bounds and serialize every device job under the shared host lease. Retain
failures/partial outputs, stop at limits and never retry admitted study identities.

Acceptance: dependency-free CSC/import/identity/budget/failure contracts; real
CPU scalar/bulk native readback against canonical input; 24 min/max endpoints
(three methods, two adapters, profile off/on), fresh certification and independent
verification. Compare binary64 numerical state/native work excluding clocks and
memory reports. Full pinned-native tools/check.sh before device admission and
at completion. Unchanged project CUDA code retains prior sanitizer receipts.

Report all attempts, coverage, paired latency medians/bootstrap intervals,
component costs, profile overhead and construction versus numerical/work agreement.
Withhold unsupported equivalence/work claims and retain mixed-65536 failures.
Negative performance completes the investigation; no preset/default follows.
Commit locally after acceptance, no push; hand off to GPUP-CONVERGENCE only.
