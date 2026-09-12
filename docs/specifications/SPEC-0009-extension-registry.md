# SPEC-0009: Local Extension Registry and Conformance

Status: accepted
Scope: optimizer-registry resolution and conformance, and the optimizer-cli registry surface
Owner: extension runtime
Introduced: C8
Last reviewed commit: 6cf6d5e
Supersedes: none
Implementation: [registry document](../../crates/optimizer-registry/src/document.rs), [resolution](../../crates/optimizer-registry/src/resolve.rs), [conformance](../../crates/optimizer-registry/src/conformance.rs), [provider table and subcommands](../../crates/optimizer-cli/src/registry.rs), [search and verify integration](../../crates/optimizer-cli/src/search.rs), [validator](../../tools/validate_artifacts.py)
Tests: [registry contracts](../../crates/optimizer-registry/tests/contracts.rs), [conformance suite and CLI contracts](../../crates/optimizer-cli/tests/registry.rs), [scheduling CLI contracts](../../crates/optimizer-cli/tests/schedule.rs), [run surface contracts](../../crates/optimizer-cli/tests/search.rs), [schema contracts](../../tests/integration/test_registry.py)

## Purpose

Let a caller name an extension in a search configuration and have that search
actually run it, and let the resulting record be re-executed and verified. The
[C3 extension runtime](SPEC-0004-extension-runtime.md) established what an
extension may propose and what the core refuses, but
`optimizer_solver::search_with_extensions` takes an in-memory `&[Registration]`
slice for one search and the [C4 run surface](SPEC-0005-run-surface.md) has no
mechanism to populate it. So the run surface refuses any configuration whose
extension policy is non-empty, and a
[C5 scheduling run](SPEC-0008-flow-shop.md) performed with the NEH producer is
not verifiable by re-execution at all. This specification is the seam both of
those refusals point at.

A registry is a document that maps a declared extension identity to an extension
this build provides, together with the facts a caller needs in order to decide
whether to permit it: version, license, category, the authority that category
implies, host contract compatibility, declared determinism, counted limits, data
and hardware needs, inter-extension requirements and conflicts, and whether the
extension has passed a recorded conformance run.

The registry resolves; it does not load. A registry entry names an extension the
binary already provides, and an entry naming an identity this build does not
provide is refused rather than skipped. Dynamic loading of separately
distributed native components requires a second unsafe boundary that
[ADR-0003](../decisions/ADR-0003-highs-backend.md) prohibits outside
optimizer-highs, and it stays deferred with its own recorded blocker. This
boundary is what makes the rest of the registry implementable in safe Rust now.

Nothing here grants an extension any mathematical authority. Resolution decides
which extensions a search may consult; SPEC-0004 continues to decide what their
output is worth, which is nothing until the core validates it. Promotion in this
specification means an extension passed the recorded contract conformance suite.
It never means the extension improves a search, which is a
[C7](../../implementation-plan.md) question and is not measured here.

Excluded: the Python SDK and any foreign-function boundary, whose blocker is
recorded separately; comparative experiment execution over a benchmark manifest,
which remains [SPEC-0007](SPEC-0007-artifacts.md)'s artifact contract without a
runner; dynamically loaded native extensions and process-isolated extension
workers, both deferred by SPEC-0004; any default, discovered or implicit registry
location; remote or network registries and any form of publication or
distribution; transformation-category extensions, still refused at declaration
time by SPEC-0004 requirement 3; GPU device selection and residency (C6);
learned or adaptive selection among registered extensions (C7); checkpoint
restart and progress streaming. No performance claim is made or measured, and
requirement 27 forbids recording one.

## Terminology

A registry document is the versioned file listing entries. An entry is one
extension's recorded metadata: what it is claimed to be. A declaration is what
the extension itself reports through SPEC-0004's `Extension::declare`, and it is
authoritative; an entry is a claim about a declaration. A provider is the
component that constructs an extension from an identity, owned by the caller
rather than by this specification. Resolution is checking a set of entries
against a configuration's extension policy and the providers available, and
producing the registrations a search will use. A resolved set is the outcome of
successful resolution. Refusal is resolution declining to produce a resolved set,
which is an error before a search starts, never a silent omission. Conformance is
the fixed contract suite this specification defines over one extension, and a
conformance record is that suite's versioned result document. Promotion is an
entry's recorded claim that a conformance record exists and passed; an
experimental entry makes no such claim. A data requirement is auxiliary input an
extension needs beyond the model, and a hardware requirement is the device class
it needs.

## Requirements

1. A registry document MUST carry its schema version, a registry identifier and
   its entries, and MUST be refused at parse time when any is missing.
2. A registry entry MUST carry its schema version, the extension identity, the
   extension version, a license identifier, the category, the authority basis,
   the host contract version, the supported problem classes, the declared
   determinism, the counted limits, the data requirement, the hardware
   requirement, the required and conflicting extension identities, and the
   promotion state. A document whose entry is missing any of these MUST be
   refused at parse time.
3. Parsing a registry document MUST reject unknown fields, duplicate fields,
   positional arrays in place of objects and unknown enum variants, matching
   SPEC-0001's strict document rules, and MUST validate the version of every
   entry nested inside it rather than only the document's own, matching SPEC-0004
   requirement 23.
4. A registry document MUST be refused when two entries name the same extension
   identity, because the entry governing a resolution would otherwise be
   ambiguous, matching the rule SPEC-0004 already applies to a policy list.
5. Resolution MUST refuse an entry naming an extension this build does not
   provide. Resolving the remainder and silently omitting it is forbidden: the
   caller named it, and a search that ran without it would produce a record
   describing a search the caller did not request.
6. Resolution MUST treat the extension's own declaration as authoritative and
   MUST refuse an entry whose recorded version, category, host contract version,
   problem classes, declared determinism or counted limits disagree with that
   declaration. A disagreement MUST NOT be resolved in favor of either the entry
   or the declaration.
7. Resolution MUST refuse an entry whose authority basis is not the authority
   SPEC-0004 derives from that entry's category. Authority MUST remain derived
   from the category and MUST NOT become selectable by an entry.
8. Resolution MUST refuse an entry whose data requirement is not satisfied by
   the auxiliary input the caller supplied, and MUST NOT substitute a default,
   an empty value or an unrelated instance.
9. Resolution MUST refuse an entry requiring a hardware class this build
   performs no work on. No device is selected, acquired or leased by this
   specification.
10. Resolution MUST refuse a resolved set in which a required extension identity
    is absent, or in which two entries declare a conflict with one another, and
    MUST name the unsatisfied requirement or the conflicting pair.
11. Resolution MUST refuse a promoted entry whose conformance record is absent,
    whose bytes do not match the recorded checksum, whose recorded outcome is
    not a pass, or which names a different extension identity or version.
    Promotion MUST NOT be assertable by prose in an entry alone.
12. Resolution MUST refuse an experimental entry unless the caller explicitly
    permitted experimental extensions. When such an entry is registered, the run
    record MUST carry a warning naming it, so a record cannot conceal that an
    unpromoted extension participated in the search it describes.
13. Resolution MUST be refused as a whole rather than partially applied. A
    search MUST NOT begin with a subset of the extensions its configuration
    named.
14. Resolution MUST NOT consult, invoke, construct or otherwise execute an
    extension it refuses. A refused entry MUST leave the extension's own
    invocation count at zero.
15. Registration order and invocation order MUST remain SPEC-0004 requirement
    18's order keyed by extension identity, and MUST NOT depend on the order
    entries appear in a registry document.
16. Resolution MUST NOT alter the meaning of a search. It selects which
    extensions the SPEC-0004 host may consult and adds no authority; every
    proposal remains validated against the original model and every action
    remains checked against executive state.
17. A search whose configuration names no extension MUST produce the record the
    extension-free entry point produces even when a registry is supplied,
    preserving SPEC-0004 requirement 22 exactly.
18. `optimizer search` and `optimizer schedule solve` MUST resolve a non-empty
    extension policy through a registry the caller named explicitly, and MUST
    refuse such a configuration when no registry was named. There MUST be no
    default, discovered or implicit registry location.
19. `optimizer verify` MUST re-execute a record naming extensions by resolving
    them through a registry the caller named, and MUST use only the
    configuration embedded in the record, never its recorded results, preserving
    SPEC-0005 requirement 9.
20. `optimizer verify` MUST refuse, as unsupported rather than as divergence, a
    record whose named extension resolves to a different extension version than
    the record's summary states, and a record any of whose extension summaries
    declares nondeterminism. SPEC-0004 requirement 18 withholds replay equality
    for a nondeterministic search, so a comparison could not be meaningful, and
    reporting either case as divergence would blame the record for a property of
    the verifier's inputs.
21. Verification MUST compare exactly the fields SPEC-0005 requirement 11 names.
    An extension summary difference MUST NOT be added to agreement, MUST NOT
    change an exit code, and MUST be reported as a diagnostic note only, matching
    the existing environment-difference rule.
22. Verification MUST NOT strengthen a claim. Agreement with extensions
    registered MUST NOT be reported as proven optimality, and a forfeited record
    MUST remain forfeited, preserving SPEC-0005 requirement 13.
23. The conformance suite MUST establish, over a fixed model grid with no
    randomness and unlimited budgets, that an extension leaves the search
    outcome, the proven optimum, the dual bound, the forfeiture state and both
    prune counters identical to a run with no extension registered, matching
    SPEC-0004 requirement 13.
24. The conformance suite MUST assert that the extension was actually invoked
    before asserting anything about its effect, so a conformance record cannot
    pass because the extension was never consulted.
25. A conformance record MUST carry its schema version, the extension identity
    and version, the host contract version, the grid size, the relaxation
    backend's own reported version, each check's result and the overall outcome.
    A failing check MUST produce a recorded failure rather than an absent one.
26. A registry document and a conformance record MUST each have a JSON Schema,
    and that schema and the Rust parser MUST accept the same documents. Neither
    MUST be laxer than the other, matching SPEC-0005 requirement 20.
27. This specification MUST NOT record a performance, runtime or
    solution-quality claim, and promotion MUST NOT be described as evidence that
    an extension improves a search.

## Interfaces

```
optimizer registry list  --registry <path>
optimizer registry check --registry <path> --extension <id> [--instance <path>] [--output <path>]
optimizer search   --model <path> --config <path> [--registry <path>] [--allow-experimental] [--output <path>]
optimizer verify   --record <path> --model <path> [--registry <path>] [--allow-experimental]
optimizer schedule solve --instance <path> --config <path> [--registry <path>] [--allow-experimental] [--output <path>] [--output-model <path>]
```

`--registry` is explicit and has no default. `--allow-experimental` permits
registering an experimental entry and is likewise absent by default, so the
permissive case is always visible in the command that produced a record.

`RegistryDocument` is a strict versioned object carrying `schema_version`,
`registry_id` and `entries`. `REGISTRY_SCHEMA_VERSION` is 1.

`RegistryEntry` is a strict versioned object carrying `schema_version`,
`extension_id`, `version`, `license`, `category`, `authority_basis`,
`host_contract_version`, `problem_classes`, `deterministic`, `limits`,
`data_requirement`, `hardware_requirement`, `requires`, `conflicts_with` and
`promotion`. Every field is required. `category`, `authority_basis`,
`problem_classes` and `limits` are SPEC-0004's own `Category`, `Authority`,
`ProblemClass` and `DeclaredLimits` rather than new types, so an entry cannot
describe a category or an authority the runtime does not have.

`DataRequirement` has the variants `none` and `flow_shop_instance`. It gives
SPEC-0004's deliberately parked "data needs" field a checked meaning: an entry
declaring `flow_shop_instance` is refused unless the caller supplied an instance.

`HardwareRequirement` has the variants `cpu` and `gpu`. `gpu` is refused at
resolution, because no device selection exists before C6 and an entry must not be
able to claim a capability nothing provides.

`Promotion` is `experimental`, or `promoted` with a `conformance_path` and a
`conformance_sha256`. A promoted entry's claim is checkable, which is the whole
of requirement 11.

`Provider` is the caller-owned seam that turns an identity into an extension:
given an identity and a `ProviderContext`, it returns the constructed extension
or nothing. `ProviderContext` carries the original model and the optional
auxiliary instance. This mirrors how SPEC-0002 keeps backends replaceable behind
`&dyn Backend` and how SPEC-0004 keeps extensions caller-supplied behind
`&[Registration]`; the registry crate therefore contains no list of first-party
extensions, and the command surface owns the concrete table.

`ResolvedSet` owns the constructed extensions for one search and lends
SPEC-0004 `Registration` values, which is exactly what
`search_with_extensions` already accepts. No new search entry point is
introduced and no existing signature changes.

`ConformanceRecord` is a strict versioned object carrying `schema_version`,
`extension_id`, `version`, `host_contract_version`, `grid_size`,
`backend_version`, `checks` and `outcome`. `CONFORMANCE_SCHEMA_VERSION` is 1.
Each check carries a stable name, a pass flag and a bounded detail string.

The schemas are
[extension-registry-v1](../../schemas/extension-registry-v1.schema.json) and
[conformance-record-v1](../../schemas/conformance-record-v1.schema.json), listed in
[the schema index](../../schemas/README.md).

## State and Invariants

M1 model, tolerance and candidate semantics are unchanged. C1 solve semantics,
C2 search semantics, C3 extension semantics and C5 scheduling semantics are all
unchanged; this specification adds no requirement to any of them and no
mathematical authority of any kind. It decides which extensions a search may
consult and records why.

No document version changes. `RUN_SCHEMA_VERSION` stays 1,
`SEARCH_SCHEMA_VERSION` stays 2, and `EXTENSION_SCHEMA_VERSION` stays 1, which is
also the host contract version. An extension is identified in a record by the
`extension_id` and `version` its summary already embeds verbatim, so a record
naming an extension needs no new field to be re-resolvable. Adding the registry
to the compared fields would change what agreement means, which SPEC-0005's
compatibility section reserves for a new record version and an ADR, and
requirement 21 therefore keeps the comparison exactly as it was.

Resolution is total and ordered. It either produces a resolved set for every
named entry or refuses, so a search never begins with a subset of what it was
configured with. The resolved set is ordered by extension identity before it
reaches the host, and the host sorts by identity again, so the registry document's
line order is not observable in a record.

The declaration is authoritative and the entry is a claim. This asymmetry is the
registry's analogue of SPEC-0004 requirement 2's exact contract-version match: a
mismatch is refused in both directions rather than reconciled, because reconciling
it would mean trusting one untrusted statement over another.

Determinism is inherited. Resolution introduces no randomness, no iteration over
a hash map, no wall-clock dependence and no filesystem-order dependence; entries
are matched by identity and ordered by identity. A search's replay guarantee
therefore continues to rest exactly where SPEC-0004 requirement 18 put it, on
every registered extension declaring determinism, which is why requirement 20
refuses to verify a record that declares otherwise.

Conformance evidence is about contracts, not quality. The suite's grid is fixed
and owned by the registry crate, its budgets are unlimited so an adviser cannot
change an outcome by spending a budget badly, and the property it establishes is
invariance rather than improvement.

## Errors and Recovery

Categories reuse `ErrorKind`: a malformed or wrongly versioned registry document
or conformance record is a document failure; a duplicated identity, an
unsatisfied requirement and a declared conflict are structural failures; an
unprovided extension, a gpu hardware requirement, an unsatisfied data
requirement, an experimental entry without permission, a declaration mismatch, a
version mismatch at verification and a nondeterministic record are unsupported
failures. Stderr categories reuse the established `argument:`, `io:`,
`document:` and `unsupported:` prefixes.

Every resolution failure occurs before a search starts, so none writes a run
record, matching SPEC-0005 requirement 8: a run that could not start is an error
rather than a run. A conformance failure is the opposite: `registry check` writes
its record and exits nonzero, because a failed conformance run is a result about
an extension rather than an error about a command.

Cancellation is the executive's under SPEC-0003 and is not re-specified.
Resolution holds no native resource, creates no device context and performs no
network access, so it has nothing to unwind.

A registry naming an extension whose provider panics during construction is
outside this specification's containment claim in the same way SPEC-0004
requirement 15 excludes a process abort: SPEC-0004's host contains panics inside
`declare`, `propose` and `advise`, and construction happens before the host
exists.

## Compatibility and Versioning

The registry document and the conformance record are new documents at
`schema_version` 1. Neither is embedded in an existing record, so no existing
schema version changes and no existing document gains or loses a field. The
committed C4 example run record therefore continues to verify unchanged.

A breaking change to either document requires a new versioned schema file, a new
Rust version constant and migration notes. Version mismatches are rejected
rather than migrated, matching SPEC-0004's treatment of version-1 search
documents.

The command surface adds two subcommands and two optional flags, which is
compatible. Changing an exit code's meaning, a stderr category, a field's role in
agreement, or the set of extensions a given registry resolves to is breaking.

Adding a provider is compatible. Changing which extension an identity resolves
to, or changing a resolved extension's behavior for the same inputs, is breaking:
a record naming that identity would re-execute against something else, and
requirement 20's version check is what turns that into a refusal rather than a
silent divergence.

Making an entry's authority basis, category derivation or promotion checking
laxer is breaking, because a record produced under the stricter rule was accepted
on a claim the laxer rule no longer verifies.

## Security and Resource Limits

A registry document is a trusted local project document read under the existing
16 MiB input bound, and this surface is not a service for untrusted input. No
path outside the caller-named ones is read or written, no directory is scanned,
and there is deliberately no search path, so a registry cannot be introduced into
a run by placing a file somewhere.

Extensions remain in-process and trusted with the availability of the process but
with no mathematical authority, exactly as SPEC-0004 states; containment covers
panics and not aborts or memory faults, and no per-extension memory budget
exists. Registering an extension through a registry changes nothing about that
boundary, and this specification adds no isolation claim.

Budgets stay the caller's. Resolution enforces no budget of its own and applies
SPEC-0004's counted invocation and proposal limits unchanged, taking the minimum
of the policy's and the declaration's as the host already does. Conformance runs
under unlimited node budgets over a fixed tiny grid, so its cost is bounded by
that grid rather than by a caller-supplied limit.

No GPU work is performed, no device is selected and the shared host lease is not
involved. No network access occurs. Unsafe code remains prohibited outside
optimizer-highs, and this specification introduces no new unsafe boundary, which
is precisely why dynamic native loading stays out of it.

## Examples

```bash
optimizer registry list --registry examples/extension-registry-v1.json

optimizer registry check --registry examples/extension-registry-v1.json \
  --extension flow-shop-neh --instance examples/flow-shop-v1.json \
  --output artifacts/conformance.json

optimizer schedule solve --instance examples/flow-shop-v1.json \
  --config examples/search-config-neh-v2.json \
  --registry examples/extension-registry-v1.json \
  --output artifacts/schedule-run.json \
  --output-model artifacts/schedule-model.json

optimizer verify --record artifacts/schedule-run.json \
  --model artifacts/schedule-model.json \
  --registry examples/extension-registry-v1.json
```

The scheduling run registers the NEH producer and reports `proven_optimal` with
objective 7 for the committed three-job, two-machine example instance, which is
the minimum makespan over its six permutations by exhaustive enumeration.
Verification re-executes it through the same registry and agrees, exiting 0. This
is the case that is not possible before this specification: the same run verified
without a registry is refused as unsupported.

Verifying that record against a registry whose entry names a different version of
the producer is refused as unsupported rather than reported as divergence.
Registering an experimental entry without `--allow-experimental` is refused, and
with it the written record carries a warning naming the entry.

## Acceptance Tests

Requirements 1-4: a valid registry document round-trips; documents missing a
field, carrying an unknown or duplicate field, arriving as an array, naming an
unknown enum variant, carrying a wrong version at the document or entry level, or
repeating an extension identity are each refused at parse time.

Requirements 5-14: each refusal path is asserted separately in its own
`ErrorKind` category, and each is asserted against the extension's own invocation
counter to establish requirement 14, so no refusal test can pass because the
extension was never built. The paths are an unprovided identity; a declaration
disagreeing with the entry on version, category, host contract version, problem
class, determinism and limits, each individually; an authority basis that does
not derive from the category; an unsatisfied data requirement; a gpu hardware
requirement; an absent required identity; a declared conflicting pair; a promoted
entry whose conformance record is absent, whose bytes were tampered with, whose
outcome is a failure, and which names another version; and an experimental entry
without permission. Requirement 13 is asserted by a two-entry registry in which
one entry is refused and the search does not run at all.

Requirements 15-17: two registries differing only in entry order produce
byte-identical records apart from elapsed time; a search with a registry supplied
and an empty extension policy produces the record the extension-free entry point
produces apart from elapsed time; and the committed C4 example record still
verifies unchanged, which is what establishes that no existing behavior moved.

Requirements 18-22: a scheduling run registering the NEH producer through a
registry writes a run record and that record verifies by re-execution, which is
the property that does not exist before this specification and is asserted both
in Rust and, across a commit boundary, by the acceptance gate re-executing a
committed registry-backed record; a non-empty policy without `--registry` is
refused as unsupported; a record whose extension resolves to a different version
is refused as unsupported rather than diverging; a record declaring
nondeterminism is refused as unsupported; a summary difference in invocations,
proposals, acceptances, rejections or disabled state is reported as a note
without changing the exit code, asserted by a run that agrees while reporting
one; and a forfeited registry-backed record that verifies still reports
forfeiture and still fails `proves_completion`.

Requirements 23-25: `registry check` on an honest producer writes a record whose
checks pass, and on a producer whose every proposal is refused writes a record
that still reports identical search conclusions with the refusals recorded; the
grid size is asserted so it cannot silently shrink; a deliberately misbehaving
extension produces a recorded failing check rather than an absent one; and the
suite is shown to fail when the invariance it asserts is violated, so it can fail.

Requirement 26: the committed registry and conformance examples validate under
their JSON Schemas and parse in Rust, and a document either authority rejects is
rejected by the other, including a wrong nested entry version. Requirement 27: no
test records a runtime or a solution-quality comparison, and the conformance
record carries no timing field that could be read as one.

Native-dependent tests report an explicit skip when the pinned library is absent,
so a missing build is never counted as coverage. The complete
`bash tools/check.sh` gate with native acceptance covered is required before this
slice is complete.

## Open Questions

Whether a run record should identify the registry that resolved it is
unresolved. A record names each extension's identity and version but not the
registry document's bytes, so licenses and promotion state are auditable through
the registry rather than through the record. Closing that needs a new run record
version and an ADR under SPEC-0005's compatibility rule, and nothing here
authorizes it.

An extension is identified by identity and version, so two different builds of
one version are indistinguishable. This is the same limitation already recorded
for the pinned native library, and it is why requirement 21's summary difference
exists as a diagnostic: it can show that a resolved extension behaved
differently, without claiming to know why.

Whether any registered extension improves a search is a hypothesis and is
deliberately unmeasured. Promotion here means the contract conformance suite
passed. A promotion gate based on held-out performance is C7's work and needs its
own contract.

Dynamic loading of separately distributed native extensions and process-isolated
extension workers both remain deferred with SPEC-0004's recorded blockers. A
registry makes their absence more visible rather than less: it is now the obvious
place such an extension would be named, and it deliberately cannot name one.
