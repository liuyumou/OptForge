# Corrected FP4 acceleration research executor

Implements [SPEC-0031](../../docs/specifications/SPEC-0031-fp4-corrected-acceleration.md)
in an isolated package, with actual SM120 E2M1 tensor instructions, retained
FP32-pair iterates, original-coefficient FP64 reference products per at most 32
updates, original-model audits and independent 1e-7/1e-9 certificates. The bounded
model domain is at most 512 rows/columns; this is not a general sparse solver or
a proved trajectory enclosure. Public solver defaults are unchanged.

The `native` lane is fused FP64; `nativefast` uses parallel tiles on dense models.
`fp4x2` and `fp4x4` use fused centered products; `gridfp4x2` and `gridfp4x4` spread
tiles and their reductions across GPU blocks/warps. Scalar correction controls
remain available as `scalarfp4x2`/`scalarfp4x4`. `auto` selects native for sparse
and smaller dense inputs and two-component grid FP4 for dense padded size 512.
It is an experimental study policy, not a supported performance preset.

Build with the pinned Rust toolchain and `cargo build --release --offline --locked
--manifest-path research/lp-fp4-accel/Cargo.toml`. Image builds use
`tools/setup_fp4_accel.py` and preserve versioned PTX, SASS and compiler receipts.
Device execution requires the pinned shared lease and must use
`tools/lp_fp4_accel_budget.py`; the allocation and failure accounting are separate
from every earlier experiment. The `serve` API caches original model, checker and
GPU preparation, then resets all iterates/controller state per solve. Cold `once`
execution includes actual startup/preparation. CPU-only `check` and `check-serial`
replay the same original-model certificate with parallel/serial column scheduling.

Original enclosure and reduction sources are included without modification.
Column terms are concatenated in original order before the unchanged final tree;
600 differential cases require identical certificate bits or first refusal.
`check-serial` remains the independent replay authority. No fast-math flags are used.

Qualification and lifecycle tools cover independent component recurrences, exact
rollback, actual failed conversion, cancellation, stale requests and hard limits.
Four sanitizers precede the frozen complete-cost cohort. Formal cells cannot be
retried. Raw endpoints and receipts remain replayable; every failed development
source/image/log/reservation is retained.

The completed [measured report](../../docs/benchmarks/lp-fp4-accel.md) distinguishes
the dense kernel improvements from the failed broad cold-latency criterion.
`lp_fp4_accel_cold_delivery.py` supplies the separately validated EOF-driven cold
adapter. The optional `lp_fp4_accel_plot.py` requires Matplotlib, which is not
installed in the execution environment; its failed source/charge is retained and
the report uses exact numeric tables instead.
