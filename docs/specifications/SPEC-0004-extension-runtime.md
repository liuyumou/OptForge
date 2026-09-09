# SPEC-0004: Extension Runtime and Authority Model

Status: accepted
Scope: optimizer-extension runtime, authority model and executive integration
Owner: extension runtime
Introduced: C3
Last reviewed commit: a85da69
Supersedes: none
Implementation: [runtime](../../crates/optimizer-extension/src/lib.rs), [declarations](../../crates/optimizer-extension/src/declare.rs), [guarded host](../../crates/optimizer-extension/src/guard.rs), [records](../../crates/optimizer-extension/src/record.rs), [executive integration](../../crates/optimizer-solver/src/hooks.rs)
Tests: [runtime contracts](../../crates/optimizer-extension/tests/contracts.rs), [independent extensions](../../crates/optimizer-extension-examples/tests/acceptance.rs), [native end to end](../../crates/optimizer-highs/tests/executive.rs)

## Purpose

Let separately authored components propose candidates and search actions to the
[C2 executive](SPEC-0003-solver-executive.md) without acquiring any mathematical
authority. Extensions declare what they are and what they need; the core decides
what is true. A proposed candidate becomes an incumbent only after
original-model validation, and a proposed action takes effect only after the
executive has checked it against its own state.

An extension's output is a suggestion. This specification defines the claim an
extension can never make: that a search result is correct. Proof completion
stays exactly where SPEC-0003 put it, and no extension behavior, however
hostile, may change it.

Excluded: the local registry, CLI and SDK surface (C4); scheduling producers
(C5); GPU extensions (C6); portfolio allocation and learned selection (C7);
validity of cuts, presolve, bound tightening and reformulations (Stage 5), so
the transformation category is refused at declaration time rather than
implemented; dynamic loading of separately distributed native components;
process-isolated workers; memory limiting. Numerical backends are delivered by
[SPEC-0002](SPEC-0002-backend-contract.md) and are outside this runtime.

## Terminology

An extension is a component implementing one of this specification's traits. A
declaration is the versioned document by which an extension states its identity,
category, host contract version, determinism and limits. Registration is the
core's admission of an extension for one search, after checking its declaration.
The host is the guarded invocation boundary the core owns. A proposal is a
candidate offered by a candidate producer. Advice is a search action offered by a
search adviser. Rejection is the core refusing a proposal or advice while the
search continues. Disabling is the permanent exclusion of one extension from the
remainder of one search. An extension failure is a recorded rejection, disable or
refusal; it is never a search outcome. Authority means the consequences the core
permits an extension's output to have.

## Requirements

1. An extension MUST declare its identity, version, host contract version,
   category, supported problem classes, determinism and limits before it is
   invoked. A declaration that fails validation MUST be refused at registration
   and the extension MUST NOT be invoked.
2. Registration MUST refuse a declaration whose host contract version differs
   from the host's, in either direction, and MUST record the refused extension's
   identity and version. Version compatibility MUST NOT be inferred from a
   successful invocation.
3. Only the candidate-producer and search-adviser categories MUST be admitted.
   The transformation category MUST be refused at registration, so no
   transformation is applied by any code path in this specification.
4. An extension MUST receive read-only information. It MUST NOT be given a
   mutable reference to executive state, the node store, the incumbent, budgets,
   counters or the model, and MUST NOT be able to mutate them through any value
   this specification passes it.
5. A proposed candidate MUST pass
   [`Model::evaluate`](../../crates/optimizer-core/src/evaluate.rs) against the
   original model under the recorded tolerances, and MUST be reported feasible,
   before it is offered as an incumbent. Validation MUST use the original model,
   never a node.
6. A proposed candidate's objective MUST be the independently recomputed one. An
   objective, bound, status or proof claim asserted by an extension MUST NOT be
   read, recorded as a measurement, or used in any comparison.
7. An invalid, infeasible, unevaluable, wrong-model or incomplete proposal MUST
   be rejected and recorded. It MUST NOT become an incumbent, MUST NOT return an
   error from the search entry point, and MUST NOT forfeit the proof claim.
8. A proposal MUST replace the incumbent only under SPEC-0003 requirement 13:
   validated feasible, and better than the incumbent by more than the
   caller-supplied improvement tolerance.
9. Advice selecting a node MUST be honored only when that node is open at the
   moment the advice is evaluated. Advice naming a closed, already-selected or
   nonexistent node MUST be rejected.
9a. A search adviser MUST NOT be consulted for a decision that has only one
    possible answer: a frontier of at most one open node, or a node with no
    branchable variable. Such a consultation could only restate the default or
    name something absent, so it would manufacture rejections that describe the
    hook rather than the extension. This is also what makes requirement 20
    hold: a continuous model's frontier never exceeds one node, so no adviser
    is invoked for it.
10. Advice selecting a branching variable MUST be honored only when that
    variable is in the executive's own recomputed set of variables whose
    relaxation value exceeds `Tolerances.integrality` from a permitted domain
    value at this node. Advice naming a continuous variable, an integral
    variable or an unknown variable MUST be rejected. This is a termination
    requirement: branching on an integral value produces two children that do
    not tighten the node, so the search could regenerate an identical child
    indefinitely.
11. Rejected advice MUST fall back to the SPEC-0003 default decision, which MUST
    remain unmodified and reachable, and the rejection MUST be recorded.
12. Advice MUST NOT determine how a node is split. Given a branching variable,
    the two children MUST remain exactly the SPEC-0003 requirement 10 children,
    so branch coverage is preserved by construction.
13. No extension path MUST forfeit the proof claim, terminate the search loop or
    return an error from the search entry point. A search's outcome, forfeiture
    state and prune counters MUST be independent of extension behavior.
14. A panicking extension MUST be contained, MUST be disabled for the remainder
    of the search, and MUST be recorded. The search MUST continue and MUST
    report the outcome it would have reported without that extension. The host
    MUST require the unwind panic strategy and MUST NOT install a process-global
    panic hook.
15. Containment MUST be described as panic containment only. Process abort,
    stack exhaustion and memory faults are outside this boundary and MUST NOT be
    claimed as covered.
16. Every extension MUST have caller-supplied budgets with no defaults. A budget
    MUST be counted in invocations and proposals, never in wall-clock time, so
    the search path cannot depend on machine speed. An extension exceeding a
    budget MUST be disabled and recorded.
17. Recorded diagnostics MUST be bounded independently of the node count. A
    per-event string MUST NOT be accumulated, because an extension emitting one
    rejection per node would otherwise grow memory with the search.
18. Extensions MUST be invoked at fixed points in a deterministic order keyed by
    extension identity. With every registered extension declaring determinism,
    SPEC-0003 requirement 21 MUST continue to hold: two identical searches
    explore identically. When any registered extension declares itself
    nondeterministic, the record MUST state that replay equality is not claimed.
19. An extension MUST NOT supply a warm start, so SPEC-0003 requirement 23's
    prohibition on cross-node basis reuse is untouched.
20. A model with no discrete variable MUST NOT invoke a search adviser at all,
    preserving SPEC-0003 requirement 20's single-relaxation behavior exactly.
21. Search configuration MUST carry the caller's extension policy and search
    records MUST carry one summary entry per registered extension, so a record
    cannot conceal that extensions influenced the search it describes.
22. A search with an empty extension policy MUST produce the same record as the
    extension-free entry point, apart from measured elapsed time.
23. Extension documents MUST be versioned, MUST reject unknown fields,
    positional arrays and unknown enum variants, and MUST omit an unavailable or
    nonfinite measurement rather than serializing null in place of a number.
    Parsing a search record MUST validate the version of every extension
    summary and policy nested inside it, not only the record's own version.

## Interfaces

`ExtensionDeclaration` is a strict versioned object containing
`schema_version`, `extension_id`, `version`, `host_contract_version`,
`category`, `problem_classes`, `deterministic` and `limits`. Every field is
required. Data needs, hardware requirements and inter-extension dependencies are
deliberately absent: nothing in this specification reads them, and they belong to
the C4 registry.

`Category` has the variants `candidate_producer`, `search_adviser` and
`transformation`. Deserialization MUST reject an unknown variant. There is
deliberately no `backend` variant: replaceable numerical backends already exist
under SPEC-0002's public `Backend` trait, and duplicating them here would
suggest that contract had been narrowed.

`Authority` is the consequence the core permits, stated per category:
`propose_validated_candidate` for a candidate producer, and
`propose_checked_action` for a search adviser. It is recorded so a reader can see
the acceptance boundary that applied, and it is derived from the category rather
than chosen by the extension.

`SearchSnapshot` is the read-only value an extension receives: objective sense,
the recorded seed, tolerances, the incumbent objective when one exists, the
global dual bound when one exists, the explored-node count, and the open
frontier as `OpenNodeSummary` entries of node identity, inherited parent bound
and depth. The frontier summary deliberately excludes per-node restriction
lists: SPEC-0003's resource clause bounds memory by the open-node limit times the
per-node restrictions, and copying every restriction of every open node at every
iteration would exceed that bound.

`FractionalVariable` carries a variable identity, its relaxation value and its
distance from the nearest permitted domain value. The branching hook receives
the executive's own set of these, which is the same set the default decision
uses.

`Extension` exposes `declare`. `CandidateProducer` exposes `propose`, returning
zero or more candidates. `SearchAdviser` exposes `advise`, returning `Advice`.
`Advice` has the variants `abstain`, `select_node` with a node identity, and
`branch_variable` with a variable identity. All three traits are object-safe, so
the executive holds registered extensions the way it already holds `&dyn Backend`.

`ExtensionPolicy` is a strict versioned object naming one permitted extension
and its invocation and proposal budgets. Search configuration carries a list of
them; an empty list means no extension participates. `ExtensionSummary` records
one registered extension's identity, version, category, authority, declared
determinism, invocation and proposal counts, acceptance count, rejection count,
whether it was disabled and why, and a bounded set of distinct failure entries.
`ExtensionFailure` pairs a `FailureKind` with a bounded message. `FailureKind`
has the variants `declaration_invalid`, `incompatible_contract`,
`unsupported_category`, `invalid_candidate`, `invalid_advice`,
`budget_exhausted` and `panicked`, each matched exhaustively so a later variant
fails to compile rather than falling into a catch-all.

Structured artifacts in this specification are the typed Rust records and their
JSON serialization. No JSON Schema file is introduced: search records have none
today, and the enclosing experiment artifact format is C4's work.

## State and Invariants

M1 model, tolerance and candidate semantics are unchanged. C1 solve semantics are
unchanged; this specification adds no requirement to the backend contract. Every
SPEC-0003 invariant continues to hold, and this specification adds no way to
weaken one.

The executive owns all state. An extension observes a snapshot and returns an
owned value; no reference into executive state outlives an invocation. Because
only owned values cross the boundary, a panic inside an extension cannot leave
executive state partially mutated.

Disabling is monotone: once an extension is disabled for a search it is never
re-enabled. This is required for soundness, not merely as policy, because an
extension that panicked may have left its own state unusable, so a further
invocation could panic again indefinitely.

An accepted proposal can only tighten the incumbent, and pruning against a
validated incumbent can only close nodes that cannot beat it by more than the
improvement tolerance. Honored node advice changes exploration order only; the
node tree is the same tree, so an exhausted tree is still an exhausted tree.
Honored branching advice changes which variable is split, and requirement 10
guarantees the split still strictly tightens both children.

An adversarial adviser can change which outcome a *budgeted* search reaches, by
spending the node budget on unpromising nodes. That is exploration quality, not
correctness, and it is why this specification's equivalence claims are stated
over unlimited budgets.

## Errors and Recovery

Categories reuse `ErrorKind`: document, structural, candidate, tolerance,
numerical, unsupported, backend. An invalid extension policy or declaration
supplied by the caller is an error from the search entry point, because it is
malformed configuration. Everything an extension itself does wrong is a recorded
failure rather than an error: a rejected proposal, rejected advice, an exhausted
budget and a panic all leave the search running and the record honest.

A refused registration invokes nothing. A disabled extension is invoked no
further. A failed search publishes no successful record. Native resources belong
to the backend; the runtime holds none.

## Compatibility and Versioning

`ExtensionDeclaration`, `ExtensionPolicy`, `ExtensionSummary` and
`ExtensionFailure` are new documents at their own `schema_version` 1, and that
constant is also the host contract version, so later extension-shape work moves
one number rather than two.

`SEARCH_SCHEMA_VERSION` moves from 1 to 2. `SearchOptions` gains a required
extension policy list and `SearchRecord` gains a required extension summary
list; requirement 21 cannot be met otherwise, because search configuration is a
strict all-fields-required document with no additive escape hatch, and a version-1
record of an extension-influenced search would claim to be sufficient to repeat a
search it does not describe. `Checkpoint` moves to version 2 with a
byte-identical shape because it shares that constant. Version-1 search documents
are rejected, not migrated, matching existing behavior. M1 and C1 documents stay
at version 1. The Rust API stays at workspace version 0.1.0. No Python SDK, CUDA
dependency, registry or dynamically loaded native extension is introduced.

## Security and Resource Limits

Linux x86-64, CPU only, single-threaded. Invocation is synchronous with explicit
counted budgets and the existing cooperative cancellation. Extensions run
in-process and are trusted with the availability of the process but with no
mathematical authority: containment covers panics, not aborts or memory faults.
Memory stays bounded by SPEC-0003's open-node limit clause plus one reused
frontier-summary buffer and the bounded per-extension diagnostics. Extension
execution time is included in the search's measured elapsed time and can
therefore consume the caller's wall-clock budget. Every size and index
conversion MUST be checked. No stdin, network or GPU access. Unsafe code remains
prohibited outside optimizer-highs.

## Examples

No example is executable at acceptance time: this specification precedes its
implementation and no extension API is public yet. Executable commands and
expected output are added with the implementation, as C1 did for solving.

## Acceptance Tests

Requirements 1-4: a declaration round trip and validation failures; refusal of a
newer and an older host contract version, each recording identity and version;
refusal of the transformation category with no invocation; and the absence of any
mutable path, established by the snapshot types themselves. Requirements 5-8: an
adversarial producer returning infeasible, out-of-bounds, wrong-model,
incomplete, duplicated and nonfinite candidates, and one reporting a false
objective, each rejected in its own `ErrorKind` category, never an incumbent,
never an error from the entry point, with the recorded objective always the
recomputed one. Requirements 9-12: advice naming a closed, nonexistent,
continuous, integral or unknown target, each rejected with a fallback to the
default decision; no consultation for a single-node frontier or a node with no
branchable variable; an adviser that always names the same integral variable
terminating rather than looping; and the two children of an advised branch
checked against the default's children. Requirement 13: every adversarial
extension above re-run over the fixed exhaustive tiny-model grid, asserting the
identical proven optimum, the identical outcome, no forfeiture and unchanged
prune counters against the extension-free run, under unlimited budgets.
Requirements 14-15: a panicking producer and a panicking adviser contained,
disabled and recorded, with the search still reporting its C2 outcome.
Requirement 16: an exceeded invocation budget and an exceeded proposal budget,
each disabling and recording, with the outcome unaffected. Requirement 17:
diagnostics bounded under an extension rejecting once per node. Requirements
18-20: replay equality of two identical searches with deterministic extensions,
a nondeterministic declaration reflected in the record, an unchanged warm-start
argument, and no adviser invocation for a continuous model with the
single-relaxation counters intact. Requirements 21-23: version-2 round trips,
rejection of version 1, unknown fields, positional arrays and unknown variants,
absent-not-null serialization, rejection of a record whose nested extension
summary or policy carries a wrong version, and an empty-policy search producing
a record identical to the extension-free entry point apart from elapsed time.

Independently authored extensions live in their own crate depending only on the
published extension and core APIs, with the executive as a test-only dependency,
so "runs without engine-internal changes" is established by the workspace build
rather than asserted. One end-to-end search with a registered extension runs
over the pinned native library and reports an explicit skip when it is absent, as
C1 does. The complete `bash tools/check.sh` gate is required before C3
completion.

## Open Questions

The versioned C-compatible boundary for separately distributed native components
is deliberately absent. It requires a second unsafe boundary, which ADR-0003
currently prohibits outside optimizer-highs, so it needs its own decision record
and its own lifecycle, ABI-stability and crash-isolation evidence. Process
isolation for experimental generated code is deferred with it; process isolation
protects execution and establishes nothing about mathematical validity.
Transformation validity, including cut soundness and solution-space
preservation, requires its own specification before that category is admitted.
Whether search advisers improve search is a hypothesis: C3 establishes safety and
makes no performance claim.