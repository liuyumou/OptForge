# Active Task

## C4 Follow-up: Gated Re-execution and Engine Diagnostics (2026-09-11)

Objective: close three gaps found reviewing the C4 slice — a gate that never
re-executed a committed record, a divergence that could not distinguish a changed
engine from a wrong result, and a non-native build recording a backend version it
never called.

Status: complete; the full gate passes with native acceptance covered, and the
non-native configuration passes separately.

Acceptance gate: the committed example record re-executes against the current
build inside `bash tools/check.sh`, with both refusal directions asserted there
too; a record naming a different revision or compiler still verifies while
reporting the difference; a divergence carries that difference as a note without
changing its exit code; a build linking no native library records `unavailable`
rather than the pinned version, shown by a test that fails when the old code is
reinstated. Resource budget: CPU only, no GPU workloads.

Scope boundary: consulting engine identity as an *explanation* is within
SPEC-0005 as accepted, because requirement 11 fixes the ten compared fields and
requirement 13 forbids strengthening a claim; neither constrains diagnostic text.
Deciding that a version mismatch makes divergence *tolerable* would change the
meaning of agreement, which SPEC-0005's compatibility section says requires a new
record version and an ADR. That remains open and is recorded, not implemented.

Evidence (2026-09-11): the complete gate passed with the pinned library linked and
zero skip messages. Rust tests rose from 156 to 159: two environment-difference
contracts in optimizer-experiment and one CLI contract asserting the diagnostic
does not decide agreement. Python tests remain 39 and documentation 46 pages. The
new `tools/verify_committed_record.py` step reports
`committed run record re-executed and verified: passed`.

`AI_OPTIMIZER_SKIP_NATIVE=1 bash tools/check.sh` also passed with all 159 tests,
still printing its uncovered-acceptance warning, and correctly skipping the
committed-record step because a build with no library cannot solve at all.

The backend-version fix is verified by reinstating the defect rather than by
assertion alone: with `PINNED_VERSION` restored on the pre-cancelled path, the
non-native test fails at backend.rs:172; with the fix, it passes. The same test
runs in both configurations, so the native path is covered by the same assertion.
`interrupted_record` was the reachable path, because a pre-cancelled solve returns
a record without touching the library.

Why the gate step exists: every Rust re-execution test produces its record moments
earlier in the same process against the same binary, so none of them exercised the
property SPEC-0005 actually claims, that a record outlives its author. The gate now
re-runs a record committed at an earlier revision, and asserts the fingerprint
refusal and a counter divergence there as well, so the passing case is not the
only thing checked.

Noted: the example record's own provenance differs from any current checkout by
construction, since it carries the all-zero revision. That made it the natural
fixture for the diagnostic — verifying it now reports `environment_differs: true`
while still agreeing and exiting 0, which is exactly the separation between
explanation and decision that this change is about.

## C4 Agent-Independent Run Surface (2026-09-11)

Objective: implement the first C4 slice under a new SPEC-0005: expose the C2
executive and C3 extension host through the CLI, wrap each search in a
provenance-bearing run record, and add a verification command that re-runs a
search from its record alone and fails on disagreement.

Status: complete; the specification preceded the implementation, and the full
gate passes with native acceptance covered.

Acceptance gate: a search performed through the CLI writes a schema-valid run
record carrying source revision, dirty state, hardware, toolchain, backend
identity and version, the canonical model fingerprint and hashed inputs; that
record is re-executable by `optimizer verify` using only its embedded
configuration and the model it names; verification detects a mutated outcome,
objective, dual bound, forfeiture flag and each node counter individually, and
rejects a model whose fingerprint changed while its `model_id` did not;
elapsed time alone never fails verification; and `bash tools/check.sh` passes
with native acceptance covered. Resource budget: CPU only, four Cargo workers,
no GPU workloads.

Scope boundary, decided before implementation: the backlog's C4 line bundles
four deliverables and CONTRIBUTING.md mandates one complete vertical slice. This
slice delivers the CLI run surface and pinned reproducible runs. The local
registry and the Python SDK are deferred to their own specifications and gates
and are recorded in [known failures](known-failures.md) rather than dropped
silently. The SDK deferral has a technical basis: pyo3 expands to unsafe code,
the workspace forbids it, and ADR-0003 permits unsafe only inside
optimizer-highs, so an SDK needs an amending decision record.

Expected changes: new SPEC-0005 and ADR-0006; `crates/optimizer-experiment`
gains its first types and dependencies; new `schemas/run-record-v1.schema.json`
and `schemas/search-record-v2.schema.json`; `crates/optimizer-cli` gains
`search` and `verify` over new optimizer-solver and optimizer-experiment
dependencies; new tests in optimizer-cli, optimizer-experiment and
tests/integration; `examples/run-record-v1.json`;
`tools/validate_artifacts.py`; README.md, CHANGELOG.md,
docs/architecture/{overview,testing}.md, a new run-and-verify tutorial,
docs/operations/build.md, wiki/{status,glossary}.md, schemas/README.md,
cuda/schedule_eval/README.md, implementation-plan.md, state/backlog.yaml,
state/known-failures.md and this record.

Evidence (2026-09-11): the complete `bash tools/check.sh` gate passed with the
pinned HiGHS 1.11.0 library built and linked, with **zero skip messages**, in 20
seconds on a warm build directory: format, warnings-as-errors Clippy over all
targets, 156 Rust tests, workspace build, warnings-as-errors rustdoc, cargo-deny
(advisories, bans, licenses, sources all ok), artifact validation, 39 Python
tests, 46-page documentation and link validation, and bootstrap smoke. No checks
were waived.

Rust tests rose from 132 to 156: 11 run surface CLI contracts in optimizer-cli,
11 run record contracts in optimizer-experiment, and 2 SHA-256 unit tests.
Python tests rose from 20 to 39: 12 run record and search record schema
contracts plus 2 checksum-agreement tests, counted with subtests as unittest
reports them. Documentation pages rose from 43 to 46: SPEC-0005, ADR-0006 and
the run-and-verify tutorial.

Cargo.lock changed only by adding local dependency edges: optimizer-cli on
optimizer-experiment and optimizer-solver, and optimizer-experiment on
optimizer-core, optimizer-solver, serde and serde_json. No external package
version changed, and no new external dependency was introduced.

Reproducibility evidence, stated as what was actually checked rather than as a
property claimed in prose:

- `optimizer search` over examples/model-v1.json reported
  `outcome: proven_optimal`, `objective: 2.5`, `dual_bound: 2.5`, `forfeited:
  false` and exit 0, matching the C1 solve of the same model exactly. The record
  carried a 40-hex revision, the model fingerprint `fnv1a64:cc63f58b64d1c205`,
  and a SHA-256 for each of the two input documents.
- `optimizer verify` on that record re-ran the search and agreed, exit 0, naming
  all ten compared fields in its verdict.
- Verification was shown to be able to fail, in both directions it must. A model
  whose objective coefficient changed from 2.0 to 2.5 while keeping
  `model_id: tiny-mixed` was refused before any search ran:
  `document: model fingerprint mismatch`, exit 2. A record whose objective was
  edited to 1.5 was refused after re-running:
  `divergence: numerical: objective: recorded 1.5, reproduced 2.5`, exit 2.
- Each of the ten compared fields is asserted to fail when it alone is mutated,
  and the list of mutated field names is asserted equal to
  `RunRecord::compared_fields()`, so a field cannot be dropped from the
  comparison without a test failing.
- A record differing only in `elapsed_ms` by 987 seconds still verified with exit
  0, which fixes elapsed time as diagnostic rather than contractual.
- A node-limited search wrote its record, reported `outcome: node_limit` and exit
  1, and that record verified as still limited. A forfeited search that verifies
  is asserted to remain forfeited and to fail `proves_completion`.

Why the SHA-256 is implemented rather than taken from a crate: `sha2` and its
dependencies would add six external packages under `deny.toml`'s
`multiple-versions = "deny"` policy for one well-specified function. It is
implemented in safe Rust and checked against the FIPS 180-4 published vectors,
including the three padding edge cases at 55, 56 and 64 bytes and the
one-million-character vector, then independently against Python's `hashlib` over
the committed example documents and over a freshly generated record. Agreement
between the two implementations is verified rather than assumed.

Both normative authorities accept the same documents. The new schemas give C2 and
C3 records their first schema coverage, and `RunRecord::from_json` validates the
embedded search record's version on the parse path, so the divergence that
produced commit 6516a6f cannot recur here.

Resolved during implementation: an early assertion that a record with absent
measurements contains no `null` at all was wrong and was narrowed. Search
configuration serializes an absent budget as an explicit `null` meaning
unlimited, which is SPEC-0003's stated convention; the omit-rather-than-null rule
governs measurements. The test now asserts the three measurements are absent and
that `node_limit` is still explicitly null beside them.

Noted and not changed: the example record is generated from a real search and
then rewritten with the all-zero revision and example hardware, matching how
examples/experiment-result.json marks itself as a shape rather than evidence. Its
input hashes are the real ones and are verified against the committed files by
both the validator and a Python test.

Scope split recorded in the backlog: C4's original line covered four
deliverables. C4 is now the run surface and the registry, SDK and comparative
runner are backlog item C8, which depends on C4. C5, C6 and C7 keep their
dependency on C4, which remains meaningful because the run surface is what they
build on. The four deferrals are recorded in
[known failures](known-failures.md) with their blockers.

Clean-checkout verification, which is the stronger C1 and C3 standard and the
case that matters here because this change adds four crate dependency edges where
a stale lockfile or a missing manifest entry would otherwise hide behind a
populated `target/`: the branch was cloned to /tmp/c4-verify with
`--no-hardlinks` and no `target/` directory present, and
`bash tools/check.sh` passed there in 1 minute 36 seconds. That run built the
pinned HiGHS 1.11.0 library from the checksum-verified upstream archive inside
the clone and ran the same 156 Rust and 39 Python tests. The only lines matching
"skip" were CMake's own `Check for working CXX compiler - skipped` probes, not
test skips, so native acceptance was genuinely covered rather than inherited from
a warm build directory.

On the clean committed tree the run surface produces evidence-grade provenance:
`optimizer search` recorded revision c0eac20 with `dirty: false`, and
`optimizer verify` reported `agreement: true` with `evidence: true` and exit 0.
The dirty mid-implementation runs reported `evidence: false`, which is the
requirement 5 rule working rather than a defect.

No remote refs were changed and nothing was pushed; main remains unpushed pending
separate authorization. The branch feat/run-surface holds two commits, 8775da1
specifying the surface and c0eac20 implementing it.

## Local C3 Integration (2026-09-09)

Objective: verify the reviewed feat/extension-runtime branch from a clean
checkout, integrate it into local main, and delete the feature branch after
confirming its commits are retained.

Status: complete; clean-checkout verification, fast-forward integration and
feature-branch cleanup finished.

Acceptance gate: the complete gate passes in an independent clone with nothing
prebuilt; fast-forward integration preserves the reviewed tip 6516a6f; the
feature branch is deleted and the worktree is clean. Resource budget: CPU only,
four Cargo workers, no GPU workloads.

Evidence (2026-09-09): the branch was cloned to /tmp/c3-verify with no `target/`
directory present, and `bash tools/check.sh` passed there in 1 minute 44 seconds
with **zero skip messages**, so native acceptance was genuinely covered rather
than inherited from a warm build directory. That run built the pinned HiGHS
1.11.0 library from the checksum-verified upstream archive inside the clone,
producing both `libhighs.a` (10.2 MB) and the standalone reference executable
(5.0 MB). It ran 132 Rust tests and 20 Python tests, validated 43 documentation
pages, and passed cargo-deny, artifact validation and bootstrap smoke.

The clean clone also solved examples/model-v1.json to `termination: optimal`,
`objective: 2.5`, `backend_version: 1.11.0` with an independently validated
feasible incumbent and exit 0, matching the workspace result exactly.

This clean-checkout pass is the acceptance evidence for the integration. It was
run because C3 adds two crates and a new dev-dependency edge, which is exactly
the case where a stale lockfile or a missing manifest entry hides behind a
populated `target/`. The C2 integration relied on its pre-integration gate pass
instead; this record restores the stronger C1 standard.

main was fast-forwarded from b934dbd to 6516a6f without conflicts or history
rewriting, so the integrated tree is byte-identical to the verified revision.
`git merge-base --is-ancestor` confirmed the reviewed tip is retained on main,
`git rev-parse` confirmed main is exactly the verified revision, and
`git branch -d` removed the fully merged feat/extension-runtime branch. The
worktree is clean and the bootstrap smoke was rerun on the integrated revision
for clean revision-bound provenance.

The RustSec advisory-database fetch failed in the clean clone and recovered
through the cached database, as recorded in [known failures](known-failures.md).
Bans, licenses and sources were checked normally. No checks were waived.

No remote refs were changed. main is now 3 commits ahead of origin/main and
remains unpushed pending separate authorization; the origin remote and its
outstanding protection settings are recorded in
[known failures](known-failures.md).

Follow-up: C4, the agent-independent SDK, CLI, experiment workspace and local
registry, is dependency-ready. Write its specification before introducing any
public SDK or registry API.

## C3 Review Follow-up: Test Provenance and Nested Versions (2026-09-09)

Objective: resolve three problems found reviewing the C3 commit — a history that
made four mandatory test repairs indistinguishable from weakened ones, a
replacement test helper that asserted on serializer whitespace, and Rust record
parsers laxer than the JSON Schemas about nested document versions.

Status: complete; the branch is three commits and the full gate passes with
native acceptance covered.

Acceptance gate: the test repair compiles and passes on its own at search
schema version 1, proving it is not a consequence of the version bump; the
repaired assertions are shown to fail when the helper is sabotaged, so none is
vacuous; a record with a wrong nested version is rejected by both
`from_json` and `tools/validate_artifacts.py`; and `bash tools/check.sh` passes
with native acceptance covered. Resource budget: CPU only, four Cargo workers,
no GPU workloads.

Expected changes: the branch history; `crates/optimizer-core/src/{lib,solve}.rs`;
`crates/optimizer-solver/src/search.rs`; contract tests in optimizer-core,
optimizer-solver and optimizer-extension-examples; SPEC-0002 requirement 11,
SPEC-0003 requirement 22, SPEC-0004 requirement 23 and their acceptance
mappings; CHANGELOG.md and this record.

Evidence (2026-09-09): the branch is `b934dbd` → `9a2eda5` (test repair) →
`a85da69` (C3) → this commit. `git diff c3-pre-split a85da69` touches only the
test helper, confirming the split preserved the reviewed C3 content byte for
byte elsewhere; the pre-split tip is retained as tag `c3-pre-split`. The repair
commit's 22 contracts pass at version 1 with no extension field present, which
is what establishes that the repair was independent of the feature rather than
produced by it. Sabotaging `retarget_version` to a no-op makes both version
tests fail, so neither is vacuous.

The complete `bash tools/check.sh` gate passed with the native library built and
linked, with **zero skip messages**. Rust tests rose from 130 to 132: one nested
version contract in optimizer-core and one in optimizer-solver, plus extension
document coverage folded into the existing round-trip test. Cargo.lock changed
only by adding a `serde_json` dev-dependency edge for
optimizer-extension-examples; no external package version changed.

Why the parser change needed no ADR: `schemas/solve-record-v1.schema.json`
already pins the nested candidate's `schema_version` to `const 1` and pins
`options` by `$ref`, and those schemas are normative under SPEC-0007. The Rust
parsers checked only their own top-level version, so the two enforcement paths
disagreed and `tools/validate_artifacts.py` rejected documents the Rust parser
accepted. This change brings code into line with an accepted contract rather
than deciding anything new, and it is strictly narrowing: no document valid
under both paths becomes invalid. Verified by parsing one fixture with a wrong
nested version through both paths and confirming both reject it.

`Candidate::canonical` is deliberately not called on the parse path. It also
sorts and range-checks values, and parsing a record must reject a wrong version
without silently rewriting the document it was handed.

Resolved during implementation: the acceptance suite needed `serde_json` as a
dev-dependency to mutate a parsed document by field path. It is test-only, so
the examples crate's runtime dependencies remain optimizer-core and
optimizer-extension alone, and the independence evidence is unaffected.

Noted and not changed: `crates/optimizer-core/tests/solve.rs` still replaces
every `"schema_version": 1` occurrence in one assertion, which passes only
because the top-level check fires first. It is not wrong today and its
assertion is the top-level rule, so it is left alone; the new nested-version
contract beside it covers what the replacement cannot distinguish.

Follow-up: C4, the agent-independent SDK, CLI, experiment workspace and local
registry, is dependency-ready. Write its specification before introducing any
public SDK or registry API.

## C3 Extension Runtime and Authority Model (2026-09-09)

Objective: implement C3 under a new SPEC-0004: an extension runtime with a
declared authority model, candidate producers and search advisers, whose actions
the core validates and whose failures are recorded rather than absorbed.

Status: complete; the specification preceded the implementation, and the full
gate passes with native acceptance covered.

Acceptance gate: independently authored extensions build and run against the
published APIs with no engine-internal change; invalid candidates, invalid
advice, incompatible versions, panics and budget abuse each produce a typed
record entry; the proven optimum and the proof claim are identical with and
without extensions, including adversarial ones; and `bash tools/check.sh` passes
with native acceptance covered. Resource budget: CPU only, four Cargo workers,
no GPU workloads.

Expected changes: new SPEC-0004 and ADR-0005; new crates optimizer-extension and
optimizer-extension-examples; optimizer-solver contracts, executive and hooks;
`SEARCH_SCHEMA_VERSION` 1 to 2; the C2 search and native executive tests;
SPEC-0003 compatibility and exclusion clauses; implementation-plan.md, README.md,
docs/architecture/{overview,testing}.md, wiki/{status,glossary}.md, CHANGELOG.md,
state/backlog.yaml, state/known-failures.md and this record.

Evidence (2026-09-09): the complete `bash tools/check.sh` gate passed with the
native library built and linked, with **zero skip messages**: format,
warnings-as-errors Clippy, 130 Rust tests, workspace build, warnings-as-errors
rustdoc, cargo-deny (advisories/bans/licenses/sources), artifact validation, 20
Python tests, 43-page documentation/link validation and bootstrap smoke. Rust
tests rose from 84 to 130: 27 new extension runtime contracts, 18 new
independent-extension acceptance contracts, and 1 new native end-to-end
contract. No checks were waived.

The RustSec advisory-database fetch failed on the final run and recovered
through the cached database, as recorded in
[known failures](known-failures.md). Bans, licenses and sources are offline and
were checked normally; the advisory check ran against the cache rather than a
fresh fetch.

Cargo.lock changed only by adding local dependency edges for
optimizer-extension (optimizer-core, serde, serde_json),
optimizer-extension-examples (optimizer-core, optimizer-extension, and
optimizer-solver as a dev-dependency), the optimizer-solver dependency on
optimizer-extension, and optimizer-highs dev-dependencies on both new crates.
No external package version changed.

Correctness evidence, stated as what was actually checked:

- Three honest extensions and three hostile ones covering 17 distinct
  misbehavior modes (7 bad proposals, 4 bad actions, 6 unadmittable
  declarations) live in optimizer-extension-examples, which depends on the
  published extension and core APIs and takes optimizer-solver only as a
  dev-dependency. That the
  workspace builds is the evidence that a third-party extension needs no
  engine-internal change; it is not an assertion in prose.
- Over a fixed 25-model grid covering both senses, integer and binary domains,
  three capacities, two coefficient settings and a proven-infeasible case, every
  hostile extension leaves the outcome, the
  proven optimum, the dual bound, the forfeiture state and both prune counters
  identical to the extension-free run, which itself agrees with brute-force
  enumeration of the whole assignment space. These comparisons use unlimited
  node and time budgets deliberately: a hostile adviser spending a node budget
  on unpromising nodes legitimately changes which outcome a *budgeted* search
  reaches, so a budgeted assertion would be flaky by design rather than a real
  correctness check.
- An empty extension policy reproduces the extension-free record exactly, apart
  from measured elapsed time. That is the direct check that C3 did not perturb
  C2, and all 22 C2 contracts still pass unchanged in substance.
- Refusals are typed and recorded: infeasible, out-of-bounds, wrong-model,
  incomplete and nonfinite candidates; advice naming a nonexistent node, an
  unknown variable or an integral variable; both directions of host-contract
  mismatch; a refused transformation category; an unclaimed problem class;
  contained panics in `propose`, `advise` and even `declare`; and exhausted
  invocation and proposal budgets. A refused extension is never invoked at all,
  which is asserted against a call counter the extension itself maintains.
- A producer's claimed objective is never read. The out-of-bounds producer
  offers a candidate with an enormous objective and the record still reports the
  true optimum from independent recomputation.
- Recorded diagnostics stay bounded: 10,000 distinct rejections leave the
  counter exact at 10,000 and the retained messages capped at 8.
- The native end-to-end test drives the real executive over pinned HiGHS with a
  lying producer, a ghost-node adviser and a panicking adviser registered
  simultaneously, and still proves the optimum independent enumeration finds.

Resolved during implementation:

- The first acceptance run showed a search adviser being consulted for a
  continuous model, which requirement 20 forbids. Root cause: the node-selection
  hook ran whenever the frontier was non-empty, including when it held exactly
  one node and there was no choice to make. Fixed by not consulting an adviser
  for a decision with one possible answer, and recorded as SPEC-0004
  requirement 9a rather than patched silently. Consulting there could only
  manufacture rejections describing the hook rather than the extension.
- Three acceptance tests initially asserted against models whose LP relaxations
  happen to be integral, so no branching occurred and no adviser was ever
  consulted; they were passing or failing for reasons unrelated to their names.
  They now use a model with a genuinely fractional relaxation and assert
  `nodes_explored > 1` first, so a future change that removes the branching
  cannot make them vacuous.
- Three C2 record tests needed repair rather than renumbering. Two mutated "the
  first `schema_version` in the JSON", which at version 2 is the nested
  candidate's or is absent entirely, so they would have parsed successfully and
  panicked on `unwrap_err`. A third hand-wrote a complete configuration object
  plus an unknown field; with a new required field it would have been rejected
  for the *missing* field while still passing, silently ceasing to test
  unknown-field rejection. All three now target the document's own version or
  build their base from a serialized valid configuration.

Deferred and recorded rather than hidden: the extension host is in-process, so
containment covers panics but not a process abort, stack exhaustion or a memory
fault, and no per-extension memory budget is enforced. Process isolation and the
versioned C boundary for dynamically loaded native components are specified as
deferred and need their own decision record, because a second unsafe boundary
would amend ADR-0003. No CLI subcommand exposes extensions yet, no JSON Schema
covers search or extension records, and no performance claim is made: C3
establishes safety only, and whether advisers improve search is C7's question.

Follow-up: C4, the agent-independent SDK, CLI, experiment workspace and local
registry, is dependency-ready. Write its specification before introducing any
public SDK or registry API.

Contract decisions worth recording, because they are the ones a later
implementation could get quietly wrong:

- No extension path may reach forfeiture, a search-loop break, or an `Err`
  return from `search`. An adversarial extension must not be able to deny a
  proof the engine would otherwise complete. C2 forfeits when a *backend*
  misbehaves because its bounds become untrustworthy; a bad extension candidate
  implies nothing about bounds, so it is a recorded rejection and a disable.
- A proposed candidate is validated by `Model::evaluate` against the original
  model, and the record's objective is the recomputed one. A producer's claimed
  objective is never read.
- An advised branching variable must lie in the recomputed fractional set. This
  is a termination requirement, not a preference: branching on an integral
  variable yields two children that do not tighten the box, which is the same
  hazard SPEC-0003 requirement 12a exists to prevent.
- Extension budgets are counted in invocations and proposals, never wall clock,
  so the search path cannot depend on machine speed and requirement 21's replay
  guarantee survives.
- The `backend` category is not introduced: `optimizer_core::Backend` is already
  public and replaceable under SPEC-0002, and declaring the category only to
  refuse it would read as a regression of an accepted contract.
- `transformation` is refused at declaration time, so no code path for it
  exists until its validity has its own contract.

## Local C2 Integration (2026-09-09)

Objective: integrate the reviewed feat/solver-executive branch into local main
and delete the feature branch after confirming its commits are retained.

Status: complete; fast-forward integration and feature-branch cleanup finished.

Acceptance gate: fast-forward integration preserves the reviewed tip 5a74184;
the feature branch is deleted and the worktree is clean. Resource budget: CPU
only, no GPU workloads.

Evidence (2026-09-09): main fast-forwarded from c742064 to 5a74184 without
conflicts or history rewriting, so the integrated tree is byte-identical to the
revision whose complete gate pass is recorded below. `git merge-base
--is-ancestor` confirmed the reviewed tip is retained on main, and `git branch
-d` removed the fully merged feat/solver-executive branch. The worktree is clean
and the bootstrap smoke was rerun on the integrated revision for clean
provenance.

No remote refs were changed. main remains unpushed pending separate
authorization; the origin remote and its outstanding protection settings are
recorded in [known failures](known-failures.md).

## C2 Owned Solver Executive Implementation (2026-09-09)

Objective: implement C2 under SPEC-0003: an owned branch-and-bound executive in
optimizer-solver that consumes the C1 backend contract as a relaxation service
and owns proof completion.

Status: complete; executive, contract documents, node representation and
acceptance tests are in place and the full gate passes with native acceptance
covered.

Acceptance gate: exhaustive tiny-model search compared against independent
enumeration, termination semantics, budgets, cancellation, proof completion, and
`bash tools/check.sh`. CPU only, four Cargo workers, no GPU workloads.

Expected changes: optimizer-solver runtime and tests, an end-to-end test in
optimizer-highs, SPEC-0003 implementation/test links, project records, changelog
and this task record.

Evidence (2026-09-09): the complete `bash tools/check.sh` gate passed with the
native library built and linked, with **zero skip messages**: format,
warnings-as-errors Clippy, 84 Rust tests, workspace build, warnings-as-errors
rustdoc, cargo-deny (advisories/bans/licenses/sources, fetched successfully this
run without the cached-database fallback), artifact validation, 20 Python tests,
41-page documentation/link validation and bootstrap smoke. Rust tests rose from
58 to 84: 22 new search contracts and 4 new native end-to-end contracts. No
checks were waived.

Cargo.lock changed only by adding local dependency edges for optimizer-solver
(optimizer-core, serde, serde_json) and the optimizer-highs dev-dependency on
optimizer-solver. No external package version changed.

Correctness evidence, stated as what was actually checked:

- 192 tiny discrete models over a fixed coefficient, bound and row-limit grid,
  both objective senses, integer and binary domains, agree with brute-force
  enumeration of the entire assignment space on the proven optimum and on proven
  infeasibility. The grid is fixed with no randomness, so a failure reproduces.
- Every non-optimal relaxation termination (time, iteration and node limits,
  interruption, feasible-without-proof, numerical failure, backend failure,
  unsupported) forfeits the proof claim and prunes nothing by bound.
- The executive runs entirely on test backends, which is what demonstrates
  backend neutrality; the end-to-end test over pinned HiGHS lives in
  optimizer-highs so optimizer-solver keeps that guarantee. Both agree with
  independent enumeration.

Resolved during implementation:

- The first test run did not terminate. A backend that returns the same
  fractional solution regardless of node bounds caused the executive to
  regenerate an identical child forever. Root cause: the executive trusted the
  relaxation solution to lie inside the node it asked about. Fixed by checking
  every relaxation solution against its own node before branching, which makes
  termination independent of backend correctness. Recorded as SPEC-0003
  requirement 12a rather than fixed silently.
- A record test asserted no `null` anywhere in the serialized record. That
  conflated two rules: absent *measurements* are omitted, while an absent
  *budget* stays an explicit null meaning unlimited, matching the C1
  configuration convention. The assertion now targets measurements by name.

Deferred and recorded rather than hidden: checkpoint restart is specified in
shape and deliberately unimplemented; no CLI subcommand exposes search yet; no
performance claim is made and no comparison against another solver was run.
Cross-node basis reuse remains Stage 5 reoptimization work.

Follow-up: C3, the extension runtime and authority model, is dependency-ready.
Write its specification before introducing any public extension API.

## C2 Solver Executive Specification (2026-09-09)

Objective: write and accept the C2 contract before any owned search API exists,
as required by AGENTS.md and the Stage 2 entry condition. No C2 behavior is
implemented by this change.

Status: complete; SPEC-0003 and ADR-0004 are accepted and the project records
that reference C2 are synchronized.

Acceptance gate: the specification uses numbered observable MUST/MUST NOT
requirements with an acceptance-test mapping, states its exclusions, and passes
documentation/link validation; `bash tools/check.sh` continues to pass with
native acceptance covered and unchanged test counts, because no behavior changed.
Resource budget: CPU only, four Cargo workers, no GPU workloads.

Expected changes: docs/specifications/SPEC-0003-solver-executive.md,
docs/decisions/ADR-0004-owned-search.md, state/backlog.yaml, README.md,
implementation-plan.md, docs/architecture/overview.md, wiki/status.md, the two
stale placeholder doc comments in optimizer-solver and optimizer-schedule, and
this record.

Contract decisions worth recording, because they are the ones a later
implementation could get quietly wrong:

- A relaxation objective is admitted as a dual bound only when that relaxation
  reported `Termination::Optimal`. Any limit, interruption or failure leaves the
  node bound unavailable, forbids pruning that node by bound, and permanently
  forfeits the search's proof claim, recorded as `forfeited` in the record. This
  is what stops a timeout inside a child solve from silently discarding an
  optimal solution.
- `SearchOutcome` is a new type rather than a reuse of `Termination`. The two
  express different claims: one relaxation solve versus an exhausted node tree.
- The executive consumes the C1 `Backend` trait and must not depend on
  optimizer-highs, so the pruning and forfeiture rules are testable against a
  stub backend without the native library.
- `Tolerances.integrality` governs both incumbent acceptance and the decision to
  branch, so the two cannot disagree.
- Checkpoints are specified in shape only; restart is deliberately not part of C2
  and needs its own acceptance evidence.

Numbering: no spec-numbering convention exists in the repository, so SPEC-0003
and ADR-0004 take the next free sequential numbers. Two placeholder doc comments
referenced the retired M0-M6 scheme and dangled at nonexistent specifications;
optimizer-schedule's stale "SPEC-0003" claim would have collided with this
specification and now names C5 with an unassigned number.

No CHANGELOG.md entry accompanies this change: the changelog records user-visible
changes, and an accepted contract with zero behavior is not one. C2 enters the
changelog when its behavior ships.

Follow-up: C2 implementation is now dependency-ready under SPEC-0003. It requires
a stub-backend test crate for the bound-validity and forfeiture rules plus
exhaustive tiny-model comparison against independent enumeration.

## Local C1 Integration (2026-09-09)

Objective: verify the reviewed feat/highs-backend branch from a clean checkout,
integrate it into local main, and delete the feature branch after confirming its
commits are retained.

Status: complete; clean-checkout verification, fast-forward integration and
feature-branch cleanup finished.

Acceptance gate: the complete gate passes in an independent clone with nothing
prebuilt; fast-forward integration preserves the reviewed tip c8bb6f3; the
feature branch is deleted and the worktree is clean. Resource budget: CPU only,
four Cargo workers, no GPU workloads.

Evidence (2026-09-09): the branch was cloned to /tmp/c1-verify with no populated
target/native, and `bash tools/check.sh` passed there in 1 minute 43 seconds.
That run built the pinned HiGHS 1.11.0 library from the checksum-verified
upstream archive, produced both libhighs.a and the standalone executable, and ran
58 Rust and 20 Python tests with **zero skip messages**, so native acceptance was
genuinely covered rather than bypassed. The clean clone also solved
examples/model-v1.json to `termination: optimal`, `objective: 2.5`,
`backend_version: 1.11.0` with an independently validated feasible incumbent and
exit 0, and wrote a smoke record bound to revision c8bb6f3 with `dirty: false`.

This clean-checkout pass is the acceptance evidence for the integration. main was
fast-forwarded from 9b42b62 to c8bb6f3 without conflicts or history rewriting, so
the integrated tree is byte-identical to the verified revision.
`git merge-base --is-ancestor` confirmed the reviewed tip is retained on main, and
`git branch -d` removed the fully merged feat/highs-backend branch. No remote refs
were changed; main remains 9 commits ahead of origin/main and unpushed, pending a
separate authorization to push.

The advisory database fetch failed again during the clean-clone run and recovered
through the cached database, as recorded in
[known failures](known-failures.md). No checks were waived.

Follow-up: C2, the owned solver executive, is dependency-ready. Its specification
is now accepted as SPEC-0003; see the C2 record at the top of this file. No C2
behavior existed at the time of this integration.

## C1 Backend-Neutral Solve Contract and HiGHS Adapter (2026-09-09)

Objective: implement C1 under SPEC-0002: backend-neutral solve/session types,
HiGHS adapter boundary, strict solve configuration and structured records.

Status: complete; contract, native adapter, solve CLI, schemas and acceptance
tests are in place and the full gate passes with native acceptance covered.

Acceptance gate: core and adapter contract tests, strict CLI solve flow,
status/cancellation/limits/warm-start behavior, reproducible records, and
`bash tools/check.sh`. CPU-only; native HiGHS setup uses the pinned 1.11.0
source and at most four build workers.

Expected changes: optimizer-core, optimizer-highs, optimizer-cli, experiment
schemas, specifications, changelog, tests, and task state. No GPU workload.

Evidence (2026-09-09): the complete `bash tools/check.sh` gate passed with the
native library built and linked: format, warnings-as-errors Clippy, 58 Rust
tests, workspace build, warnings-as-errors rustdoc, cargo-deny
(advisories/bans/licenses/sources), artifact schema/provenance, 20 Python tests,
38-page documentation/link validation and bootstrap smoke. No checks were waived.

Native provisioning and FFI: `tools/setup_highs.sh` builds the pinned static CPU
library under `target/native/highs-1.11.0/install` from the checksum-verified
upstream archive. A hand-written private FFI module links it; no `highs-sys`
dependency is introduced. `Highs_version()` reports 1.11.0 and the compile-time
assertion confirms a 4-byte `HighsInt`, matching the pinned `HIGHSINT64=OFF`.

Differential acceptance: the standalone executable, built from the same source,
is driven as a separate process over generated LP files and agrees with the
adapter on status and objective for LP, objective-offset, equality, ranged, MILP
and infeasible cases. Disagreement fails the test rather than deferring to the
adapter. The reference is run in a sandbox directory with its log redirected, so
native output cannot litter the tree.

Correctness contracts verified: all 18 native model statuses map explicitly with
no catch-all arm; extracted candidates are re-validated through SPEC-0001 before
publication and a validation failure becomes a numerical failure rather than an
optimality claim; a pre-cancelled solve returns interrupted without creating
native state; limits and interruptions never satisfy `proves_completion`; binary
bounds intersect [0,1] regardless of declared bounds; coefficients below the
native small-matrix threshold are rejected instead of being silently dropped; a
basis is bound to a canonical-model fingerprint, so changed data under an
unchanged `model_id` is rejected.

Resolved review findings during implementation:

- The workspace `unsafe_code = "forbid"` made ADR-0003's native boundary
  unimplementable: `forbid` cannot be relaxed by an inner crate
  (`E0453 overruled by previous forbid`). optimizer-highs now declares its own
  `[lints.rust]` block with `unsafe_op_in_unsafe_fn` denied.
- `serde_json` serializes a nonfinite `f64` as `null`, which is indistinguishable
  from an absent field, so SPEC-0002's absent-not-null rule cannot rely on a
  serializer error. Records omit absent measurements and reject nonfinite ones
  explicitly as numerical failures.
- The stub adapter's pre-cancellation path required a provisioned library, which
  contradicted requirement 6. The check now precedes native dispatch and is
  answered identically with or without the library. Found by running the gate
  with the library deliberately absent.
- A no-op `.max()` in bound conversion and an unfulfilled lint expectation were
  caught by Clippy and removed.

Deferred and recorded rather than hidden: sanitizer runs over repeated native
lifecycles are not yet in the gate; presolve, scaling and reoptimization remain
Stage 5 work; owned search remains C2.

## Roadmap redesign (2026-09-09)

Objective: replace the narrow M0-M6 implementation sequence with the
architecture-driven C1-C7 capability roadmap in implementation-plan.md.

Status: complete; plan and backlog metadata synchronized.

Acceptance gate: roadmap is decision-complete, preserves M0/M1 evidence, keeps
HiGHS as the first replaceable backend, defines executive/extension/SDK/GPU
gates, and bash tools/check.sh reaches the required gate.

Evidence: implementation-plan.md, state/backlog.yaml, README.md, and CHANGELOG.md
now describe C1-C7 and the next dependency-ready task is C1. `git diff --check`
passes. `bash tools/check.sh` reaches preflight but cannot start Cargo because
the environment cannot create its sandbox namespace; no Rust checks were waived.

## M2 Backend Contract and Implementation (2026-09-09)

Objective: implement the approved M2-M6 plan sequentially, starting with the
HiGHS backend contract, safe lifecycle, validated solving and reproducible records.

Status: superseded; see the C1 record at the top of this file. The M2-M6 sequence
was replaced by the evidence-staged roadmap, and this objective was delivered as
C1 under the same SPEC-0002 and ADR-0003 contracts.

Acceptance gate: accepted SPEC-0002 and supporting ADR; standalone HiGHS
differential LP/MILP tests, explicit statuses, cancellation/limits, warm starts,
lifecycle sanitizers, structured records, and bash tools/check.sh. Inspect and
fix review findings before committing.

Expected changes: optimizer-highs, core solve contracts, CLI, experiment schemas,
native build/validation tooling, tests, specifications, ADRs and project state.
Resource budget: CPU only, at most four workers, bounded deterministic
tests and benchmark batches of at most 30 minutes. GPU work will use one shared
host GPU lease at a time. Existing M0/M1 defaults remain unchanged.

Follow-up order under the current roadmap: C2 owned executive, C3 extension
runtime, C4 SDK/registry, C5 flow shop, C6 GPU feasibility, C7 adaptive research.
No remote publication is included.

## Local M1 Integration (2026-09-08)

Objective: merge the reviewed feat/model-validation branch into local main and
delete the feature branch after confirming its commits are retained.

Status: complete; local integration and feature-branch cleanup finished.

Acceptance gate: fast-forward integration preserves reviewed commit 27b1b3a;
bash tools/check.sh passes on main; the merged feature branch is deleted and the
worktree is clean after recording evidence. Expected changes: local Git refs and
this task record. Resource budget: CPU only, four Cargo workers, no GPU workloads.

Evidence (2026-09-08): main fast-forwarded from 9e6dc86 to reviewed tip 27b1b3a
without conflicts or history rewriting. git merge-base --is-ancestor confirmed
the reviewed tip is retained on main, and git branch -d removed the fully merged
feat/model-validation branch. No remote refs were changed.

The unchanged runtime passed the complete acceptance gate before integration,
as recorded below. Two post-merge attempts passed format, Clippy, all 29 Rust
tests, workspace build and rustdoc, then stopped because the RustSec advisory
database could not be fetched. These attempts do not constitute a new full-gate
pass; the successful pre-integration gate remains the full acceptance evidence.
The only additional tracked change is this integration record, validated with
the documentation/link builder and git diff --check before committing.

## Repeated Branch Review (2026-09-08)

Objective: review the complete feature branch against main, fix any substantiated
findings, and repeat until the final review has no unresolved actionable findings.

Status: complete.

Acceptance gate: inspect every changed runtime path and the SPEC-0001/ADR-0002
contracts, verify relevant regression coverage, and run bash tools/check.sh.

Expected changes: this review record and any bounded fixes supported by reproduced
failures. Resource budget: CPU only, at most four Cargo workers, deterministic
tests, no GPU workloads. Review base: local main at 9e6dc86; starting HEAD: 58df6bb.

Current finding: model validate panics with exit 101 when a model/candidate path
contains non-UTF-8 bytes because main uses env::args. Preserve native paths with
args_os and report malformed non-path text as an argument error. Expected fix:
CLI parsing, Unix path/error regression tests, specification and release notes.
Follow-up finding: incomplete/unknown model commands returned bare usage without
the required argument category. Add a categorized dispatch error and regression.

Evidence (2026-09-08): both new regressions failed before their fixes and pass
afterward. Native model/candidate filenames retain their OS representation;
non-UTF-8 command, flag and tolerance text returns an argument error with exit 2.
Incomplete and unknown model commands now return the same error category.
Unix regressions cover real non-UTF-8 filenames, successful reports and missing
files. Specifications, tutorial, changelog and regression instructions agree.

The final complete bash tools/check.sh gate passed: format, warnings-as-errors
Clippy, 29 Rust tests, workspace build, rustdoc, cargo-deny, artifact validation,
8 Python tests, 36-page documentation/link validation and bootstrap smoke.
Temporary RustSec advisory-fetch failures recovered; no checks were waived.
Cargo preflight checks also passed for missing Cargo (exit 127 with a diagnostic)
and the rustup-only PATH fallback to the pinned Rust 1.93.1 toolchain.

Final review against local main at 9e6dc86534de2efa414205752ca58d7584976052
found no unresolved actionable findings. Coverage included strict JSON parsing,
canonical model construction, candidate coverage, arithmetic and tolerance
contracts, report output, CLI errors, dependencies, specifications and fixtures.
The existing independent dense oracle covers 18,522 evaluations and the f64
round-trip suite covers 968 values. Resource use remained CPU-only with four
Cargo workers; scope remains M1. Commit after acceptance, then rerun bootstrap
smoke to record the clean committed revision.

## M1 Review Contract Fixes (2026-09-08)

Objective: reject alternate JSON representations for all model/candidate input
types and return categorized CLI I/O errors when report output fails.

Status: complete.

Acceptance gate: regressions for positional records, object-wrapped enums,
and failed stdout writes; full bash tools/check.sh under SPEC-0001 and ADR-0002.

Expected changes: optimizer-core document parsing, optimizer-cli report output,
contract tests, minimized fixtures, specification clarifications, changelog,
and this task record. Resource budget: CPU only, four Cargo build workers,
bounded deterministic tests, no GPU workloads.

Evidence (2026-09-08): new regressions reproduced accepted alternate JSON forms
and exit 101 on failed stdout before their fixes. Public record types and tagged
bounds now reject positional arrays; domain/objective enums require strings.
Direct and nested parsing tests pass, preserving unknown/duplicate-field rejection
and f64 round trips. CLI tests verify categorized io errors and exit 2 for /dev/full
and closed pipes in structural and candidate modes. Output writes and flushes
are fallible; the specification clarifies that delivered bytes cannot be retracted.

The complete bash tools/check.sh gate passed: format, warnings-as-errors Clippy,
26 Rust tests, workspace build, rustdoc, cargo-deny, artifact validation, 8 Python
tests, 36-page documentation/link validation, and bootstrap smoke. No checks were
waived. Rust 1.93.1, four Cargo workers, and CPU-only simulations were used.
Minimized JSON fixtures and reproduction instructions are in tests/regression/.
Both review findings are resolved; no dependency or numerical-policy changes.

## Commit and Branch Review (2026-09-08)

Objective: validate and commit the pending acceptance-script diagnostic change,
then review the complete feature branch against local main in PR style.

Status: complete; committed as 4981aef and reviewed against local main.

Acceptance gate: run bash tools/check.sh before committing; inspect the complete
main-to-branch diff against SPEC-0001 and ADR-0002 and report actionable findings.

Expected changes: the pending tools/check.sh change and this task record.
Resource budget: CPU only, at most four Cargo build workers; no GPU workloads.

Evidence (2026-09-08): the complete bash tools/check.sh gate passed with Rust
1.93.1 and four Cargo workers: format, Clippy, 22 Rust tests, workspace build,
rustdoc, cargo-deny, artifact validation, 8 Python tests, 36-page documentation
build/link validation, and bootstrap smoke. No checks were waived. Review found
alternate JSON representations and panicking stdout writes, resolved by the M1
review contract fixes above. The comparison base was local main
at 9e6dc86534de2efa414205752ca58d7584976052 (also origin/main locally).

## Current diagnostic fix (2026-09-08)

Objective: make the acceptance gate locate the repository-pinned Rust toolchain and report executor failures clearly.

Status: complete.

Acceptance gate: shell syntax and toolchain preflight behavior pass; existing Rust gate remains unchanged after Cargo is resolved.

Evidence (2026-09-08): `bash -n tools/check.sh` passed. With Cargo absent, the gate exits 127 with an actionable diagnostic instead of an opaque `command not found`; with the pinned toolchain bin directory available, the existing Rust checks remain the executed gate.

Expected changes: tools/check.sh and this task record.

Resource budget: CPU only; no GPU workloads.


Objective: implement M1 core models, candidate validation, versioned JSON, and CLI.

Status: complete.

Acceptance gate: accepted SPEC-0001 and ADR-0002; independent property/exhaustive
model tests, serialization and numerical boundary tests, CLI contracts, and
the complete bash tools/check.sh gate. Commit locally after acceptance.

Expected changes: optimizer-core, optimizer-cli, model fixtures/examples,
specification and ADR, current scope/status documentation, changelog, task state.
Resource budget: CPU only, at most four Cargo build workers, bounded deterministic
tests; no GPU workloads. Existing smoke seeds and configuration remain unchanged.

Evidence (2026-09-08): accepted SPEC-0001 and ADR-0002 preceded implementation.
The complete bash tools/check.sh gate passed after the final runtime/test edits:
format, warnings-as-errors Clippy, 22 Rust tests, workspace build, warnings-as-errors
rustdoc, cargo-deny advisories/bans/licenses/sources, artifact schema/provenance,
8 Python artifact tests, 36-page documentation/link build, and bootstrap smoke.
No checks were waived. The 14 new Rust contracts include 18,522 independent dense
oracle evaluations, generated model ordering properties, 968 finite f64 values
round-tripped through both model and candidate JSON, numerical/domain boundaries,
edge-model fixtures, CLI exit/report behavior, and exact 16 MiB file boundaries.

Resolved regression: Serde internally tagged unit variants accepted an unknown
field on infinite bounds. Strict bound deserialization now rejects the minimized
fixture in tests/regression/infinite-bound-extra-field.json; its contract test passes.

Environment: Rust 1.93.1 and cargo-deny 0.19.0 under /tmp/ai-optimizer-cargo,
RUSTUP_HOME=/tmp/ai-optimizer-rustup, Python tooling /tmp/ai-optimizer-venv,
CARGO_BUILD_JOBS=4. Core contracts completed in 0.17 s and CLI model contracts in
0.78 s in the final gate. Work was CPU-only; lease tests used temporary locks and
simulated jobs. Cargo.lock only adds local core/CLI dependency edges; no external
package versions changed. Serde JSON's float_roundtrip feature preserves f64 input.

Provenance: the precommit gate's smoke honestly records a dirty working tree.
The local feature commit is followed by a smoke rerun for clean revision-bound
provenance at artifacts/bootstrap-smoke.json. This remains CLI startup evidence,
not solver or GPU performance. No push or hosting changes are part of M1.

Follow-up: M2 is dependency-ready. Write SPEC-0002-backend-contract.md before
implementing HiGHS lifecycle, status mapping, cancellation, limits and solve records.
No M2 behavior is implemented here.

## Previous Repository Synchronization

Objective: synchronize the project to https://github.com/liuyumou/OptForge.git.

Status: complete.

Acceptance gate: origin points to the requested repository; main is pushed with
upstream tracking; the remote main revision matches local HEAD; the worktree is
clean. Preserve existing history and validate updated documentation.

Expected changes: Git remote/tracking configuration and repository hosting/task
records. Resource budget: bounded CPU checks and Git operations; no GPU work.

Evidence: the original main history was pushed successfully and main now tracks
origin/main. The complete tools/check.sh gate passed, including 8 Rust tests,
8 artifact tests, dependency policy, documentation, and smoke validation. Hosting
records identify the remote. The synchronization includes this documentation
update; remote revision equality and clean worktree are checked after its push.

## M0 Bootstrap Evidence

Objective: implement M0 from implementation-plan.md.

Status: complete.

Acceptance gate: pinned Rust workspace builds; format, Clippy, tests, dependency
policy, rustdoc, documentation links/build, schemas, and benchmark smoke pass.
GPU discovery must report available UUIDs or an explicit unavailable state.
Simulated jobs must serialize and release ownership after cancellation or exit.

Expected changes: repository bootstrap, crates, tools, schemas, CI, documentation,
examples, benchmark fixtures, and task state. Preserve both original plans.

Resource budget: CPU-only builds and bounded tests; GPU discovery only, no kernels.
One developer, one bounded milestone. M1-M6 remain dependency-ordered backlog.

Evidence before initial commit: Rust workspace build, format, warnings-as-errors
Clippy, 8 Rust unit/integration tests, rustdoc, cargo-deny (advisories, bans,
licenses, sources), 8 Python artifact tests, schema/provenance validation, shell
syntax, and a 33-page documentation/link build passed. Discovery returned all
three expected physical GPU UUIDs without launching kernels.

Clean-checkout acceptance: the complete tools/check.sh gate passed on revision
a628c0c8605dd2434cdf7fd775fae85e96423a31 in an independent local clone at
/tmp/ai-optimizer-m0-verification. It rebuilt every crate and generated a validated
measured smoke record with dirty=false. No acceptance checks were waived.

Verified lease cases: competing-process timeout and serialization, normal release,
SIGINT while waiting, SIGTERM while holding, SIGKILL recovery, and interoperability
with the shell runner's flock primitive. All were CPU simulations. Inventory
reported two RTX 5090 devices and one RTX PRO 6000 by their expected UUIDs.

Artifacts: the clean-clone record is at
/tmp/ai-optimizer-m0-verification/artifacts/bootstrap-smoke.json. The workspace
runner can reproduce artifacts/bootstrap-smoke.json. Records measure CLI startup
only; no solver or GPU performance result is claimed.

Environment: Rust 1.93.1 and cargo-deny 0.19.0 were installed under
/tmp/ai-optimizer-cargo with RUSTUP_HOME=/tmp/ai-optimizer-rustup. Documentation
and schema tooling use /tmp/ai-optimizer-venv. Hosting workflows are configured
but were not run on GitHub; remote protection and GPU-runner provisioning remain
external setup, as documented in state/known-failures.md.

Follow-up: M1 is dependency-ready. Write SPEC-0001-model-and-validation.md, then
implement the original-model numerical authority boundary and its independent
property/exhaustive tests. No M1 behavior has been implemented as part of M0.

## Toolchain recovery (2026-09-09)

The pinned Rust toolchain was present under `/tmp/ai-optimizer-cargo` and
`/tmp/ai-optimizer-rustup` but absent from the default PATH. `tools/check.sh`
now discovers those locations and sets `RUSTUP_HOME` automatically, and the
search order is overridable through `AI_OPTIMIZER_CARGO_HOME` rather than being
hardcoded to one machine's layout.

Superseded detail: this record previously stated that the gate stopped at
artifact validation for a missing Python `jsonschema`. That diagnosis is stale.
`jsonschema` is present and artifact validation passes; the missing module was
`Markdown`, which `tools/requirements.txt` already pins. The gate now checks both
imports as a precondition, so this class of failure is reported in seconds rather
than after several minutes of compilation. C1 native HiGHS and solve CLI
implementation are now complete; see the C1 record at the top of this file.
