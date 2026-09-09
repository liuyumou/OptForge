# Active Task

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
