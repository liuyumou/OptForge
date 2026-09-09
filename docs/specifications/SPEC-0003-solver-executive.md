# SPEC-0003: Owned Solver Executive

Status: accepted
Scope: optimizer-solver owned branch-and-bound executive
Owner: search executive
Introduced: C2
Last reviewed commit: c742064
Supersedes: none
Implementation: [executive](../../crates/optimizer-solver/src/executive.rs), [contracts](../../crates/optimizer-solver/src/search.rs), [nodes](../../crates/optimizer-solver/src/node.rs)
Tests: [search contracts](../../crates/optimizer-solver/tests/executive.rs), [native end to end](../../crates/optimizer-highs/tests/executive.rs)

## Purpose

Own the search process that proves optimality of an original M1 model, using the
[C1 backend contract](SPEC-0002-backend-contract.md) only as a relaxation service.
The executive owns session state, the node store, budgets, cancellation, telemetry,
incumbent acceptance and proof completion.

A backend termination describes one relaxation solve. This specification defines a
separate, stronger claim: that the executive itself exhausted its own node tree.
Neither claim implies the other, and neither is an exact-arithmetic certificate.

Excluded: extensions and the authority model (C3); presolve, scaling,
reoptimization, cut generation and numerical recovery (Stage 5); parallel search;
decomposition; portfolios; any performance claim. Node and work-item interfaces
MUST remain usable by those later capabilities, but none is introduced here.

## Terminology

A node is a subproblem of the original model restricted by branching bounds. A
node relaxation is the continuous problem obtained from a node by dropping
integrality. A node bound is a relaxation objective admitted as a dual bound. A
valid bound is one whose relaxation solved to proven optimality. An incumbent is
a candidate that passed original-model validation. The global dual bound is the
best valid bound over open nodes. Forfeiture is the permanent loss of the
executive's proof claim for one search. Better means smaller for a minimize sense
and larger for a maximize sense.

## Requirements

1. The executive MUST own all search state privately; callers MUST NOT mutate the
   node store, incumbent, budgets or counters during a search.
2. A node MUST be represented as the original model plus tightened variable
   bounds on discrete variables only. Branching MUST NOT alter constraints,
   coefficients, the objective, the objective sense, variable identities or
   constraint identities.
3. A node relaxation MUST preserve the original model ID and all original
   variable and constraint IDs, so an extracted candidate evaluates directly
   against the original model without renumbering or re-stamping.
4. Relaxations MUST be dispatched through the backend-neutral
   [`Backend`](../../crates/optimizer-core/src/solve.rs) trait. optimizer-solver
   MUST NOT depend on optimizer-highs or on any backend-specific behavior.
5. A relaxation objective MUST be admitted as a node bound only when that
   relaxation reported `Termination::Optimal`. Any other termination MUST leave
   the node bound unavailable.
6. A node with an unavailable bound MUST NOT be pruned by bound, and MUST cause
   forfeiture. A forfeited search MUST NOT report proven optimality or proven
   infeasibility, whatever else it reports.
7. A node MUST be pruned as infeasible only when its relaxation reported
   `Termination::Infeasible`. A relaxation limit, interruption or failure MUST
   NOT be treated as node infeasibility.
8. A node MUST be pruned by bound only when a valid node bound is not better
   than the incumbent objective by more than the caller-supplied improvement
   tolerance. Pruning MUST NOT use an incumbent that has not been validated.
9. A relaxation solution whose discrete variables all lie within
   `Tolerances.integrality` of a permitted domain value MUST be offered as a
   candidate. Otherwise the executive MUST branch on a discrete variable whose
   value exceeds that tolerance. The same tolerance governs both decisions.
10. Branching on a variable with relaxation value `v` MUST create exactly the two
    children bounded by `x <= floor(v)` and `x >= ceil(v)`, so the two children
    cover the node's entire discrete feasible set and lose no solution. A child
    whose bounds do not intersect MUST be discarded as infeasible without a
    relaxation solve.
11. Branching bounds MUST remain finite and within the SPEC-0001 discrete
    magnitude limit of 2^53; a branch that cannot be represented MUST fail
    explicitly as unsupported rather than being silently widened or clamped.
12. Every candidate MUST pass
    [`Model::evaluate`](../../crates/optimizer-core/src/evaluate.rs) against the
    original model, not against a node, under the recorded tolerances before it
    becomes an incumbent. An infeasible or unevaluable relaxation solution MUST
    return a numerical failure and MUST NOT become an incumbent.
12a. A relaxation solution MUST also be checked against the node it was solved
    for before it is branched on. A solution outside that node's own bounds is
    inconsistent backend output and MUST forfeit rather than be branched on:
    branching on it would not tighten the domain, so the search could
    regenerate an identical child indefinitely. This check is what makes
    termination independent of backend correctness.
13. A candidate MUST replace the incumbent only when it is validated feasible and
    its recomputed objective is better than the incumbent's by more than the
    improvement tolerance.
14. The executive MUST report its outcome through its own type, distinct from
    `Termination`. Proven optimality MUST require an exhausted node tree, every
    prune justified by requirement 7 or 8, no forfeiture, and a validated
    incumbent.
15. A node limit, time limit, open-node limit, interruption, numerical failure or
    backend failure MUST NOT report proof completion.
16. A relaxation reporting `Unbounded` or `UnboundedOrInfeasible` MUST be reported
    as unbounded-or-infeasible for the search. The executive MUST NOT claim
    unboundedness of a discrete model from a relaxation alone, and MUST NOT
    present it as a feasible incumbent.
17. Budgets MUST be caller-supplied with no defaults: a node limit, a wall-clock
    limit, an open-node limit, and the explicit `SolveOptions` used for every
    node relaxation. A present limit MUST be positive.
18. The open-node limit MUST bound the frontier, so an unbounded discrete
    variable cannot grow the node store without limit.
19. Cancellation MUST be cooperative through the shared
    [`CancellationToken`](../../crates/optimizer-core/src/solve.rs), MUST be
    checked between nodes, and MUST be propagated into every relaxation. A
    pre-cancelled search MUST return interrupted without dispatching any
    relaxation.
20. A model with no discrete variable MUST perform no branching: it solves one
    relaxation and reports that outcome under this specification's own type.
21. Search MUST be deterministic and replayable from its record: the same model,
    options and backend MUST explore the same nodes in the same order. Node
    selection and branching-variable choice MUST be total orders keyed by the
    recorded seed and original IDs, never by iteration order of an unordered
    collection.
22. Records MUST be versioned, MUST retain node counters and configuration
    sufficient to repeat the search, and MUST omit an unavailable or nonfinite
    measurement rather than serializing null in place of a number.
23. Node relaxations MUST NOT reuse an LP basis across nodes whose bounds differ,
    because a basis is bound to an exact canonical model fingerprint. Warm-start
    reuse between nodes is deferred to Stage 5 reoptimization.

## Interfaces

`SearchOptions` is a strict versioned object containing `schema_version`, `seed`,
`node_limit`, `time_limit_ms`, `open_node_limit`, `improvement_tolerance`, and the
`relaxation` `SolveOptions` applied to every node. Every field is required; absent
limits are explicit nulls meaning unlimited, matching the C1 configuration style.
There are deliberately no default budgets, seeds or tolerances.

`SearchOutcome` is the executive's own outcome type with these variants:
`proven_optimal`, `proven_infeasible`, `unbounded_or_infeasible`, `feasible`,
`node_limit`, `time_limit`, `open_node_limit`, `interrupted`,
`numerical_failure`, `backend_failure`, `unsupported`. It exposes
`proves_completion`, true only for `proven_optimal`, `proven_infeasible` and
`unbounded_or_infeasible`. Deserialization MUST reject an unknown variant.

`SearchRecord` contains `schema_version`, `model_id`, `backend`,
`backend_version`, `outcome`, optional `objective`, optional `dual_bound`,
optional `gap`, optional `candidate`, optional `validation`, `nodes_explored`,
`nodes_pruned_infeasible`, `nodes_pruned_bound`, `open_nodes_remaining`,
`relaxations_solved`, `forfeited`, `warnings`, `elapsed_ms` and `options`.
`forfeited` is recorded explicitly so a reader can see why a completed-looking
search made no proof claim. `objective` is the independently recomputed original
objective of the incumbent, never a backend-reported value.

The executive accepts an immutable `Model`, explicit `SearchOptions`, a `&dyn Backend`
relaxation service and a shared `CancellationToken`, and returns
`Result<SearchRecord, ValidationError>` using the existing `ErrorKind` taxonomy.

`Checkpoint` is a versioned shape containing the schema version, model ID, model
fingerprint, the serialized open-node frontier, the incumbent, the global dual
bound and the counters. C2 defines and serializes this shape; **restart from a
checkpoint is not implemented in C2** and requires its own acceptance evidence
before any public restart entry point exists.

## State and Invariants

M1 model, tolerance and candidate semantics are unchanged. C1 solve semantics are
unchanged; this specification adds no requirement to the backend contract.

The global dual bound is monotone: it never improves in the better direction as
the search proceeds. The incumbent objective is monotone in the better direction.
Both are invariants an implementation MUST be able to assert. Once `forfeited` is
set it MUST NOT be cleared for that search.

Node identity is assigned in deterministic creation order. The node store is an
ordered structure; equal-priority nodes break ties by node identity so selection
is total. Objective comparisons use the caller's improvement tolerance and are
performed in the original objective's units. A discrete relaxation value within
the integrality tolerance of a domain value is treated as integral for
acceptance and is not branched on, so the two decisions cannot disagree.

Proven optimality means the executive exhausted its node tree under recorded
numerical settings, with each pruned node justified by a proven relaxation. It
MUST NOT be described as an exact certificate. An empty node tree with no
validated incumbent is proven infeasibility only when every closure was a proven
infeasibility.

## Errors and Recovery

Categories reuse `ErrorKind`: document, structural, candidate, tolerance,
numerical, unsupported, backend. Unsupported input, malformed configuration and
unrepresentable branches are errors, not outcomes. A relaxation `BackendFailure`
or `NumericalFailure` forfeits the proof and terminates the search with the
corresponding outcome; the executive MUST NOT retry silently or continue as if the
node were closed. A failed search publishes no successful record. Native
resources belong to the backend; the executive holds none.

## Compatibility and Versioning

`SearchOptions`, `SearchRecord` and `Checkpoint` are new documents at
`schema_version` 1. M1 and C1 documents stay at version 1 and are not migrated.
Bootstrap and solve schemas are unchanged. The Rust API stays at workspace version
0.1.0. No Python SDK, CUDA dependency or extension API is introduced.

## Security and Resource Limits

Linux x86-64, CPU only, single-threaded. Search is synchronous with explicit
budgets and cooperative cancellation. Memory is bounded by the open-node limit
times the per-node bound restrictions; the executive MUST NOT retain a full model
copy per node. Every size and index conversion MUST be checked. No stdin, network
or GPU access.

## Examples

No example is executable at acceptance time: this specification precedes its
implementation, and `optimizer-solver` exposes no public API yet. Executable
commands and expected output are added with the implementation, alongside a
tutorial, as C1 did for solving.

## Acceptance Tests

Requirements 1-4: node construction preserves original IDs, bounds-only
restriction, and a backend-neutral dispatch test using an in-crate stub backend
rather than optimizer-highs. Requirements 5-8: a stub backend returning each
`Termination` in turn asserts that only `Optimal` yields a bound, that only
`Infeasible` prunes, and that a time-limited or interrupted relaxation neither
prunes nor leaves a proof claim intact. Requirements 9-11: fractional branching
partitions, empty-child discard, and the 2^53 boundary. Requirements 12-13:
original-model validation of every incumbent, rejection of an infeasible
relaxation solution, and termination under a backend whose solutions ignore the
node bounds it was given. Requirements 14-16: exhaustive tiny discrete models compared
against independent brute-force enumeration over the full assignment space,
covering feasible, infeasible, unbounded and proof states. Requirements 17-19:
each budget triggers its own outcome, and a pre-cancelled search dispatches no
relaxation. Requirements 20-23: continuous-only pass-through, replay equality of
two identical searches, absent-not-null serialization, and rejection of basis
reuse across differing nodes.

Native relaxations require the pinned library, so those tests report an explicit
skip when it is absent, as C1 does. The complete `bash tools/check.sh` gate is
required before C2 completion.

## Open Questions

Checkpoint restart is specified in shape only and deliberately unimplemented.
Best-bound versus depth-first node selection is an implementation choice inside
requirement 21's determinism constraint and is not fixed here. Dual certificates,
cut validity, presolve reconstruction and parallel node processing require their
own specifications. The claim that owned search improves on delegating MILP search
to the backend is a hypothesis; C2 establishes correctness only and makes no
performance claim.