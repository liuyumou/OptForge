# GPUP-STATE: full expansion controller admission refusal

Status: complete bounded CPU/resource admission refusal; full pinned-native acceptance passed
Owner: numerical backend and validation tooling
Introduced: GPUP-STATE, 2026-10-13
Last reviewed commit: bootstrap
Implementation: CPU mathematical validation and compile-only diagnostics
Tests: independent fixture, CPU integer/Fraction differentials, resource audit and native gate

## Result and limits

The requested full expansion controller is unadmitted. Its first direct exact-bin
implementation of full-range scalar FMA fails the accepted device resource gate:
both 48-bit compensated-pair and 64-bit expansion variants require **255 registers**,
a **152-byte stack**, **296 spill-store bytes** and **152 spill-load bytes**.
The limits are at most 128 registers/thread and zero compiler spills.
This is the user-approved admission-refusal path under
[ADR-0036](../decisions/ADR-0036-full-expansion-state-admission.md), not a solver
implementation or a mathematical impossibility result for expansion arithmetic.

The smaller 320-bit restoring division/root construction fits at 62 registers;
an unprojected primal/Halpern update fits at 76. Both have zero stack/spills.
Every inspected path contains no native FP64 arithmetic or unaudited calls.
These are compile-only resource results. No CUDA context or device workload ran,
so no device correctness, sanitizer, checkpoint/replay or performance pass is claimed.

| Planned comparison | Timing cells | Profiles | Admitted/executed |
| --- | ---: | ---: | ---: |
| Existing tuned FP64 | 24 | 3 | 0 |
| New matched FP64 | 24 | 3 | 0 |
| Compensated scaled pair | 24 | 3 | 0 |
| Expansion64 | 24 | 3 | 0 |

All eight inherited development models, original tolerances/seeds/deadlines and
the 96-timing/12-profile proposal remain documented inputs. No planned cell is
reported as a failed solve, a primary attempt, a timing, or evidence of residual
contraction. Full controller, pair codec, complete state/snapshots, publication
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
Rejecting it does not establish that a guard/sticky algorithm or explicit global
scratch would fail. Those alternatives can avoid retaining every aligned zero
bit, but require their own proofs, range/rounding tests and accounting of traffic,
allocations and launches. Narrowing scalar ranges or returning to FP64 changes
the requested numerical contract; neither is silently substituted.

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
remain unchanged. Final exact-source acceptance is in native-reviewed.log and
native-reviewed-resources.json under the same artifact directory.

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

The user allocated 3600 GPU seconds inside existing authority, split 2300 timing,
450 profiles and 850 acceptance. **Actual GPU charge is zero.** No GPU reservation
or ledger event was appended. Cumulative consumption remains
17635.432015338 / 21602.574545061 seconds, with exactly 16366 events and SHA-256
4d083cdb06b4baa38452bb331541fa8874614aeb037f34e40001ce9692ede26b.
Every prior phase ceiling/prefix and historical limitation remains. Compiling and
inspecting a code object is provisioning/CPU work, not executing a project GPU job.

GPUP-STATE completes as this demonstrated admission refusal with the full
pinned-native gate passed. No preset or accuracy/performance benefit is selected.
GPUP-REFINE is next, with native FP64 outer state first and its own accepted
SPEC-0021 subset and allocation. The unused state allocation does not reserve
that next task or authorize any alternative expansion implementation.
