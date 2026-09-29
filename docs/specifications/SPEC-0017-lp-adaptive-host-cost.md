# SPEC-0017: Adaptive LP Preparation and Host Copy Costs

Status: accepted by the maintainer on 2026-09-29 before implementation
Scope: GPUP-ADAPTIVE-COST, within one fresh adaptive solve
Owner: optimizer-lp and bounded study tooling
Introduced: GPUP-ADAPTIVE-COST
Last reviewed commit: 5b9a9d083b27547e8bcb3ee4c9d265dde1a40bbb
Supersedes: none; extends SPEC-0012 and SPEC-0013
Implementation: shared adaptive operators, streamed audits and borrowed probes
Tests: host legacy differentials, fixed-work/replay and bounded study

## Purpose and requirements

1. PreparedAdaptive MUST construct at most one PrecisionOperator for each matrix
   width present in the canonical ladder. It MUST share successful immutable
   operators and reuse failures, preserving the failure entry for every rung.
   All operators MUST be prepared against the same original engine step; the
   conservative common step MUST be restricted only after preparation completes.
2. Audit comparisons MUST unscale each pre-step, proposed and reference component
   separately in original units and preserve the existing multiplication, error,
   allowance, finite checks, shape behavior and primal-before-dual traversal.
   They MUST NOT allocate the six temporary unscaled vectors.
3. Probes MUST borrow the original state except for working_fp32, which MUST retain
   the full clone and ordered working/anchor narrowing. Reference updates, sparse
   products, endpoint narrowing, controller state and work charging MUST be unchanged.
4. Checkpoints, window rollback, promotion/demotion, guards, cancellation, deadlines,
   original-model assessment/certification and single active device residency MUST
   retain SPEC-0012 behavior. No mathematical authority is cached.
5. CLI settings, v1-v5 evidence, compact encoding, replay, identities, defaults,
   precision kernels and code images MUST remain compatible. Reuse MUST NOT cross
   solve boundaries. Sessions, presets and numerical tuning are excluded.
6. Existing opt-in profiling MUST separate preparation and copying from required
   reference arithmetic; reports MUST avoid double-counting nested scope times.
7. The strict gpup-adaptive-cost-v1 study MUST bind source, binary, model, policy,
   precision code image, settings, request and output identities, verify complete
   endpoints with both archived executables and retain every unsuccessful attempt.
8. Every GPU job MUST preserve the shared lease, append-only ledger prefix, original
   output binding, cumulative and phase caps. ADR-0029 fixes resources and schedule.

## Interfaces and compatibility

PreparedAdaptive.operators changes to
Vec<Result<Arc<PrecisionOperator>, &'static str>>. The Arc owns one immutable
represented matrix and its admission observations; borrowed consumers dereference it.
PrecisionOperator::new and proposal/run signatures stay unchanged. There is no new
solver option or evidence version. The separate study/trial v1 schemas are strict;
historical schemas and protocols remain unchanged. Existing caller ownership of the
engine and its paired prepared ladder remains the contract.

## Errors and recovery

Conversion failures retain their exact reasons and per-rung visibility. Failed
preparation never executes. Shape mismatches, nonfinite audit arithmetic and probe
narrowing failures preserve existing results. Interrupted and failed execution
cannot gain a proof claim. All physical work remains charged across rollback.

## Resources and acceptance

Four build jobs and four CPU-hours; task GPU cap 1800 seconds within existing
allowance, with timing/profile/acceptance caps 1000/300/500. See ADR-0029 for the
frozen study, reservations, bounds and ledger prefix.
Requirements 1-3: compare all sixteen valid ladders and independent old audit/probe
implementations bitwise, including failed conversion, zero/subnormal coefficients,
signed zero, tolerance boundaries, nonfinite values and shape mismatches.
Requirements 4-5: retain host fault injection, exact-rational regressions, regular
device tests, four adaptive sanitizers and twelve old/new fixed-work pairs plus
twelve compact replays, verified by both binaries. Requirements 6-8: strict identity,
clean-checkout synthetic-ledger tests, 24 timing attempts and eight separate profiles.
Full pinned-native tools/check.sh is required. No speedup is an acceptance condition.

## Open questions

The bounded report will determine scoped latency, memory and remaining arithmetic
cost; historical large-model/session/racecheck gaps remain outside this change.

## Acceptance evidence

The [bounded report](../benchmarks/lp-adaptive-host-cost.md) records full native,
all-ladder/legacy differentials, source-only budget/provenance tests, 55 regular
device tests, four adaptive sanitizers and twelve fixed-work pairs plus twelve
replays. All 32 study attempts verify, all 24 timings certify and all 16
numerical/work pairs match. Historical gaps and unchanged arithmetic remain explicit.
