# PREP3: final-source attribution and exact preparation

Status: prospective CPU-only protocol; execution and allocation not opened
Owner: LP research
Introduced: GPUP-8-DISPOSITION / ADR-0076
Last reviewed commit: bootstrap
Implementation: future isolated research executor; current sources remain exact
Acceptance: CPU exactness, source/target factorial, preparation cost and stop decision

## Question and scope

Measure how much of the final CHECKER2 CPU improvement comes from source and
how much from the host target, then test one evidence-selected exact preparation
change. Both native and FP4 must receive shared host improvements. This task
does not run GPU solves, establish full-session speedups or pass
[GPUP-CERTIFIED-COST-GATE](../decisions/ADR-0076-gpup8-disposition.md#replacement-progression-gate).
It preserves original validation, binary64 values, error order, model identity,
certificate authority and full-range fallbacks; it permits no endpoint-answer cache.

The CPU plan is deliberately bounded before considering larger GPU problems.
Dense generic/coupled 1024/2048 remain development fixtures. Their labels are
those of the MIXED2 generators, not the older dense-block-65536 manifest. Larger
fixtures, production workloads and an unseen holdout are outside this roster.

## Frozen controls and measurements

1. Before comparative measurement, bind the exact CHECKER2 original baseline
   source and **final guarded-product** source from the retained admission
   snapshots, pinned toolchain/dependencies, model bytes, endpoint/tier corpus,
   CPU capability record and strict floating-point flags. Build each source with
   the portable target and `x86-64-v4`: four executables. The earlier tree checker
   is not the final source. An unsupported host refuses v4 admission.
2. Independently compare all four builds' validated model inspections and all
   original serial checker fields, including signed zero, malformed/nonfinite
   input, overflow, extremes and guarded fallback. Run the native gate and
   relevant isolated CPU/process tests with CUDA hidden. Any mismatch stops
   performance admission; retain source, failure and full charge.
3. Freeze 16 independent blocks, seed 430076, the four existing families, four
   builds and two CPU endpoints: preparation from original bytes through ready
   ownership, and a fresh checker process performing the same twelve retained
   assessments, six per tier, then exiting. This is **512 measured process
   executions** (16 x 4 x 4 x 2), not 512 solver sessions. Bind the exact twelve
   request identities per family before launch. Label the builds A (old portable),
   B (old v4), C (final portable), D (final v4). Repeat balanced orders ABCD,
   BDAC, CADB, DCBA four times per family/endpoint, shuffling block assignments
   from the frozen seed. Every build occupies each position four times and every
   pair has eight observations in each order. Include startup and teardown; preserve
   complete spans as well as separately labeled internal diagnostics. No device
   or kernel timing is inferred.
4. Report source effects at each target and target effects for each source, plus
   the interaction. Preserve per-block values, medians, both order strata and
   failed/missing cells. For four families x two endpoints x four direct
   contrasts x ratio/saved-time endpoints, use 64 simultaneous exact median
   intervals at familywise alpha .05. With 16 blocks the interval from ordered
   observations 2 and 15 has per-endpoint noncoverage 34/65536, sufficient for
   that Bonferroni family. This protects coverage conditional on independent
   blocks; shared-host activity and temporal dependence remain limitations.
   Interaction is descriptive; no selection claim uses
   it. Partial coverage suppresses a factorial confirmation, never drops cells.
5. Use separately timed CPU spans to locate parsing, validation, model building,
   norms, hashing, original-buffer lifetime and checker startup costs. Do not
   add overlapping spans or infer cache/scheduler causes from elapsed times.
   The existing aggregate setup/checker shares identify priorities only.

## One preparation candidate

After the factorial diagnosis, select at most one exact preparation design on
measured cost grounds. Specify its ownership/validation/error contract before
implementation. Keep the final CHECKER2 source as control and one identical
compiler target for both executables. No numerical solve, device image, audit
schedule or original certificate changes are allowed. Preserve rejected versions.

Admit exact model inspections, error behavior, CPU process lifecycle and the
original serial certificate corpus first. Then freeze a **new** 16-block,
four-family, two-executable preparation cohort, seed 430077: 128 process
executions, separate from development and the factorial. Balance eight control-
first and eight candidate-first pairs per family. Across four ratios and four
absolute savings, use simultaneous exact median intervals at familywise .05.
For 16 blocks, ordered observations 3 and 14 suffice (noncoverage 274/65536
per endpoint). Scoped CPU value requires speedup lower bound >1 and preparation
savings lower bound >10 ms for both preselected 2048 families, with each 1024
guard speedup lower bound >1/1.05 and identical correctness/coverage. The 10 ms
floor is a development screening value, not a production SLO. Failure or
inconclusiveness is a valid negative disposition and does not release device work.

Estimate a subsequent complete-cost opportunity using retained **same-cell**
disjoint spans, label unchanged-work and zero-overhead assumptions, and include
native as well as FP4. A forecast is not measured full-session performance. A
favorable CPU result may support proposing a separate cold/prepared study with
the final source/target factorial at the full lifecycle boundary. That later
study must freeze its own coverage, guards, value floor, power case and budget.
Current compiled v4 results cannot support other-host portability claims.

## Prospective resources and stopping

| CPU phase | Ceiling, CPU seconds |
| --- | ---: |
| Implementation and admission preparation, including 512 admin | 4096 |
| Native and isolated correctness/process acceptance | 8000 |
| Four-build factorial, including builds and diagnostic spans | 6000 |
| One candidate and independent preparation comparison | 4000 |
| Reporting, preservation and closure, including 128 closing admin | 1904 |
| **Total** | **24000** |

GPU allocation is **zero**; hide CUDA for all jobs. Use four CPU slots, the
unchanged one-second supervisor, 5–10 ms target, all >100 ms advisories, 16 GiB
sampled aggregate RSS and no historical fund transfer. Reserve four times each
job's wall deadline as CPU seconds, including teardown/finalization. Failed
jobs retain the full reservation and sources. Sampled RSS cannot enclose peaks.
Receipts will use a new `artifacts/gpup-prep3-v1` allocation.

Before freezing either cohort, measure bounded admission costs and show that
every cell plus reporting/cleanup fits its phase cap. If it does not fit, stop
before freezing and report infeasibility; do not shrink the roster after seeing
timings. Freeze all sources, binaries, requests, order and analysis. A scientific
cell cannot be retried. Preserve every refusal and partial file. Resource overrun,
loss of supervision or nonempty cleanup closes execution for disposition.

Completion requires a complete positive, negative or explicitly incomplete
report, original-source/byte preservation, reproducible CPU measurements and
empty cleanup. No public defaults, GPU allocation, GPUP-9 release or scientific
regrading follow. This plan is proposed for the next task, not an active budget.
