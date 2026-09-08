# Project Status

The repository implements M1 model and candidate validation plus M0 bootstrap.
Acceptance evidence is recorded in
[active task](../state/active-task.md).

| State | Features |
| --- | --- |
| Implemented | Original linear models, Rust/JSON/CLI candidate validation with explicit tolerances, workspace, CLI hello, GPU discovery, simulated leases, artifact schemas, CI and documentation tooling |
| Planned | HiGHS M2, CPU flow shop M3, owned MILP M4, CUDA evaluator M5, evidence package M6 |
| Experimental | None enabled |
| Deprecated | None |

Candidate reports recompute objectives and violations; they are not solver proofs.
No solver, Python SDK, CUDA kernel or extension registry is available.
See the [M1 contract](../docs/specifications/SPEC-0001-model-and-validation.md),
[backlog](../state/backlog.yaml) and
[implementation plan](../implementation-plan.md) for dependency and research stages.
