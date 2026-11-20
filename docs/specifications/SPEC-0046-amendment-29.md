# SPEC-0046 amendment 29: safe portable component encoding

Packing-quality-v4 reaches compilation and refuses the explicit AVX2 implementation
because the crate forbids unsafe Rust. Retain its compiler diagnostics, complete
sources, empty cleanup and full 1200 CPU / zero GPU-second charge. Do not relax
the unsafe-code lint or claim SIMD acceptance. The prior quality-v3 interruption
and independent cleanup disposition remain unchanged.

The still-unadmitted image-v7 now uses a safe, portable branchless component
encoder. Boolean comparisons at the original thresholds produce the exact E2M1
code, and integer binary64 bit construction replaces the decoder table. The
original FP64 multiplication, residual subtraction, scalar maximum reduction,
exponent selection and component order remain. There is no explicit target-feature
dispatch, unsafe code or measured SIMD instruction claim. The independent original
encoder and complete boundary/tail/residual tests remain mandatory.

Fresh packing-quality-v5 / build-packing-v5 must pass all 54 tests and complete
build acceptance before image-v7 sealing. The third CPU cohort remains wholly
unattempted, so its fresh source/library/executable freeze binds this corrected
implementation. Operational plans v15/v16 must bind this amendment as well as
the quality-v3 cleanup disposition and all preceding failures. Every allocation,
phase cap, original guard, certificate criterion and GPU admission requirement
remains unchanged. No attempted scientific cell or failed reservation is repeated.
