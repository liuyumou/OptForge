# Project Status

The repository implements the C8 local extension registry on top of the C5
flow-shop scheduling slice, the C4
agent-independent run surface, C3
extension safety, C2 owned branch-and-bound search, C1 pinned HiGHS solving, M1
model and candidate validation and the M0 bootstrap. Acceptance
evidence is recorded in [active task](../state/active-task.md).

| State | Features |
| --- | --- |
| Implemented | Original linear models, Rust/JSON/CLI candidate validation with explicit tolerances, backend-neutral solve contract, pinned CPU HiGHS LP/MILP solving with validated incumbents and reproducible records, owned branch-and-bound executive with budgets, cancellation and proof completion, extension runtime with declared authority, validated candidate producers and checked search advisers, typed extension failure records, CLI search over the executive with provenance-bearing run records and re-execution verification, flow-shop instances with an independent makespan recurrence, a big-M-free positional encoding, deterministic NEH and insertion producers, a frozen generated Taillard development subset and CLI scheduling commands, a local extension registry resolving a named identity to an extension this build provides with checked licenses, authority, compatibility, requirements and promotion, a reusable conformance suite and its record, workspace, CLI hello, GPU discovery, simulated leases, artifact schemas, CI and documentation tooling |
| In progress | None |
| Planned | GPU feasibility and adaptive research (C6/C7), Python SDK (C9), comparative runner (C10) |
| Experimental | None enabled |
| Deprecated | None |

Solve records recompute objectives and violations independently of the backend. A
backend optimality claim holds under the recorded numerical settings; it is not an
exact certificate, and a limit, interruption or failure is never reported as a
completed proof. Owned search adds a second, distinct claim: proven optimality
means the executive exhausted its own node tree with every prune justified by a
relaxation that itself proved optimality. A search whose relaxation hit a limit
forfeits that claim and says so. Extensions may propose candidates and search
actions; the core validates every one of them, and no extension can forfeit a
proof, end a search or change its outcome. Extension containment covers panics,
not a process abort. A search is recorded with the revision, model fingerprint
and input hashes needed to repeat it, and verification re-runs that search from
the record alone rather than trusting its stored result; agreement establishes
determinism on one host, never optimality, and a forfeited search stays forfeited
after it verifies. No Python SDK, CUDA kernel, dynamically
loaded native extension, checkpoint restart or comparative experiment runner is
available, cross-host reproducibility is untested, and no solver performance
claim is made.

The registry decides which extensions a search may consult and records why. It
resolves a named identity to an extension this build already provides and refuses
one it does not; it never loads a separately distributed native component, which
would need a second unsafe boundary ADR-0003 prohibits. An entry is a claim and the
extension's own declaration is authoritative, so a disagreement between them is
refused in both directions rather than reconciled. Resolution is total: a search
either registers every extension its configuration named or does not start.
Promotion means a recorded conformance suite passed, checked against the cited
record's bytes; it never means the extension improves a search, which stays a C7
question and is deliberately unmeasured. A registry-backed run record is now
verifiable by re-execution, which is the gap C5 recorded.

The flow-shop slice adds the first application workload whose objective has a
second, independent computation: a makespan recurrence that shares no code with
anything proposing a schedule. An instance is encoded into an ordinary model with no
big-M constant, so every earlier contract carries it unchanged. It claims
correctness, not tractability: the encoding's linear relaxation is weak, proven
optimality is asserted only for tiny instances checked against exhaustive
permutation enumeration, and the frozen Taillard subset carries feasibility and
determinism evidence only. No best-known bound is committed as a threshold.

See the [M1 contract](../docs/specifications/SPEC-0001-model-and-validation.md),
[backend contract](../docs/specifications/SPEC-0002-backend-contract.md),
[solver executive contract](../docs/specifications/SPEC-0003-solver-executive.md),
[extension runtime contract](../docs/specifications/SPEC-0004-extension-runtime.md),
[run surface contract](../docs/specifications/SPEC-0005-run-surface.md),
[flow-shop contract](../docs/specifications/SPEC-0008-flow-shop.md),
[extension registry contract](../docs/specifications/SPEC-0009-extension-registry.md),
[backlog](../state/backlog.yaml) and
[implementation plan](../implementation-plan.md) for evidence stages and dependencies.