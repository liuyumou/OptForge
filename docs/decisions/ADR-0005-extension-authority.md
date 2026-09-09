# ADR-0005: Extension Authority Boundary

Status: accepted
Owner: extension runtime
Introduced: C3
Last reviewed commit: b934dbd
Supersedes: none; ADR-0001, ADR-0002, ADR-0003 and ADR-0004 remain in force

## Context

C2 is complete: optimizer-solver owns a branch-and-bound executive that proves
optimality of the original model, using the C1 backend contract as a relaxation
service. But the only replaceable seam in the engine is `&dyn Backend`. Node
selection and branching-variable choice are private functions inside the
executive, so nothing outside the workspace can contribute a heuristic candidate
or a search decision. The architecture's claim that extensions declare
capabilities and authority while the core validates candidates, actions and proof
claims has no implementation behind it.

[SPEC-0003](../specifications/SPEC-0003-solver-executive.md) excluded extensions
and the authority model from C2 while requiring that its node and work-item
interfaces stay usable by them. The Stage 2 entry condition requires an accepted
specification before any public extension API exists.

## Decision

Implement [SPEC-0004](../specifications/SPEC-0004-extension-runtime.md) in a new
optimizer-extension crate plus an integration layer in optimizer-solver, in safe
Rust, retaining the workspace `unsafe_code = "forbid"` prohibition;
optimizer-highs remains the only crate permitted to contain unsafe code.

Extensions propose; the core decides. A candidate producer's output becomes an
incumbent only after `Model::evaluate` validates it against the original model,
and the recorded objective is that recomputation. An extension's own claimed
objective is never read. This is the decision that keeps the authority model from
degenerating into trust.

No extension path may forfeit the proof claim, break the search loop, or return
an error from the search entry point. C2 forfeits when a relaxation misbehaves,
because the executive can then no longer trust its bounds. A bad extension
candidate implies nothing about any bound, so it is a recorded rejection and a
disable. Without this rule an adversarial extension could deny a proof the engine
would otherwise complete, which is the same class of failure as reporting a
timeout as optimality.

Advised branching is restricted to variables the executive itself computed as
above its integrality tolerance at this node. This is a termination requirement
rather than a preference: branching on an integral value produces two children
that do not tighten the node, and the search could regenerate an identical child
indefinitely. It is SPEC-0003 requirement 12a's lesson applied to a second
source of untrusted input. Advice chooses which variable to split, never how, so
requirement 10's covering children are preserved by construction.

Extensions receive owned read-only snapshots, not borrowed view traits. Traits
would have to duplicate node and restriction shapes anyway, because
optimizer-extension cannot depend on optimizer-solver; they cannot carry a
schema version that a record reader can check; and a live borrow across the
invocation fights the executive's own `&mut self` node selection. The frontier
snapshot deliberately omits per-node restriction lists, which would breach
SPEC-0003's memory clause if copied every iteration.

Budgets are counted in invocations and proposals, never wall clock. A
time-based extension budget would make the search path depend on machine speed
and break requirement 21's determinism outright.

Panics are contained with `catch_unwind` and the offending extension is disabled
for the rest of the search. Disabling is required for soundness: an extension
that panicked mid-operation may be permanently unusable, so re-invoking it could
panic indefinitely. Containment covers panics only; process abort and memory
faults are outside it and are not claimed.

`SEARCH_SCHEMA_VERSION` moves from 1 to 2 so search configuration carries the
extension policy and search records carry per-extension summaries. Search
configuration is a strict all-fields-required document, so there is no additive
alternative, and a version-1 record of an extension-influenced search would claim
to be sufficient to repeat a search it does not describe.

No `backend` extension category is introduced. Replaceable numerical backends
already exist under SPEC-0002's public `Backend` trait; declaring the category
here and refusing it would misrepresent that contract as narrower than it is.
The transformation category is refused at declaration time, so no code path
applies a transformation until its validity has a contract of its own.

Existing seeds, tolerances, thresholds, splits and solver defaults do not change.

## Alternatives

Making extensions mutate executive state directly would be simpler and is what a
plugin system usually does; it is rejected because it puts the proof claim inside
untrusted code. Letting an extension's rejected output forfeit the proof would be
the conservative-looking choice and is rejected for the opposite reason: it hands
every extension a veto over correctness the engine can establish on its own.
Trusting a producer's reported objective would avoid a validation pass and is
rejected because an unchecked objective is exactly the "declare success by
returning a number" failure the research plan names. Keeping
`SEARCH_SCHEMA_VERSION` at 1 and emitting a separate extension record would
churn no tests, but the side-car can be discarded while the search record still
claims proven optimality. Implementing the C ABI and dynamic loading now would
require a second unsafe boundary and amend ADR-0003 without any extension yet
needing it.

## Consequences

C3 is the implementation scope; C4 through C7 remain specification-gated. The
runtime is in-process, so a hostile extension can still abort the process or
exhaust memory; that is stated rather than hidden, and process isolation is
deferred with its own decision record. An adversarial adviser can waste a node
budget and turn a provable search into a limited one, which is exploration
quality rather than correctness, so the equivalence evidence is stated over
unlimited budgets.

Search documents move to version 2, and four existing C2 record tests must be
repaired rather than renumbered: three of them assert on the first
`schema_version` occurrence or on a struct literal in ways that would silently
stop testing what they name.

No performance claim is made. Whether advisers improve search is C7's question.

## Implementation and Tests

Implementation in [optimizer-extension](../../crates/optimizer-extension/src/lib.rs)
and [optimizer-solver](../../crates/optimizer-solver/src/lib.rs) over the
[evaluation authority](../../crates/optimizer-core/src/evaluate.rs), verified
through the [gate](../../tools/check.sh). No behavior is implemented by this
decision record. Acceptance evidence is recorded in
[active task](../../state/active-task.md); C3 is not complete until its full gate
and adversarial extension tests pass.