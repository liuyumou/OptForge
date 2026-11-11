# ADR-0056: Execute the persistent FP4 specification as CPU contracts

Status: accepted, 2026-11-11

## Context

The user requests GPUP-FP4-SPEC implementation and permits additional budget as
needed. The selected semantics allow approximate inner iterations with unchanged
original-model FP64 residual checks and 1e-9 final certification. ADR-0055 proposed
this direction after RESIDENT2 reduced synchronizations without retaining a
total-latency gain.

## Decision

Accept [SPEC-0025](../specifications/SPEC-0025-persistent-fp4-contract.md).
Implement exact CPU oracles and strict proposal/checkpoint/cost contracts, with
bounded E2M1 power-of-two expansions, shared matrix/transpose tile scales,
conservative projection/error decisions and observation-only audit transactions.
Bind the development grid and cost review to retained native evidence. Missing
hardware/profile evidence remains an explicit refusal to admit a performance
claim. This does not implement or authorize the device prototype.

Allocate an independent 16000 CPU seconds, zero GPU: implementation 3200
(including 256 preparation), contracts 1600, native integration 8000, reporting
2400 and cleanup 800. Use four slots and the unchanged in-container supervisor,
16 GiB sampled host RSS, whole reservations and retained failure charges. No
historical fund transfer or scientific rerun is authorized. Local commit follows
acceptance; no push/publication.

## Consequences

The executable specification can reject inconsistent operators, optimistic
error/cost claims and incomplete rollback state before device work. Its restricted
range and conservative enclosures may reject useful candidates; that is visible
evidence for a separately versioned design. It does not establish exact FP64
emulation, convergence, actual FP4 instruction accuracy or latency improvement.
GPUP-FP4-PROTO becomes next ready after this contract passes. GPUP-MIXED2 remains
an alternative, the native control remains supported, GPUP-8 remains incomplete
and GPUP-9 remains gated.
