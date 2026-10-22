# GPUP-REFINE: bounded correction LPs and guarded anchors

Status: complete bounded research evaluation, 2026-10-22; no preset selected
Owner: numerical backend and experiment tooling
Last reviewed commit: bootstrap
Contract: [SPEC-0021](../specifications/SPEC-0021-lp-refinement.md),
[ADR-0037](../decisions/ADR-0037-bounded-lp-refinement.md), operational repair
[ADR-0038](../decisions/ADR-0038-selected-device-activity-telemetry.md)
Implementation: [host](../../crates/optimizer-lp/src/refine.rs),
[CUDA products](../../crates/optimizer-lp-cuda/src/refine.rs),
[study evidence](../../crates/optimizer-experiment/src/lp_refine.rs)
Acceptance: full pinned-native gate, independent rational admission and endpoint
oracles, 66 ordinary device tests, three refinement differentials, nine fixed-work
replays and four scoped sanitizers

## Result and scope

The implemented native-FP64-outer correction method passes its bounded arithmetic,
device, recovery and replay gates. The frozen evaluation retains all 108 primary
attempts, independently verifies 48 endpoints and certifies 30/96 timing attempts.
Tuned FP64 certifies 21/24 timings; each refinement configuration certifies 3/24.
Refinement loses coverage on seven of eight development models. No sparse-product
speedup, general convergence result or supported preset follows.

All nine certified refinement timings are small-4, whose initial point already
passes original-model host certification. They perform **zero inner updates,
zero sparse products and no CUDA context creation**. The roughly 29–30x scoped
latency ratios measure an earlier host stopping path versus the unchanged tuned
control's 200-update assessment. They cannot establish a benefit from correction
LPs, FP32 arithmetic or anchored products.

Raw evidence is retained under `artifacts/gpup-refine-v1` and
`artifacts/gpup-refine-v2`; binaries and source archives remain local artifacts.
Tracked, independently reviewed outputs are [summary](data/refine/summary.json),
[exact residual checks](data/refine/exact-evidence.json),
[acceptance](data/refine/acceptance.json), [replays](data/refine/replays.json),
[kernel audit](data/refine/kernel-audit.json),
[final native receipt](data/refine/final-native.json) and
[artifact inventory](data/refine/artifact-inventory.json).

## Implemented numerical boundary

The original model becomes equality plus box with v=(x,z), B=[A,-I], g=(c,0).
Original IDs, objective sense/offset and bound tags are retained. Only A is stored
on the device; the activity identity is implicit. Host FP64 interval arithmetic
evaluates original residuals, anchor products, correction transforms and merit.
Separate dyadic primal/dual scales normalize residuals toward [1,2), reducing
the exponent as necessary and refusing overflow or lost nonzeros.

The transformed matrix is preconditioned once using the inherited settings.
A research-only checked interface rebinds its correction objective and bounds;
it cannot substitute a different matrix. The represented canonical coefficient
array and transpose permutation define both orientations. Conservative original
and represented norm bounds include preconditioning errors and the identity.
The inherited PDHG/Halpern controller retains native FP64 iterates, updates,
restart and weight state. **Vector updates and the controller execute on the
host**; the isolated CUDA image executes sparse products/reductions. FP32 modes
change sparse coefficients, products and reductions, retaining FP64 working state.

Frozen merit is the outward-enclosed maximum of equality residual divided by
max(1,sum abs(B_ij)*s_vj), box violation/s_v, and
abs(v-project_box(v-(s_v/s_g)*(g-B^T*y)))/s_v, with the ADR's fixed s_v/s_g.
Uncertified acceptance requires candidate.upper <= anchor.lower/2. Each of
representation, product/reduction, anchor/transform and state/update error receives
at most anchor merit/32 in these original merit units. Per-proposal interval
guards include actual products, recurrence operations and reconstruction; this
is checked progress at represented states, not a bound against an ideal infinite
precision trajectory. Original-model feasibility and certified gap alone admit
successful endpoints.

Limits are 32 outer corrections, 2000 physical updates per correction attempt,
50000 overall, assessment every 200 updates plus boundaries/final, and eight
anchor refreshes per attempt. Both anchor deltas are maintained directly. A
failed FP32 correction restarts once at its outer anchor with sticky FP64
promotion; failed work remains charged. Native failure terminates. Cancellation,
expired deadline and device failure cannot initiate recovery. Below the requested
tolerance merit floor only certification and remaining declared native recovery
are permitted.

In-memory checkpoints include masters, inner/controller state, anchor bases and
deltas, correction scales, generation, errors and assessment position. Restoring
the same engine preserves already charged work, sticky promotion and the earlier
deadline. Persistence and cross-solve reuse are excluded. `physical_updates`
counts attempted proposals including rejected/uncertain work;
`committed_updates` counts completed inner updates, including those in discarded
corrections; `corrections` counts attempts, including promotion restarts.
These are not interchangeable with the legacy control's iteration count.

Feature `precision-research` exposes the isolated host/CUDA modules and
`lp_precision_refine solve|verify|replay` example. Strict `lp-refine-v1` requests
and evidence bind model, options, method, source, executable, image and executed
device. Trace verification recomputes original merits, scales, progress and
certification. Replay compares numerical outcomes with their serialized floating
bits, excluding observational timing. Existing CLI defaults, schemas, kernels and
historical replay remain unchanged. No new unsafe or solver boundary is introduced.

## Admission and retained counterexample

The independent Fraction fixture covers 240 general models and 1200 exact
forward/reverse primal/dual/objective correction maps. It includes ranged,
equality, one-sided and free rows, free/fixed variables, both senses and offsets,
both anchor orientations and projected-stationarity/KKT equivalence. Fixture
SHA-256 is `ed83c38a962da0b276f1ab82e287b12887a200d20a9a2e8801553ffe2be662a1`.
After the study, a separate sparse Fraction oracle checks all 21 available new
method endpoints: **93 merit enclosures and 39 exact contractions** pass.
It independently computes original activities, bound violations, objective and
projected stationarity from binary64 input rationals, without the represented
operator or Rust interval implementation.

CPU tests retain a concrete rounded-step counterexample. Set step=.875*2^-500,
weight=1.5*2^574, norm=2^500. Subnormal rounding yields tau=2^-1074 and exact
tau*sigma*norm^2=21/16 > 1 despite the nominal .9 margin. The implemented gate
checks the actual rounded steps using an outward sqrt(tau)*sqrt(sigma)*norm
bound before committing work. The counterexample remains in the host tests.
Other fault tests cover cancellation, deliberately inaccurate products,
noncontracting/uncertain progress, exhausted refreshes, sticky promotion, stale
generations, matrix rebinding, checkpoint rollback of accounting/deadlines,
nonfinite data, memory/range refusal, forged success and changed identities.

Generated sm_120 code uses 40 registers, zero stack/shared/local bytes and compiler
zero spill stores/loads. The audit checks actual SASS FP32 multiplies/adds and
absence of atomic reduction; FP64 instructions remain for the native path and
analytic identity. The image SHA-256 is
`90ba929efc7ad5789116bbfbc145d723240c4fe8381151039f79a953d0faa5bf`.
Provisioning uses nvcc separately; ordinary Cargo builds have no toolkit/device
requirement.

## Frozen cohort, admission refusal and reader correction

The four configurations are tuned FP64 (resident, necessary uploads, separate,
warp32), refinement FP64, refinement FP32 and anchored refinement FP32. The
[v1 protocol](../../benchmarks/configs/lp-refine-v1.json) freezes the eight
GPUP-EXEC development models, three timing repetitions and three profile models
at 200 physical updates. Tolerances remain 1e-9, seeds 17/17001/17002 and deadlines
10/30 seconds. No holdout, threshold or supported setting was selected.

The first regular acceptance identity was activity-blocked before child launch:
a global process query returned an N/A PID for an unselected PRO 6000 even though
the selected 5090 was idle. Its request, raw telemetry, worker, zero child time,
source archive and **0.125948387 s** charge remain. All 108 primary cells and six
other acceptance gates of v1 remain unexecuted. ADR-0038 scopes both strict
management queries to the selected UUID and freezes the separate
[v2 continuation](../../benchmarks/configs/lp-refine-v2.json), on the same
RTX 5090 UUID `GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48`. No attempt identity
was retried and no device was substituted. All numerical Rust/CUDA sources,
executables and image bytes are identical between the cohorts.

Original source tree: `4e8af4e8fc3a197af2c5d8e31f7e25c798833588c7e8ae4986db487c80f294d6`.
Measured continuation source tree:
`b6a462fb9b43a168e2da890a75e70abd345d929dcfc1ae2dfcad173838f6d3a2`.
Every executed job holds the shared host lease and passes selected-device
activity admission. All primary failures, partial files, interruption receipts
and conservative charges are retained without retries.

The first final reporting pass failed with `KeyError: record`: its reader accessed
a compact control wrapper before decoding `endpoint`. The original failure log
is preserved. The [exact correction receipt](data/refine/report-correction.json)
binds measured/reviewed hashes of only the CPU report reader and its regression.
The corrected reader verifies the frozen archive and these declared differences;
no worker, endpoint, request, numerical source, image or ledger was changed or
executed again. The later exact residual oracle is separately identified tooling.

## Timing coverage and costs

Numbers below are certified timing counts out of three repetitions per cell.
Control latency is the median complete fresh-process latency in milliseconds;
failed or interrupted cells are excluded from successful latency comparisons.

| Development model | Tuned FP64 | Refine FP64 | Refine FP32 | Anchored FP32 | Certified control median ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| small-4 | 3 | 3 | 3 | 3 | 431.56 |
| scheduling-20x5 | 3 | 0 | 0 | 0 | 564.63 |
| irregular-2048 | 3 | 0 | 0 | 0 | 461.95 |
| dense_block-1024 | 3 | 0 | 0 | 0 | 421.46 |
| scaling-256 | 3 | 0 | 0 | 0 | 407.32 |
| irregular-32768 | 3 | 0 | 0 | 0 | 2530.88 |
| dense_block-65536 | 3 | 0 | 0 | 0 | 6243.52 |
| mixed-65536 | 0 | 0 | 0 | 0 | — |
| Total /24 | 21 | 3 | 3 | 3 | — |

Small-4 refinement medians are 15.00/14.62/14.90 ms. Paired median ratios against
control are 28.67 [26.70,32.26], 30.50 [26.50,31.82], 30.37 [26.88,30.79]
(95% paired bootstrap, three repetitions, 10000 resamples, seed 17002).
As explained above, only an early certification path was exercised.
Complete numerical outcomes repeat identically across all three repetitions of
small-4 and scaling-256 for each refinement mode; timing is excluded.

Scaling-256 returns nine verified numerical refusals in about 4.85–4.89 seconds.
Native products commit 800 of 801 charged proposals across five attempts before
`operator_error_budget`. Plain FP32 promotes once, commits 799/801 across six
attempts, and then hits the same native guard. Anchored FP32 promotes once,
commits 791/809 across six attempts, charges 16 refreshes/32 anchor products and
also refuses. Neither represented residual improvement nor an objective near
-121357598.64 establishes original feasibility. The exact residual summary and
host certificates retain that distinction. Do not report these as successful
solve latencies. The other 54 refinement timing attempts expire without complete
endpoints. Three mixed-65536 tuned controls time out with independently verified
interrupted endpoints, retaining their timeout classification.

The independent exact original-operator calculation finds maximum unnormalized
bound violations of 0.1990681 / 0.1994454 / 0.2083310 for the FP64 / FP32 /
anchored endpoints in repetition zero. Their normalized merits are approximately
0.0009677 / 0.0009534 / 0.0010755. Those small normalized values do not satisfy
the original-model acceptance checks. All three repetitions reproduce the same
numerical outcomes within each mode.

All 12 profile attempts remain. Three control profiles exit nonzero with complete,
verified iteration-limit endpoints (raw `process_failure` labels retained).
Three irregular-2048 refinement profiles complete 200 physical updates, with
verified iteration-limit endpoints. Six larger refinement profiles time out
without complete endpoints. These are cost diagnostics, not certified successes.
Different transformed dimensions/trajectories mean 200 updates do not imply
equal numerical work or progress between methods.

| irregular-2048 profile cost, ms | Tuned FP64 | Refine FP64 | Refine FP32 | Anchored FP32 |
| --- | ---: | ---: | ---: | ---: |
| Complete process | 404.00 | 9787.81 | 9770.82 | 9768.45 |
| Context | 193.83 | 269.72 | 198.64 | 199.95 |
| Preconditioning / transformed preparation | 26.62 | 55.45 | 54.88 | 55.11 |
| Kernels plus synchronization/readback | 3.30 | 12.92 | 13.51 | 13.24 |
| Vector upload (new method) | — | 5.29 | 5.27 | 5.39 |
| Host product interval guards | — | 2337.60 | 2387.94 | 2387.46 |
| Original assessments + final (new method) | — | 13.18 | 13.22 | 13.24 |

New phases are host-observed and inclusive: preparation/context and product
guards are within refinement, with teardown and serialization in complete cost.
Do not add overlapping scopes or call them hardware-counter kernel times.
The remaining time includes host FP64 recurrences, original-unit error mapping,
correction/reconstruction and merit evaluation. No hardware-counter claim is made.
Each new 2048 profile launches 400 products, transfers 14101376 bytes to device
and 19660800 bytes back, and records 1211 synchronizations. Anchored mode has
zero refreshes in this particular profile; its refresh path is exercised by
scaling-256 and fault tests. Scaling anchor refreshes cost about 4.92 ms,
already included, and failed/recovery work is never subtracted.

Observed primary process-tree RSS peaks at 835399680 bytes, below 8 GiB.
Verified new endpoints record up to 994176 device-buffer bytes; interrupted
attempts without endpoints do not supply a peak-memory receipt. Static checked
admission bounds resident device buffers to 1 GiB; no second resident operator
coexists during rebinding or promotion, also respecting the 2 GiB device
preparation allowance. These buffer counts exclude CUDA driver/context storage.
The separate conservative host preparation envelope, within 8 GiB, includes
canonical/transposed views, implicit activities, anchors/checkpoints, input and
promotion overlap. Shapes are capped at 65536 original rows/columns and
2^23 nonzeros, with up to 131072 transformed variables; the memory gate may
refuse a shape inside those ceilings. Artifacts remain below the 32 GiB cap.
CPU work uses four build jobs within the declared 21600-second allocation.

## Acceptance, accounting and reproduction

The exact-source pretrial full pinned-native `bash tools/check.sh` passes all
Rust/native, dependency, committed-record replay, documentation and smoke gates,
with 299 Python tests. The final full gate passes **304 Python tests**, including
the compact-reader regression and four independent endpoint-oracle regressions,
plus all Rust/native, dependency, historical replay, 130 documentation-page and
smoke checks. It uses 116.036960146 elapsed / 140.362833 CPU seconds, with
1644863488 bytes peak sampled process-tree RSS (1663217664 bytes maximum child
RSS). Native acceptance is enabled, not skipped. Ordinary Cargo builds do not
invoke nvcc. Only this CPU evidence and the artifact inventory change afterward.
The retained final log/resource receipt and exact-source marker are under
`artifacts/gpup-refine-v2`; no numerical files changed after device freezing.

All seven v2 GPU acceptance gates pass: 66 ordinary tests, three refinement tests
with 1920 bitwise product comparisons in both orientations/widths and repeated
calls (empty/partial blocks and long rows included), original CPU/device
trajectory differentials, memcheck, racecheck, initcheck, synccheck and nine
fresh solve/verify/fixed-work replay pairs. Sanitizer receipts are read from both
stdout and stderr and require zero errors/hazards. These scoped receipts do not
close historical unrelated racecheck/session/mixed-model gaps.

| Combined task allocation | Charged GPU seconds | Cap seconds |
| --- | ---: | ---: |
| Timing / screening | 1275.123297404 | 2300 |
| Profiles / ablations | 217.195487188 | 450 |
| Acceptance / repeatability, including blocked v1 | 49.400351920 | 850 |
| Total | **1541.719136512** | **3600** |

V2 alone charges 1541.593188125 seconds inside its reduced 3599-second cap.
Cumulative use is **19207.265220123 / 21602.574545061 seconds**. The final
16684-event ledger SHA-256 is
`e83d07792fb0775fc26d8d2cca8a2411f59fcbc94f742cafd8f6b844ffb60535`.
It preserves the exact original 16452-event prefix
`24949150272600fe58364f25ebbf7bf892f7454da342edc268d50684568c5f18`
and intermediate 16454-event refusal prefix
`900bbaed980f273db069819028e48ee8c896024e4492ade21382199b78ae8e6e`.
Every phase cap and the cumulative ceiling is independently checked. No added
campaign allowance or reservation for another task follows from unused headroom.

CPU-only reproduction with retained local artifacts:

```sh
python3 tools/lp_refine_oracle.py --check
python3 tools/lp_refine_accept.py verify
python3 tools/report_lp_refine.py
python3 tools/lp_refine_evidence_oracle.py
CARGO_BUILD_JOBS=4 bash tools/check.sh
```

`verify` and report commands check original-model endpoints without CUDA execution.
`replay` executes work and requires a separately authorized, charged shared-lease
job; it is not part of CPU verification. Never rerun primary study identities.
Source/image/ELF hashes, frozen requests, ledger charges, raw stdout/stderr and
all failures are required for the local verification above; tracked summaries
are not substitutes for those artifacts.

GPUP-ASSESS is the next bounded contract/proof task and is not started here.
Expansion masters, FP32 working state, selective precision, assessment policy,
sessions and supported presets remain outside this result. This experiment
rejects the evaluated guarded implementation as a general latency improvement;
it does not rule out separately specified refinement methods or cheaper guards.
