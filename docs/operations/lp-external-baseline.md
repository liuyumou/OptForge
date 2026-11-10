# External LP baseline execution

This isolated research harness implements [SPEC-0022](../specifications/SPEC-0022-external-lp-baseline.md)
under [ADR-0048](../decisions/ADR-0048-external-baseline-execution.md) and the
[versioned integration correction](../decisions/ADR-0049-baseline-adapter-correction.md),
[bounded artifact transport](../decisions/ADR-0050-baseline-artifact-transport.md) and
[CPU transport correction](../decisions/ADR-0051-baseline-cpu-transport-cost.md). It does not
register a vendor as a runtime backend or change existing numerical code.

The CPU integration tests build both standalone checker crates from their locked
sources and create an explicit mock worker context. They require neither a vendor
installation nor ignored study manifests/binaries. Install `tools/requirements.txt`
and `tools/baseline-test-requirements.txt`, then run `bash tools/check.sh`; the normal
gate prepares HiGHS before these tests. The buffered checker's standalone Rust test
also runs. Vendor Solve calls in these tests are mocked and no GPU is used.

The [PR source bridge](../benchmarks/data/external-baseline-pr-source-bridge-v3.json)
preserves four original test files and the requirements manifest, binding only
CPU test setup/dependency and historical-admission changes.
Historical experiment receipts continue to bind their original frozen source
archive; this integration bridge does not amend any numerical result or charge.

The completed continuation uses [ADR-0052](../decisions/ADR-0052-baseline-native-return.md)
and [SPEC-0023](../specifications/SPEC-0023-baseline-native-return.md). At the
user's request, cuOpt's error-free native returns pass a separate comparison
policy even if strict certification refuses. Error code/message, exact native
termination, objectives/residuals, raw duals, certificate differences and GPU
confirmation remain separate evidence. Limits remain limits; no vendor claim is
converted into a mathematical certificate. The presolve-only maximization dual
mapping remains an adapter uncertainty rather than an attributed cuOpt defect.
The [completed report](../benchmarks/lp-external-baseline-native-return.md) records
all 240 settled attempts, including native errors and outer timeouts; completion
does not mean every solver succeeded.

`tools/lp_baseline_study_v5.py` supplies `freeze`, `screening` and `report`.
Its [execution manifest](../../schemas/lp-baseline-execution-v5.schema.json) reuses
all 123 settled screening cells and selects exactly the 117 unexecuted cells.
The thin v5 worker invokes the unchanged v4 worker with a cuOpt metadata adapter;
non-cuOpt numerical functions and the checker binary are reused directly. Native
settings, deadlines and ordering stay unchanged. Old strict admission outcomes
remain retained diagnostics; cuOpt's strict gate no longer blocks this comparison.

The original model is canonicalized without coefficient arithmetic. COPT uses
scalar construction and exact CSC readback; cuOpt uses native paired row bounds,
CSR permutation and exact readback. Both attempt to export original-unit row
multipliers normalized to minimization; the cuOpt presolve-only maximization path
has a retained mapping refusal. Four tiny min/max/ranged/equality cases with nonzero
duals and an offset precede each nontrivial admission endpoint. The two project
FP64 lanes reuse the retained executable/code objects. HiGHS uses its existing
safe diagnostic API through the new research binary.

`research/lp-external-baseline-buffered` builds the active solver-neutral checker.
The original `research/lp-external-baseline` and its receipts are retained.
Both have byte-identical mathematical assessment and strict parsing; the active
writer buffers output, then flushes and fsyncs. Its `check`
command takes original model, candidate and output paths. Unknown/duplicate fields,
wrong hashes/IDs, missing vector fields and wrong dimensions refuse. Null vectors
are unavailable evidence. The mathematical decision calls `Model::evaluate`,
`certify` and `assess_gap` with absolute and relative tolerances 1e-9. It records
the actual binary hash; the execution manifest binds that binary to its sources.
The [candidate schema](../../schemas/lp-baseline-candidate-v1.schema.json) is
separate from the final endpoint to avoid a circular certificate hash.

The [execution schema](../../schemas/lp-baseline-execution-v4.schema.json) freezes
all 260 admission/screening jobs. The retained `tools/lp_baseline_study_v4.py` provides `freeze`,
`hardware`, `admission`, `screening` and `report` commands. They run sequentially
under the separate budget ledger and the retained cooperative CPU supervisor.
An existing identity is never overwritten or retried. The v1 admission remains
immutable; v2 corrects cuOpt bound method names and the project artifact filename,
requests the retained project/HiGHS APIs' supported one native thread, and reuses
six COPT and two hardware passes. v3 separates the 16 MiB cap on each output log
from the 128 MiB artifact cap. v4 compiles two flat schemas and buffers checker
serialization; it reuses all admission outcomes and five complete small-model
blocks. The separate large-model timeouts remain failed observations. All four
identities count against the same caps. The original proposal
retains `execution_authorized=false`; only this accepted execution allocation
and a complete freeze permit the new worker release.

The v1-v4 GPU allowance is 3600 seconds, divided into hardware 60, admission 420
and screening 3120. Its closed CPU allocations total 16000 seconds: implementation
2700, hardware 240, admission 2400, screening 9860, reporting 600 and restricted
cleanup 200. Reserve an entire job
before release; failures and unsettled reservations retain their full charge.
An overrun or incomplete reservation closes further release. The historical
campaign ledger is checked byte for byte and never appended by this harness.

The newly authorized v5 continuation has its own 32000-CPU-second cap:
implementation 1600, screening 28080, reporting 1600 and restricted cleanup 720.
Prior CPU charges and ceilings remain closed historical allocations. Total baseline
GPU authority stays 3600 seconds, including 1277.244626616 already spent; v5 can
reserve 2322 whole remaining seconds. Each whole reservation must still fit.
The worst-case grid exceeded the GPU remainder, but the observed complete run
fit within it. Every failure retains its full reservation and no deadline or
GPU cap was increased. The final report links exact settled accounting.

The primary latency comes from a launch wrapper immediately before starting a
fresh worker through its exit after durable candidate/certificate/endpoint output.
The endpoint's own `elapsed_ns` describes only its extraction/checking envelope;
the separate trial clock is authoritative for comparisons. Queue/lease waiting
and supervisor overhead are separately recorded. Optional native solve time is
never substituted for this primary measurement.

All GPU jobs use the shared host lease, one frozen UUID and four CPU affinity
slots. Project and HiGHS use one supported native CPU thread; COPT and cuOpt
request four. This measures implementations within equal available CPU resources,
with explicit differences in native thread usage. Vendor GPU confirmation uses affirmative native execution evidence or
process-attributed SM activity. Device memory is sampled through `nvidia-smi
pmon`; host aggregate RSS is sampled by the retained supervisor. Neither is a
hard memory enclosure. Project allocations also retain their explicit native
buffer limit. A context-only probe is not solver admission.

The cuOpt environment stays unchanged. A separate hashed validator overlay copies
the host's JSON-schema support packages for the fresh worker; its exact bytes
and compiled extension are recorded in the environment manifest. v4 additionally
binds a separate `fastjsonschema==2.21.2` wheel and installation. Only the two
flat canonical-model/endpoint schemas use it; original strict JSON, finite-value,
integer and sparse conversion checks remain. No license
contents are read or copied into provenance. COPT discovers its existing license
through its normal environment API.

Report all planned cells, including unavailable, blocked and unexecuted cells.
Per-model speedups require all three corresponding certified pairs and confirmed
GPU execution where requested. Use paired log ratios, their median and 10000
bootstrap resamples with seed 17111; the 95% percentile interval is deliberately
limited by only three repetitions. There is no aggregate competitiveness claim
on this generated development corpus and no held-out access.

Under SPEC-0023, show cuOpt native-return timing separately from certified timing.
It requires completed outer transport for a complete-latency statistic. A vendor
return surviving a later checker/worker failure is still logged but has no
successful full-delivery time. Ratios involving cuOpt native acceptance are
explicitly not quality-matched certified speedups. Reused small-model v2 transport
differs from new v5 transport; its cross-cohort paired ratios are withheld.

New CPU acceptance covers checker witnesses, resource admission, vendor API
mapping, log containment, schema equivalence and buffered serialization. It lives
in the new `test_lp_baseline_*` integration modules and buffered research crate.
Historical passed scientific tests and profiles are reused, not rerun.

The v1-v4 identities are closed. Running their commands again must never
overwrite evidence or retry a refused numerical admission. A continuation needs
a separate manifest, explicit reservation fit and retained outcomes. The user's
native-return amendment changes comparison acceptance while preserving the strict
quality contract. See the [original execution report](../benchmarks/lp-external-baseline-gpup-baseline.md)
for coverage and the [roadmap](../plans/gpu-lp-precision-roadmap.md#current-plan-2026-11-10)
for the next design decisions.
