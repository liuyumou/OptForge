# Project Status

## GPUP-FP4-PROTO CPU refusal (2026-11-11)

The [bounded prototype attempt](../docs/benchmarks/lp-fp4-proto-gpup-fp4-proto.md)
implements independent original-A and persistent-component CPU trajectories,
explicit local rounding and transactional rollback. No lane qualifies: nine
guard and three metadata refusals across twelve cells, before any 200-update
observation. Device implementation, actual MMA, sanitizers and all 36 profiles
remain unexecuted; full prototype acceptance is incomplete and GPU usage zero.

A separate local error-budget correction passes primitive software tests; the
scientific attempt is not repeated. Next ready is GPUP-FP4-RECOVERY-SPEC for a
proved error policy and justified precision/cost proposal. Keep native control,
original-model checks and strict 1e-9 certification. GPUP-8 stays incomplete and
GPUP-9 gated. Earlier dated entries describe their original handoffs.

## GPUP-FP4-SPEC CPU contract (2026-11-11)

[SPEC-0025](../docs/specifications/SPEC-0025-persistent-fp4-contract.md) implements
the E2M1 reference, interval/error guards, observation-only audits, complete
checkpoints and strict source-bound proposal/cost validation. The
[delivery report](../docs/benchmarks/lp-fp4-spec-gpup-fp4-spec.md) records acceptance
and the proposed 192-cell / 288-endpoint comparison. Six of 24 retained native
cold trials fail even the ideal per-trial 10% arithmetic-only speedup bound;
fifteen need profiles and three remain uncertified. No GPU work or FP4 speedup
claim follows. Next is FP4-PROTO's CPU reference/admission, then conditional device
work. Older dated entries retain their original handoffs.

## Persistent multi-FP4 planning priority (2026-11-11)

The [FP4 assessment](../docs/plans/lp-fp4-persistent-state.md) and
[ADR-0055](../docs/decisions/ADR-0055-persistent-fp4-direction.md) prioritize
approximate persistent component state with fused iterations, original-model
residual checks and strict final certification. GPUP-FP4-SPEC is next ready for
CPU-only numerical/cost contract work; prototype and study remain conditional.
MIXED2 and DELIVERY2 remain alternatives. The native control, historical evidence
and GPUP-8/GPUP-9 gates are unchanged. No new solver or GPU execution occurred.

## GPUP-RESIDENT2 bounded result (2026-11-11)

The [resident execution report](../docs/benchmarks/lp-resident2-gpup-resident2.md)
delivers explicit cold/prepared phases, transactional native FP64 windows and
normal-limit export. All 64 cells complete; both modes certify 42/48 endpoints
and all 42 certified pairs match bitwise. All four sanitizers pass.
Synchronization decreases, but 1.027370x cold geomean and four regressing models
fail the retention criterion. Keep the native control and select no preset.
GPUP-MIXED2 is next ready; GPUP-8 remains incomplete and GPUP-9 gated.


## GPUP-BASELINE complete under the amended comparison policy (2026-11-10)

The [completed report](../docs/benchmarks/lp-external-baseline-native-return.md) includes all 240 planned screening
attempts: 198 comparison passes and 135 strict certificates. CuOpt's
90/96 native-return passes follow the user's explicit policy; only 24/96
meet the unchanged strict checker. Native limits/errors, outer timeouts, raw
vectors and original-model discrepancies are reported separately. No failure
is silently dropped and no native pass becomes certified optimality.

The continuation reuses 123 results and executes only 117 unexecuted cells.
Nine new policy tests and one installed API check pass. GPU charge totals
3091.995889713 / 3600 seconds; CPU charges and all cleanup/evidence checks are
in the linked report. Next ready: GPUP-RESIDENT2. GPUP-8 remains incomplete,
GPUP-9 gated, and no supported precision recipe is selected. Entries below
retain earlier phase outcomes.

## GPUP-BASELINE implementation delivered; comparison incomplete (2026-11-10)

The [baseline report](../docs/benchmarks/lp-external-baseline-gpup-baseline.md)
records six admitted configurations, 123/240 executed screening cells and 108
independently certified results. Four cuOpt configurations fail quality or
postsolve admission, blocking 96 cells; another 21 eligible cells cannot fit the
CPU screening allocation. GPU charge is 1277.244626616 / 3600 seconds. The full
comparison remains incomplete, with every failure and unexecuted cell retained.

Adapters, neutral Rust checker, immutable manifests, resource runner and paired
statistics are implemented. Twenty-five new Python tests and one Rust writer
test pass, with scoped format/lint/build checks. Historical numerical sources,
passed checks and the 17438-event ledger remain preserved. Full source/evidence
and documentation checks are in the linked report's delivery receipt.

Next ready: `GPUP-BASELINE-FOLLOWUP`, a CPU-only protocol for the exact remaining
cells, cuOpt dual/quality admission and cold/prepared delivery-cost decisions.
The [roadmap](../docs/plans/gpu-lp-precision-roadmap.md#baseline-follow-up-decisions)
gives concrete gates and reservation arithmetic. GPUP-8 remains incomplete and
GPUP-9 stays gated. The dated entries below describe earlier deliveries.

## GPUP-BASELINE-SPEC CPU contracts complete (2026-11-10)

[SPEC-0022](../docs/specifications/SPEC-0022-external-lp-baseline.md) defines canonical
LP arrays, solver-neutral endpoint/checker outcomes, strict original-model quality,
fresh-process timing and the external comparison admission contract. Three schemas,
lossless CPU conversion/validation, synthetic examples and twenty new tests pass.
The [protocol](../docs/benchmarks/lp-external-baseline-v1.md) fixes ten lanes, eight
development models and 240 proposed screening cells. Phase A proposes 6040 CPU /
480 GPU seconds; conditional phase B proposes 58600 CPU / 10080 GPU seconds.
Both are proposals, not resource allocations; no solver or GPU work ran.

Next ready implementation task: GPUP-BASELINE, including the new Rust checker
bridge because existing external readers are COPT-specific. Actual device/solver
acceptance, source/device freeze and resource release remain required. Gurobi is
excluded. Historical evidence/charges are preserved; GPUP-8 stays incomplete and
GPUP-9 stays gated.

## Current direction and solver availability (2026-11-10)

The [system diagnosis](../docs/benchmarks/lp-system-diagnosis-2026-11-10.md) records
the current bottlenecks and cuOpt/COPT/Gurobi comparison. The
[revised roadmap](../docs/plans/gpu-lp-precision-roadmap.md#current-plan-2026-11-10)
and [ADR-0047](../docs/decisions/ADR-0047-certified-performance-roadmap.md) prioritize
external baselines, lean resident execution and simpler mixed precision before
conditional Tensor work. Next ready: `GPUP-BASELINE-SPEC`, a CPU-only comparison
contract and resource proposal. Future scientific execution needs its own admission.

cuOpt 26.10.0 is [installed in an isolated environment](../docs/operations/cuopt.md);
dependency and LP import checks pass with GPUs hidden. No solver run or speed claim
follows. COPT 8.0.6 is locally available; Gurobi is unavailable and not a dependency.
GPUP-8's latest result is the proof/device pass and profile timeout below. It stays
incomplete with science closed, and GPUP-9 stays gated. Historical budgets,
completion criteria, failed charges and evidence are preserved.

## GPUP-8 corrected proof and device acceptance pass; profile timeout (2026-10-24)

Final delivery passes 173 documentation pages/internal links, immutable evidence
checks and staged diff hygiene. Four exact hash-bound EOF blank-line exceptions
preserve historical/generated bytes; all other whitespace checks pass.
Cumulative CPU is 59603.097503214 / 77640 seconds; this recovery charges
8034.404049688. Timing and restricted-margin funds remain unused.
All coordinator/guardian cleanup receipts are empty. Final accounting:
docs/benchmarks/data/tensor-expanded/recovery-final-accounting-v1.json.
Final journal: artifacts/gpup-tensor-expanded-v1/recovery-hygiene-v1/cpu-journal-final-v21.json.

The corrected 7376-case proof, CPU/model/native gates and all six device jobs pass.
All twelve fixed-work/replay pairs are accounted for; twenty changed endpoints
independently verify once. Six small-model profiles complete. The first large-model
BF16 profile times out at its unchanged 18-second deadline without an endpoint.
Nine profiles and sixty timings remain unexecuted. Preserve the full 3200 CPU-second
profile failure charge and every source, image, receipt and historical charge.
No completed check/profile is rerun; no numerical or latency criterion changes.
GPU charge is 178.049776450 seconds; GPUP-8 1410.959187474/3000 and campaign
22770.545043263/25202.574545061. The 17438-event ledger
preserves the exact 17412-event prefix. Timing funds remain unused.
Report: docs/benchmarks/lp-tensor-expanded-recovery-gpup8.md.
Scientific stages are closed. GPUP-8 remains incomplete; GPUP-9 stays gated.

## GPUP-8 expanded-window proof stops on noncanonical fixture (2026-10-24)

Final CPU-only delivery passes source/evidence preservation, documentation/internal links,
syntax and diff checks. Cumulative CPU is 51568.693453526 / 77640;
continuation charge 5666.151624356 seconds. Reporting retains
761.762326424 seconds. All failure/delivery cleanup is empty.
Final journal: artifacts/gpup-tensor-expanded-v1/cpu-journal-final-v4.json.
Final report: docs/benchmarks/lp-tensor-expanded-final-gpup8.md.
Exact accounting: docs/benchmarks/data/tensor-expanded/final-cpu-accounting-v1.json.

ADR-0046 and the 24000-CPU-second / 1760-existing-GPU-second amendment are accepted.
Twelve authority/evidence and sixteen new CPU prototype checks pass. The new
scalar host harness compiles with UBSan, then rejects input 19: the generator
changes a short subnormal significand's exponent to -63 without normalization.
No scalar result was independently compared before the return-code refusal; no
arithmetic defect is inferred. Preserve the original corpus, sources and failure.

The full 5600 CPU-second proof reservation remains charged. Scientific stages
are closed; no correction/retry, implicit transfer or later scientific stage.
Implementation/native/device/profile/timing allocations remain unused. No old
passed check or profile is rerun and no GPU work or commit occurs. GPUP-8 stays
incomplete, GPUP-9 gated; cross-window persistence remains future work.
The exact 17412-event GPU ledger is unchanged. Both proof cleanup receipts are
empty. CPU-only delivery uses the separate reporting allocation.
Report: docs/benchmarks/lp-tensor-expanded-gpup8.md. Diagnosis:
docs/benchmarks/data/tensor-expanded/proof-fixture-diagnosis-v1.json.
Failed journal: artifacts/gpup-tensor-expanded-v1/cpu-journal-proof-stop-v2.json.

## GPUP-8 receipt correction passes; gain forecast refuses (2026-10-24)

Seventeen focused correction checks and exact source/provenance admission pass.
Sixteen separately stored corrected trial views bind the existing independent
verification receipts; every original trial retains its null link and exact hash.
No passed check, profile or retained numerical verification is rerun. The original
strict reader accepts the corrected views. All sixteen profiles and useful
integer/floating families satisfy the unchanged profile/forecast inputs.

The unchanged gain forecast now runs and refuses all six candidates. The best
small-model forecast is 0.642764297 s against the 0.415902600 s threshold; the best
large-model forecast is 8.977063370 s against 5.697919800 s. This is a forecast
refusal, not a measured primary timing comparison or numerical failure. No
resource-fit gate or timing worker follows. Preserve the corrected views,
original records, sources, reports, full historical charges and new forecast.

The forecast stage retains its full 400 CPU-second failure charge. The separate
6400-second timing reservation stays unused. The CPU-only scientific report
passes with original completion calculations and receipt reuse. Scientific stages
are closed; no automatic retry or implicit transfer follows. GPUP-8 remains
incomplete and GPUP-9 gated. There is no new GPU work: warp32 remains
369.700946478 / 1640, GPUP-8 1232.909411024 / 3000, and campaign
22592.495266813 / 25202.574545061. The exact 17412-event ledger remains unchanged.
Final CPU accounting is 45902.541829170 / 53640; this receipt recovery charges
843.323873964 CPU seconds entirely from unused funds. Reporting retains
315.762945624 CPU seconds. Delivery passes 168 documentation pages/internal
links, exact preservation of 637 original artifacts and sixteen corrected views,
source metadata and diff hygiene. All workload and guardian cleanup is empty.
Final closed journal: artifacts/gpup-tensor-warp32-v1/cpu-journal-receipt-final-v31.json.
Exact accounting: docs/benchmarks/data/tensor-warp32/receipt-final-cpu-accounting-v1.json. Cleanup is empty.
No host/container/supervisor change, bootstrap rerun, commit, publication or merge.
Report: docs/benchmarks/lp-tensor-warp32-receipt-recovery-gpup8.md.
Refusal: docs/benchmarks/data/tensor-warp32/receipt-forecast-refusal-v1.json.

## GPUP-8 approved receipt-link recovery (2026-10-24)

The user authorizes correcting receipt links in separate versioned records and
continuing GPUP-8 using unused funds. Preserve original trials/receipts, all
sources, failures and charges, and the exact 17412-event GPU prefix. Rerun no
passed checks or profiles. All scientific completion criteria remain unchanged.

Reallocated existing CPU headrooms: implementation 240, forecast 400, timings
6400, reporting 600 and restricted termination margin 400 seconds. No additional
CPU/GPU budget; CPU ceiling 53640 and warp32 GPU cap 1640 (330/320/990) remain.
Active journal: artifacts/gpup-tensor-warp32-v1/cpu-journal-receipt-recovery-v29.json.
Write artifact-only correction/reader adapters, run focused correction acceptance,
then the interrupted forecast and conditional timing sequence. No automatic
retry, host/container/supervisor change, bootstrap rerun or GPUP-9. Likely writes:
new correction manifests, journal/receipts/report and state documentation.
Accepted plan: docs/plans/lp-tensor-warp32-receipt-recovery.md.

## GPUP-8 funded continuation stops at profile receipt binding (2026-10-24)

The approved 10400 CPU-second addition and 850 GPU-second reallocation are
recorded. Fourteen new adapter checks and exact source/provenance admission pass.
Initcheck and synccheck pass; full device acceptance reuses ordinary/project tests,
all twelve fixed-work/replay pairs and 24 verifications, memcheck and racecheck.
All sixteen profile workers complete with independent verification receipts.
The frozen writer captures artifact references before creating verification
receipts, leaving every trial's verification reference null. The strict forecast
reader refuses these links. No forecast or timing runs, and no numerical or gain
failure is inferred. Preserve every source, trial, receipt and the traceback.

The profile stage retains its full 2400 CPU-second failure charge. The separate
6400-second timing reservation remains unused. Scientific stages are closed;
there is no automatic repair/retry or implicit transfer. Four new post-stop
reader checks and the CPU-only report pass using sixteen profile, 24 acceptance
and 24 historical CPU verification receipts, with no numerical verification rerun.
Completion criteria are unchanged. GPUP-8 remains incomplete and GPUP-9 gated.

This continuation charges 113.279588268 GPU seconds; combined warp32 is
369.700946478 / 1640 (acceptance 261.200177856 / 330,
profiles 108.500768622 / 320, timings 0 / 990).
GPUP-8 is 1232.909411024 / 3000; campaign is
22592.495266813 / 25202.574545061. The exact 17412-event ledger
preserves the 17376-event prefix. Workload and guardian cleanup are empty.
Final CPU accounting is 45059.217955206 / 53640; this continuation charges
2664.409180444 CPU seconds. Reporting retains
466.729267256 seconds, unavailable for automatic retries. Delivery passes
166 documentation pages/internal links, exact source/evidence preservation and
diff hygiene. Every workload and guardian cleanup receipt is empty. Final closed
journal: artifacts/gpup-tensor-warp32-v1/cpu-journal-funded-final-v28.json.
Exact accounting: docs/benchmarks/data/tensor-warp32/funded-final-cpu-accounting-v1.json. No host/container
or supervisor change, bootstrap rerun, commit, publication or merge occurs.
Report: docs/benchmarks/lp-tensor-warp32-funded-gpup8.md.
Failure receipt: docs/benchmarks/data/tensor-warp32/funded-profile-refusal-v1.json.

## GPUP-8 approved fully funded continuation (2026-10-24)

The user approves 10400 additional CPU seconds and 850 GPU seconds reallocated
from GPUP-8's existing allowance. CPU ceiling 53640; warp32 GPU cap 1640,
including all prior charges, with acceptance/profiles/timings caps 330/320/990.
Prospective CPU allocations are implementation 200, sanitizers 1000, profiles
2400, timings 6400, reporting 600 and restricted termination margin 400.
Active journal: artifacts/gpup-tensor-warp32-v1/cpu-journal-funded-continuation-v26.json.

Reuse all passed checks and exact verification receipts. Artifact-only adapters
must pass focused acceptance and exact source/provenance admission first. Run
only initcheck and synccheck, then the frozen sixteen profiles and conditional
sixty timings, in separate CPU reservations. Original scientific criteria,
source/image identities and every historical charge remain unchanged. Preserve
the exact 17376-event GPU prefix. No automatic retry, implicit transfer, host or
container change, supervisor change or bootstrap rerun. GPUP-9 remains gated.
Likely writes: artifact adapters/journal/receipts, new budget policy, reports and
task documentation. Accepted plan: docs/plans/lp-tensor-warp32-funded-continuation.md.

## GPUP-8 deadline recovery result (2026-10-24)

Final result: all twelve fixed-work/replay pairs and all 24 independent endpoint
verifications pass; ordinary/project-unit tests and software/inventory acceptance
were reused, not rerun. The resumed project and memcheck/racecheck pass. Initcheck
is refused before reservation because its required 36 GPU seconds exceed the
remaining 33.578641790 acceptance seconds. Synccheck and all 76 study
cells remain unexecuted. The full 3600-worker-CPU-second failure charge is retained.

The separately funded CPU report passes with no verification errors, and 164
documentation pages/internal links plus diff hygiene pass. All cleanup is empty.
This recovery adds 160.386137810 GPU seconds; combined warp32 consumption is
256.421358210 / 790, entirely within the 290-second acceptance cap.
GPUP-8 total is 1119.629822756 / 3000; campaign total is
22479.215678545 / 25202.574545061. The exact 17376-event ledger
preserves both the 17370-event and 17366-event prefixes. Final CPU is
42394.808774762 / 43240; this recovery charges 3663.609175120 CPU seconds.
Reporting retains 213.895961888 CPU seconds; worker headroom is zero.
Exact accounting: docs/benchmarks/data/tensor-warp32/deadline-final-cpu-accounting-v1.json.
Final failed/closed journal:
artifacts/gpup-tensor-warp32-v1/cpu-journal-deadline-final-v25.json.
All historical sources, frozen requests, failures, images and charges remain.
No numerical/latency relaxation, automatic retry, implicit phase transfer or
local commit occurs. GPUP-8 remains incomplete; GPUP-9 stays gated.

The approved deadline continuation has finished its bounded attempt. See
 docs/benchmarks/lp-tensor-warp32-deadline-recovery-gpup8.md and the separate
machine report for exact status. All earlier failures/charges and passed checks
remain preserved; no full software or inventory rerun occurs. Scientific work
stops at the recorded failure/refusal or completed sequence; all original
completion criteria and the combined 790-GPU-second cap remain unchanged.
Final accounting follows supervisor finalization. GPUP-9 remains gated.

## GPUP-8 deadline relaxation selected; CPU funding pending (2026-10-24)

The user authorizes reasonable operational deadline relaxation. Selected:
180 seconds for the remaining project acceptance actions, 60 seconds for final
reporting. Numerical and completion criteria and the 790-second GPU cap remain
unchanged. Passed checks and all failed charges are retained. Worker CPU funds
are exhausted. The concrete proposal requests 3600 new CPU seconds plus unused
implementation/native/reporting reallocation; prospective ceiling 43240. Funding
is unaccepted, so no scientific execution resumes. See
 docs/plans/lp-tensor-warp32-deadline-recovery.md.

## GPUP-8 inventory complete; project acceptance timed out (2026-10-24)

Final metadata delivery validates the inventory/composite, all fifteen completed
verification bindings, exact ledger/prefix and 162 documentation pages/internal
links plus diff hygiene. It does not replace either failed gate or complete the
sixteenth endpoint verification. Final CPU is 38710.817591066 / 39640;
this adapter recovery charges 4097.609224304 CPU seconds with all historical
charges preserved. Reporting retains 23.730196880 CPU seconds,
unavailable for automatic retries. Exact accounting:
 docs/benchmarks/data/tensor-warp32/native-final-cpu-accounting-v5.json.
Final failed/closed journal:
artifacts/gpup-tensor-warp32-v1/cpu-journal-inventory-device-final-v20.json.
All cleanup is empty. The exact 17370-event ledger and historical 17366-event
prefix verify unchanged after delivery. No local commit occurs.

The approved adapter correction and 36-worker-CPU-second transfer pass six new
focused checks and exact provenance admission. All four compile-only device
suites and explicit composite acceptance pass without rerunning passed software
checks. The frozen source/archive and all prior failed reservations remain exact.

All 66 ordinary device tests pass. The project unit suite passes 280 product
pairs, five controller comparisons and 32 warp32 bit/refusal witnesses, then
hits its unchanged 60-second deadline during fixed-work/replay acceptance.
Seven of twelve required pairs have complete host-verification receipts; an
eighth pair is retained with its replay verification incomplete. Sixteen
endpoints and fifteen completed verification receipts remain. No sanitizer,
profile or timing follows. The separate CPU-only final-report attempt also
reaches its deadline; no complete final verification report is claimed. Preserve
both failed sources/receipts and full charges: workers 3964, reporting 64 CPU
seconds. All workload/guardian cleanup is empty.

New GPU charge 96.035220400 / 790 seconds; GPUP-8 959.243684946 / 3000;
campaign 22318.829540735 / 25202.574545061. The 17370-event ledger SHA-256 is
2dac176a925a0bba6096eea8f57ed694465c0199625d120eeb32d468310dc4e4,
preserving the exact 17366-event prefix. CPU at worker stop is
38616.699832818 / 39640; at reporting stop 38684.699832818. Final metadata
accounting follows. Scientific stages are closed; no automatic retry, implicit
transfer or criterion relaxation. GPUP-8 remains incomplete; GPUP-9 stays gated.
Report: docs/benchmarks/lp-tensor-warp32-inventory-device-gpup8.md.

## GPUP-8 inventory admission stops before compilation (2026-10-24)

Final CPU-only delivery passes exact failure/source/receipt/budget checks,
161 documentation pages/internal links and diff hygiene. No passed software
check is rerun. Final cumulative CPU is 34613.208366762 / 39640;
this continuation charges 104.152044872 CPU seconds, retaining all
prior charges. Reporting retains 117.847955128 CPU seconds;
unused funds do not authorize an automatic retry. Final failed/closed journal:
artifacts/gpup-tensor-warp32-v1/cpu-journal-inventory-admission-final-v16.json.
Exact accounting: docs/benchmarks/data/tensor-warp32/native-final-cpu-accounting-v4.json.
Workload/guardian cleanup and diagnostic/delivery cleanup are empty. Fresh hashing
confirms the unchanged exact 17366-event GPU ledger. No commit occurred.

The approved 2500 CPU-second increase and proposed reallocation are recorded:
cumulative ceiling 39640, continuation allocation 9840, unchanged 790 GPU cap
and completion criteria. All covered sources match the passed 1137-file archive;
only 15 exact metadata paths differ. Eleven new adapter checks pass, then
provenance admission fails on the adapter's assumption that extracted Cargo
packages contain .cargo-checksum.json. Charge the full 64 CPU seconds. This is
an adapter assumption error, not an observed dependency or numerical failure.
Post-stop CPU-only diagnosis verifies all 26 retained locked crate archives and
every extracted member; all 26 lack that metadata file. A separate correction
draft is unexecuted. No inventory command, composite acceptance, freeze or GPU
work occurs, and no passed software check is rerun. Both cleanup receipts are
empty; the exact 17366-event GPU ledger is unchanged. CPU at setup stop is
34581.056321890 / 39640; reporting charges follow separately.

Scientific stages are closed; no automatic retry or implicit transfer. GPUP-8
remains incomplete; GPUP-9 stays gated. Preserve all failed sources and charges.
Report: docs/benchmarks/lp-tensor-warp32-inventory-admission-gpup8.md. The separate
unaccepted recovery proposes a 36-worker-CPU-second transfer, no new CPU budget,
one corrected admission and the unchanged inventory/device/completion sequence.
See docs/plans/lp-tensor-warp32-inventory-admission-recovery.md.

## GPUP-8 availability fixed; inventory deadline stops recovery (2026-10-24)

The user-approved 1240 additional CPU seconds are recorded: cumulative ceiling
37140, continuation allocation 7340, unchanged 790-GPU-second cap. The CUDA
availability tests now distinguish initialization from version-query failures;
the actual availability test and four new mocked Rust cases pass. Eight source-
bridge checks pass. Production driver/numerical bytes and historical CPU evidence
remain exact through the separate test-only source bridge.

Every tools/check.sh command passes on source
267c5b7488482ea9005f359e367dcff2b97f363fe2e9ffd7b6008db5cb897138:
Clippy, Rust/native, 424 Python tests, dependencies, replay, 157 documentation
pages and CPU smoke. The complete source tree is archived. The supervisor then
reaches its 298-second work deadline before compile-only device inventory
completes. The combined native/resource gate is refused; its full 1200 CPU
seconds remain charged. No complete inventory, freeze, device acceptance,
sanitizer, profile or timing follows. No numerical failure is inferred.

Both workload and guardian cleanup are empty. The exact 17366-event GPU ledger
remains 9142829b3be8afdb1865425c83ca9122371284ca0e16f7bc8b18d303a5894426;
GPUP-8 remains 863.208464546 / 3000 GPU seconds. CPU at the native stop is
34458.336534342 / 37140; final CPU-only delivery is separately charged.
Scientific stages are closed. No automatic retry, implicit transfer, bootstrap
rerun, host/container change, supervisor change, numerical/latency relaxation,
commit or GPUP-9. Preserve every prior failure/source/image/journal/report.
See docs/benchmarks/lp-tensor-warp32-availability-recovery-gpup8.md and
 docs/benchmarks/data/tensor-warp32/native-refusal-v3.json.

Final CPU-only delivery passes exact failure/source-archive/ledger checks, 158
documentation pages/internal links, CPU smoke and diff hygiene. Cumulative CPU is
34492.792106322 / 37140; this availability recovery charges
1263.732468604 CPU seconds, retaining all prior charges.
Reporting retains 25.307512328 CPU seconds, unavailable for an
automatic retry. Final failed/closed journal:
artifacts/gpup-tensor-warp32-v1/cpu-journal-availability-final-v11.json.
Exact accounting: docs/benchmarks/data/tensor-warp32/native-final-cpu-accounting-v3.json.
Native and delivery cleanup are empty. No new GPU work or commit occurred.


## GPUP-8 corrected native gate stops at driver availability (2026-10-24)

The approved 1200-native/40-reporting transfer is recorded and the one new
native gate runs once. Clippy passes, but the existing CUDA driver-availability
test rejects an error from driver_version while the native wrapper hides all
CUDA devices. Source inspection identifies an unhandled Driver error path;
the exact driver call/status is absent from the failure log. No numerical
failure is inferred. The full 1200 CPU seconds remain charged. No complete
native/Python integration gate or compile-only inventory passes, and no GPU
work, frozen study, bootstrap rerun, host access or container change occurs.
Cleanup is verified empty. Scientific stages are closed under ADR-0045; there
is no automatic retry or implicit transfer. GPUP-8 remains incomplete and
GPUP-9 stays gated. The exact 17366-event GPU ledger is unchanged.

At the native stop cumulative CPU accounting is 33196.332668818 / 35900.
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
 Failure receipt:
`docs/benchmarks/data/tensor-warp32/native-refusal-v2.json`. Preserve all prior
native failures, sources, journals, images, endpoints and reports.

## GPUP-8 approved native recovery (2026-10-24)

The user explicitly approves one new full native gate after the retained
one-line fixture correction, transferring 1200 unspent worker CPU seconds to
native acceptance and 40 to reporting. All prior failures and charges remain.
Active journal: artifacts/gpup-tensor-warp32-v1/cpu-journal-native-recovery-v6.json.
Continuation allocations including charges are implementation 258, proofs 800,
native 2400, workers 2052, reporting 190 and margin 400 CPU seconds, total 6100.
Cumulative CPU accounting after bounded authorization bookkeeping is
31996.332668818 / 35900. Run the approved 1200-CPU-second native gate once.

If every native check and compile-only inventory passes, freeze all behavior
and run the existing conditional device sequence under the 2052-worker-CPU-
second envelope and 790-GPU-second cap (290 acceptance, 200 profiles, 300
timings). Select this active journal at runtime before worker admission; keep
the verification-cache helper source unchanged. Preserve the exact 17366-event
GPU prefix and every historical source, image, journal and report. Per-job
CPU/GPU admission and the frozen forecast/resource-fit rules can refuse early.
No host access, bootstrap rerun, supervisor change, unrelated-process signals,
container configuration change, numerical/latency relaxation or automatic retry.
GPUP-8 remains incomplete until every unchanged completion criterion passes;
GPUP-9 stays gated. The accepted plan is
[the native recovery](../docs/plans/lp-tensor-warp32-native-recovery.md).

## GPUP-8 warp32 native-gate final handoff (2026-10-24)

The corrected image passes 88-register/zero-spill admission and 592 independent
bit/refusal cases. All 48 eight-model CPU cells are retained, 24 endpoints
independently verify, and all twelve required dense configurations admit useful
400-update trajectories. Ten launcher/harness tests pass. The full native gate
fails Clippy on a redundant i32 cast in the new device fixture: charge all 1200
CPU seconds and retain the original source/failure. The one-line fix preserves
all admitted numerical-source hashes. Targeted format, 155 docs pages, CPU smoke
and diff checks pass; a full native pass remains unclaimed. No new GPU work,
resource-bootstrap rerun, host access, container change or commit occurs.

Final CPU accounting is 31980.332668818 / 35900; continuation charge is
2225.626854560. Reporting retains 12.490053208 CPU seconds. Exact receipt:
docs/benchmarks/data/tensor-warp32/native-final-cpu-accounting-v1.json. Final
failed/closed journal: artifacts/gpup-tensor-warp32-v1/cpu-journal-native-handoff-v5.json.
All cleanup is verified empty. The exact 17366-event GPU ledger stays unchanged.

The proposed native recovery transfers 1200 native and 40 reporting CPU seconds
from workers, leaving 2052 worker CPU seconds, under the unchanged 6100 total,
35900 ceiling, 790 GPU cap and completion criteria. It is unaccepted; no repeated
native gate or GPU reservation is authorized. GPUP-8 stays incomplete and GPUP-9
stays gated. See docs/plans/lp-tensor-warp32-native-recovery.md.

## GPUP-8 final warp32-launch handoff (2026-10-24)

GPUP-8 remains incomplete. The isolated correction is written but uncompiled.
Compiler launch fails because replaced PATH hides Python: charge 108 CPU seconds.
CPU-only delivery passes four mocked launch tests, exact historical preservation
and 153 docs pages; smoke then cannot find rustc: charge its full 100 CPU seconds.
No smoke retry, completed final gate or numerical acceptance is claimed. All
project cleanup is verified empty; no new GPU execution, bootstrap rerun, host
access, container configuration change or commit occurs. Final CPU accounting is
30008.459145450 / 35900. New continuation CPU charge is 253.753331192 seconds.
The final failed/closed accounting journal is
artifacts/gpup-tensor-warp32-v1/cpu-journal-accounting-v3.json; exact receipt is
docs/benchmarks/data/tensor-warp32/final-cpu-accounting.json. Reporting retains
42 CPU seconds, unavailable for automatic retries. The separate recovery plan
proposes one corrected compiler invocation and transfer of 108 unspent worker
CPU seconds to implementation, with all charges, criteria and the 790-GPU-second
cap preserved. It is unaccepted; scientific stages remain closed.

Current GPUP-8 disposition: the corrected in-container supervisor passes 26 checks
and the pre-device native gate passes 405 Python tests plus Rust/native,
dependencies, replay, 149 docs pages and smoke. The bounded device continuation
then stops at an INT8 controller reference mismatch. All 66 ordinary GPU tests
and 280 product pairs pass; profiles/timings remain unrun. The
[device-stop report](../docs/benchmarks/lp-tensor-cost-device-gpup8.md) retains the
38.094432271-second charge and every prior failure. GPUP-8 remains incomplete;
GPUP-9 is gated. No bootstrap rerun, host access or device retry follows.

The dated bootstrap/planning notes below remain historical.

[Revised ADR-0044](../docs/decisions/ADR-0044-tensor-cost-continuation.md) and its
CPU allocation are accepted. The in-container supervisor's first bootstrap
refuses before workload release on a missing Python pidfd binding. The portable
repair has four mocked regressions; a corrected bootstrap awaits authorization
under the no-automatic-retry rule. No numerical/GPU work or native gate runs.
GPUP-8 remains incomplete; historical evidence and the ledger are preserved.

[ADR-0044's proposed in-container amendment](../docs/decisions/ADR-0044-tensor-cost-continuation.md)
specifies a cooperative CPU supervisor, explicit memory/cleanup limitations and
16000 CPU seconds to finish the bounded package, requiring 14300 additional CPU
seconds. Numerical/latency criteria and the 1806-GPU-second study are unchanged.
The amendment awaits acceptance; no implementation or experiment has started.

[GPUP-8's revised Kubernetes plan](../docs/plans/lp-tensor-kubernetes-constraint.md)
stays inside the existing container. Its read-only cgroup controls cannot satisfy
ADR-0044, and the CPU admission/reporting stages are exhausted. Execution remains
blocked; the additional 3600-GPU-second offer is unreserved and does not remove
the CPU prerequisite. GPUP-8 remains incomplete; no experiment is launched.

[Approved ADR-0044 resource admission](../docs/benchmarks/lp-tensor-cost-gpup8.md)
refuses because delegated CPU/memory containment is unavailable. No preparation
or GPU reservation runs. GPUP-8 remains incomplete and requires a host-provided
task enclosure before further admission. All historical evidence is preserved.

[GPUP-8 latency diagnosis](../docs/benchmarks/lp-tensor-latency-diagnosis.md) is
complete on CPU. Its bounded cost proposal was subsequently accepted as
[ADR-0044](../docs/decisions/ADR-0044-tensor-cost-continuation.md); the resource
admission refusal above prevents further execution. GPUP-8 remains incomplete.

[GPUP-8 residual continuation](../docs/benchmarks/lp-tensor-residual-gpup8.md)
now qualifies useful INT8/FP16/BF16 solves on both dense models: 60/60 timings
certify overall, twelve full profiles and 120 LP records verify. All six adjusted
latency comparisons fail, and initial CPU preparation concurrency is uncertified;
GPUP-8 remains incomplete. The original evaluation
below remains historical; GPUP-9 is unstarted and no preset follows.

[GPUP-8](../docs/benchmarks/lp-tensor-gpup8.md) retains its bounded implementation
and evaluation under ADR-0042 but remains incomplete. INT8/FP16/BF16 operators
pass device/replay/sanitizer gates, while useful solve windows are CPU-refused.
All 20 admitted FP64 timings certify (20/60 planned), four profiles finish and
128 LP records verify. GPU charge is 236.856927634 seconds; no working-family
solve/gain gate or supported preset follows. GPUP-9 remains unstarted.

The combined GPUP-7/7R [PR review](../docs/benchmarks/lp-quant-pr-review.md)
strengthens operator immutability, malformed-window rejection, strict evidence
and profile eligibility. Its CPU-only source bridge and acceptance remain separate
from both measured studies; no GPU execution or allowance is added.

[GPUP-7R resident execution](../docs/benchmarks/lp-quant-resident-gpup7r.md) is
complete under accepted ADR-0041, preserving the
[original GPUP-7 evaluation](../docs/benchmarks/lp-quantization-gpup7.md).
All 36 admitted fresh timings certify (36/108 planned coverage), all three FP64
profiles reach 2000 logical updates and 21 operator endpoints verify. The six
quantized candidates have no useful-low CPU admission on eight models; 78
dependent timing/profile cells remain refused without replacement. Resident
matched FP64 recovers coverage but tuned FP64 stays faster on nontrivial models.
No quantized solve benefit or supported preset follows.

Full native, ordinary/new device, 29 fixed-work/replay pairs and four scoped
sanitizers pass. Fresh CPU verification accepts all 313 LP and 21 operator
endpoints. Task charge is 245.686586823 GPU seconds, cumulative
21359.585855789 / 25202.574545061, with every ceiling unchanged and the exact
historical ledger prefix retained. GPUP-8 needs its own conditional disposition
and contract; unused allowance reserves nothing. Local delivery is recorded in
[active task](../state/active-task.md).

The repository implements the C8 local extension registry on top of the C5
flow-shop scheduling slice, the C4
agent-independent run surface, C3
extension safety, C2 owned branch-and-bound search, C1 pinned HiGHS solving, M1
model and candidate validation and the M0 bootstrap. Acceptance
evidence is recorded in [active task](../state/active-task.md).

The [2026-09-30 low-precision research analysis](../docs/plans/lp-low-precision-research-2026-09-30.md)
preserves historical evidence and research guidance. The
[2026-10-12 precision architecture](../docs/plans/lp-precision-architecture-2026-10-12.md)
adds component motivations, exact encoding and algorithm designs, SPEC-0020/0021,
and an isolated/interaction experiment plan. GPUP-REP is complete under ADR-0034
and the accepted CPU subset of SPEC-0020: independent exact storage, binary64 and
64-significand-bit arithmetic oracles plus bounded layout receipts.
[GPUP-EXEC](../docs/benchmarks/lp-exact-executor-gpup-exec.md) is complete under
ADR-0035: bounded exact sparse products, 108 retained attempts, 94 independently
verified endpoints and 58/96 certified timings. No total-cost win or preset is
selected. [GPUP-STATE](../docs/benchmarks/lp-expansion-state-gpup-state.md) closes
with ADR-0036's resource admission refusal: the first full-bin FMA primitive uses
255 registers and nonzero spills in both expansion formats. PR 19's compact
full-range FMA passes at 40 registers and zero spills, with 5900 additional
independent cases per construction and host UBSan checks. All 6170 device cases,
four scoped sanitizers and 36 primitive timing attempts pass on RTX PRO 6000
Blackwell. The blocked 5090 attempt and receipt-reader repair remain visible;
combined charge is 30.114068273 seconds. No full controller, state/replay or
solver benefit is admitted. [GPUP-REFINE](../docs/benchmarks/lp-refinement-gpup-refine.md)
is complete under ADR-0037/0038: native FP64 correction state, guarded FP32 sparse
products, sticky recovery and strict replay. All 108 attempts remain, 48 endpoints
verify and 30/96 timings certify. Refinement certifies only initially solved
small-4 without device work; other cells refuse or time out. No product benefit
or preset is selected. Full native, 66 ordinary device tests, 1920 refinement
product checks, nine replays and four scoped sanitizers pass. The telemetry
refusal and CPU report-reader correction remain visible. Task GPU charge is
1541.719136512 seconds; cumulative 19207.265220123 / 21602.574545061 seconds.
The 16684-event ledger preserves every historical prefix and phase cap.
[GPUP-ASSESS](../docs/benchmarks/lp-assessment-scheduling-gpup-assess.md) is complete
under ADR-0039: fixed_200/bounded_800 assessment scheduling preserves the numerical
controller and original-model host authority. All 60 attempts remain, 57 endpoints
verify and 24/48 timings certify. Six common-trajectory pairs match bitwise; full
native, 66 ordinary/three new device tests, six fixed-work pairs/twelve replays
and four scoped sanitizers pass. A scoped 1.0272x FP64 irregular-32768 gain leaves
coverage unchanged; no preset is selected. CPU-only signed-zero replay/profile
review retains the original workers/report and verifies all 57 available endpoints.
Task charge is 523.674592721 GPU seconds; cumulative consumption is
19730.939812844 / 21602.574545061 seconds. The 16816-event ledger SHA-256 is
dd5d7281a152d8fb56df373d913ac2dc7077aac9cf6ba2eb5f6e7781493ea52c, preserving every
historical prefix and phase cap. GPUP-7's contract is next, with no resource
reservation or new numerical behavior implied.

| State | Features |
| --- | --- |
| Implemented | LP-only frozen study infrastructure, independently certified endpoints and a development baseline (GPUP-2), a backend capability declaration a caller cannot widen, a first-order linear programming method with a host-side certified dual bound, host and device backends for it, first-order LP kernels in f64 whose reduction order is fixed so a result cannot depend on scheduling, Original linear models, Rust/JSON/CLI candidate validation with explicit tolerances, backend-neutral solve contract, pinned CPU HiGHS LP/MILP solving with validated incumbents and reproducible records, owned branch-and-bound executive with budgets, cancellation and proof completion, extension runtime with declared authority, validated candidate producers and checked search advisers, typed extension failure records, CLI search over the executive with provenance-bearing run records and re-execution verification, flow-shop instances with an independent makespan recurrence, a big-M-free positional encoding, deterministic NEH and insertion producers, a frozen generated Taillard development subset and CLI scheduling commands, a local extension registry resolving a named identity to an extension this build provides with checked licenses, authority, compatibility, requirements and promotion, a reusable conformance suite and its record, workspace, CLI hello, GPU discovery, simulated leases, artifact schemas, CI and documentation tooling |
| In progress | GPUP-8 working-family/gain qualification; bounded result retained |
| Planned | GPU LP precision track (GPUP-8 revised admission, then GPUP-9/10; full expansion state remains gated), adaptive research (C7), Python SDK (C9), comparative runner (C10); full MILP performance is a later track |
| Experimental | Bounded research assessment scheduling under ADR-0039; bounded native-FP64-outer correction LPs and guarded FP32/anchored products under ADR-0037; bounded exact-dot cached/uncached CUDA executor under ADR-0035; opt-in cuda-lp-matched shared FP64 control and cuda-lp-tuned explicit residency/reduction/fusion execution plus explicit FP32 comparisons with fixed FP64 correction and opt-in adaptive audit/recovery policies and isolated COPT CPU/GPU PDLP controls; feature-gated exact scaling and component sparse research; independently checked versioned endpoints, no supported precision recipe |
| Deprecated | None |

GPUP-0 has saved the [precision roadmap](../docs/plans/gpu-lp-precision-roadmap.md),
draft specifications, design ADRs, and dependency-ordered tasks. GPUP-1 repairs
host certification and objective/gap arithmetic in both LP backends, with independent
exact-rational regressions. GPUP-2 implements measurement infrastructure and the
[development baseline](../docs/benchmarks/lp-baseline-gpup2.md): 144 trials,
173.148261443 GPU seconds. GPUP-3 adds the shared resumable FP64 controller,
bit-preserving certification optimization and schema/activity repairs. Its
[matched study](../docs/benchmarks/lp-matched-fp64-gpup3.md) retains 160 attempts and
27/36 matched CUDA certified timing trials. GPUP-4 implements explicit cuda-lp-tuned
with resident buffers, transfer avoidance, warp32 reduction and fusion. Its
[reviewed report](../docs/benchmarks/lp-tuned-fp64-gpup4.md) preserves a failed first
round and a complete correction, each 320 attempts. All eight configurations retain
27/36 timing coverage. Cumulative study use is 902.574545061 GPU seconds, including
the original 445.988045904; no ledger history was reset. Matched remains the general
reference; fused-warp is provisional only on three named development instances.
Full native/device/scoped sanitizer gates passed. GPUP-5 now extends cuda-lp-tuned
with explicit FP32 settings, fixed charged FP64 correction and separate code identity.
Its [480-attempt report](../docs/benchmarks/lp-fp32-gpup5.md) retains 27/36 timing
coverage for FP64, 12/36 for storage/products/accumulation/master correction and
6/36 for FP32 working state. COPT CPU/GPU PDLP certify 27/36 and 24/36. Total study
consumption after that study was 1324.210639253 GPU seconds. The subsequent
[213-job FP32 diagnosis](../docs/benchmarks/lp-fp32-slowdown-diagnosis.md) adds
143.056235443 seconds, totaling 1467.266874696, with all history preserved. It
separates extra iterations and representation error from executor/correction costs;
no runtime change was made. The subsequent
[GPUP-5B investigation](../docs/benchmarks/lp-exact-components-gpup5b.md) verifies
all 840 attempts and isolates exact power-of-two/factored scaling and component
products behind a research feature. Every new mode recovers 27/36 timing coverage;
component cross-products remain slower on the larger profiled cases. Full native,
device and all four scoped sanitizer gates pass. Its 697.211414922 study plus
70.875589353 acceptance seconds are charged to screening, totaling 2235.353878971
campaign seconds, with original artifacts and ledger prefixes intact. The
[rounding analysis](../docs/benchmarks/lp-fp32-rounding-analysis.md) and
[candidate register](../docs/plans/lp-precision-candidates.md) retain the diagnosis
and future alternatives. The [FP64-pipe root-cause note](../docs/benchmarks/lp-fp64-pipe-root-cause.md)
attributes the component slowdown to the sm_120 FP64 pipe; GPUP-5C acts on it under
[ADR-0022](../docs/decisions/ADR-0022-fp64-pipe-execution-and-tolerance-tiers.md)
with integer-pipe guards, a fused two-launch schedule, double-float FP32 pairs,
explicit tolerance tiers and a frozen development extension; its
[report](../docs/benchmarks/lp-fp64-pipe-gpup5c.md) verifies 806 of 850 attempts,
raising cumulative consumption to 3794.758955639 seconds. Because context creation
and fixed host phases, not arithmetic, now dominate solves, the user pulled
GPUP-THROUGHPUT (repeated-solve throughput with explicit matrix and device reuse)
ahead of GPUP-6 on 2026-09-20. It is complete under accepted
[SPEC-0014](../docs/specifications/SPEC-0014-lp-repeated-solve-throughput.md) and
[ADR-0023](../docs/decisions/ADR-0023-repeated-solve-throughput.md): opt-in tuned
and research sessions pay setup once per batch, and its
[report](../docs/benchmarks/lp-repeated-solve-throughput.md) verifies 687 of 705
admitted attempts with 4785/4785 batch solves bitwise identical to fresh singles,
amortized throughput as a separately labeled endpoint (never single-solve
latency), and cumulative consumption of 6951.059845871 seconds. GPUP-6 is also complete under accepted ADR-0025; its
[adaptive report](../docs/benchmarks/lp-adaptive-gpup6.md) records explicit audits,
rollback, promotion/demotion, independent v5 evidence, complete correctness gates
and retained comparison failures. GPUP-EVIDENCE is complete under SPEC-0015 and
ADR-0027; its [report](../docs/benchmarks/lp-compact-evidence.md) retains 24 fresh
attempts, 15 verified endpoints and 12 certified timings. GPUP-HOST is complete
under SPEC-0016/ADR-0028: its [report](../docs/benchmarks/lp-immutable-host-input.md)
verifies all 28 attempts, certifies 24 timings and preserves all 14 numerical pairs.
One duplicate model reconstruction is removed while every assessment stays fresh.
GPUP-ADAPTIVE-COST is complete under SPEC-0017/ADR-0029; its
[report](../docs/benchmarks/lp-adaptive-host-cost.md) verifies 32 attempts,
certifies 24 timings and preserves all 16 numerical/work pairs. Full native,
regular device, fixed-work/replay and four adaptive sanitizers pass.
GPUP-SETUP is complete under SPEC-0018/ADR-0030: its
[report](../docs/benchmarks/lp-fresh-setup.md) verifies 32 attempts, certifies 24 timings
and preserves 16 equal comparisons. Primary contexts show no consistent latency
benefit and remain study-only. All acceptance gates pass. GPUP-COPT-ADAPTER is
complete under SPEC-0019/ADR-0031: its [report](../docs/benchmarks/lp-copt-adapter.md)
verifies all 84 attempts, certifies 42 timings, and finds this bulk adapter slower
in every certified cell. Twelve readbacks and 24 acceptance endpoints pass. Carry
15804.186067059 / 18002.574545061 GPU seconds and the 15776-event ledger
2b99b615dc77da07fb078e1cefc188d2131db5ca671fe9b86f989a6d660606f0 forward.
GPUP-CONVERGENCE is complete under ADR-0032/SPEC-0013; its
[report](../docs/benchmarks/lp-convergence.md) retains 176 attempts, independently
verifies 174 endpoints and certifies 87/104 timings. No solver behavior or preset
changes. The historical handoff was GPUP-7; the accepted 2026-10-12 order now
selects GPUP-EXEC after completed GPUP-REP. The
[ordered follow-ups](../docs/plans/gpu-lp-precision-roadmap.md#current-follow-up-order-2026-09-27)
separate priority from prerequisites. No supported recipe is available. The
campaign retains its eight GPU-hour cap; acceptance details remain
in the active-task record.

Solve records recompute objectives and violations independently of the backend. A
backend optimality claim holds under the recorded numerical settings; it is not an
exact certificate, and a limit, interruption or failure is never reported as a
completed proof. Owned search adds a second, distinct claim: proven optimality
means the executive exhausted its own node tree with every prune justified by a
relaxation that itself proved optimality. A search whose relaxation hit a limit
forfeits that claim and says so. Extensions may propose candidates and search
actions; the core validates every one of them, and no extension can forfeit a
proof, end a search or change its outcome. Extension containment covers panics,
not a process abort. A search is recorded with the revision, model fingerprint
and input hashes needed to repeat it, and verification re-runs that search from
the record alone rather than trusting its stored result; agreement establishes
determinism on one host, never optimality, and a forfeited search stays forfeited
after it verifies. No Python SDK, dynamically
loaded native extension, persistent checkpoint restart or general comparative experiment runner is
available. Cross-host reproducibility is untested; the development baseline
reports measured costs and coverage without a general solver superiority claim.

The registry decides which extensions a search may consult and records why. It
resolves a named identity to an extension this build already provides and refuses
one it does not; it never loads a separately distributed native component, which
would need a second unsafe boundary ADR-0003 prohibits. An entry is a claim and the
extension's own declaration is authoritative, so a disagreement between them is
refused in both directions rather than reconciled. Resolution is total: a search
either registers every extension its configuration named or does not start.
Promotion means a recorded conformance suite passed, checked against the cited
record's bytes; it never means the extension improves a search, which stays a C7
question and is deliberately unmeasured. A registry-backed run record is now
verifiable by re-execution, which is the gap C5 recorded.

The flow-shop slice adds the first application workload whose objective has a
second, independent computation: a makespan recurrence that shares no code with
anything proposing a schedule. An instance is encoded into an ordinary model with no
big-M constant, so every earlier contract carries it unchanged. It claims
correctness, not tractability: the encoding's linear relaxation is weak, proven
optimality is asserted only for tiny instances checked against exhaustive
permutation enumeration, and the frozen Taillard subset carries feasibility and
determinism evidence only. No best-known bound is committed as a threshold.

C6 is implemented. Two contracts make it up:
[heterogeneous computation](../docs/specifications/SPEC-0010-heterogeneous-computation.md)
fixes device selection, residency, batching, arithmetic width, fallback,
cancellation, recovery and equivalence, and a
[GPU LP backend](../docs/specifications/SPEC-0011-gpu-lp-backend.md) adds a
capability declaration to the solve contract so a caller reaching a backend that
cannot solve its model is refused rather than answered. Neither grants a device any
mathematical authority. A device-produced candidate is validated against the original
model like any other, and an approximate LP iterate becomes a dual bound only through
a host-side certification that treats the device's output as an untrusted guess; a
bad guess is required to yield a weak bound or no bound, never an invalid one.
GPUP-1 repairs the [reduced-cost cancellation defect](../state/known-failures.md#lp-certification-can-lose-the-roundoff-allowance-at-zero-reduced-cost)
with outward arithmetic and a shared, sense-aware objective/gap check. See the
[numerical argument and conservative limits](../docs/architecture/lp-certification.md).

Both are implemented. Two kernels evaluate
flow-shop schedules in 32-bit integer arithmetic and agree with the host recurrence
exactly rather than within a tolerance, which is available only because the
arithmetic is integer. A search selects a device in its configuration, registers a
device-backed candidate producer, and writes a record that names the hardware and
re-executes on it; when the device declines, the host computes the same
neighbourhood and the proposals are identical. A first crossover is measured: the
device loses below roughly fifty jobs and context creation costs about 148
milliseconds, so the CPU remains the default and residency is what makes a device
worth reaching.

The linear-programming half adds a second and a third backend behind the same
contract, selected only by an explicit `--backend`. A restarted primal-dual method
runs on the host or on a device, and in both cases everything it is permitted to claim
is computed on the host: the candidate is validated against the original model, and a
dual bound exists only where a host-side certification builds one from the model's own
coefficients. That certification reads no residual the device computed, which is what
stops it checking the device against itself, and it is valid for an arbitrary
multiplier vector -- a bad guess yields a weak bound rather than an invalid one. The
device's iterates agree with the host engine's bit for bit, which is stronger than the
contract asks and is recorded as this project's property rather than a guarantee.

No performance claim is made. The crossover is a development diagnostic on one host
and no default consults it, so "CPU below the crossover" holds because CPU is the
default everywhere rather than because anything measured. Each remaining gap is
recorded in [known failures](../state/known-failures.md) rather than implied by the
parts that work.

See the [M1 contract](../docs/specifications/SPEC-0001-model-and-validation.md),
[backend contract](../docs/specifications/SPEC-0002-backend-contract.md),
[solver executive contract](../docs/specifications/SPEC-0003-solver-executive.md),
[extension runtime contract](../docs/specifications/SPEC-0004-extension-runtime.md),
[run surface contract](../docs/specifications/SPEC-0005-run-surface.md),
[flow-shop contract](../docs/specifications/SPEC-0008-flow-shop.md),
[extension registry contract](../docs/specifications/SPEC-0009-extension-registry.md),
[heterogeneous computation contract](../docs/specifications/SPEC-0010-heterogeneous-computation.md),
[GPU LP backend contract](../docs/specifications/SPEC-0011-gpu-lp-backend.md),
[backlog](../state/backlog.yaml) and
[implementation plan](../implementation-plan.md) for evidence stages and dependencies.

GPUP-COPT is complete under ADR-0026. Its [component-cost report](../docs/benchmarks/lp-copt-comparison.md)
retains all 1140 attempts, independently verifies 948 endpoints and certifies
402/816 primary timings. Evidence output at 65536 rows and COPT graph internals
remain explicit gaps; no winner or preset is selected. Task charge is
5853.941357570 GPU s; cumulative 14766.435441716/18002.574545061 s.
The 15340-event ledger SHA-256 is
5cf76ffbea09e21fdf21692c4030f8176ae5ef7f481c2e5c6e83fe302371b51b,
preserving the 13056-event prefix and every phase cap. Performance repairs ranked
in the report are ordered in the roadmap and backlog; GPUP-EVIDENCE and GPUP-HOST
are complete, as are GPUP-ADAPTIVE-COST and GPUP-SETUP. At setup completion, consumption was
15632.281207415 / 18002.574545061 GPU s. The 15606-event ledger SHA-256
ad3d84354f0b74ae62fcc019ee4dcbf29b0a3251d066f1e0f2df11ccb107230b
preserves the 15528-event adaptive-cost prefix and all prior history.
GPUP-7 still needs its accepted contract.

GPUP-CONVERGENCE is complete under accepted ADR-0032/SPEC-0013. Its
[report](../docs/benchmarks/lp-convergence.md) retains all 176 frozen attempts,
independently verifies 174 endpoints and certifies 87/104 timings
and 32/72 diagnostic profiles. Two dense-65536 accumulation-FP32 timings
have no endpoint; every interruption and rejection remains visible, without retries.
Scoped per-proposal savings do not overcome unsuccessful FP32 work; adaptive
reference arithmetic, recovery and original-model assessments remain material.
Full pre/post native gates, 58 regular device tests, twelve fixed-work pairs and
replays, eight COPT min/max/profile endpoints and ten source-only contracts pass.
Runtime, kernels, settings, defaults and historical evidence remain unchanged;
no preset is selected. CPU-only recovery/report review corrections are exactly bound.
Task charge 1311.088550794 GPU seconds: timing
634.748860654/800, profiles 441.911765452/800,
acceptance 234.427924688/300; cumulative 17115.274617853 /
18002.574545061 seconds, with no new allowance. The 16134-event ledger SHA-256
60649d29992d21508e60aa60f3e334e9ac18fe3254525ec38cc0eef298e84823 preserves the
15776-event prefix 2b99b615dc77da07fb078e1cefc188d2131db5ca671fe9b86f989a6d660606f0
and every phase cap. Historical racecheck/session/mixed-model gaps remain open.
That study handed off to GPUP-7; the 2026-10-12 order inserted GPUP-REP, which is
now complete, followed by GPUP-EXEC under ADR-0035. GPUP-STATE closes with the
bounded resource admission refusal and compact FMA review under ADR-0036; GPUP-REFINE is next and
requires its own accepted numerical/resource contract. Current GPU consumption
is 17665.546083611 / 21602.574545061 seconds; the 16452-event ledger preserves
every historical prefix. No supported preset follows.
