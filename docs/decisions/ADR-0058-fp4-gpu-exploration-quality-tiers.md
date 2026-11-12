# ADR-0058: Separate FP4 GPU exploration from solver qualification

Status: accepted planning amendment, 2026-11-11
Owner: numerical backend and CUDA runtime
Last reviewed commit: bootstrap
Implementation: [roadmap](../plans/gpu-lp-precision-roadmap.md#fp4-gpu-exploration-and-quality-tiers-2026-11-11), [backlog](../../state/backlog.yaml)
Acceptance: documentation/dependency/history checks in [active task](../../state/active-task.md)

## Context and user authority

The user accepts the recommendation to separate CPU recovery, a bounded FP4 GPU
feasibility experiment and a subsequent certified solver comparison. They also
state that achieving a **1e-7 final certificate** is encouraging if FP4 makes the
computation sufficiently faster. The 1e-9 strict tier remains available.

The [frozen prototype attempt](../benchmarks/lp-fp4-proto-gpup-fp4-proto.md) has
nine enclosure-guard and three metadata refusals. It neither qualifies a solver
nor measures GPU performance. ADR-0057 made the complete 600-update CPU trajectory
gate a prerequisite even for device implementation. That sequencing prevented
measurement of the hardware questions the user wants answered. The monotone
1e-7 *inner iterate-error enclosure* in SPEC-0025 is not a final LP certificate.

## Decision

1. Make **GPUP-FP4-GPU-PILOT** the next ready task, dependent on completed
   GPUP-FP4-SPEC, not on GPUP-FP4-RECOVERY-SPEC or the failed 600-update admission.
   Its first work freezes the concrete protocol, source/device/compiler mapping,
   workload, measurements, stop rules and independent CPU/GPU resource envelope.
   Corrected CPU primitive/packing/transpose/projection tests precede device
   execution. Actual-instruction smoke and differential tests precede fused
   iterations; failure/cancellation/rollback and four scoped sanitizers precede
   profiling. No full trajectory-enclosure proof or positive complete-solve
   forecast is required merely to measure bounded exploratory kernels.
2. The pilot implements actual FP4 component products and legally fused
   primal/dual updates with persistent component state. It retains the phase
   dependency and avoids routine full-state FP64 reconstruction during updates.
   It measures local numerical errors and short bounded trajectories, useful and
   padded work, component pairs, packing/scales/normalization, sparse tails,
   single-RHS utilization, registers/spills, launches, copies and audit costs.
   Compare native FP64 and matched FP8/FP16 component controls, plus fusion and
   persistence ablations. Full error bounds or convergence may remain unresolved:
   label such results empirical and uncertified. A fast kernel is not a faster
   certified solve. Unsupported ISA, primitive/device mismatch, unsafe execution
   or resource failure stops the affected stage with its full recorded cost.
3. **GPUP-FP4-RECOVERY-SPEC** remains independently ready. It addresses the local
   rounding/encoding defect and specifies a credible precision/error/recovery
   policy. A tighter proved coupled bound is one option; a separately specified
   residual-driven operational guard is another. The latter must not claim a
   proved iterate-error enclosure: its certification authority remains the
   independent original-model final checker. CPU recovery and the GPU pilot have
   no ordering dependency; any concurrent execution still needs admitted resources.
4. Add **GPUP-FP4-INTEGRATE** after the pilot and recovery contract. Implement
   and validate the selected error/progress policy, observation-only original-A
   FP64 audits by 200 updates, complete checkpoints, bounded cancellation,
   explicit escalation/correction and native recovery. Nontrivial trajectory,
   failure and independently checked endpoint tests admit this new solver
   variant. A replacement policy needs a new executable specification and
   source-bound evidence; the old twelve cells are never relabeled as passes.
   This integration gate replaces the old incomplete prototype as the future
   prerequisite for GPUP-TENSOR2, without marking GPUP-FP4-PROTO complete.

## Quality and speed criteria

Use three explicitly different result categories:

| Category | Numerical authority | Permitted conclusion |
| --- | --- | --- |
| GPU exploration | Admitted primitives/safety; measured local and trajectory error, potentially no final certificate | Hardware/kernel feasibility and measured costs only |
| `certified-1e-7` | Original-model independent checker, absolute and relative target tolerances both 1e-7 | Encouraging approximate-solve result when the matched speed/coverage criterion passes |
| `certified-1e-9` | Original-model independent checker, absolute and relative target tolerances both 1e-9 | Strict certified-solve result under the retained quality target |

The future checker variant must retain the same feasibility, dual/bound authority,
objective offsets, conservative gap enclosure, normalization and nonfinite/refusal
rules. Only explicit target tolerances differ. Freeze and test the tolerance
parameterization before a new cohort. A native return, small iterate difference,
or inner 1e-7 bound is never a final certificate. Existing checker defaults and
all historical 1e-9 outcomes remain unchanged. Keep separate assessments at both
tolerances when the necessary endpoint evidence is available; failure at 1e-9
does not disqualify an otherwise eligible 1e-7 result or become a strict pass.

For the initial future solver study, retain **at least 1.10x cold model-median
geometric-mean speedup**, no certified model-median regression, and no loss of
certified coverage relative to the matched native control **at the same target
tolerance**. Report all failures/limits, repetition ranges and uncertainty; a
gain indistinguishable from timing variability is inconclusive. This is the
initial roadmap threshold for "sufficiently faster", not a measured gain or a
claim that 1e-7 and 1e-9 have equal quality. Larger gains are desirable; any
revised threshold must be fixed before the cohort, never selected from results.

FP64 controls must also target 1e-7 for the 1e-7 comparison. Comparing FP4 at
1e-7 with native at 1e-9 is a separately labeled quality/time tradeoff, not an
FP4 acceleration claim. Matched FP8/FP16 controls and fusion/persistence ablations
help distinguish benefits of FP4 from lower accuracy or changed execution.
Time-to-certificate includes setup, iteration changes, audits, correction/fallback,
export and checking. Record the earliest actually checked crossing only when
instrumented; a later endpoint cannot supply an invented earlier completion time.
Cold latency and prepared throughput remain separate.

GPUP-TENSOR2's new protocol must freeze both quality cohorts, stopping rules,
paired order, roster, coverage/uncertainty rules and complete resource reservations.
A conservative complete-cost screen precedes that campaign, informed by pilot
measurements; it does not block the pilot that supplies missing cost information.
The old 192-cell/288-endpoint SPEC-0025 proposal remains exact. A dual-tier campaign
needs a new identity and explicitly enumerated cells/endpoints; no implicit
doubling, execution, rechecking or reinterpretation of the old proposal follows.

## Scope and consequences

This decision supersedes ADR-0057's blanket pre-device trajectory dependency for
the **new pilot and integration path**, and supersedes the strict-only future FP4
planning scope of ADR-0055/0056. It does not alter their historical executions,
SPEC-0025/0026, sources, outcomes, failures, charges or closed resource envelopes.
The new 1e-7 tier is limited to future explicitly identified FP4 comparison work;
native public defaults, MIXED2 and other historical study criteria do not change.

The present task changes documentation only, with an independent 512 CPU / zero
GPU envelope: 128 preparation/receipt packaging, 320 validation and 64 cleanup,
four CPU slots and 6 GiB sampled RSS. No numerical job, scientific retry, hardware
profile, held-out access, supported preset or publication is released now.
Future task implementation starts with a concrete admitted resource package;
old unused funds do not authorize it. Native control remains supported, GPUP-8
remains incomplete and GPUP-9 gated. Commit this planning update locally.
