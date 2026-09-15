# ADR-0014: Freeze the Initial LP Baseline Protocol

Status: accepted by the maintainer's Slice 2 implementation instruction
Owner: experiment tooling and numerical backend
Introduced: GPUP-2
Last reviewed commit: bootstrap (first commit containing this document)
Supersedes: none; instantiates ADR-0013
Superseded by: none

## Decision

Freeze campaign gpup-baseline-v1 before comparative trials. Absolute, relative
and integrality tolerances are 1e-9; solver seed 17; one CPU thread; ten seconds
per solve and two seconds cancellation/cleanup. Set an 8 GiB aggregate host RSS
watchdog sampled every 10 ms and an 8 GiB LP device-buffer limit. RSS monitoring
is not hard memory isolation; CUDA virtual addresses are not resident memory.
Retain the 16 MiB model input limit. LP settings: 50,000 iterations, check interval
200, ten Ruiz passes, alpha 1, twenty power iterations, restart fractions
0.2/0.8/0.36 and weight gains 0.5/0/0. Native simplex work limit is 50,000.

Partition seed bases are development 17100, validation 27100, held_out 37100.
Add family indices 0 through 4: scheduling, irregular, dense_block, scaling,
small. Related sizes/transformations share a family/partition group. Scheduling
uses the existing Taillard generator and Rust positional encoder, relaxing only
integer domains: 20x5 and 50x10. Irregular square LPs have 256/2048 variables and
row widths 4 through 32. Dense-block LPs have 256/1024 variables, 32x32 blocks
and sparse coupling. Scaling cases have 64/256 variables and power-of-two
coefficients with exponents -20 through 20. Small 4/16-variable cases have
constructed primal/dual witnesses. Other generated families use a versioned
SHA-256 counter generator, integer coefficients and dyadic values, bounded
variables, and a known feasible construction. Record exact generator parameters,
source/license, group and byte hashes. Existing ta001/ta011 relaxations remain
development diagnostics. No external dataset is introduced.

Freeze all partitions, but measure development only in GPUP-2. Source/hash
inspection is for correctness; validation/held-out solve outcomes are not used.
Compare highs, host-lp and cuda-lp in three repetitions. Within each instance and
repetition sort configurations by SHA-256 of order seed 17001, instance,
repetition and configuration ID. No unrecorded warmups. Primary time runs from
fresh process launch through independently checked output and teardown. Run one
separate profile per development instance/backend; exclude profiles from primary
samples. Per-instance paired median ratios use 10,000 paired bootstrap resamples,
seed 17002, percentile 95% intervals. Only mutually certified pairs enter ratios;
show full coverage/failures alongside them. Three repetitions provide weak timing
variability evidence, not cross-problem generalization. No aggregate winner score.

Pin GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48 (RTX 5090); pause on competing
activity rather than switching devices. Slice 2 study cap is 900 seconds within
the existing 1,800-second baseline phase. Preserve total 28,800 and phase limits
1800/7200/7200/9000/3600. Charge failed/profile jobs from lease acquisition through
teardown; report queue wait separately. Reserve each complete job before launch;
charge unresolved reservations fully after a crash. CPU study and acceptance
costs are separate. No ledger reset or phase borrowing.

## Interfaces and consequences

The strict version-1 artifacts are specified in SPEC-0013. Optional solve evidence
contains an unchanged solve-record-v2, canonical dual witness, fresh host endpoint
assessment and diagnostics. HiGHS multipliers are untrusted inputs to the host
certifier; native optimal status and native bound diagnostics do not certify an
endpoint. A standalone verifier recomputes the assessment. Preserve the Backend
trait, ordinary solve formats, numerical defaults and existing unsafe boundaries.

The host uses adaptive restart/weight control; the GPU currently does not. Their
comparison is not a pure device speedup. Matching controllers belongs to GPUP-3.
Incomplete measurements yield an interim report. Frozen choice changes need a new
decision and experiment identity before affected trials.

## Acceptance

Strict schemas, exact generation, corrupted endpoint evidence, crash/limit/lease
and cleanup tests, hand-checkable paired/censored analysis, the pinned-native gate
and relevant device/sanitizer cases precede baseline acceptance. The implementation
records actual resource consumption and maps SPEC-0013 requirements to tests.
