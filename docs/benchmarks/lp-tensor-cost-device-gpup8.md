# GPUP-8 Tensor cost continuation: device correctness stop

GPUP-8 remains incomplete. The bounded ADR-0044 continuation stops at device
controller acceptance; it establishes no certified solve or latency gain.

The in-container supervisor passes 26 resource tests, including completion
results larger than 64 KiB, truncation and tampering. The full pre-device native
gate passes 405 Python tests, Rust/native, dependencies, historical replay,
149 documentation pages and smoke. Both CPU cohorts, independent component/norm
proofs, compact-preparation comparisons and the 88-register/zero-spill image are
retained separately. Cooperative sampling does not establish hard cgroup limits.

All 66 ordinary GPU tests pass. The new suite passes 280 CPU/device product pairs
and its range-refusal test. The INT8 controller comparison fails after 64 logical
updates, 66 physical updates and two audits: host/device binary64 endpoints differ.
The frozen `tc_ref_product` accumulates serially, whereas the host
`precision::product` uses a fixed warp32 reduction. Those orders are not
interchangeable under the accepted exact reference-adoption requirement. Small
rounding differences cannot be excused by relaxing that requirement.

The project failure occurs before all twelve actual-model fixed-work/replay pairs,
four sanitizers, sixteen profiles and sixty primary timings. All 76 frozen study
cells remain unexecuted. No forecast or multiplicity-adjusted gain qualifies.
Historical ADR-0043 useful Tensor solves and its failed latency comparisons remain
historical evidence; this continuation does not replace or re-sign them.

The two acceptance workers charge 38.094432271 GPU seconds, all in repeatability.
GPUP-8 cumulative charge is 863.208464546 / 3000 seconds; campaign cumulative is
22222.794320335 / 25202.574545061 seconds. The ledger has 17366 events and retains
the exact 17362-event prefix. Unspent allowance authorizes no retry, alternate
source cohort, replacement cell or GPUP-9 work.

All failed supervisor/inspection/report attempts keep their conservative charges.
The final device command charges its full 2050 CPU-second reservation. Its
supervisor verifies empty cleanup, sampled peak RSS 450502656 bytes and maximum
sample gap 7296669 ns. No host/container/cluster configuration changes or signals
to unrelated users' processes are part of this work. The bootstrap is not rerun.

The [machine report](data/tensor-cost/device-refusal-v1.json) binds frozen sources,
images, workers, requests, ledger, endpoint differences and independent CPU
verification. The post-device reader is separate from the frozen measurement
source. Its original quoted-`SKIP` traceback false positive and full 250-CPU-second
charge remain retained; the correction matches actual runtime skip lines.

Any future continuation needs a separately accepted correction and source/resource
contract. It must reproduce the host's lane32 accumulation and reduction order,
add cancellation/subnormal/adversarial exact-order witnesses, then pass unchanged
controller, replay, sanitizer, numerical and latency gates. The present frozen
source/image is preserved, not patched or retried. No local numerical commit is
claimed after failed device acceptance.

Final delivery acceptance (2026-10-24): 150 documentation pages, internal
links/anchors, smoke and diff hygiene pass. The repeated combined integration
suite reaches its remaining wall deadline, so no final combined pass is claimed;
its full 530 CPU seconds remain charged. The earlier pre-device full native pass
is separate. [Final CPU accounting](data/tensor-cost/final-cpu-accounting.json)
retains 29749.705814258 / 35900 seconds and verified empty final cleanup.

Independent CPU review verifies 48 retained CPU records with both originating and final frozen verifiers. The final ledger SHA-256 is `9142829b3be8afdb1865425c83ca9122371284ca0e16f7bc8b18d303a5894426`. Maximum vector differences are primal: 3 ulps, dual: 3 ulps, scaled_primal: 3 ulps, scaled_dual: 4 ulps.
