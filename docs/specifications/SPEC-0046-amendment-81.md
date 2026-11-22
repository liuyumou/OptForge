# SPEC-0046 amendment 81: prospective common solve window within approved reservations

Before freezing any new billion-scale cell, use a **1200-second common solver
allowance** for both selected COPT GPU PDLP and image-v11 FP4 requests. This
supersedes the provisional 600-second solver window in amendment 79. The outer
process reservation remains exactly 1800 seconds for both lanes. The full CPU/GPU
reservation worksheet, every phase cap, physical limit, ownership/idle guard,
certificate criterion and the complete approval chain remain unchanged. No extra
scientific repetition is added and no past result is regraded.

The original COPT billion attempts failed to reach logged GPU PDLP startup within
roughly 810–875 seconds of supervised activity. The new 64 M diagnostics show
that disabling scaling reduces startup, but also show that preparation remains
substantial and that faster startup need not improve convergence. A 1200-second
common window gives both solvers more opportunity to make progress after
preparation, within the process time already reserved and explicitly approved.
This is a prospective implementation choice within that allocation, not a new
allocation or an assertion that either solver will converge.

Both allowances start after original input loading, and include all solver
preparation. Input, output, teardown and the cold independent final proof remain
part of reported complete cost. The project keeps its 10000-update safety cap,
control100/certificate500, original strict acceptance logic, and at most the
already reserved twenty certificate intervals plus final/repaired-witness checks.
Every available intermediate assessment is independently audited. The same
10000-update endpoint-storage bounds and family-specific audit reservations apply.
COPT keeps its selected public parameters and unchanged strict tolerances.

The full freeze must bind this amendment, explicitly record 1200 seconds, and
write wall_ms=1200000 into both the request/accounting metadata and the vendor
allowance. Retain iteration-cap outcomes separately. Timely certification requires
both the original-model 1e-9 proof and actual solver elapsed time within 1200
seconds. A late accepted endpoint is never counted as a timely solve. Only jointly
timely, strictly certified pairs support solve-time ratios; all other outcomes
remain visible in the six-family roster.

Preserve the native timing-boundary difference explicitly: project input loading
also constructs its original CSR-to-CSC transpose, while the COPT adapter reports
its CSR-to-CSC conversion as preparation. Both operations count in fresh-process
and complete cost, and both lanes have the identical outer process ceiling.
Do not compare inner solver times as if they covered identical work, or omit
either conversion from end-to-end comparisons. The 1200-second native allowance
and 1800-second outer reservation are separate limits, not a claim that all
internal stage boundaries coincide.
