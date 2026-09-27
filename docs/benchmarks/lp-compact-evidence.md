# Compact independently verifiable LP evidence

All **24/24 fresh timing attempts** are retained; **15 endpoints independently verify** and **12 qualify as certified timings**. Compact evidence restores assessable output at 65536 rows within the unchanged 32 MiB file cap. Mixed-65536 remains time-limited; no supported preset is selected.

This implements [SPEC-0015](../specifications/SPEC-0015-compact-lp-evidence.md) and [ADR-0027](../decisions/ADR-0027-compact-lp-evidence.md). The [study CLI tutorial](../tutorials/lp-compact-evidence.md) documents compatibility, replay and verified conversion. Ordinary solve output and legacy endpoints remain the defaults. Original-model certification, arithmetic, kernels, tolerances and historical trials are unchanged.

## Data and reproduction

[Full independent analysis](data/evidence/evidence-analysis.json), [all attempts](data/evidence/evidence-trials.csv), [coverage](data/evidence/evidence-coverage.csv), [CPU measurements and conversion identities](data/evidence/evidence-cpu.json), [CPU summary](data/evidence/evidence-cpu-summary.csv), [device equivalence](data/evidence/evidence-device-equivalence.json), [fresh-pair numerical comparison](data/evidence/evidence-fresh-equivalence.json), [resources](data/evidence/evidence-resources.json) and [SHA-256 provenance catalog](data/evidence/evidence-provenance.json) are repository data. The catalog binds every complete/partial output, worker receipt, executable, source archive, code image and acceptance log retained locally.

Raw evidence remains under `artifacts/gpup-evidence-v1`, `artifacts/gpup-evidence-cpu-v1/initial` and `artifacts/gpup-evidence-acceptance`. Generated models remain the frozen development manifests. Converted historical evidence is derived data, never a recovered historical timing or new solve.

Measured source tree: `dc6eae6832a6f8d4eb0f6c3bf375ade7eb6cf70781b1eab7924ad1233b75d024`; release binary: `aa9422eaa630ab7ed54a5a22ba655ff49fcf9d8ed70659aab4c35ff44ef3ab81`. The exact dirty source is archived with its schema snapshot. Host: Linux 5.19.0-32-generic, Intel Xeon Platinum 8457C, RTX 5090 `GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48`, driver 580.105.08, Rust 1.93.1; supervised solves use CPU affinity [0].

Report existing evidence with `python3 tools/report_lp_evidence.py`, using the archived source/schema snapshot and retained paths. CPU measurements use `python3 tools/lp_evidence_cpu.py --run-id NEW_NAME`; that command refuses an existing run directory. `python3 tools/benchmark_lp_evidence.py --dry-run` displays the frozen 24-attempt grid without device work. The runner preserves admitted identities and does not retry failures. A new live study needs separately declared identities and budget authority.

## Representation and CPU acceptance

The strict minified `lp-compact-v1` envelope retains endpoint versions 1–5 and their original payload hashes, candidate values/IDs, dual witnesses, row IDs, method/settings, assessment, observations and execution identity. It omits only `record.validation`, replacing it with a required nullable SHA-256. Verification reconstructs that report from the exact model and recorded tolerances, checks the digest and runs the unchanged legacy verifier. There is no compression or numerical representation change.

All four full-witness fixtures pass exact legacy→compact→legacy byte round trips, including the original payload hash. Each format has three independent CPU verifications per model. Two missing complete historical witnesses use explicitly synthetic canonical-zero candidates/duals and work-limited outcomes. The retained mixed trace remains time-limited after conversion.

| Model | Fixture | Outcome | Legacy bytes | Compact bytes | Reduction |
|---|---|---|---:|---:|---:|
| irregular-32768 | retained | certified_success | 32,280,626 | 2,244,255 | 93.05% |
| irregular-65536 | synthetic | work_limit | 59,082,946 | 2,863,050 | 95.15% |
| dense_block-65536 | synthetic | work_limit | 59,225,810 | 2,863,054 | 95.17% |
| mixed-65536 | retained | timeout | 58,419,348 | 4,298,555 | 92.64% |

All compact fixtures fit below **33,554,432 bytes**. File-size savings establish representation feasibility; the fresh comparison below measures complete solve latency.

| Model | Legacy write / compact write (ms) | Legacy verification / compact verification (s) |
|---|---:|---:|
| irregular-32768 | 33.223 / 3.121 | 1.728 / 1.211 |
| irregular-65536 | 64.332 / 3.962 | 3.270 / 2.425 |
| dense_block-65536 | 63.870 / 3.807 | 3.729 / 2.999 |
| mixed-65536 | 62.706 / 5.813 | 3.271 / 2.650 |

These are three-repetition medians. Write wall covers already encoded bytes, flush and fsync, excluding serialization. Verification wall includes a fresh verifier process, parsing, reconstruction, validation and conservative certification. It is reported separately from solve wall; compact reconstruction is required even though total verification was faster on these fixtures. Transcode/restore durations and all raw measurements are retained in the CPU data.

## Frozen fresh-process comparison

The separate [gpup-evidence-v1 protocol](../../benchmarks/configs/lp-evidence-v1.json) freezes four extension models × two output formats × three repetitions with tuned FP64. Format is part of each configuration hash and exact supervised request. Settings match the COPT study: seed 17, one CPU thread, 1e-9 tolerances, 50,000-update limit, 30-second extension deadline, two-second cleanup, 8 GiB host/device limits, 128 MiB explicit study input allowance and 32 MiB output cap. Blocked order uses seed 17001; paired analysis uses seed 17002 and 10,000 bootstrap resamples. Independent CPU verification keeps its 120-second limit.

Fresh-process latency includes input, device setup, iteration, certification, endpoint publication and stdout. Compact stdout contains only the assessment. Legacy stdout remains the full solve record. The independent post-process verifier is outside this timing.

| Model | Format | Completed process | Verified / planned | Certified / planned | Certified median (s) |
|---|---|---:|---:|---:|---:|
| irregular-32768 | legacy | 3 / 3 | 3 / 3 | 3 / 3 | 2.853 |
| irregular-32768 | compact-v1 | 3 / 3 | 3 / 3 | 3 / 3 | 2.737 |
| irregular-65536 | legacy | 0 / 3 | 0 / 3 | 0 / 3 | — |
| irregular-65536 | compact-v1 | 3 / 3 | 3 / 3 | 3 / 3 | 5.294 |
| dense_block-65536 | legacy | 0 / 3 | 0 / 3 | 0 / 3 | — |
| dense_block-65536 | compact-v1 | 3 / 3 | 3 / 3 | 3 / 3 | 6.662 |
| mixed-65536 | legacy | 0 / 3 | 0 / 3 | 0 / 3 | — |
| mixed-65536 | compact-v1 | 0 / 3 | 3 / 3 | 0 / 3 | — |

All 12 compact attempts publish complete endpoints (2,244,255–4,510,209 bytes) and assessment-only stdout (209–312 bytes). The three complete legacy endpoints each use 32,280,626 bytes plus 28,629,301 bytes of stdout; the other nine legacy attempts retain partial endpoints exactly at the 33,554,432-byte cap. Six are process failures and three are also timeouts. All three compact mixed-65536 endpoints independently verify an interrupted outcome, but their workers timed out and none qualifies as a successful timing. The old COPT primary cells remain unchanged; this table contains new executions under a separate protocol.

| Model | Qualifying paired repetitions | Median legacy / compact ratio | 95% paired bootstrap interval |
|---|---:|---:|---:|
| irregular-32768 | 3 | 1.0463 | [1.0226, 1.0499] |
| irregular-65536 | 0 | — | — |
| dense_block-65536 | 0 | — | — |
| mixed-65536 | 0 | — | — |

The statistic is the median of per-repetition legacy/compact ratios. Ratios above one favor compact; failed members never supply pairs. Three development repetitions support only this scoped observation, not a general latency guarantee. All qualifying fresh timing pairs have identical binary64 numerical digests after excluding elapsed-time/profiling observations.

## Acceptance and limitations

- Full pinned-native `bash tools/check.sh`: 500 Rust tests, 179 Python integration tests, clippy, rustdoc, dependency policy, committed-record replay, schema/provenance validation, documentation and smoke. Exact-rational regressions and both objective senses remain covered.
- Strict codec tests cover versions 1–5, fixed/adaptive/fallback records, absent candidates/reports, unsuccessful outcomes, signed zero, and mutations of models, candidates, duals, digests, assessments, settings and execution identities. CLI tests cover flag scope, bounds, destination refusal, failed partial writes, replay, conversion and ordinary compatibility.
- Regular device acceptance: 55 tests, no skipped device coverage. Six fixed-work legacy/compact pairs and six compact replays cover tuned FP64, fixed FP32 accumulation and gradual adaptive recovery on small-4 and irregular-2048; all 18 endpoints independently verify and agree in numerical bits and execution counters.
- No kernels changed. Existing sanitizer receipts apply only to their unchanged tested scopes. The historical `tuned_cases` racecheck gap and old 65536-row session gaps remain open. No new sanitizer receipt is claimed.
- The first CPU gate exposed a historical-schema test that treated new schemas as old. The check now enumerates the old revision, preserving byte checks and detecting deleted old schemas. Initial failure and subsequent passing gates are retained. No GPU trial was retried.

## Resources and handoff

Task GPU charge is **305.274714773 seconds**: timing **283.019581049 / 900** in ablations and acceptance **22.255133724 / 300** in repeatability. All 24 timing reservations were 36 seconds (864 seconds total); actual lease charges include failures, admission and cleanup. Every device job used the shared host lease, one at a time. No new cumulative allowance was added.

Cumulative consumption is **15071.710156489 / 18002.574545061 seconds**. The **15392-event** ledger SHA-256 is `6a30c1954ff9bc80c733364d8e8a7c0fc4c4439d70b959d2c10996d71993e518`. The first 15,340 events still hash to `5cf76ffbea09e21fdf21692c4030f8176ae5ef7f481c2e5c6e83fe302371b51b`; the original output binding and all earlier prefixes remain intact.

| Campaign phase | Used GPU seconds | Cap |
|---|---:|---:|
| baseline | 1170.475765674 | 1800 |
| screening | 6113.346416442 | 7200 |
| ablations | 5957.981357124 | 7200 |
| repeatability | 1829.906617249 | 3600 |
| finalists | 0.000000000 | 9000 |

Metered build/validation/analysis child CPU consumption is 1277.512 seconds against four CPU-hours; four build jobs were used. Resource receipts include failed gates. Earlier focused developer checks have retained duration logs but no child CPU receipt; the metered subtotal is not represented as an exact whole-session total.

GPUP-EVIDENCE passes its bounded acceptance: large full witnesses fit, format/replay contracts hold, and all frozen fresh attempts are retained and independently classified. It does not require every solver to converge or a latency improvement. The next task is **GPUP-HOST**, one measured immutable host reconstruction/preparation repair with fresh candidate and certificate assessments.
