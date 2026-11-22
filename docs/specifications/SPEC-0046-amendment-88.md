# SPEC-0046 amendment 88: audited-data cleanup and smaller host reservations

The ill-scaled project attempt completes normally at its solver deadline:
6400 accepted / 6500 physical updates, 1875.828319590 seconds native elapsed,
99.153492464 seconds input. All fourteen distinct endpoint proofs pass their
independent audit and confirm the uncertified outcome. Complete cost including
the cold final proof is 2236.278415066 seconds; offline intermediate verification
takes 1981.486336049 seconds. The original source/settings and every proof remain.

The following COPT launch fails the physical host-headroom preflight before any
reservation, CUDA context or LP attempt. The four-cell driver exits and must not
run again. Three cells remain untouched: ill-scaled COPT and both degenerate lanes.
Observed GPU use is 0.750 GiB, zero utilization and no listed processes. Host
availability is approximately 129.6 GiB, below the old 128+4 GiB requirement.
Do not infer ownership of host memory or disturb another job.

All ill-scaled project endpoint checks are complete. Delete only its obsolete
large endpoint objects, excluding every original model/construction object;
retain small responses, proofs, raw logs and a deletion receipt. The original
ill-scaled model remains available for COPT. No checkpoint replay is claimed.

For the two untouched COPT cells, prospectively reduce the per-job host RSS stop
and reservation from 128 to 120 GiB. Their retained empirical forecasts including
the existing 15% plus 8 GiB margin are 110.064356208 and 110.062436938 GiB. Thus
120 GiB adds almost 10 GiB beyond those already padded forecasts. This remains an
empirical admission, not a hard vendor enclosure. The native soft MemLimit stays
48000 MB; no solver setting or numerical request changes. A smaller observed RSS
stop is stricter, and the physical preflight still requires an additional 4 GiB.
Never launch when available host memory is below 124 GiB or GPU idle checks fail.

The global caps remain four CPU slots, 128 GiB host, 80 GiB GPU and 400 GiB storage.
Actual one-second supervision, the 0.9-second inventory timeout, 100 ms advisories,
all ownership checks, CPU v34 / GPU v26 and numerical bindings remain exact. The
three native allowances remain 1800 seconds, outer reserves 2700 seconds, and
strict original-model 1e-9 checks remain. The completed ill-scaled project cell
and every prior attempt/failure retain their exact declarations and full charges.

Reserve the whole untouched scope before launch: 960 admission / 36000 development /
34000 reporting / 720 cleanup CPU seconds, and 8100 development GPU seconds. This
includes the three solves, one 900-second degenerate regeneration, both 900-second
vendor audits, the 4600-second project audit, a fresh 480-second joint host/GPU idle
window, report/verification and contingency. Cleanup includes early endpoint
deletion plus both family cleanups. Total 570000 CPU / 68000 GPU seconds and all
phase caps remain unchanged. No new approval, exception, scientific retry or
operational source change is introduced.
