# Known Failures and Limitations

No known implementation failure has been accepted as a waived gate.

## Source planning references

The preserved ai-native-optimizer-plan.md references optimizer-survey.md and
llm-or-survey.md from another session; neither is present. Reproduction:
inspect its Background links. Next diagnostic step: recover those source surveys
if research work needs them. The maintained documentation book excludes the two
original planning inputs from recursive link validation.

## External configuration

The origin remote is https://github.com/liuyumou/OptForge.git. Protected main,
labeled GPU runner provisioning, and artifact retention still require hosting
administration. Next step: configure these settings separately from Git syncing.

## Deferred hardware evidence

GPU support queries inventory only. CUDA sanitizer and kernel equivalence tests
remain gated on C6 implementation. HiGHS differential tests are implemented and
passing under C1; see [active task](active-task.md). No solver performance or
hardware claim is made.

## Intermittent advisory database fetch

`cargo deny check advisories` fetches the RustSec database from github.com, which
has repeatedly been unreachable in this environment. The acceptance gate now
falls back to the cached database rather than failing spuriously or skipping the
check; an absent cache is still a hard failure. Reproduction: run
`cargo deny --locked check` without network egress to github.com. Next step: seed
the advisory database in CI so the check does not depend on egress at gate time.

## Native acceptance can be skipped explicitly

`AI_OPTIMIZER_SKIP_NATIVE=1 bash tools/check.sh` runs without the pinned HiGHS
build and prints a prominent warning that native acceptance was not covered. Such
a run is not a complete acceptance gate pass and must not be recorded as one.

## Sanitizers not yet in the gate

SPEC-0002's acceptance list mentions running repeated native lifecycle tests under
available sanitizers. The repeated-lifecycle test exists and passes, but no
sanitizer run is part of `tools/check.sh` yet. This is an uncovered part of the C1
acceptance list, recorded rather than waived silently.

## Extension containment covers panics only

The C3 extension host runs extensions in-process and contains panics with
`catch_unwind`. It cannot contain a process abort, stack exhaustion or a memory
fault, and it enforces no per-extension memory budget. A hostile extension can
therefore still take down the process, even though it cannot affect a search's
mathematical conclusion. Reproduction: an extension calling
`std::process::abort` ends the test process. Next step: process-isolated
workers, which SPEC-0004 defers and which need their own decision record. The
host also requires the unwind panic strategy; no repository profile sets
`panic = "abort"`, and nothing currently pins that.

## Python SDK is deferred with a stated blocker

SPEC-0005 delivers the C4 run surface through the CLI and defers the Python SDK
to its own specification. The blocker is concrete rather than a matter of
sequencing: pyo3 expands to unsafe code, the workspace sets
`unsafe_code = "forbid"`, and ADR-0003 permits unsafe only inside
optimizer-highs. An in-process binding therefore requires a decision record
amending ADR-0003, plus maturin packaging and a Python test layer in the gate.
AGENTS.md also states that Python under tools/ is validation tooling and not the
SDK. Reproduction: add a pyo3 dependency to any runtime crate and build. Next
step: decide the SDK's shape in its own specification, now backlog item C9; a
subprocess wrapper over the versioned run records needs no unsafe boundary and is
the cheaper option if an SDK is wanted before that decision.

## Resolved: the local extension registry is implemented

This was recorded from C4 through C5 and is now closed by C8 under
[SPEC-0009](../docs/specifications/SPEC-0009-extension-registry.md) and
[ADR-0008](../docs/decisions/ADR-0008-registry-resolution.md). `optimizer search`,
`optimizer verify` and `optimizer schedule solve` resolve a configuration's
extension policy through a registry document the caller names with `--registry`,
and registration, promotion, licenses, compatibility, authority basis and
inter-extension requirements are all checked rather than parked. The declaration
fields SPEC-0004 deliberately left unread — data needs, hardware and dependencies —
now have checked meanings.

Retained as the limits the implementation actually has, each recorded rather than
absorbed:

- A run record names each extension's identity and version but not the registry
  document that resolved it, so licenses and promotion state are auditable through
  the registry rather than through the record. Closing this needs a run-record v2
  and an ADR, because SPEC-0005 makes a change to the compared fields breaking.
- An extension is identified by identity and version, so two different builds of one
  version are indistinguishable. This is the same limitation already recorded for
  the pinned native library, and it is why the summary-difference diagnostic exists.
- The registry resolves only extensions this build provides. It cannot name a
  dynamically loaded native extension, and it refuses an entry requiring a GPU;
  both refusals are explicit and both remain recorded below.
- Provider construction happens before SPEC-0004's guarded host exists, so a
  provider that panics while constructing an extension is outside the
  panic-containment claim. The host's containment of `declare`, `propose` and
  `advise` is unchanged.
- Conformance establishes contract invariance only. A passing record means the
  contract held, never that the extension improved a search, which stays a C7
  question.

## Resolved: a scheduling run record with a producer registered now verifies

Recorded from C5 and closed by C8. `optimizer verify` previously re-executed every
record through the extension-free search entry point, so a record whose
configuration named an extension policy was refused as unsupported: re-running
without the named producer would have reproduced a search the record does not
describe, and its node counters would have differed for that reason alone.

Under [SPEC-0009](../docs/specifications/SPEC-0009-extension-registry.md)
requirement 19 the verifier reconstructs the producer a record names, through a
registry the caller passes with `--registry`. Reproduction of the closed case:
`optimizer schedule solve` with a configuration naming `flow-shop-neh` and a
registry, then `optimizer verify` on the resulting record with the same registry;
it agrees and exits 0. The gate re-executes such a record across a commit boundary
in `tools/verify_committed_record.py`. A record naming an extension policy with no
`--registry` is still refused, which is requirement 18 rather than a limitation.

## Resolved: a run record's identifier no longer depends on the clock

`optimizer search` built `record_id` as `run-{model_id}-{elapsed_ms}` and
`optimizer schedule solve` built `schedule-{model_id}-{elapsed_ms}`. The
identifier was a pure function of a measurement the project excludes from meaning
everywhere else: SPEC-0005 requirement 12 fixes elapsed time as diagnostic rather
than contractual, and verification ignores it. Two runs of the same search on the
same machine got different identifiers whenever the host spent a different number
of milliseconds, and two unrelated searches that took equally long collided.

Found by the C8 clean-checkout verification, which is the case it takes to see it:
the requirement 17 contract compares a record produced with a registry against one
produced without, and both runs completed in 0 ms on a warm working tree but in 0
and 1 ms on the clean clone.

Closed by SPEC-0005 requirement 1a, which now states that an identifier is derived
only from what the record describes. Both commands derive it from the SHA-256
digests of the input documents the record already carries, so a different model or
a different configuration yields a different identifier and a repeated run yields
the same one. Two runs of the same inputs sharing an identifier is the intended
reading rather than a residual collision: the identifier names the inputs, and
whether two such runs agree is what `optimizer verify` answers. Reproduction of the
closed case: run `optimizer search` twice over the same model and configuration and
compare the two `record_id` values; the contract test asserts this and was shown to
fail with the old derivation reinstated.

## C8 requirements whose acceptance tests are thinner than the specification

SPEC-0009's acceptance section describes cases that the implementation does not
yet assert. These are recorded rather than quietly downgraded, because the
specification is accepted and its own test mapping is the thing out of date.

- Requirement 14 says resolution "MUST NOT ... construct" a refused extension, but
  the declaration-mismatch and role-mismatch paths necessarily construct the
  extension and call `declare` in order to discover the disagreement. The
  construction counter is therefore non-zero on those paths by design. The rule
  holds as written only for the refusals decided before construction — an unmet
  data requirement and a gpu hardware requirement — and those are the two the
  tests assert it against. Next step: narrow requirement 14's wording to the
  refusals it can actually govern, which is a specification correction rather than
  a code change.
- Requirement 20's nondeterministic-record refusal has no test. Neither example
  extension declares nondeterminism, so producing such a record needs a fixture
  that does not exist in the CLI's provider table.
- Requirement 20's other half, refusing a record whose named extension resolves to
  a *different version than the record's summary states*, may not be reachable at
  all: resolution already forces the declaration and the entry to agree on version,
  and a summary's version was itself copied from a declaration. Both tests aimed at
  this rule restamp the registry entry and are refused earlier, by the declaration
  check. Reproduction: `crates/optimizer-cli/src/search.rs` compares
  `declaration.version` against `summary.version` after resolution has already
  equated the first with the entry's. Next diagnostic step: determine whether the
  branch is dead and either remove it or find the input that reaches it; do not
  delete it on inspection alone, because it guards a record re-executing against a
  different extension.
- Requirement 21's positive case — a run that agrees while reporting an extension
  summary difference as a diagnostic note — is asserted only in its negative form,
  that no difference is reported when none exists. `ExtensionDifference` has no
  unit test.
- Requirement 22's forfeited registry-backed record is not produced by any test.
  The forfeiture rule itself is covered without a registry under SPEC-0005.
- Requirement 18 is asserted for `optimizer schedule solve` but not for
  `optimizer search --registry` with a non-empty policy, because both extensions
  this build provides are flow-shop producers that cannot be constructed from a
  bare model. A search-command case needs a provider that takes no auxiliary
  instance.
- Requirement 1's document-level missing-field refusal and requirement 3's
  duplicate-field rejection are covered for entries but not for the document
  itself.

## Verification assumes an unchanged native library

`optimizer verify` re-runs a search and compares the two records field by field. A
divergence now reports whether the backend library, source revision or compiler
differs from the record's, so a changed engine is distinguishable from a wrong
result *in the diagnostic*. What remains unresolved is whether such a mismatch
should ever be **tolerated**: verification still fails, because deciding otherwise
would change the meaning of agreement and needs a new record version plus an ADR
under SPEC-0005's compatibility rule. Cross-host reproducibility is separately
untested, because floating-point behavior and library builds may differ between
machines, and closing it needs a second machine in CI rather than local code.
Agreement therefore remains evidence of determinism on one host over time, which
is what ADR-0006 claims and no more.

## Checkpoint restart is still unimplemented

C2 defines and serializes `Checkpoint` and SPEC-0003 states that restart is not
implemented. The C4 run surface does not add a restart entry point either, so a
long search cannot be resumed and a run record cannot be continued. Verification
re-runs from the beginning under the record's own budgets. Reproduction: no CLI
command consumes a checkpoint. Next step: restart needs its own acceptance
evidence before any public entry point exists.

## The flow-shop encoding is correct but weak

Two limits recorded before implementation, both confirmed by it.

The positional encoding is exactly linear and its optimum equals the instance's
minimum makespan by construction, but its linear relaxation is weak and the model
is quadratic in the job count: a 20-job, 5-machine Taillard instance is 400 binary
variables. The executive is not expected to prove optimality at that size, so the
specification confines proven-optimal claims to tiny instances checked against
exhaustive permutation enumeration and confines the frozen subset to feasibility,
determinism and validated-incumbent evidence. This is a stated scope boundary, not
a defect, and it is why requirement 26 forbids recording a performance claim.
Reproduction: encode any 20-job instance and run the executive without a budget; a
node-limited run over `ta001` is asserted in the CLI contracts to report its limit
rather than an optimum. Next step: a stronger formulation or a scheduling-specific
bound would each need its own contract, and the evidence justifying one does not
exist yet.

Permutation schedules are also not optimal for the general flow shop beyond three
machines, confirmed by direct enumeration on a 3-job, 4-machine instance where the
best permutation schedule costs 50 and the best general schedule costs 47. The
permutation restriction is part of the problem C5 solves rather than an
approximation it makes, and nothing in the slice should be read as solving the
general flow shop.

## Dynamically loaded native extensions are not implemented

SPEC-0004 specifies host-contract-version negotiation and implements it in safe
Rust, but the versioned C-compatible boundary for separately distributed native
components is deliberately absent. It needs a second unsafe boundary, which
ADR-0003 prohibits outside optimizer-highs, so it requires an amending decision
record plus its own lifecycle, ABI-stability and crash-isolation evidence. This
is a recorded deferral, not a gap discovered late.

[SPEC-0009](../docs/specifications/SPEC-0009-extension-registry.md) does not change
this. Its registry *resolves* a named identity to an extension the build already
provides and refuses one it does not, so the registry is now the obvious place a
dynamically loaded extension would be named and deliberately cannot name one. That
makes the deferral more visible rather than closing it.
