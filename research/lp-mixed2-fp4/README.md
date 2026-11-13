# MIXED2 FP4 research executor

This isolated SM120a executor uses two/four normal E2M1 tensor components for
matrix increments, FP64 persistent state and original-matrix references, outward
local error bounds, transactional promotion and an independent original-model
CPU certificate at `certified-1e-7` or `certified-1e-9`.
See [the numerical contract](../../docs/specifications/SPEC-0038-mixed2-fp4.md)
and [measurements and limitations](../../docs/benchmarks/lp-mixed2-fp4.md).
The root solver's public defaults are unchanged.

Build on the repository's pinned Rust toolchain:

```sh
cargo build --manifest-path research/lp-mixed2-fp4/Cargo.toml --release --locked
bash tools/check_mixed2_fp4_cpu.sh
```

Ordinary Cargo builds require no CUDA toolkit or device. Compile the explicit
research image with CUDA 13 and SM120a support:

```sh
nvcc -O3 -lineinfo -fmad=false -ftz=false -arch=sm_120a --cubin \
  research/lp-mixed2-fp4/cuda/mixed.cu -o /tmp/mixed2-fp4.cubin
```

The service command is `lp-mixed2-fp4 serve IMAGE MODEL`. It requires the pinned
shared device and inherited lease managed by `tools/lp_mixed2_fp4_budget.py`;
create a new independent allocation for a new study. Do not reopen the closed
published cohort. Each line is a bounded JSON request; EOF closes the session.
A solve request has `op: "solve"`, current `solve_id`, `generation: 0`, an explicit
`lane` (`native`, `fp4x2`, `fp4x4`) and final `tier`. The selected research
configuration uses `fixed_audit: true`, `audit_max: 200`, `window_max: 16` for
FP4 or 32 for native. Limits remain explicit; no runtime timing-based routing.
Every response records physical/logical work, windows, recovery, costs, original
endpoint and independent certificate. Inspect `certified`; a transport success
is not a solution certificate. Debug unguarded products are read-only diagnostics
and never enter the solver.

CPU-only reproduction of committed measurements requires no GPU or artifacts tree:

```sh
python3 tools/lp_mixed2_fp4_analysis.py verify
```

The portable evidence contains original response bytes and source identities.
Device conclusions remain scoped to the tested image, shapes and shared-device
conditions. The report preserves an unexplained development sanitizer exit and
small-problem regressions; this is a research implementation, not a public preset.
