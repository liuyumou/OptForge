# GPUP-STATE: original admission refusal and compact FMA challenge

Status: original refusal retained; compact FMA passes scoped device validation; full controller remains gated
Owner: numerical backend and validation tooling
Introduced: GPUP-STATE, 2026-10-13
Last reviewed commit: bootstrap
Implementation: CPU mathematical validation, compile-only controls and isolated Rust/CUDA scalar diagnostics
Tests: independent CPU/device differentials, four scalar sanitizers, verified primitive timings, resource audit and native gate

## Result and limits

PR 19 review finds that the scalar resource obstacle is avoidable: a full-range
compact FMA uses **40 registers and zero stack/spills** in each expansion format,
under the same compiler options and 128-register/zero-spill limit. Independent
Fraction comparisons and host undefined-behavior checks pass. The compact scalar
implementation also passes all 6,170 independent cases on an RTX PRO 6000 Blackwell,
fresh-process repeatability and four scoped sanitizers. All 36 descriptive primitive
timing endpoints verify. The full controller remains unimplemented and unadmitted;
no solve-performance result follows.

The original direct exact-bin implementation still fails the resource gate:
both 48-bit compensated-pair and 64-bit expansion variants require **255 registers**,
a **152-byte stack**, **296 spill-store bytes** and **152 spill-load bytes**.
The limits are at most 128 registers/thread and zero compiler spills.
That original result is the user-approved admission-refusal path under
[ADR-0036](../decisions/ADR-0036-full-expansion-state-admission.md), not a solver
implementation or a mathematical impossibility result for expansion arithmetic.
The review's counterexample means that failure is no longer a sufficient resource
reason to stop full-range scalar FMA work. Remaining controller obligations,
including device division/root/transcendentals, complete state and error handling,
still need their own implementations and gates.

The smaller 320-bit restoring division/root construction fits at 62 registers;
an unprojected primal/Halpern update fits at 76. Both have zero stack/spills.
Every inspected path contains no native FP64 arithmetic or unaudited calls.
Those division/root and update controls remain compile-only: they were not
launched. Device correctness, sanitizer and timing evidence below applies only to
the compact scalar FMA and its chain/batch wrapper, with no checkpoint/replay pass.

| Planned comparison | Timing cells | Profiles | Admitted/executed |
| --- | ---: | ---: | ---: |
| Existing tuned FP64 | 24 | 3 | 0 |
| New matched FP64 | 24 | 3 | 0 |
| Compensated scaled pair | 24 | 3 | 0 |
| Expansion64 | 24 | 3 | 0 |

All eight inherited development models, original tolerances/seeds/deadlines and
the 96-timing/12-profile proposal remain documented inputs. No planned cell is
reported as a failed solve, a primary attempt, a timing, or evidence of residual
contraction. Full controller, pair codec, complete state/snapshots, solver publication
and runtime modules remain gated. Existing original-model certification remains
the authority and all runtime sources/legacy behavior remain unchanged.

## Numerical admission and why the widths differ

For an admitted 64-significand-bit operand, a product has magnitude below 2^128.
The bounded row's 128-bit base alignment and at most 2^16 terms give magnitude
below 2^272. This means **at most 272 magnitude bits**, not fewer than 272; the
signed 320-bit bin is still sufficient. A regression attains 272 bits using
65535 maximum products at the high base and one at the low base.
Canonical binary64 coefficients times expansion state need a smaller 261-bit
bound; accurate squares/norm reductions require the larger bound.

Full-range scalar FMA cannot inherit the row's exponent-window assumption.
For Expansion64, operand unit exponents span [-1085,960], product units span
[-2170,1920], and the addend spans [-1085,960]. Aligning a minimum product with
a maximum addend can require 64+(960+2170)=3194 magnitude bits. The opposite
ordering requires 128+(1920+1085)=3133. For the 48-bit pair the corresponding
maximum is 48+(976+2138)=3162. A signed 3200-bit integer bin retains the complete
sum and all tie/sticky information, followed by one nearest-even rounding.

The tested construction decodes finite dyadics and retains this bin in the
thread's working values. The compiler exceeds the register ceiling and spills.
The compact review construction below demonstrates that every aligned zero bit
need not be retained. It needs no explicit global scratch and preserves the full
scalar range. Its separately measured primitive costs appear below. Other scratch algorithms
retain their own proof and traffic/allocation gates. Narrowing scalar ranges or
returning to FP64 changes the requested numerical contract.

## PR 19 challenge and evidence repairs

The original experiment tested one direct full-bin construction. Its large
register footprint is a property of retaining thousands of aligned bits, rather
than evidence against the two numerical formats. The review adds a separately
identified construction and corpus under the bounded amendment to ADR-0036.
The original fixture, sources, image, resource receipts and failed attempts stay
byte-identical. No original result is relabeled as a device or performance pass.

The compact FMA aligns at `max(product_unit, addend_unit) - 160`. The exact
product has at most 128 bits and the addend at most 64; retained operands fit
288 bits and the sum fits 289, within the existing 320-bit container. At most one
operand loses a tail. A nonzero tail is represented by forcing its low bit odd.
When that approximation is inexact, the other operand is divisible by 2^160,
and the shifted operand is below 2^127. Even opposite signs leave a leading bit
of at least 159. Final rounding discards at least 96 bits at precision 64, so
all rounding boundaries are even integers in the intermediate grid. The odd
surrogate differs from the true sum by less than one grid unit and cannot cross
a boundary. Gradual underflow only increases the discarded width. Exact sums,
overflow boundaries, signed zeros and cancellation use the original rounding
contract. This proof applies to FMA's two terms, not arbitrary multi-term dots.

| Compile-only construction | Formats | Registers/thread | Stack | Spill stores/loads |
| --- | --- | ---: | ---: | ---: |
| Original 3200-bit exact bin | 48 and 64 bits | 255 | 152 B | 296 / 152 B |
| Compact 320-bit alignment with odd tail | 48 and 64 bits | 40 | 0 B | 0 / 0 B |

Both are compiled together with NVCC 13.0.88 for sm_120 using the original flags.
The integer/update controls retain 62/76 registers and zero spills. All eight
generated kernels are inspected with the corrected instruction parser; none has
native FP64 arithmetic or unaudited calls. Fewer registers establish admission
headroom, not faster execution, occupancy under a full controller, or a preset.

The new seed-17019 fixture contains 5,900 cases per construction: 992 alignment,
512 cancellation, 4,096 full-range seeded, 208 midpoint, 12 overflow, 48 underflow
and 32 signed-zero cases across both formats. Midpoints have positive/negative
perturbations; alignment cases straddle the 160-bit retention and 64/128-bit
shift cutoffs. Both constructions match all 11,800 supplementary comparisons
under ordinary host compilation and UBSan. They also match the original 270
FMA cases each, without changing that historical fixture. These finite tests
support the proof; none substitutes for a CPU/device differential.

Two evidence-verifier defects are corrected. Uniform predicates such as `@UP0`
were silently skipped, allowing a predicated FP64 instruction to evade the audit.
The parser now consumes every addressed instruction or refuses it, and covers
FP64 conversions, matrix instructions and calls. The archive verifier previously
reproduced the oracle fixture but did not execute the frozen log/exp candidate.
It now runs that candidate in isolated Python, checks all 48 results and requires
the complete frozen file inventory. Regression tests corrupt only the archived
candidate and inject forbidden/malformed instructions. Original resource counts
and numerical results reverify unchanged with these stronger checks.

The self-contained review freeze is
`artifacts/gpup-state-pr-review-20261013/compact-reviewed`, with a
[reviewed summary](data/state/fma-review-v1.json). Its receipt SHA-256 is
79a1b572f6cf73906d3e1632f8833c368dba7365d9e6fb8760e5e8f2c9fe0d44.
The earlier `compact-v1` freeze omitted verifier-only import dependencies; it is
retained as preliminary evidence. The reviewed freeze includes those dependencies
and host compiler logs, with unchanged kernel sources and test inputs. A source-only
isolated-archive regression checks that no checkout supplies missing imports.

~~~bash
python3 tools/lp_state_review.py
python3 -m unittest discover -s tests/integration -p 'test_lp_state*.py' -v
python3 tools/lp_state_review.py --output artifacts/gpup-state-pr-review-reproduction
python3 tools/lp_state_review.py --verify artifacts/gpup-state-pr-review-20261013/compact-reviewed/review.json
~~~

The review adds no GPU reservation, workload or ledger event. All 21 focused CPU
tests pass. Full pinned-native `CARGO_BUILD_JOBS=4 bash tools/check.sh` passes
280 Python tests, Rust/native/dependency checks, committed-record replay,
127 documentation pages and smoke. It uses 125.078377860 elapsed / 152.458983
CPU seconds and 1663545344 bytes maximum child RSS. Logs and resource receipts
are `native.log` and `native-resources.json` in the review artifact directory.
Native coverage is enabled, and no GPU workload runs.

## Scoped device validation and primitive costs

The original RTX 5090 cohort, gpup-state-device-v1, was refused by the quiet-device
admission check before child/context launch. It retains one blocked attempt and
41 unexecuted cells, with 3.002084480 seconds charged. Both RTX 5090s were busy;
the user explicitly requested another idle GPU. The separately frozen v2 cohort
uses **RTX PRO 6000 Blackwell Server Edition, sm_120, 188 multiprocessors**,
GPU-6721b13a-30f9-83ec-dace-ba2d9738556f. These are PRO 6000 measurements and
establish no equivalence with historical RTX 5090 timings. The shared host lease
remained in force; no project workload used two GPUs simultaneously.

V2 verifies all 42 endpoints: two ordinary fresh-process checks, four scoped
compute-sanitizer checks and 36 timing attempts. Each correctness process checks
all 6,170 cases (3,085 per precision), twice each at block sizes 64/128/256, plus
counts 0/1/31/32/33/127/128/129 and short odd/even benchmark chains. Overflow
refusals preserve initialized outputs; unused outputs and canaries remain exact.
All six 40-launch correctness endpoints have the same numerical SHA-256:
ab00b1babc428941e17fe073c2b0609e5cffc9c6666cb59c7a73ed95a23e4b1c.
Memcheck, racecheck, initcheck and synccheck pass for these paths. The compact
entry points use 40 registers and benchmark wrappers 48, with no stack/spills,
native FP64 arithmetic or unaudited calls. The generated dynamic loops and clock
reads remain present. No rejected full-bin kernel is launched.

The first memcheck classification incorrectly reported a missing receipt because
the verifier read stderr and this installation writes the summary to stdout.
Its raw zero-exit worker, zero-error summary, endpoint and failed classification
remain immutable. A separately hashed reviewed classification fixes only receipt
interpretation; **no attempt is repeated**. The continuation archive differs only
in the verifier, its source-only tests, ADR-0036 and active task. Every executable,
kernel, build, supervisor, corpus and protocol source matches the original freeze.
The repaired reader requires an exact zero-error/zero-hazard summary in either
captured stream. Its own exact-source full native gate passed before continuation.

The fixed timing roster is two precisions × three patterns × two shapes × three
fresh-process repetitions, with one checked warmup and one checked measured launch.
A chain is one thread performing 16,385 dependent FMAs. A batch is 65,536 threads
each performing 129 dependent FMAs (8,454,144 operations). Inputs are runtime values;
odd iteration counts produce endpoints different from the initial states. Every
warmup and measured result is checked against independent exact dyadic endpoints.
The table gives medians; the [full summary](data/state/device-v2.json) retains
all attempts and min/max values, without selecting a best repetition.

| Precision | Pattern | Chain launch (ms) | Cycles/FMA | Batch launch (ms) | Batch GFMA/s |
| --- | --- | ---: | ---: | ---: | ---: |
| 48 | increment | 71.307 | 10139.0 | 0.680 | 12.437 |
| 48 | far_tail | 55.769 | 7927.5 | 0.545 | 15.509 |
| 48 | cancellation | 55.903 | 7948.9 | 0.896 | 9.432 |
| 64 | increment | 82.461 | 11724.0 | 0.783 | 10.801 |
| 64 | far_tail | 68.075 | 9679.0 | 0.657 | 12.872 |
| 64 | cancellation | 62.061 | 8823.3 | 1.051 | 8.048 |

Cycles/FMA includes dependent-loop control and is not a native instruction latency.
Launch wall time includes host submission and synchronization. Batch GFMA/s divides
logical scalar operations by that wall time; it is not solver throughput. Median
context creation across cells ranges from 220.8 to 254.6 ms, module/stream setup
25.1–26.1 ms, allocation 0.184–0.202 ms, measured upload 0.031–0.966 ms and download
0.029–0.409 ms. Total process work is 410.7–503.2 ms, excluding final endpoint-file
serialization; charged lease time includes that output and supervision. The
maximum explicit device allocation is 4,980,812 bytes, below the 64 MiB limit.

The engineering conclusion is narrower than a speedup: full-range scalar FMA is
feasible under the register/spill gate, but these dependent patterns still cost
roughly 7,928–11,724 cycles per operation. Batch parallelism changes throughput
substantially. There is no executed FP64/full-bin comparator, full controller,
LP workload, worst-case latency sweep or hardware-clock control. Three repetitions
on one GPU are descriptive, not a general performance ranking. Successful scalar
admission does not close division/root/transcendental, state/replay or numerical
error-budget obligations for the full controller.

The [blocked v1 summary](data/state/device-v1.json) and v2 summary preserve all
planned outcomes. Raw source archives, binaries, images, endpoints, stream logs,
requests, worker receipts and immutable ledger snapshots remain under
artifacts/gpup-state-device-v1 and artifacts/gpup-state-device-v2. V2's original
source identity is fa77a3fcf7ead3179b368fec802d3e7d392422063e7fb8638d9dd0ece29b46f9;
freeze SHA-256 is 6bb24a27ab7265e161af22948087a6c522ee09898e6e83f2b128292744bb4671.
The verifier continuation source is
55b9d5592760156751ab4a0d44b2a3b2b717cf6bf35ca08bedce80e23b0d9741.
Full pinned-native acceptance passes with 289 Python tests; 30 focused state tests
cover the arithmetic and evidence readers. Preflight syntax/lint failures and all
historical freezes are retained. Ordinary Cargo builds still need no CUDA toolkit.

~~~bash
# Reverify retained outcomes without executing a GPU job.
python3 tools/lp_state_device.py report --cohort v1
python3 tools/lp_state_device.py report --cohort v2
python3 -m unittest discover -s tests/integration -p 'test_lp_state*.py' -v
CARGO_BUILD_JOBS=4 bash tools/check.sh
~~~

## Original transcendental admission

The CPU scalar candidate uses directed integer intervals at resolutions 128,
192 and 256 bits. Multiplication uses twice-width intermediates before directed
truncation. For log, normalize to m in [1,2), use z=(m-1)/(m+1) in [0,1/3), and
enclose the positive atanh tail by z^(2N+1)/((2N+1)*(1-z^2)). For exp, reduce to
2^q*exp(r), 0<=r<ln(2), and bound the Taylor tail by twice the next term after
N terms. Every endpoint operation rounds outward; an uncertain reduction or
rounding cell refines, then explicitly refuses at 256 bits.

The independent Fraction oracle uses the log(1+t) series with its geometric
remainder, and argument halving/Taylor/outward squaring for exp. Its absolute
squaring grid has 2048 bits to resolve subnormal outputs; working resolution and
actual intermediate size are recorded separately. Zero/domain, halfway-adjacent,
near-one, extreme exponent, tiny/large exp, cancellation and signed-zero cases
are included. Inexact results carry the half-output-unit error; exact log(1)
and exp(0) have exact outcomes. This does not prove LP convergence or replace
original-unit operator/state error admission.

## Reproducible evidence

The independent seed-17004 fixture contains **192** integer division/root cases,
**270** full-range FMA cases, **64** unprojected update graphs and **48** log/exp
cases. Integer/Fraction expected results share no candidate arithmetic. The
same scalar integer construction is compiled as a host validation executable
and checked before its CUDA resource compilation. The host check covers bits
and explicit overflow refusal, not a complete device error-envelope interface.
All 13 CPU admission tests pass, including corruption, malformed-input, fixture
reproduction and resource-evidence rejection tests. Initial full pinned-native acceptance
passes all Rust/native/dependency gates, 270 Python tests, committed-record replay,
127 documentation pages and smoke, with GPU opt-in unset and native coverage enabled.
Its first completed receipt records 128.209268496 elapsed seconds, 175.761509
CPU seconds and maximum child RSS 1663467520 bytes. Final logs/resources and all
failed launcher receipts are retained under the task artifacts.
Final source-only review additionally rejects duplicate/boolean evidence fields
before private file access and prevents an overlooked non-FMA kernel failure
from passing the aggregate gate. The frozen numerical construction and outcome
remain unchanged. Final exact-source acceptance passes 272 Python tests and
all Rust/native/dependency, committed-record replay, documentation and smoke
gates. Its receipts are native-reviewed.log and native-reviewed-resources.json
under the same artifact directory.

| Identity | SHA-256 |
| --- | --- |
| Fixture | 624048e320d5c4cca9a9b53fff236f5fb1220f4583e160e3489c1fd47829e822 |
| CUDA construction | ae7eedf7e53d2a6e5b5ec70333a7a1cd72146431dde9ca676f9e8236644eb3b7 |
| Host harness | 4c3fa1bb587819931d4739c22e0e452cafe37b545e83016e6f394572354d5ec2 |
| Host executable | d16036816b2dae3a7f42cdaadcaac7cea492dca7eb17f5e515121cee096db5c7 |
| Compile-only image | 14bdccf1e246b6966bafc4d33a3aa59925a50a567b643d31c58f1052e1781c8d |
| Frozen admission receipt | 0a0313286b831721d277fcdfbc3b012dfc7fd1940b9c8dcc3c2cd08b6c8977e2 |

NVCC is 13.0.88, architecture sm_120, C++17, -O3, -lineinfo, -fmad=false,
-ftz=false. Full source copies, host binary, cubin, compiler log, generated
instructions and resources are under artifacts/gpup-state-v1/admission-v1.
The verifier rederives resource/instruction receipts directly from the image,
checks all file/source/fixture hashes, reproduces the independent fixture and
reruns the frozen host executable. A zero LOCAL field cannot hide stack spills.
Reviewed metrics are in [the admission summary](data/state/admission-v1.json).

~~~bash
python3 tools/lp_state_admission.py
python3 -m unittest discover -s tests/integration -p 'test_lp_state.py' -v
python3 tools/lp_state_admission.py --output artifacts/gpup-state-v1/reproduction-1
python3 tools/lp_state_admission.py --verify artifacts/gpup-state-v1/admission-v1/admission.json
CARGO_BUILD_JOBS=4 bash tools/check.sh
~~~

Ordinary Cargo builds and tests do not invoke nvcc or load a device. The C++ host
harness is validation tooling, not runtime code or another unsafe/native boundary.
The first CPU oracle used a 512-bit absolute squaring grid, which could not
resolve a small exponential; its observed failure and correction are retained.
The first fixture-generation attempt used a wrong oracle operation spelling and
left a partial source freeze. Those failed attempts, preliminary compiler images
and the resource parser's initially permissive empty-opcode regression remain
under the task artifacts; none is promoted to accepted evidence.

## Accounting and handoff

The original CPU/compile-only investigation and review charged zero GPU seconds.
The device extension uses the existing GPUP-STATE authority: 1100 seconds total,
500 acceptance and 600 timing, within the original 3600/850/2300 allocation and
unchanged campaign/phase ceilings. V1 charged 3.002084480 seconds for refused
admission; v2 charged 27.111983793 seconds (5.458835182 acceptance and
21.653148611 timing). **Combined charge is 30.114068273 GPU seconds**, including
8.460919662 acceptance. No profiles or additional allowance were used.

Cumulative consumption is **17665.546083611 / 21602.574545061 seconds**. The
16452-event ledger SHA-256 is
24949150272600fe58364f25ebbf7bf892f7454da342edc268d50684568c5f18,
preserving the 16368-event v1 prefix
a97630527900a1a11cfd612bd3f96d55a86c211555bb0adc7de3ab52adebfc96 and original
16366-event prefix 4d083cdb06b4baa38452bb331541fa8874614aeb037f34e40001ce9692ede26b.
Independent verification replays every reservation/settlement and checks phase,
cohort and cumulative caps. All historical evidence and limitations remain.

GPUP-STATE retains the first-construction refusal and the compact scalar
counterexample, now with scoped device validation and descriptive measurements.
Full state/controller acceptance remains open. No preset or solver benefit is
selected. GPUP-REFINE is next, with native FP64 outer state first and its own
accepted SPEC-0021 subset and allocation. Unused state allowance does not reserve
that next task or authorize complete expansion-state implementation.
