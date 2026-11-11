# Exact independent checker acceleration

Separate research executor under SPEC-0032. It reuses the admitted FP4-ACCEL
GPU image, model transformation, controller and device code. Public solver/checker
defaults and all historical sources remain unchanged.

The checker caches original variable lookup indices and coefficient decompositions,
parallelizes independent feasibility rows on larger dense inputs, and reuses dual
reduction scratch without changing the original tree or outward arithmetic.
The exact-product predicate uses integer representability, including subnormals.
The original serial certificate and complete feasibility reports are the authority.

Build/test: `cargo test --release --offline --manifest-path research/lp-fp4-checker/Cargo.toml`.
Use the repository's documented resource supervisor for numerical studies.
The binary accepts the previous `serve`, `once`, `check`, `check-serial` and
`check-service` protocols. `check-serial` retains original serial certification.
`profile MODEL ENDPOINT TIER COUNT OUTPUT` interleaves baseline and optimized
CPU checking and rejects any receipt difference. `GPUP_CHECKER_ORIGINAL` is a
CPU development switch; formal controls use the exact archived original binary.

The allocation and immutable attempts live under `artifacts/gpup-fp4-checker-v1`.
See SPEC-0032 and the measured checker report for coverage, costs and limitations.

[Measured report](../../docs/benchmarks/lp-fp4-checker.md).
