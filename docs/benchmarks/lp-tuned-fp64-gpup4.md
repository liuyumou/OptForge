# Tuned FP64 GPU Execution: GPUP-4

Purpose: isolate FP64 allocation, transfer, sparse reduction and fusion costs.
Owner: numerical backend and experiment tooling.
Status: complete verified development study and acceptance, 2026-09-15.
Contracts: [ADR-0017](../decisions/ADR-0017-tuned-fp64.md),
[ADR-0018](../decisions/ADR-0018-fp64-study-correction.md) and
[SPEC-0012](../specifications/SPEC-0012-mixed-precision-lp.md).

## Findings and provisional control

All seven GPU configurations and current host LP certified **27/36 timing trials**
on the same nine instances. GPU configurations retained identical endpoint bits,
iteration counts and restart counts across all 36 paired timing runs. This includes
unsuccessful endpoints; it does not claim that distinct reductions always agree.
The cancellation-heavy independent fixture explicitly distinguishes warp32 from
the legacy tree, and the device checks each against its declared arithmetic.

Resident buffers, necessary uploads and fusion reduce measured device work.
On irregular-2048, allocations fall from 74 to 20 with residency, uploads from
39 to 27 with necessary transfers, and launches from 8400 to 2800 with fusion.
Adding warp32 plus fusion reduces the separately profiled launch/synchronization
phase from 34.645 ms to 14.541 ms. Full-solve improvement is much smaller because
context creation and host work remain substantial.

**Retain cuda-lp-matched as the general numerical and performance reference.**
Resident/necessary/warp32/primal-dual execution is a provisional development
comparison on scheduling-20x5, dense_block-1024 and scaling-256 only: coverage is
preserved and their matched/fused-warp paired 95% intervals exceed one. The paired
ratio on scheduling-20x5 is 1.221, interval [1.172, 1.245], with medians 609.574 and
499.234 ms. Other instances retain the matched reference where evidence is weak;
this is no automatic dispatch rule, supported preset or final recipe. Legacy fusion
also has useful results, and is retained as an explicit ablation. Final selection
belongs to GPUP-9/10, with more repetitions and held-out evidence.

## Protocol and timing boundaries

Eight configurations use three fresh-process repetitions on all 12 frozen
development instances, followed by one separate profile per configuration on
small-4, irregular-256, irregular-2048 and dense_block-1024: 320 attempts per round,
280 GPU and 40 CPU. No held-out or validation instance is solved. The original
722e0b0 matched executable/source/code object were archived before implementation;
current host and tuned execution have their own archived executable and source.

Seeds remain 17/17001/17002, 1e-9 absolute/relative targets, one CPU thread/affinity
[0], 50000 iterations, checks every 200, published preconditioning/restart/weight
settings, 10-second solve deadlines, two-second cleanup, and 8 GiB host RSS/device
buffer ceilings. GPU attempts reserve the full 16 seconds including admission and
supervisor overhead; host attempts reserve 13. All GPU jobs hold the shared
host-wide lease after quiet-device admission on RTX 5090
GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48, driver 580.105.08, with an Intel Xeon
Platinum 8457C host. Queue and activity waits are reported separately.

Primary elapsed time covers fresh child launch, preparation, context, iteration,
host certification, independent endpoint construction, output and teardown. The
standalone Rust re-verification occurs afterward and is timed separately. Profile
phases are host-observed costs including launches and synchronization; they are not
isolated hardware kernel event times. The primary runs add no profiling-only
synchronization. RSS is a sampled process-tree estimate; explicit LP buffer counters
exclude driver/context memory. Occupancy and bandwidth counters are unavailable.

## Coverage and observed medians

Seconds. C = certified, W = work limit without certification, T = censored timeout.
Every entry represents three repetitions with the same outcome class. W/T costs
are observed execution costs, not times to a certified solution. Each GPU
configuration has nine W attempts; the host has three W and six T. All 32 profiles
certify. There are no correction-round launch failures, missing/invalid endpoints,
fallbacks or unsettled reservations.

Compat selects per-check allocation, repeated uploads, legacy tree and separate
kernels. Resident changes allocation only; Uploads adds necessary state transfers;
Warp adds warp32. Fused tree and Fused warp use resident/necessary transfers with
the named reduction and two fused kernels. Every tuned configuration caches kernel
handles and launch configurations. Matched retains its original implementation.

| Instance | Matched | Compat | Resident | Uploads | Warp | Fused tree | Fused warp | Host |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| scheduling-20x5 | 0.610 C | 0.598 C | 0.605 C | 0.598 C | 0.612 C | 0.493 C | 0.499 C | 2.661 C |
| scheduling-50x10 | 3.244 W | 3.290 W | 3.224 W | 3.223 W | 2.813 W | 2.997 W | 2.550 W | 10.146 T |
| irregular-256 | 0.384 C | 0.355 C | 0.367 C | 0.340 C | 0.356 C | 0.353 C | 0.360 C | 0.185 C |
| irregular-2048 | 0.486 C | 0.493 C | 0.462 C | 0.504 C | 0.487 C | 0.473 C | 0.473 C | 1.662 C |
| dense_block-256 | 0.339 C | 0.366 C | 0.347 C | 0.371 C | 0.379 C | 0.412 C | 0.364 C | 0.196 C |
| dense_block-1024 | 0.414 C | 0.442 C | 0.418 C | 0.435 C | 0.412 C | 0.442 C | 0.394 C | 0.870 C |
| scaling-64 | 0.380 C | 0.364 C | 0.397 C | 0.389 C | 0.377 C | 0.350 C | 0.380 C | 0.123 C |
| scaling-256 | 0.432 C | 0.407 C | 0.441 C | 0.466 C | 0.402 C | 0.373 C | 0.391 C | 0.656 C |
| small-4 | 0.299 C | 0.350 C | 0.340 C | 0.334 C | 0.304 C | 0.333 C | 0.328 C | 0.007 C |
| small-16 | 0.350 C | 0.352 C | 0.353 C | 0.344 C | 0.305 C | 0.310 C | 0.329 C | 0.011 C |
| ta001-relaxation | 1.362 W | 1.324 W | 1.357 W | 1.306 W | 1.207 W | 0.921 W | 0.924 W | 9.708 W |
| ta011-relaxation | 1.435 W | 1.483 W | 1.440 W | 1.422 W | 1.270 W | 1.035 W | 1.054 W | 10.052 T |

## Paired end-to-end evidence

Ratios are matched/fused-warp medians from mutually certified repetitions, with
10000 paired bootstrap resamples and seed 17002. Values above one favor tuned
execution. Each available interval uses three pairs. The three uncertified
instances have no certified ratio. These are unadjusted development intervals;
three repetitions and many comparisons are insufficient for generalization.

| Instance | Ratio | 95% interval |
| --- | ---: | --- |
| scheduling-20x5 | 1.2210 | [1.1717, 1.2450] |
| scheduling-50x10 | unavailable | unavailable |
| irregular-256 | 1.0661 | [0.9563, 1.2136] |
| irregular-2048 | 1.0256 | [0.9992, 1.0681] |
| dense_block-256 | 0.9310 | [0.8118, 1.1848] |
| dense_block-1024 | 1.0497 | [1.0181, 1.2072] |
| scaling-64 | 1.0009 | [0.9642, 1.1370] |
| scaling-256 | 1.1059 | [1.0581, 1.2248] |
| small-4 | 0.9108 | [0.8658, 1.0378] |
| small-16 | 1.0627 | [0.9009, 1.1556] |
| ta001-relaxation | unavailable | unavailable |
| ta011-relaxation | unavailable | unavailable |

The full raw report includes all thirteen declared comparisons, including each
successive ablation. Negative and ambiguous effects are retained:

- Integration (matched versus Compat) has no certified instance whose interval
  excludes one. Residency has supported gains on irregular-2048 and dense_block-1024.
- Necessary uploads reduce actual traffic but are slower than repeated uploads on
  irregular-2048 (ratio 0.9175) and scaling-256 (0.9470), with intervals below one.
  The saved transfer phase is small; these timings do not establish a universal
  benefit from transfer avoidance.
- Warp32 improves five transfer-control comparisons but regresses dense_block-256
  (ratio 0.9770, interval below one). Adding fusion to warp32 has supported gains on
  scheduling-20x5 and dense_block-1024; fusion and reduction interact.
- Fused-warp medians are slower than matched on dense_block-256 and small-4, though
  those intervals overlap one. Host LP remains much faster on tiny instances.
- Faster unsuccessful scheduling runs remain failures. No configuration certifies
  scheduling-50x10, ta001-relaxation or ta011-relaxation at these limits.

## Iterations, restarts and arithmetic

All 36 reference/Compat, Compat/Resident, Resident/Uploads, Uploads/Fused-tree,
Warp/Fused-warp and Uploads/Warp timing pairs have identical candidate/witness,
objective/bound/gap bits and iteration/restart observations. These are endpoint
comparisons, separate from whole-trajectory acceptance tests. No convergence gain
or regression was observed on this development set. The three scheduling failures
retain their 50000-step GPU limits; timeouts stay censored on the host.

The independent Rust mirror covers complete primal/dual/controller histories,
nonzero integral/derivative settings, restarts and checkpoint restoration. Exact
Fraction fixtures cover finite dot-product error, cancellation and boundaries from
empty lines through 2049 entries, including 31/32/33 and 1023/1024/1025. Device tests
also exercise signed zero, subnormals, overflow, objective senses, 64-step partial
cancellation, early interruption, allocation refusal and repeatability. GPUP-1's
independent exact-rational certification/gap regressions remain unchanged.

## Allocation, transfer and phase observations

The separate irregular-2048 profiles all perform 1400 iterations and six restarts.
Counts include invariant allocations/uploads. Allocated bytes are cumulative;
peak bytes are simultaneous explicit buffers, including empty padding and scratch.
All tuned variants read back 229376 bytes in fourteen calls, preserving host checks.

| Configuration | Allocations | Allocated bytes | Peak bytes | Upload calls / bytes | Synchronizations | Launches |
| --- | ---: | ---: | ---: | --- | ---: | ---: |
| Compat | 74 | 2009984 | 1125248 | 39 / 1436544 | 81 | 8400 |
| Resident | 20 | 1125248 | 1125248 | 39 / 1436544 | 81 | 8400 |
| Uploads | 20 | 1125248 | 1125248 | 27 / 1239936 | 69 | 8400 |
| Warp | 20 | 1125248 | 1125248 | 27 / 1239936 | 69 | 8400 |
| Fused tree | 16 | 1059712 | 1059712 | 27 / 1239936 | 69 | 2800 |
| Fused warp | 16 | 1059712 | 1059712 | 27 / 1239936 | 69 | 2800 |

Milliseconds from that separate profile; whole-process timings are not paired estimates.

| Configuration | Context | Working allocation | Working upload | Launches + sync | Controller | Host checks | Independent check | Whole process |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Matched | 263.791 | 0.110 | 0.243 | 34.615 | 14.356 | 29.328 | 8.617 | 498.709 |
| Compat | 219.426 | 0.116 | 0.243 | 34.645 | 14.266 | 29.674 | 8.161 | 464.336 |
| Resident | 269.735 | 0.013 | 0.247 | 34.610 | 14.324 | 29.471 | 8.699 | 516.488 |
| Uploads | 249.333 | 0.013 | 0.152 | 34.629 | 14.274 | 29.712 | 8.685 | 493.490 |
| Warp | 268.523 | 0.012 | 0.151 | 23.239 | 14.283 | 29.390 | 8.843 | 497.464 |
| Fused tree | 206.791 | 0.008 | 0.162 | 28.888 | 14.218 | 29.399 | 8.448 | 437.068 |
| Fused warp | 243.940 | 0.008 | 0.166 | 14.541 | 14.296 | 29.538 | 8.989 | 465.320 |

Preconditioning adds about 26 ms, input preparation about 8 ms, and other output,
startup and teardown costs remain outside the shown phases. Host LP's separate
irregular-2048 profile spends 1552.361 ms in iteration and 1661.715 ms overall.
The full summary preserves all phases on all four profiling instances. Context
variation and millisecond-scale measurement noise dominate submillisecond
allocation/upload savings, so phase reductions alone do not select a control.

## Preserved failed round and resource accounting

The original gpup4-tuned-fp64-v1 round completed all 320 attempts. Its first 24
reference timing attempts exited before solving because copying the archived
executable lost execute permission. Restoring mode 0755 preserved its exact bytes
and enabled remaining attempts. All failures, outputs and charges remain; its
independently verified report stays interim. The correction repeats the entire
schedule, not a selected numerical subset, under ADR-0018. The two rounds are
analyzed separately and never pooled. There is no third round.

| Item | GPU seconds |
| --- | ---: |
| Prior GPUP-2/3 campaign | 445.988045904 |
| Original GPUP-4 round | 219.094449232 |
| Correction round | 237.492049925 |
| Total GPUP-4 supplement used | 456.586499157 / 900 |
| Cumulative campaign | 902.574545061 / 1345.988045904 |

The 1800-second baseline phase and 28800-second campaign ceilings remain enforced.
Both rounds retain 640 attempts (560 GPU / 80 CPU), including all failures, profiles,
timeouts and actual leased charges. The pre-GPUP-4 622-event prefix is checked by
SHA-256; the original authority and output binding remain unchanged. New attempts
require full reservations, and crash recovery charges the complete reservation.

The original/correction invocations took 566.431045699 / 583.406262495 wall seconds.
Correction host jobs used 111.610830772 seconds, additional independent verification 19.466426820, activity wait 128.275209579, and lease queue wait 0.005310117. These are distinct measurements, not additional GPU allowance.

## Acceptance and limitations

The measurement source passed full pinned-native bash tools/check.sh: 410 Rust
tests, 110 Python tests, all dependency/license, replay, formatting, Clippy and
73-page documentation gates. Native-freeze took 19.140472299 seconds and its exact
source receipt is archived. All 41 regular device cases passed on the frozen RTX
5090 and compatible sm_120 RTX PRO 6000. Eight scoped observation/matched/tuned cases
passed each of memcheck, racecheck, initcheck and synccheck on PRO 6000 with zero
errors and zero racecheck warnings. CLI evidence, pinned fallback, recorded-settings
replay and altered-code rejection passed on both devices. Device work observations
survive injected fault/fallback metadata; unavailable completed work is not invented.

The RTX 5090 had only 797 MiB free and could not allocate memcheck instrumentation.
Both failed runs are retained, including the force-synchronization-limit retry.
Sanitizer evidence is from GPU-6721b13a-30f9-83ec-dace-ba2d9738556f, not a claimed
RTX 5090 sanitizer pass. Regular tests and every comparative trial use the frozen
5090. All device workloads are sequential under the same host-wide lease.

After measurement, strict-schema review reproduced acceptance of object-wrapped
execution enum names. A regression failed before the fix and passes after using
the established string-only parsing pattern. The measured string-valued settings,
iteration code and code object are unchanged. The final parser-only repair is not
remeasured; timings refer to the archived executable and source identified below.
No new precision, recovery policy, supported preset, dispatch, seed or numerical
threshold is introduced. Final full-native acceptance passed: 411 Rust tests,
110 Python tests and 73 documentation pages in 35.965244998 seconds. The final
41-case RTX 5090 suite and CLI fallback/replay/altered-code checks passed in
16.587609922 seconds.

Acceptance is separate from study spending: at most 60 CPU wall minutes with four
build jobs, and 30 GPU minutes, sequential with CPU gates. Receipts and complete
logs are in artifacts/gpup4-acceptance, including failed native/fixture checks and
failed sanitizer attempts. Final GPU acceptance including failures totals
479.537579339 seconds of 1800. Native/focused-regression receipts total
177.027801669 CPU wall seconds; four-worker builds and acceptance stayed within
the 60-minute allocation. The [active task](../../state/active-task.md) records
completion and the GPUP-5 handoff.

## Provenance and reproduction

Both source snapshots are based on revision
722e0b01aecc5875b44ae0a7124f7c1b41eeeeed. The reference is clean; current execution
honestly records dirty=true plus the complete frozen source archive. Current host
and all tuned configurations share the recorded current executable, while host
code-object identity is null. The legacy kernel source and archived cubin remain
unchanged; tuned provisioning uses a separate cubin and never runs during Cargo
builds. Archive modes are preserved, and executable permission is preflighted.

| Artifact | SHA-256 |
| --- | --- |
| Reference source tree | 3772e690e99ad93f914f955d13654414da0d7a79920a9c143495178eea9a8bf7 |
| Reference source archive | e8911cdb14e2ba0242869a0f1e5134b31f20f855aefc7e448d35abae7023dca8 |
| Reference executable | 3f145b255d0aae934eb88068f991ece09cc8a46c22b35c7970119ad736e91993 |
| Reference LP code object | 6a4c87550f7efec3ff2b29e247e604aac42d8cff83fa42f438d3823d15580f5e |
| Correction source tree | 8307df2ecb105552551058d93d885d10e93063695b188889fe520705ccdaef86 |
| Correction source archive | 48fdc51b2588679fb10bc537845ab30b3fe8b7cf4eef428b6635b116489218ab |
| Current measured executable | da6867e1c7e5cd580ac015d241815a49642d2aab3bb7ebcaf6ae658a20c189d8 |
| Tuned code object | a60a3a15dee107ea87e727f23496ad4a516706991a8a05ae7cc23f38083bd235 |
| Correction protocol | d1b709359e28a6f1a5410fca27f1fae19538296896fb2bdef1f090f6cccb6071 |
| Correction raw index | 9b560b44b74f2035525a2d0c86ea5438f03097fdb203e2fb33723b3023a98b77 |
| Final study ledger | 35b58ef0b0d58637288801bac2bdaa32b65b97b42b429debcffc615768c7c543 |
| Original round raw index | 5c71d77e0f8ff8202531bb92b2e927c1f4a9508759025ae83ab5420c1307db2a |
| Original round ledger | 41e9bb277d23c35bec059fda85081d5da2337ccbe88faab0dba6e73660b98697 |

Reference artifacts live under artifacts/gpup4-reference. Original and correction
outputs live under artifacts/gpup4-tuned-fp64-v1 and
artifacts/gpup4-tuned-fp64-correction-v1. Each directory retains all trial/worker/
endpoint/output files, source/executable/code archives, per-configuration identities,
protocol, ledger snapshot, summary, full paired report and artifact index. The
canonical writer remains artifacts/lp-campaign-ledgers/gpup-baseline-v1. Raw large
artifacts are locally archived, not committed as project source.

```sh
# Provision before freezing; preserve the archived legacy objects.
bash tools/setup_cuda.sh --tuned-only
bash tools/check.sh
cargo build --release --workspace
python3 tools/benchmark_lp_tuned.py --dry-run \
  --campaign benchmarks/configs/lp-tuned-correction-v3.json
python3 tools/benchmark_lp_tuned.py \
  --campaign benchmarks/configs/lp-tuned-correction-v3.json \
  --output artifacts/gpup4-tuned-fp64-correction-v1
python3 tools/report_lp_tuned.py \
  --campaign benchmarks/configs/lp-tuned-correction-v3.json \
  --input artifacts/gpup4-tuned-fp64-correction-v1
```

The existing completed campaign has no unattempted IDs to rerun. Resume requires
the exact archived source/executable/protocol and retains the existing ledger;
these commands do not authorize new attempts or reset budgets. Re-verification
reads the retained evidence without spending GPU time. See the
[execution guide](../architecture/lp-tuned-fp64.md) for explicit CLI settings and
compatibility. GPUP-5 must retain the original rational authority regressions,
matched reference and full ledger, and specify its new precision interfaces before
introducing lower-precision behavior.
