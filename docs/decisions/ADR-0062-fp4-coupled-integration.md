# ADR-0062: Integrate bounded coupled FP4 execution and operational recovery

Status: accepted implementation contract, 2026-11-11
Owner: numerical backend and CUDA runtime
Implementation: [SPEC-0030](../specifications/SPEC-0030-fp4-integration.md)

The user requests GPUP-FP4-INTEGRATE and aggressive performance optimization.
The completed FAST kernel only evolves independent 32-by-32 blocks. A meaningful
integration must first add real cross-tile dependence, general bounds, complete
checkpoints, audits, recovery and independently checked endpoints.

Use a separate one-CTA coupled executor up to 128 rows/columns, keeping packed
state and both operator orientations resident. Extend the pilot's fixed-step
PDHG recurrence, with identically configured native/FP8/FP16 controls. This is a
bounded research variant, not a replacement for the production native solver.
Select SPEC-0029's operational residual policy and original-model final authority;
no global trajectory enclosure or general convergence proof follows.

Use a persistent safe Rust service and reuse the admitted CUDA driver boundary.
The checker has an independent mode using unchanged original-model certificate
mathematics with explicit tier parameters. Optimize measured complete delivery
cost, preserve cancellation/checkpoint semantics, and retain failures. New source
versions and ordinary development repairs are allowed under this user's request;
formal frozen scientific cells are not automatically retried.

The independent allocation is 96000 CPU / 14400 GPU seconds, itemized in SPEC-0030.
The earlier proposal was non-executable and earlier allocations stay closed.
Freeze the 96-cell integration grid after admission, then a separate bounded
same-tier performance comparison. Report honest coverage and latency, including
negative results. No supported preset, TENSOR2 campaign, GPUP-9 run or publication
is released by this integration work. Commit locally after acceptance.

Delivery: [GPUP-FP4-INTEGRATE](../benchmarks/lp-fp4-integrate.md) completes all
96 diagnostics and 576 cold/prepared solves. Safety and original-model endpoint
admission pass; same-tier certified coverage matches native. FP4 cold geometric
means of 0.959–0.986x fail retention, so no preset or TENSOR2 execution follows.
All failed development charges and exact old evidence remain preserved.
