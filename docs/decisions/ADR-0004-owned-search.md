# ADR-0004: Owned Search Executive Boundary

Status: accepted
Owner: search executive
Introduced: C2
Last reviewed commit: c742064
Supersedes: none; ADR-0001, ADR-0002 and ADR-0003 remain in force

## Context

C1 is complete: the pinned CPU HiGHS backend solves LP and MILP models behind the
backend-neutral contract, and every extracted candidate is re-validated against
the original model. That leaves the project with no owned search. The backend's
own branch-and-bound is currently the only thing proving MILP optimality, so the
architecture's central claim, that the engine owns mathematical authority, is not
yet supported by an implementation.

[SPEC-0002](../specifications/SPEC-0002-backend-contract.md) deliberately deferred
safe owned-search pruning to a C2 contract. The roadmap's Stage 2 requires an
accepted specification before any public search API exists.

## Decision

Implement [SPEC-0003](../specifications/SPEC-0003-solver-executive.md) in
optimizer-solver, in safe Rust, retaining the workspace `unsafe_code = "forbid"`
prohibition; optimizer-highs remains the only crate permitted to contain unsafe
code.

The executive uses the C1 `Backend` trait as a relaxation service and MUST NOT
depend on optimizer-highs, so the first owned search is backend-neutral by
construction and testable against a stub backend.

Introduce a `SearchOutcome` type distinct from `Termination` rather than reusing
it. The two describe different claims: `Termination` reports what one relaxation
solve did, while `SearchOutcome` reports whether the executive exhausted its own
node tree. Reusing one type would let a relaxation's `Optimal` be read as
original-model optimality.

Admit a dual bound only from a relaxation that reported proven optimality. Any
other relaxation termination leaves the node bound unavailable, forbids pruning
that node by bound, and permanently forfeits the search's proof claim, recorded
explicitly as `forfeited` in the record. This is the decision that keeps a
timeout inside a child solve from silently discarding an optimal solution.

Nodes restrict discrete variable bounds only, and node relaxations preserve the
original model and variable IDs so extracted candidates evaluate directly against
the original model. Do not reuse an LP basis across nodes: a basis is bound to an
exact canonical model fingerprint, and cross-node reoptimization is Stage 5 work.

Budgets, seed and tolerances stay caller-supplied with no defaults, matching M1
and C1. Checkpoints are specified in shape; restart is not implemented in C2.

## Alternatives

Delegating MILP search to HiGHS would work today but leaves the project with no
owned search and destroys the independent reference: the same code would be both
the implementation and the thing it is checked against. Reusing `Termination` for
search outcomes would conflate two different proof claims. Pruning on a
best-effort bound from a limited relaxation would be faster and is what an
unprincipled implementation does; it is rejected because it can silently return a
suboptimal answer labelled optimal. Depending on optimizer-highs directly would
have made the executive untestable without the native library.

## Consequences

C2 is the implementation scope; C3 through C7 remain specification-gated. The
executive is slower than a mature solver's search, and that is accepted: C2
establishes correctness and makes no performance claim. Forfeiture means a
constrained environment may legitimately produce searches that find good
incumbents and prove nothing, which the record must state plainly.

Stub-backend tests cover the pruning and forfeiture rules without the native
library, so those contracts stay covered even when HiGHS is skipped; native
relaxation tests still report an explicit skip rather than false coverage.

No existing seed, tolerance, threshold, split, schema version or solver default
changes, so no replacement experiment is required.

## Implementation and Tests

Implementation in [optimizer-solver](../../crates/optimizer-solver/src/lib.rs)
over the [solve contract](../../crates/optimizer-core/src/solve.rs) and
[evaluation](../../crates/optimizer-core/src/evaluate.rs), verified through the
[gate](../../tools/check.sh). No behavior is implemented by this decision record.
Acceptance evidence is recorded in [active task](../../state/active-task.md);
C2 is not complete until its full gate and exhaustive search tests pass.