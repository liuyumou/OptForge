# ADR-0067: Implement factorial delivery diagnosis and independent confirmation

Status: accepted implementation slice, 2026-11-12
Specification: [SPEC-0034](../specifications/SPEC-0034-delivery3.md)
Protocol decision: [ADR-0066](ADR-0066-delivery-retention-scope.md)

The user requests implementing GPUP-DELIVERY3. Separate checker batching and
checker/device setup overlap in a new executor while preserving all numerical
state transitions, exact certificates and historical sources. Instrumented
factorial diagnostics establish measured phase effects; a disjoint uninstrumented
cohort selects one candidate per lifecycle. Freeze both choices before the full
32-block confirmation. No lane-specific or outcome-dependent dispatch.

Independent prepared sessions and closely paired, balanced configurations address
DELIVERY2's single-session uncertainty. The new median-of-block estimands and
simultaneous intervals implement the prospective scoped decision without
regrading the historical failure. A failed or inconclusive prepared route retains
the control, regardless of a cold gain. A delivery gain helps either arithmetic
lane and does not establish FP4 superiority.

The specification supplies a new bounded CPU/GPU allocation and whole-block
reservations. Exact CPU/source/lifecycle admission precedes new GPU diagnostics;
the unchanged device image alone reuses its prior sanitizer acceptance. All
failures retain sources, partial evidence and full reservation charges. Historical
allocations remain closed, public defaults unchanged, GPUP-9 gated.
