# GPUP-THROUGHPUT: Repeated-Solve Sessions, Setup Amortization and Amortized Throughput

Status: completed bounded research study, 2026-09-21, under
[ADR-0023](../decisions/ADR-0023-repeated-solve-throughput.md) and
[SPEC-0014](../specifications/SPEC-0014-lp-repeated-solve-throughput.md).
The [GPUP-5C report](lp-fp64-pipe-gpup5c.md) motivated this slice; its evidence,
every prior protocol, manifest, code object and archived artifact are unchanged.
Amortized repeated-solve throughput is a separately labeled endpoint throughout:
it is never substituted for, tabulated as, or merged into one latency table with
fresh-process single-solve latency, and the comparison below is titled as
separate endpoints (SPEC-0014 requirements 1-4, ADR-0013).

## Findings

1. **Batch solves are bitwise identical to fresh-process single solves.** Over
   all verified attempts, 4785 of 4785 compared pairs agree on primal and dual
   bits, logical iteration and restart counts, termination status and kernel
   launch count (requirement 15), for cuda-lp-tuned and both research modes, in
   repeat and variant batches at every size. Variant solves 0 and 7 agree with
   block G's fresh solves of the same materialized model. Between the two
   research modes the numerical trajectories agree 2451 of 2451 (launch counts
   differ by construction: two launches per proposal fused, six guarded).
2. **Setup dominates the fresh single solve.** Median device-context creation is
   207-325 ms of the 298-577 ms fresh-process single-solve latency on the
   development instances; preconditioning is 0.07-26.5 ms, research preparation
   0.01-19.5 ms, module load 1.4-4.1 ms and the invariant allocation/upload
   0.5-1.2 ms at these sizes. This is the cost GPUP-5C measured; nothing here
   changes it.
3. **Amortization works, and a batch of one does not.** The paired ratio of
   fresh single-solve latency to amortized per-solve time (separate endpoints)
   is 0.67-1.04 at N=1 across instances and configurations — the batch evidence
   machinery costs about what the saved setup returns. At N=8 the ratio is
   1.3-8.4 and at N=32 it is 1.5-26.6. The extreme is small-4 on tuned-fp64:
   414.4 ms fresh versus 15.6 ms amortized (26.6x, 64.1 solves per second),
   because its per-solve work is 2.6 ms against a 312 ms context.
4. **Per-solve session phases are negligible at study size.** Median per-solve
   engine_rebind is at most 0.09 ms, bound_upload about 0.02 ms, and
   variant_rebind (variant batches only) 0.002-1.4 ms up to 2048 rows — the
   full-variable-clone cost SPEC-0014's open questions name, measured rather
   than optimized. The residency's `uploads()` stays 1 for the session;
   rebinds are counted separately (device tests).
5. **The research sessions cost more setup, not more solve.** Their batches add
   research preparation and a heavier module load, so tuned-fp64 reaches the
   best amortized figures on every instance (for example irregular-2048 N=32:
   202.1 ms tuned, 355.4/370.3 ms fused/intguard); per-solve execution stays
   mode-typical.
6. **At 32768 rows the session does not pay off, and at 65536 rows it cannot
   finish.** On irregular-32768 the paired ratio is 0.65 at N=8: host
   preparation (preconditioning 457 ms plus research preparation 453 ms) is
   amortized, but per-solve evidence and certification on the large model leave
   amortized per-solve at 6.09 s against 3.95 s fresh. All 18 short batches on
   the three 65536-row instances (both kinds, three repetitions, N=8,
   research-fused-fp64) exceeded their 58-second reservations and were stopped
   without endpoint evidence; they remain charged and retained. ADR-0023 makes
   this negative result valid evidence.
7. **The 200-proposal short blocks terminate at the work limit everywhere**, on
   scheduling-50x10, ta001, ta011 and the extension instances, fresh and
   batched alike — the known convergence behavior of these instances, unchanged
   by batching. Their timing comparisons use complete equal-work batches; no
   short block claims a certificate.

## Fresh-process single-solve latency (primary endpoint)

Median worker elapsed milliseconds over three repetitions, tier 1e-9; all 81
development fresh attempts and all 48 fresh-variant attempts certified, all 39
fresh-short attempts verified with work-limit outcomes:

| Instance | tuned-fp64 | research-fused-fp64 | research-intguard-fp64 |
| --- | ---: | ---: | ---: |
| small-4 | 414.4 | 311.5 | 318.5 |
| small-16 | 349.9 | 298.3 | 304.5 |
| scaling-64 | 411.1 | 349.6 | 365.9 |
| scaling-256 | 434.6 | 406.2 | 436.4 |
| irregular-256 | 376.2 | 344.3 | 410.1 |
| irregular-2048 | 491.4 | 542.2 | 556.3 |
| dense_block-256 | 441.4 | 359.1 | 424.0 |
| dense_block-1024 | 444.7 | 474.9 | 496.4 |
| scheduling-20x5 | 577.1 | 495.8 | 558.7 |
| scheduling-50x10 (short) | 478.8 | 627.9 | 569.5 |
| ta001-relaxation (short) | 364.1 | 334.5 | 338.9 |
| ta011-relaxation (short) | 373.3 | 359.8 | 359.6 |
| irregular-32768 (short, research) | — | 3945.1 | — |
| irregular-65536 (short, research) | — | 8084.8 | — |
| dense_block-65536 (short, research) | — | 10446.2 | — |
| mixed-65536 (short, research) | — | 8068.6 | — |

## Amortized repeated-solve throughput (separate endpoint)

Median amortized per-solve milliseconds (batch elapsed / N) and paired ratio of
the fresh latency above to the amortized time — **separate endpoints: amortized
per-solve time is never single-solve latency**. Three batches per cell, all
certified except the work-limit short rows and the uncompleted 65536 rows.

| Instance | Config | N=1 | N=8 | N=32 | Ratio N=1 | Ratio N=8 | Ratio N=32 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| small-4 | tuned | 410.2 | 49.3 | 15.6 | 1.01 | 8.40 | 26.58 |
| small-4 | fused | 368.5 | 42.3 | 13.7 | 0.85 | 7.36 | 22.68 |
| small-4 | intguard | 359.0 | 47.8 | 15.0 | 0.89 | 6.67 | 21.20 |
| small-16 | tuned | 413.8 | 53.9 | 15.9 | 0.85 | 6.49 | 21.99 |
| scaling-64 | tuned | 461.8 | 92.3 | 59.4 | 0.89 | 4.46 | 6.92 |
| scaling-256 | tuned | 513.7 | 143.7 | 104.1 | 0.85 | 3.02 | 4.18 |
| irregular-256 | tuned | 442.3 | 79.5 | 45.7 | 0.85 | 4.73 | 8.23 |
| irregular-256 | fused | 370.3 | 97.2 | 61.4 | 0.93 | 3.54 | 5.61 |
| irregular-2048 | tuned | 676.7 | 247.0 | 202.1 | 0.73 | 1.99 | 2.43 |
| irregular-2048 | fused | 794.5 | 402.5 | 355.4 | 0.68 | 1.35 | 1.53 |
| dense_block-256 | tuned | 424.4 | 92.5 | 57.3 | 1.04 | 4.77 | 7.70 |
| dense_block-1024 | tuned | 587.3 | 194.6 | 158.7 | 0.76 | 2.29 | 2.80 |
| dense_block-1024 | fused | 692.4 | 314.8 | 269.0 | 0.69 | 1.51 | 1.77 |
| scheduling-20x5 | tuned | 619.3 | 284.3 | 252.3 | 0.93 | 2.03 | 2.29 |
| scheduling-50x10 (short) | tuned | — | 243.5 | 189.6 | — | 1.97 | 2.53 |
| ta001-relaxation (short) | tuned | — | 74.8 | 34.6 | — | 4.87 | 10.52 |
| ta011-relaxation (short) | tuned | — | 87.8 | 47.5 | — | 4.25 | 7.86 |
| irregular-32768 (short) | fused | — | 6092.3 | — | — | 0.65 | — |
| irregular/dense_block/mixed-65536 | fused | — | timeout | — | — | — | — |

Variant batches track repeat batches within a few percent at every size (the
variant_rebind phase above is the only added cost); the full grid, all
configurations, batch sizes 1/8/32 and the bootstrap intervals are in
artifacts/gpup-throughput-v1/analysis.json.

## Setup-cost breakdown and per-solve session phases

Median one-time setup milliseconds per batch (N=32, batch-repeat), and median
per-solve session-phase milliseconds:

| Instance | Config | device_context | module_load | preconditioning | research_preparation | invariant_allocation_upload | engine_rebind (per solve) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| small-4 | tuned | 312.0 | 1.4 | 0.1 | 0 | 0.5 | 0.0005 |
| irregular-256 | tuned | 266.9 | 1.4 | 3.3 | 0 | 0.6 | 0.0075 |
| irregular-2048 | tuned | 313.9 | 1.4 | 26.5 | 0 | 1.2 | 0.076 |
| dense_block-1024 | tuned | 325.0 | 1.4 | 14.9 | 0 | 1.0 | 0.065 |
| irregular-2048 | fused | 270.7 | 3.4 | 26.3 | 19.3 | 1.2 | 0.080 |
| dense_block-1024 | intguard | 270.5 | 3.5 | 14.8 | 16.0 | 1.1 | 0.066 |
| irregular-32768 | fused | 311.2 | 3.3 | 456.9 | 453.2 | 9.5 | — |

Variant batches add variant_rebind (0.002 ms on small-4 to 1.4 ms on
irregular-2048, the full-variable clone) and bound_upload (about 0.02 ms) per
changed solve; repeat batches upload only per-solve working state.

## Bitwise identity counts

Reported as counts, never asserted (requirements 15-17):

| Comparison | Identical | Compared |
| --- | ---: | ---: |
| repeat batch solves vs same-repetition fresh single | 4425 | 4425 |
| variant batch solves 0 and 7 vs block G fresh materialized single | 360 | 360 |
| fused vs intguard batch solves, numerical fields (launch counts differ by construction) | 2451 | 2451 |
| **total batch vs fresh** | **4785** | **4785** |

Every compared pair comes from retained evidence alone: each per-solve record
re-verifies independently against its re-materialized model bytes, and the
analysis recomputes every request, variant family and hash.

## Coverage and missing attempts

The frozen protocol planned 705 attempts; all 705 were admitted (none missing)
and 687 verified independently with the archived executables. The 18 unverified
attempts are the 65536-row N=8 short batches (batch-repeat-short and
batch-variant-short on irregular-65536, dense_block-65536 and mixed-65536, three
repetitions each): each hit its 58-second supervisor reservation timeout with
no endpoint written, charged and retained. No attempt failed verification, and
no reservation was exceeded before its timeout.

| Kind | Planned | Verified | Certified |
| --- | ---: | ---: | ---: |
| fresh | 81 | 81 | 81 |
| fresh-short | 39 | 39 | 0 (work limit) |
| batch-repeat | 243 | 243 | 243 |
| batch-repeat-short | 66 | 57 | 0 (work limit) |
| batch-variant | 216 | 216 | 216 |
| batch-variant-short | 12 | 3 | 0 (work limit) |
| fresh-variant | 48 | 48 | 48 |
| **total** | **705** | **687** | **588** |

## Completeness and budget

| Quantity | Value |
| --- | --- |
| Study GPU seconds | 2617.929459541 of 2700 |
| Acceptance GPU seconds | 538.371430691 of 600 |
| Combined slice seconds | 3156.300890232 of 3300 |
| Cumulative campaign seconds | 6951.059845871 of 8102.574545061 |
| Ledger events / SHA-256 | 8178 / dd957404ed65763775afba63bc11f8b03ffa9c64dcad19112f76fc9b1f5f32f6 |
| Preserved 6722-event prefix | ff6f1b5471e80791e964d1e6679017ea33593a7899718d0431f666cfaa5fa23b |
| Measured source tree | 6343d622025803e6e9637612c8fd05d30832b138788ab652fe5ed791f245b1ea |
| optimizer executable | 6498e4f3e126cd24d3bb2587dadd792857a4819ec44ac5f6ddbd3f009e087676 |
| Research executable | ec778ceeba80bc072525c4447863a46e892d72bc11fc94d151c088a4ab776e1e |
| Research code object | 6a743e1e745159f304168124800eec86891c641dfe9f18a91c0aa11d0555b7a2 (unchanged from GPUP-5C) |
| Analysis tool | 2916421b148e70ebb676a6e353fdf745fd1af8c9768fbcc66463070b3de40448 |

Measured on GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48 (RTX 5090), rustc 1.93.1,
release profile, dirty tree on commit 0d5d713; source.tar in the artifact
directory binds the measured tree. Every GPU job ran under the shared host
lease; all 728 new reservations (1456 ledger events) settled with none pending.

Acceptance charges: regular device suites on both binaries; all session_ cases
under memcheck, racecheck, initcheck and synccheck sequentially with zero
errors and zero race hazards; the research binary's research_ cases under all
four sanitizers; the pre-existing study_observation/matched_control/tuned_cases
filters under memcheck, initcheck and synccheck; and the CLI evidence check
including solve-batch, materialize, verify-batch and the pinned HiGHS fallback.
Retained failures: one stale-binary launch (exit 127), one run of three
session-test defects (fixed before all final evidence), two CLI-check failures
(the verify-batch tool rejected its own endpoint version; fixed), one
session-racecheck reservation timeout at 200 s (retried with a larger
reservation; passed in 116.8 s), and the device-filters racecheck below.

**Sanitizer coverage limitation.** The pre-existing-filters racecheck run
exceeded its 90-second reservation after study_observation (2 cases) and
matched_control (3 cases) had each passed with zero hazards, during
tuned_cases. The session_ scope SPEC-0014 requirement 34 mandates passed all
four sanitizers including racecheck (116.8 s), and tuned_cases passed the other
three sanitizers; only the pre-existing tuned_cases filter lacks a clean
racecheck receipt. The frozen 600-second acceptance cap had 61.6 seconds left,
which could not fit a rerun (the killed run had spent 26 s inside tuned_cases
with one of three cases done); the partial receipts are retained and this
paragraph records the gap rather than claiming it closed.

## What this evidence supports and does not support

- Sessions deliver exactly their contract: setup paid once per batch, cold
  iterates and fresh certification per solve, and bitwise identity with the
  fresh-process endpoint on every compared pair. Throughput gains at N>=8 on
  development sizes are real and bounded by the per-solve work.
- Sessions remain opt-in only. No selector, dispatch rule, default or preset
  routes a solve through a session; the fresh-process single-solve endpoint is
  unchanged and primary; amortized throughput stays its own labeled endpoint.
- At 32768 rows with short 200-proposal solves a session does not pay off, and
  at 65536 rows the frozen batch sizing could not complete N=8; using sessions
  there would need its own protocol, not a preset.
- No warm start, adaptive recovery, quantization, precision or tolerance change
  follows. GPUP-6 remains next and requires its bounded adaptive contract
  before behavior.

## Reproduction

`python3 tools/benchmark_lp_throughput.py --protocol benchmarks/configs/lp-throughput-v1.json`
refuses to rerun admitted attempts. `python3 tools/analyze_lp_throughput.py
--protocol benchmarks/configs/lp-throughput-v1.json` revalidates every endpoint,
request, variant family, identity count, ledger prefix and budget and
regenerates artifacts/gpup-throughput-v1/analysis.json. Acceptance scripts are
tools/lp_tuned_gpu_check.sh, tools/lp_research_gpu_check.sh and
tools/lp_gpu_cli_check.py under the shared lease.
