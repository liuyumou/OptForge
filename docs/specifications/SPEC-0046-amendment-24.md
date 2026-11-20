# SPEC-0046 amendment 24: CPU packing diagnostic after repeated operational stops

Operational GPU v12 also stops with `lost_coordinator_heartbeat`, after about
18 seconds. Retain its nineteen partial candidate response files, sources,
ownership trace, empty cleanup and full 480 CPU / 120 GPU seconds. These are
prior-image-v2 operational responses, not image-v5 validation. Together v11/v12
retain 960 CPU / 240 GPU seconds. Neither failed reservation is repeated or
reconstructed. Candidate GPU admission, all four sanitizer suites and all ten
image-v5 scientific cells remain unattempted. No billion-scale solve has run.

The host-packing change can be measured without a CUDA context. A separate
diagnostic links the already-built image-v5 library, loads the six retained 64 M
original inputs, prepares their exact scaled arrays with the unchanged CPU engine,
and times the original and indexed packers on those same arrays. Each input has
one fresh paired measurement; reference/candidate order alternates by frozen input
position. The reference includes dropping zero-tile residual arrays, as production
image-v4 does. Compare complete packed representations bitwise when tiles qualify;
otherwise both paths must return no packed operator after transpose validation.
Report input/engine/operator costs separately and keep every timing regression.
This is a preparation-stage diagnostic, not a full preparation or solve benchmark.

Operational v13 prospectively retains and supersedes failed v12 for future GPU
admission only. Fresh CPU acceptance permits only the six named CPU diagnostic
development jobs while GPU readmission is incomplete. Bind diagnostic source,
linked library and executable, immutable model/request/order manifests, full
supervision and resources. Each cell reserves 240 wall seconds, four CPU slots,
20 GiB sampled RSS and 1 GiB storage, with the existing physical headroom. The
reference/candidate outputs coexist only for exact comparison. The source-bound
diagnostic build and small smoke checks use a separate CPU admission reservation.

Keep all phase caps and allocation totals, one-second supervision, 100 ms
advisories, original ownership/idle guards and strict certificate checks unchanged.
No GPU work is enabled by CPU diagnostic success. Future GPU v13 still requires
a new complete observed-idle result, fresh final proof and operational admission.
Remain container-only; no reset, other-job signals or shared-memory clearing.
