# ADR-0054: Use RESIDENT2 evidence to gate further optimization

Status: roadmap planning amendment, 2026-11-11; future execution protocols and allocations pending
Owner: numerical backend and experiment tooling
Last reviewed commit: 0c4a395334a44121970322cacec10fb4ff709f91
Supersedes: ADR-0047's forward priority for resident optimization after baseline delivery
Implementation: [current roadmap](../plans/gpu-lp-precision-roadmap.md#resident2-lessons-and-planning-changes-2026-11-11), [backlog](../../state/backlog.yaml)
Acceptance: documentation links, backlog consistency and preservation of numerical sources/evidence

## Context

The user asks whether the lessons from GPUP-RESIDENT2 warrant roadmap changes.
The [completed study](../benchmarks/lp-resident2-gpup-resident2.md) retains 64 cells
and 96 endpoints. Certified coverage and all 42 certified pairs' bytes/work are
unchanged, but 1.027370x cold geomean and four regressing medians fail the declared
retention gate. The admission trace reduces synchronizations from 58 to 44 at
2800 launches while approximately doubling transfer volume. Individual guard,
submission and transfer latency effects were not isolated.

For dense-65536, native execution accounts for roughly 2.40 of 9.78 cold seconds;
independent checking takes 3.16 seconds and conversion/preparation about 2.33
seconds. These are marginal medians, not an additive per-trial decomposition.
Prepared lifecycle reuse helps observed throughput, but each mode/model has only
one batch. Normal-limit export is fixed; the mixed-model bound refusal persists.

## Decision

1. Keep the tuned native control. MIXED2 remains the next numerical candidate,
   starting with CPU-only cost and numerical contract preparation from retained
   evidence. A numerical implementation/allocation is a separate accepted slice.
2. Before device work, identify the accelerated portion of complete latency and
   count added representation, transfer, guard, correction, recovery and checking
   costs. A planning model is `T_new = (T - A) + w*A/s + O`: `T` is one matched
   control trial's complete time, `A` the affected portion, `s` its assumed speed
   ratio, `w` the work multiplier and `O` added cost. State assumptions/ranges;
   this is a forecast, not measured performance. For `0 <= A < T`, even the ideal
   zero-overhead bound `T/(T-A)` must support the predeclared total-latency target. Unknown
   phase attribution warrants a separately bounded measurement pilot, not
   assigning all native time to accelerated arithmetic. Apply the actual
   predeclared model/coverage rule; do not discard unfavorable models afterward.
3. Add GPUP-DELIVERY2 as a conditional alternative before precision device work.
   Inspect demonstrated duplicate parsing, immutable preparation, checker input
   preparation, provenance and transport work. Select it when its complete-cost
   case is stronger; it is not an unconditional prerequisite for MIXED2.
   Preserve exact source/model bindings, fresh independent original-model
   certificates, complete output and conservative refusal behavior. Faster
   evidence production must not mean fewer mathematical checks or missing evidence.
4. Treat further resident changes as new hypotheses. Require a quantified change
   in launch/copy/byte/allocation and safety cost; synchronization count alone
   does not justify another study. Compact flag transport and graph submission
   remain unmeasured alternatives. Retain cancellation, controller and rollback
   contracts unless separately superseded.
5. Keep cold latency and prepared throughput separate. Reuse immutable setup,
   never warm iterates or a prior certificate. Match transport between control
   and candidate, and predeclare repetitions, uncertainty and regression rules.
   Three repetitions and one batch do not establish a general ranking or preset.
6. Separate the mixed-model bound-authority investigation from export repair and
   arithmetic tuning. Use retained endpoints for diagnosis; preserve infinite
   bounds and the original 1e-9 authority. Uncertified endpoints remain visible
   in coverage and ineligible for certified speed ratios.

Before future device admission, bind the executable actually produced by the
build, verify failure stimuli after preprocessing, and check real output schemas
and counters. These address retained admission errors, not the measured latency
failure. Failed logs, binaries and charges remain immutable.

## Consequences and limits

The roadmap makes host/evidence cost a selectable engineering task and requires
mixed precision to justify its attainable complete-path gain. It retains low
precision as a candidate rather than inferring that residency or FP64 itself is
the bottleneck. TENSOR2 keeps its proposed 10% complete-path admission margin.

No historical criterion, certificate, source, timing result, charge or accepted
ADR is rewritten. RESIDENT2 is complete as a negative result, GPUP-8 remains
incomplete with scientific stages closed, and GPUP-9 stays gated. This revision
authorizes no new numerical execution, retry, resource transfer or publication.
