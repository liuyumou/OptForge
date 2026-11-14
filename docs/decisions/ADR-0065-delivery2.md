# ADR-0065: Batch checker transport and overlap independent preparation

Status: accepted implementation slice, 2026-11-12
Specification: [SPEC-0033](../specifications/SPEC-0033-delivery2.md)
Roadmap: [GPUP-DELIVERY2](../plans/gpu-lp-precision-roadmap.md)

The user requests DELIVERY2 implementation. Retained FP4-CHECKER evidence shows
cold setup dominates; its source writes each JSON token directly to ChildStdin
and starts independent checker preparation after CUDA initialization. These are
concrete delivery mechanisms, distinct from the unattributed timing residual.

Use a separate Rust package, preserving historical numerical sources. Batch pipe
writes without changing endpoint representation; start the independent CPU checker
before device setup and join its readiness before any solve. Retain fresh checks,
model/endpoint/image bindings, exact refusals, durable output and bounded cleanup.
The same executable exposes the retained delivery control to isolate the change.

CPU transport measurements establish the mechanism; a separately admitted matched
complete-cost cohort measures whether it matters. Any speedup is a delivery gain,
not evidence of faster FP4 arithmetic. A failed cold retention gate remains a
negative result and selects no preset. Historical budgets remain closed. The new
bounded allocation and admission order are in SPEC-0033; this is no GPUP-9 release.
