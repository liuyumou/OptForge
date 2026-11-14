# ADR-0066: Scope delivery retention to the workload and lifecycle

Status: accepted prospective planning revision, 2026-11-12
Owner: experiment tooling
Baseline: d453675
Plan: [GPUP-DELIVERY3](../plans/lp-delivery3.md)
Roadmap: [GPU LP precision](../plans/gpu-lp-precision-roadmap.md)

## Context

The user authorizes revising the protocol and asks which task should follow
DELIVERY2. Its [frozen result](../benchmarks/lp-delivery2.md) remains a failure of
SPEC-0033's broad retention gate. Strict dense512 cold latency improves about
1.40x in both lanes, while the broad geometric means are 1.0584/1.0665x.
Prepared dense512 total medians regress despite cheaper checker transport.

That gate carried the FP4 roadmap's 1.10x/no-observed-regression rule into a
delivery optimization. It mixes an adoption decision with a mechanism question:
equal weighting can dilute a useful preparation gain, any tiny median increase
vetoes retention, and the reported intervals do not participate in the decision.
Five repetitions and one prepared session also leave important uncertainty.
This does not establish that the observed regressions are merely noise.

## Decision

Prioritize **GPUP-DELIVERY3: isolate delivery mechanisms, resolve prepared
regressions, and confirm a scoped cold benefit**. Independently switch batching
and checker/device startup overlap in a new research package. First diagnose
their individual effects and interaction; select and freeze a candidate for
each lifecycle before a separate confirmation cohort. All four variants retain
the same numerical work and independent original-model checker.

Use the prospective decision rules in the plan: dense128/256/512 are the declared
target class; retain a 1.10x complete-time benefit target there, and replace the
zero-observed-regression veto with a declared material-regression margin plus
simultaneous uncertainty bounds. Correctness and coverage remain hard gates.
Cold and prepared eligibility are separate, so a cold improvement cannot justify
deploying a regressing prepared route. Unresolved uncertainty is inconclusive.

The target class is selected using development evidence. Fresh timing blocks
can confirm that scoped claim; they do not establish unseen-model or production
performance. Small/sparse families and intentional refusals remain in the
confirmation roster and guardrails. No unfavorable family is dropped afterward.

## Scope and consequences

This revision governs the new delivery follow-up. It does not relabel DELIVERY2,
edit SPEC-0033/ADR-0065, revise historical scientific cells, or change TENSOR2's
separate FP4-versus-native criterion. MIXED2 remains independently ready as a
numerical alternative. A supported delivery improvement benefits both native
and FP4 and does not establish an FP4 arithmetic advantage.

The present work is documentation only. Implementation starts with a concrete
independent resource package and source/lifecycle admission. Historical
allocations stay closed. No new GPU study, public preset, GPUP-8 completion,
GPUP-9 release, push or publication follows from this planning revision.
