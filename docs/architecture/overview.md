# Architecture

Purpose: define stable ownership boundaries. Scope: M0-M1 and planned dependencies.
Owner: architecture. Status: accepted.
Last reviewed commit: 9e6dc86534de2efa414205752ca58d7584976052.

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

## Planned numerical flow

Original model -> optimizer-core validation -> optimizer-solver executive ->
optimizer-highs LP backend and optimizer-schedule candidate production ->
optimizer-core result validation -> experiment record and CLI.

The core owns feasibility, objective recomputation, and mathematical status.
Extensions may propose candidates or actions; the core must validate them.
Raw native handles will remain inside the corresponding FFI crate.
M1 defines candidate numerical tolerances; solver proof contracts remain deferred.

## Ownership and resources

| Crate | Responsibility | First behavior |
| --- | --- | --- |
| optimizer-core | Original models, numerical validation | M1 |
| optimizer-highs | Safe backend lifecycle and status mapping | M2 |
| optimizer-schedule | Flow-shop recurrence and heuristics | M3 |
| optimizer-solver | Search executive, branch and bound | M4 |
| optimizer-cuda | Discovery, ownership, later kernels | M0 / M5 |
| optimizer-experiment | Schemas, later experiment execution | M0 / M6 |
| optimizer-cli | Agent-independent command interface | M0 |

All GPU devices share one host lease. Selection uses UUIDs. Later transfers and
batching must be explicit; timings include overhead. Multi-GPU work is deferred.
See [ADR-0001](../decisions/ADR-0001-bootstrap-boundaries.md),
[lease implementation](../../crates/optimizer-cuda/src/lib.rs), and
[acceptance tests](../../crates/optimizer-cli/tests/cli.rs).
