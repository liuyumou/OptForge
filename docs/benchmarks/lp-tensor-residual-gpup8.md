# Loss-preserving Tensor continuation: GPUP-8

Status: bounded continuation evaluated; GPUP-8 remains incomplete on latency gain,
2026-10-23, under accepted
[ADR-0043](../decisions/ADR-0043-tensor-residual-continuation.md).
The user explicitly approves a separate bounded continuation using only the
unspent GPUP-8 allowance. The [ADR-0042 report](lp-tensor-gpup8.md) and every
historical source/image/endpoint remain exact. This is a separate arithmetic
contract and study identity; no historical cell is retried or replaced.

## Arithmetic and proof

Represent each resident binary64 vector entry as x = x0 + xr, with the existing
56-bit block integer main part and an explicit binary64 residual. Toward-zero
truncation makes x0 have the same sign as x and at most its magnitude. If x0 is
nonzero, x0 <= |x| < 2*x0 in magnitude, so binary64 subtraction x-x0 is exact by
the factor-two subtraction property. If x0 is zero, xr=x exactly. The
independent Fraction oracle also checks this identity directly across exponent
spread, signs, normal/subnormal boundaries and every retained range witness.
No tiny nonzero input is silently dropped. Coefficient conversion still refuses
lost nonzeros; its outward original-unit error bound remains explicit.

Each selected tile computes a correctly rounded exact integer dot for A0*x0,
a deterministic FP64 serial correction A0*xr, then one FP64 sum of the parts.
For a tile group with n stored coefficients, let M=sum(|A0_i*x_i|). Because x0
and xr share the sign of x, their absolute masses sum to M before rounding.
Dot rounding, n residual multiplications, their serial sum and recombination
are bounded by gamma(n+4)*M plus (n+4) minimum-subnormal units. The coefficient/
scaling error contributes sum(error_i*|x_i|). A further gamma(group_count+2)
bounds the deterministic outer reduction. These terms use outward successor
operations and original-unit output scaling. Nonfinite results and lost-nonzero
arithmetic products still refuse. Local budgets remain 1e-7; final original-model
host certification remains 1e-9. CPU and device use the same operation order.

Residual multiplications have their own checked physical counter. Main Tensor
nonzero counts exclude values whose integer part is zero, so a residual-only
calculation cannot qualify as useful Tensor work. Resident FP64 state, immutable
operators, 32-update audits, 200-update numerical boundaries, whole-window charged
replay and uniform sticky native promotion remain.

## Frozen evaluation contract

The separate [protocol](../../benchmarks/configs/lp-tensor-residual-v1.json)
retains eight-model CPU admission, 60 fresh timing cells on the same two dense
models with five repetitions/configuration, twelve forced 2000-update profiles
and three product diagnostics. Timing deadlines are explicitly 8/28 seconds;
profile/diagnostic deadlines are 29 seconds. No refused or interrupted identity
is replaced. Device acceptance requires CPU admission, MMA/register/spill audits,
ordinary tests, arithmetic/controller differentials, fixed-work/replay checks
and all four scoped sanitizers. Full pinned-native CPU/docs/smoke and strict
source-only portability remain required.

Reservations are screening 1440, ablations 525 and repeatability 700 seconds,
total 2665, inside the original remaining allocation in each phase. No resource
ceiling increases. Previous consumption is 236.856927634 GPU seconds for GPUP-8
and 21596.442783423 campaign seconds. Preserve the exact 17200-event ledger
SHA-256 5af7782a384ac73226f339d98d0b33e320518053c1accdf67c1339db36d0e0f1,
including the exact 17132-event historical prefix. CPU allowance is 10000 seconds
inside the original 21600 seconds after prior accounting. RSS and artifact caps
remain 8 GiB and 32 GiB. Use only the originally authorized device under shared
host admission.

Completion still requires useful INT8 and floating Tensor certified nontrivial
solves and a multiplicity-adjusted certified total-latency gain over unchanged
tuned FP64, with all five pairs and no coverage loss across the two timing models.
Numerical admission and microbenchmarks alone do not establish completion.
GPUP-9, supported presets, publication and merge remain outside this task.

## Measured continuation result

The separate evaluation retains all 75 planned cells: **60/60 fresh timings
certify**, all twelve profiles complete exactly 2000 logical updates, and all
three product diagnostics pass. Each of the thirty INT8/FP16/BF16 timing runs
certifies at 2200 logical updates with 66 useful windows and no native promotion.
Thus useful integer and floating Tensor solves now qualify on both dense models.
All five repetitions certify in each configuration; candidate coverage equals
control coverage on both models.

Fresh-process median seconds, including all setup, transfers, correction, guards,
audits, recovery, original-model certification and output:

| Model | Tuned FP64 | INT8 Tensor | FP16 Tensor | BF16 Tensor | Represented SIMT | Matched FP64 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| dense_block-1024 | 0.462114 | 0.614776 | 0.625008 | 0.720782 | 0.608621 | 0.597043 |
| dense_block-65536 | 6.331022 | 10.390881 | 10.482344 | 10.739558 | 10.371203 | 10.352774 |

All six predeclared paired bootstrap intervals are below one, after Bonferroni
adjustment at 95% family confidence (10000 resamples, seed 17002). A ratio is
tuned-FP64 latency divided by candidate latency, so ratios below one indicate a
slowdown. **No certified total-latency gain qualifies.**

| Model | Candidate | Speedup | Adjusted interval |
| --- | --- | ---: | --- |
| 1024 | int8-tensor | 0.7517 | [0.7281, 0.9291] |
| 65536 | int8-tensor | 0.6093 | [0.6039, 0.6143] |
| 1024 | fp16-tensor | 0.7394 | [0.6164, 0.8300] |
| 65536 | fp16-tensor | 0.6040 | [0.5970, 0.6112] |
| 1024 | bf16-tensor | 0.6411 | [0.5356, 0.7732] |
| 65536 | bf16-tensor | 0.5895 | [0.5842, 0.6018] |

Tensor and policy-matched profiles use 2070 physical updates, including 70 audits,
and remain feasible but uncertified at their forced 2000-update endpoints. Their
fresh solve timings certify at 2200 updates. Tuned profiles use 2000 physical
updates and first certify at update 1400. Profiles remain diagnostic records.
On dense-65536 the INT8 profile spends 3.4695 seconds in host preparation and
1.2478 seconds in host audit arithmetic. Represented SIMT and matched FP64 are
also close to Tensor latency. These observations identify preparation, policy
checks and update count as material costs; they do not isolate a causal kernel
speedup or establish that a future optimization will win.

## Independent acceptance and resources

All 66 ordinary GPU tests, 280 CPU/device product pairs, five controller pairs,
twelve actual-model fixed-work/replay pairs and all four scoped sanitizers pass.
The exact split/rounding oracle checks 27164 cases, including all 73 retained
range witnesses; 12288 original-unit product components and all 961 BF16 digit
products pass. Lane addresses cover all 3072 matrix and 1536 vector positions.
The final image uses at most 88 registers, zero spills and audited IMMA/HMMA.

Independent frozen-verifier checks accept **120 continuation LP records**:
24 CPU endpoints, 24 device acceptance/replay endpoints and 72 study endpoints.
No payload is normalized or re-signed. Separate [machine report](data/tensor-residual/report.json),
[oracle](data/tensor-residual/oracle.json) and [instruction admission](data/tensor-residual/instruction-admission.json)
retain the exact evidence. All 1272 files in the prior GPUP-8 retained inventory
remain byte-identical; both historical ledger prefixes are checked independently.

Continuation GPU charge is **588.257104641 / 2665 seconds**: timing
322.826798512 / 1440, profiles/diagnostics
67.444213966 / 525 and acceptance
197.986092163 / 700. Combined GPUP-8 consumption is
**825.114032275 / 3000 seconds**; cumulative campaign consumption is
**22184.699888064 / 25202.574545061 seconds**. All existing phase ceilings and the
independent 28800-second cap remain unchanged. No identity is retried.
The 17362-event ledger SHA-256 is
e1766490f8de2affa14f4f950afed18be7f69531c3c28eedfd74539fcc0d9db5, preserving the exact 17200-event and 17132-event prefixes.

GPUP-8 remains **incomplete on certified total-latency gain**. The approved
continuation's frozen comparison is exhausted. No retry, replacement study cell,
relaxed numerical budget, supported preset or GPUP-9 progression follows from
unused headroom. Local delivery only; no publication or merge.

Final software/native/docs/smoke acceptance and CPU/RSS/artifact accounting are
recorded separately in the [delivery receipt](data/tensor-residual/acceptance.json).

## CPU preparation concurrency limitation

The initial four-worker CPU admission overlapped the first native build, which
also allowed four build jobs. Aggregate active jobs and RSS for that overlap were
not recorded. The aggregate four-job constraint therefore cannot be certified
for initial preparation; this is an additional resource-acceptance limitation.
The [separate receipt](data/tensor-residual/cpu-concurrency-limitation.json)
retains it explicitly. Subsequent acceptance and the leased GPU study run
sequentially. Conservative CPU time accounting and monitored RSS do not establish
an unrecorded aggregate concurrency bound. Software and numerical checks passing
do not imply full task resource acceptance. No historical evidence is removed or
reclassified to hide the overlap.

## Final software delivery acceptance

Final software delivery acceptance (2026-10-23): stable-source pinned-native
tools/check.sh passes 363 Python tests, Rust/native/dependencies, historical
replay, 142 documentation pages and smoke. All 248 GPUP-8 LP records freshly
verify (120 continuation plus 128 historical); the historical machine report
reproduces exactly. Source-only portability passes 39 tests without study
artifacts/native dependencies. Final gate source SHA-256 is
ed68a106e072dfe19d568f32898d7f39aed1b4fe0eb14e4d6ff266939508511a.
Conservative continuation CPU accounting is 8797.192667 / 10000
seconds; combined GPUP-8 accounting is 19134.822845 / 21600.
Monitored process-tree RSS peaks at 2671681536 bytes;
combined task artifacts total 1818373856 bytes, below 32 GiB.
These measurements do not certify the unrecorded aggregate four-job/RSS bound
during the initial admission/build overlap. Software acceptance passes; task
completion and full preparation-resource acceptance remain unmet. Separate
[delivery receipt](data/tensor-residual/acceptance.json).
Subsequent edits only record acceptance metadata; numerical sources stay exact.
