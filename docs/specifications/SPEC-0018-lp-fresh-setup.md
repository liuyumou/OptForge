# SPEC-0018: Fresh LP Device Setup Diagnosis

Status: accepted by the maintainer on 2026-09-29 before implementation
Scope: GPUP-SETUP, fresh single-process tuned LP studies
Owner: optimizer-cuda-sys, optimizer-cuda and bounded study tooling
Introduced: GPUP-SETUP
Last reviewed commit: 9bf8e8d5d6f6e4fd3b2eb60ae494506ed620323e
Supersedes: none; extends SPEC-0013 and the ADR-0009 boundary
Implementation: opt-in phase attribution and experimental primary contexts
Tests: lifecycle fault injection, strict study/replay identities and bounded device gates

## Requirements

1. Opt-in profiling MUST separate management discovery, driver loading/resolution,
   initialization, lookup, context creation, UUID checks, image preparation, module
   loading/lookup and teardown, retaining existing parent scopes and disjoint exclusive
   costs. Disabled observation MUST NOT read clocks or add device synchronization.
2. Four control profiles MUST complete before primary-context implementation. The
   diagnosis MUST report measured lifecycle contribution and an Amdahl upper bound.
3. Only lp-study tuned solve/replay MAY explicitly request --cuda-context
   user|primary-experimental, with a separate --setup-receipt output. Default and
   ordinary solve/session behavior MUST retain user contexts. Unknown/duplicate or
   incompatible options MUST fail before device work.
4. Experimental contexts MUST require no current context and an inactive primary
   context, use zero scheduling flags, retain once, make current and verify the
   requested UUID. Optional symbols MUST be resolved only on this path. No reset,
   persistent context, cache, cross-solve reuse or automatic promotion is permitted.
5. All buffers, modules and streams MUST drop before detach/release, with the shared
   host lease held through cleanup. Partial initialization MUST release each retained
   reference exactly once. Setup/cleanup failures MUST be retained and disqualify
   performance success, without altering mathematical certification of an endpoint.
6. Strict setup receipts MUST bind requested/observed policy, lifecycle outcomes and
   endpoint hash. The strict outer study binds source, binary, device, request, model,
   code images and receipt. Numerical endpoint v1-v5 formats MUST remain unchanged.
   Study replay MUST verify the source receipt and restore its context policy;
   ordinary endpoint replay retains its historical execution semantics.
7. Original-model host certification, settings, seeds, work charging, kernels,
   compact encoding and old artifacts MUST remain unchanged. No new device authority.
8. The append-only ledger, original output binding, historical prefixes and all
   cumulative/phase/category caps MUST hold for every device job, including failures.

## Interfaces and failure behavior

The safe device session gains explicit context-mode construction; existing open
calls select user mode. The native boundary owns optional primary symbols and an
owned context-kind tag used for teardown. A scoped thread-local observer records
setup and drop outcomes without selecting a context mode. Study receipts are
separate from the numerical endpoint and preserve errors even if no endpoint exists.
Failed or incomplete receipts cannot qualify as successful timings. Missing primary
symbols or incompatible current/primary state are explicit refusals; no fallback to
a different context policy is allowed. Inherited host-lease execution is required for
experimental primary study work, retaining ownership through process cleanup.

## Resources and acceptance

[ADR-0030](../decisions/ADR-0030-fresh-lp-setup.md) freezes 24 timings/eight profiles,
1800 GPU seconds within existing allowance and four CPU-hours. Full pinned-native
acceptance, exact-rational regressions, source-only budget/identity tests, regular
device gates, four primary-context sanitizers and twelve fixed-work pairs/replays
are required. Compare binary64 bits and physical work, excluding clocks and setup
metadata. No speedup threshold or supported preset is implied.

## Open questions

The experiment determines whether primary retention/release reduces fresh-process
latency. Historical mixed-65536, large-session and tuned_cases racecheck gaps remain.

## Acceptance evidence

The [bounded report](../benchmarks/lp-fresh-setup.md) verifies 32 attempts and 24
certified timings, with 16 matching numerical/work comparisons. Four control profiles
precede primary implementation. Full native, clean-source budget/identity tests,
58 candidate device tests, four primary sanitizers and twelve fixed-work pairs/replays
pass. No consistent latency benefit is established; legacy defaults and all historical
gaps remain. Source/binary/code images and the original ledger prefix are hash-bound.
