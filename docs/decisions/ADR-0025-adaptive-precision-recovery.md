# ADR-0025: Bounded Adaptive FP32/FP64 Recovery

Status: accepted by the maintainer on 2026-09-26 before implementation.
Scope: GPUP-6; extends SPEC-0012/0013, preserving every earlier contract.

## Interface and authority

Explicit `--lp-adaptive` on cuda-lp-tuned is exclusive with `--lp-precision` and
requires resident/necessary/warp32_v1/separate execution. Strict lp-adaptive-v1
settings name a monotonically widening ladder ending in fp64, an audit interval,
primal/dual absolute and relative audit tolerances, and null demotion or explicit
clean_windows and margin_fraction. Rungs are working_fp32, accumulation_fp32,
products_fp32, storage_fp32, fp64. FP64 alone is a valid control. These are
experimental settings, never defaults or supported presets. New solve records,
endpoints and study artifacts use version 5; earlier bytes and readers retain
 their meanings. Runtime stays within existing Rust ownership/unsafe boundaries.

Audits compare original-unit primal and dual components against
`absolute + relative * max(abs(pre_step), abs(reference))`. They are independent
of final feasibility/gap tolerances. The original model and host outward
certification retain all mathematical authority. No sampled audit certifies the
intervening trajectory. Existing precision kernels/code objects are reused unchanged.

## Recovery

Prepare canonical operators and one conservative step valid for all executable
rungs. Preparation guards record unavailable rungs; they never weaken guards.
Keep one active device executor, recreate residency on transitions, and admit the
maximum rung buffer requirement before execution. Include setup/transfers in costs.
Windows end at the audit interval or next controller assessment boundary. Save
complete numerical and policy state at their start and final pre-step state before
working-state narrowing. Passing audits adopt the original-operator FP64 endpoint.
Failed audits/guards restore the whole window, promote one rung and replay toward
 the same endpoint. Physical work, deadlines, cancellation and diagnostics never
roll back. Reserve closing-audit work; chunks are at most 64 proposals and the
 audited final step is isolated. Exhausted ladders fail without a proof claim.

Demotion requires clean windows and a charged CPU-mirror probe of the prospective
lower rung against the same FP64 reference with a stricter margin. Discard the
probe endpoint, demote at most one rung, and reset the clean counter. Sticky
policies never demote. Interruption/limits preserve the last committed endpoint
and previously validated results. Device failure is not numerical recovery;
availability fallback remains pinned HiGHS. No adaptive sessions, disk checkpoints,
component research arithmetic, FP8, Tensor Cores or portfolios are introduced.

## Frozen comparison

Use the twelve existing development instances, four existing profile instances,
unchanged seeds/method settings, 10-second solves, 50000 physical updates and final
1e-9 tolerances. Audit intervals 1/8/32/128; all three audit tolerances 1e-7 or
1e-5; sticky or demotion after four clean windows at margin 0.25. Seven ladders
comprise four direct-to-FP64 and three nontrivial gradual ladders.

Coverage: 26 configurations x 12 instances x 3 repetitions = 936. Configurations
are HiGHS, host, legacy/matched/tuned/precision FP64; five fixed precision controls;
adaptive FP64; and fourteen interval-32, 1e-7 recovery policies.
Policy interactions: 112 policies (seven ladders x four intervals x two tolerances
x two recovery policies), four adaptive FP64 interval controls and tuned/precision
FP64, on four profile instances x three repetitions = 1416.
Separate profiles: tuned FP64, adaptive FP64 interval 32, sticky direct accumulation
intervals 1/32/128, gradual working-state demotion interval 32 (all 1e-7), on four
profile instances = 24. Total 2376 planned attempts. Randomize within paired blocks
using the existing seed; retain failures, timeouts, unavailable and missing cells.
Measure fresh-process single-solve latency including certification and recovery.
No held-out evaluation or preset selection occurs.

## Resources and gates

Preserve 8278 ledger events, SHA-256
`c185d5c069a892f10654b737b0a96737005b1fe9a70b5f0f3ee445d162af976a`, and
7015920961503 charged nanoseconds. A new hash-bound authority chains the previous
throughput ceiling (8102574545061 ns) plus 6300000000000 ns, giving
14402574545061 ns. New study: 5400 seconds in ablations; acceptance: 900 seconds
in repeatability; combined 6300 seconds. Campaign 28800 seconds and all phase caps
stay unchanged. Old protocol accounting is unchanged. Require complete admission
reservations, original output binding and intact prefix before any leased job.
Stop at caps with explicit incomplete evidence. Four build jobs, four CPU-hours.

Require full pinned-native tools/check.sh; CPU fault injection and exact-rational
regressions; strict identity/schema/replay and clean-checkout budget tests;
regular device acceptance and four adaptive sanitizers; independent endpoints and
report with paired uncertainty, coverage, transitions, costs and full ledger.
Mark completion only after correctness gates pass. Preserve historical large-model
and tuned_cases racecheck gaps. Commit locally after acceptance; do not publish.
