# SPEC-0046 amendment 79: proposed complete fair COPT comparison allocation

This is a proposal, not an applied allocation change or a scientific freeze.
The user requests a fair comparison against installed COPT on the same problems,
with strict original-model 1e-9 checks. The current 370000 CPU / 44000 GPU-second
allocation cannot reserve the full comparison. Investigation under amendment 78
continues within existing caps while this proposal awaits explicit approval.

Proposed totals: **570000 CPU / 68000 GPU seconds**. CPU phase caps, in order,
are implementation 10000, native 26000, admission 72000, development 260000,
reporting 200000 and cleanup 2000. GPU caps are admission 12000 and development
56000. Preserve the entire previous approval chain and every failed charge.
No new overrun exemption is proposed. Physical limits remain four CPU slots,
128 GiB sampled host RSS, 80 GiB owned GPU and 400 GiB owned storage, with the
existing headroom, idle, ownership and supervision checks. Stay inside the
container and use only the idle Pro6000. Commit locally only.

The conservative added reservations below start from the settled image-v11
checkpoint of 314228.458381384 CPU / 35557.827345976 GPU seconds. They include
the investigation already starting under existing capacity; actual settled
charges replace its prospective reservations without double charging.

| Work | CPU seconds | GPU seconds | CPU phase / GPU phase |
| --- | ---: | ---: | --- |
| Contracts, small GPU admission, fresh CPU/GPU operational checks | 2880 | 420 | admission / admission |
| Three remaining 64 M capacity cells and four 256/512 M cells | 13800 | 3450 | admission / admission |
| Pilot input regeneration, twelve startup diagnostics | 8400 | 1800 | development / development |
| Remaining smaller capacity input regeneration | 4080 | 0 | development |
| Six billion input regenerations, at 600 wall seconds each | 14400 | 0 | development |
| Twelve full billion attempts, at 1800 wall seconds each | 86400 | 21600 | development / development |
| Two sustained idle windows | 3360 | 0 | reporting |
| Twelve diagnostic and seven capacity endpoint audits | 9240 | 0 | reporting |
| Six project final/intermediate audits | 79200 | 0 | reporting |
| Six COPT independent final audits | 12400 | 0 | reporting |
| Retrospective analysis, reporting, final verification, documentation | 2400 | 0 | reporting |
| Nine bounded cleanup jobs | 1080 | 0 | cleanup |
| Prospective plan validation | 240 | 0 | implementation |
| **Total added reservation** | **237880** | **27270** | |

Thus the whole conservative task totals 552108.458381384 CPU /
62827.827345976 GPU seconds, below the proposed totals and every proposed phase
cap. The remaining margin covers limited failed administrative/admission attempts;
it does not authorize extra scientific repetitions or unbounded tuning.

Use one global COPT configuration selected from the prespecified startup
diagnostics, retaining every losing or regressing configuration. First maximize
strictly accepted, timely diagnostic endpoints, then compare complete cost among
jointly certified endpoints; unresolved cases and initialization progress remain
explicit. Do not select a separate favorable configuration for each family.
Retain automatic-scaling Presolve=0 as the instrumented diagnostic control.
Do not change installed COPT or numerical project sources in this study.

Complete the selected configuration's six-family 64 M capacity coverage, reusing
already completed matching diagnostics, then two 256 M and two 512 M paths.
Every observed path must pass supervision and demonstrate optimization workspace
or a strict optimum before it admits a billion slot. Keep empirical peak growth
and physical limits explicit; a missing or setup-only path cannot admit capacity.
Keep all six original billion families and both solver slots visible, including
unsupported entries. A full paired run is conditional on measured capacity.

Freeze fresh COPT GPU PDLP / image-v11 FP4-request pairs before execution. Both
receive the same 600-second solver allowance after original input loading;
preparation counts against it. Both get the same 1800-second outer process ceiling
including input, teardown, and interrupt grace. Image-v11 keeps control100 and
certificate500, but uses a prospective 10000-update safety ceiling to avoid the
previous 1000-update truncation. Report any binding iteration limit explicitly;
it is not equivalent to a wall timeout. COPT retains MatrixTol=0,
FeasTol=DualTol=1e-9 and PDLPTol=1e-12. No construction witness or warm start is
provided. Use identical original model/chunk hashes and alternate solver order
by family. One paired repetition is descriptive, not broad superiority evidence.

Separate strict endpoint validity from deadline compliance for both solvers.
Every returned endpoint receives the same unchanged independent original-model
checker. Every project intermediate assessment remains independently audited.
Only pairs with timely strict certificates support time-to-solution ratios.
Preserve startup time, all regressions, late endpoints, missing responses, capacity
refusals and actual FP4 work. Include original input, preparation, vendor call or
project phases, extraction/transport/teardown, and independent final checking in
complete cost; report additional intermediate audits separately.

Project audit reservations by family are 3500/4500/2800/2000/3500/3500 wall seconds
(irregular/wide/tall/coupled/ill-scaled/degenerate), covering up to twenty
certificate intervals plus final checking and repaired witnesses. COPT final
audit reservations are 500/700/500/400/500/500 seconds. Freeze full endpoint storage
before each stage. Regenerate and execute one billion family at a time, deleting
its large chunks only after both lanes and all dependent audits finish. Keep
compact results, phase journals, source bindings and failure records.
