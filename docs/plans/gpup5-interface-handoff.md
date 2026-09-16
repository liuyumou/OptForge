# GPUP-5 interface handoff

Status: recommendation recorded at the maintainer's request on 2026-09-16;
interface decision and precision contracts remain pending.
Next task: [GPUP-5](../../state/backlog.yaml), after completed GPUP-4.
Contracts: [SPEC-0012](../specifications/SPEC-0012-mixed-precision-lp.md),
[ADR-0012](../decisions/ADR-0012-opt-in-lp-precision.md),
[ADR-0017](../decisions/ADR-0017-tuned-fp64.md).

## Recommendation

Keep the existing GPU backend identities for compatibility and reproducible
research. Consolidate future experimental precision choices into versioned
settings on one experimental implementation, instead of adding a public backend
name for every precision or optimization. Three GPU names are useful controls
at this stage, but multiplying them through FP32, FP16/BF16, FP8, recovery and
Tensor Core variants would make selection, testing and replay harder to maintain.
The current GPU choices already share the `CudaLpBackend` implementation.

| Existing choice | Role to preserve |
| --- | --- |
| `cuda-lp` | Frozen legacy execution and old-record compatibility. |
| `cuda-lp-matched` | Shared-controller FP64 numerical reference for comparative work. |
| `cuda-lp-tuned` | Explicit experimental execution settings and optimization work. |
| `host-lp` | Independent CPU arithmetic oracle and comparison. |
| Pinned HiGHS | Authoritative fallback, explicitly identified as the executed backend. |

GPUP-4 can merge independently of this interface decision. Its
[report](../benchmarks/lp-tuned-fp64-gpup4.md) keeps matched as the general reference;
the three scoped provisional fusion results are not supported presets. Existing
names, defaults, arithmetic and recorded replay semantics remain unchanged.

## Decisions required before GPUP-5 behavior

1. Revisit the reserved, currently unavailable `cuda-lp-quantized` selector in
   SPEC-0012 and the roadmap. Prefer extending one experimental interface through
   explicit versioned settings; determine whether its public name remains
   `cuda-lp-tuned` or needs a compatibility-preserving replacement. Accept the
   specification and any necessary ADR amendment before exposing the decision.
2. Specify the relationship between method, execution and precision settings.
   Keep storage, product, accumulation and working-state precision explicit and
   validate supported combinations. Capability declarations must describe actual
   mixed arithmetic; they must not claim FP64-only execution for an FP32 path.
3. Define new record/schema versions, code-object selection and replay rules before
   adding fields. Preserve solve-record v2/v3 and endpoint v1/v2/v3 emission and
   reading for their existing configurations, with migration and altered-provenance
   fixtures. Old records must retain their original settings and numerical meaning.
4. Keep matched FP64 stable and put new optimization in the experimental executor.
   Share internal plumbing where appropriate without changing legacy or matched
   trajectories. Record requested settings, executed arithmetic and pinned fallback
   separately, including device work attempted before fallback.
5. Leave supported presets and any public-name simplification to evidence-backed
   later decisions. GPUP-9/10 owns final selection; automatic dispatch is separate.
   A future deprecation must include a documented compatibility/replay policy.

This handoff does not accept a new selector, precision schema, default, recovery
policy or runtime behavior. GPUP-5 starts by resolving its interfaces and accepting
its bounded contract. Then implement its FP32 comparisons and required acceptance
and study evidence under the [roadmap](gpu-lp-precision-roadmap.md).

## Evidence and budget to carry forward

Preserve GPUP-1 independent exact-rational certification/gap regressions, existing
matched trajectories, original-model host authority, ordinary toolkit-free builds,
and the existing unsafe boundaries. Reuse the complete GPUP-4 evidence and retain
its negative results and convergence failures; do not infer a general winner.

Carry forward **902.574545061 campaign GPU seconds**, including GPUP-4's
456.586499157 and the earlier 445.988045904. Preserve the canonical ledger's
original authority, output binding, complete history, archived source/executables
and code objects. GPUP-4's cumulative ceiling was 1345.988045904 seconds; do not
interpret unused allowance as approval for an unfrozen GPUP-5 study. Declare the
next slice's study and separate acceptance budgets before work, within the global
28800-second campaign cap. Raw evidence lives in ignored `artifacts/` directories;
branch cleanup must retain those directories and the reference commit history.
