# SPEC-0043: Scoped certified low-precision research capability

Status: accepted research milestone; satisfied for the retained MIXED2 FP4 prepared-session scope
Scope: GPUP-8 research readiness and its handoff to GPUP-9
Owner: numerical backend and experiment tooling
Introduced: GPUP-8 redesign / ADR-0077
Last reviewed commit: bootstrap
Supersedes: historical arithmetic-family and cold-only prerequisites for progression, not their recorded experimental criteria
Implementation: retained MIXED2 FP4/reuse/confirmation executors; no numerical source change
Tests: retained exact/native/device/recovery/serial/portable acceptance and the current evidence-recognition checks

## Purpose and terminology

Establish that at least one admitted low-precision method can perform useful
work and improve delivery of independently certified solutions in a declared
scope. A capability milestone permits further controlled research. It is not
a universal speed claim, a public preset or production adoption.

A complete prepared session begins with fresh process/input preparation and
ends after all requests, independent checking, durable output, EOF and owned
destruction. Its batch length and model-switch pattern are part of the scope.
A cold single solve has its own complete endpoint. Neither endpoint substitutes
for the other. A GPU event span is a nested diagnostic, never complete cost.

## Requirements

1. The capability MUST identify arithmetic, executor/configuration, source,
   binary/image, hardware/compiler target, workload, lifecycle and tolerance tier.
2. Claimed strict results MUST retain original-model host certification at the
   existing absolute/relative 1e-9 policy; a 1e-7 tier MUST remain separately labeled.
3. The candidate MUST perform useful nonzero low-precision work; all-native
   promotion or a host-only initial certificate MUST NOT establish that capability.
4. Numerical bounds, recovery and original-input ownership MUST retain their
   accepted source-bound contracts, including invalid input, unsupported ranges,
   overflow, cancellation, limits, rollback and native promotion.
5. Comparisons MUST use the same original models, required quality, compiler
   target, available resources and lifecycle for native and low-precision lanes.
   Policy differences such as audit windows MUST be disclosed. Shared host
   optimizations MUST apply equally; an implementation gain within a lane MUST
   NOT be attributed to low precision without a direct comparison.
6. The complete endpoint MUST include setup, transfers, all work and rejected
   work, audits, recovery, independent checking, delivery and destruction.
7. A qualifying complete study MUST retain all planned cells and certify every
   claimed successful solve, with no coverage loss versus its native control.
   Missing or refused execution MUST NOT be removed to manufacture a passing
   comparison or be filled by historical pooling.
8. Research value MUST be established in at least one strict family/tier
   comparison under that study's predeclared multiplicity-corrected ratio and
   positive savings criteria. All other comparisons, uncertainty and sensitivity
   results MUST remain visible; universal gain across every family is not required.
9. Recognition of existing evidence MUST use its original frozen statistical
   decisions and MUST explicitly identify the recognition as evidence-informed.
   It MUST NOT claim the new milestone scope was preregistered or that the legacy
   cohort met its old gate. Future studies MUST freeze their own criteria first.
10. Admission, independent checking, source-bound replay, resource receipts,
    cleanup and failure accounting MUST support the retained scope. Receipt
    reuse MUST be restricted to the source/image and behavior actually admitted.
11. GPUP-9 MUST receive its own protocol, workload/analysis freeze and independent
    budget before scientific execution. Completion of this capability MUST NOT
    open old allocations or authorize retries of frozen historical cells.
12. Public defaults and adoption MUST remain separate under GPUP-10. Hosted CI,
    external competitiveness and portability MUST support the relevant release
    or claim; they MUST NOT be blanket prerequisites for recognizing an already
    certified scoped research capability.

## Recognized evidence and interfaces

The [evidence map](../benchmarks/lp-gpup8-redesign.md) recognizes the original
MIXED2-CONFIRM2 comparison: native window32 versus FP4x2 window16, generic/coupled
1024/2048, separate 1e-7/1e-9 tiers, four original scenarios cycled eight times
per fresh 32-solve session, with FP64 reset on each solve. All 512 sessions /
16384 solves complete. Five of eight comparisons pass the original simultaneous
ratio lower bound >1 and savings lower bound >10 ms/session, including three
strict comparisons. The 10 ms floor remains a research value criterion, not a
production SLO. None passes the separate provisional 1.10 lower bound.

CHECKER2's exact shared improvements and source-bound admission are supporting
engineering evidence. Its portable-control/v4-candidate 1.1348–1.2832x ratios
remain within-lane results, and its FP4/native contrasts remain descriptive.
No new solver protocol, schema, arithmetic, operator or checker API is introduced.

## Invariants, errors and recovery

Retain FP64 state/original-A authority, conservative admitted FP4 bounds and
transactional restoration/native promotion. The new milestone does not change
determinism, signed-zero behavior, nonfinite handling, overflow behavior, error
ordering, cancellation or numerical limits. A complete cohort with no recovery
event is not evidence of universal recovery; retain the separate fault tests.
Constructed cyclic scenarios and a shared host limit generalization and temporal
independence. No original certificate is relaxed or cached by this decision.

## Compatibility and resources

[ADR-0077](../decisions/ADR-0077-gpup8-fp4-redesign.md) defines the explicit waiver
and supersedes ADR-0076's forward gate. GPUP-8-LEGACY retains the incomplete old
experiment; GPUP-8 is the redesigned, scoped capability. GPUP-CERTIFIED-COST-GATE
is superseded, not passed. The reviewed historical evidence and allocations stay
immutable. GPUP-9 becomes ready for its own protocol; no study starts here.

The current decision slice uses ADR-0077's independent 8000 CPU / zero GPU ceiling.
Future execution retains four CPU slots, 16 GiB sampled RSS, at most 12 GiB owned
device buffers, one pinned shared lease, the finite one-second supervisor and
100 ms advisories unless separately amended. Every study needs its own finite
wall/phase caps and reserved cleanup. Sampled RSS is not a hard memory enclosure.

## Acceptance mapping and open questions

Requirements 1–7 and 10 bind to retained numerical/native/device/process/recovery,
trajectory, serial-checker and portable receipts. Requirements 8–9 bind to all
eight original comparisons and their exact-binomial interval arithmetic.
Requirements 11–12 bind to the backlog dependency and public-default checks.
Current validation also requires the full native gate, documentation links and
exact preservation of historical bytes; it is not another scientific cohort.

Unresolved: current CHECKER2 direct FP4/native inference, final-source/compiler
factorial attribution, cold value, larger or production workloads, cross-host
portability, held-out robustness and hosted CI startup. These delimit claims and
future experiments; they do not negate the completed scoped capability.
