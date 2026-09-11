# ADR-0007: Flow-Shop Correctness by Independent Evaluation

Status: accepted
Owner: scheduling application
Introduced: C5
Last reviewed commit: 5157786
Supersedes: none; ADR-0001 through ADR-0006 remain in force

## Context

C1 through C4 are complete. The engine can solve a model, own a search, host an
extension and reproduce a run from its record, and every one of those contracts is
checked against something independent: C1 against a separately built HiGHS
executable, C2 against brute-force enumeration of an assignment box, C3 against an
extension-free run, C4 against a re-execution. What none of them has is an
application whose objective can be computed from a definition rather than from
another solver.

The [implementation plan](../../implementation-plan.md) names the flow shop as the
first application family and states the remaining Stage 3 evidence as exhaustive
tiny instances, independent evaluator agreement, validated incumbents and a frozen
Taillard development subset with provenance. Stage 4's entry condition is a
workload with independent evaluation, so what this slice decides is what
"independent" means before any research is measured on top of it.

Three decisions have to be made before code exists, and each is one a later
implementation could get quietly wrong in a way tests would not obviously catch.
How the instance reaches the solver. Which computation is the authority on a
schedule's makespan. And what a frozen benchmark subset actually consists of.

## Decision

Implement [SPEC-0008](../specifications/SPEC-0008-flow-shop.md).

The makespan recurrence is the authority, and it is implemented once, separately
from everything that proposes a schedule. A heuristic's claimed makespan is never
read; a candidate's objective is recomputed. This mirrors the rule ADR-0005 fixed
for extensions, where a producer's asserted objective has no standing, and extends
it: here the recomputation can be checked against a closed-form definition rather
than against the same linear algebra that produced the candidate. The evaluator
depends on neither the encoding nor any producer, which is what makes agreement
between it and the model's recomputed objective evidence rather than a tautology.

An instance reaches the solver as a genuine M1 model through a positional encoding:
binary variables place a job in a position, continuous variables carry completion
times, and the constraints are assignment rows plus the recurrence's two
predecessor inequalities. The formulation is exactly linear and introduces no
big-M constant, so the claim that the model's optimum equals the instance's minimum
makespan holds by construction rather than by a numerical margin. This was verified
before the decision was recorded: over three hundred randomly generated instances,
the encoded optimum for a fixed permutation equals the recurrence, and the minimum
over all permutations equals brute-force enumeration.

Encoding into the existing model type rather than building a scheduling solver is
the load-bearing structural choice. Because the result is an ordinary
`optimizer_core::Model`, the entire existing stack applies unchanged:
`Model::evaluate` validates a schedule, the C2 executive searches, the C3 host
admits producers, and a run record verifies by re-execution under SPEC-0005 with no
new record type, no new schema version and no change to what agreement means. A
separate scheduling engine would have needed all of that rebuilt, and every
rebuilt piece would have been a second place for a proof claim to be made
incorrectly.

The two heuristics named in the specification, NEH and insertion, are candidate
producers under SPEC-0004 and nothing more. They are registered by a caller, never
loaded by default, and hold no authority. They are specified as deterministic
because reproducibility requires it, not because determinism makes them good.

The frozen development subset is generated from published seeds rather than
downloaded. Taillard's generator is documented in the paper the benchmark protocol
already cites, and an independent implementation of it reproduces his published
first instance exactly, which was checked against the OR-Library transcription
before this record was written. The generated instance documents are committed
alongside their seeds and checksums, so the manifest records how each instance was
produced and the artifact validator confirms the committed bytes still match. The
subset is small and its split is development.

What this slice does not claim is part of the decision. The positional encoding's
linear relaxation is weak, and a twenty-job instance is four hundred binary
variables, so the executive will not prove optimality at Taillard sizes.
Proven-optimal assertions are therefore confined to tiny instances where
exhaustive permutation enumeration is the oracle, and on the frozen subset the
assertions are feasibility, determinism and validated incumbents. No best-known
bound is committed, because a committed bound is an acceptance threshold and the
benchmark protocol requires a decision record and an experiment record before one
exists.

Existing seeds, tolerances, thresholds, splits and solver defaults do not change.
This slice adds an application and no numerical policy.

## Alternatives

A disjunctive big-M formulation, with sequencing variables between job pairs and
precedence constraints activated by a large constant, is the other standard
encoding and is rejected because its correctness depends on the constant. Too small
a value silently excludes optimal schedules, and too large a value degrades the
relaxation and invites tolerance-dependent misclassification. Both failures are
numerical rather than structural, which makes them exactly the class this project's
contracts exist to refuse. The positional formulation needs no such constant.

A dedicated combinatorial branch-and-bound over permutations, with a
scheduling-specific bound, would almost certainly solve larger instances than the
positional encoding does. It is rejected for this slice because it would bypass the
C1 through C3 interfaces the C5 scope requires, and because `RunRecord` embeds a
`SearchRecord` and cannot represent a search the executive did not perform. Adding
it would mean a new record type, a new schema and a new verification path, which is
a large amount of new authority to introduce alongside a first application. It
remains available later on its own contract, and the evidence that would justify
one does not exist yet.

Implementing the makespan recurrence inside the encoding, so that one piece of code
both built the model and evaluated schedules, would be less code and is rejected
because it destroys the independence that is the point. Two computations that share
an implementation agree by construction, and their agreement establishes nothing.

Letting a producer report its own makespan and trusting it would save a
recomputation per proposal and is rejected on the same grounds ADR-0005 rejected
it for extensions generally: a component that can assert an objective can assert a
wrong one, and the record would then carry a number no authority checked.

Downloading the Taillard instances at gate time, with checksum verification, is the
most literal reading of the benchmark protocol's download-tooling sentence and is
rejected on evidence. The canonical instance host did not respond from this
environment, and the advisory-database fetch is already a recorded intermittent
failure for exactly this reason. A gate that depends on a third-party host is a
gate that fails for reasons unrelated to the code. Generating from seeds published
in the cited paper is reproducible offline and strictly more transparent, because
the manifest then records the parameters that produced the data rather than only a
hash of bytes someone else served.

Committing the downloaded instance files instead of generating them was also
considered and is rejected as the weaker of the two: it records what the bytes are
but not how they arose, and CONTRIBUTING.md discourages committing datasets.
Generating and committing both, which is what this decision does, records the
derivation and still lets the validator check the bytes.

Vendoring a third-party scheduling library to cross-check the evaluator was
considered as an independence mechanism and is rejected because the recurrence is
four lines and a definition. A dependency would add supply-chain surface and policy
review to replace something the paper states directly, and the exhaustive oracle
over tiny instances is a stronger check than agreement with another implementation
of the same formula.

## Consequences

The engine gains an application whose objective has a second, independent
computation, which is the property Stage 4 research needs and the reason this slice
precedes it.

The encoding is quadratic in the job count, so model size grows quickly and the
executive's reach on this problem class is modest. This is stated plainly rather
than discovered later: nothing in this slice establishes that the engine is
competitive on flow-shop instances, and its acceptance evidence is built so that no
reader could take it as such.

Two computations of makespan now exist and must not drift. The exhaustive grid is
what detects drift, and it compares both against enumeration rather than against
each other, so a shared error cannot hide. A disagreement between them is specified
as a numerical failure rather than resolved in favor of either.

A scheduling run verifies through the existing C4 surface with no new record type,
so reproducibility is inherited rather than re-established. The corollary is that
changing the encoding breaks verification of older records even when the encoding
stays correct, because the run record's fingerprint is computed from the encoded
model. That is why the specification treats an encoding change as breaking.

The permutation restriction is part of the problem being solved, not an
approximation of a more general one. Permutation schedules are not optimal for the
general flow shop beyond three machines, which was confirmed by direct enumeration
on a small instance where the best permutation schedule is strictly worse than the
best general schedule. Nothing here should be read as solving the general flow shop.

The workspace gains a crate dependency edge from the scheduling crate onto the core
and, for the producers, onto the extension API. The producers live in their own
crate so that "a scheduling producer needs no engine-internal change" is
established by the workspace build in the same way ADR-0005 established it for the
example extensions, rather than asserted.

Job shop remains unimplemented and is gated on this slice's correctness evidence,
as the implementation plan already sequenced it.

## Implementation and Tests

Implementation in [optimizer-schedule](../../crates/optimizer-schedule/src/lib.rs)
over the [core model](../../crates/optimizer-core/src/lib.rs), the
[executive](../../crates/optimizer-solver/src/lib.rs) and the
[extension runtime](../../crates/optimizer-extension/src/lib.rs), with the frozen
subset recorded as a [benchmark manifest](../../schemas/benchmark-manifest-v1.schema.json)
and verified through the [gate](../../tools/check.sh). No behavior is implemented by
this decision record. Acceptance evidence is recorded in
[active task](../../state/active-task.md); this slice is not complete until its full
gate passes with native acceptance covered, the exhaustive permutation grid agrees
with the executive on the encoded models, and the generator is shown to reproduce
its published reference instance.
