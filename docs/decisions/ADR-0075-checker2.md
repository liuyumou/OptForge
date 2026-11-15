# ADR-0075: Optimize exact checking and preparation under original authority

Status: accepted for isolated research
Date: 2026-11-14

## Context

SPEC-0041 measures about 46% exact checking and 34% preparation in strict
coupled2048 FP4 complete sessions. The user requests continuing these optimizations.
Existing caches and row/column parallelism require attribution before further work.

## Decision

Apply SPEC-0042 with an independent bounded allocation and isolated executor.
Preserve original serial certificates, validated input, numerical solve work and
CUDA image. Optimize both lanes equally; measure full fresh-session cost against
the admitted prior executor with an independently frozen paired cohort. No cached
endpoint answers, relaxed tolerances, public defaults or historical regrading.

## Consequences

CPU profiling, exact differential tests and process admission precede device
measurement. Negative and inconclusive findings remain durable. Previous allocations
and completed-task restrictions remain scoped to their original work. This user
request authorizes the new slice, with local commits and no GPUP-9 release.
