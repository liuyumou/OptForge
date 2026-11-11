# Agent Instructions

## RESIDENT2 lessons applied to the roadmap (2026-11-11)

ADR-0054 refines future planning from the completed RESIDENT2 evidence. Keep the
native control. GPUP-MIXED2 remains next ready for CPU-only contract/cost
preparation; quantify the accelerated fraction and all added costs before device
work. GPUP-DELIVERY2 is a planned alternative before precision device work when
its setup/checker/transport cost case is stronger, not an automatic prerequisite.
Cold latency and prepared throughput remain separate. Normal-limit export is
fixed; mixed-model finite-bound authority remains unresolved at original 1e-9.

This is a documentation-only revision, with a separate 256 CPU / zero GPU
envelope and no historical allocation reuse. No scientific task, retry, new
precision default or publication is released. RESIDENT2 stays complete as a
negative result, GPUP-8 incomplete/science closed and GPUP-9 gated. See
docs/plans/gpu-lp-precision-roadmap.md and state/active-task.md for acceptance.

## GPUP-RESIDENT2 completed; latency retention gate fails (2026-11-11)

The requested bounded implementation and comparison are complete under
SPEC-0024 / ADR-0053. Report: docs/benchmarks/lp-resident2-gpup-resident2.md.
All 64 planned cells completed and delivered 96 endpoints. Control and resident
each certify 42/48; all 42 certified pairs have identical candidate bytes and
iteration counts. All twelve mixed-model normal-limit endpoints now export
65536 primal/dual entries and remain uncertified at variable 3's infinite-bound
refusal. The original 1e-9 authority is unchanged.

The candidate uses exact per-window coefficients, u64 sticky flags, bounded
asynchronous submission and transactional host adoption. Prepared lifecycles
reuse immutable preparation with fresh iterates/controller/checking per solve.
The nontrivial trace reduces synchronizations 58 to 44 at the same 2800 launches,
but increases transfer bytes. The cold model-median geometric mean is 1.027370x;
four of seven certified medians regress. The predeclared total-latency criterion
fails, so retain the native control and select no supported preset.

Acceptance: full CPU/native gate (638 Rust tests, 515 Python tests, replay,
dependency/artifact/docs/smoke), separately verified test-only overflow correction,
five focused Python contracts, device boundary/controller/cancellation/rollback,
four independent transport certificates, and all four zero-error sanitizers.
The original overflow fixture and stale-test-binary failures retain their full
charges; all development/native failures remain recorded. Active study reader:
tools/lp_resident2_study_v4.py. No timing cell was retried. Exact sources and old
scientific results/charges are preserved; the six historical source edits have
an exact additive/test-only bridge.

Task GPU charge is 598.631222067 / 1800 seconds, including all failures.
CPU and final cleanup receipts are in the report's acceptance/accounting files,
within the independent 32000-second ceiling. Historical allocations stay closed.
Next ready: GPUP-MIXED2, using the native control; no next-task execution is
released. GPUP-8 stays incomplete and GPUP-9 gated. Local commit after delivery;
no push or publication was requested.


## GPUP-RESIDENT2 implementation (2026-11-11)

The user requests implementation and permits more time as needed. PR #23 is
merged at 4e62cab04ca2236d419c2deea4063a42a4f519ef; the prerequisite is met.
Implement SPEC-0024 / ADR-0053: non-overlapping delivery phases, cold/prepared
immutable model lifecycles, separate native resident FP64 execution with bounded
submission, coefficient tables and sticky device flags. Preserve exact original
coefficients, host controller boundaries, fresh independent certificates and all
historical evidence. Diagnose normal-limit export without changing bound authority.

New task envelope selected under this implementation/time authorization: 32000
CPU seconds (implementation 8000 including 128 preparation, native acceptance
8000, device acceptance 4000, study 8000, reporting 3200, cleanup 800); four CPU
slots, one shared GPU lease, 16 GiB sampled host RSS, 12 GiB device buffer limit.
New GPU ceiling 1800 seconds (acceptance 600, study 1200), independently accounted
in artifacts/gpup-resident2-v1/resources. No historical funds are transferred.
Per-job full reservations must fit; failed/unsettled reservations remain charged.
Use the unchanged in-container supervisor. All jobs stay in this container.
Development fixes retain failed logs and sources; scientific cells have no automatic
retry. CPU/native admission precedes device checks, sanitizer admission precedes
matched study. No GPUP-8 rerun or GPUP-9 release. No push/publication requested.

Acceptance: focused CPU contracts, full tools/check.sh, device differential and
failure/cancellation checks, four scoped sanitizers, frozen same-transport native
control/candidate cold and prepared cohorts with launch/copy counts, independent
endpoint checking, all-cell coverage and total latency decision. Record an honest
negative or blocked result if admission or performance fails. Likely writes:
new research module/kernels/driver/tools/tests/specification/report and task state;
no legacy numerical source or public solver default changes.


## GPUP-BASELINE PR integration (2026-11-10)

PR #23 is ready for the normal merge path. Local composite acceptance passes
634 Rust tests, 512 Python tests, committed-record replay, all 188 documentation
pages/internal links and CPU smoke. The native build, Clippy, dependency and
artifact gates also pass. The initial full-gate failures and all charges remain
preserved; the last documentation failure is resolved by publishing the original
733-byte JSON receipt at its existing ADR link target. No executable/test source
changed after the passing numerical suite. Final acceptance:
`docs/benchmarks/data/external-baseline-pr-local-acceptance-v5.json`.
Hosted Actions still starts no jobs and reports startup_failure; the full local
command coverage is disclosed in the PR. Integration GPU usage is zero.

The user explicitly requests merging the current changes through a PR before
starting the next task. This authorizes commits, push, PR creation and merge;
older no-publication handoffs below describe their original scope. Integrate the
four unmerged GPUP-8 commits and the completed baseline, diagnosis and roadmap.
GPUP-8 remains incomplete and GPUP-9 remains gated; no new GPU study follows.

Acceptance: preserve recorded scientific sources/results and charges, make the
baseline CPU tests reproducible without local benchmark installations, run the
repository CPU integration gate, inspect the complete PR diff and lockfiles,
require passing CPU/docs/smoke checks, then merge and verify main ancestry. Test-only
portability changes retain their exact prior sources and a separate source bridge.
Likely writes: test support/fixtures, CI dependency pins, integration receipt and
current handoff. No vendor binaries, credentials or ignored experiment directories
are published. Local validation is bounded to four CPU slots and 6000 CPU seconds
(including 128 for preparation); GPU allocation is zero. Hosted CI keeps its
existing 30/10/10-minute CPU/docs/smoke deadlines. Historical allocations remain
closed. The full CPU integration gate is newly authorized for this PR; it does
not rerun the GPU campaign or its formal proof/profile sequence.

Local clean-checkout baseline tests pass with no historical study artifacts or
vendor environments. The v3 source bridge preserves 813 frozen runtime files,
eight exact prior test sources and the original requirements manifest. The first
full local gate found 22 historical test-fixture errors; the portable GPUP-8
fixture correction passes all 79 affected/neighboring CPU tests. Both failed
attempts retain their logs and charges in the v4 integration receipt.

Hosted Actions currently returns startup_failure without starting any jobs;
the earlier main CI annotation explicitly reports an Actions budget restriction.
Run the identical full CPU gate and separate docs/smoke commands locally before
normal merging, record the hosted limitation in the PR, and never bypass branch
protection or manufacture a successful hosted status. This operational fallback
implements the user's already authorized merge; no scientific criterion changes.

## GPUP-BASELINE completed with native-return reporting (2026-11-10)

The user authorized completion and counting cuOpt returns without reported errors
as passes while logging differences. ADR-0052 / SPEC-0023 implement that policy
separately from unchanged strict certification. All 240 planned screening cells
now have settled attempts: 123 reused and 117 new. 198 meet their
comparison policy; 135 certify strictly. CuOpt has 90/96 native-return
passes and 24/96 strict certificates. Normal limits remain limits; explicit
NumericalError remains a native failure. Outer failures and missing certificates
remain separate even when a native return passed. Nothing is relabeled optimal.

Report: docs/benchmarks/lp-external-baseline-native-return.md. Full machine rows:
docs/benchmarks/data/external-baseline-native-result-v1.json. Final accounting and
acceptance: external-baseline-native-accounting-v1.json and
external-baseline-native-acceptance-v1.json in the same directory. Total baseline
GPU charge is 3091.995889713 / 3600 seconds, including all prior failures.
The new CPU allocation is separately bounded at 32000; final settled charges are
in the accounting receipt. Historical CPU caps/charges remain closed and exact.

Nine new policy/export tests and one installed Solution API check pass. Prior
hardware/tests/certificates are reused; source/input/settings admission and final
metadata/documentation/cleanup checks are recorded in the delivery receipt.
Versions v1 through v5, their sources, partial native returns and all failed
reservations stay immutable. No old numerical gate/profile was rerun. The
historical 17438-event GPU ledger remains exact. No vendor installation, native
settings, checker mathematics or public solver defaults changed.

GPUP-BASELINE and its follow-up protocol are complete under the amended policy.
Next ready: GPUP-RESIDENT2, with explicit phase attribution and cold/prepared
model lifecycles before claims about faster arithmetic. No new scientific task
or spending is released by this handoff. GPUP-8 remains incomplete and GPUP-9
stays gated. No commit, publication or merge was requested.

## GPUP-BASELINE native-return continuation (2026-11-10)

Status: accepted continuation, now closed by the delivery above; the user requested
to complete the baseline and
accept cuOpt results without vendor-reported error while logging discrepancies.
ADR-0052 and SPEC-0023 supersede the CPU-only handoff and cuOpt certificate gate
for this separate v5 cohort. Strict mathematical certification remains unchanged
and separately reported; native success never becomes certified optimality.

Reuse all 123 settled screening trials and run only the 117 unexecuted cells.
Retain all original models, settings, deadlines, order, failures and charges.
Likely files: new policy/metadata adapter, versioned coordinator/worker/budget,
new focused tests and execution schema, frozen evidence, report and task state.
Acceptance: actual cuOpt error/status metadata, immutable prior bindings, full
240-cell disposition, separate native and strict-quality results, cleanup,
resource accounting and documentation. No historical solver check/profile rerun.

New continuation CPU ceiling: 32000 seconds (implementation 1600 including 128
preparation, screening 28080, reporting 1600, cleanup 720). This is a separate
allocation for the newly requested work; old CPU caps/charges remain historical.
Total baseline GPU cap remains 3600 seconds, including 1277.244626616 already
charged; v5 may reserve 2322 whole GPU seconds. Entire jobs must fit. Four CPUs,
one shared GPU lease and existing memory/output limits remain. No automatic
retry, new vendor installation, native parameter change or GPUP-9 execution.

## GPUP-BASELINE bounded implementation delivery (2026-11-10)

Implementation is delivered; the full scientific comparison remains incomplete.
Report: docs/benchmarks/lp-external-baseline-gpup-baseline.md. Machine summary:
docs/benchmarks/data/external-baseline-result-v1.json. Final accounting and
acceptance: docs/benchmarks/data/external-baseline-final-accounting-v1.json and
external-baseline-acceptance-v1.json in the same directory.

Six configurations/twelve admission suites pass. Of 240 planned screening cells,
123 execute and 108 certify; 96 are blocked by four cuOpt admission failures and
21 remain unexecuted after CPU reservation admission exhausts. Preserve cuOpt
numerical/postsolve refusals, the native failures and all unexecuted cells.
GPU charge is 1277.244626616 / 3600 seconds. CPU screening charges
9775.536859960 / 9860; total baseline CPU ceiling is 16000. ADR-0051's current
phase caps supersede the initial allocation below. Final CPU delivery totals
are in the accounting receipt. No unused phase or GPU headroom authorizes a retry.

Active implementation: tools/lp_baseline_study_v4.py and the buffered research
checker; v1 through v4 sources, artifacts, failed charges and source bridges stay
immutable. The active v4 reuses all admission outcomes and five small-model
blocks; its 33 large-model executions are separate from sixteen retained v3
transport timeouts. The lost-guardian v2 cancellation retains its full 240 CPU
charge and cleanup record. No passed numerical acceptance or historical profile
is rerun. Twenty-five new Python tests and one Rust writer test pass; scoped
format/lint/build and delivery checks are recorded in the report.

Next ready task: GPUP-BASELINE-FOLLOWUP, a CPU-only protocol using retained
records. Specify the exact 21 missing cells (5040 worker CPU / 720 GPU seconds
plus itemized overhead), per-path cuOpt postsolve/quality admission and native
missing-candidate error handling, and cold versus prepared model/evidence costs.
Do not launch those jobs, relax certification or silently transfer funds from
this handoff. GPUP-BASELINE stays in progress; RESIDENT2/MIXED2 remain gated on
its disposition. Historical GPUP-8 is incomplete with scientific stages closed;
GPUP-9 remains gated. The 17438-event historical GPU ledger and original numerical
sources remain exact. No commit, publication or merge is part of this delivery.

## GPUP-BASELINE initial implementation authorization (2026-11-10)

Status: accepted initial allocation, superseded by the delivery above and ADR-0051;
authorized by the user's instruction to implement GPUP-BASELINE
with 3600 additional GPU seconds. Implement separate vendor adapters, a neutral
Rust checker, immutable execution manifests, bounded admission and conditional
screening. Keep all ten lanes and 240 planned screening cells visible. Reuse the
retained numerical libraries and supervisor; do not reopen GPUP-8 or GPUP-9.

Bounds: new baseline GPU cap 3600 seconds (480 admission, 3120 screening),
charged separately without changing the historical ledger. CPU ceiling for this
new work is 16000 seconds, conservatively within the 18036.902496786 seconds below
the existing cumulative ceiling: 2400 implementation, 240 hardware, 2400 adapter
admission, 8960 screening, 1200 reporting and 800 reserved cleanup. Four CPUs,
one foreground job, 16 GiB sampled aggregate host RSS, 12 GiB sampled GPU memory.
This is an explicit allocation for the newly authorized baseline; no prior
failure is refunded or old stage retried. Whole-job reservations must fit before
launch; failed/unsettled jobs retain the full reservation. A partial grid is
reported as partial, never silently reduced to a favorable subset.

Acceptance: new checker/conversion/runner tests; pinned input readback and
min/max/offset/ranged dual mapping; nontrivial original-model certificates and
actual execution evidence; frozen dependencies; cleanup and immutable history.
Likely files: research/lp-external-baseline, new lp_baseline tools/tests/schemas,
ADR-0048, run artifacts/report and task state. No public solver defaults change.


## GPUP-BASELINE-SPEC CPU contract delivery (2026-11-10)

The user explicitly requested GPUP-BASELINE-SPEC implementation. SPEC-0022 and
docs/benchmarks/lp-external-baseline-v1.md now define the comparison, including
three schemas and tools/lp_baseline_contract.py with twenty focused CPU tests.
The non-executable proposal fixes ten lanes/eight development models/240 screening
cells; no held-out manifest is accessed. Gurobi is excluded. Existing Rust external
readers are COPT-specific, so GPUP-BASELINE must add a separate solver-neutral bridge.

Next ready implementation task is GPUP-BASELINE. Phase A proposes 6040 CPU / 480 GPU
seconds; phase B separately proposes 58600 CPU / 10080 GPU seconds. Neither is an
allocation or execution authorization. Freeze actual sources, device, settings,
supervisor and accepted resource authority before numerical jobs; the proposal
validator cannot execute them. Preserve all historical sources/receipts/charges;
no passed GPUP-8 check/profile is rerun. GPUP-8 stays incomplete and GPUP-9 gated.

## System diagnosis and roadmap revision (2026-11-10)

The user requests a saved diagnosis, concrete roadmap decisions and optional
cuOpt installation; Gurobi is unavailable. Current direction is ADR-0047 and
docs/plans/gpu-lp-precision-roadmap.md#current-plan-2026-11-10. Next ready task is
GPUP-BASELINE-SPEC: CPU-only common-checker comparison contract and resource
proposal, followed by separately admitted cuOpt/COPT adapters, resident execution,
simpler mixed precision and conditional Tensor work. This is not GPUP-9 execution.

cuOpt 26.10.0 is installed under artifacts/cuopt-26.10.0-cu13/venv; pip check and
cuopt.linear_programming import pass with GPUs hidden. The package lock and setup
receipt are documented in docs/operations/cuopt.md. Device/solver acceptance is
unrun. COPT and all historical environments are unchanged. No numerical source,
passed scientific check/profile, historical charge or ledger is changed/rerun.
GPUP-8 remains incomplete and its scientific stages closed; GPUP-9 stays gated.
New numerical protocols and resource packages require separate acceptance; unused
historical funds do not authorize retries or transfers. Dated entries below are
historical handoffs, not the current planning priority.

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

## GPUP-8 authorized fixture correction and one proof retry (2026-10-24)

The user authorizes fixture/harness fixes, one corrected proof attempt and
conditional continuation from unused funds. This supersedes the earlier proof
stop only for this recovery. Transfer 100 unused authority CPU seconds to setup
and 1600 unused prototype seconds to the corrected proof reservation; add no
resources. Retain the full 5600-second failed proof charge and all original
sources, corpus, reports and journals. CPU ceiling remains 77640; GPU caps and
every completion criterion remain unchanged.

Active journal: artifacts/gpup-tensor-expanded-v1/proof-recovery-v1/cpu-journal-v5.json.
Authority: docs/benchmarks/data/tensor-expanded/proof-recovery-authorization-v1.json.
Implement versioned generator/harness adapters, canonical-input preflight and
indexed diagnostics. Reuse the source-bound 12 authority and 16 prototype passes;
rerun no passed checks or historical profiles. After the corrected proof passes,
continue the accepted ordered gates. No supervisor/bootstrap/host/container
change. A numerical or resource failure retains its charge and closes later
scientific stages. GPUP-8 remains incomplete until all criteria pass; GPUP-9 stays
gated. Expected writes: correction adapters, focused validation, new receipts,
accounting, and conditional candidate implementation under ADR-0046.

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

## GPUP-8 approved expanded-within-window continuation (2026-10-24)

The user accepts the expanded-window plan and its resource amendment: add 24000
CPU seconds, ceiling 77640, prospective allocation 31600; reallocate 1760 GPU
seconds inside the unchanged 3000-second GPUP-8 and campaign ceilings. Use the
new lp-tensor-expanded-v1 / gpup-tensor-expanded-v1 identities and journal
artifacts/gpup-tensor-expanded-v1/cpu-journal-v1.json. Preserve the exact 17412-event
ledger prefix, all prior sources, binaries, failures, profiles and charges.

Implement expanded working state within at-most-32-update windows, canonicalize
the shared penultimate audit input, and retain FP64 reference adoption and the
200-update host controller/certification boundaries. Scientific criteria stay
unchanged. New candidate gates run once in dependency order; retained passed
checks/profiles are not rerun. A failed formal gate closes scientific execution;
later funds remain unused. No automatic retry, transfer, bootstrap rerun, host or
container change. GPUP-8 remains incomplete and GPUP-9 gated. Cross-window state
persistence is documented future work with no allocation.

Likely additions: separate CPU/reference and CUDA candidate, artifact adapters,
new validation/evidence and ADR-0046. Authority and evidence admission precede
numerical execution. Starting CPU: 45902.541829170; authorization bookkeeping
charges 16 CPU seconds within the 400-second authority stage.

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

## GPUP-8 approved deadline recovery (2026-10-24)

The user approves 3600 additional CPU seconds and unused-fund reallocation.
Cumulative ceiling is 43240; continuation allocation including historical charges
is 13440. Prospective headrooms: implementation 100, workers 3600, reporting 248,
restricted termination margin 400 CPU seconds. All prior failures/charges remain.
Active journal: artifacts/gpup-tensor-warp32-v1/cpu-journal-deadline-recovery-v23.json.
Eight implementation seconds cover preparation and authorization bookkeeping.

Use the accepted 180-second remaining-project deadline and 60-work-second final
report. Reuse passed software, inventory, ordinary/project-unit tests and seven
complete fixed-work/replay pairs. Finish one interrupted replay verification and
four unexecuted large-model pairs, then run all still-unexecuted sanitizers and
the existing conditional profile/forecast/timing sequence. Preserve twelve-pair
acceptance and all 76 study cells. Numerical sources, test/build inputs and the
verification helper remain byte-exact. Separate artifact-only adapters and exact
metadata source bridges must pass focused acceptance before resumed execution.
Likely writes: adapters/receipts/journal, authorization/task state and final report.

Preserve the old frozen source, all requests/failures and every ledger event.
Never relabel an old failed worker as passing. The 790 GPU seconds include the
already charged 96.035220400 seconds; phase caps remain 290/200/300. Per-job CPU,
GPU, forecast/resource-fit gates may refuse and do not authorize borrowing.
All completion criteria remain unchanged. No automatic retry, host/container or
supervisor change, bootstrap rerun, numerical/latency relaxation or GPUP-9.
Accepted plan: docs/plans/lp-tensor-warp32-deadline-recovery.md.

## GPUP-8 user-authorized deadline relaxation (2026-10-24)

Deadline amendment acceptance: retained timing/resource arithmetic, immutable
prior receipts and 17370-event ledger, 163 documentation pages/internal links and
diff hygiene pass. Amendment CPU charge is 20.382008576 seconds; cumulative
CPU is 38731.199599642 / 39640. No worker, compiler, numerical verification or
GPU job ran. Worker headroom remains zero. Final failed/closed journal:
artifacts/gpup-tensor-warp32-v1/cpu-journal-deadline-amendment-final-v22.json.
Exact accounting: docs/benchmarks/data/tensor-warp32/deadline-amendment-accounting-v1.json.
The 180-second remaining-project and 60-second reporting deadlines are selected;
the separate 3600-additional-CPU-second/reallocation proposal remains unaccepted.
All cleanup is empty and every prior charge is preserved.

The user authorizes choosing reasonable operational deadlines. Select 180 work
seconds for the remaining project acceptance actions and 60 work seconds for
final reporting. Preserve all prior failures/charges and passed checks; no
numerical or completion criterion changes. Record settings separately in
 docs/benchmarks/data/tensor-warp32/deadline-amendment-v1.json; never overwrite
the frozen request or reuse its failed identity.

The remaining work is one interrupted CPU replay verification and four unexecuted
large-model fixed-work/replay pairs. The completed large INT8 pair took about
27.423 wall seconds; 180 allows about 1.5 times the observed remaining-work
estimate. Forty-second individual action limits remain. A 60-work-second report
requires 248 CPU seconds under the unchanged supervisor's four-times-wall policy
and two-second work reserve.

Worker CPU headroom is zero after the retained full 3964-second failure charge.
Deadline authorization does not supply additional CPU funds or refund charges.
Use at most 32 existing implementation CPU seconds for this concrete amendment,
resource-fit proposal, documentation and receipt checks; active journal is
artifacts/gpup-tensor-warp32-v1/cpu-journal-deadline-amendment-v21.json.
Likely writes are the separate policy, diagnostic/resource proposal and task
state. No compilation, software-check rerun, numerical verification or GPU job.
Keep the 790-GPU-second cap, all phase caps, scientific gates and exact 17370-event
ledger. Reopen scientific execution only when its required CPU budget is funded.

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

## GPUP-8 approved adapter correction and inventory recovery (2026-10-24)

The user explicitly approves the prepared adapter correction and transfers 36
unused worker CPU seconds to setup. Preserve the original failed adapter and its
full 64-second charge. No additional CPU funds: ceiling 39640, continuation
allocation 9840. New setup headroom 64 comprises 8 preparation, 32 corrected
admission and 24 composition CPU seconds; inventory retains 400, workers 3964,
reporting 117.847955128 and restricted termination margin 400 CPU seconds.
Active journal: artifacts/gpup-tensor-warp32-v1/cpu-journal-inventory-adapter-recovery-v17.json.

Apply only the artifact adapter correction: validate locked crate archive hashes
and every extracted member, rejecting unexpected source files. Run focused new
checks for the correction and exact source/provenance admission once. Reuse all
passed software checks. Run the unchanged compile-only inventory once; after its
resource/cleanup pass, validate a separate composite acceptance, then freeze and
run the unchanged conditional device/profile/forecast/timing sequence. Likely
writes are artifact adapters, receipts/journal, authorization/task state and
post-execution delivery. No covered solver/test/build/harness source edits.

Keep all completion criteria and the 790-GPU-second cap (290 acceptance, 200
profiles, 300 timings). Preserve the exact 17366-event ledger prefix and all
historical evidence. No source edits after freeze, automatic retry, bootstrap
rerun, host/container or supervisor change, numerical/latency relaxation or
implicit transfer. GPUP-8 remains incomplete until every criterion passes;
GPUP-9 stays gated. The accepted proposal is
 docs/plans/lp-tensor-warp32-inventory-admission-recovery.md.

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

## GPUP-8 approved inventory continuation (2026-10-24)

The user accepts docs/plans/lp-tensor-warp32-inventory-continuation.md: add
2500 CPU seconds and explicitly reallocate unused stage funds. The cumulative
ceiling is 39640 CPU seconds; continuation allocation including all historical
charges is 9840. Prospective headrooms are implementation 100, compile-only
inventory 400, workers 4000, reporting 150 and restricted termination margin 400.
All prior charges remain; 35.649492368 assigned seconds remain unused. Journal:
artifacts/gpup-tensor-warp32-v1/cpu-journal-inventory-continuation-v14.json.
Eight implementation CPU seconds conservatively cover authorization bookkeeping.

Validate exact source equivalence and retained provenance using an artifact-only
admission adapter with focused negative checks. Reuse the completed software
receipt and run the unchanged compile-only inventory once, separately supervised;
do not rerun passed checks. Then validate a separate composite acceptance record
and conditionally freeze/run the existing device/profile/forecast/timing sequence.
Likely writes: artifact-only adapter/receipts/journal, authorization and task state,
then separate report/accounting after workers. No covered behavior source edits.

Keep the 790-GPU-second cap (290 acceptance, 200 profiles, 300 timings), all
completion criteria and the exact 17366-event ledger prefix unchanged. No
bootstrap rerun, host/container change, supervisor change, numerical/latency
relaxation or automatic retry. Freeze all source during workers. Any failed gate
stops scientific work; GPUP-8 remains incomplete until every criterion passes;
GPUP-9 stays gated. Preserve all historical evidence and failed charges.

## GPUP-8 proposed inventory-only continuation (2026-10-24)

The completed software gate can be reused subject to exact source-equivalence
admission. Fresh archive comparison finds only eleven documentation/state/receipt
differences; all covered code, tests, harnesses and build inputs remain unchanged.
A separate proposed composite gate must retain the old software pass and failed
resource receipt, complete a new inventory with passing resource cleanup, and
bind both source identities. No prior failure is relabeled or charge refunded.

The proposal requests 2500 additional CPU seconds and explicit reallocation to
5050 prospective headroom: 100 admission/setup, 400 one compile-only inventory,
4000 workers/verification, 150 reporting and 400 termination margin. Proposed
cumulative ceiling 39640, continuation allocation 9840; GPU cap stays 790 and
all completion criteria remain exact. This is unaccepted planning only: no
compiler, native rerun, GPU execution, reopened scientific stage or new resources.
See docs/plans/lp-tensor-warp32-inventory-continuation.md. GPUP-8 is incomplete;
GPUP-9 remains gated. Preserve the exact 17366-event ledger and all old evidence.

Planning acceptance: exact source comparison, integer budget arithmetic, the
unchanged 17366-event ledger, 159 documentation pages/internal links and diff
hygiene pass. Planning charges 16.264215568 CPU seconds; cumulative accounting
is 34509.056321890 / 37140. Reporting retains 9.043296760
CPU seconds. The final failed/closed planning journal is
artifacts/gpup-tensor-warp32-v1/cpu-journal-inventory-planning-final-v13.json;
receipt: docs/benchmarks/data/tensor-warp32/inventory-continuation-planning-v1.json.
The proposed 5050-second headroom would reach at most 39559.056321890
under the proposed 39640 ceiling. No compilation, GPU work, source implementation
or resource increase occurred; the proposal remains unaccepted.


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


## GPUP-8 approved availability-test recovery (2026-10-24)

The user explicitly approves 1240 additional CPU seconds: 1200 native and 40
reporting. The cumulative CPU ceiling is 37140; continuation allocations including
all retained charges are implementation 258, proofs 800, native 3600, workers
2052, reporting 230 and margin 400, total 7340 CPU seconds. Prior native failures
remain exact and fully charged. The active journal is
artifacts/gpup-tensor-warp32-v1/cpu-journal-availability-recovery-v9.json.
Authorization and source inspection charge eight implementation CPU seconds.

Correct only the CUDA availability tests and add deterministic mocked coverage
for load, symbol, initialization and version-query failures. Preserve the
production driver and numerical bodies, admitted CPU evidence, images and
verification helper. Expected files are the CUDA-sys test module, separate
native/worker entry points, source receipts and recovery documentation.
Run one 1200-CPU-second full native gate and compile-only device inventory.
On success, freeze and run the existing conditional device sequence under the
2052-worker-CPU-second envelope and unchanged 790-GPU-second cap: 290 acceptance,
200 profiles, 300 timings. Select the active journal at runtime. Retain every
completion criterion, per-job admission, forecast and resource-fit gate.

No bootstrap rerun, host/container change, supervisor change, automatic retry,
numerical/latency relaxation, GPUP-9 or publication. A real failure ends this
recovery. Record acceptance or refusal with exact accounting and cleanup; all
prior sources, reports and the exact 17366-event GPU prefix remain preserved.

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
[the native recovery](docs/plans/lp-tensor-warp32-native-recovery.md).

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

Current authorization (2026-10-24): the user explicitly approves the bounded
warp32 launch recovery and 108-worker-CPU-second transfer to implementation.
This supersedes the stopped/unaccepted handoff below only for that recovery.
Use cpu-journal-recovery-v3.json and the corrected preserving-PATH entry once;
then follow all accepted CPU-first/device/completion gates, preserving every
charge, artifact and the 17366-event ledger prefix. CPU ceiling stays 35900,
continuation allocation 6100, GPU cap 790. No host access, bootstrap rerun,
supervisor change, numerical/latency relaxation or automatic retry.

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

GPUP-8 warp32 recovery authorization (2026-10-24): the user explicitly accepts
ADR-0045, 6100 unspent CPU seconds reallocated and one corrected frozen
continuation capped at 790 GPU seconds. This narrowly supersedes the retained
device stop below. Preserve all failed sources/images/workers/reports and the
exact 17366-event ledger prefix. No host access, bootstrap rerun, supervisor
change, numerical/latency relaxation or automatic retry. Follow the accepted
stage/aggregate caps and CPU-first gates in state/active-task.md. GPUP-8 remains
incomplete until every completion criterion passes; GPUP-9 stays gated.

Current GPUP-8 stop (2026-10-23): accepted ADR-0044 resource recovery passes all
26 supervisor tests and full pre-device native acceptance (405 Python tests,
Rust/native/dependencies, replay, 149 docs pages and smoke). The frozen device
cohort passes all 66 ordinary tests and 280 product pairs, but its first INT8
controller comparison fails exact binary64 reference adoption after 64 updates.
The device reference uses serial reduction rather than the host's warp32 order.
Preserve the exact failed source/image/workers/roster and all historical evidence.
No actual-model fixed-work/replay pairs, sanitizers, profiles or primary timings
follow. Task GPU charge 38.094432271 s; GPUP-8 863.208464546 / 3000 s; campaign
22222.794320335 / 25202.574545061 s, 17366 ledger events preserving the exact
17362-event prefix. GPUP-8 remains incomplete; no retry, source substitution,
later task, supported preset or extra resources. CPU-only evidence/report/docs
delivery may finish from existing funds. No bootstrap rerun, host access,
container/cluster configuration changes or signals to unrelated processes.
No local numerical commit after failed device acceptance. See
docs/benchmarks/lp-tensor-cost-device-gpup8.md and current active-task accounting.

Final delivery (2026-10-24): 48 retained CPU records independently verify, five
posthoc reader tests pass and 150 docs pages/smoke pass. The repeated combined
integration gate is partial after its deadline; do not replace the separate
pre-device 405-test native pass with a final combined claim. All task descendants
are reaped. CPU upper accounting is 29749.705814258 / 35900 seconds. Current
delivery receipts are under docs/benchmarks/data/tensor-cost; unused resources
authorize no additional task or retry.

Implement one dependency-ready bounded task at a time. Follow
[CONTRIBUTING.md](CONTRIBUTING.md), accepted specifications, and ADRs.
Update state/active-task.md before work and record acceptance evidence afterward.
Read state/known-failures.md before implementing related behavior.

GPUP-8 in-container implementation authorization (2026-10-23): the user explicitly
accepts revised ADR-0044, 14300 new CPU seconds and reallocation of 1700, raising
the cumulative CPU ceiling to 35900 with a 16000-second prospective allocation.
All work stays inside this container. The first supervisor bootstrap refuses
before workload release because Python lacks os.pidfd_open. Retain the failed
source/journal and supervisor-bootstrap-refusal.json; charge the full 100 CPU
seconds. The portable Linux wrapper and four mocked portability tests are ready,
but a corrected bootstrap requires explicit authorization under the ADR's
single-attempt rule. No real supervisor acceptance, numerical preparation, full
native gate or GPU reservation has passed. No automatic retry. Numerical/latency
criteria and all GPU ledger events remain exact. A separate 100-CPU-second
refusal-delivery reservation is charged conservatively; prior CPU upper accounting
becomes 20099.822845162 / 35900. Remaining approved stage allocations are
implementation 1900, proofs 2600, native 2200, workers 8400, reporting 300 and
margin 400; total 15800. Preserve all historical reports/sources/receipts.

GPUP-8 in-container amendment proposal (2026-10-23): the user requests revision
of ADR-0044's CPU admission/budget only. The amended document proposes a locked,
four-CPU cooperative process supervisor/guardian, sampled RSS with a 6-GiB stop
threshold under an 8-GiB policy, and four-times-wall CPU charging. This explicitly
does not provide cgroup-equivalent hard memory/swap containment. No host access.
Numerical, GPU roster/allocation and latency completion sections remain exact.
Proposed prospective CPU allocation: 16000 seconds, using 1700 remaining plus
14300 additional; proposed cumulative CPU ceiling 35900. The contract/budget
amendment is not yet accepted and no implementation or execution is authorized
by the drafting request. Planning charges 5 CPU seconds; prior upper accounting
is now 19899.822845162 / 21600, with 1700.177154838 remaining overall. Preserve
the exact pre-amendment ADR and prior planning sources in the source bridge at
docs/benchmarks/data/tensor-cost/adr0044-amendment-prior/source-bridge.json and
all measured records/ledger prefixes. Extra GPU offer remains unreserved.

GPUP-8 Kubernetes constraint (2026-10-23): the user confirms Kubernetes and
prohibits escaping this container. Follow the documentation-only disposition in
docs/plans/lp-tensor-kubernetes-constraint.md. No host/namespace/privileged-helper
route or cluster mutation; no new admission, preparation or GPU attempt. Current
read-only controls cannot implement accepted ADR-0044 containment. Admission and
reporting stage reserves are exhausted; 1700 CPU seconds in other stages cannot
be transferred implicitly. The separate planning charge is 10 CPU seconds from
unallocated original-ceiling headroom: cumulative CPU upper 19894.822845162 /
21600, overall remaining 1705.177154838. The additional 3600-GPU-second offer is
unreserved and does not amend cumulative/phase ceilings or remove the CPU gate.
GPUP-8 stays incomplete. Preserve the accepted ADR, reports and exact ledger.

GPUP-8 ADR-0044 admission result (2026-10-23): approved continuation starts with
CPU resource admission and refuses because the only cgroup mount is read-only,
no delegated subtree exists, and no system/user host manager is accessible.
Retain docs/benchmarks/lp-tensor-cost-gpup8.md and data/tensor-cost receipts.
Seven simulated refusal tests pass; full coordinator/containment, native,
numerical and device acceptance have not run. No preparation or GPU reservation.
Charge the full admission/reporting CPU reservations, 350 seconds; cumulative
CPU upper accounting is 19884.822845162 / 21600. Task/campaign GPU consumption
and the exact 17362-event ledger are unchanged. The accepted ADR requires stop
on absent delegation; a host-provided task enclosure is required before further
admission. GPUP-8 remains incomplete. No new retry or later-task allowance.

GPUP-8 ADR-0044 approval (2026-10-23): the user explicitly approves the bounded
continuation and directs starting with CPU resource admission. Implement/evaluate
only within its 2050 CPU seconds and 1806 GPU seconds (990/320/496 by phase),
without raising existing ceilings. Delegated task cgroup containment and complete
aggregate admission/accounting must pass first. If unavailable, retain the CPU
admission refusal and stop before preparation/device reservations. The historical
CPU overlap remains uncertified. Preserve all 17362 ledger events and every
historical artifact. No retries, substitute device, GPUP-9, publication or merge.

GPUP-8 latency planning (2026-10-23): the user requests CPU-only diagnosis and a
bounded completion proposal, including repaired aggregate CPU admission. The
separate diagnosis is docs/benchmarks/lp-tensor-latency-diagnosis.md. ADR-0044 is
proposed, not accepted: at most 1806 GPU seconds (990 screening, 320 ablations,
496 repeatability) and 2050 CPU seconds after a 400-CPU-second diagnosis charge,
all within original ceilings. No new GPU work or numerical implementation is
authorized by the proposal. Current cgroup controls are read-only; delegated
task containment and one shared coordinator must pass CPU preflight before
preparation. Preserve the historical uncertified overlap; prospective admission
cannot certify it retroactively. Keep all 17362 ledger events and every measured
source/image/worker/report exact. GPUP-8 remains incomplete and GPUP-9 unstarted.

GPUP-8 continuation handoff (2026-10-23): the user explicitly approved
ADR-0043's loss-preserving residual correction and separate frozen study using
only the original unspent allowance. All 60 timings certify; all 30 Tensor solves
perform 2200 logical updates with 66 useful windows and no native promotion.
Useful integer/floating families now qualify, but all six multiplicity-adjusted
latency comparisons fail. GPUP-8 remains incomplete on gain; no GPUP-9.
The initial four-worker CPU admission overlapped a four-job native build;
aggregate concurrency/RSS were not recorded. This preparation resource gate
is not certified, despite passing software/device checks. Preserve the separate
cpu-concurrency-limitation.json receipt and all initial evidence.
All twelve profiles, three product diagnostics, 280 CPU/device product pairs,
five controller pairs, twelve fixed-work/replay pairs, 66 ordinary GPU tests and
four sanitizers pass. Independent CPU verification accepts 120 new LP records;
all 1272 prior inventory files and both historical ledger prefixes remain exact.
Separate report/receipts: docs/benchmarks/lp-tensor-residual-gpup8.md and
 docs/benchmarks/data/tensor-residual. Continuation charge 588.257104641 GPU s;
combined GPUP-8 825.114032275 / 3000, cumulative 22184.699888064 /
25202.574545061. Ledger 17362 events, SHA-256
e1766490f8de2affa14f4f950afed18be7f69531c3c28eedfd74539fcc0d9db5.
Final stable-source software acceptance passes 363 Python tests plus Rust/native,
dependencies, historical replay, 142 docs pages and smoke; 39 source-only tests
pass. All 248 GPUP-8 LP records freshly verify. Software acceptance does not
certify the recorded initial CPU concurrency limitation.
The bounded continuation is exhausted; no retry, replacement cell, new numerical
budget, supported preset or later-task allowance follows. Preserve every source,
image, worker and report. Local commit after final acceptance; no publication/merge.

GPUP-8 authorization (2026-10-23): the user explicitly approves ADR-0042's
INT8 and FP16/BF16 component Tensor plan and 3000 GPU seconds inside existing
ceilings (1600 screening, 550 ablations, 850 repeatability). This supersedes the
historical no-next-task-allocation handoffs only for GPUP-8. Preserve the exact
17132-event ledger prefix and all historical sources/images/workers/reports.
CPU admission precedes device execution; no study retry or device substitution.
Keep 1e-7 local budgets, 1e-9 original-model host certification, resident FP64
state, charged whole-window replay and uniform sticky promotion. Completion
requires useful integer/floating Tensor solves and a multiplicity-adjusted
certified total-latency gain. Refusal/no gain leaves GPUP-8 incomplete and does
not authorize GPUP-9 or additional resources. Local commit after applicable
acceptance is authorized; publication and merge are outside this task.

GPUP-8 handoff (2026-10-23): the bounded ADR-0042 implementation/evaluation is
retained, but GPUP-8 remains incomplete under the user's working-family and
certified latency-gain requirements. Correct INT8/FP16/BF16 operators pass 260
CPU/device pairs, five controller comparisons, four fixed-work/replay pairs,
66 ordinary GPU tests and four sanitizers. Forty-eight study cells are CPU-refused;
27 execute, all 20 admitted FP64 timings certify (20/60 planned), and four profiles
finish. All 128 LP records verify across four CPU cohorts and device/study data.
No useful Tensor solve window or gain qualifies; do not advance GPUP-9. Preserve
all four CPU cohorts, the unreserved allocator preflight, failed first device
cohort/charge, corrected cohort and every source/image/worker/report. Task charge
is 236.856927634 GPU s; cumulative 21596.442783423 / 25202.574545061. Ledger has
17200 events, SHA-256 5af7782a384ac73226f339d98d0b33e320518053c1accdf67c1339db36d0e0f1,
retaining the exact 17132-event prefix. Final pinned-native acceptance passes 353 Python tests plus Rust/native,
dependencies, replay, 140 docs pages and smoke. CPU/native/docs/smoke evidence is
under docs/benchmarks/data/tensor. No preset, new cells, study retries or later-task
allowance follows. Local commit after applicable checks; no publication/merge.

PR integration authorization (2026-10-23): the user explicitly requests opening
the combined GPUP-7/7R PR, repeated review/fixes, merge and safe cleanup. This
supersedes the historical local-only restrictions below. Review is CPU-only;
preserve all measured sources/images/workers/reports and the exact 17132-event
ledger. Prepared operators must be immutable, malformed physical counters must
refuse before aggregation, and evidence/report boundaries must remain strict.
Keep separate PR source/acceptance receipts and reports. Run every cpu/docs/smoke
test command, retain native dependencies/artifacts, and verify merged ancestry
before removing task branches. No additional GPU work or next-task allowance.
PR acceptance passes 344 Python tests, Rust/native/dependencies, historical replay,
138 documentation pages and smoke; 20 source-only portability tests pass. Fresh
verification accepts 495 LP plus 21 operator endpoints. Rebuilt verifiers cover
423 LP/21 operator endpoints; the 72 initial resident CPU records retain their
earlier required-field layout and original frozen verifier. Do not normalize or
re-sign historical payloads. Separate PR report/receipts are under
docs/benchmarks/lp-quant-pr-review.md and docs/benchmarks/data/quant-resident/pr-*.

Current handoff (2026-10-23): GPUP-7R is complete under accepted ADR-0041 and
the bounded resident subset of SPEC-0012/0021. Its
[report](docs/benchmarks/lp-quant-resident-gpup7r.md) retains all 120 planned
study cells/jobs: 42 execute and 78 quantized timing/profile cells are CPU-refused.
All 36 admitted timings certify (36/108 planned coverage), three FP64 profiles
finish 2000 logical updates, and 21 product endpoints verify. None of six
quantized candidates admits a useful low window on eight models. Residency
recovers matched FP64 coverage, but tuned FP64 remains faster on nontrivial
models; no quantized solve benefit or supported preset follows.
Full native acceptance passes 338 Python tests plus Rust/native/dependencies,
historical replay, 137 documentation pages and smoke. All 66 ordinary GPU tests,
628 product/bound vectors, six CPU/device controller comparisons, 29 fixed-work
endpoint/replay pairs and all four scoped sanitizers pass. Final CPU verification
accepts 313 LP endpoints and 21 operator endpoints. Preserve the preflight with
no GPU reservation, sanitizer-scope source bridge, all three CPU cohorts and
both frozen execution cohorts. No completed GPU identity was retried.
Task GPU charge is 245.686586823 s (timing 69.376705845, profiles 69.783306098,
acceptance 106.526574880), within 3600 and every phase cap. Cumulative is
21359.585855789 / 25202.574545061 s. The 17132-event ledger SHA-256 is
930de6771ab9bfbcb855bd05a07a58f6700aa1ade36bca09346790a94e7ff035, preserving
the exact 17036-event prefix and all earlier artifacts/authority. GPUP-8 is next
for a conditional numerical/hardware/resource disposition, with no allowance
reserved. Local commit is authorized after acceptance; publication/merge are
outside this request. Historical handoffs below remain exact in their context.

Prior implementation authorization (2026-10-22): the user explicitly accepts
ADR-0041 and allocates 3600 GPU seconds within existing ceilings for GPUP-7R.
Implement the approved resident/guard plan and bounded comparison, preserve all
historical evidence and commit locally after acceptance. The exact resource,
device, admission and validation limits are in state/active-task.md. This
authorization supersedes the historical planning-only handoff below. No push,
publication or merge is authorized.

Prior planning handoff (2026-10-22): the user requests the bounded
[GPUP-7R resident/guard follow-up](docs/plans/lp-quant-resident-follow-up.md)
before GPUP-8. [ADR-0041](docs/decisions/ADR-0041-resident-matrix-quantization.md)
is proposed, not accepted. Planning authorizes documentation and CPU checks only;
do not implement or run GPU work without acceptance of the new contract/resource
allocation. The proposed 3600 GPU seconds fit existing cumulative/phase ceilings
with no increase, but unused GPUP-7 allowance does not authorize this task.
Preserve its exact 17036-event ledger prefix and all historical numerical bodies,
images, reports and evidence. Keep 1e-7 local budgets, 1e-9 certification, sticky
promotion and host authority. CPU useful-low admission gates quantized timings;
the policy bridge and resident matched FP64 controls separate execution costs.
The completed GPUP-7 handoff below remains historical and exact.

Current handoff (2026-10-22): GPUP-7 implementation and bounded evaluation are
complete under accepted ADR-0040. Final pinned-native acceptance passes 329
Python tests plus Rust/native, dependency, historical replay, 134 documentation
pages and smoke; no GPU work runs in that gate. Research-only
lp-quant-v1 adds canonical 32x32 matrix tiles, uniform/selective FP16/E4M3/E5M2,
FP64 state, conservative original-unit budgets, sticky promotion and charged
whole-window replay. Its [report](docs/benchmarks/lp-quantization-gpup7.md)
retains all 104 attempts, verifies 34 study endpoints and certifies 33/96 timings.
Each new candidate and matched FP64 certifies only initial host-only small-4;
unchanged tuned FP64 certifies 12/12. Seventy timeouts remain. Seven diagnostic
paths time out and tuned FP64 certifies at 1400 rather than the requested 2000
updates, leaving no complete profile horizon. No useful quantized solve benefit
or supported preset follows. CPU admission retains all 56 cases, including seven
scaling-256 refusals, with 162015 independent format and 3072 product components.
All 66 ordinary/three new device tests, 384 product-vector comparisons, six
CPU/device controller comparisons, 18 fixed-work endpoints/18 bitwise replays and
four scoped sanitizers pass. Both CPU cohorts, their source bridge, the initial
RSS sampler limitation/conservative bound and corrected monitor remain visible.
CPU-only report review excludes CPU fallback and incomplete horizons, retaining
the original report and exact measured execution/image/source bodies. Fresh host
verification accepts all 182 retained study, acceptance/replay and CPU endpoints.
No review GPU work or allowance is added. Preserve artifacts/gpup-quant-v1 in full,
all historical reports/source bridges and native dependencies. Task charge is
1382.959456122 GPU seconds: timing 1109.904216936, profiles 215.675211186 and
acceptance 57.380028000, within 3600 and every phase cap. Cumulative consumption is
21113.899268966 / 25202.574545061 seconds, retaining the independent 28800 ceiling.
The 17036-event ledger SHA-256 is
861c90d8d82a20ff9655173742db37a5047d315e8cc4c983e0d6b2e6fa09bb97,
preserving the exact 16816-event prefix
dd5d7281a152d8fb56df373d913ac2dc7077aac9cf6ba2eb5f6e7781493ea52c
and all earlier history. GPUP-8 conditional contract/disposition is next and needs
its own accepted hardware/layout/error/cost and resource admission. Unused
headroom reserves nothing. Vector quantization, stochastic rounding, Tensor Core
execution, refinement/assessment combinations, sessions and presets remain gated.
Preserve original-model host authority. Delivery is a local commit only; no
publication or merge is authorized for this slice.

Prior handoff (2026-10-22): GPUP-ASSESS is complete under accepted ADR-0039
and SPEC-0021's bounded assessment subset. Its
[report](docs/benchmarks/lp-assessment-scheduling-gpup-assess.md) retains all 60
attempts, independently verifies 57 endpoints and certifies 24/48 timings.
Research-only fixed_200/bounded_800 scheduling on tuned FP64 and existing
accumulation FP32 preserves every 200-update restart/weight check. Cheap movement
only schedules original-model host assessment; final certification remains fresh
and cancellation/deadline/failure status cannot become a successful timing.
Frozen-cohort pinned-native acceptance passes 322 Python tests, Rust/native and
dependency checks, historical replay, 132 documentation pages and smoke; no GPU
work runs in that gate. CPU admission checks 16 trajectories/320 boundary witnesses. Six 2000-update
profile pairs match bitwise; no observed delayed success, while synthetic cases
retain transient-success loss and a 600-update delay. All 66 ordinary/three new
device tests, six fixed-work policy pairs/twelve replays and four scoped
sanitizers pass. FP64 irregular-32768 has a scoped 1.0272x paired gain over three
repetitions; coverage is unchanged and no supported preset follows. FP32 retains
its numerical failures and three fixed-FP64 mixed timings lack endpoints.
CPU-only review strengthens signed-zero replay and unverified-profile eligibility;
all twelve actual replays already match bitwise and the rebuilt host verifier
accepts all 57 endpoints. Preserve the exact measured workers/images/source,
original report, five-file review source bridge and all historical evidence.
Final PR pinned-native acceptance passes 324 Python tests plus Rust/native, dependency,
historical replay, documentation and smoke with no GPU work. PR review binds
checkpoints to the originating session, rejects inconsistent
failure metadata/oversized counters and excludes interrupted profile horizons
from pair discovery. Preserve the additional PR source bridge and counterexamples;
the measured execution loop and original-model authority bodies remain exact.
The final PR reader protects both historical report paths/aliases and writes to
a separate PR report; preserve both PR source bridges and their exact cohorts.
The rebuilt host verifier accepts all 97 retained study/acceptance/replay/CPU-trace
endpoints, including all 57 study endpoints. Final PR acceptance and source
receipts are docs/benchmarks/data/assess/pr-final-native-acceptance.json and
pr-review-final-source.json; prior gates/receipts remain exact and separate.
Review adds no GPU work or allowance. Task charge is 523.674592721 GPU seconds
(413.636131592 timing, 32.633232920 profiles, 77.405228209 acceptance), within 2300
and every phase cap. Cumulative consumption is 19730.939812844 / 21602.574545061 s.
The 16816-event ledger SHA-256 is
dd5d7281a152d8fb56df373d913ac2dc7077aac9cf6ba2eb5f6e7781493ea52c, preserving the exact
16684-event prefix e83d07792fb0775fc26d8d2cca8a2411f59fcbc94f742cafd8f6b844ffb60535
and all earlier history. GPUP-7 contract work is next and needs its own accepted
quantization/error-budget and resource allocation. Unused headroom reserves
nothing; full expansion state, selective precision, assessment/adaptive/refinement
combinations, sessions and supported presets remain gated. Preserve original-model
host authority and all identities. The user authorizes draft PR review, protected
merge and safe cleanup for this slice; retain all research evidence/native
dependencies and verify merge ancestry before deleting its branch.

Prior handoff (2026-10-22): GPUP-REFINE is complete under accepted ADR-0037/0038
and the native-FP64-outer subset of SPEC-0021. Its
[report](docs/benchmarks/lp-refinement-gpup-refine.md) retains all 108 primary
attempts, independently verifies 48 endpoints and certifies 30/96 timings.
Correction LPs, guarded FP32/anchored products, charged sticky promotion,
in-memory checkpoints and strict replay are implemented behind the research
feature; iterates/updates/controller remain FP64 on the host. Refinement certifies
only initially solved small-4 before any device work; scaling-256 refuses numerical
budgets and other cells time out. No sparse-product benefit or preset follows.
Full pinned-native, 66 ordinary device tests, 1920 product comparisons, nine
fixed-work replays and four scoped sanitizers pass. Fraction oracles check 240
models/1200 maps plus 93 endpoint merit enclosures/39 contractions. Preserve the
first telemetry refusal, operational continuation and CPU-only report-reader
correction; no attempt is retried or device substituted. Task charge is
1541.719136512 GPU s (1275.123297404 timing, 217.195487188 profiles,
49.400351920 acceptance), within 3600 and all phase caps. Cumulative consumption
is 19207.265220123 / 21602.574545061 s. The 16684-event ledger SHA-256 is
e83d07792fb0775fc26d8d2cca8a2411f59fcbc94f742cafd8f6b844ffb60535, preserving
the exact 16452-event prefix below and all earlier history. GPUP-ASSESS is next
and needs its own bounded contract/allocation; unused headroom reserves nothing.
Expansion state, selective precision, assessment scheduling, sessions and supported
presets remain gated. Preserve original-model host authority and all identities.
Prepublication review repairs logical checkpoint restoration, candidate-free
trace acceptance, final assessments after refresh/promotion offsets and instruction
parsing. Exact before/after source receipts preserve the historical cohort and
report; the rebuilt host verifier accepts all 39 available refinement endpoints
on CPU. Review adds no GPU execution or allowance. Publication, protected merge
and safe cleanup are now explicitly authorized by the user; preserve all evidence.

Prior handoff (2026-10-13): GPUP-STATE is complete as a bounded resource
admission refusal under [ADR-0036](docs/decisions/ADR-0036-full-expansion-state-admission.md).
Its [report](docs/benchmarks/lp-expansion-state-gpup-state.md) independently checks
192 integer, 270 FMA, 64 update and 48 transcendental cases. The first full-range
exact-bin FMA construction in both expansion formats uses 255 registers and
nonzero spills, exceeding the accepted 128-register/zero-spill gate. Bounded
320-bit probes fit but do not qualify the complete family. PR 19 review adds a
full-range compact FMA: 40 registers and zero spills in both formats, with 5900
additional independent cases per construction and host UBSan acceptance. The
first refusal remains exact but no longer establishes a scalar resource obstacle.
The instruction audit and frozen transcendental verification are repaired.
The compact scalar now passes 6170 device cases, two fresh checks, four scoped
sanitizers and 36 independently verified primitive timings on the user-selected
idle RTX PRO 6000 Blackwell. The busy-5090 admission refusal and a memcheck
stdout-reader correction remain visible; no execution is retried. No controller,
state/replay or solver benefit is admitted. Combined GPU charge is 30.114068273 s;
cumulative consumption is 17665.546083611 / 21602.574545061 s. The 16452-event
ledger SHA-256 is 24949150272600fe58364f25ebbf7bf892f7454da342edc268d50684568c5f18,
preserving the original 16366-event prefix and every phase ceiling. GPUP-REFINE is next
and requires an accepted SPEC-0021 subset and its own allocation; unused state
allowance does not reserve it. Preserve full expansion/alternative construction
gates, original-model host authority, identities and all historical evidence.

Prior handoff (2026-10-13): GPUP-EXEC is complete under accepted ADR-0035 and
the bounded exact-dot subset of [SPEC-0020](docs/specifications/SPEC-0020-lp-expansion-arithmetic.md).
Its [report](docs/benchmarks/lp-exact-executor-gpup-exec.md) retains all 108 attempts,
independently verifies 94 endpoints and certifies 58/96 timings. All 27 cached/
uncached study pairs match bitwise. Full native, 66 regular device tests, oracle,
six replays and four scoped sanitizers pass. Fourteen initial FP64 controls failed
discovery because the archive omitted an unchanged dependency; the repair and
failed attempts are retained without retries. Scheduling/scaling/mixed exact
solves refuse the bounded exponent window. No total-cost win or preset is selected.
The subsequent GPUP-STATE admission result is recorded above. Read the
[architecture and component motivations](docs/plans/lp-precision-architecture-2026-10-12.md),
draft [SPEC-0021](docs/specifications/SPEC-0021-lp-refinement.md), and
[component/interaction experiment design](docs/benchmarks/lp-precision-design-experiments.md).
GPUP-REP remains the CPU reference; full expansion state and correction/anchored
products remain independently gated. No next-task reservation follows from unused
GPUP-EXEC headroom. Preserve final original-model host authority and all identities.
Task charge is 520.157397485 GPU seconds: timing 431.684266725/2300, profiles
36.003675982/450 and acceptance 52.469454778/850. Cumulative consumption is
17635.432015338 / 21602.574545061 seconds under ADR-0035's amended authority.
The 16366-event ledger SHA-256 is
4d083cdb06b4baa38452bb331541fa8874614aeb037f34e40001ce9692ede26b,
preserving the 16134-event prefix
60649d29992d21508e60aa60f3e334e9ac18fe3254525ec38cc0eef298e84823.
The dated handoffs below remain historical; follow next_ready_task and the
roadmap's 2026-10-12 order.

For low-precision LP follow-ups, read the preserved
[2026-09-30 research analysis](docs/plans/lp-low-precision-research-2026-09-30.md)
alongside the roadmap and candidate register. It records measured failure
mechanisms, proposed correction-LP/anchored-product methods, SM120 bypasses,
FP16/FP8 progression, limitations and experiment gates. It is research guidance,
not an accepted numerical contract or a change to next_ready_task or GPU budgets.

M1, C1, C2, C3, C4, C5, C6 and C8 are complete and specified. C6 was heterogeneous
computation and GPU feasibility, specified as
[SPEC-0010](docs/specifications/SPEC-0010-heterogeneous-computation.md) for device
selection, residency, batching, arithmetic width, fallback, cancellation, recovery and
the batched integer schedule evaluator, and
[SPEC-0011](docs/specifications/SPEC-0011-gpu-lp-backend.md) for the GPU linear
programming backend. Both are implemented with evidence: a search can register a
device-backed candidate producer and re-execute from the record it writes, and
`optimizer solve --backend host-lp|cuda-lp` runs a first-order linear programming
method whose dual bound comes only from a host-side certification. The next capability
is C7, adaptive portfolios, which has no specification yet and needs one before any
behavior. The user has prioritized the separate
[GPU LP precision research track](docs/plans/gpu-lp-precision-roadmap.md) before C7;
follow `next_ready_task` in state/backlog.yaml and implement one GPUP slice at a time.
SPEC-0013 is accepted and GPUP-2 implements the bounded LP study and baseline report.
SPEC-0012 is accepted for implemented GPUP-3 shared resumable FP64 control. The
opt-in cuda-lp-matched backend and measured overhead repairs preserve legacy cuda-lp.
GPUP-4 adds explicit experimental cuda-lp-tuned under ADR-0017, with the preserved
first round and complete ADR-0018 correction documented in
[the report](docs/benchmarks/lp-tuned-fp64-gpup4.md). Matched remains the general
reference; scoped provisional fusion results are not supported presets. GPUP-5 is
implemented under ADR-0019: lp-precision-v1 on cuda-lp-tuned, separate precision
code identity, FP32 storage/products/accumulation/state and fixed FP64 correction,
v4 evidence and optional isolated COPT 8.0.6 CPU/GPU PDLP baselines. Its
[report](docs/benchmarks/lp-fp32-gpup5.md) verifies all 480 attempts and records
coverage losses; no supported preset is selected. Existing identities/replay and
original-model authority remain. GPUP-6 is a separate explicit adaptive contract (below); no audit/rollback/promotion/demotion is implicit
in GPUP-5. Later quantization and precision requirements remain pending.
The [FP32 latency diagnosis](docs/benchmarks/lp-fp32-slowdown-diagnosis.md) adds
213 equal-work/profiler diagnostics under ADR-0020: convergence amplification,
scaled-matrix bias and executor/correction overhead, with hardware counters denied.
The diagnosis reached 1467.266874696 campaign GPU seconds: the prior 1324.210639253
plus 143.056235443 diagnostic screening seconds. Never reset the ledger or evidence.
GPUP-5B is complete under ADR-0021: feature-gated exact scaling and two/three-component
sparse products, separate research code object/executable and strict research-v1
host evidence. Its [report](docs/benchmarks/lp-exact-components-gpup5b.md) verifies
all 840 attempts and full native/device/four scoped sanitizer gates. New modes
restore 27/36 timing coverage; component cross-products remain slower. Preserve
the [rounding note](docs/benchmarks/lp-fp32-rounding-analysis.md) and
[candidate register](docs/plans/lp-precision-candidates.md). No preset or adaptive
recovery is selected. Carry forward 2235.353878971 campaign seconds, including
697.211414922 GPUP-5B study and 70.875589353 acceptance screening seconds. All 4996
ledger events retain the 3288-event prefix; the final ledger SHA-256 is
737e1301cb31cf5d0ad0585aa81a4dc0b814615d39e4974827e504e880b11e5f.
GPUP-5C is complete under ADR-0022 after the
[FP64-pipe root-cause note](docs/benchmarks/lp-fp64-pipe-root-cause.md): three
feature-gated research modes (integer-pipe guards, fused two-launch schedule,
double-float FP32 pairs), research-v2 evidence, explicit tolerance tiers
1e-9/1e-6/1e-4 recorded per request, a frozen lp-manifest-v2 development extension
up to 65536 rows, and a protocol-driven harness (`--protocol`) whose v1 behavior is
byte-identical. Its [report](docs/benchmarks/lp-fp64-pipe-gpup5c.md) verifies 806
of 850 admitted attempts under identity gpup5c-v1: integer guards and fusion are
bitwise identical to the FP64 control and halve update cost at study size;
double-float is fastest at scale but underflows on scheduling LPs; tiers recover
FP32 storage coverage without changing latency. Cumulative campaign consumption is
3794.758955639 seconds; the 6722-event ledger SHA-256 is
ff6f1b5471e80791e964d1e6679017ea33593a7899718d0431f666cfaa5fa23b with the
4996-event prefix intact. On 2026-09-20 the user pulled GPUP-THROUGHPUT ahead of
GPUP-6: after GPUP-5C, context creation (208-330 ms) and the fixed host phases, not
arithmetic, dominate solves, and at 65536 rows preconditioning and research
preparation each exceed total kernel time. GPUP-THROUGHPUT is complete under
[SPEC-0014](docs/specifications/SPEC-0014-lp-repeated-solve-throughput.md) and
[ADR-0023](docs/decisions/ADR-0023-repeated-solve-throughput.md), both accepted
2026-09-20: opt-in TunedSession/ResearchSession reuse one context, prepared matrix
and residency per batch, with per-solve cold iterates, fresh certification and
bound rebinds counted separately. Its
[report](docs/benchmarks/lp-repeated-solve-throughput.md) verifies 687 of 705
admitted attempts under identity gpup-throughput-v1: 4785/4785 batch solves are
bitwise identical to fresh singles, amortized throughput reaches 26.6x fresh
single-solve latency at N=32 on small-4 as a separately labeled endpoint, a batch
of one does not pay off, sessions lose at 32768 rows, and all 18 65536-row short
batches timed out. It leaves the single-solve endpoint, protocol, defaults and
archived evidence unchanged and never reports amortized throughput as
single-solve latency. Cumulative campaign consumption is 6951.059845871 seconds
inside the 8102.574545061-second ceiling (2617.929459541 study / 2700,
538.371430691 acceptance / 600); the 8178-event ledger SHA-256 is
dd957404ed65763775afba63bc11f8b03ffa9c64dcad19112f76fc9b1f5f32f6 with the
6722-event prefix ff6f1b5471e80791e964d1e6679017ea33593a7899718d0431f666cfaa5fa23b
intact. The pre-existing tuned_cases filter lacks a clean racecheck receipt (the
session_ scope passed all four sanitizers); the partial receipts are retained.
The [review corrections](docs/benchmarks/lp-throughput-corrections.md) under
ADR-0024 repair outcome identity, common session identity and binary64 comparison;
48 new ordinary fresh-variant controls validate 360/360 retained comparisons.
Historical fresh-variant controls were N=1 sessions and remain labeled as such.
After the correction: cumulative 6982.408046756 s, study 2645.977139698/2700,
acceptance 541.671951419/600; 8276-event ledger SHA-256
b3451186b7a5fc0029fbbd612b07e795072476ab76137a78a375b1d97866c236 preserves the
8178-event prefix above. No new GPU allowance.
The subsequent [host-input repair](docs/benchmarks/lp-throughput-host-input.md)
removes repeated host parsing/reconstruction without caching assessments:
16/16 new 32768-row N=8 diagnostic results match, with original and new verifier
acceptance. Whole-batch historical comparisons are 4.53x repeat and 2.20x variant
(one repetition, no general preset). Campaign consumption is now 7015.920961503 s;
study 2679.490054445/2700, acceptance 541.671951419/600. The 8278-event ledger
SHA-256 is c185d5c069a892f10654b737b0a96737005b1fe9a70b5f0f3ee445d162af976a, preserving
the 8276-event prefix above and all prior prefixes. No new allowance or kernel
change; 65536-row coverage and the old tuned_cases racecheck gap remain open.
GPUP-6 is complete under accepted ADR-0025 and SPEC-0012: explicit lp-adaptive-v1
ladders/audits, whole-window rollback and charged replay, direct/gradual promotion,
sticky or probed demotion, fresh-single v5 evidence and replay. Original-model
host certification remains authoritative; old kernels, records and defaults remain.
Its [report](docs/benchmarks/lp-adaptive-gpup6.md) independently verifies
2086 endpoints from 2376 admitted of 2376 planned attempts.
Failed archive-discovery attempts and comparison gaps remain visible; no preset
is selected. Native, regular device and four adaptive sanitizer gates pass.
Campaign consumption is 8912.494084146 s inside the 14402.574545061 s ceiling;
GPUP-6 study 1826.094392481/5400 s, acceptance 70.478730162/900 s.
The 13056-event ledger SHA-256 is
6db55153153e66ed5c2398417d008e4edd278e11153cf87b975345f1a574d34d, preserving the 8278-event prefix
c185d5c069a892f10654b737b0a96737005b1fe9a70b5f0f3ee445d162af976a and every earlier prefix.
GPUP-7 remains the next precision feature after the COPT follow-ups ordered below;
it needs its bounded quantization/FP8 interface and resource contract before behavior.
Adaptive sessions, persistent checkpoints and supported presets remain outside GPUP-6; old 65536-row and tuned_cases racecheck gaps remain.

GPUP-COPT is complete under ADR-0026. Its [component-cost report](docs/benchmarks/lp-copt-comparison.md)
retains all 1140 attempts, independently verifies 948 endpoints and certifies
402/816 primary timings. Evidence output at 65536 rows and COPT graph internals
remain explicit gaps; no winner or preset is selected. Task charge is
5853.941357570 GPU s; cumulative 14766.435441716/18002.574545061 s.
The 15340-event ledger SHA-256 is
5cf76ffbea09e21fdf21692c4030f8176ae5ef7f481c2e5c6e83fe302371b51b,
preserving the 13056-event prefix and every phase cap. The user requested follow-up
ordering on 2026-09-27. GPUP-EVIDENCE and GPUP-HOST are now complete (below).
GPUP-SETUP, GPUP-COPT-ADAPTER and GPUP-CONVERGENCE are now complete (below);
continue with GPUP-7's required contract work. Fresh setup diagnosis and optional COPT adapter
construction were separately prioritized investigations, not quantization prerequisites;
see the [ordered roadmap](docs/plans/gpu-lp-precision-roadmap.md#current-follow-up-order-2026-09-27)
and next_ready_task. Planning adds no GPU allowance or accepted numerical behavior;
GPUP-7 still needs its accepted contract.
GPUP-EVIDENCE is complete under accepted SPEC-0015 and ADR-0027. Its
[report](docs/benchmarks/lp-compact-evidence.md) records strict study-only compact
v1-v5 evidence, verified transcode and replay, four full-witness CPU round trips,
full native acceptance, 55 device tests and six format pairs plus six replays.
All 24 fresh attempts are retained: 15 verify and 12 certify; compact verifies
12/12 and certifies 9/12, while mixed-65536 remains time-limited. Historical outputs,
legacy defaults, numerical settings and kernels are unchanged; the old racecheck
and session gaps remain. Task charge is 305.274714773 GPU s; cumulative
15071.710156489/18002.574545061 s, with no new allowance. The 15392-event ledger
SHA-256 is 6a30c1954ff9bc80c733364d8e8a7c0fc4c4439d70b959d2c10996d71993e518,
preserving the 15340-event prefix above and all phase caps.
GPUP-HOST is complete under accepted SPEC-0016 and ADR-0028. Its
[report](docs/benchmarks/lp-immutable-host-input.md) verifies all 28 attempts,
certifies all 24 fresh timings and matches all 14 numerical/work pairs. LpInput
removes one duplicate parse/structural validation, retaining fresh sparse construction
and every candidate/certificate assessment. Native, 55 regular device tests, six
old/new fixed-work pairs and six compact replays pass. No numerical/default/kernel
change or cross-solve reuse; historical racecheck/session/mixed-65536 gaps remain.
Task charge is 134.072418846 GPU seconds; cumulative 15205.782575335 /
18002.574545061 seconds, no added allowance. The 15452-event ledger SHA-256 is
90dab78c269b74f511416ddd73cf05e123555ae006b9ad75fc896933a35f9cd2,
preserving the 15392-event prefix above and all phase caps.
GPUP-ADAPTIVE-COST is complete under accepted SPEC-0017 and ADR-0029. Its
[report](docs/benchmarks/lp-adaptive-host-cost.md) verifies all 32 attempts,
certifies all 24 timings and matches all 16 timing/profile pairs. Shared operators
reduce full-ladder preparation from five operators to two; streamed audits and
borrowed probes preserve arithmetic and charged recovery. Twelve fixed-work pairs
and twelve replays match; full native, 55 regular device tests and four adaptive
sanitizers pass. No preset or cross-solve reuse. Historical gaps remain open.
Task charge 201.890184622 GPU seconds; cumulative 15407.672759957 /
18002.574545061 seconds, with no added allowance. The 15528-event ledger SHA-256
cb0dc57f9f92546f4cc2d93b0de3c8556d6b24517f71b7a6efaa91fa96afedb6
preserves the 15452-event prefix above and all phase caps.
GPUP-SETUP is complete under accepted SPEC-0018/ADR-0030. Its
[report](docs/benchmarks/lp-fresh-setup.md) verifies all 32 attempts, certifies 24
fresh timings and matches all 16 numerical/work comparisons. Four control profiles
precede the sole experimental primary-context repair; retain/release provides no
consistent fresh-process latency benefit. User contexts remain the default, primary
contexts are study-only, with checked lifecycle receipts and setup-bound replay.
Full native, 58 candidate device tests, four primary sanitizers, twelve fixed-work
pairs and twelve replays pass. Historical racecheck/session/mixed-65536 gaps remain.
Task charge 224.608447458 GPU seconds; cumulative 15632.281207415 /
18002.574545061 seconds, no new allowance. The 15606-event ledger SHA-256
ad3d84354f0b74ae62fcc019ee4dcbf29b0a3251d066f1e0f2df11ccb107230b preserves the 15528-event prefix above
and every phase cap. The following adapter slice retains this prefix.
GPUP-COPT-ADAPTER is complete under accepted SPEC-0019/ADR-0031. Its
[report](docs/benchmarks/lp-copt-adapter.md) independently verifies all 84 attempts,
certifies 42/72 timings and 10/12 profiles, and retains all interrupted/rejected
outcomes. Twelve native readbacks and 24 min/max/profile endpoints pass; 27/36
timing pairs and 10/12 profile comparisons match, with the remaining CPU-default
pairs deadline-limited. Bulk loading is cheaper, but CSC preparation and cold
SciPy import make this adapter slower in every certified cell. No preset or
runtime/kernel/default change; historical wrappers and evidence remain intact.
Task charge 171.904859644 GPU seconds; cumulative 15804.186067059 /
18002.574545061 seconds, no added allowance. The 15776-event ledger SHA-256
2b99b615dc77da07fb078e1cefc188d2131db5ca671fe9b86f989a6d660606f0 preserves the
15606-event prefix above and every phase cap. The subsequent convergence study
retains this prefix. GPUP-7 still needs its accepted quantization contract.
GPUP-CONVERGENCE is complete under accepted ADR-0032/SPEC-0013. Its
[report](docs/benchmarks/lp-convergence.md) retains all 176 frozen attempts,
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
At convergence-study completion the handoff was GPUP-7's contract. The
2026-10-12 planning update above now makes GPUP-REP CPU-only proof/contract
validation next, before any new numerical behavior.

GPUP-5's exact cumulative ceiling was 4502.574545061 seconds. Its separate acceptance
used 80.458622460 of 900 GPU seconds. Future work must retain the campaign/phase caps.
GPUP-1 repairs certification and objective/gap arithmetic; preserve its independent
exact-rational regressions before introducing lower precision. The initial
experiment campaign is capped at eight GPU-hours. Repeated-solve throughput is
GPUP-THROUGHPUT above; full MILP search performance remains a separate future direction.
Unsafe CUDA code is permitted only inside optimizer-cuda-sys under
[ADR-0009](docs/decisions/ADR-0009-cuda-driver-boundary.md), which amends ADR-0003's
single-boundary rule; optimizer-cuda keeps the prohibition and keeps discovery and the
lease. A device never holds mathematical authority:
[ADR-0010](docs/decisions/ADR-0010-certified-gpu-lp.md) requires every bound to come
from a host-side certification that does not assume the device computed correctly.
`optimizer-lp` holds that certification and the method, takes no device dependency, and
is the oracle the kernels are differentially checked against; `optimizer-lp-cuda`
depends on it and never the reverse. Neither is a fallback: a fallback is the pinned
HiGHS adapter, because SPEC-0010 requirement 23 requires one to be the implementation
the project already treats as authoritative.
The C8 local extension registry is implemented under SPEC-0009 and ADR-0008;
it resolves a named extension identity to an extension this build provides and
deliberately does not load dynamically distributed native components, which would
need a boundary ADR-0009 does not authorize either. The Python SDK (C9) and the
comparative experiment runner (C10) are unspecified, and
[known failures](state/known-failures.md) records each blocker along with the C8
requirements whose acceptance tests are thinner than SPEC-0009 describes. Later
SDK and comparative-runner APIs require their own specifications and
acceptance gates; do not introduce them without one.
Use Rust for runtime work; Python under tools/ is build and validation tooling,
not the SDK. Native HiGHS code is permitted only inside optimizer-highs behind its
private ownership boundary, with the pinned 1.11.0 CPU contract, and CUDA driver
calls only inside optimizer-cuda-sys. Those two crates declare their own lints
because a workspace-level unsafe prohibition cannot be relaxed per crate; every
other runtime crate keeps the prohibition, and no third boundary is authorized.

Run bash tools/check.sh for acceptance; it requires the pinned native HiGHS build.
AI_OPTIMIZER_SKIP_NATIVE=1 skips it and reports uncovered native acceptance, which
must never be recorded as a full gate pass. Discovering GPUs does not authorize a
kernel workload; all actual project GPU jobs require the shared host lock, and the
lock permits one holder across device selections, so two devices are never used at
once. nvcc is a provisioning dependency, never a build dependency: an ordinary
cargo build must keep working on a host with no toolkit and no device.
Do not change experiment seeds, thresholds, splits, or defaults silently.
Do not publish, push, or configure external hosting without authorization.
