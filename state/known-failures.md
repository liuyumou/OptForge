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

## Local extension registry is not implemented

SPEC-0005 excludes the registry. `search_with_extensions` takes an in-memory
`&[Registration]` slice for one search, and the CLI has no mechanism to populate
it, so the run surface refuses a configuration naming an extension policy as
unsupported rather than running the search without the extension it names. That
refusal is the seam the registry fills; it is a stated boundary, not a silent
omission. Registration, promotion, licenses, compatibility, authority basis and
inter-extension interactions all remain unspecified, and SPEC-0004 already parks
the corresponding declaration fields there. Reproduction: run
`optimizer search` with a configuration whose `extensions` list is non-empty.
Next step: implement the accepted
[SPEC-0009](../docs/specifications/SPEC-0009-extension-registry.md) contract under
backlog item C8. The contract exists; the behavior does not yet.

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

## Scheduling run records cannot be verified with a producer registered

`optimizer verify` re-executes a record through the extension-free search entry
point, so a record whose configuration names an extension policy is refused as
unsupported rather than re-run. This is deliberate and is the same rule SPEC-0005
requirement 14 already applied to `optimizer search`: re-running without the named
producer would reproduce a search the record does not describe, and its node
counters would differ for that reason alone. Reporting that as divergence would
blame the record for a limitation of the verifier.

The consequence is real and worth stating: a scheduling run performed *with* the NEH
producer is not verifiable by re-execution today, only one performed without it.
Reproduction: `optimizer schedule solve` with a configuration naming
`flow-shop-neh`, then `optimizer verify` on the resulting record. Next step: the
seam is the extension registry under C8, now specified as
[SPEC-0009](../docs/specifications/SPEC-0009-extension-registry.md) requirement 19,
which is what will let a verifier reconstruct the producer a record names. Until
that behavior exists this limitation stands.

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
