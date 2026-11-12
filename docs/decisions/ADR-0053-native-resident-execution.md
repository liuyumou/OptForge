# ADR-0053: Attribute and bound native resident execution

Status: accepted for GPUP-RESIDENT2 implementation, 2026-11-11

The user requests GPUP-RESIDENT2 and permits additional time. PR #23 is merged.
Implement [SPEC-0024](../specifications/SPEC-0024-native-resident-execution.md)
with a separate bounded allocation and research identity. Existing tuned native
execution already batches 64 updates; the experiment therefore compares actual
complete delivery rather than assuming fewer synchronizations imply a gain.

Use immutable preparation, explicit cold/prepared lifecycles and same-transport
native controls. The candidate uses bounded coefficient tables and per-coordinate
sticky flags with transactional host adoption. Keep warp32 reduction, FP64
arithmetic, controller boundaries and original 1e-9 certificate. Normal limits
may export actual vectors, while infinite variable bounds remain mathematically
infinite. No certified claim follows merely from successful transport.

No graph capture, new unsafe boundary, vendor change, public/default backend or
precision change is introduced. Preserve all prior sources/results and charges.
GPUP-8 remains incomplete and GPUP-9 gated. Retain an optimization only if total
latency improves without coverage loss; negative research remains labeled.
