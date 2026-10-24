# GPUP-8 deadline relaxation and funding for continuation

Deadline decision: authorized by the user on 2026-10-24. The user delegates
reasonable deadline selection. Select **180 work seconds for the remaining
project acceptance actions** and **60 work seconds for final reporting**.
Resource allocation below is proposed, not accepted. No execution can resume
with the current zero worker CPU allocation.

## Evidence for the selected deadlines

The retained large-model INT8 pair took 27.423234184 seconds from request creation
through the last verification output. Its independent verification receipts take
about 5.2 seconds each; the largest is 5.331113631 seconds. Six small-model pairs
finish in approximately one second each. The large FP16 solve and replay have
both completed, but its replay verification was interrupted.

Four large-model pairs remain unexecuted. Four times the observed complete
large-pair duration plus the outstanding verification gives a diagnostic estimate
of approximately 115.024 seconds. A 1.5 multiplier gives approximately 172.536
seconds; 180 supplies additional startup and coordination room. The other four
configurations remain unmeasured, so this is an engineering allowance, not a
promise or primary latency evidence. The individual 40-second action limit stays
unchanged. A new project job reserves 180 + 6 = 186 GPU seconds.

The prior final-report reservation supplied only fourteen work wall seconds.
Allowing sixty work seconds requires **248 CPU seconds**: (60 + 2) times four,
using the existing supervisor and its unchanged work/finalization reserves.
Reuse exact completed verification receipts. Verify the one interrupted replay
on CPU and every newly produced endpoint. Do not repeat completed software,
inventory, ordinary-device, project-unit or fixed-work/replay checks.

The machine-readable [deadline amendment](../benchmarks/data/tensor-warp32/deadline-amendment-v1.json)
records the selected settings separately. Preserve all original frozen requests,
failed identities, artifacts and charges. New execution needs distinct request,
worker and composite receipts that bind the completed prior work and the newly
completed actions; a larger timeout alone must never relabel the old failure.

## CPU funding needed to use the deadlines

The last failed worker reservation retains its full 3964 CPU-second charge.
Before this deadline amendment, cumulative CPU is 38710.817591066 / 39640;
remaining worker allocation is **zero**. Only 929.182408934 seconds remain under
the ceiling, including the restricted 400-second termination allocation. The
180-second project's existing joint admission alone requires more than
4 times (186 + 120 + 2) = **1232 CPU seconds**, before setup/reporting. Extending
a deadline cannot refund a failed reservation or create this missing allocation.

Request **3600 additional CPU seconds**, raising the cumulative ceiling to
**43240**, plus explicit reallocation of unused implementation/native/reporting
funds. The continuation allocation including historical charges becomes **13440**.
Use these prospective headrooms after this amendment's final charge:

| Stage | CPU seconds | Scope |
| --- | ---: | --- |
| Implementation and admission | 100 | Versioned resume adapter, focused checks and exact source/composition bridge |
| Workers | 3600 | Remaining acceptance, conditional sanitizers/profiles/timings, monitors and verification |
| Final reporting | 248 | Sixty work wall seconds with completed-receipt reuse |
| Existing restricted termination margin | 400 | Preserve its named purpose |
| **Total** | **4348** | |

No compile-only inventory or full software gate rerun is allocated: both passed
and are retained. All covered numerical, test, build and execution sources remain
exact; scheduling/composition adapters must live separately under artifacts and
receive their own focused acceptance. Preserve the verification-cache helper.
The original source archive, inventory, successful composite and original failed
CPU/device/report receipts remain immutable. Revalidate exact source and binary
bindings before resuming; do not assume source equivalence from a matching label.

This amendment uses at most 32 existing implementation CPU seconds. Even at that
maximum, existing unused funds plus the proposed 3600 exceed the 4348 prospective
headroom by 68.238730824 seconds. Maximum cumulative accounting would be
43090.817591066 / 43240. The final amendment accounting receipt supplies the exact
measured charge. Unused funds remain unused; there are no implicit transfers.

The 3600 worker CPU seconds allow 900 wall seconds, or 898 work wall seconds.
The existing GPU allowance has 693.964779600 seconds left. This leaves about
204.035 wall seconds outside leases even if all remaining GPU allowance is used.
The existing per-job 120-second tail and 1.25 resource-fit estimator remain in
force. Queueing, overhead, missing forecasts or resource exhaustion can refuse.

## Preserve the GPU cap and every scientific completion criterion

The **790-second GPU cap includes the 96.035220400 seconds already charged**.
Do not reset that counter or the 17370-event ledger. Phase caps remain acceptance
290, profiles 200 and timings 300 seconds. Acceptance has 193.964779600 seconds
left, so the proposed 186-second project reservation fits on its own.

This does **not** guarantee that every remaining acceptance job will fit. The
four sanitizer reservations total 164 seconds; if the project consumes its full
reservation, only 7.964779600 acceptance seconds remain. Each subsequent job must
satisfy the existing admission rule using settled actual consumption. No phase
cap increase, sanitizer omission, silent borrowing or automatic retry is allowed.
Insufficient admission leaves GPUP-8 incomplete even with a longer deadline.

Keep all twelve fixed-work/replay pairs, all four sanitizers, all 76 study cells,
complete profile horizons, original timing/profile deadlines and ordering, useful
INT8 plus FP16/BF16 certified solves, 1e-7 local budgets, 1e-9 original-model host
certification, FP64 state, sticky promotion and charged whole-window replay.
Keep five certified repetitions with no coverage loss and the six-comparison,
95%-family-confidence bootstrap criterion, 10000 resamples, seed 17002.
A timeout is still a failure; a relaxed operational deadline is not a relaxed
numerical or latency threshold. GPUP-9 remains gated. No host/container change,
bootstrap or supervisor change, publication or merge follows.
