# Project Status

The repository implements C1 pinned HiGHS solving on top of M1 model and candidate
validation and the M0 bootstrap. Acceptance evidence is recorded in
[active task](../state/active-task.md).

| State | Features |
| --- | --- |
| Implemented | Original linear models, Rust/JSON/CLI candidate validation with explicit tolerances, backend-neutral solve contract, pinned CPU HiGHS LP/MILP solving with validated incumbents and reproducible records, workspace, CLI hello, GPU discovery, simulated leases, artifact schemas, CI and documentation tooling |
| Planned | Owned solver executive and extension runtime (C2/C3), SDK/registry and flow-shop slice (C4/C5), GPU feasibility and adaptive research (C6/C7) |
| Experimental | None enabled |
| Deprecated | None |

Solve records recompute objectives and violations independently of the backend. A
backend optimality claim holds under the recorded numerical settings; it is not an
exact certificate, and a limit, interruption or failure is never reported as a
completed proof. No owned search, Python SDK, CUDA kernel or extension registry is
available.

See the [M1 contract](../docs/specifications/SPEC-0001-model-and-validation.md),
[backend contract](../docs/specifications/SPEC-0002-backend-contract.md),
[backlog](../state/backlog.yaml) and
[implementation plan](../implementation-plan.md) for evidence stages and dependencies.