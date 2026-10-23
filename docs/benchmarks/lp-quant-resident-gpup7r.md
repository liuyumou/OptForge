# Resident matrix quantization: GPUP-7R

Status: complete bounded research evaluation, 2026-10-23, under accepted
[ADR-0041](../decisions/ADR-0041-resident-matrix-quantization.md).
Implementation: isolated lp-quant-resident-v1 host/CUDA executor and
lp_precision_quant_resident solve/verify/replay; historical interfaces remain exact.
Acceptance: [receipts](data/quant-resident/acceptance.json),
[results](data/quant-resident/report.json), [frozen protocol](../../benchmarks/configs/lp-quant-resident-v1.json).

Residency removes the previous new executor's timeout behavior on this cohort.
All **36 admitted fresh timings certify**, with **36/108 planned timing coverage**;
the 72 quantized timing cells and six quantized profiles are CPU-refused without
replacement. All three FP64 profiles finish exactly 2000 logical updates. All
21 independent-product endpoints verify. No quantized solve benefit or supported
preset follows. Unchanged tuned FP64 remains fastest on every nontrivial model.

The comparison freezes six format/policy candidates, resident matched FP64, a
resident tuned-operator FP64 policy bridge and unchanged tuned FP64. There are
120 planned study jobs: 108 timings, nine profiles and three microprofile jobs.
Forty-two execute; 78 remain explicit CPU refusals. Seeds 17/17001/17002,
10/10/10/30-second timing deadlines, 30-second profile deadlines, 50000 charged
updates and the original-model 1e-9 certification settings remain unchanged.

## Numerical admission

The [independent integer/Fraction proof](data/quant-resident/oracle.json) checks
162015 encoding/adjacent-rounding cases, 116960 coefficient-error components,
79120 original-unit product-error components and 1204 actual outward programs.
It covers scaling extremes, cancellation, subnormals, both orientations, native
operands and the segmented/bridge trees. The tighter detailed program passes
4198 output decisions whose new coarse envelope fails. The image has at most
64 registers and zero spills. PTX has no arithmetic contraction or FTZ; correctly
rounded division lowers to local FMA sequences, and integer truncation's F2I.FTZ
instruction maps subnormals to integer zero as required. Full instruction receipts
preserve these distinctions.

The [accepted eight-model CPU cohort](data/quant-resident/cpu-admission.json)
contains 72 independently verified trajectories, after two preserved earlier
cohorts. All numerical/work outcomes remain identical across the three cohorts;
metadata and invalid-window handling are separately source-bound. None of the
48 quantized model/configuration cells completes a full accepted 32-update window
with nonzero low products in both orientations. Small-4 has zero useful low work;
other cells recover through sticky native promotion. Recovery does not establish
quantized convergence. Twenty-three of 24 FP64 control cells pass CPU admission;
the tuned-operator bridge on scaling-256 retains its numerical refusal. All three
controls qualify on the four timing models. Historical scaling refusals remain.

The interface retains FP64 state/updates, canonical 32-by-32 coefficient groups,
direct binary64 conversion, maximum-based power-of-two scales, 1e-7 original-unit
product/audit budgets, common conservative norm/step, uniform/selective sticky
promotion, the 25% coefficient/eight-transition limits and original-model host
authority. Compact oriented sparse segments share coefficient IDs/scales/masks.
Device guards use a global-vector envelope, then coefficient-weighted detailed
bounds. No guard or budget is skipped in a solve. Checkpoints bind the complete
controller, operator generation, promotion and originating session. Started work,
audits, rejected/replayed work, predicated submissions and deadlines never roll
back. Reference endpoints are adopted after each audit; every 200-update
restart/weight/assessment boundary is retained.

## Fresh-process comparison

Median seconds over three repetitions, including input, packing/metadata,
context/allocation/uploads, guards, state updates, synchronization, audits,
promotion/replay when present, final certification and process output:

| Model | Resident matched FP64 | Resident bridge FP64 | Unchanged tuned FP64 |
| --- | ---: | ---: | ---: |
| small-4 | 0.298493 | 0.298534 | 0.407329 |
| scheduling-20x5 | 2.548714 | 2.675941 | 0.558577 |
| irregular-2048 | 0.706590 | 0.736473 | 0.452326 |
| irregular-32768 | 4.799867 | 4.890638 | 2.564014 |

New small-4 controls certify the initial host point without an update; ordinary
tuned FP64 first assesses after 200 updates. This is no arithmetic speed claim.
On scheduling, resident controls require 28600 logical updates versus 13600 for
tuned FP64; on both irregular models they require 2000 versus 1400. The policy
bridge retains the common conservative step, guards and audits while replacing
the segmented product tree with the tuned warp32 operator. Its scheduling median
is about 5% slower than resident matched FP64. The new controls' remaining cost
therefore includes policy/preparation and extra updates; sparse precision alone
cannot explain the gap. Three paired repetitions and bootstrap intervals are in
the machine report; they support only these frozen cells. Historical matched
FP64 timings are censored, so no paired historical speedup ratio is reported.

On irregular-32768, resident matched fresh medians include 1.709335 seconds of
host preparation and 2.789883 seconds in the inclusive solve phase; context
creation is 0.262399 seconds and in-loop original-model assessments total
1.013348 seconds. Context/assessments are included within the solve phase, so
these numbers must not be added. Execute-to-return is 4.582754 seconds; the
worker's 4.799867-second full process cost also includes surrounding I/O/output.
All costs remain in the endpoint phase maps. Final original-model assessment
remains fresh, including after the last diagnostic update.

## Fixed-work diagnostics

All profiles are separate fresh processes and pass independent final verification.
Early host certification is recorded but never truncates the logical horizon.
They share preparation through the research wrapper; the tuned control's primary
fresh timing above still uses the unchanged ordinary CLI.

| Profile on irregular-32768 | Logical / physical updates | Recorded first certificate | Inclusive solve phase (s) |
| --- | ---: | ---: | ---: |
| Resident matched FP64 | 2000 / 2070 | 2000 | 2.873392 |
| Resident bridge FP64 | 2000 / 2070 | 2000 | 2.910734 |
| Tuned FP64 research profile | 2000 / 2000 | 1400 | 2.053350 |

The new controls perform 70 complete device windows and 70 host audits. They
have zero host per-product scans and zero full-vector per-product transfers;
state uploads occur once per window. All native coefficients are active, with
zero low work and zero promotion/replay. The matched profile executes 2357928000
native coefficient products; the bridge records 4715856000, including 2357928000
duplicate guard products. These counters must not be interpreted as additional
useful logical work. Its final native coefficient fraction is 100% in both.

The matched profile's exclusive preparation scopes include 0.809057 seconds for
inherited quantization/metadata plus 0.090741 seconds for resident packing. Host
reference-update arithmetic takes 0.582560 seconds; device-to-host scopes take
0.249672 seconds. Asynchronous execution and synchronization overlap: these
scopes are attribution evidence, not isolated kernel-duration measurements.

## Operator diagnostics and accuracy limits

Three 30-second jobs each cover all six candidates and matched FP64, using the
same frozen synthetic and recorded primal/dual vectors and 16 independent
products per vector. The [CPU witness](data/quant-resident/micro-admission.json)
recomputes complete outputs/bounds/flags and matches every available device hash.
Both synthetic orientations admit all 32768 outputs in every configuration.
On recorded primal input, FP16 admits 20 outputs and E4M3/E5M2 admit 16; recorded
dual input admits none. There are no range refusals in these frozen vectors.
The historical coarse guard admits zero recorded outputs for the quantized
formats. Tighter bounds help individual outputs but do not admit a whole useful
trajectory window. Matched native FP64 admits every recorded output.

Milliseconds per product on synthetic primal/dual inputs, averaging the two
16-product batch durations. These are single diagnostic observations, including
launch/submission/synchronization overhead, with preparation/context excluded:

| Uniform format | Fused guarded | Product only | Guard only |
| --- | ---: | ---: | ---: |
| FP16 | 0.11871 | 0.04603 | 0.11847 |
| E4M3 | 0.11861 | 0.04568 | 0.11895 |
| E5M2 | 0.11951 | 0.04639 | 0.11871 |
| Matched FP64 | 0.06305 | 0.03961 | 0.06304 |

Selective twins have identical numerical digests and are retained separately.
Quantized products are slower here even with guards disabled. Guard-only work
still reads/computes products for range checks and overlaps the fused kernel;
its duration cannot be added to product-only time or treated as a disjoint
breakdown. Recorded guarded quantized products are refused arithmetic, never
accepted throughput. Unguarded diagnostics cannot certify a product or LP.
No Tensor Cores, vector quantization, stochastic rounding, refinement, assessment
policy combination, sessions or supported preset is admitted by this result.

## Acceptance, preservation and accounting

Full pinned-native acceptance passes 338 Python tests, Rust/native/dependency
checks, historical record replay, 137 documentation pages and smoke, without GPU
work. All 66 ordinary device tests, three inherited quantization tests, three new
resident tests, 628 product/bound vectors, six CPU/device controller comparisons,
29 fixed-work endpoints and 29 bitwise same-device replays pass. The additional
244-vector smoke and all four scoped sanitizers pass; the sanitizer filter covers
resident products, FP64 updates and controller windows.

The initial invalid project command failed its interpreter validator before any
reservation/request/device admission. Its log remains, and the ledger proves the
corrected command was the first project attempt. Before sanitizers, a separate
[source bridge](data/quant-resident/acceptance-source-bridge.json) broadens their
filter, retains the completed ordinary/project cohort and binds unchanged runtime,
executable and image bodies. No GPU identity is retried. Both native source gates,
source archives, binaries/images, frozen requests and all historical artifacts
remain. CPU-only delivery review strengthens archive/binary receipt binding and physical
launch/transfer consistency checks. Portable tests use a retained verified small
endpoint instead of ignored local campaign files; no GPU work is added.

Fresh verification accepts **313 LP endpoints**: 39 study, 58 acceptance/replay
and 216 across the three CPU cohorts. It also verifies all **21 operator
endpoints**. No failed/interrupted profile enters discovery or timing coverage.
The [acceptance receipt](data/quant-resident/acceptance.json) binds every source,
executable, image and CPU/RSS bound. Measured major CPU jobs plus conservative
preparation/final-acceptance allowances remain below 21600 CPU seconds; observed
process-tree RSS is at most 3234975744 bytes, below 8 GiB. Maximum new study device
buffers are 57675062 bytes, below 1 GiB; checked preparation admission retains
its 2 GiB limit. New artifacts are approximately 2.12 GB, below 32 GiB.

| Charged category | Actual GPU seconds | Task cap |
| --- | ---: | ---: |
| Screening timings | 69.376705845 | 2300 |
| Ablation profiles/diagnostics | 69.783306098 | 450 |
| Repeatability acceptance | 106.526574880 | 850 |
| Total | 245.686586823 | 3600 |

All jobs use GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48 under the shared lease and
activity admission, without substitution. Cumulative charge is
**21359.585855789 / 25202.574545061 seconds** within every phase ceiling and the
independent 28800-second cap. Additional authority is zero. The **17132-event**
ledger SHA-256 is
`930de6771ab9bfbcb855bd05a07a58f6700aa1ade36bca09346790a94e7ff035`,
preserving the exact 17036-event prefix
`861c90d8d82a20ff9655173742db37a5047d315e8cc4c983e0d6b2e6fa09bb97`
and all earlier history. Unused allowance reserves no later task. GPUP-8 requires
its own conditional numerical/hardware/resource disposition before behavior.
