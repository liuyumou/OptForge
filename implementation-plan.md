# AI-Native Optimizer Implementation Plan

This plan turns [ai-native-optimizer-plan.md](ai-native-optimizer-plan.md) into an
evidence-driven roadmap. It is organized by **evidence stage**: each stage states
what must be true to enter it, the work it contains, the falsifiable evidence that
closes it, and the artifacts that record that evidence. Capability numbers (C1-C7)
name work items inside the stages and are retained for
[state/backlog.yaml](state/backlog.yaml) dependency tracking.

A stage closes on evidence, not on completed code. Where evidence does not yet
exist, this document says so rather than implying it.

## Principles and invariants

- Rust owns runtime state, numerical authority, resource budgets, and extension boundaries.
- HiGHS is the first CPU backend and an independent reference, not the architecture.
- The engine runs with pinned configuration and installed extensions without an agent.
- Extensions declare capabilities and authority; the core validates candidates, actions, and proof claims.
- CLI, SDK, structured records, and a local registry are shared by humans and agents.
- GPU work is measured end to end, uses the shared one-GPU lease, and always retains a CPU fallback.
- Every behavior has a specification, acceptance tests, provenance, and a recorded failure path.

## Status summary

| Stage | Work items | State |
|---|---|---|
| 0. Foundation | M0 bootstrap, M1 model/validation authority | Complete |
| 1. Contract | C1 backend-neutral solve and HiGHS adapter | Complete |
| 2. Execution | C2 executive, C3 extension runtime | Complete |
| 3. Application | C4 run surface, C5 scheduling slice, C8 registry/SDK | C4 complete; C5 and C8 not started |
| 4. Research | C6 heterogeneous computation, C7 adaptive portfolios | Not started |
| 5. Hardening | Presolve, scaling, reoptimization, cuts, parallel search | Not started |
| 6. Reproduction | Independent reproduction, then release decisions | Not started |

Stages 0, 1 and 2 are complete, and Stage 3's reproducibility evidence is now
recorded rather than projected. Everything below that is a plan, and the
performance and learning claims in stages 4 and beyond are hypotheses, not
results. C2 establishes search correctness only, C3 establishes extension safety
only, and C4 establishes repeatability only; none makes a performance claim.

---

## Stage 0 — Foundation (complete)

**M0 — Repository and process bootstrap.** Rust workspace, pinned toolchain,
documentation and dependency checks, schemas, artifact provenance, GPU discovery,
and cancellable lease simulation, under SPEC-0000 and ADR-0001.

**M1 — Model and validation authority.** Original models, stable identifiers,
checked arithmetic, bounds/domains, objective recomputation, candidate validation,
tolerances, canonical JSON, and CLI diagnostics, under SPEC-0001 and ADR-0002.

*Evidence:* the M1 contracts include an independent dense oracle over 18,522
evaluations and 968 f64 round trips. Both stages' evidence is recorded in
[state/active-task.md](state/active-task.md).

## Stage 1 — Contract (complete)

**Entry condition:** M1 validation authority is green.

**C1 — Backend-neutral solve and session contract**, under
[SPEC-0002](docs/specifications/SPEC-0002-backend-contract.md) and
[ADR-0003](docs/decisions/ADR-0003-highs-backend.md).

Solve requests, backend capabilities, cancellation and resource limits, warm
starts, termination/status semantics, validated solution extraction, diagnostics,
and immutable solve records. Native handles stay inside the adapter crate. Backend
status, candidate feasibility, bound validity, and engine proof claims are distinct.

*Evidence:*

- The pinned HiGHS 1.11.0 CPU library is provisioned out of tree by
  `tools/setup_highs.sh` and linked through a private FFI boundary. The
  standalone executable is built from the same source as an independent reference.
- Differential agreement with that reference over LP, objective-offset, equality,
  ranged, MILP, and infeasible cases.
- All 18 native model statuses are mapped with no catch-all arm, so a HiGHS
  upgrade fails to compile rather than silently mis-classifying an outcome.
- Every extracted candidate is re-validated against the original model before
  publication; invalid native output is a numerical failure, never optimality.
- 58 Rust tests and 20 Python tests pass under `bash tools/check.sh`, with the
  native library required and a skip reported as uncovered acceptance.

*Gate met:* no backend failure, timeout, or interruption can be reported as proven
optimality. This is asserted directly by the limit, cancellation, and
termination-classification tests.

*Known limits, carried forward rather than hidden:* the adapter rejects
coefficients below the native small-matrix threshold instead of scaling the model;
presolve, scaling, and reoptimization are deliberately absent until Stage 5;
sanitizer runs over repeated native lifecycles are not yet part of the gate.

## Stage 2 — Execution

**Entry condition:** Stage 1 evidence holds and M1 behavior remains green.

**C2 and C3 are implemented under
[SPEC-0003](docs/specifications/SPEC-0003-solver-executive.md),
[ADR-0004](docs/decisions/ADR-0004-owned-search.md),
[SPEC-0004](docs/specifications/SPEC-0004-extension-runtime.md) and
[ADR-0005](docs/decisions/ADR-0005-extension-authority.md).**

**C2 — Owned solver executive.** Own session state, work scheduling, budgets,
cancellation, telemetry, checkpoint shape, incumbent acceptance, and proof
completion. Provide a relaxation service over C1 and keep search strategy
replaceable. Start with a narrow branch-and-bound strategy using HiGHS
relaxations, but keep node/work-item interfaces usable by decomposition,
portfolios, and future search strategies.

**C3 — Extension runtime and authority model.** Official Rust traits plus a
deliberately small versioned C boundary for separately distributed native
components. Extensions declare problem classes, dependencies, data needs,
hardware, limits, and authority. Initial production categories are candidate
producers and search advisers; transformations such as cuts, presolve, and
reformulations remain experimental until validity and solution-space preservation
are justified.

*C2 evidence (recorded, not projected):*

- 192 tiny discrete models across a fixed coefficient/bound/limit grid, both
  objective senses, integer and binary domains, agree with brute-force
  enumeration of the entire assignment space on both the proven optimum and
  proven infeasibility.
- Every non-optimal relaxation termination is shown to forfeit the proof claim
  and to prune nothing by bound, so a limited child solve cannot discard an
  optimal solution.
- The executive drives the pinned HiGHS backend end to end and matches
  independent subset enumeration; it also runs entirely on test backends, which
  is what demonstrates it is backend-neutral.
- Termination does not depend on backend correctness: a backend returning
  solutions outside the node it was given forfeits rather than looping.

*C3 evidence (recorded, not projected):*

- Three honest extensions and three hostile ones covering 17 distinct
  misbehavior modes live in their own crate, which depends on the published
  extension and core APIs and takes the executive only as a test dependency.
  That they build and run at all is the evidence that a third-party extension
  needs no engine-internal change.
- Over the fixed model grid, every hostile extension leaves the outcome, the
  proven optimum, the dual bound, the forfeiture state and both prune counters
  identical to the extension-free run, which itself agrees with brute-force
  enumeration. Budgets are unlimited for these comparisons, because a hostile
  adviser spending a node budget badly changes exploration quality rather than
  correctness.
- An empty extension policy reproduces the extension-free record exactly, apart
  from measured elapsed time.
- Invalid candidates, invalid advice, both directions of contract-version
  mismatch, a refused transformation category, contained panics and exhausted
  budgets each produce a typed record entry. Recorded diagnostics stay bounded
  under an extension that is refused once per node.
- A proposal's claimed objective is never read; the record's objective is the
  independent recomputation. An adviser that always names an integral variable
  terminates rather than regenerating a child forever.

*Known limits, carried forward rather than hidden:* the extension host is
in-process, so containment covers panics but not a process abort or a memory
fault; process isolation and dynamically loaded native extensions are deferred
and need their own decision record. No memory budget is enforced per extension.
C3 establishes safety and makes no claim that any adviser improves search.

## Stage 3 — Application

**Entry condition:** Stage 2 proves owned state, search correctness, and
extension safety.

**C4 — Agent-independent run surface (complete).** Implemented under
[SPEC-0005](docs/specifications/SPEC-0005-run-surface.md) and
[ADR-0006](docs/decisions/ADR-0006-run-provenance.md). `optimizer search` drives
the owned executive over the pinned backend and writes a run record carrying the
revision, dirty state, hardware, toolchain, canonical model fingerprint and input
hashes; `optimizer verify` re-runs the search from that record alone and reports
divergence by field. This is the first surface reaching the C2 executive and C3
extension host from outside Rust test code.

The remaining items from C4's original scope keep their own specifications and
gates as **C8**: the local registry for versions, licenses, compatibility,
authority basis, failures and interactions; the Python SDK, whose blocker is
recorded because pyo3 requires an unsafe boundary ADR-0003 does not permit;
comparative experiment execution over a frozen manifest; and progress streaming
and checkpoint restart, which need new public search surface. MCP may wrap these
interfaces but is not required for execution.

**C5 — Scheduling vertical slice.** Flow-shop instances, makespan recurrence,
deterministic NEH and insertion candidates, independent evaluation, and model
adapters through the common C1-C3 interfaces. Job-shop follows only after
flow-shop correctness and reproducibility gates pass.

*C4 evidence (recorded, not projected):*

- A run remains reproducible from its record after its originating agent is
  unavailable: verification reads only the record's embedded configuration and
  the model it names, never the recorded result, and re-runs the search.
- Verification is shown to fail as well as pass. A model whose coefficient
  changed under an unchanged `model_id` is refused on its fingerprint, and each
  of the ten compared fields is detected when it alone is mutated, so no field is
  nominally compared and actually ignored.
- A record differing only in measured elapsed time still verifies, which fixes
  that number as diagnostic rather than contractual.
- A node-limited search writes its record, exits 1, and verifies as limited; a
  forfeited search that verifies still reports forfeiture. Agreement cannot
  launder a claim C2 declined to make.
- The run record satisfies both normative authorities: the Rust parser and the
  JSON Schemas accept the same documents, with nested versions checked on the
  parse path.

*Remaining evidence for this stage:*

- Exhaustive tiny instances, independent evaluator agreement, validated
  incumbents, and a frozen Taillard development subset pass with provenance (C5).

*Known limits, carried forward rather than hidden:* agreement is evidence of
determinism on one host over time, not of correctness; cross-host reproducibility
is untested; verification assumes an unchanged native library and cannot
distinguish a changed engine from a wrong result; checkpoint restart and progress
streaming remain unimplemented.

## Stage 4 — Research

**Entry condition:** Stage 3 provides reproducible workflows and a workload with
independent evaluation. Baselines are tuned before any intervention is measured.

**C6 — Heterogeneous computation.** Make device selection, residency, batching,
transfer timing, arithmetic width, lease ownership, fallback, cancellation, reset
recovery, and equivalence tolerances explicit before writing kernels. Measure a
GPU candidate evaluator or batched heuristic when independent work justifies it.
Evaluate GPU LP methods as a complementary backend; approximate results remain
candidates or warm starts until justified bounds and statuses exist.

**C7 — Adaptive portfolios and agent-developed algorithms.** Establish
conventional baselines, then evaluate feature/progress-aware allocation, reusable
candidate producers, and search advisers. Give agents source, contracts,
evaluators, profiling tools, and bounded budgets. Promote only artifacts that pass
conformance, correctness, resource, compatibility, and held-out performance gates.

These correspond to Hypotheses A and B in
[ai-native-optimizer-plan.md](ai-native-optimizer-plan.md). They are hypotheses:
this stage may close with a recorded negative result, which is a valid outcome.

*Evidence that closes this stage:*

- CPU/GPU agreement, sanitizer checks, overflow and input rejection, cancellation
  recovery, serialized lease behavior, and transfer-inclusive crossover
  measurements. CPU remains the default below the measured crossover.
- Held-out effect size, uncertainty estimates, controller and discovery overhead,
  interaction effects, and failure analysis, compared against tuned static
  configurations, simple adaptive rules, and conventional selection methods.
- A principal research contribution is selected on this evidence, or the
  hypotheses are recorded as unsupported.

## Stage 5 — Hardening

**Entry condition:** measured evidence identifies a specific bottleneck. Each
item below requires its own specification; none is authorized by this document.

Presolve, scaling, reoptimization, numerical recovery, stronger cuts, parallel
CPU search, checkpoint/restart, and larger models. These can dominate both
reliability and runtime, so they are sequenced by measurement rather than by
expected importance.

*Evidence that closes this stage:* each addition preserves the Stage 1 and 2
correctness contracts, including original-variable reconstruction through any new
transformation, and shows a measured improvement on the frozen workload.

## Stage 6 — Reproduction

**Entry condition:** a principal finding exists with held-out evidence.

Independently reproduce findings from pinned artifacts, document limitations and
negative results, then make licensing, public hub, and release decisions
separately.

*Evidence that closes this stage:* principal findings are reproduced from pinned
artifacts by someone other than their author. GPU and parallel execution may
prevent bitwise reproducibility, so reproducible experimental conclusions are
distinguished from identical execution traces.

---

## Measurement rules

All benchmarks freeze datasets, checksums, splits, seeds, settings, hardware,
budgets, timing, and analysis before comparison. Correctness, numerical behavior,
optimization performance, and development efficiency remain separate scorecards
and are not combined into an aggregate score. Evaluation ownership stays distinct
from the author of the tested algorithm. Sealed evaluation data stays outside the
discovery loop.

No public publication, push, hosting configuration, multi-GPU algorithm, broad
commercial compatibility, or natural-language modeling subsystem is implied by
this plan.

## Dependency rule

Implement one bounded, dependency-ready task at a time. Before behavior exists,
write its specification and ADR as needed; after implementation run
`bash tools/check.sh`, preserve minimized regressions, update records and
changelog, and advance only when the stated evidence exists. A skipped or waived
check is recorded in [state/known-failures.md](state/known-failures.md), never
silently absorbed into a pass.