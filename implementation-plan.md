# AI-Native Optimizer Implementation Plan

This plan turns [ai-native-optimizer-plan.md](ai-native-optimizer-plan.md) into an evidence-driven implementation roadmap. M0 and M1 are complete. Later work is organized around reusable capabilities rather than a fixed solver sequence.

## Principles and invariants

- Rust owns runtime state, numerical authority, resource budgets, and extension boundaries.
- HiGHS is the first CPU backend and an independent reference, not the architecture.
- The engine runs with pinned configuration and installed extensions without an agent.
- Extensions declare capabilities and authority; the core validates candidates, actions, and proof claims.
- CLI, SDK, structured records, and a local registry are shared by humans and agents.
- GPU work is measured end to end, uses the shared one-GPU lease, and always retains a CPU fallback.
- Every behavior has a specification, acceptance tests, provenance, and a recorded failure path.

## Completed foundation

### M0 — Repository and process bootstrap

Completed. Rust workspace, pinned toolchain, documentation and dependency checks, schemas, artifact provenance, GPU discovery, and cancellable lease simulation are in place.

### M1 — Model and validation authority

Completed under SPEC-0001 and ADR-0002. Original models, stable identifiers, checked arithmetic, bounds/domains, objective recomputation, candidate validation, tolerances, canonical JSON, and CLI diagnostics are authoritative.

## Capability roadmap

### C1 — Backend-neutral solve and session contract

Specification: SPEC-0002 and a superseding ADR where required.

Define solve requests, backend capabilities, cancellation and resource limits, warm starts, progress events, termination/status semantics, validated solution extraction, diagnostics, and immutable solve records. Keep native handles inside the adapter crate. Distinguish backend status, candidate feasibility, bound validity, and engine proof claims.

Implement the HiGHS 1.11.0 adapter first for LP and narrow MILP support. Require differential tests, lifecycle cleanup, limits, cancellation, warm starts, status preservation, numerical warning retention, and reproducible records.

Gate: standalone HiGHS comparisons and all CPU checks pass; no backend failure, timeout, or interruption can be reported as proven optimality.

### C2 — Owned solver executive

Specification: new executive/search specification before public search APIs.

Own session state, work scheduling, budgets, cancellation, telemetry, checkpoint shape, incumbent acceptance, and proof completion. Provide a relaxation service over C1 and keep search strategy replaceable.

Start with a narrow branch-and-bound strategy using HiGHS relaxations, but keep node/work-item interfaces usable by decomposition, portfolios, and future search strategies. Exhaustive tiny-model tests must cover feasible, infeasible, unbounded, interrupted, limited, backend-failure, and proof states.

Gate: complete search correctness and termination evidence precedes performance claims or learned control.

### C3 — Extension runtime and authority model

Specification: extension lifecycle, capability, and conformance contracts.

Provide official Rust traits and a deliberately small versioned C boundary for separately distributed native components. Extensions declare problem classes, dependencies, data needs, hardware, limits, and authority.

Initial production categories are candidate producers and search advisers. Transformations such as cuts, presolve, and reformulations remain experimental until validity and solution-space preservation are justified. Reject invalid actions, incompatible versions, crashes, and resource abuse with structured artifacts.

Gate: independently authored extensions build and run without engine-internal changes; core validation remains authoritative.

### C4 — Agent-independent interaction and experiment workspace

Extend the CLI and add Python bindings/SDK after C1 interfaces stabilize. Support model inspection, validation, pinned solving, progress and diagnostics, cancellation, comparative experiments, profiling, extension conformance, and artifact retrieval through documented files and records.

Maintain disposable experimental and pinned execution workspaces. Add a local registry for versions, licenses, compatibility, authority basis, failures, interactions, manifests, and results. MCP may wrap these interfaces but is not required for execution.

Gate: a run remains reproducible from pinned revisions and records after its originating agent is unavailable.

### C5 — Scheduling vertical slice

Specification: flow-shop application contract.

Implement flow-shop instances, makespan recurrence, deterministic NEH and insertion candidates, independent evaluation, and model adapters through the common C1–C3 interfaces. Add job-shop only after flow-shop correctness and reproducibility gates pass.

Gate: exhaustive tiny instances, independent evaluator agreement, validated incumbents, and a frozen Taillard development subset pass with provenance.

### C6 — Heterogeneous computation

Specification: backend/device and GPU evaluator contracts before kernels.

Make device selection, residency, batching, transfer timing, arithmetic width, lease ownership, fallback, cancellation, reset recovery, and equivalence tolerances explicit. Measure a GPU candidate evaluator or batched heuristic when independent work justifies it. Evaluate GPU LP methods as a complementary backend; approximate results remain candidates or warm starts until justified bounds and statuses exist.

Gate: CPU/GPU agreement, sanitizer checks, overflow and input rejection, cancellation recovery, serialized lease behavior, and transfer-inclusive crossover measurements pass. CPU remains the default below the measured crossover.

### C7 — Adaptive portfolios and agent-developed algorithms

Establish conventional baselines, then evaluate feature/progress-aware allocation, reusable candidate producers, and search advisers. Give agents source, contracts, evaluators, profiling tools, and bounded budgets. Promote only artifacts that pass conformance, correctness, resource, compatibility, and held-out performance gates.

Measure discovery cost, per-solve overhead, reuse, interactions, negative results, and distribution shift. Compare with tuned static configurations, simple adaptive rules, and conventional selection methods.

Gate: select a principal research contribution using held-out effect size, uncertainty, overhead, and failure analysis.

## Evidence and release stages

1. **Contract stage:** C1 is complete and M1 behavior remains green.
2. **Execution stage:** C2 and C3 prove owned state, extension safety, and search correctness.
3. **Application stage:** C4 and C5 provide reproducible human/agent workflows and scheduling evidence.
4. **Research stage:** C6 and C7 compare interventions against tuned baselines on sealed family-level holdouts.
5. **Hardening stage:** add presolve, scaling, reoptimization, stronger cuts, parallel CPU search, checkpoint/restart, and larger models only when evidence justifies separate specifications.
6. **Reproduction stage:** independently reproduce findings from pinned artifacts, document limitations and negative results, then make licensing, public hub, and release decisions separately.

All benchmarks freeze datasets, checksums, splits, seeds, settings, hardware, budgets, timing, and analysis before comparison. Correctness, numerical behavior, optimization performance, and development efficiency remain separate scorecards. No public publication, push, hosting configuration, multi-GPU algorithm, broad commercial compatibility, or natural-language modeling subsystem is implied by this plan.

## Dependency rule

Implement one bounded, dependency-ready task at a time. Before behavior exists, write its specification and ADR as needed; after implementation run `bash tools/check.sh`, preserve minimized regressions, update records and changelog, and advance only when the stated gate passes.
