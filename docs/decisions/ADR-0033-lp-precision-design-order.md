# ADR-0033: Validate precision architecture before adding lower precision

Status: accepted for planning only, 2026-10-12; numerical contracts remain draft
Owner: numerical backend and experiment tooling
Introduced: GPUP-DESIGN
Last reviewed commit: bootstrap
Superseded by: none

## Context

The user requested a design review and durable implementation/experiment plans,
including compact combinations of floats, sensitive algorithm components, and
iterations that need not reconstruct native FP64 values. The completed studies
show both convergence amplification and substantial costs outside GPU arithmetic.
The [preserved review](../plans/lp-low-precision-research-2026-09-30.md) identifies
promising approaches but is not a complete implementation contract. In particular,
lossless input encoding does not establish accurate arithmetic or convergence.

## Decision

Separate four decisions: storage representation, arithmetic semantics, optimization
method, and independent authority over the original model. Prioritize a CPU-only
representation/proof contract review, GPUP-REP, before further numerical GPU work.
Then evaluate a lean executor, persistent accurate state, and residual-driven LP
refinement in separate bounded slices. Quantization remains GPUP-7; Tensor Core
execution remains conditional GPUP-8. Neither is a required winning ingredient.
GPUP-9 may select a recipe without an inadmissible or unhelpful Tensor Core route.

The [architecture plan](../plans/lp-precision-architecture-2026-10-12.md) records
motivation and alternatives. [SPEC-0020](../specifications/SPEC-0020-lp-expansion-arithmetic.md)
and [SPEC-0021](../specifications/SPEC-0021-lp-refinement.md) are **drafts**, not
permission to implement their proposed numerical behavior. Each affected slice
must close its stated mathematical/interface questions and accept a bounded
contract before behavior. The [experiment design](../benchmarks/lp-precision-design-experiments.md)
is a proposed extension of SPEC-0013; it freezes no new benchmark split or seed and
admits no device job. The backlog distinguishes dependencies from priority.

Keep accepted legacy identities, audits, authority, defaults and evidence unchanged.
An expansion can carry the original coefficients exactly without native FP64
operations in an inner loop. That does not authorize publishing an unchecked bound
or replacing original-model accuracy with accuracy for a rounded surrogate.
ADR-0010 and the accepted certifier remain authoritative. Any future replacement
of that certification mechanism requires its own proof and accepted decision.

This decision changes planning order, superseding the former immediate GPUP-7
handoff only. It adds **zero GPU seconds**. Preserve 17115.274617853 seconds used
against the 18002.574545061-second cumulative ceiling, every phase cap, and all
16134 ledger events with SHA-256
60649d29992d21508e60aa60f3e334e9ac18fe3254525ec38cc0eef298e84823.
The remaining difference is not a reservation available to a new task.

## Alternatives

- Proceed directly to FP8: retains the old order but leaves measured operator bias,
  range failures and expensive recombination unresolved.
- Require native FP64 everywhere: provides a useful control, but conflates the
  desired accuracy with one hardware instruction format.
- Remove original-model checks: can produce a faster surrogate solve, but cannot
  substantiate the project's high-accuracy objective or certified bounds.
- Build every proposed component before comparing them: spends resources on
  incompatible or unhelpful combinations. Use admission gates and small ablations.

## Consequences

New designs need explicit exponent, rounding, residual, recovery and cost semantics.
A negative CPU proof or memory/shape admission result can stop a candidate before
GPU development. Compact storage may still require more traffic than native FP64;
software arithmetic may cost more than the arithmetic it replaces. A hybrid of
accurate expansion state and inexpensive inexact corrections is a valid candidate,
not a predicted winner. No supported recipe follows from this decision.

## Implementation and tests

Only documentation and a CPU mathematical design artifact are introduced here.
The reproducible [design validator](../../tools/check_lp_precision_design.py)
checks exact examples and counterexamples; it is not a production codec or a proof
of all proposed arithmetic. Run it and the full pinned-native tools/check.sh gate.
Device acceptance, sanitizers, convergence trials and new budget admission belong
to later slices. See [active task](../../state/active-task.md) for actual receipts.
