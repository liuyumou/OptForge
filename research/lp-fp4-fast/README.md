# FP4 bounded-window performance experiments

This isolated safe Rust executor and CUDA package implement
[SPEC-0028](../../docs/specifications/SPEC-0028-fp4-fast.md). The workspace solver
and the completed pilot remain unchanged. The CUDA source includes the immutable
pilot for matched comparisons and adds separately named ablations.

Each warp owns one independent 32-by-32 matrix block and one RHS. State uses
persistent packed components. MMA columns represent different components of that
same vector, so all eight columns can contribute to an eight-component product.
Exact-zero matrix planes are skipped; matrix instruction fragments are prepared
once. Local update arithmetic uses FP32 pairs. Hardware encoding preserves the
low component's decision at E2M1 rounding midpoints, uses a native warp maximum,
and packs codes with three shuffle stages. A separate cached FP64 control is
retained for comparison.

The executor accepts `INPUT IMAGE OUTPUT`. Input can use strict JSON or the
bounded `FP4FAST1` little-endian transport written by
`tools/lp_fp4_fast_prepare.py`. Both preserve original binary64 coefficients.
The output file must not exist. Inputs permit at most 4096 independent blocks,
32 updates and 21 fresh-state repetitions. Every repetition restores a complete
checkpoint; cancellation and refusal roll back state, scales, flags and raw
exports. Measured output includes CUDA events, reset/export/audit time, transfer
counts, original-A residual observations and every repeated sample.

Selected hardware kernels require actual E2M1 device arithmetic, exact legacy
state comparisons, independent products, nontrivial dense trajectories and four
sanitizers before formal timing. `lp_fp4_fast_study.py` freezes the final sources,
image and randomized grid. Exploratory ablations, including slower caching
variants and failed compiler images, remain in their versioned artifacts.
`lp_fp4_fast_budget.py` uses the unchanged repository supervisor and separately
accounts all attempts. A closed allocation cannot launch additional jobs.

A fresh build needs the pinned Rust toolchain, CUDA 13 with SM120a support and the
existing safe CUDA driver crate. GPU execution checks the experiment's pinned
GPU UUID and inherited shared lease. Provision/build/test commands must run under
a newly authorized resource package; the delivered experiment is not implicitly
restarted by Cargo builds or tests.

The measurements concern bounded inner iterations. Exported FP64 values and
observed iterate errors do not establish an FP64-equivalent solver, a proved
trajectory enclosure or a final LP certificate. Certified integration still
requires the numerical recovery policy and original-model checking gate.
