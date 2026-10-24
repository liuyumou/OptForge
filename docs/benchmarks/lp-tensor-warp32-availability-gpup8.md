# GPUP-8 warp32 native availability stop

The approved native recovery remains **incomplete**. The new full gate passes
formatting and Clippy, then fails the existing CUDA driver-availability test
at `crates/optimizer-cuda-sys/src/lib.rs:1047`. Its full **1200 CPU seconds**
are charged; a partial Rust run does not establish full native acceptance.
The Python integration suite, subsequent native/dependency/replay/docs/smoke
commands and compile-only device inventory do not complete in this gate.
Separate CPU delivery checks, when present, do not replace it.

The native wrapper explicitly hides all CUDA devices. The test accepts only
`DriverUnavailable` and `SymbolMissing`; source inspection shows that
`driver_version` can also return a `Driver` error from `cuInit` or
`cuDriverGetVersion`. The assertion log omits the error value, so the exact
call/status is unestablished. Hidden-device initialization is the likely
trigger, not an observed numerical failure. No driver diagnostic or test
has been rerun. A future correction should preserve CPU-only operation and
make driver-availability testing deterministic or handle the documented
availability-error path with focused mocked coverage. It needs a separately
approved bounded gate and exact stage allocation before execution; this
report authorizes neither source substitution nor another attempt.

The corrected warp32 image and all accepted CPU evidence remain unchanged:
88-register/zero-spill admission, 592 independent bit/refusal cases, 48 retained
eight-model cells, 24 independently verified CPU endpoints and all twelve
required useful dense trajectories. None establishes device or latency success.

There is **zero new GPU execution**. The exact 17366-event ledger remains
`9142829b3be8afdb1865425c83ca9122371284ca0e16f7bc8b18d303a5894426`.
GPUP-8 consumption stays **863.208464546 / 3000 GPU seconds**; campaign
consumption stays **22222.794320335 / 25202.574545061**. The continuation's
790-second cap and all numerical/latency completion criteria remain unchanged.
No freeze, device acceptance, sanitizer, profile, timing or new reservation
follows the native stop. GPUP-9 stays gated.

The resource receipt verifies empty workload and guardian cleanup; sampled peak
RSS is 1691017216 bytes. No hard cgroup memory containment is claimed. No host
access, resource-bootstrap rerun, container configuration change, unrelated
process signal or commit occurs. Every previous failure charge remains.
Cumulative CPU at the native stop is **33196.332668818 / 35900**; the separately
journaled CPU-only delivery adds its measured/conservative charges afterward.

See the [failure receipt](data/tensor-warp32/native-refusal-v2.json),
[accepted recovery plan](../plans/lp-tensor-warp32-native-recovery.md) and
[ADR-0045 stop rule](../decisions/ADR-0045-warp32-tensor-reference-recovery.md).
The final delivery receipt and accounting will remain separate from the failed
full native gate.

Final CPU-only delivery passes exact failure-source/receipt checks, 156
documentation pages/internal links, repository CPU smoke and diff hygiene.
These checks do not replace the failed full native gate. Cumulative CPU is
33229.059637718 / 35900; continuation charge is
3474.353823460 CPU seconds. Reporting retains
19.763084308 CPU seconds, unavailable for automatic retries.
The final failed/closed journal is cpu-journal-native-stop-final-v8.json;
exact accounting is docs/benchmarks/data/tensor-warp32/native-final-cpu-accounting-v2.json.
Both cleanup receipts are empty, and fresh hashing verifies the unchanged exact
17366-event GPU ledger. No new GPU work, host/container change or commit occurs.

[Final accounting](data/tensor-warp32/native-final-cpu-accounting-v2.json).
