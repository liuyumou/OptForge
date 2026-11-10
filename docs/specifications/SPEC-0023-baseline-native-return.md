# SPEC-0023: Native-return baseline continuation

Status: accepted for the user-requested GPUP-BASELINE continuation.
Authority: [ADR-0052](../decisions/ADR-0052-baseline-native-return.md).
Extends [SPEC-0022](SPEC-0022-external-lp-baseline.md); historical artifacts keep
their original meaning. Scope: development comparison only.

1. Preserve all completed screening trials and strict admission outcomes. The
   executable roster is exactly the 117 unexecuted v4 screening cells. Models,
   native parameters, deadlines, repetitions and relative order do not change.
2. For cuOpt only, a returned Solution with `get_error_status()==0`, an empty
   `get_error_message()` and recognized non-error termination is a native-return
   pass. Recognized terms are Optimal, PrimalFeasible, PrimalInfeasible,
   DualInfeasible, UnboundedOrInfeasible, IterationLimit and TimeLimit. A limit
   remains a limit; an infeasible/unbounded claim remains unverified. NoTermination,
   NumericalError, unknown statuses, missing error information and API exceptions
   are not passes. Record the exact enum value and reason.
3. Persist native error/termination metadata immediately after Solve returns and
   before vector extraction/checking. Bind it to the canonical input and effective
   settings. Preserve native objectives, residuals, gap, raw dual vector and
   vector availability. Encode nonfinite diagnostic scalars explicitly; never
   replace them with numerical zeros or use them as certificate inputs.
4. Original primal feasibility and outward dual/gap checks remain at 1e-9.
   A native-return pass may coexist with a rejected or unavailable certificate.
   Retain the current dual normalization and label its unresolved presolve-only
   maximization mapping; do not silently repair it or blame the vendor.
5. A cuOpt native-return pass permits a successful comparison outcome without
   strict certification. A completed outer worker and usable primary clock are
   additionally required for complete-latency statistics. If the vendor returned
   but the checker/worker later fails, preserve the native observation while
   recording the outer failure and omitting a complete-latency success claim.
6. Other configurations retain their strict certificate policy. Publish native
   reason/error, transport/resource status, user-policy pass, certificate verdict,
   original objective, violated row/variable sides, maximum violation and allowance
   ratio, enclosed gap and GPU confirmation separately. Compare objective values
   to the matched project reference only as objective deviation, not proof of
   suboptimality when feasibility or certification fails.
7. All three repetitions must qualify for a reported median accepted latency or
   paired ratio. Publish native-return comparisons separately from certified
   comparisons and label unequal quality policies. Flag reused small-model v2
   versus new v5 transport as unmatched; do not present those ratios as controlled
   algorithm or GPU speedups. Keep every failed/missing cell in the denominator.
8. Reuse the pinned checker binary, installed vendor libraries, v4 compiled
   validation and numerical adapters for non-cuOpt configurations. New source
   snapshots bind the metadata-only cuOpt adapter and continuation coordinator.
   Validate source equivalence and new policy boundary tests before release.
9. Resource limits and charge preservation follow ADR-0052. A native-return pass
   never overrides a provenance/resource failure or supplies additional funds.
   A settled timeout is a completed attempted cell, not a successful solve.
10. Completion requires an explicit disposition of all 240 planned screening
    cells, with no unexecuted cells or unsettled reservations. No new model,
    held-out claim, production preset, GPUP-8 completion or GPUP-9 release follows.

Acceptance tests cover nonzero error status, nonempty error message, numerical
and unknown termination, no Solution, normal limits, infeasible claims, raw
metadata preservation, checker refusal with native success, outer failure after
native return, complete-pair reporting and exact unexecuted-cell selection.
