# ADR-0034: Accept bounded CPU expansion arithmetic contracts

Status: accepted, 2026-10-12
Owner: numerical backend
Introduced: GPUP-REP
Last reviewed commit: bootstrap
Superseded by: none

## Context

ADR-0033 placed a CPU proof and representation review before more GPU arithmetic.
The draft SPEC-0020 separated exact input storage from arithmetic accuracy, but did
not select a first format, primitive semantics or resource envelope. Device work
could otherwise mistake a lossless input tuple for an accurate intermediate or
admit a layout whose decoded copies erase its storage benefit.

## Decision

Accept three versioned, CPU-only contracts as the reference for later research:

- `lp-binary64-rne-v1` rounds each named primitive directly to IEEE binary64 with
  nearest-even and gradual underflow. It is the strong trajectory reference.
- `lp-expansion-input-codec-v1` encodes each finite binary64 input as canonical
  FP32 `h/l`, signed integer tail `q` in `[-8,8]` with weight `2^-53`, and an i16
  symbolic exponent. Signed zero is tagged; nonfinite coefficients and alternate
  encodings are refused.
- `fp32-24-24-16-expansion-rne-v1` uses a signed 64-bit significand represented by
  positional 24/24/16-bit FP32 chunks and an i16 symbolic exponent. Its normal
  exponent range is -1022 through 1023 and gradual underflow reaches `2^-1085`.
  Every declared operation rounds nearest-even once at its output boundary and
  carries a conservative half-ulp absolute error bound when inexact.

The accepted primitive inventory is conversion, normalization, sign operations,
addition, subtraction, multiplication, fused multiply-add, division, square root,
comparison, exact-then-rounded sum and dot product, 1/2/infinity norms, and tagged
box projection. Division uses quotient/remainder decisions. Square root uses an
integer root and exact squared-midpoint comparison. Reductions accumulate exact
represented terms and round once; this is an oracle contract, not a claim that a
compact device accumulator already exists.

Accept `lp-expansion-layout-v1` for admission analysis through 65536 rows and
columns and `2^23` nonzeros, with 1 GiB resident and 2 GiB peak caps. One canonical
coefficient array and a permutation transpose map bind both orientations. Original
binary64 sources remain distinct from materialized scaled binary64 sources.

These identities are internal research contracts. They add no solver setting,
record enum, public ABI, kernel, preset or certification authority. GPUP-EXEC must
make a separate choice of which subset it can implement and reserve all device
work before changing behavior.

## Alternatives

- Accept only the compact codec. This leaves arithmetic and long-cancellation
  behavior unresolved and is insufficient for an executor contract.
- Accept only binary64 reference semantics. This supplies an oracle but no distinct
  wider-significand candidate to test without native FP64 instructions.
- Reuse the input `h/l/q` tuple for intermediates. Its small tail proof applies to
  binary64 inputs, not products, quotients or arbitrary expansion state.
- Accept an unscaled FP32 pair. Existing evidence records product underflow and
  roughly 48 significant bits, so it cannot satisfy this contract.

## Consequences

The accepted expansion payload is 14 bytes in separate arrays and a conventional
aligned host structure is 16 bytes. It is larger than original eight-byte storage;
its possible value is arithmetic, range and deferred reconstruction rather than a
bandwidth claim. The compact exact input payload is 11 bytes before sparse indices.

Correct rounding is a semantic target, not a GPU feasibility result. The exact
accumulator used by the CPU oracle needs 67 u64 magnitude limbs for the admitted
full-range 65536-term dot-product bound. Device implementation, instruction audit,
state persistence, snapshots, solver convergence and performance remain unaccepted.
Final successful solves and published bounds still require the existing independent
original-model host authority.

## Implementation and tests

The integer-only candidate is in `tools/lp_expansion_candidate.py`; the independent
Fraction oracle and deterministic fixture generator are in
`tools/lp_expansion_oracle.py`. The committed fixture covers every binary64 exponent
and sign, codec ties/carries, arithmetic boundaries, error flags and long reductions.
`tests/integration/test_lp_expansion.py` checks reproduction, deliberate fixture
corruption, malformed encodings, layout limits, transpose identity, generations,
aliasing and cancellation. The [GPUP-REP report](../benchmarks/lp-expansion-gpup-rep.md)
records proofs, counts, hashes and remaining limits. Full pinned-native acceptance
is required before the task is complete.
