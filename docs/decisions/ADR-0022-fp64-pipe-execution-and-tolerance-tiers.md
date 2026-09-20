# ADR-0022: FP64-Pipe Execution, Tolerance Tiers and Corpus Extension

Status: accepted by the maintainer's explicit implementation request, 2026-09-19.
Scope: GPUP-5C, a bounded research slice before GPUP-6.

## Decision

The [root-cause note](../benchmarks/lp-fp64-pipe-root-cause.md) attributes the
GPUP-5B component slowdown to the FP64 pipe of the sm_120 device, not to Tensor
Cores or memory bandwidth: FP64 arithmetic, double compares and 64-bit conversions
issue at one sixty-fourth of the FP32 rate, and the component kernels recombine
every FP32 partial on that pipe. The current twelve development instances are
launch-bound. This slice acts on that diagnosis without changing any existing
runtime selector, default, code object, schema, seed, split, threshold or archived
evidence.

Add three feature-gated research modes to the isolated research executor and its
separately provisioned code object, each with a CPU oracle branch: `intguard-fp64`
keeps the six-kernel schedule and FP64 arithmetic but performs range guards as
integer bit tests; `fused-fp64` keeps that arithmetic and guard semantics but
fuses each sparse product with its vector update and store into one launch, two
per proposal, as the existing tuned fusion already does; `doublefloat-fp32`
stores each coefficient and each product operand as an unevaluated FP32 pair
(hi + lo, 48 significant bits), multiplies with one FP32 multiply and three FMAs,
accumulates with FP32 error-free sums, and never touches the FP64 pipe inside the
sparse loop. The double-float operand vectors are split by the fused update
kernels once per proposal. All three keep the shared FP64 controller, master
state, vector-update arithmetic, bounds, objective, six guard slots, strict
nonzero-to-zero and nonfinite guards, disabled contraction, gradual underflow and
original-model host certification. The nine GPUP-5B modes and their code paths
remain byte-identical; no new driver-API symbol, CUDA graph or cooperative launch
is added. Component cross-products are not measured again.

Research requests and evidence gain schema version 2. Version 2 records the
launch count per proposal and the fused execution setting; version 1 remains
valid only for the nine existing modes. The original 1e-9 absolute/relative
targets stay the default everywhere. This slice additionally measures explicit
per-configuration tolerance tiers 1e-6 and 1e-4 recorded in each request; a tier
never changes the certification arithmetic, only the caller's recorded targets, as
[SPEC-0013](../specifications/SPEC-0013-lp-precision-experiments.md) requirement 5
requires. The 1e-4 tier mirrors published PDLP defaults; the project's per-row
relative allowance remains stricter than norm-relative feasibility.

Extend the development corpus with a separate frozen manifest under a versioned
manifest schema: larger instances of existing families up to 65536 rows and one
new `mixed` family with equality rows, one-sided rows, free variables and
coefficients that are exact in FP64 but inexact in FP32, all with constructed
witnesses. Existing manifests, generator output, validation and held-out
partitions are byte-identical. Extension instances carry their own solve limit.

## Frozen experiment and resources

Configurations on the twelve development instances, three timing repetitions:
`tuned-fp64`, `storage-fp32`, `accumulation-fp32`, `research-default-fp64` and
`research-doublefloat-fp32` at tiers 1e-9, 1e-6 and 1e-4; `research-intguard-fp64`
and `research-fused-fp64` at 1e-9. Extension instances, three repetitions and a
30-second limit: irregular-32768 and mixed-65536 with `tuned-fp64`,
`research-default-fp64`, `research-fused-fp64` and `research-doublefloat-fp32` at
1e-9 and 1e-4; irregular-65536 and dense_block-65536 with `tuned-fp64`,
`research-fused-fp64` and `research-doublefloat-fp32` at 1e-4. Diagnostics at
1e-9: one profile on irregular-2048/dense_block-1024 for seven configurations;
seven 200-proposal repetitions on small-4/irregular-2048/dense_block-1024 for five
configurations; one Systems trace on irregular-2048 for five configurations; three
200-proposal repetitions on each extension instance for six configurations. The
frozen protocol file records the exact count. Seeds 17/17001/17002, controller
settings, randomized blocking, resource limits and the development partition are
unchanged. No validation/held-out data. Failed/incomplete runs remain.

All GPU work, including acceptance, the committed diagnostic microbenchmarks and
failed attempts, uses the shared lease and the original screening ledger under a
new identity `gpup5c-v1`. Preserve the 4996-event prefix SHA-256
737e1301cb31cf5d0ad0585aa81a4dc0b814615d39e4974827e504e880b11e5f and
2235353878971 charged nanoseconds. Cap new study work at 1500 seconds and
acceptance at 300 seconds, with a combined 1800-second cap inside the existing
4502574545061-nanosecond ceiling and unchanged campaign/phase caps. Admit complete
deadline/cleanup reservations before work. Exhaustion stops with explicit missing
evidence, never another allowance. Four build jobs; four-hour CPU validation ceiling.

## Documentation and acceptance

Record the uncharged 2026-09-19 investigation in the root-cause note before
measurements and label every number by its provenance. Require strict evidence
checks for both schema versions, CPU/device bitwise differentials for all twelve
modes over controller boundaries, double-float rational fixtures, fault and
memory-admission tests for the new modes, manifest-v2 validation with byte-identical
v1 outputs, full pinned-native tools/check.sh and all four scoped sanitizers
sequentially. Report coverage per tier, paired certified latency, equal-work
execution, traces on extension instances, memory and transfers; a negative speed
result is valid evidence. No supported preset, adaptive recovery, quantization or
runtime tolerance change follows from this slice.
