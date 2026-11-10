# GPUP-8 availability recovery: native inventory deadline

GPUP-8 remains **incomplete**. The approved availability-test correction works,
and every command in tools/check.sh passes, but the combined gate exceeds its
fixed CPU deadline before completing the compile-only device-test inventory.
No device work follows. This is a resource refusal, with no numerical failure
established by this attempt.

The user approved **1240 additional CPU seconds**, allocated as 1200 native and
40 reporting. The cumulative CPU ceiling is **37140**, continuation allocation
**7340**, and worker allocation **2052**. The GPU cap remains **790 seconds**
(290 acceptance, 200 profiles, 300 timings); every completion criterion is exact.
See the [accepted recovery](../plans/lp-tensor-warp32-availability-recovery.md) and
[authorization](data/tensor-warp32/availability-recovery-authorization-v1.json).

## Verified correction and retained acceptance

The actual driver-availability test and four new mocked Rust tests pass. The
correction distinguishes load/symbol/initialization failures from a version-query
failure after successful initialization. Unexpected call identities, inconsistent
availability, success-valued errors and unsupported successful versions refuse.
The original failure log still lacks its exact driver call/status; the new pass
does not retroactively identify that old error.

Eight source-bridge regressions pass before the full gate. The separate
[source bridge](data/tensor-warp32/prerequisite-source-bridge.json) preserves the
prior source bytes, verifies identical production driver bytes and rejects every
other numerical-source change. Original CPU admission payloads, endpoints,
images, release executables and the verification-cache helper are unchanged.

The completed tools/check.sh receipt binds source
`267c5b7488482ea9005f359e367dcff2b97f363fe2e9ffd7b6008db5cb897138`.
Clippy, all Rust/native tests, **424 Python tests**, dependency checks, historical
replay, **157 documentation pages/internal links**, and CPU smoke pass. The
separate native-gate-v3.json receipt is retained. Its exact 1137-file source tree
is archived in artifacts/gpup-tensor-warp32-v1/availability-native-source-v1.tar,
with a separate hash-bound inventory receipt. Later delivery documentation is
separate from this accepted software source.

## Resource refusal and stop

The unchanged supervisor returns **guardian_cpu_wall_deadline** after
298.023240105 active wall seconds. The 1200-CPU-second reservation includes a
298-second workload deadline and reserved finalization. Its full **1200 CPU
seconds** remain charged. The compile-only inventory has no completed receipt,
so the combined native/resource gate does not pass. The completed software
checks do not waive that missing prerequisite.

Both workload and guardian cleanup receipts are empty. There is no new GPU
execution, reservation, frozen study, device acceptance, sanitizer, profile or
primary timing. GPUP-9 remains gated. No bootstrap rerun, host/container change,
supervisor change, automatic retry, criterion relaxation or commit occurs.

The exact **17366-event** GPU ledger remains
`9142829b3be8afdb1865425c83ca9122371284ca0e16f7bc8b18d303a5894426`.
GPUP-8 consumption is **863.208464546 / 3000 GPU seconds**; campaign consumption
is **22222.794320335 / 25202.574545061**. All prior artifacts and charges remain.

At the native stop, CPU accounting is **34458.336534342 / 37140 seconds**.
Reporting and final delivery charges remain separate. Scientific stages are
closed; unused allocations authorize no retry or implicit transfer. The
[failure receipt](data/tensor-warp32/native-refusal-v3.json) retains the exact log,
source, resource and cleanup identities. Final CPU-only delivery verifies the
receipts, documentation, smoke and diff hygiene without replacing the missing
combined native gate.

Final CPU-only delivery passes exact failure/source-archive/ledger checks, 158
documentation pages/internal links, CPU smoke and diff hygiene. Cumulative CPU is
34492.792106322 / 37140; this availability recovery charges
1263.732468604 CPU seconds, retaining all prior charges.
Reporting retains 25.307512328 CPU seconds, unavailable for an
automatic retry. Final failed/closed journal:
artifacts/gpup-tensor-warp32-v1/cpu-journal-availability-final-v11.json.
Exact accounting: docs/benchmarks/data/tensor-warp32/native-final-cpu-accounting-v3.json.
Native and delivery cleanup are empty. No new GPU work or commit occurred.

[Final accounting](data/tensor-warp32/native-final-cpu-accounting-v3.json) and
[CPU-only delivery checks](data/tensor-warp32/availability-delivery-checks-v1.json).
