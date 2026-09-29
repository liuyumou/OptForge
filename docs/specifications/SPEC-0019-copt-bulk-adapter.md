# SPEC-0019: Isolated COPT Bulk Adapter

Status: accepted by the maintainer on 2026-09-29 before implementation
Scope: GPUP-COPT-ADAPTER, optional development-only external control
Owner: bounded Python study tooling; no runtime backend or native boundary
Introduced: GPUP-COPT-ADAPTER
Last reviewed commit: 8fdec89451c07ffea46a3d8630aa184b14e072c5
Supersedes: none; extends SPEC-0013 and ADR-0026

## Requirements

1. A separate worker MUST load canonical binary64 CSC data through COPT 8.0.6
   loadMatrix, explicitly set objective sense/offset and original ID names, and
   preserve variable/row bounds, continuous domains and coefficient import guards.
   Duplicate terms MUST be rejected, never coalesced. No coefficient rounding.
2. Historical wrappers, environments, witnesses/endpoints v1-v2 and numerical
   parameters MUST remain unchanged. Scalar and bulk fresh controls MUST share
   the new isolated Python 3.11, NumPy 2.3.4, SciPy 1.16.3 environment and pinned
   original COPT library/binding bytes. Missing dependencies MUST NOT cause fallback.
3. Every endpoint MUST receive fresh original-model Rust host certification.
   GPU claims require the inherited shared lease, pinned UUID and execution log.
   Native iteration limits and unavailable seed controls retain ADR-0026 meanings.
4. Strict study/trial v1 artifacts MUST bind adapter identity, command, source,
   dependencies, request, model, witness, endpoint, worker and optional profiles.
   Verification MUST reject substituted identities and artifact filenames/hashes.
5. Cost observation MUST separate sparse dependency import, preparation and native
   loading from solving, extraction, certification and teardown. Primary latency
   includes all fresh-process costs; profiling is a separately labeled diagnostic.
6. Every admitted attempt, failure and partial output MUST be retained. Recovery
   MUST never retry admitted identities. Preserve the full ledger prefix, campaign,
   phase and category caps, and original output binding.

## Interfaces and acceptance

New tooling is opt-in and uses identities copt-scalar-v1 and copt-bulk-v1.
The existing scalar worker is invoked unchanged; the bulk worker emits external
v2 evidence consumed by the existing external-certify/external-verify commands.
A pure CSC builder permits dependency-free construction/guard tests. Real CPU
readback compares both native representations with the original canonical input.
Malformed inputs and dependency failures are explicit errors, with no substitute
solver. Existing Rust mathematical authority and exact-rational tests remain.

[ADR-0031](../decisions/ADR-0031-copt-bulk-adapter.md) freezes resources and trials.
Require full native acceptance, clean-source strict identity/budget tests, real
readback and 24 certified min/max/profile endpoints. Report numerical/work
agreement separately from construction identity; a negative latency result is
complete evidence, not a preset. Historical gaps remain open.

## Acceptance evidence

The [report](../benchmarks/lp-copt-adapter.md) independently verifies all 84 attempts,
certifies 42/72 timings and 10/12 profiles, and retains every timeout/rejection.
Twelve native readbacks and 24 min/max/profile endpoints pass; 27/36 timing pairs
and 10/12 profile comparisons match, with deadline-limited CPU-default differences
explicit. Full native and source-only gates pass. Bulk construction is slower
end to end in every certified cell; no preset is selected.

Integration review adds CPU regressions for interrupted partial-output bindings,
surviving worker receipts, conservative recovery charges and exclusion from
successful timing samples. Declared coordinator/report corrections preserve every
measured worker, schema, protocol, endpoint and GPU ledger byte; scalar construction
remains the ordinary COPT path with unchanged runtime solver defaults.
