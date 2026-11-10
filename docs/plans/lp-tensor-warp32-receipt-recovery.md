# GPUP-8 receipt-link recovery

Accepted by the user on 2026-10-24: fix receipt links while preserving all original
records, continue from the interrupted forecast using unused funds, rerun no
passed check or profile, and keep every completion criterion unchanged.

## Resources

Reallocate only existing unused CPU funds: implementation 240, forecast 400,
timings 6400, reporting 600 and restricted termination margin 400 seconds.
Total 8040; leave 295.590819556 of retained stage funds unused. Keep the 53640
CPU ceiling and all historical charges, including the full 2400-second profile
failure. Maximum prospective cumulative CPU is 53099.217955206 / 53640.
Worker reservations are separately 400 for forecast and 6400 for timings.
No borrowing or automatic retry. Keep warp32 GPU 1640 including 369.700946478
already charged, with acceptance/profile/timing caps 330/320/990, GPUP-8 3000
and campaign 25202.574545061/28800 plus each campaign phase ceiling unchanged.

## Correction and continuation

Keep every original trial, cache receipt, endpoint, worker, image, journal, failed
source and report byte-exact. Write separately versioned corrected trial views;
the only permitted change is a null artifacts.verification field becoming the
exact existing verification receipt reference. Bind original/corrected trial and
receipt hashes. Validate model, request, endpoint, executable, source/helper and
assessment bindings before admission. Read these explicit corrections in the
unchanged strict reader without modifying original files or verification helpers.

Add focused tests for correction scope, missing/mismatched receipts, identity
substitution and no numerical rerun. Preserve all passed software/inventory,
device acceptance and sixteen completed profiles. Run the interrupted original
forecast once against corrected views, and retain its result. If it passes,
evaluate the unchanged 1.25 resource estimator against the active 6400-second
timing allocation, preserving the 120-second tail and 990-second GPU limit.
Only then execute the sixty untouched timing identities in the frozen order.
Each newly produced endpoint is independently verified once. Create the same
versioned link correction for any new trial affected by the frozen writer's
receipt ordering; do not rerun or overwrite its record.

## Completion and delivery

Keep exact roster, device, deadlines, 2000-update horizons, 1e-7 local budgets,
1e-9 original-model host certification, resident FP64 state, sticky promotion,
charged replay, working integer/floating families, all five repetitions and all
sixty certified timings without coverage loss. Keep the six-comparison adjusted
95% family confidence bootstrap, 10000 resamples and seed 17002. Original gain
forecast and scientific report calculations stay unchanged. The historical
failed profile supervisor is retained alongside the new correction/forecast
composite; it is never relabeled passing.

A failed gate closes this continuation. Produce a separately funded CPU-only
report with reused receipts, exact accounting, metadata/source bridge, docs/link
and diff checks and empty cleanup. No host/container/supervisor change, bootstrap
rerun, automatic retry, GPUP-9, publication or merge. Commit locally only after
applicable acceptance passes.
