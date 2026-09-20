# GPUP-5B: Exact Scaling and Component Sparse Products

Status: complete; all 840 attempts and acceptance gates verified, 2026-09-17.
Contract: [ADR-0021](../decisions/ADR-0021-exact-scaling-components.md),
[SPEC-0012](../specifications/SPEC-0012-mixed-precision-lp.md) and
[SPEC-0013](../specifications/SPEC-0013-lp-precision-experiments.md).
The earlier [FP32 diagnosis](lp-fp32-slowdown-diagnosis.md) is unchanged.
The companion [rounding analysis](lp-fp32-rounding-analysis.md) reproduces the
previous CPU findings before these GPU measurements. Deferred proposals remain
in the [candidate register](../plans/lp-precision-candidates.md).

## Findings

Removing the single-component coefficient approximation restores the FP64
control's certified coverage on this development corpus. Each new research mode
certifies 27/36 timing runs; ordinary scaled FP32 storage certifies 12/36.
Both the exact three-component and approximate two-component variants recover
coverage. This supports the diagnosed coefficient-error mechanism; it does not
establish that every historical failure was a rounding floor.

FP32 component cross-products do not improve the larger cases' certified latency.
Splitting both operands, recovering every multiplication residual and recombining
in FP64 costs more than native FP64 multiplication here. Exact input representation
is useful for accuracy, but does not itself imply acceleration. No supported
preset is selected. The remaining three unsuccessful instances are unsuccessful
with FP64 too; this investigation does not solve them by changing tolerances.

## Frozen protocol and implementation

The study-only precision-research feature provides an explicit exponent-scaling
host constructor, an isolated Rust executable, strict request/evidence version 1,
and lp_pdhg_research.cubin. Existing runtime selectors, schemas, FP64 code objects,
trajectory/replay fixtures and original-model host authority remain unchanged.
The code object is provisioned separately; ordinary builds need no CUDA toolkit.

Twelve configurations are frozen in benchmarks/configs/lp-research-v1.json:
existing tuned FP64, precision FP64, FP32 storage; research native FP64;
power-of-two FP64/exact-FP32 storage; factored FP64/exact-FP32 storage; and two/three
components with either reconstructed FP64 multiplication or FP32 cross-products.
All use resident allocation, necessary uploads, warp32-v1 reductions and separate
kernels. No scheduled correction, precision recovery or fallback is enabled in
the research modes. The shared FP64 controller, master state, vector updates,
bounds and objective stay FP64. All candidate/bound assessment uses the original
model and the existing host validator/certifier.

The twelve development instances, order seed 17001, solve seed 17, bootstrap seed
17002, 1e-9 accuracy targets, 50000-proposal full-solve cap, 200-update check interval,
10-second solve/process limit and 8-GiB host/device limits are unchanged.
Timing has three repetitions. The four existing profile instances have one profile
and seven 200-proposal repetitions; small-4 and irregular-2048 have Systems traces
for all twelve configurations. This totals 432 + 48 + 336 + 24 = 840 planned
attempts. Configurations are randomized within the existing instance/repetition
blocks. Validation and held-out partitions are untouched. Context creation,
preconditioning, splitting, transfers, certification and executable startup are
included in elapsed solve costs; profile phases are diagnostic subsets.

Power-of-two exponents minimize logarithmic distance to the existing diagonals.
The decision compares integer significand squares, avoiding platform logarithm
rounding. Scaling adjusts exponents and checks exact inverse reconstruction of
finite transformed matrix, bounds and objective data. Inexact/range-losing cases
are explicitly unsupported. Factored execution keeps the original coefficients
and applies inner/outer diagonal factors in FP64 in both orientations. Its
rounding order differs from precomputing the scaled matrix. Each formulation has
its own FP64 control and conservative original/represented operator bounds,
with the same downward-rounded 0.9/bound step restriction.

Components encode a normalized mantissa and an i32 exponent. Three FP32 components
retain all input significand bits, including FP64 subnormals; two intentionally
omit the third. Canonical matrix components are packed once, and transpose storage
is a permutation of those bytes. Vector operands are split per nonzero in the
sparse kernel; this prototype does not cache per-vector expansions. Two/three
components require four/nine FP32 multiplications **and** four/nine explicit FMA
residual recoveries per scalar product. Fixed FP64 compensated recombination,
exponent restoration and fixed FP64 sparse reduction follow. Implicit contraction
is disabled and gradual underflow is retained. Nonfinite or lost-nonzero products
are checked before projection. Faulted chunks retain previous validated state;
unknown physical device completion remains explicit.

For a normalized binary64 mantissa, successive nearest-even splits leave a final
residual on the 2^-53 grid, at most 16 such units in magnitude. It is exactly
representable as a third FP32 component. Normalization keeps nonzero component
products/residuals away from FP32 underflow (their least possible bit is 2^-106).
This is a representation/range argument, not a claim that FP64 recombination,
exponent restoration or the row reduction is exact. The explicit FMA construction
uses established [error-free transformation methods](https://www.tuhh.de/ti3/paper/rump/OgRuOi04a.pdf).

## Coverage and convergence

| Timing configuration | Certified / 36 | Remaining outcomes |
| --- | ---: | --- |
| Tuned FP64 | 27 | 9 work limits |
| Precision FP64 | 27 | 9 work limits |
| Scaled FP32 storage | 12 | 24 work limits |
| Research default FP64 | 27 | 9 work limits |
| Power-of-two FP64 / FP32, each | 27 | 9 work limits |
| Factored FP64 / FP32, each | 27 | 9 work limits |
| Two components, reconstructed / cross-products, each | 27 | 9 work limits |
| Three components, reconstructed / cross-products, each | 27 | 9 work limits |

All repetitions have consistent proposal counts. Scheduling-50x10, ta001 and
ta011 exhaust 50000 proposals in every configuration. Storage-FP32 additionally
exhausts work on scaling-64/256, irregular-2048, dense_block-1024 and scheduling-20x5.

| Instance | Tuned FP64 | Precision/research FP64, factored and components | Power-of-two | Storage FP32 |
| --- | ---: | ---: | ---: | ---: |
| scaling-64 | 3200 | 3600 | 4200 | 50000 |
| scaling-256 | 4600 | 6000 | 6800 | 50000 |
| irregular-2048 | 1400 | 1600 | 1600 | 50000 |
| dense_block-256 | 1200 | 1400 | 1600 | 1400 |
| dense_block-1024 | 1400 | 1800 | 1800 | 50000 |
| scheduling-20x5 | 13600 | 13400 | 16000 | 50000 |

Small-4/16 take 200 proposals in all configurations; irregular-256 takes 1200 with
tuned FP64 and 1400 otherwise. Existing tuned FP64 retains its previous step policy;
precision/research controls use the conservative operator restriction. Cross-family
iteration differences therefore do not isolate arithmetic alone.

The power-of-two FP64/FP32 pair and factored FP64/FP32 pair each have identical saved
primal/dual endpoints, statuses and proposal counts in all 36 timing runs. The
three-component reconstruction control matches research native FP64 in all 36;
each component reconstruction/cross-product pair also matches in all 36. These
are observed endpoint agreements on this corpus. They do not prove every
intermediate iterate agrees, or guarantee bitwise agreement on other inputs.

## Latency and execution costs

Paired certified solve medians, milliseconds (three repetitions each):

| Configuration | irregular-2048 | dense_block-1024 |
| --- | ---: | ---: |
| tuned-fp64 | 431.555 | 386.597 |
| precision-fp64 | 475.103 | 455.388 |
| storage-fp32 | uncertified | uncertified |
| research-default-fp64 | 512.601 | 437.555 |
| research-power2-fp64 | 604.000 | 508.641 |
| research-power2-fp32 | 590.094 | 492.871 |
| research-factored-fp64 | 525.124 | 451.263 |
| research-factored-fp32 | 508.829 | 471.496 |
| research-components2-fp64 | 532.719 | 464.029 |
| research-components3-fp64 | 533.197 | 454.616 |
| research-components2-fp32 | 550.328 | 471.749 |
| research-components3-fp32 | 566.092 | 497.887 |

Matched baseline/candidate median ratios with paired 95% bootstrap intervals
(10000 resamples, seed 17002; greater than one favors the candidate):

| Comparison | irregular-2048 | dense_block-1024 |
| --- | ---: | ---: |
| power2-fp64/power2-fp32 | 1.024 [1.011, 1.034] | 1.032 [0.938, 1.081] |
| factored-fp64/factored-fp32 | 1.032 [0.995, 1.046] | 0.957 [0.956, 1.023] |
| components2-fp64/components2-fp32 | 0.968 [0.961, 0.989] | 0.984 [0.937, 0.984] |
| components3-fp64/components3-fp32 | 0.942 [0.929, 0.965] | 0.913 [0.836, 0.954] |

All nine jointly certified instances and all paired comparisons are retained in
analysis.json. These two instances expose the larger sparse kernels; they are not
a post-hoc preset. Three timing repetitions are a small sample and intervals are
unadjusted across comparisons. Exact-FP32 storage has a small matched gain on
irregular-2048 with power-of-two scaling, but it does not repay that formulation's
additional setup against research default. Factored storage results are mixed.

Equal-work execution medians, microseconds per proposal (seven repetitions of
200 proposals; kernels, synchronization, dynamic uploads/readback, excluding setup
and host certification):

| Configuration | small-4 | irregular-256 | irregular-2048 | dense_block-1024 |
| --- | ---: | ---: | ---: | ---: |
| tuned-fp64 | 15.005 | 14.922 | 16.969 | 15.104 |
| precision-fp64 | 19.317 | 19.556 | 26.034 | 23.959 |
| storage-fp32 | 19.272 | 19.588 | 25.743 | 21.424 |
| research-default-fp64 | 16.001 | 19.403 | 21.978 | 19.861 |
| research-power2-fp64 | 16.137 | 19.439 | 21.888 | 19.873 |
| research-power2-fp32 | 15.640 | 19.372 | 21.714 | 20.654 |
| research-factored-fp64 | 19.164 | 19.451 | 26.037 | 23.885 |
| research-factored-fp32 | 19.212 | 19.441 | 25.763 | 24.777 |
| research-components2-fp64 | 19.234 | 19.412 | 30.080 | 24.049 |
| research-components3-fp64 | 19.231 | 19.476 | 30.332 | 24.182 |
| research-components2-fp32 | 19.323 | 27.593 | 40.397 | 36.354 |
| research-components3-fp32 | 23.410 | 35.782 | 59.169 | 52.940 |

Faster arithmetic is not established here. Three-component cross-products take
2.69x/2.67x research-native update time on irregular-2048/dense_block-1024, versus
1.38x/1.22x for loading the same expansion and reconstructing native FP64 operands.
Certified solve time increases by 10.4%/13.8% for cross-products versus research
native FP64. The remaining time is dominated by costs outside those sparse updates.
Existing tuned FP64 remains faster on both of these instances; comparisons across
the research executable and runtime CLI include their different setup/evidence
wrappers and conservative-step policies, not only a kernel substitution.

All 24 Systems traces decoded offline using the previously isolated libdw; no GPU
job was repeated for import. Each contains exactly 1200 launches. On irregular-2048,
the 400 sparse launches consume 1.362 ms for research native FP64, 2.524 ms for
three-component reconstruction, and 8.573 ms for three-component cross-products.
Total kernel busy time is 2.765/3.932/9.982 ms, respectively. The matching sparse
launch counts and unchanged vector kernels localize the extra device cost to the
component kernels. The source requires many FP64 compensated additions per product
in addition to splitting, four/nine multiplications and explicit FMA residuals.
This structural cost explains why merely replacing the scalar multiplication
does not exploit FP32 throughput; hardware-counter bottleneck attribution remains
unverified. Raw traces, decoder commands and final static disassembly are retained.

The single irregular-2048 profile illustrates the costs. Native research FP64
uses 1,174,416 device bytes; the two/three-component modes use approximately
1.468/1.761 MB, including both matrix orientations, indices, guards, scratch and
state. Coefficient payload alone is 8 bytes for FP64, 4 for exact FP32, 12 for
two components plus exponent and 16 for three. These expansions trade additional
traffic for preserved information. Exact FP32 storage after power-of-two scaling
uses approximately 0.881 MB; factored FP32 uses 0.914 MB, including scale buffers.

The irregular-2048 three-component cross-product profile packs in 8.731 ms and
executes 1,055,376,000 component multiplications plus the same number of FMA residual
recoveries across 1600 proposals. Kernel/synchronization time is 94.118 ms, versus
47.982 ms for reconstructed three-component FP64 and 34.248 ms for research native
FP64. The per-proposal schedule remains six launches. Packing is measured inside
invariant allocation/upload time and must not be added to that phase again.
Its uploads total 2,055,648 bytes and readbacks 2,621,440 bytes. Per-vector splitting
is charged in the sparse kernels; stored vector-tail diagnostics report normalized
omission in units of 2^-53. Matrix-tail diagnostics are in scaled coefficient units.

Power-of-two construction currently builds the ordinary preconditioner and then
an explicit scaled engine, including its norm estimate. On irregular-2048 its
preconditioning/preparation/allocation phases total about 95 ms versus 46 ms for
research default. Eliminating redundant setup is a future execution optimization,
not a reason to omit the measured cost. Context setup and host work also matter,
particularly on small instances. Hardware counters remain unavailable from the
prior diagnosis; Systems timing and static code inspection do not establish a
bandwidth/cache/occupancy bottleneck. Dense Tensor Core results do not establish
sparse single-vector performance on these matrices.

## Arithmetic, acceptance and provenance

The companion rounding note preserves all original hashes, seed, formulas,
166292-coefficient counts, 10006 sampled finite inputs and 45027 CPU product/error
pairs. tools/analyze_lp_rounding.py reproduces its machine-readable artifact.
Additional independent Fraction fixtures cover scalar products, cancellation,
32-lane reduction boundaries and transpose products; tools/lp_research_oracle.py
reproduces/checks them. Device tests compare nine modes against independent CPU
updates over controller boundaries, including full-exponent component products,
subnormals, overflow, lost nonzero products, memory admission and fault accounting.
Sampled agreement is not a proof of correct rounding for all component products.

The exact measured source passed the full pinned-native gate before measurement.
The final arithmetic implementation passed all 31 LP device cases; its four new
research cases passed memcheck, racecheck, initcheck and synccheck sequentially,
with zero errors and zero race warnings. End-to-end preflight checked all nine
research modes and the serialized execution accounting. Logs, including earlier
iterations and failures, are retained in artifacts/gpup5b-acceptance.
Independent analysis verifies all 840 endpoints and all historical indexed artifacts.
There are 451 certified endpoints and 389 work-limit endpoints across the full
schedule (including deliberately short runs); no missing endpoint, numerical
failure, fallback, timeout or unexpected process exit occurred. The 432 timing
runs contain 309 certified successes and 123 work limits. Fourteen acceptance
jobs retain every preliminary and final charge. The additional final CPU fixture
has zero-ULP disagreement for returned scalar products in its 39-case sample;
its eight sparse cases stay below 0.00719 of the documented independent error
allowance. This adds validation evidence, not a universal arithmetic guarantee.

Post-measurement changes add rational fixtures, reporting and stricter evidence
checks for altered execution settings, missing accounting and overflowing counts.
They do not change the measured kernels, executor arithmetic or controller. The
archived binaries/source remain the measurement identities. The full pinned-native gate passes 435 Rust tests, 126 Python integration tests,
83 documentation pages, formatting/clippy, dependency policy, committed replay and
smoke checks. The hardened reader independently revalidates all 630 research
endpoints. The other 210 endpoints use their unchanged existing verifier. Regular
device suites total 51 passing cases (31 LP, 14 CUDA and six scheduling), and all
four scoped sanitizers pass. Final logs and source/evidence hashes are retained in
artifacts/gpup5b-acceptance and the active-task record. A missing optional timing
utility prevented one CPU gate launcher from starting; the preserved launcher log
and successful bounded Python-supervised gate distinguish this from a test failure.
The initially slow debug compatibility audit was stopped and fully repeated with
an archived optimized verifier; this used no GPU work.

Frozen source, executables, code objects, protocol, requests, witnesses, telemetry,
worker outcomes, raw traces and the settled ledger snapshot live in
artifacts/gpup5b-v1. Read-only analysis independently revalidates every endpoint
with its archived executable. CPU analysis and final reporting do not rerun GPU
measurements. All GPU work uses the shared host lease and preserved screening
ledger. Preserve the 3288-event prefix and 1467.266874696 seconds; new work is
limited to 900 study plus 300 acceptance seconds, inside the unchanged cumulative
4502.574545061-second and campaign/phase caps. Actual study use is 697.211414922
seconds and acceptance use 70.875589353 seconds: 768.087004275 new screening
seconds, for 2235.353878971 cumulative seconds. All 854 new reservations are
settled. The ledger now contains 4996 events; its SHA-256 is
737e1301cb31cf5d0ad0585aa81a4dc0b814615d39e4974827e504e880b11e5f.
The prior prefix remains b3ca2739b1108a552b0423606ddd0cd94a8ed2323da1506098fa0150ba42bfef.
GPUP-5's separate historical acceptance remains 80.458622460 seconds; it is not
reset or charged again here. Four build jobs are used within the four-hour CPU
validation ceiling. No new GPU allowance is requested or inferred.

Measured source-tree SHA-256:
b22d72c709b98493861cfd17d642305592ac6b23e6e7dbce103e57d65bc54e40.
Source archive: bb0c249e0a848ec0808d0aab25052a72c0427a9aab7be0ac69e27a12641bac25.
Research executable: 39870cde8c249fb53da99b5272d471545f26de54b252d89f9837222467658ff5.
Research code object: 3116cc29ca171aa65f7331b45f39c92288085230e2ce36e0f5ddebb5e8c6a418.
The frozen runtime CLI hash is b52a4ebbf27f9b3985f4a4ee297c96b1e26bd96ea278a898caffee853961e387.
The RTX 5090 UUID is GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48, sm_120;
provisioning uses CUDA 13.0.88, disabled implicit contraction and enabled gradual
underflow. Execution metadata records driver, CPU affinity, compiler/library
identities and telemetry. No numerical result grants device mathematical authority.
