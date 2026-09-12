# ADR-0008: Registry Resolution Without Dynamic Loading

Status: accepted
Owner: extension runtime
Introduced: C8
Last reviewed commit: 08ed424
Superseded by: none; ADR-0001 through ADR-0007 remain in force

## Context

C3 gave extensions a contract and C4 gave searches a record, but the two do not
meet. `optimizer_solver::search_with_extensions` takes `&[Registration]`, an
in-memory slice valid for one search, and nothing outside Rust test code can
build one. The consequences are recorded rather than theoretical:

- `optimizer search` refuses any configuration whose extension policy is
  non-empty, because running without the named extension would record a search
  the caller did not request.
- `optimizer verify` refuses a record naming an extension for the same reason,
  which means a C5 scheduling run performed with the NEH producer is not
  verifiable by re-execution. C5's reproducibility evidence covers only
  producer-free runs.
- SPEC-0004 deliberately parked its data-needs, hardware and inter-extension
  dependency fields, stating they belong to the registry, so an extension has no
  way to declare auxiliary input it requires.

Two constraints bound any design here. ADR-0003 permits unsafe code only inside
optimizer-highs, so a versioned C boundary for separately distributed native
components is unavailable without an amending decision record. And a registry
that changes which extensions a search consults is exactly the kind of implicit
state that would undermine the provenance C4 established, if it could be
introduced into a run without the caller saying so.

The decision this record fixes is what a registry is permitted to do, before
either an SDK or a comparative experiment runner is built over it.

## Decision

Implement [SPEC-0009](../specifications/SPEC-0009-extension-registry.md) in a new
optimizer-registry crate plus a provider table and subcommands in optimizer-cli,
in safe Rust, retaining the workspace `unsafe_code = "forbid"` prohibition.

**The registry resolves; it does not load.** An entry names an extension the
binary already provides, through a caller-owned `Provider` seam. This is the
third instance of a pattern the repository already relies on twice — `&dyn
Backend` under SPEC-0002 and `&[Registration]` under SPEC-0004 — and it keeps the
registry crate free of any list of first-party extensions. An entry naming an
identity this build does not provide is refused, not skipped, because skipping is
the quiet substitution these records exist to prevent.

**The declaration is authoritative; the entry is a claim about it.** Resolution
refuses a mismatch in either direction rather than reconciling it, which is
SPEC-0004 requirement 2's exact-version rule applied to a wider set of fields.
Reconciling would mean preferring one untrusted statement over another. Authority
stays derived from the category by `Category::authority`, so an entry recording
an authority basis is stating a checkable fact, not choosing a privilege.

**Resolution is all-or-nothing and happens before the search starts.** A search
never begins with a subset of the extensions it was configured with, and a
resolution failure writes no run record, matching SPEC-0005 requirement 8's rule
that a run which could not start is an error rather than a run.

**A registry is named explicitly with no default and no discovery.** There is no
search path, no environment variable and no implicit location, so a registry
cannot be introduced into a run by placing a file somewhere. `--allow-experimental`
is likewise off by default, and registering an experimental entry writes a
warning into the record's existing `warnings` field. The permissive choice is
therefore always visible in both the command and the record.

**Promotion is a checkable claim about a conformance record, not prose.** A
promoted entry names a conformance record and its checksum, and resolution
verifies the bytes, the outcome and the extension version. The conformance suite
is C3's invariance pattern made reusable: over a fixed grid with unlimited
budgets, an extension must leave the outcome, proven optimum, dual bound,
forfeiture state and both prune counters identical to an extension-free run, and
the suite asserts the extension was actually invoked before asserting anything
about its effect. Promotion means that suite passed. It does not mean the
extension is good, and this record does not authorize reading it that way.

**No document version changes and agreement is untouched.** An extension is
identified in a record by the `extension_id` and `version` its `ExtensionSummary`
already embeds verbatim, so a record naming an extension is re-resolvable without
a new field. `RUN_SCHEMA_VERSION` stays 1 and verification still compares exactly
SPEC-0005 requirement 11's ten fields. This is a deliberate constraint rather
than convenience: adding a compared field would change what agreement means for
every record produced before the change, which SPEC-0005 reserves for a new record
version plus an ADR.

**Two verification cases are refused as unsupported rather than reported as
divergence:** a record whose extension resolves to a different version, and a
record any of whose summaries declares nondeterminism. SPEC-0004 requirement 18
withholds replay equality for a nondeterministic search, so comparing it could not
mean anything, and calling either case divergence would blame the record for a
property of the verifier's inputs. This is the same distinction the C5
implementation already drew when it changed a misleading divergence into a
refusal, and it is why an extension summary difference is a diagnostic note
modeled on `EnvironmentDifference` rather than a comparison.

Acceptance evidence is SPEC-0009's mapped tests plus a complete
`bash tools/check.sh` with native acceptance covered, including a gate step that
re-executes a committed registry-backed scheduling record against the current
build, so the closed gap is established across a commit boundary rather than
within one process.

## Alternatives

**Amend ADR-0003 and implement dynamic native loading now.** This is what a
registry eventually wants, and it is what "local registry" might be read to
promise. Rejected for this slice: it needs a second unsafe boundary, an ABI
stability contract, a lifecycle and unload story, and crash isolation evidence,
none of which exists. Bundling it here would make the slice's acceptance gate
depend on evidence about process isolation rather than about resolution. It stays
deferred with its recorded blocker, and the registry is now the obvious place it
would be named, which makes the absence more visible rather than less.

**A default registry path or discovered registry directory.** Convenient, and
rejected outright. A run's extensions would depend on the filesystem rather than
on the command, so two identical commands could produce different searches, and a
record could not be reproduced from the command that appears beside it. Explicit
naming costs one flag and preserves the property C4 exists to establish.

**Add the registry to the run record and to agreement.** Strictly more honest
about consumed bytes, and the right eventual answer. Rejected now because it is
breaking: a new run-record version, migration notes, a regenerated committed
example, and a changed meaning of agreement for every existing record. The
limitation is recorded instead, and it is the first open question in SPEC-0009.

**Trust the entry over the declaration, or the declaration over the entry.**
Trusting the entry would let a document grant an extension a category or an
authority the code does not implement. Trusting the declaration silently would
make the entry decorative, and a caller reviewing a registry would be reading
fields nothing checks. Refusing the mismatch is what makes the entry worth
writing.

**Let the registry name a policy's budgets.** Rejected as a scope creep that
would split the authority for budgets between two documents. SPEC-0004 already
takes the minimum of the policy's and the declaration's counted limits; a third
source would make a record's budgets ambiguous.

## Consequences

`optimizer search`, `optimizer verify` and `optimizer schedule solve` gain a
registry path, and `optimizer schedule solve` stops hardcoding a single producer
identity. Two recorded known-failures close: the registry exists, and a
scheduling record produced with a producer registered is verifiable. C5's
reproducibility claim extends to producer-backed runs, which is the concrete gain.

Costs and limits, each recorded rather than absorbed:

- A record does not identify the registry that resolved it. Licenses and
  promotion state are auditable through the registry, not the record.
- An extension is identified by identity and version, so two builds of one
  version are indistinguishable. This is the same limit already recorded for the
  pinned native library, and it is why the summary-difference diagnostic exists.
- Provider construction happens before SPEC-0004's host exists, so a provider
  that panics during construction is outside the panic-containment claim. The
  host's containment of `declare`, `propose` and `advise` is unchanged.
- The conformance suite establishes contract invariance only. Nothing here
  measures whether an extension helps, and promotion must not be read as saying
  it does.
- The registry cannot name a dynamically loaded native extension, an isolated
  worker, or a GPU-requiring extension. Each refusal is explicit.

Follow-up work, each needing its own contract: the Python SDK, whose pyo3 blocker
is unchanged by this record; comparative experiment execution over a frozen
manifest; a promotion gate based on held-out performance, which is C7's; and
recording the registry in the run record, which needs run-record v2.

## Implementation and tests

This record was accepted before its implementation, as ADR-0004 through ADR-0007
each were.

Implementation: [the registry crate](../../crates/optimizer-registry/src/lib.rs)
holding [the document](../../crates/optimizer-registry/src/document.rs),
[resolution](../../crates/optimizer-registry/src/resolve.rs) and
[the conformance suite](../../crates/optimizer-registry/src/conformance.rs), plus
[the provider table and subcommands](../../crates/optimizer-cli/src/registry.rs)
and registry integration in
[search and verify](../../crates/optimizer-cli/src/search.rs) and
[schedule solve](../../crates/optimizer-cli/src/schedule.rs).

Tests: [registry contracts](../../crates/optimizer-registry/tests/contracts.rs),
[scheduling CLI contracts](../../crates/optimizer-cli/tests/schedule.rs),
[schema contracts](../../tests/integration/test_registry.py), and the
committed-record re-execution step in
[the acceptance gate](../../tools/check.sh), which is what establishes the closed
gap across a commit boundary rather than within one process.
