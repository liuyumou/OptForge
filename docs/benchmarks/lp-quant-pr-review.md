# GPUP-7/7R PR review

This CPU-only review covers [PR #22](https://github.com/liuyumou/OptForge/pull/22),
including the GPUP-7 prerequisite absent from main and the resident GPUP-7R slice.
The [matrix study](lp-quantization-gpup7.md) and
[resident study](lp-quant-resident-gpup7r.md) remain exact historical reports.

Review reproduces mutation of coefficients/error summaries after generation
construction, partial promotion before invalid-ID refusal, and integer overflow
from a malformed device window. Prepared operators now expose a shared read-only
view, promotion validates IDs before changing state, and every returned window
counter is bounded before aggregation. Invalid windows retain the complete
checkpoint and conservatively charge the submitted window as device failure.

Standalone verification now rejects noncanonical enum/struct JSON representations,
incomplete or nonmonotone promotion histories, CPU device traffic and impossible
GPU launch/transfer counters. Shape admission also precedes microprofile engine
preparation. Profile comparisons require independently verified full horizons and
a completed worker with exit code zero. Review reports use a separate directory,
reject existing outputs and cannot overwrite historical reports through aliases.

The [PR source bridge](data/quant-resident/pr-review-source.json) records the exact
pre-PR commit, changed files and unchanged arithmetic/controller/authority bodies.
All CUDA sources/images, normal product/update bodies, accepted budgets and fresh
original-model certification remain exact. The rebuilt host executable has no new
device acceptance or timing claim. Historical admission remains bound to its
original executable; live execution admission does not accept the rebuilt source.

The full pinned-native gate passes 344 Python tests, Rust/native checks, dependency
checks, historical replay, 138 documentation pages and smoke. All CPU/docs/smoke
test commands run locally; GitHub Actions jobs cannot start because of its account
budget. Twenty quantization tests also pass in a source snapshot with no ignored
artifacts or native/CUDA dependencies. The [acceptance receipt](data/quant-resident/pr-native-acceptance.json)
and [retained-endpoint verification](data/quant-resident/pr-retained-verification.json)
record all 495 LP endpoints plus 21 operator endpoints. Local regression logs and
exact source diffs are retained under
artifacts/gpup-quant-pr-review-20261023, including failed reader preflights.

The initial 72-endpoint resident CPU cohort predates the required first-certification
field. It is freshly verified with its original frozen verifier; the rebuilt
verifiers cover the other 423 LP endpoints and all 21 operator endpoints. The
historical payloads are not normalized or re-signed, and the current strict schema
does not acquire an implicit missing-field exception. The original host authority
body is unchanged. The first attempt to use the new reader on that cohort is
retained as a reader refusal, with zero GPU work.

Two complete review passes leave no additional actionable findings. The current
reader is deliberately unable to reopen historical live-source GPU admission.
Reproducing either original study uses its preserved source/executable cohort;
reviewing its endpoints uses the separate CPU-only PR reader.

No GPU work is run. Preserve all 17132 ledger events, SHA-256
930de6771ab9bfbcb855bd05a07a58f6700aa1ade36bca09346790a94e7ff035,
cumulative charge 21359.585855789 seconds and every historical cap/prefix.
No quantized solve benefit or supported preset follows from this review.
