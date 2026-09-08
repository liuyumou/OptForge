# ADR-0002: Original Model Validation

Status: accepted
Owner: numerical core
Introduced: M1
Last reviewed commit: 9e6dc86534de2efa414205752ca58d7584976052
Supersedes: ADR-0001's M0-only implementation scope; other decisions remain in force

## Context

M0 is complete. The approved M1 plan requires Rust, JSON and CLI validation,
explicit caller tolerances, rejection of duplicate terms, and term-magnitude scaling.

## Decision

Implement [SPEC-0001](../specifications/SPEC-0001-model-and-validation.md) using
safe Rust and existing Serde dependencies. Store immutable original linear models
with stable IDs. Require explicit tolerances without defaults. Evaluate using
deterministic sequential f64 arithmetic, rejecting nonfinite intermediates.
Row tolerance includes absolute term contributions. This permits larger residuals
under cancellation; reports expose raw violations and allowances for inspection.
Reject duplicate terms instead of merging coefficients. Candidate feasibility
does not establish optimality or mathematical proof.

## Alternatives

Implicit tolerances hide caller policy. Coefficient merging changes input
arithmetic. Activity-only scaling is stricter under cancellation but was not
selected. Native solvers and transformations await their own contracts.

## Consequences

M1 is the implementation scope. M2 remains specification-gated. Finite IEEE-754
rounding and underflow are permitted. No existing experiment seeds, thresholds,
splits, tolerances or defaults change, so no replacement experiment is needed.
New numerical tests supply explicit tolerance values.

## Implementation and Tests

[Core](../../crates/optimizer-core/src/lib.rs),
[CLI](../../crates/optimizer-cli/src/main.rs), and [gate](../../tools/check.sh).
Task state records final acceptance evidence.
