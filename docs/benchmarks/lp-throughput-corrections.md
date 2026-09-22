# GPUP-THROUGHPUT review corrections

Status: implemented and measured, 2026-09-22, under
[ADR-0024](../decisions/ADR-0024-throughput-review-corrections.md).
This closes the four findings in the [branch review](lp-throughput-review.md).
The original study, source archive, executables, protocols and analysis remain
unchanged. Corrected evidence lives in artifacts/gpup-throughput-controls-v1.

## Correctness and evidence repairs

- Tuned session outcome identity is now applied outside the outcome-producing
  body. Early cancellation and all device-failure returns therefore receive
  backend cuda-lp-tuned, record version 3, method and execution identity.
- The tuned batch verifier requires a common method and execution/code identity
  across attempted records, rejects missing identity and forbids fallback.
  Per-call solve options remain per solve. Mutation tests use individually
  valid endpoints with different method settings, different code objects, or
  a HiGHS fallback: each combined directory is refused.
- Identity counting compares binary64 encodings recursively. It distinguishes
  positive/negative zero and retains integer fields exactly, including counts
  above 2^53. Historical N=1-session comparisons are labeled accordingly.
- The new fresh-variant-single block materializes on the CPU, then measures an
  ordinary solve of those bytes. The historical fresh-variant block remains an
  N=1 session. Analysis refuses to overwrite an existing result.

## Independent fresh-variant controls

The frozen [follow-up protocol](../../benchmarks/configs/lp-throughput-controls-v1.json)
contains the original block G's 48 cells: eight witness instances, variants 0
and 7, three configurations (tuned FP64, fused FP64 and integer-guarded FP64),
tier 1e-9 and one repetition. Seeds, variable changes, controller, method,
tolerances, code objects and limits match the original study. Materialization
precedes the measured worker; each measurement is the ordinary fresh-process
single-solve endpoint on the resulting model.

**48/48 controls completed and verified. All 360/360 eligible retained variant
batch solves agree with those ordinary single solves on binary64 primal/dual
encodings, iteration and restart counts, status and launch count.** There are
no missing controls or comparisons. All 48 controls certified successfully.
The comparison separately re-verifies each selected historical per-solve record
against the corrected control's re-materialized model. Historical tuned records
also match the expected method, options and execution/code identity.

The 360 historical comparisons against N=1 sessions remain valid checks of
session reuse, but are not ordinary-single controls. The new 360 comparisons
close that study gap without rewriting the old runs. The original 4,425 repeat
comparisons already used ordinary single solves; a separate original-study
reanalysis verifies 687/705 endpoints and confirms 4,425/4,425 repeat pairs,
360/360 historical N=1-session pairs and 2,451/2,451 cross-mode pairs using the
corrected bit comparator and explicit partner labels.

Evidence: `corrected-comparisons.json` and `original-reanalysis.json` in the new
artifact directory. Reproduce the independent comparison with:

```sh
python3 tools/analyze_lp_throughput_controls.py --output /tmp/throughput-controls.json
python3 tools/analyze_lp_throughput.py --output /tmp/throughput-original-reviewed.json
```

These commands are CPU-only and require previously retained evidence. Both
refuse an existing output path. The study runner refuses re-admitted attempts.

## Acceptance and resources

Full pinned-native tools/check.sh passes; targeted Rust and Python regressions
cover the four fixes. A device-gated end-to-end cancellation test constructs a
real TunedSession, cancels before its first launch, builds its endpoint and
verifies it. It passes normally and under memcheck, racecheck, initcheck and
synccheck, with zero errors/hazards. These are scoped outcome tests; the old
uncompleted tuned_cases racecheck receipt is not relabeled as a pass.

| Quantity | GPU seconds |
| --- | ---: |
| New 48-control study work | 28.047680157 |
| New scoped acceptance | 3.300520728 |
| Total gpupt study / original cap | 2645.977139698 / 2700 |
| Total gpupt acceptance / original cap | 541.671951419 / 600 |
| Total gpupt combined / original cap | 3187.649091117 / 3300 |
| Cumulative campaign / original ceiling | 6982.408046756 / 8102.574545061 |

Every GPU job used the shared lease and the original ledger, with no new
allowance. The 8276-event ledger SHA-256 is
`b3451186b7a5fc0029fbbd612b07e795072476ab76137a78a375b1d97866c236`;
the 8178-event prefix remains
`dd957404ed65763775afba63bc11f8b03ffa9c64dcad19112f76fc9b1f5f32f6`.
The original 6722-event prefix is also retained. Measured source identity:
`73936de19b351cc4f89328355c49fbcba7acf38024854067b0c004809bcaca6b`.
The source, executables, code objects, jobs, per-attempt receipts and ledger
snapshot are retained with the new protocol. No numerical kernel changed.

These corrections establish the missing controls and repair evidence handling.
They introduce no new throughput claim or supported preset. The host verification
optimization measured in the earlier review remains a CPU-only result.
