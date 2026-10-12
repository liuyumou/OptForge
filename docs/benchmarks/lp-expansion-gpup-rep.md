# GPUP-REP CPU representation and arithmetic validation

Status: accepted CPU contract and reproducible validation; no solver or GPU behavior
Owner: numerical backend
Introduced: GPUP-REP, 2026-10-12
Last reviewed commit: bootstrap
Implementation: validation tools only
Tests: independent oracle, integration suite and full pinned-native gate

## Result

GPUP-REP accepts the bounded CPU subset of SPEC-0020 under ADR-0034. It establishes
an exact finite-binary64 input codec, a correctly rounded binary64 reference, and a
separate correctly rounded 64-significand-bit expansion reference. It does not add
a runtime arithmetic implementation, device kernel, solver method or preset.

The deterministic exact-rational oracle contains 32852 codec cases, 1058 primitive
cases, 40 reductions, 40 comparisons and 80 projections. The integer candidate
agrees with every expected result. The 40 reductions include sum, dot product and
all three norms in both formats, including paths with 65536 represented terms.
Two FMA cases retain a finite maximum result although a separately rounded product
would overflow. Negative tests prove that fixture corruption and understated error
bounds are rejected.

The earlier design validator remains independently reproducible at 57429 finite
binary64 patterns, 50 correction maps and 353 proximal cases. Its role remains
design algebra; the new fixture owns arithmetic acceptance.

## Storage proof and canonicality

Normalize a finite nonzero binary64 input as `x = 2^e M 2^-53` with a signed
53-bit integer `M`. Nearest-even FP32 rounding of the normalized value gives `h`.
The exact residual remains on the `2^-53` lattice; rounding that residual gives
`l` on the same or a coarser lattice. Therefore

~~~text
q = M - integer_lattice(h) - integer_lattice(l)
~~~

is integral. Exhaustive reasoning over the two rounding cells bounds it to
`[-8,8]`; the fixture observes every value in that interval. The decoder sums
the integer lattices with the symbolic exponent and requires exact binary64 output.
It then re-encodes and compares the complete tuple, which refuses alternate scales,
tails, signed-zero tags and malformed FP32 components. Both matrix orientations
reference the same canonical coefficient bits through a permutation map.

Raw FP16 cannot retain `q*2^-53`, while scaled FP16, E4M3, E5M2 or INT8 can retain
the integer `q` under its declared weight. That fact establishes storage only.
Arbitrary arithmetic intermediates use the separate 64-bit-significand format.

## Rounding and error proof

For precision `p`, normal exponent minimum `emin` and exact real `x`, choose the
output unit

~~~text
u = 2^(max(floor(log2(abs(x)))-p+1, emin-p+1)).
~~~

Divide the exact numerator by the exact denominator in units of `u`, compare twice
the remainder with the denominator and break equality toward an even quotient.
A carry renormalizes the result. This proves an absolute error at most `u/2` for
every inexact finite result, including gradual-underflow results where `u` is the
minimum subnormal unit. Exact subnormals do not raise underflow; tiny inexact results
do. Overflow, invalid square root and division by zero are explicit flags, never LP
statuses.

Binary64 uses `p=53` and minimum unit exponent -1074. The accepted expansion uses
`p=64` and minimum unit exponent -1085. Its unsigned significand is split into
top 24, next 24 and low 16 bits. Each chunk is exactly convertible to FP32 and has
weights `2^-24`, `2^-48` and `2^-64` under one symbolic exponent. No inference is
made by adding nominal component widths; the integer reconstruction establishes
all 64 bits. A normal tuple must carry a 64-bit normalized significand; only the
minimum-unit subnormal lattice may use fewer bits, so shifted alternate tuples are
refused.

Division rounds the exact quotient from quotient and remainder. For square root,
an integer root gives the lower candidate and the oracle compares the exact input
with the square of the midpoint to choose the nearest result and even tie. Addition,
multiplication and FMA use exact integer intermediates. Sum and dot product align
complete represented terms into an exact exponent bin and round once. The 2-norm
rounds the square root of the exact sum of represented squares. Comparisons and box
projection compare exact represented dyadics, including tagged infinite bounds.

The error-free-transform literature cited by the architecture requires explicit
underflow and overlap preconditions. This contract therefore does not accept a
shortcut that silently loses a product residual or treats componentwise addition
as expansion addition. The exact CPU accumulator is the control for later bounded
windows and omitted-term error envelopes.

## Layout and bounded resources

The maximum admitted analysis shape is 65536 rows, 65536 columns and 8388608
nonzeros. Checked arithmetic produces this receipt:

| Allocation | Bytes |
| --- | ---: |
| Compact h/l/INT8/i16 payload plus bitmap | 93323264 |
| Decoded 24/24/16/i16 operator | 117440512 |
| Canonical sparse indices, offsets and transpose map | 68157456 |
| Five decoded live-vector groups | 13369344 |
| Two checkpoint copies | 3670016 |
| 67-limb per-output exact accumulator scratch | 35127296 |
| Resident total | 295960592 |
| Peak including original bits and preparation scratch | 532414480 |

Both totals fit the frozen 1 GiB resident and 2 GiB peak limits. The limits are
admission controls, not reservations. Original binary64 bits use 8 bytes/value;
compact exact input uses 11 bytes/value in separate arrays; decoded expansion uses
14; the existing aligned Parts3 ABI uses 16. Sparse indices, both orientations,
vectors, checkpoints and preparation peaks are counted rather than hidden.

The full-range product span plus the 65536-term carry allowance needs 4234 magnitude
bits, or 67 u64 limbs, in the exact expansion control. This is deliberately a costly
oracle. GPUP-EXEC must prove a smaller window or charge comparable scratch; this
report makes no performance prediction from the oracle.

## Evidence and limits

The deterministic validation seed is 17004. Fixture SHA-256 is
`0a7203554c7f15ccded04d5cac00504119851611205c4566969468848bd08760`;
its ordered codec-input SHA-256 is
`2e7bc3265f70452da9757cfec627ec1457365a9027f585a86cc205b400220e8f`.
Finite sampling does not enumerate every binary64 significand or prove a GPU
implementation. No generated-instruction audit, device differential, sanitizer,
kernel timing, persistent solver state, checkpoint format, convergence experiment
or new certification mechanism is claimed. GPUP-EXEC remains responsible for one
admitted implementation subset and its resource reservation. Original-model host
certification remains final authority.

Full pinned-native `bash tools/check.sh` passed with four build jobs and GPU
opt-in unset: Rust formatting, clippy, build, tests and documentation; dependency
policy; all 228 Python integration tests; committed-record replay; 123 documentation
pages; and smoke. The final gate log is
`/tmp/ai-optimizer-gpup-rep-check.log`. Final documentation and whitespace checks
cover the acceptance prose.

No GPU work ran. The campaign remains 16134 events with SHA-256
`60649d29992d21508e60aa60f3e334e9ac18fe3254525ec38cc0eef298e84823` and cumulative
consumption 17115.274617853 / 18002.574545061 seconds.
