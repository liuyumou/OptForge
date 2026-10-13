# SPEC-0020: Exact compact LP storage and expansion arithmetic

Status: accepted for GPUP-REP CPU reference, GPUP-EXEC bounded exact dots and GPUP-STATE admission refusal; full expansion state remains draft
Scope: research-only representations and arithmetic, not solver convergence
Owner: numerical backend
Introduced: GPUP-DESIGN, 2026-10-12
Last reviewed commit: dd57e4c71ce4eec311c58042222f92fc54af24a6
Supersedes: none; accepted SPEC-0012 modes and research identities remain unchanged
Implementation: CPU reference tools; feature-gated optimizer-lp/optimizer-lp-cuda exec modules and isolated study executable
Tests: independent CPU oracles, native gates, GPUP-EXEC device differentials/replay/four sanitizers

## Purpose

Define the obligations needed to store original binary64 data and carry accurate
state using lower-precision components. Avoid equating a lossless codec with
correct arithmetic. Motivation and alternatives are in the
[architecture plan](../plans/lp-precision-architecture-2026-10-12.md).
The unaccepted portions reserve no CLI options, record enums, public ABI or GPU allowance.

## Accepted GPUP-REP CPU subset

[ADR-0034](../decisions/ADR-0034-lp-expansion-cpu-contract.md) accepts requirements 1-12, 14 and 17-23 as CPU reference and admission
contracts only. Requirements 13 and 16 are accepted only to the extent exercised
by the preparation generation, complete primitive inventory and explicit research
identities below; persistent solver state, snapshots and replay remain draft.
Requirement 15 and every device clause remain pending actual target code.

The accepted identities are `lp-expansion-input-codec-v1`,
`lp-binary64-rne-v1`, `fp32-24-24-16-expansion-rne-v1`,
`lp-expansion-operator-v1` and `lp-expansion-layout-v1`. Binary64 reference
operations round directly to binary64. Expansion operations use a signed 64-bit
significand, positional 24/24/16-bit FP32 chunks, symbolic i16 exponent, normal
range -1022 through 1023 and gradual underflow through `2^-1085`. Conversion,
sign operations, add/subtract/multiply/FMA, division, square root, comparison,
exact-then-rounded sum/dot, 1/2/infinity norms and tagged box projection are
accepted. Every inexact finite result carries the conservative half-ulp absolute
bound for its actual output unit.

Reductions use an exact exponent-bin accumulator and round once. That establishes
the oracle semantics and a costly correctness control, not an implementation choice
for GPUP-EXEC. The bounded layout admits at most 65536 rows and columns and `2^23`
nonzeros under 1 GiB resident and 2 GiB peak caps. Original binary64 coefficients
and already-rounded materialized scaled coefficients have distinct preparation
provenance. One canonical coefficient array supplies both orientations through a
permutation map; overlap and stale generations are refused.

Signed zero, underflow, overflow, division by zero, invalid square root, malformed
encoding, unsupported shape, checked-size failure, memory refusal, aliasing, stale
generation and cancellation have explicit outcomes. They are never infeasibility,
unboundedness or proof. Original-model host certification remains authoritative.
Negation flips a zero sign and absolute value clears it. Multiplication and division
XOR operand signs. Square root preserves its zero sign. Exact addition/subtraction
of like signed zeros preserves the effective sign; every other exact cancellation,
including nonzero FMA cancellation and reductions, produces positive zero under
nearest-even. FMA whose exact product and addend are both negative zero preserves
negative zero. An overflowing rounded square root or 2-norm returns the explicit
overflow/inexact outcome; an underflowed zero has the canonical zero exponent.
The `lp-binary64-rne-v1` operation contract uses the `ieee-binary64-rne-v1`
format identifier in the oracle fixture.

Bit patterns, codec fields, positional chunks, dimensions, permutation indices and
generations are strictly typed integers; booleans and numerically equal floats are
not alternate encodings. The expansion encoder and decoder enforce the same range.
Projection accepts only finite values/endpoints or the declared infinite-bound tag,
including when an unbounded or clipping branch would otherwise hide an exception.
Preparation admits shape and memory before traversing coefficients or transpose
indices. Its generation binds dimensions, canonical coefficient bits, the transpose
permutation, source kind, scale policy and layout identity. Apply validation requires
the current source-vector generation, so omission cannot bypass stale-vector refusal.
These are CPU metadata receipts: complete CSR connectivity, concrete scale values
and device preparation remain obligations of the later executor contract.


## Terminology and exact codec derivation

An expansion denotes a real sum of weighted components, not their rounded native
sum. RN32 means IEEE round-to-nearest, ties-to-even with gradual underflow. For a
finite nonzero binary64 x, choose integer e and binary64 m such that

~~~text
x = 2^e * m, 0.5 <= abs(m) < 1, -1073 <= e <= 1024
h = RN32(m)
l = RN32(m - h)
q = (m - h - l) * 2^53
x = 2^e * (h + l + q * 2^-53)
~~~

All differences in this definition are exact real differences. After normalization,
m is on the 2^-53 lattice. The first residual has magnitude at most 2^-25. At that
boundary it is exactly representable in FP32; otherwise its exponent is at most
-26, and rounding it to FP32 introduces error at most 2^-50. Both rounded terms
remain on the 2^-53 lattice: a smaller residual is already exactly representable,
and rounding larger residuals rounds to an equal or coarser lattice. Consequently
q is an integer in [-8,8]. Negative inputs follow by sign symmetry. This sharp
bound uses this normalization and these two RN operations; the older study's
more conservative bound is not rewritten.

FP16 cannot hold every raw residual q*2^-53: its least positive subnormal is
2^-24. It can hold q exactly if the implicit scale is retained. E4M3, E5M2 and
INT8 also hold every integer in [-8,8] exactly; BF16 can hold the raw normalized
residual. Tail format names alone do not convey its weight. The exponent above
covers binary64 subnormals as well as normals. Zero has a separate sign-preserving
encoding. Infinite variable/row bounds remain tagged bounds, never finite tuples;
NaNs and infinite matrix/objective coefficients remain invalid model input.

An integer decoding path can keep the original eight-byte bits. With sign s,
exponent field E and fraction field F, use

~~~text
normal:    M = 2^52 + F;                 e = E - 1022
subnormal: k = 53 - bit_length(F);
           M = F << k;                  e = -1021 - k
x = s * M * 2^(e-53)
~~~

Split M into integer chunks of at most 24 bits for exact integer-to-FP32
conversion. An unsigned-chunk expansion is a different layout from the canonical
RN h/l/q tuple: conversion to that tuple needs explicit tie/carry handling. Neither
path needs a native FP64 instruction merely to load/decode a stored coefficient.
Do not materialize 2^e before multiplying: e=1024 would overflow needlessly.

This proof concerns encoded binary64 inputs or values explicitly rounded to
binary64. Arbitrary three-component intermediates are not subject to the small
q bound. Exact multiplication may create a 106-bit significand before rounding.

## Requirements

1. A mode MUST identify storage, exponent/tail weights, arithmetic semantics,
   reduction order, range policy and controller precision independently.
2. A lossless codec MUST round-trip every admitted finite binary64 bit pattern,
   including signed zero and subnormals, without relying on a native FP64 sum.
3. The codec MUST reject malformed/noncanonical tuples or canonicalize them by an
   explicitly versioned rule before they enter arithmetic.
4. The codec MUST preserve original coefficient identity across both matrix
   orientations through one canonical coefficient array and an index map.
5. A compact format MUST account for exponent/tail metadata, tags, exceptions,
   alignment, both sparse views, resident decoded copies and peak scratch bytes.
6. A shared-exponent mode MUST admit each block against a range/exactness bound
   and retain exact exceptions or refuse the block; no coefficient may be pruned.
7. A mode claiming binary64-equivalent primitive results MUST implement the named
   rounding rule and all admitted finite-range outcomes, with independent oracle
   checks including halfway cases. Storage equivalence alone is insufficient.
8. A bounded-error arithmetic mode MUST specify an absolute error bound for every
   primitive and reduction in represented units, then propagate it through scales
   into original model units before algorithmic admission.
9. TwoSum, FastTwoSum and FMA residual algorithms MUST only be used under their
   proved ordering, rounding, range and underflow assumptions.
10. Products and reductions MUST retain discarded components or conservatively
    bound their total effect; silently dropping cross-products is forbidden.
11. An implementation MUST keep exponents symbolic or use checked exact scaling
    wherever intermediate range would be narrower than the represented value.
12. A mode MUST declare overflow, subnormal, signed-zero and nonfinite behavior
    for each operation; flush-to-zero cannot be assumed harmless.
13. A persistent-state mode MUST cover every live primal, dual, extrapolated,
    averaged and restart state, update compensation, scale, anchor, controller
    scalar and reduction input in its operation inventory.
14. Comparisons, division, square root, norm, projection and stopping indicators
    MUST have explicit semantics; implementing only add/multiply is insufficient.
15. A no-native-FP64 inner-path claim MUST be checked against generated instructions
    and all reachable inner-path code, including conversions and guard logic.
16. Every arithmetic/executor change MUST carry a new explicit research identity
    and a fixed same-device reduction order with checkpoint/replay semantics.
17. A kernel MUST reject invalid dimensions, aliasing, layout/architecture or
    scratch admission before launch, with checked integer sizing and indexing.
18. Range, error-bound or budget failure MUST terminate or enter a predeclared,
    recorded and charged recovery path; silent native FP64 fallback is forbidden.
19. Cancellation and failure MUST preserve an observable status and complete
    charged work; partial expansion state cannot be published as a certificate.
20. The mode MUST preserve independent original-model host certification for
    published bounds and successful solve claims under current accepted authority.
21. Legacy modes, kernels, replay identities and defaults MUST remain unchanged.
22. Before device implementation, a slice MUST accept its exact format/primitive
    subset, numerical limits, interfaces, oracle plan and CPU/GPU/memory caps.
23. A preparation receipt MUST distinguish original-coefficient exactness from
    exact storage of already-rounded scaled values, charging any prior scaling
    error to the original-unit operator-error budget.

## Interfaces and layouts

Proposed internal concepts, not a public Rust API:

| Interface | Input / output and units |
| --- | --- |
| encode_finite / decode_bits | Binary64 bits to canonical tuple and back; exact equality of bits, no tolerance. Bounds use a separate finite/infinite tag. |
| prepare_operator | Validated original model, admitted scaling, layout and memory cap to immutable canonical storage, transpose map, exactness/range receipt and byte counts. |
| prepare_vector | One logical vector plus arithmetic/scales to decoded components once per use epoch; receipts bind dimension and source generation. |
| apply / apply_transpose | Canonical operator and vector to specified expansion result plus a conservative absolute error envelope; in-place overlap is either disallowed or explicitly supported. |
| state_update / scalar_ops | Named operation, operands and rounding/error policy to normalized output, exception status and propagated error. |
| snapshot / restore | All logical arithmetic and method state plus versioned identities; no raw host pointers, device handles or padding bytes. |

Initial layout candidates are original bits (8 bytes), h/l/scaled-FP16/i16 (12),
h/l/BF16/i16 (12), and separate h/l/INT8/i16 arrays (11 bytes per element before
alignment). The existing h/l/tail/i32 struct is 16 bytes. No packed unaligned
struct loads are presumed legal or fast. Five-bit tail packing, shared exponents
and lossless data-dependent compression are later alternatives, not prerequisites.
Native bit storage plus on-use integer decoding is the bandwidth control.

Matrix input, decoded working storage and state are separate allocations in the
accounting. Storing a second decoded matrix can erase an apparent compact-storage
saving; a once-per-vector split can nevertheless save substantial repeated work.
Exact scaling receipts must cover range changes and the original-to-scaled map.
Both orientations reference identical represented coefficients, including outliers.
Encoding a rounded preconditioned matrix exactly cannot recover bits lost before
encoding. A model-exact path stores original coefficients with exact power-of-two
or symbolic scaling; a non-dyadic materialized scaling needs its own error bound.
The same distinction applies to scaled objectives, bounds and residual data.

## Arithmetic design and state invariants

GPUP-REP compares two semantic targets before committing to a device primitive set:

- **Binary64-rounded reference semantics:** round each declared primitive to the
  finite binary64 result under ties-to-even, then encode it exactly. A CPU integer
  or rational oracle establishes expected results independently of production
  routines. This is a strong reference; no low-cost GPU implementation is assumed.
- **Bounded expansion semantics:** use normalized FP32 expansions with an explicit
  exponent, retained error/guard information and proved operation-wise bounds.
  A possible master target is at least 64 effective significant bits, giving
  margin beyond 53; allocating nominal 24+24+16 component bits does not prove that
  effective precision. The accepted subset must give actual bounds. It need not
  reproduce every binary64-rounded trajectory, and has a different identity.

A scaled two-component mode is a useful approximate control for the underflow
failure, not a lossless binary64 substitute. No effective precision is inferred
simply by adding component widths. For each primitive, the accepted record must
specify normalization invariant, rounding points, intermediate width, absolute
error function, range preconditions, scratch, aliases and deterministic order.
Division and square root need residual bounds or a correctly rounded algorithm;
an unanalysed Newton iteration is not a contract.

Reduction planning must consider worst-case cancellation and row length, not only
a relative error on nonzero outputs. Test long rows, alternating signs, nearly
annihilating products and opposing extreme exponents. Componentwise addition is
not expansion addition. A software rounded result must specify halfway ties and
how sticky bits or equivalent error bounds decide the final rounding.

The whole-controller candidate includes norm estimation, step acceptance, primal
weights, restarts, proximal decisions and compensation. A hybrid controller with
host FP64 scalars is permitted only as a distinctly labeled candidate. Device
FP64-free operation does not imply FP64-free host preparation or certification.

## Proposed primitive and kernel construction

This is the concrete starting design for GPUP-REP/EXEC, subject to the error and
resource proofs above. Keep an exact slow CPU oracle separate from the fast path.

1. **Decode/normalize:** obtain the integer significand and symbolic exponent;
   form canonical h/l/q or a separately named chunk layout with integer masks,
   ties-to-even carries and exact casts of integers of at most 24 bits. Decode
   matrix values per admitted storage policy and vector values once per epoch.
   Compare decoding from two u32 words with u64 operations on the actual target;
   avoiding FP64 does not make wide integer instructions or conversion free.
2. **Products:** on normalized components use p=RN32(a*b) and
   r=FMA32(a,b,-p). Under the proved range/rounding assumptions, p+r equals the
   exact component product. For the exact binary64-input h/l/q codec, component
   bits are on the 2^-53 lattice and normalized products on the 2^-106 lattice,
   avoiding the original unscaled product-range failure. This argument does not
   automatically extend to arbitrary intermediate expansions or reduction sums.
3. **Accumulate:** attach exponent e_a+e_b to each product/residual and combine
   compatible exponent bins with TwoSum and deterministic carry/renormalization.
   TwoSum is s=RN(a+b), z=RN(s-a),
   t=RN(RN(a-RN(s-z))+RN(b-z)); its operation order and assumptions are part of the
   primitive. FastTwoSum is allowed only when its magnitude ordering is proved.
   One output owns a fixed reduction tree. Normalize and round once at the
   declared output boundary, instead of reconstructing native FP64 per nonzero.
4. **Bound omitted work:** the complete three-by-three component product is the
   correctness control. A cheaper cross-product subset must sum conservative
   bounds on every omitted term over the entire row and combine those with
   rounding/anchor/state bounds. A tiny term is not discardable just because a
   larger term precedes it; cancellation can reveal it later.
5. **Handle exponent spread:** start with an integer-bin exact CPU accumulator
   and a bounded exponent-window fast candidate. For full-range binary64 inputs,
   exact products can span from 2^-2148 to below 2^2048. An exact fixed-point row
   accumulator may need about 4196+ceil(log2(row_length)) magnitude bits plus sign/
   guard storage. This is a costly oracle/control, not a compact GPU default.
   A narrower window needs a rigorous absolute discarded-tail bound or a named
   range refusal; register spills or full-range scratch can reject the candidate.
6. **State addition and projection:** add the complete weighted update to the
   master with renormalization; do not add component arrays independently.
   Compare expansion-minus-bound using its certified sign/error interval. If a
   fast comparison is uncertain, refine or use the declared accurate path.
   Store projection/compensation outcomes consistently across snapshots.
7. **Division/control functions:** normalize the divisor, seed a reciprocal in
   FP32, then apply expansion Newton corrections r <- r+r*(1-a*r). Use a
   conservatively evaluated residual to bound reciprocal error before using it;
   doubling nominal precision is not a rounding proof. For square root split the
   exponent into an even part and a remainder, iterate on the safe mantissa,
   and bound error from a-z*z and a positive denominator bound. Correctly rounded
   semantics additionally require the result interval to lie in one rounding
   cell, otherwise extra work or an exact fallback is necessary. Record its cost.
8. **Boundary publication:** explicitly round/reconstruct a host candidate only
   when the method requests an assessment/publication. Bind any conversion error
   and run the existing certifier. Keeping expansions inside iterations does not
   require serializing every component at every step; evidence still contains a
   complete endpoint and all policy/state needed by its replay contract.

An initial bounded implementation should choose one decoded layout, one reduction
family and one arithmetic target. Additional formats share the same oracle and
compare at identical represented operands before algorithm changes. The prototype
may lose because nine component products, bin carries, normalization or scratch
traffic dominate; that is a planned rejection outcome. Tensor Core products are
not substituted into this construction until their accumulation error and actual
shape/layout semantics have their own accepted bound.

## Errors, recovery and resources

Proposed error categories are malformed encoding, unsupported range/layout/device,
insufficient error budget, memory admission, primitive exception, cancellation and
work/time limit. A category is not a solver status of infeasible or unbounded.
A future accepted interface will map these to the existing research refusal and
activity records without widening mathematical authority.

Before launch, calculate resident and peak preparation bytes from nnz, rows,
columns, component counts, index widths and checkpoint copies using checked
arithmetic. Freeze per-slice byte/register/scratch caps and maximum rows/nonzeros;
do not claim universal large-model coverage. Kernels remain inside the authorized
CUDA boundary, under the shared host lease, with no runtime toolkit dependency.
The documentation/CPU example task has zero GPU allowance. Every later kernel,
profile, sanitizer and failed attempt needs its own admitted reservation.

## Compatibility and examples

Do not extend old record meanings or overload old precision settings. A new
version binds layouts, operator hash, scale policy, operation/reduction identity,
code image and complete state. Packing is counted inside fresh-solve latency.
A later conversion from expansion state to a binary64 candidate is an explicit,
charged publication step; conversion error can affect final feasibility.

~~~text
m = 0x1.23456789abcdep-1
h = 0x1.2345680000000p-1
l = -0x1.d950c80000000p-27
q = -2
raw tail = -2^-52; casting it directly to FP16 gives signed zero.
Scaled INT8/FP16/FP8 q retains it exactly with weight 2^-53.
~~~

Reproduce supporting examples without a GPU:

~~~bash
python3 tools/check_lp_precision_design.py --check docs/plans/data/lp-precision-design-examples.json
~~~

## Acceptance tests

| Requirements | Required assertion / gate |
| --- | --- |
| 1-4, 23 | Original-versus-rounded-scaled operator fixtures; written lattice/range proof; independent integer codec round trips across every exponent, sign, tie/carry boundaries, subnormals, signed zero and deterministic sampled fractions; noncanonical input refusals and transpose identity. Exhaustive coverage of a finite sample is not exhaustive binary64 coverage. |
| 5-6, 17, 22 | Actual ABI/array byte counts, metadata/exception break-even analysis, integer-overflow and alias tests; accepted bounded allocation/launch contract. |
| 7-12, 14 | Independent rational/integer expected results for cancellation, 106-bit products, halfway rounding, subnormal/overflow, norms/division/sqrt and long reductions; proof review for each claimed error bound. |
| 13, 16, 18-19 | Whole-state round trip and replay; forced range/error failures, cancellation and charged recovery; no lost compensation/scales/anchors or stale decoded vectors. |
| 15 | Generated instruction inventory and reachable-path inspection on actual target; kernel timing is a secondary diagnostic. |
| 20-21 | Original certifier regressions including exact-rational cases, old identity/replay controls and full pinned-native acceptance. |
| All device behavior | CPU/device differentials, repeatability, memcheck/racecheck/initcheck/synccheck scoped to each new kernel family and recorded unsupported cases. |

The earlier CPU design artifact demonstrates the codec formula and selected LP
identities. GPUP-REP adds the independently generated arithmetic fixture and integer
candidate for the accepted CPU subset. Neither artifact passes future device gates.

## Remaining acceptance blockers

GPUP-EXEC closes only the bounded exact-dot device gates described below.
Persistent complete solver state, snapshots, division/sqrt on a device, shared
exponents and full FP64-free control remain independently gated. No convergence or
latency result follows from the accepted CPU semantics.


## Accepted GPUP-EXEC subset (2026-10-13)

[ADR-0035](../decisions/ADR-0035-bounded-exact-executor.md) accepts `lp-exec-v1`:
binary64 exact-dot rounding within a 128-bit product-exponent window and 65536-term
rows using a signed 256-bit accumulator. Both matrix orientations use canonical
coefficients and a validated permutation. Experimental prepare_operator,
prepare_vector, apply and apply_transpose interfaces bind scale/connectivity and
source generations, return explicit error/exception receipts and reject aliases,
stale vectors, nonfinite operands, invalid resources and unsupported ranges.
This extends the earlier CPU-only acceptance with the bounded device contract;
implementation and measured acceptance are recorded in the
[GPUP-EXEC report](../benchmarks/lp-exact-executor-gpup-exec.md).
FP64 state/control, independent host authority and historical identities remain.
The ADR freezes the task and amended campaign resource authority. It does not
accept full expansion state, device division/sqrt, refinement or a preset.

The study retains all 108 frozen attempts, independently verifies 94 endpoints,
and certifies 58/96 timings. All 27 cached/uncached study pairs agree bitwise;
regular device, oracle, replay and all four scoped sanitizer gates pass. Fourteen
initial controls lack endpoints after a discovery-image packaging failure; the
unchanged dependency was restored without retrying those attempts. Scheduling,
scaling and mixed cases hit the explicit exponent-window refusal. The measured
subset does not establish a fresh-solve speedup or a supported preset. Persistent
expansion state and the remaining device primitives retain their separate gates.

## GPUP-STATE CPU admission and resource refusal (2026-10-13)

[ADR-0036](../decisions/ADR-0036-full-expansion-state-admission.md) accepts a
bounded admission investigation, with its [report](../benchmarks/lp-expansion-state-gpup-state.md).
The requested full expansion controller is **not implemented or accepted**.
Requirements 13/16, complete persistent state, snapshots/replay and the remaining
device clauses still require their independent gates. The 96 timing/12 profile
grid was not admitted and yields no solve, residual or latency evidence.

24. A CPU transcendental validator MUST use directed enclosures and publish a
    nearest-even result only when both endpoints round to the same result;
    unresolved cells MUST refuse after 128/192/256 working bits.
25. CPU working precision MUST distinguish endpoint resolution from intermediate
    integer width, including twice-width multiplication before truncation.
26. A full primitive family MUST satisfy the actual generated register, stack and
    spill gates; a zero `LOCAL` field alone MUST NOT establish zero spills.
27. A partial primitive resource pass MUST NOT be promoted to full controller,
    device correctness, replay or comparative-study acceptance.
28. An admission refusal MUST retain exact source/fixture/executable/image
    identities and classify all planned but unexecuted work as unadmitted.

The validation target `fp32-24-24-pair-rne-v1` has 48 output significand bits,
normal exponents [-1022,1023], minimum unit 2^-1069 and a half-output-unit absolute
error for inexact finite results. It uses the accepted generic CPU rounding
semantics; this does not accept a pair storage ABI or solver controller. Existing
Expansion64 reference semantics remain. Log/exp inputs are explicitly finite
integer dyadics of at most 64 magnitude bits and unit exponent [-1085,1023].
These are scalar mathematical inputs, not a native FP64 controller interface.
Infinity/invalid encodings, boolean/non-integer fields and unsupported ranges
refuse before shifts. Log requires positive input; exp has explicit overflow and
tiny-inexact outcomes. Exact log(1) and exp(0) are handled directly.

The integer candidate uses 2*atanh range reduction for log and exp remainder
in [0,ln(2)) with a positive Taylor enclosure. Endpoints are fixed-point integers;
the independent Fraction oracle instead uses log(1+t), argument halving and
outward squaring. The 48-case fixture checks results and error flags in three
output formats; this is finite supporting evidence for the written bounds, not
exhaustive transcendental coverage. Stable proximal tests cover exact dyadic
boundaries and tagged infinities; unsupported materialized endpoints refuse.

The 320-bit reduction has magnitude below 2^272 for 65536 64-by-64-bit terms in
a 128-bit base-exponent window. Full-range scalar FMA is a separate gate: the
first exact-bin construction needs 3200 signed bits and fails at 255 registers
and nonzero compiler spills in both expansion formats. Its CPU bits match 270
independent FMA cases, but this is not a device differential. No kernel executes,
no host authority changes and no new runtime identity becomes selectable.

PR 19's user-authorized CPU/compile-only review accepts a compact FMA validation
construction under the bounded amendment to ADR-0036. Exact product/addend
alignment retains 160 low guard positions beneath the higher unit exponent;
an inexact shifted tail is made odd. The written rounding proof and 5,900 new
independent cases per construction preserve the entire scalar exponent range,
nearest-even results and signed-zero/overflow/underflow behavior. Each compact
variant compiles to 40 registers and zero stack/spills under the unchanged gate.
The original 255-register refusal remains historical evidence; it no longer
establishes a resource obstacle for full-range scalar FMA. This accepts no full
primitive family, error-envelope ABI, controller, device execution or performance
claim. Every addressed instruction MUST be parsed or refused, and archive
verification MUST execute its frozen transcendental candidate against the
independently reproduced fixture, not only reproduce the oracle's expectations.
