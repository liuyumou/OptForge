# GPUP-EXEC bounded exact sparse-product executor

Status: bounded experimental contract implemented; no supported preset
Owner: numerical backend and experiment tooling
Introduced: GPUP-EXEC, 2026-10-13
Last reviewed commit: bootstrap
Implementation: feature-gated Rust executor and separate sm_120 CUDA image
Tests: Fraction oracle, full native, device differentials, replay and four sanitizers

## Result and scope

All **108 frozen attempts are retained**; **94 endpoints independently verify**
and **58/96 primary timings certify**. The exact arithmetic and device gates pass,
and all 27 cached/uncached study pairs agree bitwise. The bounded executor does
**not improve certified fresh-solve latency over tuned FP64**. Scheduling, scaling
and mixed cases hit its explicit exponent-window refusal.

This completes [ADR-0035](../decisions/ADR-0035-bounded-exact-executor.md) and the
bounded subset of [SPEC-0020](../specifications/SPEC-0020-lp-expansion-arithmetic.md).
The complete evidence includes [coverage and paired intervals](data/exec/summary.json),
[all attempts](data/exec/trials.csv), [profiles](data/exec/profiles.json),
[compressed analysis](data/exec/analysis.json.gz), [instruction inventory](data/exec/instructions.json),
[resources](data/exec/resources.json), [discovery repair](data/exec/discovery-repair.json)
and the [artifact catalog](data/exec/provenance.json).

The accepted subset is ADR-0035 / SPEC-0020: exact products and summation of
represented binary64 operands, followed by one nearest-even binary64 rounding.
It is bounded to 65536 terms and a 128-bit span of nonzero product base exponents.
FP64 vector updates, host control and final original-model certification remain.
Exact arithmetic on a rounded scaled matrix does not restore earlier scaling
information; preparation records conservative original-unit scaling-error bounds.

## Arithmetic and resource proof

A normalized significand has 53 bits. Its exact product is below 2^106; alignment
adds at most 128 bits and at most 2^16 terms add 16 bits. Every intermediate
signed partial sum therefore has magnitude below 2^250, inside the 255 magnitude
bits of the eight-u32 two's-complement accumulator. Zero products are skipped;
nonfinite inputs still refuse. No nonzero term is dropped to fit the window.
One final rounding handles carries, gradual underflow, signed underflowed zero,
exact cancellation to positive zero, inexact/subnormal/underflow flags and a
symbolic half-ulp error bound. Output overflow refuses.

Both orientations share one array of coefficient bits with CSR/CSC indices and
a validated transpose permutation. Prepared vectors bind operator identity,
orientation and generation; Rust ownership prevents input/output aliases.
An executor refreshes vectors on controller generation changes and anchors on
restarts. A failed chunk preserves host state and poisons the device executor;
its attempted work is still charged. Shape/resident checks precede operator
packing, and buffer admission precedes device-buffer allocation; no fallback is implicit.

At 65536 rows, 65536 columns and 2^23 nonzeros, conservative resident/peak
receipts are 188747776 / 1866473472 bytes under the 1 / 2 GiB caps. This includes
canonical metadata, live vectors/caches, scratch, host matrix views, packing and
hash preparation; exact per-mode device allocation is recorded separately.

The separate image is provisioned explicitly. Decode uses 14 registers/thread;
cached and uncached sparse paths use 39. All three have zero stack/local spills
and no native FP64 arithmetic/conversions in the audited reachable sparse paths.
The image also contains the existing native-FP64 update kernels. This is not a
claim of a completely FP64-free solver, and no hardware busy counters were collected.

## Frozen study and provenance

Eight development models, four configurations and three timing repetitions give
96 primary attempts. Twelve separate profiles request 200 proposals. Seed 17,
one thread, original 1e-9 tolerances, order seed 17001 and analysis seed 17002
remain frozen. Deadlines are the existing 10/30 seconds. Every GPU job reserves
its deadline plus six seconds under the shared host lease on the selected RTX 5090.

| Model | Exact cached | Exact uncached | Tuned FP64 | Precision FP64 |
| --- | ---: | ---: | ---: | ---: |
| small-4 | 3/3 | 3/3 | 2/3 | 2/3 |
| scheduling-20x5 | 0/3 | 0/3 | 2/3 | 2/3 |
| irregular-2048 | 3/3 | 3/3 | 2/3 | 2/3 |
| dense_block-1024 | 3/3 | 3/3 | 2/3 | 2/3 |
| scaling-256 | 0/3 | 0/3 | 2/3 | 2/3 |
| irregular-32768 | 3/3 | 3/3 | 2/3 | 2/3 |
| dense_block-65536 | 3/3 | 3/3 | 2/3 | 2/3 |
| mixed-65536 | 0/3 | 0/3 | 0/3 | 0/3 |

Each denominator includes every frozen timing attempt. Exact modes each certify
15/24; each FP64 control certifies 14/24. Fourteen controls failed discovery,
six mixed controls timed out with independently verified interrupted endpoints,
and eighteen exact timings refused the exponent window. All twelve 200-proposal
profiles complete and independently verify; their iteration-limit endpoints are
diagnostics, not failed primary timings.

For certified pairs only, ratios are control/cached-exact; values above one favor
cached exact. Medians below use all certified samples, so they need not have the
same ratio as the matched repetitions. Two control repetitions and three exact
repetitions remain per successful cell. Intervals are unadjusted 95% paired
bootstrap intervals (10000 resamples); these small development samples do not
establish general reliability or a preset.

| Model | Cached median s | Tuned median s | Precision median s | Tuned/exact [95%] | Precision/exact [95%] |
| --- | ---: | ---: | ---: | --- | --- |
| small-4 | 0.331300 | 0.355205 | 0.424856 | 0.9320 [0.8196, 1.0444] | 1.1468 [0.7934, 1.5002] |
| irregular-2048 | 0.547003 | 0.459823 | 0.558628 | 0.8357 [0.8222, 0.8493] | 1.0155 [0.9632, 1.0679] |
| dense_block-1024 | 0.512493 | 0.440741 | 0.484164 | 0.8692 [0.8329, 0.9055] | 0.9547 [0.9284, 0.9811] |
| irregular-32768 | 4.196704 | 2.583113 | 3.165462 | 0.6166 [0.6127, 0.6206] | 0.7556 [0.7438, 0.7674] |
| dense_block-65536 | 11.588722 | 6.417989 | 8.339692 | 0.5537 [0.5533, 0.5540] | 0.7194 [0.7182, 0.7207] |

The dense-65536 uncached/cached ratio is 1.00172 [1.00130, 1.00405] on three
pairs, a roughly 0.17% scoped difference. The other cache intervals span one.
This does not overcome the 1.62x / 1.81x cached-exact latency relative to tuned
FP64 on irregular-32768 / dense-65536. All 27 cache pairs (24 timing, three
profile) have identical endpoint bits, assessments, work, flags and refusal reasons.

## Fixed-work cost attribution

Each profile proposes exactly 200 updates; values below are milliseconds except
the kernel/synchronization host envelope per proposal, which is microseconds.
There is one profile per cell, without hardware busy counters or a statistical
interval. These are fresh-process diagnostic costs, not primary timing samples.

| Model | Mode | Process ms | Preparation ms | Allocation/upload scope ms | Kernel/sync us per proposal | Device buffers MiB |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| irregular-2048 | tuned-fp64 | 438.156 | 0.000 | 0.872 | 16.557 | 1.073 |
| irregular-2048 | precision-fp64 | 546.697 | 11.873 | 0.875 | 25.936 | 1.120 |
| irregular-2048 | exact-uncached | 484.720 | 15.109 | 6.049 | 26.518 | 1.027 |
| irregular-2048 | exact-cached | 485.132 | 14.521 | 5.915 | 30.810 | 1.090 |
| irregular-32768 | tuned-fp64 | 1897.401 | 0.000 | 6.158 | 34.996 | 17.242 |
| irregular-32768 | precision-fp64 | 2201.025 | 270.640 | 6.426 | 127.389 | 17.992 |
| irregular-32768 | exact-uncached | 3319.356 | 273.679 | 93.753 | 92.157 | 16.494 |
| irregular-32768 | exact-cached | 3298.533 | 273.960 | 94.162 | 99.792 | 17.493 |
| mixed-65536 | tuned-fp64 | 3551.525 | 0.000 | 18.286 | 53.484 | 34.449 |
| mixed-65536 | precision-fp64 | 4101.053 | 596.835 | 16.258 | 235.119 | 35.949 |
| mixed-65536 | exact-uncached | 6463.006 | 586.958 | 213.774 | 165.252 | 32.958 |
| mixed-65536 | exact-cached | 6469.165 | 586.128 | 213.358 | 169.899 | 34.958 |

The table records the extra operator-preparation phase; a zero for tuned FP64
means that distinct phase is absent, not that model preparation is free. All
phase envelopes and process RSS are retained in the data. Device-buffer totals
exclude driver/context allocations; sampled process RSS is separately recorded.

Cached exact uses eight launches per proposal, versus six for uncached exact.
At 32768 rows, cached and uncached kernel/sync envelopes are 99.792 and 92.157
microseconds/proposal, below generic precision FP64 at 127.389 and above tuned
FP64 at 34.996. The corresponding complete profiles cost 3.299, 3.319, 2.201
and 1.897 seconds. Mixed-65536 shows the same separation: exact sparse execution
is cheaper than generic precision FP64, but complete profiles are about 6.46
seconds versus 4.10 and 3.55 seconds for precision and tuned FP64.

The exact executor also pays larger invariant allocation/upload scopes. Its
fresh witness construction reparses/reconstructs the host input, rebuilds operator
metadata and independently rechecks the original-model assessment. These costs
remain inside the primary process envelope. Existing timers do not isolate every
part of that final work, so the unaccounted process remainder is not assigned to
a specific operation or called GPU time. The result supports retaining the tuned
control and treating both host evidence cost and the range window as concrete
limitations of this executor; it does not justify more arithmetic or a preset.

## Retained discovery packaging failure

The first fourteen FP64-control attempts exited during discovery because the
study directory omitted schedule_eval.cubin. Their stderr, empty output, worker
exit status, requests and charges remain untouched. The unchanged discovery
image was then restored from the source-bound acceptance archive, with a repair
receipt naming its hash and the already-failed attempts. No failed identity was
retried. This lowers the available paired repetitions and prevents treating
those setup failures as numerical-method failures or certified timing samples.
The final packaging helper requires the dependency before any future freeze;
its regression runs without a GPU. Measurement executables and numerical images
remain exactly as archived.

## Acceptance, resources and handoff

The independent seed-17004 Fraction fixture contains 2347 cases, including all
normal exponents, signed/subnormal/tie/cancellation/overflow cases, a 65536-term
sum and an over-limit refusal. The CPU candidate matches all cases; the device
checks the 2346 shape-admitted cases in both cache modes. Three new device tests
cover the fixture, CPU/GPU trajectories across restart/restore boundaries, and
range refusal without host-state corruption. All four scoped sanitizers pass
with zero errors. These receipts do not close the historical tuned_cases
racecheck gap.

The full pinned-native gate passes, with 253 Python contracts, committed-record
replay, documentation and smoke. The regular device suites pass 66 tests (14 driver, 6 scheduling, 46 LP). Three
8-update cache pairs and six same-device replays pass, and the independent report
re-verifies all six endpoints and six replays using the frozen executable. Ten
source-only GPUP-EXEC tests cover budgets, crash accounting, complete request
identity, discovery dependencies and retained interruption bytes. The original
report and hardened report agree on all numerical results and primary statistics.

The first two-test oracle run is preserved with its 0.774594710-second charge;
the final three-test gate and all other device gates bind measured source
03df0db2362dee7284deb7d10d08dda60b36eb14607164f71a3ab1e818c1350e.
The CUDA image SHA-256 is
ec3c6c03387c742ccac83742d905616f6ca4160026e00c4c8dfc36c2eb21a0c6.
CPU-only post-study repairs cover the discovery-image freeze precondition,
nonzero child exit status, artifact-free malformed-budget rejection, and complete
acceptance request identities. Measured executables, numerical sources, primary
receipts and settings remain exactly as archived.

PR self-review reproduced missing acceptance bindings for the image directory,
attempt key, executable and selected device, plus a check that admitted empty
regular suites. The verifier now binds those fields to the archived files and
requires the actual 14/6/46 regular-test counts; the earlier prose total of 58 is
corrected to 66. Recovery independently verifies complete surviving endpoints
without promoting interrupted attempts into primary timings or reducing their
full crash reservation. Six new CPU regression tests retain these cases and
prevent source-review exceptions from admitting numerical changes.

The [review correction receipt](data/exec/review-corrections.json) binds every
changed measurement/report tool to its measured and reviewed SHA-256; numerical
Rust/CUDA, benchmark inputs, schemas and dependencies remain byte-identical.
The independent report is rerun after these corrections. Review reproductions,
validation logs, artifact inventories and recovery bundles are retained under
artifacts/gpup-exec-pr-review-20261013; no additional GPU work is used.
The final pinned-native review gate passes 259 Python contracts and all Rust,
native, dependency, record, documentation and smoke checks. All 16 executor
contracts pass without campaign artifacts. The hardened report is byte-for-byte
identical to the completed study report; all 1153 catalog references verify.

Task consumption is **520.157397485 GPU seconds**: timing 431.684266725/2300,
profiles 36.003675982/450 and acceptance 52.469454778/850. Cumulative consumption
is **17635.432015338 / 21602.574545061 seconds**. The explicit ADR-0035 phase
ceilings remain independently enforced, as does the overall 28800-second cap.
The 16366-event ledger SHA-256 is
4d083cdb06b4baa38452bb331541fa8874614aeb037f34e40001ce9692ede26b;
the preserved 16134-event prefix is
60649d29992d21508e60aa60f3e334e9ac18fe3254525ec38cc0eef298e84823.
No failed identity was retried or removed. CPU work uses four build jobs under
the 21600-second task cap; CPU time is not metered by the GPU ledger. The sampled
RSS and archived artifact bytes are reported separately against the 8 / 32 GiB
limits. Unused headroom is not a reservation for the next task.

Raw evidence is retained under artifacts/gpup-exec-v1. To reproduce CPU verification
and the tracked summaries with those hash-bound artifacts present:

```bash
python3 tools/lp_exec_oracle.py --check
python3 tools/report_lp_exec.py --export docs/benchmarks/data/exec
```

The [frozen protocol](../../benchmarks/configs/lp-exec-v1.json) owns settings,
seeds, roster and budgets. Reproducing summaries does not launch GPU work or retry
measurements. Historical endpoints, defaults, code images and original-model
certification authority remain unchanged.

GPUP-STATE is the next dependency-ready contract task. Persistent expansion or
compensated state, device division/square root, refinement, adaptive sessions and
supported presets require their own accepted scope and resource gates. Historical
large-session, tuned_cases racecheck and mixed-model limitations remain open.
