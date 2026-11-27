# FP4x2 PDLP overhead implementation

The four candidate optimizations are implemented in the isolated original-array
FP4x2 PDLP executor. CPU correctness passes; GPU correctness and complete solver
performance remain pending. **All four flags default off.** No default promotion
or end-to-end speedup is claimed.

The baseline is main `7a78e26`, including merged PR #30 (`d27d982`) and PR #31.
All 472 protected pricing, shared Rust and CUDA-interface source files match the
pre-edit manifest. All original low-bit sources are retained separately. The
pricing algorithm, kernels, dispatch choices and defaults are unchanged. This
work transfers overhead techniques to PDLP; it does not implement the pricing
algorithm in PDLP. Source preservation establishes isolation; it is not a new
measurement of pricing performance.

## Changes, in implementation order

1. **Resident preparation:** transfer solve-owned CSR/CSC device buffers through
   scaling, packing and execution, and retain packed fragments and geometry.
   Preserve the downloaded host mirrors, original kernels, capacity checks,
   zero-eligible fast path and hash-overflow/long-line fallbacks. No duplicate
   resident copy is introduced. Residual FP32 conversion remains on the host.
2. **Resident control:** skip redundant uploads of accepted, downloaded iterates
   and unchanged controller anchors. Preserve full uploads on initialization and
   recovery, exact reference re-anchoring, FP4 encoding, merit checks, restarts,
   work accounting and deadline rollback.
3. **Certificate workspace:** reuse bounded solve-local multiplier, enclosure and
   worker arrays, recomputing every certificate. Preserve the binary64 enclosure
   bits, canonical reduction tree, first refusal and multiplier repair. Workspace
   is released with the solve and its retained capacity is reported.
4. **Certificate overlap:** overlap one immutable snapshot's CPU proof with durable
   endpoint output. Join before accepting a result or advancing PDLP. Use at most
   three proof workers plus the writer; publish repaired-dual output afterward.
   There are no speculative solver updates or skipped assessments. Errors still
   join both tasks. Nested proof/output timings are not additive to complete cost.

Strict original-model **1e-9** feasibility, dual bound and gap checks remain.
Every potentially accepting GPU feasibility diagnostic still requires original
CPU feasibility with the same objective bits. Independent intermediate and cold
final proofs remain required. Default control100/certificate500 is unchanged.

The [executor README](../../research/lp-billion-lowbit/README.md) documents each
flag. The legacy document interface rejects these array-only options.

## Completed CPU validation

`fp4x2-overhead-quality-v1` passes formatting, all 73 isolated Rust tests,
Clippy with warnings denied, and release builds. The certificate differential
fixture compares 640 cases against the original scalar authority at each of
one, three and four workers: **1,920 comparisons**, including refusal paths.
Overlap tests cover actual concurrent progress, immutable snapshots, output
failure, proof failure and joining before return. Assessment tests retain the
CPU acceptance authority. Option/default and legacy rejection tests pass.

The corrected `fp4x2-overhead-report-check-v2` also passes eight new Python
comparison/promotion tests, eleven unchanged PR #30 pipeline and parallel-proof
tests, and the documentation build (413 pages, local links and anchors).

The original preparation, packing, solve and assessment CUDA files are unchanged.
The new Rust ownership/control integration still requires GPU continuations and
sanitizers before admission. A successful CPU build is not GPU correctness evidence.

## CPU certificate measurement

After the correctness gate, `fp4x2-certificate-measure-v1` measures three fresh
1,048,576-nonzero matrix shapes, six rotated repetitions each, against the
existing scratch checker. Every returned certificate matches exactly. Figures
are medians of per-repetition old-time/new-time ratios; values below one regress.

| Shape | Workspace, 4 workers | Workspace, 3 workers | Retained 4-worker capacity |
| --- | ---: | ---: | ---: |
| Short columns | 1.085x | 0.741x | 3,999,616 bytes |
| Balanced | 1.056x | 0.858x | 548,864 bytes |
| Long columns | 1.015x | 1.021x | 753,664 bytes |

These component timings include workspace allocation on the first call and
reuse on subsequent calls. They exclude solver preparation, GPU advancement,
endpoint output and cold independent final checking. Caches were not flushed;
there is one model per shape, and individual samples include regressions. The
three-worker cost must be offset by useful witness overlap before overlap can
improve complete time. None of these ratios justifies a solver default change.

[Compact results and raw samples](lp-fp4x2-overhead-results.json) retain the CPU
quality binding, all 18 samples, preservation counts and availability observation.

## GPU gate and remaining evaluation

The supervised read-only observation `fp4x2-overhead-availability-v1` finds about
74.3 GiB used on the pinned Pro6000. It fails the existing idle eligibility rule,
even with zero sampled utilization. No new GPU job or sustained-idle monitor is
started, and no other workload is signaled. No GPU speedup or PR #30 timing
nonregression is claimed.

The new evaluation helper contains a guarded correctness action for all 16 flag
combinations, actual FP4 work, zero-eligible fallback, long-line preparation
fallback, recovery, cancellation, deadline rollback, multiple requests, strict
independent endpoint checks and all four sanitizers. This GPU action is unrun.
It requires a fresh five-minute idle proof, the source-bound CPU gate and a
fresh existing-budget GPU reservation. Its request fixtures and runtime envelope
must be reviewed at admission; never reuse a started identity.

Only after GPU correctness may complete-cost benchmarking proceed. Compare the
old admitted image, new all-off path and cumulative candidate stages, with at
least three fresh seeds per family, rotated cold processes and separate witness
stores. Include input, preparation, solve, output and cold final proof; retain
all failed, uncertified and unequal-work outcomes. Require unchanged certificate
coverage, at least 5% median complete improvement, no family above 5% median
regression and no resource-limit regression before any default promotion.

## Resource and evidence accounting

All jobs use fresh identities under the original 570000 CPU / 68000 GPU totals,
exact phase caps, four slots and existing supervisors. New CPU jobs reserve
16 GiB host; no GPU seconds have been consumed by this follow-up. The initial
wrong Cargo cache check retains its full **480 CPU-second** failure charge.
The first reporting check passed eight new policy tests, then failed to import
SciPy for the unchanged pricing tests; its full **720 CPU-second** charge remains.
An isolated dependency environment corrects that launch setup. Native validation
totals **863.011299344 CPU seconds**. All completed new
reservations have no overrun and empty cleanup. Historical ledgers, frozen
helpers and scientific attempts are unchanged.

The initial binary seal retained exact bytes but omitted executable mode. A
separate successful CPU receipt restores only owner-execute bits before any
binary use, preserving all sealed hashes. No failed execution is hidden.

Private evidence remains in `/storage/ai-optimizer-billion-v1`, under the fresh
`fp4x2-overhead-*`, `fp4x2-certificate-measure-v1` and
`image-fp4x2-overhead-v1` identities. The image is labeled CPU-quality-only.
The [protocol](../specifications/SPEC-0046-amendment-94.md) records the scope,
unchanged shared limits, small planning-envelope correction and promotion rule.


The [CPU checkpoint](lp-fp4x2-overhead-checkpoint.json) retains every new completed
reservation, including both full failed charges, exact source preservation and
phase accounting. Its own final reporting reservation is shown separately until
that reservation settles. Temporary test dependencies and generated HTML copies
are removed after validation; binaries and all small evidence remain available.


## Subsequent component diagnosis

The [parallel assessment follow-up](lp-fp4x2-pipeline.md) reviews the complete
phase ledger and adds work-aware proof scheduling, host state reuse and actual
CPU-proof/GPU-diagnostic overlap. It retains the original results above and keeps
GPU admission and default promotion pending.
