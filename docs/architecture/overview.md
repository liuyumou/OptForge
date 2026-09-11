# Architecture

Purpose: define stable ownership boundaries. Scope: M0-M1, C1, C2, C3 and C4, plus planned dependencies.
Owner: architecture. Status: accepted.
Last reviewed commit: f8d6091.

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

optimizer-experiment owns the run record: one search record embedded verbatim
plus the provenance needed to repeat it, and the field-by-field comparison that
decides whether a repeat agreed. The CLI exposes it as `optimizer search` and
`optimizer verify`, which is the first surface reaching the executive from
outside Rust test code. Verification re-runs using only the record's embedded
configuration, so it cannot confirm its own input, and a record is bound to model
bytes by fingerprint rather than by `model_id`. Agreement is evidence of
determinism on one host; it adds no mathematical authority and cannot clear a
forfeited proof claim. See
[SPEC-0005](../specifications/SPEC-0005-run-surface.md) and
[ADR-0006](../decisions/ADR-0006-run-provenance.md).

## Planned numerical flow

Original model -> optimizer-core validation -> optimizer-solver executive ->
optimizer-highs LP backend and optimizer-schedule candidate production ->
optimizer-core result validation -> experiment record and CLI.

C4 closes the last leg for search: the CLI drives the executive and
optimizer-experiment wraps its record with provenance, so the flow runs end to
end without an agent. C5 completes the flow's first application under
[SPEC-0008](../specifications/SPEC-0008-flow-shop.md): a scheduling instance is
encoded into an ordinary optimizer-core model, so the existing legs carry it
unchanged rather than gaining a parallel scheduling path, and a makespan recurrence
independent of every heuristic is the authority on what a resulting schedule costs.
optimizer-schedule-examples holds the NEH and insertion producers and depends only
on the published core, extension and scheduling APIs.

C1 implements the backend leg of this flow: the CLI drives optimizer-highs
directly through the backend-neutral contract in optimizer-core, and every
extracted candidate returns through optimizer-core validation before publication.

C2 implements the executive leg under
[SPEC-0003](../specifications/SPEC-0003-solver-executive.md) and
[ADR-0004](../decisions/ADR-0004-owned-search.md). optimizer-solver owns node
state, budgets, cancellation, incumbent acceptance and proof completion, and
consumes the C1 `Backend` trait purely as a relaxation service. It does not
depend on optimizer-highs, so its correctness contracts run without a native
library; the end-to-end test over pinned HiGHS lives in optimizer-highs instead.

Two proof claims stay distinct. A backend `Termination` describes one relaxation
solve; a `SearchOutcome` describes whether the executive exhausted its node tree.
A relaxation objective becomes a dual bound only when that relaxation proved
optimality, and any other termination forfeits the search's proof claim.

The core owns feasibility, objective recomputation, and mathematical status.
Extensions may propose candidates or actions; the core must validate them.
C3 implements that rule under
[SPEC-0004](../specifications/SPEC-0004-extension-runtime.md) and
[ADR-0005](../decisions/ADR-0005-extension-authority.md). optimizer-extension
owns the declaration document, the authority model derived from an extension's
category, and the guarded host that counts budgets and contains panics.
optimizer-solver validates every proposal with `Model::evaluate` against the
original model and every action against its real frontier and its own
recomputed branchable set. No extension path can forfeit a proof claim, end a
search, or return an error, so an adversarial extension cannot deny a proof the
engine would otherwise complete. Containment covers panics, not a process abort;
process isolation and dynamically loaded native extensions are deferred.

Raw native handles remain inside the corresponding FFI crate.
M1 defines candidate numerical tolerances. C1 records backend termination under
explicit native settings; owned proof contracts belong to C2.

## Ownership and resources

| Crate | Responsibility | First behavior |
| --- | --- | --- |
| optimizer-core | Original models, numerical validation, solve contract | M1 / C1 |
| optimizer-highs | Safe backend lifecycle and status mapping | C1 |
| optimizer-schedule | Flow-shop instances, recurrence, encoding and heuristics | C5 |
| optimizer-schedule-examples | Independently authored scheduling candidate producers | C5 |
| optimizer-solver | Search executive, branch and bound | C2 |
| optimizer-extension | Extension declarations, authority model, guarded host | C3 |
| optimizer-extension-examples | Independently authored and adversarial extensions | C3 |
| optimizer-cuda | Discovery, ownership, later kernels | M0 / C6 |
| optimizer-experiment | Artifact schemas, run records, verification comparison | M0 / C4 |
| optimizer-cli | Agent-independent command interface | M0 / C4 |

optimizer-highs is the only crate permitted to contain unsafe code. Because a
workspace-level `forbid` cannot be relaxed by an inner crate, it declares its own
lints rather than inheriting the workspace lints; every other runtime crate keeps
the prohibition. See [ADR-0003](../decisions/ADR-0003-highs-backend.md). The
extension runtime keeps that prohibition too, which is why C3 specifies the
versioned C boundary without implementing it: a second unsafe boundary needs its
own decision record. See [ADR-0005](../decisions/ADR-0005-extension-authority.md).

All GPU devices share one host lease. Selection uses UUIDs. Later transfers and
batching must be explicit; timings include overhead. Multi-GPU work is deferred.
See [ADR-0001](../decisions/ADR-0001-bootstrap-boundaries.md),
[lease implementation](../../crates/optimizer-cuda/src/lib.rs), and
[acceptance tests](../../crates/optimizer-cli/tests/cli.rs).
