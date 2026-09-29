# SPEC-0016: Immutable Host Input for Fresh LP Evidence

Status: accepted by the maintainer on 2026-09-29 before implementation
Scope: GPUP-HOST; one duplicate model reconstruction in fresh solve evidence
Owner: optimizer-experiment and CLI
Introduced: GPUP-HOST
Last reviewed commit: 1818cdb5405fe466728c9cfb1719c67e22f660a5
Supersedes: none; extends SPEC-0013 and SPEC-0015
Implementation: LpInput and fresh-solve endpoint construction
Tests: constructor, CLI reconstruction-count and bounded study acceptance

## Purpose

Remove the repeated JSON parse and structural validation of the exact same model
when a fresh solve constructs its LP evidence. Retained irregular-32768 profiles
attribute approximately 143 ms to this duplicate. No latency gain is assumed.

## Requirements

1. An opaque LpInput MUST own one validated Model and borrow its exact original
   bytes. Only from_bytes constructs it; fields are private and model access is
   read-only. It MUST NOT accept an independently supplied model, hash or program.
2. The fresh CLI solve MUST parse through this input once, borrow its model for
   solving, and consume the input when constructing endpoint evidence.
3. Endpoint creation MUST hash the original bytes, freshly construct its sparse
   LinearProgram, and freshly evaluate the candidate, certify the dual and assess
   the gap. No assessment, certificate, sparse operator or prepared matrix is cached.
4. LpEndpoint::new MUST remain a compatible raw-byte wrapper sharing the same
   endpoint assembly. Standalone verification MUST reconstruct from raw input.
5. v1-v5 evidence, compact/legacy encoding, replay, fallback, failure classification,
   row identities, arithmetic, kernels, numerical settings and defaults MUST retain
   their contracts. Reuse is within one fresh solve, never across solves.
6. Existing opt-in profiling scopes MUST expose the removed parse/validation call.
   A completed first-order fresh solve constructs two sparse programs as before.
   All candidate/certificate assessments remain fresh and counted.
7. The frozen gpup-host-v1 comparison MUST use both archived executables, identical
   compact output and settings, independent old/new verification and retained failures.
   Profiling is separate from primary fresh-process certified latency.
8. All GPU work MUST use the existing shared lease, append-only campaign ledger,
   prior prefix and phase/cumulative limits. ADR-0028 fixes the task allocations.

## Interfaces and ownership

optimizer_experiment::lp::LpInput<'a> exposes from_bytes(&'a [u8]), model(&self)
returning &Model, and consuming into_endpoint(requested_backend, record,
diagnostics, fallback_reason) returning Result<LpEndpoint, ValidationError>.
The wrapper LpEndpoint::new preserves its signature. The backend API is unchanged.
The input retains no additional byte copy and offers no mutable or raw-parts API.

## Errors, compatibility and resources

Parsing errors occur at the original input boundary. Assessment failures, invalid
witnesses, unsupported discrete LPs and identity failures remain errors. Interrupted,
limited or fallback records cannot gain mathematical authority through reuse.
No endpoint migration is required. New study protocol/trial schemas are strict,
separate artifacts; historical schemas and protocols remain unchanged.
The input lives only for the fresh solve. Four build jobs and four CPU-hours bound
validation; GPU category bounds and memory/deadlines are fixed in ADR-0028.

## Acceptance

Requirements 1-5: constructor equivalence for endpoint versions 1-5 and exact-byte
identity; malformed input, changed same-ID models and tampered witnesses/assessments;
legacy/compact CLI, independent verification, replay, fallback and unsuccessful
outcomes. Identical unprofiled record inputs produce byte-identical evidence.
Requirement 6: CPU CLI profiles show one parse/validation, two sparse constructions
and unchanged assessment counts. Requirements 7-8: strict schema/provenance and
synthetic-ledger budget tests, full pinned-native tools/check.sh including exact
rational regressions, regular device acceptance, fixed-work comparisons and replay,
24 fresh timing attempts and four independent profiles with all gaps retained.
A measured speedup is not required; no preset is selected. Open questions: actual
latency and peak-memory effects are resolved by the bounded report.

## Acceptance evidence

The [GPUP-HOST report](../benchmarks/lp-immutable-host-input.md) records full native,
CPU and regular device gates, all 28 independently verified attempts, 24 certified
timings and unchanged assessment counts. The raw-byte constructor and opaque input
produce identical v1-v5 evidence for identical unprofiled records. No cross-solve
reuse or numerical change is introduced. Historical limitations remain explicit.
