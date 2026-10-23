# ADR-0043: Loss-preserving Tensor residual continuation

Status: accepted, 2026-10-23, by explicit user approval of the bounded continuation
Owner: numerical backend and experiment tooling
Introduced: GPUP-8 continuation
Supersedes: ADR-0042 for a separate continuation only; historical study unchanged
Superseded by: none

## Context

The user requests continued work toward GPUP-8 completion. ADR-0042's frozen
study is exhausted. Its shared 56-bit block encoding loses tiny nonzero vector
entries before a useful window, although its kernels pass correctness gates.
Its rule to refuse lost nonzeros is correct for that representation. Continuing
requires a new arithmetic contract and new study identities, rather than retries
of any old cell. The user explicitly approves this separate continuation and its existing-allowance resource admission.

## Decision

Retain each dynamic vector as x = x0 + xr. The main operand x0 is the existing
signed 56-bit block integer times its power of two. Its explicit binary64
residual xr is computed from the original resident binary64 x. If the integer
part is zero for a nonzero input, retain the entire input in xr. Nonfinite,
overflow and unrepresentable reconstruction remain refusals. Prove the split
exact over finite binary64 inputs, including subnormals, before implementation.

Use the existing immutable represented matrix A0 for both orientations. Compute
A0*x0 with the existing exact INT8/FP16/BF16 component tile arithmetic and compute
A0*xr in deterministic native FP64 arithmetic, adding the correction once per
tile output. Keep the original coefficient/scaling error enclosure for A-A0.
Selected coefficients, transpose identity, tile occupancy and the native sparse
remainder do not change. No coefficient or nonzero vector value is discarded.
Native corrections, launches, transfers, guards, audits, rollback and replay are
charged and reported separately from useful Tensor work. Corrected products
need new rigorously derived outward bounds for coefficient error, tile rounding,
residual products/sums and outer reduction; passing an old bound alone is not a
proof for the new operation sequence. Preserve 1e-7 local absolute budgets and
fresh original-model 1e-9 host certification.

Preserve resident FP64 state, numerical update ordering, 32-update audits,
200-update restart/weight boundaries, conservative norm/step, checkpoint/session
ownership, whole-window charged replay and uniform sticky native promotion.
Fuse packing, guard and update dispatch only where operation order and bounds
are proved equivalent. Avoid a claim that numerical admission alone supplies a
latency improvement; both are required independently.

Isolate the implementation behind a new research identity lp-tensor-residual-v1,
with separate source archives, images, executable, strict request/evidence
schemas, CPU cohorts and reports. Historical executables/images/source bodies,
payloads and reports remain exact, including all four ADR-0042 CPU cohorts and
both device gates. No public backend, default, session, refinement combination,
FP8 path, preset or GPUP-9 work is included.

## CPU and device acceptance

First run an independent exact-rational split/product oracle and quantify residual
activity on both frozen dense trajectories. This is exploratory CPU evidence,
not device admission, a verified solve, or a timing comparison. Reject the
proposal if exact splits or conservative unchanged-budget bounds cannot pass.
Then require eight-model CPU admission, including a complete 400-update useful
trajectory on each dense model, before any device identity is reserved.

Require audited actual MMA instructions, at most 128 registers, zero spills,
CPU/device product and controller differentials, fixed-work endpoint/replay
pairs, all 66 ordinary GPU tests and all four scoped sanitizers. Failures remain
visible and charged; no completed identity is retried. Freeze the complete
source/executable/image/request roster and order before evaluation. Independently
verify every retained endpoint. Run full pinned-native tools/check.sh, including
CPU/docs/smoke, strict schema and source-only portability checks.

## Frozen continuation design and resources

Allocation uses only the unspent original 3000-second GPUP-8 allowance;
it adds zero GPU seconds and raises no task, phase or cumulative ceiling.
Starting task consumption is 236.856927634 seconds. Remaining phase allocations
are screening 1507.721563393, ablations 527.398140667 and repeatability
728.023368306 seconds, totaling 2763.143072366 seconds.

Keep the same six configurations and eight inherited CPU models. On each of
dense-block-1024 and dense-block-65536, retain five fresh-process repetitions of
INT8, FP16, BF16, represented SIMT, policy-matched FP64 and unchanged tuned FP64:
60 timing cells. Deadlines are 8/28 seconds, with six seconds reserved
per job overhead: total screening reservation 1440 seconds. Twelve forced
2000-update profiles and three product diagnostics each reserve 29+6 seconds:
525 seconds in ablations. Device acceptance reserves at most 700 seconds in
repeatability. Total reservations are 2665 seconds, below every remaining
allocation; task maximum would be 2901.856927634 / 3000 seconds. No transfer
between phases is needed. Refused/interrupted cells remain without replacement.
Shorter deadlines are explicit in this new protocol, never applied to old data.

The original 21600-CPU-second, four-job, 8-GiB RSS, 2-GiB preparation,
1-GiB device-buffer and 32-GiB artifact caps remain; prior CPU accounting is
10337.630178 seconds. Continuation must reserve CPU within the remainder and
stop before a cap is reached. Use only GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48
under shared host admission, with no device substitution. Keep cumulative GPU
ceiling 25202.574545061 seconds, independent campaign cap 28800 seconds and all
existing phase ceilings. Preserve all 17200 events with ledger SHA-256
5af7782a384ac73226f339d98d0b33e320518053c1accdf67c1339db36d0e0f1,
including the exact historical 17132-event prefix.

## Completion and consequences

Retain ADR-0042's substantive completion conditions: useful admitted INT8 and at
least one FP16/BF16 certified nontrivial solve; all five repetitions certify;
candidate coverage does not fall below tuned FP64 on either timing model; and
at least one paired total-latency speedup interval excludes one after Bonferroni
adjustment across six comparisons, at 95% family confidence, 10000 resamples,
seed 17002. Native-only promotion, residual-only work, initial host certificates,
product diagnostics and incomplete profiles cannot establish Tensor benefit.

The arithmetic repair may pass CPU admission and still be slower because of
packing, integer reconstruction, correction density or launch overhead. Retain
such a result as incomplete, with no budget expansion, retries, new models,
preset or GPUP-9 progression. Local commit after applicable acceptance; no
publication or merge. User approval covers this arithmetic change and separate study; numerical and
CPU/device admission still precede evaluation.
