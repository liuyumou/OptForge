# GPUP-FP4-PROTO: persistent component trajectory admission

Status: bounded CPU implementation delivered; numerical admission refused; full prototype incomplete
Owner: numerical backend and experiment tooling
Date: 2026-11-11
Authority: [SPEC-0026](../specifications/SPEC-0026-fp4-prototype-admission.md), [ADR-0057](../decisions/ADR-0057-fp4-prototype-admission.md)
Parent contract: [SPEC-0025](../specifications/SPEC-0025-persistent-fp4-contract.md)

## Implemented CPU prototype

The [component trajectory oracle](../../tools/lp_fp4_reference.py) retains packed
E2M1 x/y/extrapolation/anchor blocks. Matrix preparation quantizes each tile once;
transpose products reuse its codes and scales. Products enumerate component
pairs, check mathematical group representability and round local combinations to
two FP32 values. Direct rational-to-FP32 rounding avoids binary64 double rounding.
Local rounding/encoding errors enter the existing recurrence; enclosure metadata
rounds upward. The v1 admission exposed an incompatibility in combining two local
error terms, documented below. Original-unit guards, transactional observation
and full rollback preserve the unchanged numerical authority.

A separately coded rational original-A PDHG recurrence supplies diagnostic
iterate errors. Both paths use a fixed binary64 coefficient replay, with no
reference-iterate adoption. This is an independent CPU arithmetic experiment,
not a native-controller integration or a solver certificate. The local two-FP32
rounding model still needs a concrete implementation and error proof on device.

The [admission runner](../../tools/lp_fp4_admission.py) freezes fixtures, sources,
settings and twelve cells, then writes immutable per-cell traces and an aggregate
decision. The [fixture configuration](../../benchmarks/configs/lp-fp4-cpu-admission-v1.json)
uses scalar, coupled, diagonally dominant and ranged-row problems. All matrices
are exactly representable in the selected components, isolating iteration/error
propagation from matrix quantization. Each component count owes every fixture
at 600 updates and three observations, with nonzero useful products. An expected
software refusal or successful rollback does not qualify a fast path.

## Frozen numerical result

The one [frozen manifest](data/fp4-proto-manifest-v1.json) produced all twelve
[result rows](data/fp4-proto-result-v1.json). **No component lane qualified.** Nine
cells refused at the cumulative enclosure guard and three at the checkpoint
metadata contract. None reached the first 200-update observation. Every refusal
rolled back the complete checkpoint while preserving attempted work and deadline
metadata. No precision escalation or independent solver certificate was executed.

Each entry below is completed updates / first refused update; the requirement
was 600 updates and three observations in every fixture for a component lane.

| Frozen fixture | 2 components | 4 components | 8 components |
| --- | --- | --- | --- |
| Scalar equality | 1 / 2, guard | 1 / 2, guard | 16 / 17, guard |
| Coupled equality | 0 / 1, guard | 1 / 2, guard | 1 / 2, metadata |
| Diagonally dominant equality | 0 / 1, guard | 1 / 2, metadata | 1 / 2, metadata |
| Bounded ranged rows | 18 / 19, guard | 19 / 20, guard | 32 / 33, guard |

The [exact evidence bundle](data/fp4-proto-evidence-v1.json) preserves all cell
traces, rollback state, frozen manifest/sources and earlier development sources
as UTF-8 text with original byte lengths and SHA-256 hashes. Its paths identify
original artifacts; the embedded bytes also make them available without the
ignored experiment directory. The three metadata-refused rows retain their last
successful diagnostic at update 1; no actual error at their refused update 2 was
recorded. Earlier progress commentary miscounted the categories as eight/four;
the immutable rows and this nine/three tally are authoritative.

The accepted stop rule closes device implementation, actual-MMA admission, four
sanitizers and profiles. All 24 pilot and twelve diagnostic cells remain explicitly
unexecuted, including native/FP8/FP16 comparisons. GPU usage is zero. This is a
CPU numerical refusal, with an implementation defect in three rows; it is not a
GPU performance result or evidence that all persistent FP4 designs are infeasible.

## Causes and lessons

**Short component expansions can already exceed the inner guard.** On the scalar
fixture at update 2, two components have a dual error of 1.953125e-3 and four
components a primal error of 2.543132e-6, against the unchanged 1e-7 relative inner
guard. These are actual errors against the independently coded original-A
recurrence, not merely pessimistic bounds. Exactly represented matrices do not
make the Halpern blends or iterates exactly representable. The bounded-row
four-component case also has actual x/y errors above 1e-7 at its refused update.

**The propagated bound can lose useful primal/dual cancellation.** At scalar
eight-component update 17, actual x/y errors are approximately 1.278411e-9 and
7.753928e-10; their enclosures are 5.842887e-8 and 1.140161e-7. The dual enclosure
triggers refusal. The bounded-row eight-component case similarly refuses at
update 33 with actual x/y errors 1.441713e-8 / 3.348373e-10 and enclosures
7.503433e-8 / 1.229166e-7. These iterate differences are not residuals or final
certificates; none establishes the 1e-9 final criterion.

The [retained-data diagnosis](data/fp4-proto-diagnosis-v1.json) checks the following
algebra for the scalar equality with interior primal projection and tau=sigma=1/4.
Before the Halpern factor and local errors, the signed primal/dual map is
`[[1, 1/4], [-1/4, 7/8]]`, with spectral radius `sqrt(15)/4 < 1`. The independent
absolute-error recurrence uses `[[1, 1/4], [3/4, 9/8]]`, with largest eigenvalue
`3/2`. The monotone envelope cannot recover cancellation or shrink at observations.
This explains a mechanism for bound growth even for a stable linear map; it is
not a convergence proof for general LPs or permission to reset the enclosure.

**Rounding and encoding need separate compatible budgets.** In v1, local pair
rounding and FP4 encoding errors were combined as their net deviation from the
ideal local value. Opposite signs can make that deviation smaller than the
encoding remainder. SPEC-0025 requires the checkpoint enclosure to cover that
remainder, so three cells correctly refuse with `enclosure omits representation
remainder`. The separate [v2 correction](../../tools/lp_fp4_reference_v2.py) sums
the maximum pair-rounding error and the encoding remainder for extrapolation and
Halpern blends. It preserves v1 exactly, adds three primitive regression checks
and does not lower the guard or change qualification outcomes. No v2 trajectory
qualification has run; correcting this defect alone cannot resolve the nine
recorded guard refusals.

Next ready is **GPUP-FP4-RECOVERY-SPEC**, a CPU-only contract/proposal task. It should
separate the corrected local accounting from the global enclosure problem,
evaluate a proved bound that retains primal/dual coupling or projection structure,
and justify component precision with its full product/normalization cost. Any
replacement for the monotone policy needs an explicit versioned contract and
proof; observed small error alone cannot authorize it. A future attempt must
retain these sources/results/charges and the original final certificate, freeze
its new conditions before execution and acquire its own concrete allocation.
Neither an automatic retry nor device execution is released by this handoff.

## Software acceptance and resources

New software tests cover rounding, operator/transpose/partial tiles, independent
short trajectories, observation persistence, cancellation, rollback, malformed
reference shapes and manifest mutation. The zero-work observation test is
explicitly ineligible for fast-path qualification.

The full `tools/check.sh` passes: 638 Rust tests, 571 Python tests, native build,
Clippy, dependency/artifact validation, committed-record replay, 200 documentation
pages/internal links and smoke. The 22 new software contracts pass separately.
The v2 correction's three primitive tests also pass. A subsequent Python run
omitted Cargo from PATH and failed three class setups (557 tests ran); its full
1000 CPU-second reservation remains charged. Software integration was repeated
with the passing gate's Cargo/rustup discovery; all 574 Python tests pass. Final outcomes, source bindings,
logs, documentation checks and cleanup are in the
[acceptance receipt](data/fp4-proto-acceptance-v1.json).

The separate task ceiling is 32000 CPU / 1560 GPU seconds. The implementation/
numerical/native/conditional-worker journal has a 28240 CPU-second ceiling;
the independent reporting/cleanup journal reserves the remaining 3760 seconds.
This allows reporting a numerical refusal without reopening its failed journal.
Two development journals reserve disjoint 1200-second subsets of unused original
implementation headroom for the correction and environment repair; they add no
funds to the original 6000-second implementation or 32000-second task ceiling.
Four CPU slots, 16 GiB sampled RSS, one GPU lease and 12 GiB device buffers apply.
Failures retain full reservations. Historical allocations and evidence remain
unchanged; no scientific retry, certificate relaxation or TENSOR2 execution.

The failed formal admission retains its full 2400 CPU-second reservation;
preparation charges 256 seconds. All successful and failed software runs remain
charged. [Final accounting](data/fp4-proto-accounting-v1.json) includes the separate
journals and cleanup. Memory receipts report sampled aggregate RSS, not a hard
cgroup enclosure. Native control stays supported; GPUP-8 remains incomplete and
GPUP-9 gated. No public solver default, old numerical source or historical
scientific result changed. Delivery is a local commit, without publication.
