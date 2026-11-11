# ADR-0055: Prioritize approximate persistent multi-FP4 feasibility

Status: planning direction under the user's 2026-11-11 request and precision clarification
Owner: numerical backend and CUDA runtime
Last reviewed commit: b93ddc4c745a684c56915b3fb00e73c1447ec99b
Supersedes: MIXED2-first planning order in ADR-0054; no historical numerical contract
Implementation: [design assessment](../plans/lp-fp4-persistent-state.md), [roadmap](../plans/gpu-lp-precision-roadmap.md#persistent-multi-fp4-direction-2026-11-11), [backlog](../../state/backlog.yaml)
Acceptance: primary-source review, explicit numerical/cost gates, documentation links and unchanged historical evidence

## Context

The user wants multiple FP4 components to represent higher-precision values,
reconstruction-free iterations and fused kernels. They explicitly accept
approximate inner arithmetic with original-model FP64 residual checks and the
unchanged 1e-9 final certificate. Exact FP64-equivalent operations are not a
requirement. This permits a bounded approximate representation whose cost can
be compared with native and higher-precision component controls.

The [assessment](../plans/lp-fp4-persistent-state.md) links NVIDIA's instruction
and format documentation, recent FP4 matrix-product research, and retained
project profiles. The research supports feasibility of component products; it
does not establish persistent LP iteration correctness or latency. Historical
expanded execution spent most measured time outside its Tensor main product.
Removing repeated reconstruction and improving fused update cost is therefore
a concrete new hypothesis, while changing only operand precision is insufficient.

## Decision

1. Make GPUP-FP4-SPEC the next ready contract task. Define representation, error,
   projection, audit/recovery, hardware mapping and complete-cost admission before
   implementing arithmetic. Keep MIXED2 as a simpler alternative; do not require
   its completion before evaluating the user-selected FP4 direction.
2. Define the intended fast path as persistent component state without a routine
   per-update full FP64 reconstruction/re-encoding pass. FP32 accumulation, local
   component combination, normalization and explicit exceptions are permitted
   and charged. No claim of zero reconstruction work or automatic FP64 accuracy.
3. Require a new observation-only audit contract to preserve components across
   windows. Keep existing 200-update controller observations and independent
   original-model checking; checkpoint all component and controller metadata.
   Cross-window error and recovery semantics must pass CPU admission. The
   reference-adoption semantics of ADR-0046 remain unchanged for old candidates.
4. Fuse each product with its legal update/projection/encoding epilogue, while
   respecting whole-vector dependencies and reduction completion. A monolithic
   persistent kernel is optional and requires its own synchronization/resource
   argument. Local block synchronization cannot substitute for a global dependency.
5. Count component cross-products, scales, both operator orientations, sparse
   tails, encoding, accumulated-error control, spills, corrections and fallback.
   Projections act on the represented value, not each component separately.
   Require a meaningful FP8/FP16 component comparison so a gain can be attributed
   to FP4 as well as to persistence/fusion. Use native FP64 as the delivery control.
6. Add GPUP-FP4-PROTO after the specification: independent CPU validation first,
   then separately admitted device acceptance and bounded fused-iteration profiles.
   Reorient conditional GPUP-TENSOR2 toward this candidate after prototype/cost
   admission, keeping its proposed 10% complete-path screening headroom. Numerical
   refusal, pervasive promotion or overhead that erases the saving stops progression.

## Limits and consequences

Small component counts are hypotheses with explicit approximation error, not
universal binary64 replacements. Strict certification proves only the delivered
endpoint; it does not by itself prove convergence, safe persistent audits or a
performance gain. Normal-limit transport, native success and mathematical
acceptance remain distinct. The mixed-model bound refusal is not solved here.

The result is a prioritized research plan, not implementation acceptance or a
supported preset. Cold latency remains primary and prepared/batched throughput
separate. DELIVERY2 remains a conditional alternative under ADR-0054. Preserve
all historical sources, reports, failed charges and criteria. GPUP-8 remains
incomplete with science closed; GPUP-9 stays gated. No next-stage CPU/GPU execution,
historical retry, resource transfer, installation, push or publication is released.
