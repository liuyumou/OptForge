# ADR-0047: Prioritize certified solve cost over exact low-precision emulation

Status: accepted roadmap direction under the user's 2026-11-10 request;
new scientific protocols and resource allocations remain pending.
Owner: numerical backend and experiment tooling.
Introduced: system diagnosis and roadmap revision.
Last reviewed commit: `396bd0e2ea095f1d038dfa862bb31f29a61e0d68`.
Supersedes: forward planning order in the GPU LP roadmap only.
Superseded by: none.

## Context

The project aims to exploit modern GPUs' low-precision computation to accelerate
optimization. The latest GPUP-8 candidate passes corrected proof and device
acceptance but is incomplete after a large-model profile timeout. Retained small
profiles spend most time in expanded reconstruction and vector updates. Tensor
main-product acceleration has little influence on their total cost. Earlier
FP32, refinement and resident-quantization attempts also show that cheaper
arithmetic can be outweighed by failed convergence or guards.

The [diagnosis](../benchmarks/lp-system-diagnosis-2026-11-10.md) gives the evidence,
limits and commercial-solver comparison. The user requests a concrete roadmap,
permits cuOpt installation and states that Gurobi is unavailable.

## Decision

1. Keep certified single-solve latency the primary objective. Count preparation,
   transfers, all iterations and rejected work, recovery, postsolve, independent
   original-model assessment and delivery. Report warm throughput separately.
2. Establish cuOpt and local COPT comparisons before selecting another precision
   recipe. Use a common original model and checker. Report both forced comparable
   algorithms and portfolio defaults, with explicit resource/settings differences.
   Gurobi remains an optional future comparator, outside the critical path.
3. Prioritize bounded device-resident execution and setup/checker cost reductions.
   Preserve error propagation, controller observations, rollback and cancellation.
   A changed observation schedule requires a new contract; it is not an
   optimization that can silently reuse historical acceptance.
4. Make conventional mixed precision the next numerical candidate: first measure
   FP32 matrix storage with FP64 state/arithmetic against native FP64, then consider
   bounded lower-precision state and residual-driven escalation. The original
   matrix remains authoritative. A separate protocol must define errors,
   convergence, fallback and useful nonzero work before implementation.
5. Keep exact expansion as a reference, validation instrument and optional special
   path. Do not require full-range exact emulation in every fast-path update.
   This changes future research priority, not the accepted GPUP-8 arithmetic.
6. Admit another Tensor candidate only after a cost model includes packing,
   component multiplication, reconstruction, guards, transfers and convergence.
   Use dense structure or multiple right-hand sides when beneficial; retain a
   sparse SIMT/native alternative. Multi-right-hand-side work is a throughput
   experiment, not a replacement single-solve result.
7. Add presolve/postsolve, algorithm portfolios and search integration as explicit
   later work. Presolve needs reversible maps and independent validation on the
   original model. Search integration needs a relaxation/bound/warm-start contract
   and full MILP measurements, not only a fast LP kernel.

The next ready task is CPU-only comparison-contract preparation, `GPUP-BASELINE-SPEC`.
The [roadmap](../plans/gpu-lp-precision-roadmap.md#current-plan-2026-11-10) assigns
the subsequent tasks, prerequisites, evidence and stop decisions. These new tasks
are engineering investigations, not an authorization to run GPUP-9 early.

## Invariants and authorization boundary

Historical ADRs, numerical implementations, artifacts, source images, failed
attempts, resource charges and completion criteria remain immutable. GPUP-8 is
incomplete and its scientific stages remain closed. GPUP-9 remains gated.
Unused historic CPU/GPU allowance supplies no automatic retry or new allocation.

Documentation and an isolated optional cuOpt installation are authorized now.
Installation does not establish device acceptance or solver correctness. Each
future numerical task needs a versioned protocol, frozen workload, independent
checks, resource envelope and explicit execution authority. If a future result
supports terminating GPUP-8 as a negative investigation, a separate accepted
disposition must change the progression gate; this ADR does not mark it passed.

The historical 1e-9 final certification requirement and GPUP-8 gain threshold
remain unchanged. Any proposed 1e-6 or 1e-4 application-quality tier must be a
separate experiment and cannot satisfy the strict tier. A vendor's `optimal`
status is insufficient without the required project checker.

## Alternatives

| Alternative | Decision and reason |
| --- | --- |
| Continue widening exact Tensor emulation immediately | Defer: reconstruction dominates and wider components amplify work; no credible full-path gain case yet |
| Extend the timed-out profile deadline | Not authorized here; operational completion alone would not resolve the measured small-model cost problem |
| Drop checks or weaken tolerance to show a gain | Reject: changes the endpoint and mathematical authority; separate quality tiers may be proposed transparently |
| Treat the existing project/COPT timing table as sufficient | Reject: adapter/checker cost and constrained resources prevent a broad competitiveness claim |
| Replace the project wholesale with cuOpt | Defer: use it first as a baseline; external solutions still need the project's independent acceptance |
| Wait for Gurobi | Reject as a dependency: cuOpt and COPT can support the next comparison |
| Focus only on batching | Retain as a separate track; useful throughput does not answer the primary latency objective |

## Consequences

Low precision remains central, but the method is allowed to use native FP64 where
it lowers the cost of a certified answer. No Tensor family is guaranteed promotion.
The project gains an explicit route for negative results, with a small admission
study before a large campaign. Conventional mixed precision may also fail; that
is a reason to retain native and external fallbacks, not to hide coverage losses.
Broader presolve and commercial feature parity are substantial independent work.

## Implementation and tests

This delivery changes planning, navigation and setup evidence only. Authorities:
[backlog](../../state/backlog.yaml), [active task](../../state/active-task.md),
[diagnosis](../benchmarks/lp-system-diagnosis-2026-11-10.md),
[cuOpt setup](../operations/cuopt.md). Acceptance uses documentation links,
dependency consistency, installation/package checks with GPUs hidden, and
preservation of historical numerical files and evidence. Full native/device
acceptance is not claimed or rerun for this documentation delivery.
