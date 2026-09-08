  # AI-Native Optimizer Project Bootstrap and Development Roadmap

  ## Summary

  Establish a Rust first repository and an autonomous development process that can support the full optimizer described in ai-native-optimizer-plan.md.

  The first stage creates the repository skeleton, engineering rules, documentation system, specification templates, test strategy, benchmark manifests, reproducibility records, and CI checks. It does not attempt to implement the complete solver.

  The project uses:

  - Rust for the solver core, model representation, validation, scheduling algorithms, CLI, and experiment tooling.
  - Small, explicit FFI boundaries for HiGHS and CUDA.
  - Python bindings and a Python SDK after the Rust core has stable interfaces.
  - One GPU at a time for all development, tests, profiling, and benchmarks.
  - Trunk based Git development with short lived branches and protected main.
  - Autonomous implementation by one AI developer, with correctness gates and reproducible artifacts replacing routine human review.

  ## Repository Bootstrap

  Create a Git repository and use this initial layout:

  ai-optimizer/
  ├── Cargo.toml
  ├── Cargo.lock
  ├── rust-toolchain.toml
  ├── README.md
  ├── LICENSE
  ├── CONTRIBUTING.md
  ├── CHANGELOG.md
  ├── .gitignore
  ├── .editorconfig
  ├── .github/
  │   └── workflows/
  │       ├── ci.yml
  │       ├── docs.yml
  │       └── benchmark-smoke.yml
  ├── crates/
  │   ├── optimizer-core/       # model types, validation, numerical contracts
  │   ├── optimizer-solver/     # search executive and solver orchestration
  │   ├── optimizer-schedule/   # flow-shop and later job-shop algorithms
  │   ├── optimizer-cli/        # command-line interface
  │   ├── optimizer-experiment/ # manifests, records, reports, reproducibility
  │   ├── optimizer-highs/      # safe HiGHS FFI wrapper
  │   └── optimizer-cuda/       # GPU ownership, launch, and CUDA FFI
  ├── cuda/
  │   └── schedule_eval/        # isolated CUDA C++ kernels and tests
  ├── python/                   # added at the SDK milestone
  ├── docs/
  │   ├── architecture/
  │   ├── specifications/
  │   ├── decisions/
  │   ├── tutorials/
  │   ├── operations/
  │   └── benchmarks/
  ├── wiki/                     # concise navigational/project knowledge pages
  ├── examples/
  ├── tests/
  │   ├── fixtures/
  │   ├── integration/
  │   ├── differential/
  │   └── regression/
  ├── benches/
  ├── benchmarks/
  │   ├── manifests/
  │   ├── scripts/
  │   └── reports/
  ├── schemas/                  # versioned experiment/config/result schemas
  ├── tools/                    # validation, benchmark, and release scripts
  └── state/
      ├── backlog.yaml
      ├── active-task.md
      └── known-failures.md

  The first commit should contain only the bootstrap files, templates, and a passing “hello workspace” build. Do not create empty abstractions for solver features before their first specification requires them.

  ### Required tooling

  Pin the Rust toolchain in rust-toolchain.toml. Configure:

  - cargo fmt --check
  - cargo clippy --all-targets --all-features -- -D warnings
  - cargo test --workspace
  - cargo deny or an equivalent dependency and license check
  - cargo nextest when CI capacity permits
  - mdbook or an equivalent documentation builder
  - rustdoc for public Rust APIs
  - CUDA compiler and sanitizer tooling only on the GPU runner
  - Python tooling later: maturin, pytest, ruff, and mypy or an equivalent type checker

  CI must run CPU checks on every change. GPU checks run on a serialized, labeled runner and are never allowed to overlap with another project GPU job.

  ## Documentation, Wiki, and Specification Rules

  ### Documentation hierarchy

  Use each documentation type for one purpose:

  - README.md: project purpose, current status, quick start, supported platforms, and links to deeper documents. Keep it useful to a new contributor and under approximately 500 lines.
  - docs/architecture/: stable subsystem boundaries, data flow, ownership, and performance constraints.
  - docs/specifications/: normative behavior. A specification uses mandatory language (MUST, MUST NOT, SHOULD, MAY), explicit inputs and outputs, invariants, errors, compatibility rules, and acceptance tests.
  - docs/decisions/: architecture decision records. Each record states context, decision, alternatives, consequences, and supersession status.
  - docs/tutorials/: task oriented guides with commands and expected output.
  - docs/operations/: build, benchmark, GPU lease, troubleshooting, and release procedures.
  - docs/benchmarks/: benchmark definitions, datasets, splits, metrics, and interpretation rules.
  - wiki/: short, maintained navigation pages for concepts, workflows, glossary terms, and links to authoritative specifications. The wiki MUST NOT introduce behavior that is absent from docs/specifications/.

  Every normative document has an owner (a subsystem or role, not a person), status (draft, accepted, deprecated), last reviewed commit, and links to implementation and tests.

  ### Writing rules

  - Begin with purpose and scope.
  - Define terminology before using it.
  - Separate normative requirements from rationale and examples.
  - Use one requirement per numbered statement so tests can reference it.
  - Include failure behavior and resource limits.
  - State numerical assumptions, units, tolerances, overflow behavior, and determinism expectations.
  - Prefer executable examples and exact commands.
  - Link to symbols, schemas, tests, and ADRs rather than duplicating details.
  - Mark unknown or unvalidated claims as hypotheses.
  - Never report benchmark results without the instance manifest, revision, hardware, seed, configuration, and timing method.
  - Update documentation in the same change as behavior. A behavior change without a specification or release-note entry is incomplete.

  ### Specification template

  Each specification in docs/specifications/ follows this structure:

  # SPEC-XXXX: <title>

  Status: draft | accepted | deprecated
  Scope: <subsystem>
  Owner: <subsystem owner>
  Introduced: <commit or milestone>
  Supersedes: <SPEC or none>

  ## Purpose
  ## Terminology
  ## Requirements
  1. The component MUST ...
  2. The component MUST NOT ...

  ## Interfaces
  ## State and invariants
  ## Errors and recovery
  ## Compatibility and versioning
  ## Security and resource limits
  ## Examples
  ## Acceptance tests
  ## Open questions

  A specification may remain draft while implementation proceeds, but no feature becomes a default or public interface until its relevant specification is accepted.

  ### Decision records

  Use ADR-XXXX-title.md. Record one decision per file. Once accepted, do not rewrite history; add a superseding ADR when evidence changes the decision.

  ## Testing and Verification Rules

  Maintain separate correctness, compatibility, performance, and agent-development tests.

  ### Test layers

  - Unit tests: pure functions, model invariants, parsers, arithmetic, schedule recurrence, and status mapping.
  - Property tests: generated models and schedules; check feasibility preservation, objective recomputation, permutation invariants, and serialization round trips.
  - Exhaustive tests: enumerate all assignments or permutations for tiny instances and compare with the implementation.
  - Differential tests: compare HiGHS, SCIP where available, an independent schedule evaluator, and the owned implementation. Disagreements require diagnosis.
  - Integration tests: full CLI and SDK flows, cancellation, resource limits, extension loading, and artifact creation.
  - GPU tests: CPU/GPU bitwise or tolerance checked outputs, overflow rejection, device selection, cancellation, stale lease recovery, and serialized execution.
  - Regression tests: every discovered numerical, parser, search, or kernel defect becomes a minimized fixture.
  - Performance benchmarks: Criterion or equivalent microbenchmarks plus end to end benchmark runs. Performance tests are never used as correctness tests.

  Do not write tests that merely duplicate implementation structure. Every test must identify a contract, invariant, historical defect, or measurable performance claim.

  ### Required early correctness coverage

  The foundation must cover:

  - feasible, infeasible, unbounded, interrupted, time-limited, and backend-failure statuses;
  - objective recomputation and original-variable reconstruction;
  - integer and binary domain violations;
  - sparse matrix indexing and serialization;
  - deterministic seeded behavior;
  - flow-shop completion recurrence;
  - schedule permutation validity;
  - rejection of overflow and unsupported model features;
  - GPU and CPU evaluator agreement;
  - exclusive one-GPU leasing under normal completion and cancellation.

  A timeout or numerical failure MUST NEVER be reported as proven optimality.

  ### Test data policy

  Keep small fixtures in the repository. Store large public datasets outside Git with download scripts, checksums, license records, and exact version manifests. Store generated benchmark seeds and generation parameters, not only generated outputs.

  ## Git and Change Management Rules

  Use trunk based development:

  - main is always buildable and protected.
  - Branches use type/short-description, such as feat/model-validator or fix/highs-status.
  - Keep branches short lived and rebase before integration.
  - Every commit must build or clearly be an intermediate documentation/tooling commit that does not break the workspace.
  - Use Conventional Commit prefixes: feat, fix, refactor, perf, test, docs, build, ci, bench, chore.
  - Keep commits focused. Do not combine formatting churn, dependency upgrades, and behavior changes.
  - Commit messages state the behavior or contract changed, not the conversation that produced it.
  - Never commit credentials, private datasets, generated binaries, benchmark outputs without provenance, or unreviewed dependency lockfile changes.
  - Require CI success, specification updates, tests, and release-note updates for behavior changes.
  - Tag milestone releases with annotated tags such as v0.1.0-foundation.
  - Use CHANGELOG.md for user-visible changes and docs/decisions/ for architectural changes.
  - Revert a bad change with a new commit; do not rewrite shared main history.
  - Record unresolved issues in state/known-failures.md, including reproduction commands and the next diagnostic step.
  - Before starting work, update state/active-task.md with objective, acceptance gate, files likely to change, and resource budget. On completion, record evidence and follow-up work.

  ## Autonomous Development Rules

  The single AI developer operates one bounded task at a time.

  For every task:

  1. Read the relevant specifications, ADRs, current failures, and neighboring tests.
  2. Write or update the specification before implementing behavior that lacks a contract.
  3. Implement the smallest complete vertical slice.
  4. Run formatting, linting, unit tests, integration tests, and relevant benchmark smoke tests.
  5. Inspect failures and preserve minimized reproductions.
  6. Update documentation, changelog, experiment records, and task state.
  7. Commit only after the acceptance gate passes.
  8. Mark the task complete and select the next dependency-ready task.

  The AI MUST NOT silently alter benchmark splits, tolerances, seeds, acceptance thresholds, or solver defaults to obtain better results. Such changes require an ADR and a new experiment record.

  Use deterministic seeds, bounded compute, and serialized GPU access. Stop and record a task when a mathematical contract is unclear; continue independent documentation and tooling work while the ambiguity is resolved.

  ## Early Milestones and Detailed Specifications

  ### M0 — Repository and process bootstrap

  Goal: establish a buildable, inspectable project.

  Deliverables:

  - Initialize Git and create the repository layout.
  - Add Rust workspace, pinned toolchain, formatting, linting, dependency policy, CI, and documentation build.
  - Add CONTRIBUTING.md, templates for specifications and ADRs, benchmark manifest schema, experiment result schema, and autonomous task workflow.
  - Add the exclusive GPU lease design and a dry-run command that reports devices without launching kernels.
  - Add a project glossary and a status page identifying planned, implemented, experimental, and deprecated features.

  Acceptance tests:

  - Clean checkout builds and runs all CPU CI checks.
  - Documentation builds with no broken internal links.
  - Schemas validate representative configuration and result records.
  - GPU discovery lists the three known devices by UUID when hardware is present and reports a clear unavailable state otherwise.
  - Two simulated GPU jobs serialize correctly; cancellation releases the lease.

  ### M1 — Core model and validation

  Goal: create the numerical authority boundary.

  Specification: SPEC-0001-model-and-validation.md.

  Define Rust types for variables, bounds, domains, sparse linear constraints, objectives, model identifiers, and validation reports.

  Requirements include:

  - Stable variable and constraint identifiers.
  - Explicit finite/infinite bounds and checked arithmetic.
  - Objective recomputation from original model data.
  - Feasibility checks with declared absolute and relative tolerances.
  - Deterministic serialization.
  - Explicit errors for malformed, unsupported, or numerically unsafe models.

  Acceptance tests:

  - Property and exhaustive tests for small models.
  - Round-trip serialization.
  - Independent objective and violation recomputation.
  - Fixtures for infeasible, unbounded, degenerate, poorly scaled, and overflow-prone models.

  ### M2 — HiGHS FFI and solve records

  Goal: provide a reliable CPU LP/MILP backend boundary.

  Specification: SPEC-0002-backend-contract.md.

  Define backend creation, model loading, solve invocation, cancellation, limits, statuses, solution extraction, warm starts, and cleanup.

  Requirements include:

  - No raw C handles outside the FFI crate.
  - Every backend status maps to an explicit optimizer status.
  - Numerical warnings and failures are retained in result records.
  - Backend output is validated by the core before publication.
  - A backend failure cannot become an optimal result.

  Acceptance tests:

  - Differential LP and small MILP tests against standalone HiGHS.
  - Cancellation and time-limit tests.
  - Repeated create/solve/destroy tests under sanitizers where available.
  - Reproducible structured solve records.

  ### M3 — Flow-shop vertical slice

  Goal: produce a complete CPU scheduling workflow.

  Specification: SPEC-0003-flow-shop.md.

  Define instance format, processing-time constraints, permutation semantics, makespan recurrence, NEH, insertion neighborhoods, deterministic tie-breaking, and output format.

  Acceptance tests:

  - Exhaustive comparison on tiny instances.
  - Independent evaluator agreement.
  - Taillard development subset smoke run.
  - Candidate-to-MILP incumbent validation.
  - Reproducible reports containing instance checksum, seed, configuration, and revision.

  ### M4 — Owned MILP executive

  Goal: own the search loop while using HiGHS for LP relaxations.

  Specification: SPEC-0004-branch-and-bound.md.

  Define node state, branching, bounds, incumbent acceptance, node termination, limits, cancellation, numerical tolerances, and proof status.

  Acceptance tests:

  - Exhaustive agreement on tiny binary and integer models.
  - Correct infeasible, bounded, unbounded, timeout, and interrupted outcomes.
  - Invalid extension actions are rejected.
  - Proof completion is reported only when all required nodes are resolved.

  ### M5 — CUDA schedule evaluator

  Goal: measure useful GPU acceleration in a complete heuristic.

  Specification: SPEC-0005-gpu-schedule-evaluator.md.

  Define device selection, exclusive lease behavior, input layout, arithmetic width, batch limits, CPU fallback, timing boundaries, error recovery, and CPU/GPU equivalence tolerance.

  Acceptance tests:

  - Exact or declared-tolerance agreement with Rust for generated cases.
  - CUDA memory and race checks.
  - Input overflow and invalid permutation rejection.
  - Cancellation and device-reset recovery.
  - Transfer-inclusive benchmark on the Taillard validation subset.
  - CPU fallback for batches below the measured crossover.
  - Only one GPU lease exists at a time.

  ### M6 — Benchmark and evidence package

  Goal: establish trustworthy performance evidence.

  Use Taillard flow shop as the primary suite, generated flow-shop cases for exhaustive and distribution-shift testing, OR-Library job shop for transfer, MIPLIB 2017 for general MILP diagnostics, Netlib for LP regression, and generated sparse LPs for later GPU LP work.

  Freeze manifests, checksums, splits, seeds, solver settings, timing protocol, and analysis scripts. Report failures and unsupported cases.

  ## Long-Term Roadmap

  ### Phase 1: Foundation and correctness

  Complete M0–M2. Establish stable model, backend, status, artifact, and testing contracts. No performance claim is made during this phase.

  ### Phase 2: Owned scheduling and search

  Complete M3–M4. Support flow-shop optimization, a narrow MILP surface, validated heuristics, and a correct branch-and-bound executive. Add job-shop support only after flow-shop correctness and reproducibility gates pass.

  ### Phase 3: GPU scheduling acceleration

  Complete M5–M6. Optimize data residency, batching, and kernel occupancy based on profiles. Compare the RTX 5090 and RTX PRO 6000 sequentially, one device at a time. Keep CPU execution as the default when GPU overhead dominates.

  ### Phase 4: Research extensions

  Evaluate adaptive heuristic portfolios, search advisers, warm starts, and agent-generated candidate producers. Compare against tuned static configurations, simple adaptive rules, and conventional algorithm-selection methods. Include discovery cost and per-solve overhead.

  ### Phase 5: GPU LP research

  Implement and validate a CPU first-order LP method, then a CUDA backend with sparse matrix operations. Treat approximate GPU results as candidate or warm-start information until a mathematically justified bound and status contract exists.

  ### Phase 6: Robustness and scale

  Add presolve, scaling, reoptimization, numerical recovery, stronger cuts, parallel CPU search, checkpoint/restart, and larger model support only when benchmark evidence identifies a need. Each addition requires a specification, differential tests, and regression fixtures.

  ### Phase 7: SDK, registry, and reproducibility

  Introduce Python bindings and SDK after Rust interfaces stabilize. Add a local extension registry, package compatibility metadata, experiment retrieval, and promotion records. Keep the CLI and file formats usable without an AI agent.

  ### Phase 8: Independent evaluation and release

  Run independent reproductions, held-out benchmark analyses, ablations, hardware comparisons, and negative-result documentation. Publish only after licensing, dependency, security, and reproducibility checks are complete.

  ## Explicit Assumptions

  - Rust is the principal language; CUDA C++ is limited to device kernels and their narrow host boundary.
  - Python is introduced after the Rust core and CLI contracts stabilize.
  - One GPU at a time is a strict project-wide rule.
  - The initial supported platform is Linux with NVIDIA CUDA.
  - HiGHS is the initial CPU backend subject to FFI, licensing, numerical, and integration validation.
  - Public benchmark instances are evidence sources, not assumed secret test data.
  - Calendar durations are deliberately omitted; milestones advance by acceptance evidence.
  - Public plugin distribution, multi-GPU algorithms, broad commercial solver compatibility, and natural-language model generation remain deferred.