# GPUP-5C: Integer Guards, Fused Launches, Double-Float Pairs, Tolerance Tiers and a Larger Corpus

Status: completed bounded research study, 2026-09-19, under
[ADR-0022](../decisions/ADR-0022-fp64-pipe-execution-and-tolerance-tiers.md).
The [root-cause note](lp-fp64-pipe-root-cause.md) motivated this slice; the
[GPUP-5B report](lp-exact-components-gpup5b.md), its evidence and every v1 manifest,
configuration and code object are unchanged.

## Findings

1. **The three new modes are exact where they claim to be.** `intguard-fp64` and
   `fused-fp64` produce endpoints bitwise identical to the research FP64 control on
   every one of the 114 paired timing attempts (36 + 42 + 36 pairs). Guard placement
   and launch fusion change cost only.
2. **Fusion halves the update cost on the twelve instances.** Equal-work medians over
   seven 200-proposal runs: 21.2 us per update for the six-launch research control,
   12.1 us for `fused-fp64` and `doublefloat-fp32`, versus 17.0 us for tuned. The
   fused schedule is now the cheapest executor in the project on this corpus.
3. **Integer-pipe guards pay off only at scale.** On the twelve instances they change
   nothing (launch-bound). On the extension instances they cut per-update cost from
   82.8 to 53.8 us (irregular-32768), 150.3 to 92.5 us (irregular-65536) and 230.8 to
   111.8 us (dense_block-65536).
4. **Double-float is the fastest sparse arithmetic at scale but loses certified
   coverage.** It reaches 100.3 us per update on dense_block-65536 versus 111.8 for
   integer-guarded FP64 and 230.8 for the guarded control, and certifies 27/36 at 1e-9
   on the twelve instances. Its four losses are all the strict nonzero-to-zero product
   guard (bit 4) on the scheduling family, where FP32 products of decaying iterates
   underflow below the binary32 normal range. FP64 retains those products. A
   block-exponent or per-vector scale would be needed before this mode is a
   candidate for the scheduling family.
5. **Tolerance tiers move coverage exactly where the rounding analysis predicted.**
   FP32 storage certifies 12/36 at 1e-9, 24/36 at 1e-6 and 30/36 at 1e-4, matching
   tuned FP64 at 1e-4. FP64 itself gains ta001 at 1e-4 (30/36). Tiers change the
   proposal count modestly on this corpus (irregular-2048: 1400 -> 1000) and total
   solve time little, because fixed costs dominate.
6. **Nothing here changes end-to-end latency materially at study size.** Paired
   certified-latency ratios on the twelve instances stay within 0.92-1.11 of tuned
   for every configuration and tier. Context creation (250-330 ms) and the fixed
   host phases still dominate 400-600 ms solves.
7. **At 65536 rows the host, not the device, is the bottleneck.** Preconditioning
   (about 940 ms) and research preparation (about 1020 ms) each exceed the total
   kernel time of a 200-proposal run (19-30 ms). Full solves on mixed-65536 reach the
   30-second limit for the FP64 modes; the double-float mode stops on the product
   guard after 8128 proposals. The CLI's 16 MiB input bound refused every tuned/
   storage attempt on extension instances (SPEC-0005 requirement 18); only the
   research executable, which reads its model directly, measured them.

## Coverage by tier on the twelve development instances

Certified timing attempts out of 36 (three repetitions per instance):

| Configuration | 1e-9 | 1e-6 | 1e-4 |
| --- | ---: | ---: | ---: |
| tuned-fp64 | 27 | 27 | 30 |
| storage-fp32 | 12 | 24 | 30 |
| accumulation-fp32 | 12 | 18 | 21 |
| research-default-fp64 | 27 | 27 | 30 |
| research-intguard-fp64 | 27 | | |
| research-fused-fp64 | 27 | | |
| research-doublefloat-fp32 | 24 | 27 | 27 |

At 1e-4 the remaining FP64 failures are scheduling-50x10 and ta011 (work limit at
50000 proposals). Accumulation-FP32 additionally rejects both scaling instances
and ta001 on product loss at every tier. Double-float additionally rejects ta001
at every tier and scheduling-20x5 at 1e-9 only.

## Equal-work execution cost

Median microseconds per proposed update over 200-proposal runs (seven repetitions
on the twelve-instance rows, three on the extension rows); kernel submission,
execution, synchronization and chunk readback included:

| Instance | tuned | research FP64 | intguard | fused FP64 | double-float |
| --- | ---: | ---: | ---: | ---: | ---: |
| small-4 | 14.41 | 17.44 | 15.28 | 8.99 | 9.01 |
| irregular-2048 | 16.99 | 21.21 | 21.62 | 12.12 | 12.12 |
| dense_block-1024 | 15.25 | 20.04 | 20.00 | 9.55 | 9.61 |
| irregular-32768 | refused | 82.80 | 53.77 | 60.01 | 52.96 |
| irregular-65536 | refused | 150.32 | 92.54 | 108.54 | 95.42 |
| dense_block-65536 | refused | 230.75 | 111.78 | 126.36 | 100.30 |
| mixed-65536 | refused | 150.64 | 93.81 | 109.08 | 95.37 |

Fused FP64 is slower than integer-guarded FP64 on the extension rows because its
per-block update warp serializes eight rows' FP64 vector arithmetic behind each
block's sparse products; the separate vector kernels spread that work over all
lanes. The charged microbenchmark in artifacts/gpup5c-acceptance/microbench-fp64-pipe-2
shows the same shape per launch: on irregular-65536 the guarded FP64 SpMV takes
20.5 us, the fused dual kernel 41.0 us and the fused double-float dual 34.4 us,
against 49.2 us for the six-launch control's sparse kernel alone.

## Traces on irregular-2048

One Nsight Systems trace per configuration at 1e-9, 200 proposals, decoded offline
with the retained importer; every trace matches its endpoint's launch count:

| Configuration | Launches | Kernel busy, ms | Span, ms | Mean sparse kernel, us |
| --- | ---: | ---: | ---: | ---: |
| tuned-fp64 | 1200 | 1.836 | 3.962 | 2.28 |
| research-default-fp64 | 1200 | 2.804 | 5.069 | 3.49 |
| research-intguard-fp64 | 1200 | 2.356 | 4.618 | 2.37 |
| research-fused-fp64 | 400 | 1.509 | 2.913 | 3.77 (fused) |
| research-doublefloat-fp32 | 400 | 1.447 | 2.286 | 3.62 (fused) |

The integer guards bring the research sparse kernel from 3.49 us to 2.37 us, within
0.1 us of tuned; fusion removes 800 launches and 2.1 ms of span.

## Certified solve latency

Paired ratios (median over instances with both sides certified, 10000 bootstrap
resamples, seed 17002): tuned/intguard 0.92 at 1e-9, tuned/fused 1.02, tuned/double-float
1.09-1.11 across tiers, tuned/storage-fp32 0.93-0.99, tuned/research-control 0.99-1.04.
On irregular-32768 the fused and double-float modes are within 0.5-1.7% of the
research control at both tiers (about 4.6-4.9 s per certified solve, 1200-1600
proposals); no tuned baseline exists there because of the CLI input bound. These
are single-process solves dominated by context creation and host phases; the
kernel savings above are real but small against them.

## Completeness and budget

The frozen protocol planned 874 attempts. The study cap admitted 850 before the
1500-second cap stopped admission; 24 planned attempts (the last six mixed-65536
and dense_block-65536 timing cells) are recorded as missing. Of the 850, 806 verified
independently with the archived executables. The 44 unverified attempts are 34
CLI refusals of >16 MiB inputs (exit 2 in 0.1 s each, no endpoint) and 10 research
30-second timeouts on mixed-65536 for the FP64 modes. No attempt failed
verification, and no attempt exceeded its reservation.

| Quantity | Value |
| --- | --- |
| Study GPU seconds | 1493.313474227 of 1500 |
| Acceptance GPU seconds | 66.091602441 of 300 |
| Cumulative campaign seconds | 3794.758955639 of 4502.574545061 |
| Ledger events / SHA-256 | 6722 / ff6f1b5471e80791e964d1e6679017ea33593a7899718d0431f666cfaa5fa23b |
| Preserved 4996-event prefix | 737e1301cb31cf5d0ad0585aa81a4dc0b814615d39e4974827e504e880b11e5f |
| Measured source tree | 5e1e0ff1dd6604c54667356fa75d665c451d1e37b7f794039783acc982833e68 |
| Research executable | e1353e34408b67e69b82f17c0f518e18a20b417a27695b9c770de2811d6ab001 |
| Research code object | 6a743e1e745159f304168124800eec86891c641dfe9f18a91c0aa11d0555b7a2 |

Acceptance charges: two regular device runs (33 cases each, all twelve modes
bitwise against the CPU oracle over 40 steps), memcheck/racecheck/initcheck/
synccheck twice (before and after the fused-kernel restructure; zero errors and
zero hazards each time), and three microbenchmark runs. The first microbenchmark
run exposed that the initial fused kernels serialized their update tail on lane 0
(233 us per launch at 131072 rows); the committed kernels move the eight updates
to one warp after a block barrier (73.8 us). Both results are retained.

## Corpus extension

benchmarks/manifests/lp-development-extension-v1.json (schema lp-manifest-v2) adds
irregular-32768, irregular-65536, dense_block-65536 and mixed-65536 with constructed
exact witnesses. The `mixed` family has equality rows, one-sided rows, ten percent
free variables and coefficients `k + j*2^-30` that are exact in binary64 and
inexact in binary32. The extension is materialized by `python3 tools/lp_generate.py
--extension` and regenerated by tools/check.sh; v1 manifests and generator output
are byte-identical to commit b6732ec. The instances are 32-104 MB of JSON, which
is why the CLI refuses them and why host preparation dominates their solves.

## What this evidence supports and does not support

- Adopt integer-pipe guards and the fused schedule as the research executor's
  default arithmetic-neutral structure; they are bitwise identical to the control.
- Do not adopt double-float without a scale policy: it is the fastest sparse kernel
  at scale and matches FP64 coverage at 1e-6/1e-4 except on ta001, but its product
  underflow on the scheduling family is a real loss, not a guard artifact.
- Tolerance tiers are a legitimate lever for FP32 storage; they are not a lever for
  latency on this corpus, because iteration counts fall modestly and fixed costs
  dominate. Any tier used outside a study needs its own decision record.
- The next latency work on large instances is host-side: preconditioning and
  operator preparation at about one second each, and the 16 MiB CLI bound, which
  is a SPEC-0005 contract and needs its own decision before it changes.
- No supported preset, adaptive recovery, quantization or runtime tolerance change
  follows. GPUP-6 remains next.

## Reproduction

`python3 tools/benchmark_lp_research.py --protocol benchmarks/configs/lp-research-v2.json`
refuses to rerun admitted attempts. `python3 tools/analyze_lp_research.py --protocol
benchmarks/configs/lp-research-v2.json --decode-traces` revalidates every endpoint,
request, identity, ledger prefix and budget and regenerates artifacts/gpup5c-v1/analysis.json.
The same tool without `--protocol` reproduces the GPUP-5B analysis unchanged.
