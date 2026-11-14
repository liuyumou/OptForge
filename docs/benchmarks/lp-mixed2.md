# GPUP-MIXED2 CPU contract and complete-cost admission

MIXED2 completes its bounded CPU admission with **device work deferred**. The
FP32-matrix/FP64-compute reference and local error/recovery contract are implemented
under [SPEC-0036](../specifications/SPEC-0036-mixed2.md) and
[ADR-0069](../decisions/ADR-0069-mixed2.md). There is no new GPU solver, certified
mixed solve, public preset or measured mixed-precision speedup.

## Complete-cost decision

The [machine record](data/mixed2-cost-v1.json) retains 768 selected native cells
and 1536 solves: all twelve families and 32 blocks of strict DELIVERY4 cold
and DELIVERY3 prepared candidate controls. The 1408 retained certificates and
128 intentional refusals are historical native outcomes, not MIXED2 results.
All 145 frozen scenarios per lifecycle remain visible. No scientific cell was rerun.
The original retention decisions are unchanged.

| Lifecycle | Ideal removal of every GPU event | Hypothetical 2x every GPU event | Disposition |
| --- | --- | --- | --- |
| cold | 1.010266x [1.010135, 1.010467] | 1.005106x [1.005041, 1.005206] | Insufficient upper bound |
| prepared | 1.357697x [1.330899, 1.616584] | 1.151630x [1.141940, 1.224749] | Attribution and added costs unknown |

Ratios are medians of block geometric ratios for dense128/256/512. Brackets
are simultaneous binomial median intervals for **assumed transformed retained
costs**, not uncertainty intervals for a measured new candidate. The 1.10x
benefit, eleven family guards per lifecycle and original 1e-9 coverage rules
were fixed before this analysis; all 24 metrics use ranks 7 and 26 of 32.
Block independence and shared-device limitations from the original studies remain.
Each solve is transformed before taking the three-solve prepared session median.
All GPU event time includes non-matrix work, so these are optimistic upper cases.

Even an ideal arithmetic replacement cannot justify cold execution under the
declared benefit rule. Prepared execution remains plausible only conditionally:
the actual matrix fraction, achievable speed, work amplification and additional
representation/transfer/guard/correction/fallback/checking costs are unknown.
No assumption of zero overhead establishes their safety. A separately funded
matrix-attribution and overhead pilot is required before a solver/device cohort.

| Prepared family | Median complete delivery (ms) | Median GPU events (ms) | Median extra-cost allowance at 2x events (ms) |
| --- | ---: | ---: | ---: |
| dense-generic-128 | 10.775 | 2.910 | 0.473 |
| dense-generic-256 | 14.352 | 3.731 | 0.559 |
| dense-generic-512 | 21.038 | 5.418 | 0.792 |

Allowances are computed per solve as T/1.10 - (T - G + G/2), then summarized;
they are illustrative individual-family thresholds, not replacements for the
frozen joint target and family guards. Marginal phase medians are not additive.
Prepared setup/teardown is retained separately for every family in the machine
summary; it cannot be silently amortized into a cold-latency claim.

The retained DELIVERY4 diagnosis remains relevant: dense512 warm host
preparation 110.9 to 53.2 ms and hashing 61.3 to 9.8 ms; profiled context
setup about 222 ms (113 driver initialization, 107 context creation), owned
destruction about 74 ms including 69 ms context destruction. Another 37–38 ms
outside Rust main remains unassigned. These are prior observations from
[DELIVERY4](lp-delivery4.md), not new MIXED2 measurements.

## Numerical implementation and limits

The [architecture note](../architecture/lp-mixed2.md) derives the local product
enclosure and explains the isolated CSR representation, FP64 FMA, shared
transpose coefficients, identity scaling and independent original-model authority.
The CPU reference refuses invalid shapes, nonfinite inputs, FP32 range loss
and nonfinite arithmetic/enclosures. It preserves original coefficient bits.
The window reference restores opaque checkpoint bytes, charges attempted work,
requires positive work and primal/dual progress, and promotes permanently to native.

Eleven Rust tests and ten Python contracts pass. The independent exact-rational
oracle checks 1049 requests and 5121 outputs, separating representation and
FMA rounding errors across generic significands, cancellation, subnormals,
extreme exponents and both directions. Final source-bound oracle evidence is in
[CPU acceptance](data/mixed2-cpu-v2.json). A development review corrected
physical accounting for refused calls after native promotion and bounded sparse
dimensions before transpose-output allocation; development versions and
the earlier passing oracle receipt remain archived. No failed numerical job occurred.

These tests do not establish a useful mixed solver window, a complete executor
checkpoint, global trajectory error, convergence or an original-model certificate.
The conservative progress rule can promote if one residual is already zero.
There is no GPU subnormal/FTZ admission or sanitizer reuse claim. The prior
[refinement](lp-refinement-gpup-refine.md) and
[resident quantization](lp-quant-resident-gpup7r.md) failures remain design
inputs: zero work and zero useful mixed windows cannot qualify a future solver.

## Reproduction, acceptance and resources

`python3 tools/lp_mixed2_cost.py --verify` reproduces every selected sample and
scenario from committed portable archives. A clean temporary copy containing
only tools, the specification and bound input/output records verifies without
the original artifacts tree, CUDA or the reference executable. The isolated
Rust package builds without a toolkit; `tools/check_mixed2_cpu.sh` runs its
CPU gate and rational oracle with a fresh exclusive output receipt.

Full native gate, exact history and final cleanup: [acceptance](data/mixed2-acceptance-v1.json).
Separate phase charges, all source versions and raw supervisor receipts:
[accounting](data/mixed2-accounting-v1.json). The independent ceiling is 16000
CPU / zero GPU seconds, four slots and 16 GiB sampled RSS. It includes 512
preparation and 128 closing-administration CPU seconds; no historical transfers.
The unchanged supervisor is used for every numerical/analysis/acceptance job.

The next ready task is GPUP-8-DISPOSITION, a review requiring a separate request.
Readiness is not execution or funding. GPUP-8 remains incomplete, TENSOR2
conditional and GPUP-9 gated. No follow-on allocation, public default, push or
publication follows; the delivery is committed locally.

Final software acceptance: 638 repository Rust tests, 688 Python tests, 11 isolated Rust tests, full native/replay/artifact/docs/smoke checks. 1838 historical files remain exact; prior handoff/changelog/known-limitations text is preserved.

Allocation closed at **2050.255325136 / 16000 CPU seconds**, **zero GPU**, including closing administration. Failed jobs: 0; all cleanup empty.
