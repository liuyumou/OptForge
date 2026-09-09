# Architecture

Purpose: define stable ownership boundaries. Scope: M0-M1 and C1, plus planned dependencies.
Owner: architecture. Status: accepted.
Last reviewed commit: 98033db.

## Implemented boundaries

The CLI delegates inventory and advisory ownership to optimizer-cuda. That crate
uses nvidia-smi and standard-library file locks without linking CUDA.
optimizer-experiment embeds the versioned JSON Schemas. Python validation tools
apply the schemas and cross-record provenance checks.

optimizer-core stores immutable validated original linear models. Rust and
versioned JSON share construction checks. Candidate evaluation recomputes objective,
row activities, bounds and domains using explicit caller tolerances. The CLI reads
bounded model/candidate files and returns validation reports. See
[SPEC-0001](../specifications/SPEC-0001-model-and-validation.md) and
[ADR-0002](../decisions/ADR-0002-model-validation.md).

optimizer-core also owns the backend-neutral solve contract: explicit solve
options, cooperative cancellation, engine-owned termination, model-bound warm
starts and reproducible records. optimizer-highs implements it against the pinned
CPU HiGHS 1.11.0 build behind a private FFI boundary, and the CLI exposes it as
`optimizer solve`. See
[SPEC-0002](../specifications/SPEC-0002-backend-contract.md) and
[ADR-0003](../decisions/ADR-0003-highs-backend.md).

## Planned numerical flow

Original model -> optimizer-core validation -> optimizer-solver executive ->
optimizer-highs LP backend and optimizer-schedule candidate production ->
optimizer-core result validation -> experiment record and CLI.

C1 implements the backend leg of this flow: the CLI drives optimizer-highs
directly through the backend-neutral contract in optimizer-core, and every
extracted candidate returns through optimizer-core validation before publication.
The optimizer-solver executive is not yet implemented, so no owned search sits
between the two.

The core owns feasibility, objective recomputation, and mathematical status.
Extensions may propose candidates or actions; the core must validate them.
Raw native handles remain inside the corresponding FFI crate.
M1 defines candidate numerical tolerances. C1 records backend termination under
explicit native settings; owned proof contracts remain deferred to C2.

## Ownership and resources

| Crate | Responsibility | First behavior |
| --- | --- | --- |
| optimizer-core | Original models, numerical validation, solve contract | M1 / C1 |
| optimizer-highs | Safe backend lifecycle and status mapping | C1 |
| optimizer-schedule | Flow-shop recurrence and heuristics | C5 |
| optimizer-solver | Search executive, branch and bound | C2 |
| optimizer-cuda | Discovery, ownership, later kernels | M0 / C6 |
| optimizer-experiment | Schemas, later experiment execution | M0 / C4 |
| optimizer-cli | Agent-independent command interface | M0 |

optimizer-highs is the only crate permitted to contain unsafe code. Because a
workspace-level `forbid` cannot be relaxed by an inner crate, it declares its own
lints rather than inheriting the workspace lints; every other runtime crate keeps
the prohibition. See [ADR-0003](../decisions/ADR-0003-highs-backend.md).

All GPU devices share one host lease. Selection uses UUIDs. Later transfers and
batching must be explicit; timings include overhead. Multi-GPU work is deferred.
See [ADR-0001](../decisions/ADR-0001-bootstrap-boundaries.md),
[lease implementation](../../crates/optimizer-cuda/src/lib.rs), and
[acceptance tests](../../crates/optimizer-cli/tests/cli.rs).
