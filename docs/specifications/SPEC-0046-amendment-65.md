# SPEC-0046 amendment 65: preserve nested-test affinity failure

The native storage counter recompiles byte-identically and passes the exact
full-tree comparison in operational CPU v25. Supervision remains live, but the
original live supervisor tests reject the worker's three-CPU affinity because
they explicitly require four available CPUs. Preserve the full 720 CPU-second
failed CPU-gate charge, raw tests, independent counter proof and empty cleanup.
Do not weaken those tests or change the four-slot requirement.

Fresh operational CPU v26 runs without the numerical/control placement wrapper so
its live nested supervisor tests retain all four admitted CPUs. Independently
repeat the source-bound counter audit as disk-inventory-admission-v2, then run all
original supervisor and current resource tests. GPU v21 remains unattempted and
requires passed v26, the new full idle window and its fresh final sample. Additive
cleanup plans bind those gates. Numerical image-v10 and its complete GPU admission
remain unchanged. No scientific timing cell has started, no attempted cell is
retried, and no allocation, timing threshold or certificate criterion changes.
