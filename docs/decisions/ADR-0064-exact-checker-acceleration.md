# ADR-0064: Optimize exact checking before more GPU arithmetic

Date: 2026-11-11
Status: accepted under the user's continued checker optimization request

The completed FP4-ACCEL study finds strict dense512 FP4 GPU work faster than the
improved native control (4.457 versus 5.347 ms at the same 200 updates), but its
10.342 ms independent checker dominates complete prepared time. Cold overhead
is roughly 700 ms; sub-millisecond dense iteration savings cannot yield the
required 10% broad cold gain, while sparse/small tensor work regresses.

Implement [SPEC-0032](../specifications/SPEC-0032-exact-checker-acceleration.md)
in a separate research package. Cache original variable lookup indices and
optimize exact certificate work only with bit-level original-authority admission.
Apply checking improvements equally to native and FP4. Reuse the admitted device
image and numerical controller unchanged; preserve all historical evidence.
Separate CPU phase profiles from a new fully charged matched complete-cost study.
The new independent 24000 CPU / 1200 GPU envelope belongs only to this task.
No public preset follows without the existing complete-cost retention gate.
