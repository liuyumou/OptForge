# ADR-0030: Fresh LP Setup Attribution and Experimental Primary Contexts

Status: accepted by the maintainer on 2026-09-29 before implementation.
Scope: GPUP-SETUP under SPEC-0018 and SPEC-0013.

## Decision

Attribute fresh setup before one experimental repair: primary-context retain/release.
Keep ordinary user contexts as the default and control. Record control attribution
before implementing the candidate; preserve the instrumented control archive and
its four profiles. All primary-context work uses an explicitly inherited host lease,
no prior current/active context, zero scheduling flags and checked cleanup outcomes.
No reset or persistent context is allowed. Driver calls remain inside optimizer-cuda-sys.
See [NVIDIA lifecycle documentation](https://docs.nvidia.com/cuda/archive/13.0.3/cuda-driver-api/group__CUDA__PRIMARY__CTX.html).
A negative result completes this bounded study; no default change or preset follows.

## Frozen study

Archive clean baseline 9bf8e8d5d6f6e4fd3b2eb60ae494506ed620323e before edits.
Archive the instrumented user control and candidate separately. Study identity is
gpup-setup-v1. Two context paths, tuned FP64 and sticky direct adaptive accumulation
FP32 to FP64, small-4 and irregular-32768, three timing repetitions: 24 timings.
Eight separate profiles cover each combination once; four user profiles run first.
All complete endpoints are independently checked by both archived study binaries.
The clean original binary also supplies the twelve established 200-update acceptance
controls; replay twelve primary candidate endpoints with their recorded setup policy.
Keep every failure, missing comparison and attempted identity; never retry one.

Retain GPUP-ADAPTIVE-COST method settings, seed 17, threads one, affinity [0],
1e-9 final tolerances, 50000 physical updates and 30-second deadlines. Adaptive audit
interval 32 and all audit tolerances 1e-7; direct demotion absent. Execution is
resident/necessary/warp32_v1/separate, compact-v1 evidence. Device UUID is
GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48. Host/device bounds 8 GiB; output 32 MiB,
model reads 128 MiB, CPU verification 120 seconds, cleanup two seconds, RSS poll
10 ms. Freeze order seed 19001, analysis seed 19002, 10000 bootstrap resamples,
95% paired intervals. Profiles never replace primary timings. Scope is development.

## Resource authority

Initial charge 15407672759957 ns, 15528 events, prefix SHA-256
cb0dc57f9f92546f4cc2d93b0de3c8556d6b24517f71b7a6efaa91fa96afedb6.
Preserve cumulative ceiling 18002574545061 ns, original output binding, every
historical prefix, 28800-second campaign and all phase caps. Additional allowance
zero. Timing 900 seconds in ablations; profiles 300 and acceptance 600 seconds in
repeatability; combined 1800, no borrowing. Each timing/profile reserves 36 seconds:
864 timing and 288 profile seconds. Reserve full bounds before admission, serialize
under the shared lease and charge uncertain work in full. Stop with explicit missing
cells at any cap. Four build jobs and four CPU-hours, with retained metered receipts.

## Acceptance and delivery

Require full pinned-native tools/check.sh before device admission, lifecycle fault
injection, profile accounting, strict setup/trial/provenance and clean-checkout
synthetic budgets. Run regular device acceptance and memcheck/racecheck/initcheck/
synccheck on primary contexts. Twelve fixed-work original/primary comparisons and
twelve setup-bound replays must match numerical bits and charged work. Reports bind
all source/binary/schema/code-image identities, retain failures and report setup,
certified latency/coverage, overhead, memory, uncertainty and lifecycle outcomes.
Preserve old racecheck/session/large-model gaps. Commit locally after acceptance;
no publication. Handoff is optional GPUP-COPT-ADAPTER without beginning it.
