# MIXED2 scenario reuse research executor

SPEC-0039 / ADR-0072. Bounded same-matrix, changing-RHS/objective scenario cache.
Original SPEC-0038 arithmetic and CUDA image remain unchanged. No public preset.

The active model plus three cached models each retain their original LP, initial
observation and independent CPU checker. `cache_model` accepts only bit-identical
dimensions, matrix, scaling and step shift. `select_model` uploads the new
objective and bounds to every prepared engine. Every solve resets FP64 state;
cached scenarios do not warm-start one another. A failed switch terminates the
service before any further certificate can be issued.

CPU model preparation overlaps independent checker startup. Original input
validation still precedes CUDA. All checkers are owned and reaped on failure or
normal destruction; certificates always refer to the selected original model.

Build with the repository's pinned Rust toolchain:

```sh
cargo build --release --locked --manifest-path research/lp-mixed2-reuse/Cargo.toml
bash tools/check_mixed2_reuse_cpu.sh
python3 tools/lp_mixed2_reuse_analysis.py verify
python3 tools/lp_mixed2_reuse_evidence.py portable
```

The two replay commands need no GPU or original `artifacts` directory. The CPU
check script also uses the repository's normal Rust/Python validation dependencies.
The unchanged image and original serial-checker binary are retained in the
portable development evidence. Device execution requires the existing pinned
shared lease and source-bound resource admission; these commands do not release
a new scientific run or retry an incomplete block.

See [SPEC-0039](../../docs/specifications/SPEC-0039-mixed2-reuse.md),
[ADR-0072](../../docs/decisions/ADR-0072-mixed2-reuse.md), and the
[measurement report](../../docs/benchmarks/lp-mixed2-reuse.md) for the prospective
sampling contract, complete-cost endpoint, reliability limitations and results.
