# Project Status

The repository implements the C4 agent-independent run surface on top of C3
extension safety, C2 owned branch-and-bound search, C1 pinned HiGHS solving, M1
model and candidate validation and the M0 bootstrap. Acceptance
evidence is recorded in [active task](../state/active-task.md).

| State | Features |
| --- | --- |
| Implemented | Original linear models, Rust/JSON/CLI candidate validation with explicit tolerances, backend-neutral solve contract, pinned CPU HiGHS LP/MILP solving with validated incumbents and reproducible records, owned branch-and-bound executive with budgets, cancellation and proof completion, extension runtime with declared authority, validated candidate producers and checked search advisers, typed extension failure records, CLI search over the executive with provenance-bearing run records and re-execution verification, workspace, CLI hello, GPU discovery, simulated leases, artifact schemas, CI and documentation tooling |
| Planned | Flow-shop slice (C5), GPU feasibility and adaptive research (C6/C7), registry and SDK (C8) |
| Experimental | None enabled |
| Deprecated | None |

Solve records recompute objectives and violations independently of the backend. A
backend optimality claim holds under the recorded numerical settings; it is not an
exact certificate, and a limit, interruption or failure is never reported as a
completed proof. Owned search adds a second, distinct claim: proven optimality
means the executive exhausted its own node tree with every prune justified by a
relaxation that itself proved optimality. A search whose relaxation hit a limit
forfeits that claim and says so. Extensions may propose candidates and search
actions; the core validates every one of them, and no extension can forfeit a
proof, end a search or change its outcome. Extension containment covers panics,
not a process abort. A search is recorded with the revision, model fingerprint
and input hashes needed to repeat it, and verification re-runs that search from
the record alone rather than trusting its stored result; agreement establishes
determinism on one host, never optimality, and a forfeited search stays forfeited
after it verifies. No Python SDK, CUDA kernel, extension registry, dynamically
loaded native extension, checkpoint restart or comparative experiment runner is
available, cross-host reproducibility is untested, and no solver performance
claim is made.

See the [M1 contract](../docs/specifications/SPEC-0001-model-and-validation.md),
[backend contract](../docs/specifications/SPEC-0002-backend-contract.md),
[solver executive contract](../docs/specifications/SPEC-0003-solver-executive.md),
[extension runtime contract](../docs/specifications/SPEC-0004-extension-runtime.md),
[run surface contract](../docs/specifications/SPEC-0005-run-surface.md),
[backlog](../state/backlog.yaml) and
[implementation plan](../implementation-plan.md) for evidence stages and dependencies.