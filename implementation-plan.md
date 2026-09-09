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
| 2. Execution | C2 executive, C3 extension runtime | C2 complete; C3 not started, **unspecified** |
| 3. Application | C4 SDK/CLI/registry, C5 scheduling slice | Not started |
| 4. Research | C6 heterogeneous computation, C7 adaptive portfolios | Not started |
| 5. Hardening | Presolve, scaling, reoptimization, cuts, parallel search | Not started |
| 6. Reproduction | Independent reproduction, then release decisions | Not started |

Only stages 0 and 1 are complete, and C2 within stage 2. Everything below is a
plan, and the performance and learning claims in stages 4 and beyond are
hypotheses, not results. C2 establishes search correctness only and makes no
performance claim.

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

**C2 is implemented under
[SPEC-0003](docs/specifications/SPEC-0003-solver-executive.md) and
[ADR-0004](docs/decisions/ADR-0004-owned-search.md). C3 requires an accepted
specification before any public API is introduced; that specification does not
exist.**

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

*Evidence that still closes this stage (C3):*

- Independently authored extensions build and run without engine-internal changes,
  while core validation remains authoritative.
- Invalid actions, incompatible versions, crashes, and resource abuse produce
  structured artifacts rather than silent degradation.

## Stage 3 — Application

**Entry condition:** Stage 2 proves owned state, search correctness, and
extension safety.

**C4 — Agent-independent interaction and experiment workspace.** Extend the CLI
and add Python bindings/SDK after the C1 interfaces have stabilized under real
use. Support model inspection, validation, pinned solving, progress and
diagnostics, cancellation, comparative experiments, profiling, extension
conformance, and artifact retrieval through documented files and records. Maintain
disposable experimental and pinned execution workspaces, plus a local registry for
versions, licenses, compatibility, authority basis, failures, interactions,
manifests, and results. MCP may wrap these interfaces but is not required for
execution.

**C5 — Scheduling vertical slice.** Flow-shop instances, makespan recurrence,
deterministic NEH and insertion candidates, independent evaluation, and model
adapters through the common C1-C3 interfaces. Job-shop follows only after
flow-shop correctness and reproducibility gates pass.

*Evidence that closes this stage:*

- A run remains reproducible from pinned revisions and records after its
  originating agent is unavailable.
- Exhaustive tiny instances, independent evaluator agreement, validated
  incumbents, and a frozen Taillard development subset pass with provenance.

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