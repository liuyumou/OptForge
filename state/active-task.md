# Active Task

## GPUP-THROUGHPUT: specification, ADR and budget before behavior (2026-09-20)

Status: complete. Phase A is committed as 0d5d713 with its full pinned-native
gate receipt; Phases B-E are the implementation commit on top of it. The
[repeated-solve report](../docs/benchmarks/lp-repeated-solve-throughput.md)
holds the Phase E evidence; GPUP-6 is next_ready_task and requires its bounded
adaptive contract before behavior. The working tree carried the optimizer-lp
PreparedMatrix/Engine::from_prepared refactor, TunedSession and
ResearchSession with residency bound rebinding, solve-batch/materialize/verify-batch
CLI, lp_batch and research batch documents, both frozen schemas, lp_variants.py,
benchmark_lp_throughput.py (705 planned attempts) and the session_ device cases. The
backlog reorder record below stays as the history of how this slice was selected.

Objective: implement GPUP-THROUGHPUT (state/backlog.yaml next_ready_task) in phases,
beginning with its accepted bounded contract: SPEC-0014 (repeated-solve sessions for
cuda-lp-tuned and the research executable), ADR-0023 (two opt-in paths, variant rule,
bitwise-identity rule, frozen resources) and the frozen protocol
benchmarks/configs/lp-throughput-v1.json carrying its own ceiling authority. A batch
fixes one matrix, objective and row bounds; solves are identical repeats or per-solve
variable-bound variants tightened around the instance's frozen witness. The
fresh-process single-solve endpoint, protocol, defaults and archived evidence stay
unchanged; amortized throughput is a separately labeled endpoint, never substituted
(ADR-0013, SPEC-0013 requirements 10-13).

Acceptance gate per phase: Phase A (this record) — full pinned-native
bash tools/check.sh with zero GPU work, committed as documentation only. Phases B-D —
full gate plus Python integration tests; device session_ cases and all four scoped
sanitizers under the shared lease. Phase E — frozen study under identity
gpup-throughput-v1, independent verification of every admitted attempt, bitwise
identity counts, report and final gate.

Likely files: docs/specifications/SPEC-0014-lp-repeated-solve-throughput.md,
docs/decisions/ADR-0023-repeated-solve-throughput.md,
benchmarks/configs/lp-throughput-v1.json, crates/optimizer-lp (problem.rs, pdhg.rs),
crates/optimizer-lp-cuda (residency.rs, backend.rs, session.rs, research.rs),
crates/optimizer-experiment (lp_batch.rs, lp_research.rs, example), crates/optimizer-cli
(batch.rs, lp_study.rs, main.rs), schemas/lp-batch-request-v1/lp-batch-endpoint-v1,
tools (lp_variants.py, benchmark_lp_throughput.py, analyze_lp_throughput.py,
lp_research_budget.py), tests, and the documentation set named in SPEC-0014.

Resource budget: four build jobs; four-hour CPU validation ceiling. GPU only after
ADR-0023 is accepted: study 2700 s plus acceptance 600 s (combined 3300 s) under
identity gpup-throughput-v1, inside a cumulative ceiling of 8102.574545061 seconds
(4502.574545061 + 3600). Preserve the 6722-event ledger prefix SHA-256
ff6f1b5471e80791e964d1e6679017ea33593a7899718d0431f666cfaa5fa23b and 3794.758955639
consumed seconds; campaign 28800 s and phase caps unchanged. Phase A runs zero GPU work.

Evidence: full pinned-native bash tools/check.sh passed on the Phase A tree
(source identity 1620d714af9b4f84e41303b7d1c17ae47dbcd1481d7993c873dde5901036035;
441 Rust tests, 131 Python tests, 88 documentation pages with valid links/anchors,
artifact schemas and committed-record replay). SPEC-0014, ADR-0023 and the frozen
lp-throughput-v1 protocol (planned 705 attempts, ceiling 8102574545061 ns embedding
source campaign hash b40217f3... and decision hash 06f28fbf...) are committed as
documentation. No GPU job ran; the campaign ledger is untouched.

Phase B-D evidence (2026-09-20): full pinned-native bash tools/check.sh passed on the
implementation tree (source identity 3a10d41228d2e70b8ce1a544b21c7657a58935e870c33985b185041273df6f36;
146 Python tests including 15 throughput grid/variant/budget/analysis gates, 88
documentation pages with valid links/anchors, artifact schemas and committed-record
replay; log /tmp/gpupt-gate-b2.log). Resumed work added tools/analyze_lp_throughput.py
(separate-endpoint labeling, bitwise identity counts), the lp_gpu_cli_check.py
solve-batch/verify-batch section, the v3 acceptance ledger authority in
lp_research_budget.py's main, the CHANGELOG behavior entry and SPEC-0014
implementation/test mappings. The Rust workspace test suite passes across 54
binaries with zero failures; the eight session_ device cases compile and await
their leased acceptance run. No GPU job has run; the campaign ledger is untouched.

Phase E evidence (2026-09-21): the frozen gpup-throughput-v1 study admitted all 705
planned attempts; 687 verified independently with the archived executables and 18
(the 65536-row N=8 short batches, both kinds, three repetitions) stopped at their
58-second reservations without endpoints, charged and retained. Batch solves are
bitwise identical to fresh singles on 4785/4785 compared pairs; fused and intguard
research trajectories agree on 2451/2451 numerical comparisons (launch counts
differ by construction). Study 2617.929459541/2700, acceptance 538.371430691/600,
combined 3156.300890232/3300, cumulative 6951.059845871/8102.574545061 GPU seconds;
the 8178-event ledger SHA-256 dd957404ed65763775afba63bc11f8b03ffa9c64dcad19112f76fc9b1f5f32f6
preserves the 6722-event prefix ff6f1b5471e80791e964d1e6679017ea33593a7899718d0431f666cfaa5fa23b,
with all 728 new reservations settled. Device acceptance passed on
GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48: regular suites on both binaries, all
session_ cases under all four scoped sanitizers with zero errors/hazards, the
research_ cases under all four, the study_observation/matched_control/tuned_cases
filters under memcheck/initcheck/synccheck, and the CLI evidence check including
solve-batch, materialize, verify-batch and the pinned fallback. Retained failures:
one stale-binary launch, one three-defect session-test run and two CLI-check
failures (all fixed before final evidence), one session-racecheck reservation
timeout (retried, passed 116.8 s), and the pre-existing-filters racecheck that
timed out after study_observation and matched_control passed clean; tuned_cases
lacks a racecheck receipt because the frozen acceptance cap left 61.6 seconds, and
the gap is recorded in the report and known failures, not relabeled. The measured
source tree 6343d622025803e6e9637612c8fd05d30832b138788ab652fe5ed791f245b1ea
(optimizer 6498e4f3e126cd24d3bb2587dadd792857a4819ec44ac5f6ddbd3f009e087676,
research ec778ceeba80bc072525c4447863a46e892d72bc11fc94d151c088a4ab776e1e, code
object 6a743e1e745159f304168124800eec86891c641dfe9f18a91c0aa11d0555b7a2 unchanged
from GPUP-5C) is archived in artifacts/gpup-throughput-v1 with protocol, jobs,
ledger snapshot and analysis.json (analysis tool
2916421b148e70ebb676a6e353fdf745fd1af8c9768fbcc66463070b3de40448). The
[report](../docs/benchmarks/lp-repeated-solve-throughput.md) keeps the amortized
endpoint separate and records the N=1 and 32768-row negative results. The
post-measurement changes are the analysis-tool tuple fix and cross-mode
launch-count exclusion (each with a regression test), documentation and state
records; measured kernels, sessions and frozen evidence are unchanged.

## GPUP-THROUGHPUT pulled ahead of GPUP-6; GPUP-5/5B/5C integrated (2026-09-20)

Status: ready; no behavior implemented. PR #6 merged branch
codex/gpup5b-exact-products into main as merge commit 8e768247 after the cpu, docs
and smoke checks passed; the recorded full pinned-native gate receipt
(target/lp-native-gate.json) matched the merged source identity
e8055b7e8158f5919c0d4b82e08e1af1b388aa1dcfb7577e48e7c98a8ea8f758. GitHub refuses
self-approval, and the main ruleset requires zero approving reviews, so the merge
rests on the recorded gate and the required status checks.

Objective: reorder the backlog only. The user pulled GPUP-THROUGHPUT ahead of
GPUP-6 because the GPUP-5C report shows the remaining cost is outside arithmetic:
paired certified-latency ratios stay within 0.92-1.11 of tuned for every mode and
tier, context creation (208-330 ms) and fixed host phases dominate 400-600 ms solves
at study size, and at 65536 rows preconditioning (about 940 ms) and research
preparation (about 1020 ms) each exceed the 19-30 ms total kernel time of a
200-proposal run. GPUP-THROUGHPUT becomes next_ready_task with status ready and
depends_on GPUP-5C; GPUP-6 now also depends on it. Its acceptance keeps the ADR-0013
separation: an accepted specification, API and resource budget before any behavior;
the fresh-process single-solve endpoint, protocol, defaults and archived evidence
unchanged; amortized throughput never reported as single-solve latency.

Acceptance gate: bash tools/check.sh (documentation build and policy checks cover
the edited pages); no solver, protocol, seed, tolerance, artifact or ledger changes.
Likely files: state/backlog.yaml, AGENTS.md, docs/plans/gpu-lp-precision-roadmap.md,
docs/plans/lp-precision-candidates.md, wiki/status.md and this record.
Resource budget: documentation-only; at most four build jobs for the gate; zero
project GPU work. The slice's own CPU/GPU budget is set by its specification, which
is the first deliverable of GPUP-THROUGHPUT and must be accepted before behavior.

Evidence: full pinned-native bash tools/check.sh passed on the edited tree (source
identity 38d6a626c4a32e44668d280d31fbdbe23e0c0ca9ecc9f3610f094cab374d3248; 131
Python tests, 86 documentation pages, committed records re-executed, bootstrap
smoke). No GPU job ran; the campaign ledger is untouched.

## GPUP-5C: FP64-pipe execution, tolerance tiers and corpus extension (2026-09-19)

Status: complete under [ADR-0022](../docs/decisions/ADR-0022-fp64-pipe-execution-and-tolerance-tiers.md);
see the [report](../docs/benchmarks/lp-fp64-pipe-gpup5c.md). Evidence below.
Objective: act on the [root-cause note](../docs/benchmarks/lp-fp64-pipe-root-cause.md)
without changing runtime selectors, defaults, existing code objects, archived
evidence or the nine GPUP-5B modes. Add feature-gated research modes
intguard-fp64 (integer-pipe guards), fused-fp64 (two launches per proposal) and
doublefloat-fp32 (FP32 hi/lo pairs, no FP64 in the sparse loop) with CPU oracles;
research-v2 requests/evidence; explicit tolerance tiers 1e-9/1e-6/1e-4 recorded
per configuration; a frozen development-extension manifest under lp-manifest-v2
with instances up to 65536 rows and a new mixed family; a protocol-driven research
harness with byte-identical v1 behavior; committed diagnostic microbenchmarks.

Acceptance gate: full pinned-native tools/check.sh; CPU rational fixtures for
double-float products; strict v1/v2 evidence tests; device differential over all
twelve modes across controller boundaries, fault/admission tests, and all four
scoped sanitizers sequentially; frozen lp-research-v2.json attempts all admitted
through the shared lease and the preserved ledger; independent revalidation of
every endpoint; report with coverage per tier, paired latency, equal work, traces.

Likely files: crates/optimizer-lp/src/research.rs and tests; cuda/lp_pdhg_research;
crates/optimizer-lp-cuda/src/research.rs and tests/device/research.rs;
crates/optimizer-experiment/src/lp_research.rs; schemas/lp-manifest-v2.schema.json;
tools/lp_generate.py, lp_protocol.py, lp_research_budget.py, benchmark_lp_research.py,
analyze_lp_research.py, lp_research_oracle.py; cuda/diagnostics; benchmarks/configs/
lp-research-v2.json; benchmarks/manifests/lp-development-extension-v1.json; docs.

Resource budget: four build jobs; CPU validation within four hours; GPU study
1500 s and acceptance 300 s (combined 1800 s) charged to the preserved
gpup-baseline-v1 ledger under identity gpup5c-v1. Preserve the 4996-event prefix
SHA-256 737e1301cb31cf5d0ad0585aa81a4dc0b814615d39e4974827e504e880b11e5f and
2235.353878971 cumulative seconds inside the 4502.574545061-second ceiling.
Uncharged 2026-09-19 investigation work is recorded, not repeated silently.

Evidence: artifacts/gpup5c-v1 (850 admitted of 874 planned attempts, 806 verified,
24 missing at the study cap, 44 without endpoints: 34 CLI 16 MiB refusals and 10
mixed-65536 timeouts) and artifacts/gpup5c-acceptance (two regular device runs of
33 cases, all four sanitizers twice with zero errors/hazards, three charged
microbenchmark runs). All twelve modes match the CPU oracle bitwise over 40 steps;
intguard/fused endpoints are identical to the FP64 control on all 114 pairs.
Full pinned-native tools/check.sh passed on the measured source
5e1e0ff1dd6604c54667356fa75d665c451d1e37b7f794039783acc982833e68 (131 Python
tests, 85 documentation pages) and again on the final source. Study
1493.313474227/1500 plus acceptance 66.091602441/300 seconds; cumulative
3794.758955639/4502.574545061. Ledger 6722 events, SHA-256
ff6f1b5471e80791e964d1e6679017ea33593a7899718d0431f666cfaa5fa23b, 4996-event prefix
intact. The initial fused kernels serialized their update tail on lane 0 and were
restructured before the study; both microbenchmark results are retained. Every GPU
job used the shared lease; no push or publication. Next ready task: GPUP-6.

## GPUP-5B: exact scaling and component sparse products (2026-09-16–17)

Status: complete; all 840 attempts and required acceptance gates passed. The
maintainer accepted ADR-0021 and SPEC-0012/0013 amendments before behavior.
Feature-gated host scaling, separate research code object/executable and strict
research-v1 evidence implement power-of-two/factored exact storage and two/three
components with matched reconstructed-FP64/FP32-cross-product controls. Ordinary
runtime schemas, selectors, code objects, replay and original-model authority
remain. No correction, adaptive recovery or supported preset was added.

The [report](../docs/benchmarks/lp-exact-components-gpup5b.md) retains all results:
432 timings, 48 profiles, 336 equal-work runs and 24 Systems traces. All 840
endpoints independently verify; all traces decode offline and match 1200 launches.
Timing coverage is 27/36 for every new mode versus 12/36 for plain FP32 storage.
Three-component cross-products recover convergence but cost 2.69x/2.67x native
research update time on irregular-2048/dense_block-1024. Failures remain visible;
no held-out/validation measurement or supported preset. The prior diagnosis is
unchanged. The [rounding note](../docs/benchmarks/lp-fp32-rounding-analysis.md)
reproduces every CPU claim and archived witness/hash; the
[candidate register](../docs/plans/lp-precision-candidates.md) preserves future work.

Acceptance: full pinned-native tools/check.sh on measured and final code, with
435 Rust tests, 126 Python integration tests and 83 documentation pages on final
source, plus format/clippy/dependency/replay/smoke checks. Independent Fraction
fixtures cover reconstruction/products/sparse cancellation/transpose; CPU/device
differentials cover all nine modes and controller boundaries. Memory refusal,
cancellation, exhausted physical work, range/fault accounting and strict evidence
mutations pass. All 51 regular device cases pass; all four scoped sanitizers run
sequentially with zero errors/race warnings. All nine research modes pass the
end-to-end preflight; the hardened final reader revalidates all 630 research
endpoints. Evidence: artifacts/gpup5b-v1, artifacts/gpup5b-rounding-v1 and
artifacts/gpup5b-acceptance (native-final.log, canonical device/sanitizer logs,
final-verification.json, exact source/code identities and artifact indexes).
Preliminary compile/CPU launcher/debug-audit records are retained. Post-measurement
changes only strengthen CPU evidence checks, rational fixtures and reporting;
measured numerical kernels/executor/controller are unchanged.

Resources: four build jobs, CPU validation within four hours; GPU measurements and
CPU acceptance run separately. New study 697.211414922/900 plus acceptance
70.875589353/300 = 768.087004275/1200 screening seconds. Preserve prior
1467.266874696 seconds: cumulative 2235.353878971/4502.574545061, with all original
campaign/phase caps. All 854 new reservations settled. The 3288-event prefix SHA
b3ca2739b1108a552b0423606ddd0cd94a8ed2323da1506098fa0150ba42bfef is intact;
4996-event final ledger SHA
737e1301cb31cf5d0ad0585aa81a4dc0b814615d39e4974827e504e880b11e5f.
Historical artifact indexes and all their referenced files verify. GPUP-5's
80.458622460 acceptance seconds remain separate and unchanged. Every GPU job used
the shared host lease. No push/publication. Next ready task: GPUP-6; accept its
bounded adaptive interface/contract before implementation.

## Standalone pelican bicycle animation (2026-09-16)

Status: complete. User-requested creative artifact, separate from the optimizer
capability backlog. Objective: one self-contained `pelican-bicycle.html` containing
an original 2D SVG pelican riding a bicycle, synchronized pedaling/wheels, a moving
seaside scene, responsive layout, pause/speed controls and reduced-motion support.
Likely files: the HTML artifact and this task record. Acceptance: inspect the SVG
and script, browser checks if a local browser is available, and `bash tools/check.sh`.
Resource budget: 20 minutes CPU wall time, at most four build jobs; zero project
GPU work. CONTRIBUTING and relevant task state were read before implementation.

Acceptance evidence: the self-contained SVG parses with unique IDs and resolved
references; JavaScript syntax passes. Chromium desktop (1440px) and mobile (390px)
previews were visually inspected. Browser checks passed for moving pedals,
pause/resume, exclusive pace selection, reduced motion, keyboard activation,
no horizontal mobile overflow and no script errors. Temporary browser dependencies
were extracted under /tmp; no system package or project dependency changed.
Full pinned-native `bash tools/check.sh` passed, including 121 Python tests,
79 documentation pages, policy checks, committed replay and bootstrap smoke.
Evidence is retained under artifacts/pelican-bicycle. No optimizer behavior,
research backlog, GPU campaign ledger or archived study evidence changed.

## GPUP-5 follow-up: diagnose FP32 latency (2026-09-16)

Status: complete; diagnostic evidence and full pinned-native acceptance passed.
The requested investigation preserves runtime behavior, all 480 original trials,
code objects, guards, controller, original-model authority and defaults. No GPUP-6
behavior or supported preset was introduced. See
[diagnosis report](../docs/benchmarks/lp-fp32-slowdown-diagnosis.md) and ADR-0020.

All 213 frozen GPU jobs ran under the shared lease: 196 equal-update repetitions,
14 Nsight Systems traces and three unsuccessful Nsight Compute counter attempts.
Every endpoint independently verifies and records exactly 200 proposals (206
physical steps with correction). Every decoded trace matches 1200 launches. Raw
traces initially failed automatic import; existing private libdw decoded them offline.
All counter attempts retain ERR_NVGPUCTRPERM; no driver permission was changed.
No retry, timeout, fallback or missing endpoint. Hardware bottleneck counters remain
unavailable, and first-200-update timings do not establish late convergence behavior.

Exact rational representation analysis covers 72 archived witnesses across all
twelve development models. All 166292 original coefficients are exactly FP32;
only 18 scaled values are. Concrete original-row violations exceed allowances by
34.2x/15.8x while meeting the implied represented-operator allowance. Other failures
also retain represented residuals, so quantization alone is not asserted for every
model. Equal-work FP32 savings are small or instance-dependent; extra iterations,
generic guarded execution, state readback and fixed correction dominate large losses.

Full pinned-native tools/check.sh passed before measurement (422 Rust tests,
119 Python tests, 78 pages) and on final tooling/documentation (422 Rust tests,
121 Python tests, 79 pages), including formatting, clippy, native HiGHS,
dependency policy, committed replay and smoke gates. Final log:
artifacts/gpup5-diagnosis-v1/native-final.log. Five new diagnostic tests cover schedule,
exact arithmetic, historical totals, phase/counter status and work-limit eligibility.
All 480 old endpoints reverify in a temporary copy; old report/index bytes and all
original indexed artifacts are unchanged. No runtime/device changes required another
sanitizer run; GPUP-5 device evidence remains intact.

Resources: four build jobs within the two-hour CPU validation ceiling; GPU jobs and
CPU acceptance sequential. Diagnostics consume 143.056235443 of their 300-second
cap, charged to screening, plus the preserved 1324.210639253 = 1467.266874696 total
GPU seconds, within 4502.574545061 and global/phase caps. GPUP-5 acceptance remains
80.458622460/900 seconds, unused here. All 213 reservations settled; complete
2862-event old prefix SHA-256
66d8c2b0ee24ce050ee051c6dbea2184361abe2c2fc4a57b8ee202c001479ff0 is preserved.
New 3288-event ledger SHA-256:
b3ca2739b1108a552b0423606ddd0cd94a8ed2323da1506098fa0150ba42bfef.

Evidence: artifacts/gpup5-diagnosis-v1 (frozen protocol/source/executable, raw runs,
traces/decoder commands, counter failures, disassembly, exact row diagnostics,
paired analysis and artifact hashes). Post-measurement changes affect only read-only
analysis/reporting/tests/documentation. No old report or evidence was rewritten.
Known failures and CONTRIBUTING were read first. GPUP-6 remains next, requiring its
bounded contract. No push or publication.

## GPUP-5: explicit FP32 comparisons and COPT baselines (2026-09-16)

Status: complete; full native, device, sanitizer and frozen-study gates passed.
Next ready task: GPUP-6, bounded adaptive contract before implementation.
The maintainer accepted the complete plan before behavior (ADR-0019 and
SPEC-0012/0013 amendments). cuda-lp-tuned now has strict lp-precision-v1, v4
records/replay, canonical FP32 storage/products/accumulation/state and charged fixed
FP64 correction. Original-model authority, prior behavior/code objects and unsafe
boundaries remain. COPT 8.0.6 CPU/GPU PDLP uses isolated ignored Python 3.11 bindings;
licenses remain in /root/copt80. No adaptive recovery or preset was introduced.

Evidence: [GPUP-5 report](../docs/benchmarks/lp-fp32-gpup5.md),
artifacts/gpup5-fp32-v1 and artifacts/gpup5-acceptance. All 480 attempts have verified
endpoints, exact schedule/provenance and settled ledger entries. No missing/invalid
endpoint, fallback or lease failure. Lower-precision failures remain in coverage.
Full pinned-native final gate: 422 Rust tests, 116 Python tests, 77 documentation
pages plus format/clippy/dependency/replay/smoke gates; native-final.log records the
pass. The exact measured source also passed its pre-study gate (421/115/76).
Final device suites: 47 cases.
All six precision cases pass memcheck/racecheck/initcheck/synccheck sequentially on
the original RTX 5090 with zero errors/race warnings. Six CLI/replay pairs and
missing-code pinned HiGHS fallback pass. Native COPT original-model min/max,
ranged-row and objective-constant fixtures pass; actual GPU preflight certifies.
Initial callback/log-wording preflight failures are retained. Final source adds an
independent device subnormal/tie/guard fixture and refuses COPT input coefficients
at or below its native discard threshold; every frozen model is above it.

Resources: four build jobs within a four-hour CPU validation ceiling. All GPU work
used the shared one-device lease. Acceptance used 80.458622460 of its separate 900
seconds. Study added 421.636094192 screening seconds to the preserved
902.574545061 seconds, totaling 1324.210639253 of 4502.574545061 allowed seconds.
The full 1902-event prefix SHA-256 remains
35b58ef0b0d58637288801bac2bdaa32b65b97b42b429debcffc615768c7c543;
final ledger SHA-256 is 66d8c2b0ee24ce050ee051c6dbea2184361abe2c2fc4a57b8ee202c001479ff0.
Global 28800-second and original phase caps remain. No ledger, archive, seeds,
thresholds, defaults or partitions were reset. Validation/held-out remain untouched.
Known failures/CONTRIBUTING were read before work. No push or publication.

## GitHub main protection (2026-09-16)

Status: complete; main protection is active and independently verified.
The user explicitly authorized protecting main on GitHub.
Follow release operations: require CPU, documentation and smoke checks; prevent
force pushes and deletion. Inspect existing rules and actual check identities
before configuring protection. Require pull requests with current checks, while
retaining the documented autonomous workflow without mandatory human approval.
No administrator bypass is planned. Preserve repository visibility, source history,
existing permissions and GPU/study evidence.

Acceptance: validate the concrete ruleset request, read back active rules and their
application to main, and record the final settings or any hosting-plan limitation.
CPU administration/documentation only, bounded to 15 minutes; no GPU work.
Evidence: artifacts/main-protection. Read release operations and known failures.

Created active [ruleset 23515452](https://github.com/liuyumou/OptForge/rules/23515452),
then independently read it back and checked the effective rules on main. GitHub
reports main protected and current_user_can_bypass=never. Required cpu/docs/smoke
contexts are bound to the observed GitHub Actions application ID 15368. PRs must
be up to date and have resolved review conversations. Approving-review count is
zero; no bypass actors, force pushes or branch deletion are allowed. Existing
merge methods remain available. Main's source commit was unchanged by configuration.

The exact request, response, verified ruleset and effective branch rules are saved
under artifacts/main-protection. Updated release operations and resolved the stale
main-protection blocker in known failures. Documentation uses a PR under the active
rules; do not push completion records directly to main or disable protection.

Full pinned-native acceptance passed in 18.739547708 seconds: 411 Rust tests,
110 Python tests, 74 documentation pages and all policy/replay checks. No source,
solver behavior, GPU work or study ledger changed. The documentation commit follows
the newly enforced PR and hosted-check requirements; integration receipts are
retained with the configuration evidence under artifacts/main-protection.

## GPUP-4 integration follow-up: supervisor timing fixture (2026-09-16)

Status: complete; fixture repair reviewed, merged and its branch removed.
PR #3 and branch cleanup completed after all six pre-merge
checks passed. The subsequent completion-documentation commit's CPU CI run
35041476887 found a pre-existing fixture timing assumption: coordinator-loss
supervision correctly reported timeout, but 1.340948131 leased seconds exceeded
an arbitrary one-second assertion. Preserve its failed hosted log and receipts in
artifacts/gpup4-pr-integration. Inspect the supervisor contract before changing tests.

Objective: make the coordinator-loss fixture assert independent timeout, complete
lease accounting and released ownership within its existing three-second outer
wait. Keep solve/cleanup limits, production supervisor and all GPU/study behavior
unchanged. Acceptance: targeted repeated fixture runs, full pinned-native gate,
reviewed follow-up PR with hosted CPU/docs/smoke checks, main synchronization and
branch cleanup. CPU only within the remaining integration budget; four build jobs.
No new study or GPU work. GPUP-5 interface handoff remains the next feature task.

Ten consecutive targeted coordinator-loss cases passed in 7.123434293 seconds.
The full pinned-native gate passed in 18.939487085 seconds: 411 Rust tests,
110 Python tests and 74 documentation pages, including all policy/replay checks.
Review confirms this changes only test assertions and documentation. The existing
three-second completion wait and 0.1-second solve/cleanup settings remain. Timeout
signal timing, negative child status, complete lease timing and nonblocking lock
reacquisition now establish the intended contract without assuming CI scheduling
or durable output always fits an additional one-second ceiling.

[PR #4](https://github.com/liuyumou/OptForge/pull/4) merged as
1b8e33d13138dcb2da751bd113d5560976c2c073. All six hosted CPU/docs/smoke checks passed for
reviewed head 8ced5d85e879a6191251ede1904e8bcb3246f792. The
[author review](https://github.com/liuyumou/OptForge/pull/4#pullrequestreview-5217393475)
verified the four file blobs and reports no blocking finding. The merge required
that SHA and preserved its exact tree. Main was synchronized and the local/remote
codex/gpup4-supervisor-fixture branches were deleted after ancestry verification,
with expected-head protection for remote deletion. The failed prior main run is
retained; its failure is not relabeled as a pass. New hosted receipts are in
artifacts/gpup4-pr-integration/hosted-fixture-pr.json. Final completion updates are
documentation only and pass the documentation/link gate. All study artifacts and
902.574545061 campaign GPU seconds remain unchanged. GPUP-5 is next.

## GPUP-4 PR integration and GPUP-5 interface handoff (2026-09-16)

Status: complete. The user authorized publishing the completed GPUP-4 branch,
reviewing and merging its PR after required checks, synchronizing main, and deleting
the completed feature branch. Preserve reference commits, ignored study archives,
code objects and the canonical 902.574545061-second campaign ledger.

Record the backend-interface recommendation in the GPUP-5 handoff and discovery
paths. This is planning guidance: GPUP-5 precision behavior and any interface
migration still require accepted contracts before implementation. No new study.
Read CONTRIBUTING, release operations and known failures before work.
Acceptance: complete diff/unsafe/dependency review, fresh full pinned-native gate,
hosted CPU/docs/smoke checks for the reviewed head, verified merge ancestry and
synchronized main before branch cleanup. Budget: 30 CPU wall minutes with four
build jobs; at most five GPU acceptance minutes only if a runtime review repair
requires them, sequentially under the shared lease. Existing device/sanitizer
results apply to unchanged runtime. Integration receipts: artifacts/gpup4-pr-integration.

Local review, acceptance, publication, hosted checks, merge and branch cleanup
are complete.
Full pinned-native tools/check.sh passed in 18.889058079 seconds: 411 Rust tests,
110 Python tests, 74 documentation pages, formatting/Clippy/rustdoc, dependency and
license policy, artifact checks and recorded replay. No runtime change or additional
GPU job was needed. Existing 41 regular device cases and eight scoped cases under
each of all four sanitizers remain applicable, with the documented device limitation.

Review covered the complete implementation diff, resident/restored state, bounded
cancellation and physical work, padded memory admission, deterministic reductions
and fusion, legacy schemas and code, strict execution/replay/provenance, fallback,
ledger reservations/admission, pairing/coverage and report limitations. No blocking
finding remains. The lockfile adds only a dev-dependency on existing serde_json;
SHA-256 moved unchanged into core and no new unsafe boundary was introduced.

Fresh read-only evidence verification checked all 640 trial records, 616 available
endpoints and 5530 indexed files across the preserved original and correction rounds.
The canonical ledger hash remains 35b58ef0b0d58637288801bac2bdaa32b65b97b42b429debcffc615768c7c543;
study consumption is unchanged at 902.574545061 seconds. GitHub sign-in was restored
with the maintainer's device authorization. At pre-merge review, remote main was
still the reference 722e0b01aecc5875b44ae0a7124f7c1b41eeeeed, so no rebase was needed.

The [GPUP-5 interface handoff](../docs/plans/gpup5-interface-handoff.md) recommends
versioned experimental precision settings, preserving existing backend identities
and replay, and revisiting the reserved quantized selector before behavior. It is
linked from AGENTS, the roadmap, SPEC-0012 and the GPUP-5 backlog entry; the interface
decision remains pending. This documentation does not begin GPUP-5 implementation.

[PR #3](https://github.com/liuyumou/OptForge/pull/3) merged as
1982bbf8f4522f604f899983990ec0a7e849a10e. All six hosted CPU CI, Documentation and
Benchmark Smoke push/pull-request runs passed for reviewed head
7820ccf688bb759107386120505dee38cb3288c2. All 59 PR file blobs matched the reviewed
local tree. The [author review](https://github.com/liuyumou/OptForge/pull/3#pullrequestreview-5217348891)
is a self-review comment, not independent peer approval. The merge API required the
reviewed SHA; the resulting tree matches it exactly and retains 4bca1a0, 722e0b0
and e415918 ancestry.

Local main was fast-forwarded to the merge. Remote feature-branch deletion required
its expected head, then the merged local codex/gpup4-fp64-execution branch was
removed. Study archives, reference code objects, ignored artifacts and the canonical
ledger remain intact. No new GPU work, ruleset change or release tag was introduced.
Machine-readable merge, review, hosted-run and preservation receipts are retained
in artifacts/gpup4-pr-integration. This completion record follows the merge; GPUP-5
remains the next bounded task, beginning with its pending interface decision.

The completion documentation passed the full pinned-native gate in 30.104146154
seconds (411 Rust tests, 110 Python tests, 74 documentation pages). Both local
gate receipts are retained; no additional GPU time was consumed.

## GPUP-4: tuned FP64 execution (2026-09-15)

Status: complete; all required gates and study evidence passed, ready for local
commit. GPUP-5 is next_ready_task; no GPUP-5 behavior is implemented.
Objective: explicit cuda-lp-tuned under accepted SPEC-0012/ADR-0017; resident
allocation, necessary uploads, deterministic warp32 and two-kernel fusion, with
recorded execution settings/provenance. Legacy/matched behavior and host authority
remain. Runtime and reference source/code were archived before measurement.

The [reviewed report](../docs/benchmarks/lp-tuned-fp64-gpup4.md) retains 640 attempts:
320 original plus the separately frozen ADR-0018 correction, each 280 GPU/40 CPU.
The original remains interim after 24 archived-reference execute-permission failures;
its source/binary bytes, failed attempts and charges are preserved. The full
correction has 248 certified endpoints, 66 work limits and six host timeouts, with
no process/invalid/missing evidence or unsettled reservations. Each configuration
certifies 27/36 timings. All 36 GPU endpoint pairs preserve bits and iteration/restart
counts across ablations. Matched remains the general reference; fused warp32 is a
provisional comparison on three named development instances only. No preset,
held-out solve, lower precision, dispatch, publication or push is introduced.

Study charges: prior 445.988045904; original round 219.094449232; correction
237.492049925; GPUP-4 total 456.586499157 of 900 additional GPU seconds. Cumulative
902.574545061, below the exact 1345.988045904 ceiling, 1800-second baseline phase
and 28800-second campaign. Original authority/output binding and the exact 622-event
prior prefix are preserved. Final study ledger SHA-256:
35b58ef0b0d58637288801bac2bdaa32b65b97b42b429debcffc615768c7c543.
Correction raw index SHA-256:
9b560b44b74f2035525a2d0c86ea5438f03097fdb203e2fb33723b3023a98b77.
Correction source/archive/executable/code identities are in the report and immutable
artifacts/gpup4-tuned-fp64-correction-v1. Native-freeze receipt binds measured source
8307df2ecb105552551058d93d885d10e93063695b188889fe520705ccdaef86.

Acceptance budget: 60 CPU wall minutes, four build jobs; 30 GPU minutes, sequential
with CPU gates. The measured source passed all 410 Rust/110 Python tests and 73 doc
pages in 19.140472299 seconds. All 41 regular device cases passed on RTX 5090 and
PRO 6000. Eight scoped cases passed each of all four sanitizers on PRO 6000, zero
errors/racecheck warnings. RTX 5090 lacked memcheck memory (797 MiB free); both
failed attempts remain recorded. The final parser-only schema repair was reproduced
by a failing regression and passes afterward; measured iteration code/settings/code
object are unchanged, and its untimed status is explicit in the report. Final
41-case RTX 5090 acceptance plus CLI evidence/fallback/replay/altered-code rejection
passed in 16.587609922 seconds. Total acceptance GPU use including failures:
479.537579339 seconds of 1800. Complete receipts/logs: artifacts/gpup4-acceptance.

Review fixes cover peak observations on early stops, cached launch configuration,
executor/residency agreement, GPU overflow, signed bits in both vectors/anchors,
strict enum shapes, complete ledger/trial coverage, torn-ledger read refusal,
immutable pre-campaign history and archive execution permission. GPUP-1 independent
rational authority and matched trajectory regressions remain. Only a dev-dependency
edge to existing serde_json was added; no external package version or unsafe boundary
changed. Read CONTRIBUTING and known failures before implementation.

Final full pinned-native acceptance passed in 35.965244998 seconds: 411 Rust tests,
110 Python tests, 73 documentation pages, formatting/Clippy/rustdoc, dependency and
license policy, artifact/provenance checks and recorded-run replay. Native and
focused schema-regression receipts total 177.027801669 CPU wall seconds; builds
used four workers and remained within the 60-minute acceptance allocation. Final
GPU acceptance including failed attempts totals 479.537579339 seconds of 1800.
The post-measurement parser-only change has a failed-before/passed-after fixture,
full native acceptance and fresh 41-case/CLI RTX 5090 acceptance. The report names
its measurement limitation. The complete diff, legacy schema/source preservation,
unsafe boundaries and lockfile were reviewed. Commit locally; no push authorized.


## GPUP-2/3 PR review and integration (2026-09-15)

Objective: publish the completed branch, review its full diff, merge after acceptance
and hosted checks, synchronize main, and delete the completed branches. The user
explicitly authorized PR creation, self-review, merge and cleanup. Preserve the five
bounded implementation/diagnosis commits, source archives, model hashes and the
445.988045904-second cumulative study ledger; no new experiment or GPUP-4 work.

Status: complete. [PR #2](https://github.com/liuyumou/OptForge/pull/2) is merged
as 3c8d1ffba2b79e527a1dd32bcea2e695eb34ae80. Local main is synchronized; the
remote and local codex/gpup2-lp-measurement branches were removed after merged
ancestry verification. The five bounded commits and e415918 reference are retained.
Reviewed CONTRIBUTING, known failures and accepted contracts.
Gate: full pinned-native tools/check.sh; full branch/unsafe/dependency/CI review;
successful remote CPU/docs/smoke checks; verified merged ancestry before cleanup.
Budget: 30 minutes CPU review/acceptance with four build jobs; up to five minutes
GPU acceptance only if a runtime review fix requires it, sequential with CPU gates
and under the shared lease. Existing device/sanitizer evidence remains applicable
to unchanged runtime. GitHub authentication is restored with the maintainer's sign-in; Git SSH access
works. Two review findings are fixed: CI now fetches full history for the archived
e415918 schema comparison, and the lease test observes worker readiness before
measuring queue wait. The initial full native gate caught the latter race (40.380
ms observed against its 50 ms requirement); this was fixture startup timing, not
a lease exclusion failure. The corrected fixture retained its threshold, gained
an assertion that no child output opens under the held lease, and passed ten
consecutive runs (2.553 seconds). No runtime, kernel or measurement artifact changed.

Fresh full pinned-native acceptance passed in 19.144629400 seconds: 405 Rust tests,
103 Python tests, dependency/license checks, committed-record replay and 69 doc pages.
Logs and the failed first run are retained in artifacts/gpup-pr-review. No additional
GPU work was necessary; prior 38 regular device tests and five scoped cases under
each of four sanitizers remain applicable. Review checked the complete branch:
native row multipliers and sense/order normalization, independent endpoint authority,
matched checkpoints/work/cancellation, legacy compatibility, outward reduction
ordering and signed zeros, frozen generation, schema strictness and provenance,
ledger/crash recovery, lease/activity/process cleanup, report pairing/censoring,
CI and the lockfile's single internal dependency addition. No blocking review finding
remains after the two integration fixes. Preserve the original commit history on
merge because the accepted reference source is named by its commit.

Hosted acceptance: CPU CI, Documentation and Benchmark Smoke all passed for both
push and pull-request runs of reviewed head faf4a9075fe218872d2d85563cb3406f665f0f9c.
The [self-review](https://github.com/liuyumou/OptForge/pull/2#pullrequestreview-5206719687)
is recorded as an author comment review, not independent peer approval. GitHub
confirmed the merge at 2026-09-15T07:13:44Z. The merge API required the reviewed SHA;
remote deletion used an expected-head lease. No branch protection or hosting
configuration was changed. Machine-readable run IDs, review URL and merge receipt
are retained in artifacts/gpup-pr-review/integration.json. Completion documentation
is committed after integration; GPUP-4 remains next with campaign use unchanged.

## GPUP-3: shared resumable matched FP64 control (2026-09-15)

Status: complete; acceptance passed, ready for local commit. SPEC-0012 accepted before implementation; ADR-0016 freezes
the opt-in FP64 contract and comparative protocol. Prerequisites committed separately
as 18fe686 (schema/activity) and 223ee6c (bit-preserving certification), each after
its full native gate. No legacy controller/default, numerical target or frozen
baseline artifact changed. GPUP-4 is the next dependency-ready task.

The [reviewed report](../docs/benchmarks/lp-matched-fp64-gpup3.md) retains all 160
attempts: 144 primary timings and 16 profiles, all development-only, in one
468.090-second invocation. Matched CUDA and current host certified 27/36 timing
trials; both legacy CUDA builds certified 6/36. Three scheduling instances remain
infeasible at the matched iteration limit. No invalid/missing evidence, device
failure or fallback occurred. All 33 mutually completed reference/current legacy
pairs and 27 mutually certified host/matched pairs agree on candidate, witness,
objective, bound and gap bits. The report includes paired intervals and limitations.

Budget: 251.845179881 additional GPU seconds from the allocated 600; prior
194.142866023 carried forward through the original authority. Cumulative is
445.988045904 of 900, preserving the 1,800-second baseline phase, 28,800-second
campaign and remaining allocations. All 160 distinct attempts settled, no pending
crash reservation. Pre-reservation waits total 55.605846414 seconds, lease queue
0.002241305 seconds; no study restart. Original baseline summary and ledger hashes
are unchanged. Current ledger SHA-256:
49ea15fc24a24fcabb4e677d6a684ea8a8d0d6c5fc1d1a52dba7b098c827a8f3.
Raw source/binary/schema identities and indexed artifacts are in the report.

Acceptance uses the separate 60-minute CPU/four-build-job and 30-minute GPU budgets.
Premeasurement full pinned-native gate passed: 405 Rust, 103 Python and 68 doc pages,
18.273888354 seconds. CPU gates/builds and device workloads were sequential.
The 38 regular GPU cases and five scoped cases under each of memcheck, racecheck,
initcheck and synccheck passed with zero errors; racecheck zero warnings. The first
combined job then caught a missing controller phase in endpoint-v2's schema.
Schema/parser parity and a CPU regression fixed it; a full native gate and targeted
leased CLI evidence/fallback/replay rerun passed. Runtime/controller/kernel output
was unchanged. Both attempts are retained. Total GPU acceptance was
77.351226566 + 2.322113705 = 79.673340271 leased seconds, within 1,800.

Logs: /tmp/gpup3-measurement-ready.log/.json, /tmp/gpup3-acceptance and
/tmp/gpup3-cli-acceptance. Durable copies are indexed under
artifacts/gpup3-matched-fp64-v1 along with raw trials and independent verification.
No precision work, persistent checkpoint format, preset, general runner or
publication is included.

Final gate: full pinned-native bash tools/check.sh passed in 18.284103359 seconds,
405 Rust tests, 103 Python tests and 69 documentation pages, with dependency/license
checks, unchanged-record replay and smoke verification. Evidence is retained in
artifacts/gpup3-final-acceptance/native.log and native.json. Native log SHA-256:
8601cc1a629acab78d33c6661d7ddea10d00d35b7603f8d5be827f7832ec5f90.
Only completion-state documentation and backlog selection changed afterward;
the source/kernel/device acceptance and measured artifacts remain intact.
GPUP-3's required gates are satisfied; GPUP-4 is ready, with no new work authorized
by merely selecting that backlog item. Local commit includes all bounded GPUP-3
implementation, acceptance and handoff documentation.

## GPUP-3 prerequisite: bit-preserving certification cost (2026-09-15)

Status: accepted for local commit. Full pinned-native gate passed in 22.844
seconds: 398 Rust tests, 98 Python tests and 68 documentation pages. New tests
compare 138 length/input combinations bit-for-bit with the retained padded reducer
and verify exactly n-1 live enclosure additions across segment boundaries. All
independent exact-rational certificate/gap fixtures pass. No GPU work occurred.
Logs: /tmp/gpup3-cert-tests.log and /tmp/gpup3-cert-gate.log/.json.

Optimize only outward reduction padding under ADR-0016.
Keep the partition, meaningful addition order, rounded/enclosure bits, signed zeros
and conservative refusals. Keep the literal padded differential oracle and GPUP-1
exact-rational authority. Acceptance: signed-zero/subnormal/cancellation/overflow
and segment-boundary differential cases, meaningful operation counts, full native
gate. CPU only, four build jobs, charged to the combined 60-minute acceptance cap.
No GPU work or campaign consumption; runtime reduction/controller settings unchanged.

## GPUP-2 follow-up: schema reuse and activity admission (2026-09-15)

Acceptance: completed. Full pinned-native tools/check.sh passed in 18.026 seconds,
396 Rust tests, 98 Python tests and 68 documentation pages. The targeted study
suite passed 26 tests in 2.172 seconds, including schema reuse/strictness, immutable
refresh, residual activity, process exclusion, telemetry refusal, exact wait limits
and a simulated post-lease race that launches no child. No GPU work occurred.
Reference executable SHA-256 remains 9538f9b16f1fdf3e224674a9c2e4f76f5e797022f730f858eaf63d2080b048fb.
Evidence: /tmp/gpup3-harness-gate.log and .json; /tmp/gpup3-harness-tests.log.

Status: accepted for local commit. First bounded change in the maintainer-approved matched FP64
plan, followed by bit-preserving certification and GPUP-3. Read CONTRIBUTING,
known failures and accepted contracts. Accept SPEC-0012 with later requirements
explicitly deferred; ADR-0016 freezes implementation and supplementary measurements.
Preserve original artifacts, legacy behavior and 194.142866023 seconds of campaign
consumption. Objective: immutable reusable schema registries and cancellable,
accounted GPU admission. Acceptance: strictness/activity/lease simulations and the
full pinned-native tools/check.sh gate. Combined acceptance budget across changes:
60 CPU wall minutes, four build jobs; 30 GPU minutes sequential with CPU gates.
Supplementary study cap: 600 additional GPU seconds, cumulative 900, baseline
1,800 and campaign 28,800 unchanged. Record exact evidence before local commits.

## GPUP-2 follow-up: Diagnose slow GPU study (2026-09-15)

Objective: measure and carefully explain solver latency, convergence, GPU setup,
certification and study orchestration costs requested by the maintainer. This is
bounded diagnosis of the existing FP64 baseline, not GPUP-3 implementation.
Status: complete; accepted for local commit. GPUP-3 remains next.
Read accepted contracts and known failures first. Preserve
all frozen trials, original solver settings and exact-rational regressions.
Budget: 30 minutes CPU diagnostic/acceptance wall time, four build jobs; at most
120 additional GPU study seconds within the existing 900-second Slice 2 allowance
and 1,800-second baseline phase. Prior campaign spending is 173.148261443 seconds.
GPU jobs use the same RTX 5090 UUID and shared host lease; CPU gates and device
jobs run sequentially. If device acceptance is needed, separately cap it at five
minutes. No publication or later-slice algorithm changes.

Plan: audit phase accounting and implementation; time original-model evaluation,
certification and reductions independently; replay fixed GPU control on the host;
profile Python schema/analysis overhead; use bounded driver/kernel traces on
selected development cases. Freeze supplementary diagnostic choices and ledger
extension before GPU launches. Retain raw profiles under ignored artifacts and
write a reviewed diagnosis with uncertainty, reproduction and resource accounting.
Acceptance: useful component/trajectory consistency checks, full pinned-native
tools/check.sh for committed tooling, and independently verified device endpoints.

Evidence: CPU component/replay diagnostics completed in 15.27 seconds. Both
50,000-step fixed CPU replays matched every primal/dual bit of the archived GPU
endpoints. The first full pinned-native gate passed in 41.317 seconds, with
396 Rust tests, 91 Python tests and 66 documentation pages. Seven supplementary
GPU jobs completed with independent endpoint checks, using 20.994604580 seconds;
canonical cumulative consumption is 194.142866023 seconds. No additional GPU
acceptance job was required. Four activity pauses resumed only unattempted jobs.

Both Nsight traces retained raw qdstrm files despite automatic importer failure.
A missing libdw.so.1 was supplied from a pinned Ubuntu package extracted privately
to /tmp; offline import/export then succeeded, without new GPU work. Both traces
contain exactly 1,200 kernels for 200 iterations. A reviewed report and strict
raw-prefix/hash/ledger/count analysis are in
[the diagnosis](../docs/benchmarks/lp-gpu-slowdown-diagnosis.md). Main findings:
fixed-controller convergence, repeated padded host certification, setup/launch
costs and redundant schema construction. GPU transfers are small on these cases.
No solver/controller/kernel/default changed.

Final acceptance: full pinned-native bash tools/check.sh passed in
39.866 seconds, with 396 Rust tests, 91 Python tests, 67 documentation pages,
dependency/license checks, committed-record replay and smoke verification. The
native gates total 81.184 seconds; CPU component/replay measurement used 15.271
seconds; four recorded resume invocations plus intervening waits used 174.924
seconds, dominated by repeated ledger/schema validation. The initial invocation,
Python profiling, builds, provisioning and offline trace analysis also remained
within the declared 30-minute CPU allocation. Final log/summary:
/tmp/gpup2-diagnosis-final.log and /tmp/gpup2-diagnosis-final.json. No CPU gate
ran concurrently with GPU jobs. All indexed raw artifact hashes were rechecked;
original baseline evidence is unchanged.

Cumulative ledger SHA-256:
9a1bed26e90ad69bc641355c68ca6edff055268a3971f948df69cc89abeb254f.
Diagnosis SHA-256:
0c79e7bb322df44fdcaa7cc8679d0a6c7347138d721562822638eb44b570a7cb.
Remaining original Slice 2 allowance: 705.857133977 seconds; remaining baseline
phase: 1,605.857133977 seconds; remaining total campaign: 28,605.857133977 seconds.
No budget reset, repeated attempt, changed numerical threshold or publication.

## GPUP-2: LP measurement infrastructure (2026-09-15)

Objective: implement the maintainer-approved Slice 2 plan: accepted contract,
frozen repository/generated workloads, independent host-lp/cuda-lp/HiGHS
endpoints, strict artifacts, crash-safe accounting and a baseline cost report.
Status: complete; accepted for local commit. GPUP-3 is the next ready task.
Known failures have been read. Preserve GPUP-1 rational
regressions and existing host/GPU controller differences; no later slice.
Acceptance: full pinned-native bash tools/check.sh; adversarial artifact,
endpoint, budget/crash/lease/cleanup and analysis tests; regular device suites
and relevant new cases under all four sanitizers; development measurements.
Budget: 60 minutes CPU acceptance wall time, four Cargo jobs; 30 minutes GPU
acceptance sequential with CPU gates. Study cap 900 GPU seconds from the 1,800
baseline phase within the 28,800 campaign total. Device is exclusively
GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48 under the shared host lease.
Likely files: diagnostic backend APIs, CLI solve/study, experiment types/schemas,
Python tooling/tests, frozen manifests/configs, SPEC-0013, ADR-0014 and task/docs.
No publication. Evidence and actual consumption follow below.

Pre-measurement acceptance: two full pinned-native gates passed (50.974 and
39.336 seconds), each with 396 Rust tests, 89 Python tests and 64 documentation
pages. Release solver/device-test preparation took 10.299 seconds. Additional
CPU orchestration checks exercised one complete trial and an interim report with
source archive/raw-reference validation, with no GPU work. The second gate
includes a correction preventing --output from creating a fresh campaign ledger.

Device acceptance: all 35 regular device cases passed on the pinned RTX 5090.
Both new study_observation cases passed under memcheck, racecheck, initcheck and
synccheck, with zero errors; racecheck also reported zero warnings. The first
combined invocation exited 1 only at the CLI fallback fixture: it hid the
scheduling code object required to open a session, before LP fallback was reachable.
The corrected fixture preserves that object and hides only lp_pdhg.cubin.
The targeted CLI rerun passed device evidence and pinned fallback verification.
No runtime code changed for this fixture correction. Total GPU acceptance was
27.249 + 1.266 = 28.515 seconds, well within 1,800. Logs and timing JSON are in
/tmp/gpup2-gpu-acceptance.* and /tmp/gpup2-gpu-cli.*. This is the declared scoped
sanitizer acceptance, not a claim of running the historical broad sanitizer suite.

The third full pre-measurement native gate passed in 39.966 seconds with the
same coverage. All 144 development attempts then completed: 108 timing trials,
36 separate profiles, 48 GPU jobs. The canonical campaign ledger charged exactly
173.148261443 GPU seconds; CPU-only jobs used 202.666858567 seconds and additional
standalone host verification used 24.459310130 seconds. Two activity pauses resumed
on the same device/ledger without repeated trials. No validation/held-out solves.

The [reviewed baseline](../docs/benchmarks/lp-baseline-gpup2.md) records medians,
paired intervals, coverage, work, phases, memory, certificate quality and raw hashes.
CUDA certified 6/36 timing trials (two small witness cases), host LP 27/36 and
HiGHS 30/36. No fallback or malformed evidence occurred in the campaign. Failure,
work-limit and deadline evidence is retained. No solver default, seed, split or
numerical threshold moved; the exact-rational GPUP-1 regressions are unchanged.

Raw artifacts: artifacts/gpup-baseline-v1, with canonical budget storage in
artifacts/lp-campaign-ledgers/gpup-baseline-v1. Ledger SHA-256 is
aee3f1398725fedf8ad37d644c8960156b897b3a11478839359def4619eb8e37;
summary SHA-256 is c57de898e75b5c422efd09ed3590e8e9d39f97f2b50ce99535f63d1c41a6cc63.
The measured dirty source is archived and hashed in the report. Preserve spending
when a later slice introduces a recorded campaign migration. Remaining baseline
phase is 1,626.851738557 seconds; remaining total is 28,626.851738557 seconds.

Final review tightened the supervisor after measurement: persist SIGINT intent
before escalation, reap orphaned process-group children before releasing the lease,
and stream artifact hashes after checking model size. Fifteen targeted study tests
passed, including exact simulated deadline boundaries and orphan cleanup. Existing
raw measurements and their source archive remain intact; these tooling-only edits
introduce no solver, kernel, controller or protocol-setting change.

Final acceptance: bash tools/check.sh passed with pinned native HiGHS 1.11.0,
396 Rust tests, 91 Python tests, 65 documentation pages, dependency/license checks,
committed-record replay and smoke verification (39.666 seconds). The four full
native gates total 169.942 CPU wall seconds; release preparation was 10.299 seconds,
the last focused study tests 5.891 seconds, and explicit Rust validation of all
32 frozen models plus 24 planted primal witnesses was 1.215 seconds. Earlier
bounded orchestration/interim-report checks added approximately 4.17 seconds;
acceptance remained below the 3,600-second CPU allocation with four build jobs.
Logs: /tmp/gpup2-cpu-final.log and timing JSON; /tmp/gpup2-partition-validation.*.

The final supervised GPU CLI/evidence/fallback check passed in 1.467 seconds
(leased job 1.308638432 seconds). Signal history was empty for the successful job;
forced-signal and orphan-reaping cases passed the CPU simulation tests. Including
the prior regular suites, all four scoped sanitizers and failed fixture attempt,
GPU acceptance totals 29.981850548 seconds of 1,800. Its machine-readable worker
record is /tmp/gpup2-final-supervisor/acceptance.worker.json; summary is
/tmp/gpup2-gpu-final.json. No CPU gate overlapped device acceptance.

Slice 2's gate is satisfied. Preserve the accepted source/records, exact-rational
regressions, frozen splits/settings, unsuccessful trials and cumulative campaign
spending. GPUP-3 must accept SPEC-0012 before implementing shared resumable FP64
control. No mixed precision, C10 runner, supported preset or publication is included.

## GPUP-0/1 PR Review and Integration (2026-09-14)

Objective: review the roadmap and certification repair, publish one PR preserving
both slice commits, record the review, merge through GitHub after acceptance,
synchronize local main, and remove the two completed branches. The maintainer
explicitly authorized publication, self-review, merge, and branch cleanup.

Status: complete. PR #1 is merged, main is synchronized, and both completed
local branches plus the published feature branch have been removed. Base main is ee2d4fe; reviewed implementation is 61c53f4,
which includes roadmap commit f28bf0e. No later precision slice is in scope.

Acceptance gate: numerical proof and caller review; full pinned-native CPU gate;
finish the previously incomplete broad GPU sanitizer coverage if the bounded
integration allocation permits, otherwise explicitly assess the existing scoped
coverage; successful PR CI; remote merge confirmation and clean synchronized main
before branch deletion. GitHub author self-approval restrictions must be respected;
record the review without changing branch protections if formal approval is refused.

Resource budget: at most 30 minutes CPU gate wall time with four Cargo build jobs
and 30 minutes additional GPU acceptance on one device under the shared host lease,
sequentially with the CPU gate. Profiling and performance trials remain out of scope;
the eight GPU-hour research campaign is unspent. Likely files: active task, known
failures/publication state, and review evidence; runtime changes only for review
findings, with a fresh gate before publication.


Review evidence: checked the finite enclosure primitives, concave variable-bound
contributions, row repair, objective-sense conversion, conservative tolerance
arithmetic, both backend callers, and the shared reduction tree. The independent
Fraction oracle evaluates the stored coefficients without copying the interval
algorithm. No blocking numerical or contract finding was identified. Original-model
feasibility remains tolerance-based, and interval dependency can weaken/refuse a
certificate; neither limitation is hidden by the gap result. No runtime edit was
needed. The two original slice commits remain separate.

The fresh full CPU gate passed (23.30 seconds, pinned native HiGHS covered), with
390 Rust tests, 76 Python tests and 62 documentation pages. A GPU launch without
the provisioned Rust PATH failed before device work (0.08 seconds). The next run
failed from CUDA context allocation on the busy RTX 5090 (4.31 seconds); both
5090s had approximately 30 GiB allocated by other activity. Those processes were
left untouched. Remaining acceptance moved to the idle RTX PRO 6000 Blackwell,
UUID GPU-6721b13a-30f9-83ec-dace-ba2d9738556f, under the same host-wide lock and
remaining total budget. A temporary sanitizer wrapper adds --error-exitcode 99;
no test counts, timeouts inside tests, or numerical thresholds were reduced.

Publication readiness: the reviewed slice commits were pushed to
codex/fix-lp-certification through SSH. The maintainer completed GitHub CLI browser
login, enabling API access as liuyumou. Main was unprotected; merge settings and
protections remained unchanged. [PR #1](https://github.com/liuyumou/OptForge/pull/1)
was opened as a draft with its review prepared locally. Documentation and benchmark
smoke CI passed first; CPU CI initially hit the tooling-cache finding below.

Integration finding: the first remote CPU CI run failed before acceptance during
cargo-deny installation (run 34859538269, job 104027791392). The Cargo cache restores
bin/ but not Cargo installation metadata, so reinstalling reports "binary
cargo-deny already exists in destination". Bounded correction: verify the cached
binary reports exactly cargo-deny 0.19.0; reuse that version, otherwise install the
same pinned locked package with --force. No toolchain or dependency version changes.
The final local gate and remote CI must pass after this workflow edit.

Sanitizer scope decision before the remaining runs: the broad PRO 6000 job was
stopped after 1,294.10 seconds during the existing atomic-reduction negative-control
stress case under racecheck. The 20,000-iteration publication test had completed
successfully under racecheck; the original Slice 1 coverage gap at that case is
therefore narrowed. The entire broad job is still not a completed gate. Use the
remaining total allocation for all three full initcheck and synccheck suites,
both non-LP full racecheck suites, and the 11 other LP racecheck cases (excluding
the already-observed publication case and the unfinished atomic stress case).
Keep error-exitcode 99 and every test's internal settings unchanged. Review accepts
this explicit sanitizer coverage for a host-only arithmetic repair with unchanged
kernels and prior scoped coverage on RTX 5090; it does not waive a known numerical
failure or claim the entire broad sanitizer gate passed.

Final device evidence: the nine supplemental invocations all passed with exit 0
in 251.97 seconds. Full initcheck and synccheck each ran 13 LP, six scheduling,
and 14 CUDA tests with zero errors. The completed racecheck invocations ran 11 LP,
six scheduling, and 14 CUDA tests with zero errors and warnings; only the LP
invocation filtered the two explicitly named cases above. Together with all
regular device suites, all three full memcheck suites, the observed long publication
test completion under racecheck, and the prior RTX 5090 scoped checks, this is the
accepted coverage. The unfinished atomic negative-control racecheck remains a
known acceptance limit, not a full broad-gate pass. No device test silently skipped.

Total additional GPU acceptance: 1,550.46 seconds including both failed launches,
the stopped broad job, and supplemental checks; within 1,800 seconds. No CPU gate
overlapped GPU acceptance, and the performance campaign remains unspent. Logs:
/tmp/gpup-pr-cpu.log, /tmp/gpup-pr-gpu-launch-failure.log,
/tmp/gpup-pr-gpu-5090-oom.log, /tmp/gpup-pr-gpu.log, and
/tmp/gpup-pr-remaining-sanitizers.log, with timing summary JSON siblings. These are
ephemeral acceptance diagnostics. Reproduction and scope are recorded in
[LP certification arithmetic](../docs/architecture/lp-certification.md).

Final local acceptance after the CI/documentation edits: bash tools/check.sh passed
with pinned native HiGHS 1.11.0, 390 Rust tests, 76 Python tests, and 62 documentation
pages (23.53 seconds; /tmp/gpup-pr-cpu-final.log and its timing summary). The CI setup
shell passed bash syntax validation, and the cached-tool guard's version string was
checked against the actual pinned binary. The original runtime and CUDA files are
unchanged from 61c53f4. PR CI, review publication, merge, and cleanup follow this
accepted local tree. Final integration evidence follows.

Integration evidence: both push and pull-request CPU, documentation, and benchmark
smoke CI passed on PR head 1930a0b09c4b0c0f9c8009111480203c0592fc12. CPU workflow
runs 34862464456 and 34862468896 passed; manual-only GPU discovery was skipped as
configured and is not GPU acceptance evidence. GitHub rejected a formal author
APPROVE review ("Can not approve your own pull request"). The completed technical
approval, including acceptance of the sanitizer scope, is published as a
[COMMENT review](https://github.com/liuyumou/OptForge/pull/1#pullrequestreview-5199671767).
This is the requested agent self-review, not an independent human review or a
formal GitHub approval event. No branch protection or merge setting was changed.

GitHub confirmed PR #1 merged at 2026-09-14T15:32:28Z, merge commit
2c84a95e8580bb51ac74dff6bfe4535b2edbb282. The rebase check was a no-op against
unchanged main ee2d4fe. A merge commit preserves the original roadmap, numerical
repair, and review-evidence commit identities and their documentation references.
The merged tree exactly matches the CI-tested PR head. Local main fast-forwarded;
both former branch tips were verified as ancestors before deletion. The remote
feature branch was deleted with an expected-head guard, both local branches were
removed with git branch -d, and remote references were pruned. The roadmap branch
had never been published.

Post-merge audit acceptance: bash tools/check.sh passed on synchronized main
with the completed task/publication records (33.46 seconds), again covering pinned
native HiGHS, 390 Rust tests, 76 Python tests and 62 documentation pages. The log is
/tmp/gpup-pr-main-audit.log with its timing summary. Total local CPU gate wall time
for integration was 80.29 seconds, within the declared 30-minute allocation.

This post-merge audit changes task/publication records only. Follow-up remains
GPUP-2: finalize and accept SPEC-0013 before the LP experiment harness. No later
slice, performance experiment, or supported low-precision recipe was introduced.

## GPU LP Precision Slice 1: Conservative Certification (2026-09-14)

Objective: reproduce and repair the zero-reduced-cost cancellation defect, bound
rounding uncertainty conservatively through certification, and review objective/gap
arithmetic and minimization/maximization termination in both first-order backends.

Status: complete. GPUP-0 is complete; this is GPUP-1 only.

Acceptance gate: independent exact-arithmetic regressions, the full
`bash tools/check.sh` gate with pinned native HiGHS, and the device acceptance and
sanitizer gate if the shared host-side change reaches device integration. Resource
budget: up to 60 minutes CPU gate/test wall time with four Cargo build jobs; up to
15 minutes GPU acceptance under the shared host lease on one device, sequentially
with the CPU gate. No performance study jobs; the eight-hour campaign remains
unspent. No GPU kernel or iteration arithmetic change is planned.

Likely files: optimizer-lp certification, a private outward-arithmetic helper,
shared objective/gap assessment, host/device backend integration, regression
fixtures and exact validation tooling, SPEC-0011, numerical documentation,
changelog, known failures, roadmap and backlog. No new runtime dependency or
unsafe boundary is authorized. Existing caller tolerances remain unchanged.

Evidence (2026-09-14): the rounded-zero and free-variable regressions both failed
against the old certifier, which returned bound 0 and allowance 0. The separate
maximization gap regression also failed before repair. All now pass. The rational
oracle covers 1,083 primitive arithmetic cases, five fixed-tree sums (including a
multi-segment sum), 26 certificate cases, and 18 objective/gap cases; the Python
integration gate independently regenerates the fixture from exact Fractions.

The final `bash tools/check.sh` passed, exit 0: pinned native HiGHS 1.11.0,
390 Rust tests, 76 Python tests, artifact/provenance validation, committed-record
re-execution, and 62 documentation pages. The final gate took 27.46 seconds; both full CPU gates stayed within the
declared allocation and ran sequentially with GPU acceptance.
No runtime dependency, GPU kernel, original-model coefficient, caller tolerance,
experiment seed/split, or solver default changed.

Device evidence: RTX 5090, UUID GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48,
driver 580.105.08, provisioned CUDA 13.0 code objects. All three regular device
suites passed, including the new maximization case and existing bitwise iteration
comparisons. All three full memcheck runs reported zero errors. The broad
`tools/gpu_check.sh` sanitizer invocation was explicitly stopped during the
existing 20,000-iteration publication test under racecheck; **the full broad
sanitizer gate did not complete and is not claimed as passed**.

Bounded replacement coverage: memcheck, racecheck, initcheck, and synccheck each
ran the new one-iteration maximization integration, the existing 400-iteration
CPU/GPU bitwise comparison, and the wide-row differential case. All 12 scoped
runs reported one executed passing test and zero errors, with no skips. The
scoped commands set `--error-exitcode 99` and retained the existing test iteration
counts/thresholds. This is the relevant sanitizer coverage for unchanged kernels
with repaired host-side certification/gap arithmetic; reproduction commands are
in docs/architecture/lp-certification.md.

The stopped broad job consumed 499.99 seconds and the scoped checks 59.74 seconds:
559.73 seconds total acceptance wall time, within the 900-second allocation,
on one device under the shared host lease. Performance campaign consumption is
zero. Local logs and machine-readable timing summaries are in
`/tmp/gpup-1-cpu-final.log`, `/tmp/gpup-1-gpu-acceptance.log`, and
`/tmp/gpup-1-scoped-sanitizers.log` with sibling summary JSON files. These are
ephemeral acceptance diagnostics, not retained performance artifacts.

Resolution: certification carries outward enclosures through original-model
products, reductions, reduced costs, variable contributions, and the final sum.
Both LP backends use the shared outward objective/gap check, including sense
conversion and conservative finite tolerance arithmetic. Certificate fields stay
compatible; LP record gaps remain absolute objective-unit diagnostics, now
nonnegative conservative upper bounds. Feasibility and reported objective values
retain their existing tolerance-based meanings. Interval dependency and overflow
can weaken or prevent a certificate, as the numerical documentation records.

Follow-up: GPUP-2 is ready. Complete and accept draft SPEC-0013 before implementing
the LP-only measurement harness; freeze its concrete manifests, artifacts,
analysis and campaign accounting before performance trials. This repair satisfies
the certification prerequisite and does not implement mixed precision, select a
recipe, or complete C7/C9/C10.

## GPU LP Precision Slice 0: Roadmap and Contracts (2026-09-14)

Objective: persist the user-approved GPU LP performance roadmap as a separate,
dependency-ordered research track, draft its numerical and experiment contracts,
and record the prerequisites before any new arithmetic is implemented.

Status: complete. This slice changes documentation and task state only.

Acceptance gate: `bash tools/check.sh` with the pinned native HiGHS build,
documentation link/anchor validation, and a manual requirement-to-test and backlog
dependency review. Resource budget: CPU only, at most 30 minutes of gate wall time
with four Cargo build jobs; zero GPU work. The first later experiment campaign has
an eight GPU-hour cap, not a budget consumed by this documentation slice.

Likely files: the new roadmap under `docs/plans/`, two draft specifications,
arithmetic/reproducibility and experiment ADRs, project navigation, benchmark
protocol, changelog, backlog, and known failures. Existing runtime behavior,
experiment seeds, splits, thresholds, and solver defaults remain unchanged.

Acceptance evidence (2026-09-14): `bash tools/check.sh` passed, exit 0, with
pinned native HiGHS 1.11.0, 380 Rust tests, 72 Python tests, artifact/provenance
validation, committed-record re-execution, and 61 documentation pages with valid
local links/anchors. The gate completed within the 30-minute CPU wall-time budget;
GPU jobs and GPU campaign consumption: zero. The full local gate log is
`/tmp/gpup-0-acceptance.log` (ephemeral, not a retained benchmark artifact).

Supplemental review checked all 38 SPEC-0012 and 35 SPEC-0013 numbered requirements
against their planned acceptance mappings, unique backlog identities and ordered
dependencies, the campaign allocation sum (28,800 GPU seconds), and the exact
rational objective in the cancellation counterexample. These are documentation
and planning checks; none is recorded as runtime precision or performance evidence.
No runtime source, schema, dependency, experiment manifest, seed, threshold, or
default changed. ADR-0012 and ADR-0013 accept design decisions; SPEC-0012 and
SPEC-0013 remain drafts requiring completion before their implementation slices.

Follow-up: GPUP-1 is ready under the existing SPEC-0011 certification contract.
Reproduce the recorded cancellation case with an independent exact-arithmetic
fixture; repair conservative reduced-cost/contribution handling including uncertain
signs and infinite bounds; review objective/gap rounding and objective-sense
conversion; run the full gate and record evidence before any lower precision.
The known-failure entry remains open. GPUP-2 then finalizes and accepts the LP
experiment contract before implementing measurement. C7/C9/C10 remain planned,
and repeated-solve throughput and full MILP performance are separate future tasks.

## C6 Clean-Checkout Verification and Local Integration (2026-09-13)

Objective: verify C6 from a checkout with nothing prebuilt before integrating it, as
the C4, C8 and Track B branches each were, and as this branch already was at `6dbaf8c`
when only SPEC-0010 was implemented.

Status: complete. The branch is integrated into local `main` by fast-forward.

Acceptance gate: `bash tools/check.sh` passes in an independent clone with no `target/`
directory, no provisioned HiGHS library, no provisioned device code object, and no CUDA
toolkit on `PATH`. Resource budget: CPU only, no GPU workloads — which is itself part of
what is being verified.

The earlier verification at `6dbaf8c` no longer covered the tree. Eight commits since
then added two crates, a schema, two examples, a step to the acceptance gate itself and
a second code object, and every one of those is surface a clean clone exercises and a
warm working tree does not. Re-running it was the point of having the ritual.

What the clone establishes that a local run cannot. The build script's warning fired
four times, so `cuda_native` was unset throughout and every device path compiled to its
unsupported form: ADR-0009's "nvcc is a provisioning dependency, never a build
dependency" observed rather than asserted, and now covering the linear-programming
kernels as well as the integer ones. `nvcc` was absent from `PATH` deliberately. The
pinned HiGHS library was built from source inside the clone, so native acceptance was
covered rather than skipped — the loud banner did not print and the differential test
against the standalone reference ran. And the twelve device tests reported their skips
rather than failing, which is what keeps a host with no GPU a full gate pass.

Evidence (2026-09-13): cloned with `--no-hardlinks` at `d7c2118` with no `target/`
present; `bash tools/check.sh` passed there, exit 0, with 380 Rust tests, 72 Python
tests and 56 documentation pages — the same counts as the working tree.

`Cargo.lock` gained three workspace entries across this branch: `optimizer-cuda-sys`
from the device work, and `optimizer-lp` and `optimizer-lp-cuda` from the
linear-programming work. No third-party crate was added — the diff contains no new
`source` line — so the workspace still resolves the same eighteen external packages,
which is what `cargo deny --locked check` confirms on every gate run. No code object,
native library or other build output is tracked; `git ls-files` finds no `.cubin`,
`.ptx`, `.so`, `.a` or `.o`.

Integration was a fast-forward. `main` had not moved, so the branch was already linear
on top of it and the rebase CONTRIBUTING.md asks for before integration was a no-op;
this repository's history carries no merge commits and that is preserved.

Not pushed. Everything after `dfdc245` remains local, as `state/known-failures.md`
records, and publishing needs authorization this task does not carry.

Follow-up: C6 is complete and integrated. C7 is next and has no specification; it needs
one before any behavior.

## C6 Evidence and the Limits It Carries (2026-09-13)

Objective: reach SPEC-0011 requirements 17, 20, 21, 22 and 23 — the two tests ADR-0010
names as the ones that can fail, the fallback, and the rule that no acceptance artifact
records a timing — and record what C6 does not establish.

Status: complete. C6 is complete: both its contracts are implemented with evidence, and
the backlog line closes.

Acceptance gate: `bash tools/check.sh` plus
`bash tools/gpu_job.sh <uuid> bash tools/gpu_check.sh`. Resource budget: one GPU under
the shared host lease, for the device runs only.

Requirement 22 needed an early-stopped iterate to mean anything. At convergence the
certified bound and the pinned backend's can round to the same `f64` — that backend
sets its bound equal to its objective for a continuous LP — so a converged instance
would have made "strictly weaker" turn on rounding rather than on the procedure. Three
iterations produce a bound that is valid and visibly weaker, which is what ADR-0010
asks for: a certificate that only ever agrees has not been shown to be a certificate.

The other able-to-fail test asserts three things because the hazard has three parts. A
point outside the row bound looks better than the optimum, `Model::evaluate` refuses it,
and no multiplier — including two scaled by 1e9 — turns into a bound below the true
optimum. A wrong kernel's most dangerous output is a plausible number better than the
truth, and two independent host computations stand in its way.

Requirement 20's fallback is provoked by a code object that is not there, which is a
real availability failure rather than a simulated one, and the test asserts the failure
fired before asserting the agreement. Without that ordering the agreement would hold
just as well if the device had quietly succeeded.

One gap was found by running the end-to-end command rather than by reading the
contract. The device backend ran to its iteration limit and assessed once, so the
recorded check interval changed nothing — requirement 10 exists precisely to stop an
interval being a number that is recorded and ignored. It now assesses at each interval,
and a test asserts both halves: that the interval is consulted, and that changing it
leaves the iterates bit for bit identical. The second half is the one that could have
gone wrong quietly, because the Halpern coefficient sequence has to continue across an
interval boundary rather than restart at it.

Seven entries were added to `state/known-failures.md` rather than left implied: no
dispatch threshold for either contract, a fallback that cannot be verified field for
field, the difference between a device that cannot be opened and one that fails after
opening, tolerances reused as an optimality-gap policy, bitwise CPU/GPU identity being
this project's property rather than the contract's, the third device suite not running
in CI either, and the two candidate explanations any weak bound on a scheduling
instance would have.

Evidence (2026-09-13, RTX 5090, driver 580.105.08, CUDA 13.0):
`bash tools/check.sh` passed, exit 0, 380 Rust tests, 72 Python tests, 56 documentation
pages, every device test reporting an explicit skip.
`bash tools/gpu_job.sh GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48 bash tools/gpu_check.sh`
passed, exit 0: three device suites, twelve sanitizer runs across memcheck, racecheck,
initcheck and synccheck, zero errors.
End to end, `optimizer solve --backend cuda-lp --device GPU-...` writes a record naming
`cuda-lp`, carrying the settings that produced it, an objective the host recomputed and
a bound below the true optimum, and terminating as `iteration_limit` rather than
claiming a proof it did not have at the caller's tolerance.

One observation worth carrying: `tools/check.sh` is CPU-only but not independent of
device activity. `test_a_named_device_is_refused_rather_than_run_on_the_cpu` blocked for
the lease's full timeout while a device gate held it, and the gate failed on a timeout
rather than on a defect. That is the lease behaving as SPEC-0006 specifies, not a new
fault, but running both gates at once on one host does not work.

Follow-up: C6 is complete. C7 is next and has no specification; it needs one before any
behavior.

## C6 First-Order LP Kernels on a Device (2026-09-13)

Objective: reach the device halves of SPEC-0011 requirements 5 to 8 — the iteration's
kernels in `f64` on a leased device, with the reduction order fixed so a result cannot
depend on how the hardware scheduled it.

Status: complete. This is the last implementation slice of SPEC-0011 and therefore of
C6.

Acceptance gate: `bash tools/check.sh` on the CPU, where every device test reports an
explicit skip, plus `bash tools/gpu_job.sh <uuid> bash tools/gpu_check.sh` on hardware.
Resource budget: one GPU under the shared host lease, for the device runs only.

`optimizer-lp-cuda` is a separate crate rather than a module in `optimizer-cuda`. That
crate is what every existing GPU consumer depends on, so putting the LP engine there
would force `optimizer-cuda` to depend on `optimizer-lp` and make the CLI and the
scheduling examples compile an engine none of them calls. It would also put a `Backend`
implementation in the crate that owns discovery and the lease. The new crate inherits
the workspace lints, so it forbids unsafe and opens no second boundary: it reaches
hardware only through `optimizer-cuda-sys`, which is the one ADR-0009 authorizes. The
single change to that boundary is an `F64` kernel argument, which requirement 5 makes
unavoidable.

A real defect was caught before it could hide. The first kernel accumulated per-segment
partials left to right while the host reduces them by the same tree. Those orders agree
for any line of at most `SEGMENT` entries and disagree for every wider one, so the
models this project currently produces would all have passed and the defect would have
surfaced later as an unexplained disagreement on a large instance. The kernel now
performs the same two-level recursion, and a test builds a deliberately wide row to
exercise the second level — without it the agreement tests would only ever cover the
single-segment path.

The able-to-fail instrument for determinism substitutes the atomic reduction *inside*
`spmv_row` rather than adding a second kernel beside it. A separate kernel could drift
from the real one and leave the instrument measuring something else; substituting into
the production path is also literally what the specification's acceptance section asks
for. The first attempt did add a separate kernel, reached by hand-written launch code in
the test, and that code faulted — which is its own argument for exercising the machinery
the other tests use.

Bitwise CPU/GPU identity holds and is asserted, but it is this project's property rather
than the contract's. Requirement 8 asks only for same-device reproducibility. The
identity needs `-fmad=false` on the device, Rust never contracting on the host, and the
`log`, `exp` and `sqrt` staying host-side; the test re-verifies it on every run instead
of assuming it. A tolerance was rejected because a tolerance on an iterative method is
nearly untestable: loose enough to pass at iteration ten thousand, it hides a real
defect at iteration ten.

`tools/check.sh` gains a grep for atomic accumulation outside the guarded build. It is
CPU-only and it is the sole guard on a host with no GPU, where the device suite reports
a skip. Its first version flagged the file's own documentation of the prohibition and
was tightened to match the call rather than the name; both directions were then checked.

Evidence (2026-09-13, RTX 5090, driver 580.105.08, CUDA 13.0):
`bash tools/check.sh` passed, exit 0, 372 Rust tests, 72 Python tests, 56 documentation
pages, with all ten device tests reporting explicit skips.
`bash tools/gpu_job.sh GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48 bash tools/gpu_check.sh`
passed, exit 0: three device suites and twelve sanitizer runs, three binaries under each
of memcheck, racecheck, initcheck and synccheck, zero errors.

Follow-up: the evidence record and the limits that must be carried rather than hidden.

## C6 Backend Selection at the Run Surface (2026-09-13)

Objective: reach SPEC-0011 requirements 18 and 25 — the first-order backend
reachable by explicit caller configuration, with the pinned CPU backend still the
default, and the settings document a caller supplies validated by both authorities.

Status: complete for the host backends. Requirement 20's fallback and requirement 17's
relaxation forfeiture belong to the device backend and are not reached yet.

Acceptance gate: `bash tools/check.sh` with the pinned HiGHS library present.
Resource budget: CPU only, no GPU workloads.

`optimizer solve` gains `--backend` and `--lp-settings`. The default is the pinned
backend, and it is the default in the strongest available sense: there is no threshold
anywhere that could promote a solve to another backend, so nothing could say otherwise.
That is deliberate rather than unfinished. Requirements 18 and 19 make a dispatch
threshold a recorded measurement, and `state/known-failures.md` already records for
SPEC-0010 requirement 22 that this project commits no such number without an ADR and
held-out evidence. The same entry now covers two specifications.

Settings are required rather than defaulted when the first-order backend is named, and
`--lp-settings` is refused outright for a backend that has none. A caller who thinks
they configured something is told they did not, rather than having the flag ignored.

`lp-settings-v1` is its own schema rather than a block inside the record. It is a
document a caller passes on the command line, so it needs to be checkable on its own,
and the record `$ref`s it exactly as it already `$ref`s the solve configuration. Both
authorities are asserted to refuse the same documents: the Rust parser and the JSON
Schema each reject a settings document missing any recorded field, and a record
embedding an incomplete block is rejected too.

`examples/lp-model-v1.json` is new because the existing example model is discrete, so
the specification's own worked example would have refused. Both examples are now
validated by `tools/validate_artifacts.py`, so a committed example cannot drift from
the schema a record embeds it under.

Evidence (2026-09-13): `bash tools/check.sh` passed, exit 0, with 362 Rust tests, 72
Python tests and 56 documentation pages. Eleven tests are new. The default reaching the
pinned backend is asserted positively, on the backend named in the record rather than
by observing that nothing else happened. Both backends are shown to agree on the
example model, which is what makes naming one a choice of implementation rather than a
choice of answer. The discrete refusal is asserted end to end at the run surface, not
only in a unit test: exit 2, `unsupported`, and the record still names the backend that
refused.

Follow-up: the device kernels, then the evidence record and the honest limits.

## C6 Host First-Order Engine and Backend (2026-09-13)

Objective: reach SPEC-0011 requirements 3, 5, 8, 10, 14 to 16, 21 and 24 to 26 — the
restarted primal-dual method on the host, a backend that claims only what two
independent computations support, and a record that states the settings it ran under.

Status: complete. Requirements 9 and 10's recording half lands here as
`solve-record-v2`. Requirements 17 to 20 (relaxation forfeiture, dispatch and
fallback) belong to the CLI surface and are not reached yet.

Acceptance gate: `bash tools/check.sh` with the pinned HiGHS library present.
Resource budget: CPU only, no GPU workloads.

Two version constants now exist where one did. `SOLVE_SCHEMA_VERSION` keeps its value
and its meaning narrows to the configuration; `SOLVE_RECORD_SCHEMA_VERSION` is 2. That
split is what confines the bump: the configuration is embedded in `search-config-v3`,
so bumping it would have moved the search configuration, the search record and the run
record as well — four documents to record something no configuration carries. Nothing
embeds a solve record, so the record moves alone. The settings are constructor state,
which is what SPEC-0011's own `open(residency, settings)` interface already implied.

The settings documents live in `optimizer-core` for the same reason `ProblemClass`
does: a record carries them, records are core types, and a second copy in the
implementing crate would be the drift SPEC-0008 requirement 8 exists to prevent. The
method stays in `optimizer-lp`.

A sign convention was wrong on the first attempt and the test caught it. The method
converged to an infeasible point with objective -2 on an instance whose optimum is
-1.5, because the dual update used the saddle function with the opposite sign of the
one the certification assumes. The fix is not cosmetic: this module takes
`cᵀx − yᵀAx + h(y)` so that the reduced cost is `c − Aᵀy`, the ordinary linear
programming convention and the one the certification recomputes. Under the other
convention the multipliers come out negated, certification stays *valid* — it is valid
for any vector — and every bound is uselessly weak. That is a much harder defect to
notice than a wrong answer, which is why the convention is now stated where the update
is written. With it right, the engine's own dual on the worked instance is exactly
-1.0, the true optimal dual, and the certified bound sits one rounding allowance below
the optimum.

Two departures from the published method, both made for determinism and both
recorded rather than absorbed. The step size is fixed rather than line-searched,
because an adaptive step retries an input-dependent number of times and the trial
count would then depend on rounding. The power iteration count is fixed for the same
reason. The cost is convergence rate, which requirement 23 forbids claiming anything
about in either direction.

The KKT residuals this module computes steer the algorithm and justify nothing. No
bound, status or proof reads them. A device computing them badly converges badly and
cannot produce a wrong answer — a distinction easy to lose at a glance, so it is
written where the residuals are.

Evidence (2026-09-13): `bash tools/check.sh` passed, exit 0, with 355 Rust tests, 68
Python tests and 56 documentation pages. Twenty-three tests are new. Agreement with
the pinned backend is asserted over the same four LP shapes its own differential
acceptance uses, with a mutated instance shown to disagree so the comparison is known
able to fail. All four fixtures reach optimality with a certified bound, which is
asserted rather than assumed: without that assertion the closure test would pass by
taking its other branch if certification ever regressed.

Follow-up: the CLI surface, dispatch and fallback, then the device kernels.

## C6 Host Certification of a Dual Bound (2026-09-13)

Objective: reach SPEC-0011 requirements 11, 12 and 13 — a bound produced only by a
host-side procedure that does not assume the device computed anything correctly, and
that is valid even when the iterate is far from optimal.

Status: complete. This is the piece ADR-0010 calls load-bearing in a way little else
in the project is, and it is tested for validity far from optimality rather than only
near it.

Acceptance gate: `bash tools/check.sh` with the pinned HiGHS library present.
Resource budget: CPU only, no GPU workloads.

Nothing here reads a residual, a norm or an objective any device computed. The only
device-produced numbers the procedure touches are the row multipliers, and they enter
inequalities that hold for every real number. That is what makes the result a
certification rather than a check: the reduced costs are recomputed from the model's
own coefficients, so `z = c − Aᵀŷ` is true by construction rather than claimed.

The two sides of the repair are not symmetric, and the asymmetry is the reason
ADR-0010's wording was corrected in `fde1d82`. A row multiplier with the sign whose
bound is infinite can be zeroed, because projecting it breaks no identity. A reduced
cost cannot, because it is determined by the multipliers, and adjusting one alone
would falsify the identity the bound rests on. Where a variable's bound is infinite on
the side its reduced cost needs, the infimum really is negative infinity and the
honest answer is no bound, naming the variable. Clamping to a large finite number
would fabricate one and is the most dangerous shortcut available in this module.

Both mechanisms were checked to be load-bearing rather than assumed to be. Removing
the repair fails three tests including the central validity one. Removing the rounding
allowance fails the test written for it.

Finding an instance where the allowance matters took a search, and the search is worth
recording because the first attempt produced a test that proved nothing. A violation is
pure `f64` rounding, so it only appears where the margin is zero: at the optimal dual,
where complementary slackness makes every bounded term tight. Away from it the slack is
of order the reduced costs, and rounding at 1e-16 cannot reach across — half a million
random multipliers produced no violation at all. With the multiplier set to the one that
zeroes a variable's reduced cost, an instance appeared whose raw sum exceeds the true
optimum by 6.6e-14. The first version of this test used an instance where the raw sum
landed exactly on the optimum, and asserted only that the allowance was positive and the
bound weaker; that would have passed with the subtraction deleted.

Evidence (2026-09-13): `bash tools/check.sh` passed, exit 0, with 332 Rust tests, 68
Python tests and 56 documentation pages. Eight tests are new. Validity is asserted
against every feasible point on a grid rather than against an optimum, because weak
duality claims the bound is below the objective everywhere feasible — testing the claim
itself needs no second solver and no optimum. The multipliers include zero, a
sign-flipped one and two scaled by 1e18, none near optimal.

Follow-up: the host PDHG engine and the settings document, which is where requirements
9 and 10 are recorded and where `solve-record-v2` lands.

## C6 Canonical LP Form and Fixed Reduction Order (2026-09-13)

Objective: reach SPEC-0011 requirements 6, 7 and 27 — the constraint matrix in both
orientations, one reduction order both engines share, and a recorded preconditioner.

Status: complete. Requirement 9's recording half waits on the settings document; what
lands here is the preconditioner itself and the proof that it is a pure function of
its parameters, which is what makes recording them sufficient.

Acceptance gate: `bash tools/check.sh` with the pinned HiGHS library present.
Resource budget: CPU only, no GPU workloads — deliberately, because this crate is the
oracle the device kernels will be checked against and must not need one.

The new `optimizer-lp` crate takes no device dependency and adds no third-party crate,
so `cargo deny` still resolves the same eighteen external packages. It inherits the
workspace lints, so it forbids unsafe; ADR-0009's single new boundary is untouched.

Holding the matrix twice is the requirement that most looks like a performance choice
and is not. Each product reads the orientation whose major axis it writes, so every
output element is owned by exactly one accumulation and no atomic is needed anywhere.
The column-major form is built from the same triples transposed rather than derived
from the row-major one, because deriving it would make a defect in the first invisible
in the second, and the two exist to be an independent pair.

`SEGMENT`, the tree, and the `+0.0` padding are one definition rather than a rule the
kernel will restate. Padding is what removes the length from the tree shape, and it
changes no bit because adding `+0.0` is an exact identity.

The reduction has two orders on purpose. `DeviceMirror` is the kernel's own, so a host
and device result can be compared bit for bit and a drifted index shows immediately.
`Sequential` shares no order with the kernel, so agreement with it is evidence about
the method rather than about a copied summation. One number could not establish both.

Two tests earned their place by being rewritten. The first version of the partition
test compared `tree_sum` with itself, which asserts only determinism — a much weaker
claim than the one its name made, and one the repeatability test already covers. It
now checks a literal transcription of the documented steps, written separately, bit
for bit across seven lengths including the segment boundary. And
`a_tree_sum_differs_from_a_left_to_right_sum_on_a_catastrophic_input` exists because
without it every later determinism assertion would be vacuous: if no input
distinguished the two orders, any order would satisfy them.

Evidence (2026-09-13): `bash tools/check.sh` passed, exit 0, with 324 Rust tests, 68
Python tests and 56 documentation pages. Fifteen tests are new, covering both
orientations holding the same nonzeros, infinite bounds surviving conversion, a
maximization negated once and reported back in the caller's direction, a discrete
model refused rather than relaxed, the documented reduction rule, the two orders being
distinguishable, padding changing no bit, and the preconditioner being a pure function
of its recorded parameters.

Follow-up: the host certification, which is the load-bearing piece.

## C6 Backend Capability Declaration (2026-09-13)

Objective: reach SPEC-0011 requirements 1, 2 and 4 — a declaration a caller can read
without knowing which implementation it holds, and which that caller cannot widen.

Status: complete. Requirement 3's refusal is not reached here, because it needs a
backend that refuses something, and the pinned adapter accepts every class.

Acceptance gate: `bash tools/check.sh` with the pinned HiGHS library present.
Resource budget: CPU only, no GPU workloads.

`ProblemClass` moved from `optimizer-extension` to `optimizer-core` and is re-exported
from its old path. It is a relocation rather than a redesign: its only constructor
already read nothing but `Model` and `Domain`, both core types, and the serde
implementation was carried verbatim. The alternative was a second enum on the solve
contract with the same two variants and the same wire form, which is the drift
SPEC-0008 requirement 8 exists to prevent arriving from a new direction — a registry
entry claiming `continuous` and a backend declaring `continuous` would have become two
unrelated facts. Every `optimizer_extension::ProblemClass` path still compiles, and the
unchanged extension contract tests and `tests/integration/test_registry.py` are the
evidence that no wire byte moved.

Requirement 4 is carried by three mechanisms rather than one, because the obvious one
is the weakest. Private fields stop a caller mutating a declaration; `capabilities`
takes no argument, so there is no request-shaped input to influence it with; and a
backend consults its own declaration inside `solve`, which is what makes a caller
holding a widened copy still refused. The requirement is about authority, and only the
third mechanism establishes it.

The specification's printed interface could not be implemented and was corrected in
`fde1d82` first. `version` is a `String`: the adapter reports the version it actually
linked and `unavailable` when it linked nothing, and a `&'static str` would have forced
it to name a version it may never have called.

What the widening test does and does not establish. The `compile_fail` doctest is the
first in this workspace. It was verified to fail with `E0616`, the private-field error,
by compiling the same snippet directly. But the `E0616` annotation is **not enforced**:
substituting `E0308` was tried and the doctest still passed, so stable rustdoc accepts
any compilation failure. On its own the block would therefore keep passing if the field
were renamed rather than kept private. A positive test reads the same field through its
accessor so a rename cannot leave both green, and the doc comment records the
limitation rather than implying the annotation checks anything.

Evidence (2026-09-13): `bash tools/check.sh` passed, exit 0, with 309 Rust tests, 68
Python tests and 56 documentation pages. Nine tests are new: four on declaration
validation, one pairing with the doctest, three on the pinned adapter's declaration,
and the doctest itself. `the_pinned_adapter_accepts_every_class_it_declares` solves a
model of each declared class and requires a real outcome rather than `Unsupported`,
so a declaration cannot drift from behavior and the test cannot pass by refusing
everything.

Follow-up: the canonical LP form and the fixed reduction order, then the host
certification.

## C6 SPEC-0011 Corrections Before Implementation (2026-09-13)

Objective: settle two requirements of SPEC-0011 that cannot be satisfied as written,
before any of the GPU linear-programming backend is implemented against them.

Status: complete. Documents only; no behavior changes, so no changelog entry, as
the C2, C5 and C8 specification commits each recorded.

Acceptance gate: `bash tools/check.sh` passes unchanged, with the same 300 Rust and
68 Python tests, because nothing executable changed. Resource budget: CPU only, no
GPU workloads.

Three corrections, each a conflict found by reading the contract against the tree
rather than a preference.

Requirements 9 and 10 require the preconditioner and the termination check interval
to be recorded "as part of the settings that produced a record", and the acceptance
section requires a record missing either to be refused. Compatibility freezes
`solve-record-v1`, and that document is closed: `deny_unknown_fields` on the Rust side
and `additionalProperties: false` in the schema. Both cannot hold. The correction
permits `solve-record-v2` and keeps `solve-config-v1` at version 1, which is what the
specification's own `CudaLpBackend::open(residency, settings)` interface already
implies: settings are constructor-time state, not per-solve options. Nothing embeds
`solve-record`, so this is a leaf bump with no cascade into `search-config-v3`,
`search-record-v3` or `run-record-v2` — checked before choosing it. The rejected
alternative was a sidecar settings document, which obeys the frozen version literally
but leaves a `SolveRecord` unable to reproduce its own solve, contradicting the
doc comment on that type and weakening SPEC-0005's reproducibility spine.

The Interfaces block cannot be implemented as printed. `version: &'static str` cannot
hold the HiGHS version, which is a runtime `String` and is `UNAVAILABLE_VERSION` when
nothing was linked, so a `&'static str` would force the adapter to name a version it
may never have called. And public fields make widening a declaration a mutation the
compiler permits, which contradicts requirement 4 and its acceptance line that a
caller attempting to widen one does not compile.

The host first-order method is the oracle the device kernels are checked against,
which `state/backlog.yaml` requires be built first. Shipping it as a selectable
backend rather than as test scaffolding makes it a public feature, and CONTRIBUTING.md
requires an accepted specification for one. Requirements are added here rather than
the surface being introduced without a contract.

ADR-0010's "which is finite wherever the repair needs it" is true of every model this
project currently produces and false of `model-v1` in general: a free variable admits
no finite repair on the column side, because the reduced cost is determined by the
dual iterate and repairing it alone falsifies the identity the bound rests on. The
behavior there is a refusal rather than a wrong bound, so this is a scope statement,
but the sentence reads as a theorem and is narrowed to the models it is a theorem
about.

Follow-up: the implementation slices, in order — the capability declaration on the
solve contract, the canonical LP form and fixed reduction order, the host
certification, the host engine with dispatch, the device kernels, and the evidence
record.

Evidence (2026-09-13): `bash tools/check.sh` passed with the pinned HiGHS library
present, exit 0, 300 Rust tests, 68 Python tests and 56 documentation pages — the same
counts as before this change, which is what a specification-only commit should
produce. The advisory database fetch failed and fell back to the cached copy, which
`state/known-failures.md` already records as intermittent.

## C6 Clean-Checkout Verification (2026-09-13)

Objective: verify the C6 branch from a checkout with nothing prebuilt, before any
integration, as the C4, C8 and Track B branches each were.

Status: complete; the branch passes from a fresh clone and one environment-dependent
test was found and fixed by doing so.

Acceptance gate: `bash tools/check.sh` passes in an independent clone with no
`target/` directory, no provisioned HiGHS library and no provisioned device code
object. Resource budget: CPU only, no GPU workloads — which is itself part of what
is being verified.

The verification earned its place. `a_device_no_registered_extension_needs_is_refused`
passed locally and failed in the clone. With a code object present the refusal is
"no extension requires one" and names the device; without one the session fails
earlier with "no device code object at <path>", which names a path. The test was
environment-dependent, and the message was genuinely worse than the test: a caller
who asked for a device and got a message about a file cannot tell which device was
refused. Fixed by making every refusal name the device rather than by weakening the
assertion.

What the clone establishes that a local run cannot. The build script's warning fired
four times, so `cuda_native` was unset throughout and every device path compiled to
its unsupported form: this is SPEC-0010 requirement 37 and ADR-0009's "nvcc is a
provisioning dependency, never a build dependency", observed rather than asserted.
The pinned HiGHS library was built inside the clone from scratch. And the twenty
device tests reported their skips rather than failing, which is what keeps a CPU-only
host a full gate pass.

Evidence (2026-09-13): cloned with `--no-hardlinks` at `6dbaf8c` with no `target/`
present; `bash tools/check.sh` passed there in 1 minute 35 seconds, exit 0, with 300
Rust tests, 68 Python tests and 56 documentation pages — the same counts as the
working tree.

`Cargo.lock` did change across the branch, and the earlier wording here said it had
not. What it gained is the `optimizer-cuda-sys` entry, its one dependency edge on
`libc`, and the edges naming the new crate from `optimizer-cuda` and
`optimizer-schedule-examples`. No third-party crate was added: `libc` was already in
the lockfile transitively, so the workspace still resolves the same eighteen
external packages it did before, which is what `cargo deny --locked check` confirms
on every gate run.

Follow-up: the branch is ready to integrate. C6 itself is not complete: SPEC-0011's
GPU linear-programming backend is accepted and unimplemented, so the backlog line
stays open.

## C6 Bounded Launch Chunks and Host Fallback (2026-09-13)

Objective: reach SPEC-0010 requirements 27 to 30 — bounded launch chunks with a
cancellation check between them, a poisoned context that is not launched into again,
and a device fault that never becomes a solver outcome.

Status: complete. Requirement 29 takes its fall-back-for-the-run option rather than
rebuilding a context, which the specification permits and which is recorded as the
choice it is.

Acceptance gate: a 500-job neighbourhood takes four launches rather than one,
asserted against a counter; the chunked result is identical to the host's; a
pre-cancelled call launches nothing and reports cancellation; a cancelled residency
is still usable afterwards; an input error touches the device at all; the host
fallback produces byte-identical proposals; `bash tools/check.sh` passes with native
acceptance covered. Resource budget: **GPU, one device under the shared host lease**.

What had to be bounded is work, not calls, and the two chunk sizes differ for a
reason worth recording. The batch kernel is one thread per permutation, so 4,096
permutations is 4.1e7 integer operations at the largest supported shape. The
neighbourhood kernel is one block per removed job and each block's recurrence is
serial, so the same block count buys far less parallelism and takes longer; 128 jobs
is 2.6e6 dependent operations. Picking one constant for both would have made one of
them either uselessly small or unboundedly large.

Synchronizing per chunk is what makes the cancellation check mean anything, and that
is not free. Without it the launches queue and the loop finishes before any of them
has run, so the check would test a token nothing had waited on. It is also where a
kernel fault surfaces, which is why the sticky check wraps the synchronize rather
than the launch.

The measurement did not move: a 500-job neighbourhood still runs in the same time it
did as a single launch, because four synchronizes at this size cost microseconds
against milliseconds of work. That is the expected result and it is worth stating,
because a chunking change that *did* move it would mean the chunks were too small.

Requirement 29 offers two responses to a sticky fault and this takes the second.
Rebuilding a context would mean replacing one that the residency's buffers hold
through an `Rc`, which is a lifetime problem rather than a driver one; falling back
for the remainder of the run is permitted, simpler, and loses only a transient
fault's device. The cost is recorded in [known failures](known-failures.md) along
with the honest gap: the decision logic is unit-tested, and recovery from a real
sticky fault is not, because provoking one means corrupting a device.

The producer's fallback closes requirement 24's recorded gap, and the assertion is
the one that matters. The fallback is `optimizer_schedule::insertion_neighborhood`
— the CPU path this project already treats as authoritative, not a second
implementation written to match the kernel — so the two cannot drift, and the
contract asserts the proposals are *identical* rather than equally good. A caller
cannot tell which path ran, which is the definition of a fallback; the `fallbacks()`
counter is how a test can.

Evidence (2026-09-13): `bash tools/check.sh` passed with the pinned HiGHS 1.11.0
library linked and **zero test skips other than the twenty device tests**, exit 0.
Rust tests rose from 295 to 300 and Python remains 68; documentation remains 56
pages. `Cargo.lock` is unchanged; `optimizer-cuda` gained an `optimizer-core` edge
for `CancellationToken`, which requirement 27 names explicitly. Separately,
`bash tools/gpu_job.sh <uuid> bash tools/gpu_check.sh` passed both device suites —
fourteen kernel contracts and six producer contracts — and all four sanitizers over
both binaries, with zero errors and zero hazards.

Follow-up: none blocking. What remains open on SPEC-0010 is requirement 22's
threshold, which is deliberately not implemented because a dispatch threshold is an
acceptance-shaped number that the benchmark protocol requires an ADR and an
experiment record to commit.

## C6 Device-Backed Candidate Producer (2026-09-13)

Objective: make a search reach a device. Until now the device path existed and was
verified, and nothing outside a test could use it — the same gap C8 closed for
extensions, open again for hardware.

Status: complete; `optimizer schedule solve` with a device named and
`flow-shop-neh-gpu` registered runs the neighbourhood on the device, writes a record
whose provenance names the hardware, and that record re-executes and agrees.

Acceptance gate: every device-produced candidate is feasible by `Model::evaluate`;
the producer applies exactly the best single insertion move by the host's own
computation; repeated proposals are identical; a `gpu` registry entry resolves with
a device and is refused without one, still before construction; a configuration
naming a device that no registered extension needs is refused and writes no record;
`bash tools/check.sh` passes with native acceptance covered. Resource budget:
**GPU, one device under the shared host lease**.

Where the enforcement lives took the most thought. Requirement 6 says a record must
not claim a device the run did not use, and it has two halves that cannot live in
one place. The executive can see that a device is named and no extension is
registered at all, which makes the device certainly unused — that check is
necessary and it is not sufficient, and the code says so rather than implying
otherwise. Whether a *particular* registration uses a device needs the hardware
requirement, which SPEC-0004 deliberately keeps out of an extension's declaration
and SPEC-0009 puts in the registry. So the sufficient half belongs to the surface
that resolved the registry. Splitting it felt like a smell until the alternative was
written down: putting both in the executive would mean teaching it to read registry
entries, which is exactly the coupling ADR-0008 avoided.

The registry's condition is a UUID, not a device handle, so optimizer-registry stays
free of the driver boundary. That is sound because of where the UUID comes from: the
only way to obtain one is `DeviceSession::open`, which leases the host lock, creates
a context and reads the identity back. A caller cannot fabricate `Some` without
having done all three, so "a device is selected" and "a device is held" are the same
statement.

A refactor was needed and is worth recording because it improved the code rather
than merely enabling it. The driver handles borrowed their context with a lifetime,
which a producer cannot satisfy: a `Box<dyn CandidateProducer>` has no lifetime to
borrow from. They now hold `Rc<Context>`, so a context outlives its modules, streams
and allocations by refcount rather than by the borrow checker. That is strictly more
robust — the old arrangement was correct only because every holder happened to be
borrowed from the same scope.

Two mistakes the work caught, both mine.

The first was a wrong test. I asserted the device producer is never worse than
`SchedulingProducer` and it failed on `ta051`, 4059 against 4040. The producer was
right and the test was wrong: the CPU producer runs a full sequential pass, up to one
accepted move per job with each visible to the next, while this one applies a single
best move. Comparing them compares two algorithms, and neither promises to beat the
other. The test now asserts what is actually promised — that the move applied is the
best single move, checked against `insertion_neighborhood` on the host — and the
old assertion is recorded in its doc comment so the next reader does not reinstate
it.

The second was a wrong diagnostic, found by a test helper making the obvious error.
It chose a device from the host inventory, and under `tools/gpu_job.sh` the inventory
and the driver disagree: the wrapper restricts the process to one device, so the
inventory's first entry is usually one the driver cannot see. The message was "no
device with UUID", which is true and sends a reader to check a UUID that is already
correct. There is now a separate `HiddenFromDriver` refusal naming
`CUDA_VISIBLE_DEVICES`, and `visible_uuids()` reports what the driver can actually
see, which is the list a consumer must choose from.

Evidence (2026-09-13): `bash tools/check.sh` passed with the pinned HiGHS 1.11.0
library linked and **zero test skips other than the fifteen device tests**, exit 0.
Rust tests rose from 286 to 295 and Python remains 68; documentation remains 56
pages. `Cargo.lock` is unchanged and one `Cargo.toml` gained one intra-workspace
edge. Separately, `bash tools/gpu_job.sh <uuid> bash tools/gpu_check.sh` passed both
device suites — eleven kernel contracts and four producer contracts — and all four
sanitizers over both binaries, with zero errors and zero hazards, on an RTX 5090.

End to end on an RTX PRO 6000: a scheduling search with the device producer
registered proved optimality, recorded `gpu_uuid`, `gpu_name` and driver 580.105.08
in its provenance, and `optimizer verify` re-executed it on the same device and
agreed on every compared field.

Follow-up: bounded launch chunks with a cancellation check between them, which is
the part of requirements 27 to 30 an interrupted long device run would notice.

## C6 Device Probe and Driver Version (2026-09-13)

Objective: give the driver version a producer, under SPEC-0006 requirement 1a, and
add `optimizer gpu probe` so a caller can find out whether this build can use a
device without running a search on one.

Status: complete; discovery reports four fields, and a probe creates a real context
under the lease and reports what the driver and the code object actually provide.

Acceptance gate: discovery refuses a row without a driver version rather than
accepting a hole; a probe reads the requested UUID back through the context it
created and reports both; it resolves every kernel this build expects without
launching one; a UUID no device carries, a missing device flag, a repeated flag, an
unknown lease mode and an out-of-range timeout are each refused with exit 2 and no
report; `bash tools/check.sh` passes with native acceptance covered. Resource
budget: **GPU, one device under the shared host lease** for the device-gated tests;
the CPU gate is unchanged and still runs none of them.

Why a probe is a separate command from discovery. Discovery asks management tooling
what hardware exists and never touches the driver, which is why it needs no lease
and runs anywhere. A probe asks the driver, so it creates a context and therefore
must hold the lease. Collapsing the two would have made the cheap question expensive
and the expensive one look free.

The report keeps `requested` and `observed` as separate fields, and that is the
point of it rather than a detail. Requirement 3's check is that they are equal; a
single field would have recorded the answer while recording nothing about whether
anything was compared. The same reasoning put the kernel list in the report: the
probe resolves every entry point this build expects without launching any of them,
so a code object that loads but is missing a kernel is found here rather than by a
first launch.

Two arguments were refused where a lenient reading was available. `--lease` accepts
only `acquire` and `inherited`, and a repeated `--device` is an error rather than
last-one-wins, because a caller who named two devices did not mean either of them
and the lock permits one holder anyway.

The unsafe prohibition caught a design mistake, which is worth recording because it
was mine. The first version of the probe command set the inherited-lease environment
variable so the library would see it. `optimizer-cli` forbids unsafe and
`env::set_var` is unsafe under edition 2024, so it would not compile. The
prohibition was right on the merits, not merely in the way: a command that mutates
its own environment to signal a library is harder to follow than one that passes an
argument. The lease decision is now a `LeaseRequest` parameter, and `LeaseRequest`
is deliberately distinct from the `LeaseMode` the report carries — one is what the
caller asked for, the other is what happened, and `Auto` can produce either.

`--lease acquire` inside a wrapped job is now a bounded refusal rather than a hang.
It waits on the lock its own parent holds and gives up at the timeout, which is the
deadlock requirement 8 exists to prevent, made visible in a test run instead of a
stuck job.

What this does not do, stated because it is easy to read as further along than it
is: `Hardware::driver` in a run record is still null. That is correct rather than
outstanding. Every search this build performs is a CPU search, and SPEC-0007
requirement 9 forbids a CPU record claiming GPU execution; the field takes a value
when a search runs on a device, which is the device-backed producer's work.

Evidence (2026-09-13): `bash tools/check.sh` passed with the pinned HiGHS 1.11.0
library linked and **zero test skips other than the eleven device tests**, exit 0.
Rust tests rose from 277 to 286 and Python remains 68; documentation remains 56
pages. `Cargo.lock` and every `Cargo.toml` are untouched. Separately,
`bash tools/gpu_job.sh <uuid> bash tools/gpu_check.sh` passed all eleven device
tests and all four sanitizers — memcheck, racecheck, initcheck and synccheck — with
zero errors and zero hazards, on an RTX 5090. A probe on the RTX PRO 6000 reported
compute capability 12.0, 188 multiprocessors, 101,376 bytes of shared memory per
block and driver 580.105.08, with both kernels resolved.

Follow-up: the device-backed candidate producer. It is what would make the
registry's unconditional refusal of a `gpu` hardware requirement worth narrowing,
and the measured crossover worth consulting; until it exists, no search reaches a
device.

## C6 Device Selection Schema Cascade (2026-09-13)

Objective: put the selected device on the search configuration, under SPEC-0010
requirements 40 and 41, so that a device run is describable by a record that
verification can re-execute — and pay the three version bumps that forces rather
than avoiding them by putting the device somewhere verification never reads.

Status: complete; `search-config-v3`, `search-record-v3` and `run-record-v2` are in
both authorities, and a configuration naming a device is refused rather than run on
the CPU.

Acceptance gate: both the Rust parsers and the JSON Schemas accept exactly the same
documents and are asserted to refuse the same four mutations; an earlier version is
refused rather than migrated; a configuration naming a GPU is refused with the
device named and writes no record; the three committed example records still
re-execute and agree; `bash tools/check.sh` passes with native acceptance covered.
Resource budget: CPU only, no GPU workloads.

Why the field is in the configuration and not in provenance. Provenance was the
cheaper answer by a wide margin: `Hardware` already has three nullable GPU fields
and no version would have moved at all. It is the wrong answer because SPEC-0005
verification re-runs a search using only the record's embedded configuration, on
purpose, so that a record cannot confirm its own result. A device recorded only in
provenance is therefore invisible to the thing that repeats the run, and a record
naming a device would be re-executed without one. The cascade is what it costs to
keep the device where a re-execution can see it.

One field moved three versions because the documents nest: a search record embeds
its configuration, and a run record embeds that search record. The solve
configuration deliberately did not move. A relaxation inherits the search's device
because SPEC-0006 requirement 6 permits one lease holder across device selections,
so a search cannot use two devices and a per-solve field could express a
configuration the lease forbids.

Nothing is migrated, and the reason is not conservatism. A version-2 configuration
is exactly a version-3 one with the `device` line deleted, so defaulting an absent
device to `cpu` looks free. It is not: a version-2 record of a device run and a
version-2 record of a CPU run are byte-identical, so a migration would have to
invent the fact that tells them apart. Both authorities refuse, and a test asserts
they refuse the same documents rather than each refusing separately.

The refusal that matters most is the one that looks like an omission. The executive
rejects a configuration naming a GPU, because no search path dispatches to a device
yet. Honouring it by quietly running on the CPU would not have been a smaller
version of the feature; it would have been a false record that *passes*
verification, because verification re-runs from the same configuration, also lands
on the CPU, and agrees — and that agreement would certify a hardware claim nothing
ever checked. The refusal names the device it refused, and the CPU configuration
differing only in that field still runs, so it is discriminating rather than a
blanket failure.

One thing nearly went wrong and is worth recording. The three committed example
records are synthetic: an all-zero revision, `dirty: false`, a fixed identifier and
a warning saying they are not measurement evidence. Regenerating them with
`optimizer search` was the obvious way to move them to the new version and would
have silently replaced all four of those properties with real ones from a dirty
working tree. They were version-bumped in place instead, with only their
configuration input's path and checksum updated, and all three still re-execute and
agree.

Evidence (2026-09-13): `bash tools/check.sh` passed with the pinned HiGHS 1.11.0
library linked and **zero test skips other than the eight device tests**, exit 0.
Rust tests rose from 273 to 277 and Python from 63 to 68. Documentation remains 56
pages. `Cargo.lock` and every `Cargo.toml` are untouched.

Follow-up: the surfaces that make the field do something — `optimizer gpu probe`,
the driver version SPEC-0006 requirement 1a needs, a device-backed candidate
producer, and narrowing the registry's unconditional refusal of a `gpu` hardware
requirement. Until one of those lands, the device field is honoured only by being
refused.

## C6 Device Boundary and Batched Schedule Evaluation (2026-09-13)

Objective: implement SPEC-0010's device path far enough to answer the question the
whole capability exists for — whether a device agrees with the host exactly, and
where the crossover is — without granting the device any authority.

Status: complete for the boundary, the kernels and the evidence; incomplete for the
surfaces that would let anything outside a test reach a device. Both halves are
recorded in [known failures](known-failures.md) rather than one of them implied.

Acceptance gate: device makespans equal `optimizer_schedule::makespan` exactly, at
tolerance zero, over the whole ADR-0011 sweep; the device neighborhood equals both
the accelerated CPU path and a full recomputation; a repeated evaluation is bitwise
identical; a residency uploads once, asserted against a counter; a nonexistent UUID
and an absent code object are each refused by name; the ordinary gate stays CPU-only
and green with no device. Resource budget: **GPU, one device under the shared host
lease**, which is the first task in this project whose budget is not CPU only.

The boundary is `dlopen`, not a link. `optimizer-cuda-sys` opens `libcuda.so.1` and
resolves about twenty entry points, so `cargo build --workspace --all-features` keeps
working on a host with no toolkit and no device, and an absent driver is a typed
`DriverUnavailable` rather than a link error. That is what makes requirement 37
reachable rather than aspirational, and it added no third-party crate: `libc` was
already in the lockfile transitively. `optimizer-cuda` keeps `unsafe_code = "forbid"`
and keeps discovery, the lease and residency, so the crate every GPU consumer already
depends on did not become unsafe.

Both kernels are pure `unsigned int`, and that choice is forced twice over. The
hardware runs FP64 at one sixty-fourth of FP32 and issues integer and
floating-point instructions on one pipeline, so integer code runs at the full lane
rate. And the head and tail tables are 80,000 bytes at 500 jobs by 20 machines,
inside the 99 KB a block may address at compute capability 12.0, where 64-bit tables
would be 160,000 and would not fit on any block of this hardware. Both numbers were
checked rather than assumed: the driver reports the 99 KB limit and `ptxas -v`
reports 31 registers with zero spill for the batch kernel, inside the 42 that 48
resident warps allow.

Agreement is exact. Not "within a tolerance" — the assertion is `assert_eq!` on
`u32` values, over 64 permutations of each of the twelve instances and over every
job of every instance's neighborhood, plus a full cubic recomputation on the
twenty-job instances so the two head-and-tail implementations cannot share a wrong
idea of what an insertion costs. This is the strongest form of the CPU/GPU agreement
evidence Stage 4 asks for, and it is available only because the arithmetic is
integer; SPEC-0011's floating-point path will not have it.

The crossover is measured and both of its findings are inconvenient. The device
loses at twenty jobs by a factor of four, crosses over at roughly fifty, peaks at
16x on 200x20 — and then falls back to 9.5x at 500x20, because the 80 KB tables
leave one block resident per multiprocessor and two threads build the recurrence
while 254 wait. Context creation costs about 148 ms, which dwarfs every other number
in the table including the largest CPU time. The losing row and the falling tail are
both why the table is believable: SPEC-0010 names the first as the expected outcome,
and a sweep stopping at 200 jobs would have reported a monotonic trend that does not
hold. The full table is in [known failures](known-failures.md).

What is deliberately not done: the max-plus scan that would parallelise the
recurrence across machines. It is named in the kernel comment and left undone,
because correctness came first and an unmeasured optimisation would have had no
baseline to be measured against. Now it has one.

Device tests are opt-in behind `AI_OPTIMIZER_GPU=1`. Every earlier task record in
this project states "CPU only, no GPU workloads", and a suite that silently took the
host lease and ran kernels would have made those records false; it would also contend
on a lock that permits one holder for the whole host. The ordinary gate therefore
reports eight explicit skips naming the variable, which is the same shape as the
native-library skip and is never counted as coverage.

Evidence (2026-09-13): `bash tools/check.sh` passed with the pinned HiGHS 1.11.0
library linked and **zero test skips other than the eight device tests**, exit 0.
Rust tests rose from 253 to 273 and Python remains 63; documentation remains 56
pages. `Cargo.lock` gained `libc` as a direct dependency of the new crate and nothing
else. Separately, `AI_OPTIMIZER_GPU=1 bash tools/gpu_job.sh <uuid> cargo test
--release -p optimizer-cuda --test device` passed all eight on both an RTX 5090 and
the RTX PRO 6000, under an inherited lease. No device test has run in CI, because the
labeled runner is still not provisioned, and that is recorded rather than glossed.

Sanitizers (2026-09-13, added after the boundary landed): `bash tools/gpu_check.sh`
under the wrapper runs the device suite and then all four `compute-sanitizer` tools.
memcheck 0 errors, racecheck 0 hazards, initcheck 0 errors, synccheck 0 errors on an
RTX 5090. Racecheck was the one worth having: the neighborhood kernel has two threads
writing disjoint halves of one dynamically sized shared array while 254 others wait on
a barrier, which is exactly the shape a reviewer cannot check by reading. The script
refuses to run without an inherited lease rather than taking one, so it cannot escape
the wrapper that names a single device.

Follow-up: the schema cascade — `device` on the search configuration, and the
`search-config-v3`, `search-record-v3`, `run-record-v2` versions it forces — then the
CLI probe and the device-backed producer, then `compute-sanitizer`. Nothing reaches a
device from outside Rust test code yet, which is the same gap C8 closed for
extensions and is open again here.

## C6 Scale Split (2026-09-13)

Objective: add a frozen flow-shop split that spans published instance shapes, so the
crossover SPEC-0010 requirement 22 makes the CPU default depend on can be located
rather than merely bounded from below.

Status: complete; ADR-0011 is accepted, twelve instances are committed with their
derivations, and the manifest validates under both authorities.

Acceptance gate: the manifest validates against the SPEC-0007 schema; every committed
document is reproduced from its recorded seed by an independently written generator
and matches its checksum; the reproduction check is shown to fail for a wrong seed
and for a transposed loop order; the development subset is byte-identical to before;
`bash tools/check.sh` passes with native acceptance covered. Resource budget: CPU
only, no GPU workloads.

Why a new split rather than a larger one: SPEC-0008 requirement 24 and the benchmark
protocol both require a decision record before a split changes, and the development
subset's own documentation says enlarging it is such a change. Enlarging it would
also have altered the split a completed capability's evidence cites, for a reason
that has nothing to do with that capability. ADR-0011 therefore adds a split and
leaves C5's untouched.

Why one instance per shape rather than ten: the two splits answer different
questions. C5 asks whether an encoding and a recurrence are correct, and correctness
does not vary with shape, so ten instances of one shape exercise the same paths ten
times and that is the right sample. C6 asks how cost grows with shape, so the sample
has to move along the axis that varies. Ten per class would have committed twelve
times the bytes to answer a question about within-shape variance that nothing in C6
asks — and would have invited averages over a split never designed to support them.

The smallest shape is in the split deliberately. Twenty jobs by five machines is
where a device is expected to lose, so it is the crossover measurement's own
falsification check: a report showing the device winning everywhere is evidence the
measurement excluded transfers, not evidence the device is fast. A sweep starting at
the large end could not produce that signal.

One property of the source caught a wrong assertion before it was written. Taillard
reuses time seeds across classes — `ta051` and `ta071` are both 1539989115 — so the
development subset's "seeds must be unique" assertion is true only within one shape.
Carrying it over would have failed on the published table itself rather than on a
mistake. Both the Rust and the Python contracts now assert uniqueness of the seed
together with its shape, and the reason is recorded beside them.

The seed table was transcribed from the same OR-Library source the development subset
cites, and the ten seeds already in the repository matched it exactly, which is a
cross-check on both rather than on neither.

With the split in place the Phase 1 measurement was retaken over all twelve
instances, replacing the earlier table that reported shapes without naming instances.
The numbers are materially unchanged, which is the expected result — processing times
are drawn from the same distribution regardless of seed — but the rows now name
instances that exist. The full table is in [known failures](known-failures.md).

Evidence (2026-09-13): `bash tools/check.sh` passed with the pinned HiGHS 1.11.0
library linked and **zero test skips**, exit 0. Rust tests rose from 252 to 253 and
Python tests from 60 to 63; documentation rose from 55 to 56 pages, which is ADR-0011
and nothing else. `Cargo.lock` and every `Cargo.toml` are untouched. The tracked
instance documents add roughly 280 KB, which is the cost of checkable provenance.

Follow-up: SPEC-0010's device phases. The next is the CUDA driver boundary and the
provisioning script, which must leave an ordinary `cargo build` working on a host
with no toolkit and no device.

## C6 Tuned Flow-Shop Baseline (2026-09-13)

Objective: implement Taillard's exact head and tail acceleration inside `neh` and
`insertion` so that Stage 4's entry condition — baselines are tuned before any
intervention is measured — holds before any device work is measured against them.

Status: complete; both heuristics score insertion positions from head and tail
arrays, the returned permutations are asserted identical to the pre-change
algorithm's, and the measurement is recorded.

Acceptance gate: every existing SPEC-0008 contract passes unchanged; a new contract
test compares both heuristics against the pre-change algorithm over the fixed grid
and all ten frozen Taillard instances and requires the same permutation rather than
the same makespan; that test is confirmed able to fail; `bash tools/check.sh` passes
with native acceptance covered. Resource budget: CPU only, no GPU workloads.

Why this first, before any kernel: the pass being replaced was `Theta(n^3 m)`, and a
device measured against it would have been measured against the clone-and-re-evaluate
loop rather than against the algorithm. That is the failure mode Stage 4's entry
condition exists to prevent, and it would have been invisible in the result: a large
speedup is exactly what a strawman baseline produces.

Where the acceleration lives is a contract question rather than a style one. The
value it computes is a makespan, and SPEC-0008 requirement 8 makes the recurrence
module the sole authority on what a schedule costs by keeping it architecturally
independent of everything that proposes one. Putting head and tail arrays in
`heuristic` would have given a heuristic its own cost model that happens to agree,
which is the shape of argument requirement 8 exists to refuse. They are in
`evaluate`, and `head[i]` is by construction the row `partial_completion_times`
would leave after `i` jobs.

The assertion is on permutations, not costs, and the difference is load-bearing.
Requirement 17 fixes which of several tied permutations a caller receives, so two
implementations can return different sequences of equal makespan and a
cost comparison would pass. The test therefore compares sequences, and it was
confirmed able to fail by relaxing the insertion tie-break from strictly-less to
less-or-equal — the exact mistake this rewrite invites, because it is the rewrite
that moves that comparison. Under that mutation the new test fails and
`construction_is_deterministic_including_under_ties` still passes, which is the
evidence that the existing suite could not have caught it: a deterministic wrong
answer is still deterministic.

`insertion` stays sequential. An accepted move is visible to the next job, so the
jobs cannot be scored independently of one another, and only the scoring of one
job's positions is accelerated. This is worth stating because the obvious next
optimization — evaluate all removals in parallel — would silently change which moves
the pass accepts, and it is the reason the device workload SPEC-0010 specifies is a
new producer rather than a faster `insertion`.

Measured on the development host, release build, best of three after a warmup, with a
0.41% noise floor from an identical binary. The full table is in
[known failures](known-failures.md). A 100-job, 20-machine improvement pass falls
from 32.66 ms to 0.92 ms, and a 200-job, 10-machine pass from 98.87 ms to 1.88 ms;
the ratio grows from roughly 3x at 20 jobs to roughly 50x at 200, which is what an
`O(n)` factor should do. The smallest instance is in the table on purpose: a single
large instance would have supported almost any claim about the shape of the
improvement.

What the numbers are not: a benchmark result or evidence. They are a development
diagnostic on one host, comparable only against another run of themselves, and
SPEC-0008 requirement 26 continues to forbid this slice recording a performance
claim. What they do change is C6's starting position, and not in a convenient
direction: a device now has to beat 23.86 ms of tuned single-threaded CPU work at 500
jobs rather than the several seconds the naive pass would have taken, so the
crossover will sit further out than it would have.

Evidence (2026-09-13): `bash tools/check.sh` passed with the pinned HiGHS 1.11.0
library linked and **zero test skips**, exit 0. Rust tests rose from 251 to 252, the
one new test being the naive-comparison contract; Python tests remain 60 and
documentation remains 55 pages. `Cargo.lock` and every `Cargo.toml` are untouched: no
crate was added and no dependency edge changed.

Follow-up: SPEC-0010's remaining phases. The next dependency-ready one is the scaled
workload, because a crossover measured only on the frozen 20-by-5 subset would report
that the CPU wins and would establish nothing about where the crossover lies.

## C6 Heterogeneous Computation Specification (2026-09-13)

Objective: write and accept the C6 contracts before any public GPU or
backend-selection API exists, as required by AGENTS.md, CONTRIBUTING.md and the
Stage 4 scope. No C6 behavior is implemented by this change.

Status: complete; SPEC-0010, SPEC-0011, ADR-0009 and ADR-0010 are accepted and the
project records that reference C6 are synchronized.

Acceptance gate: each specification uses numbered observable MUST/MUST NOT
requirements with an acceptance-test mapping, states its exclusions, and passes
documentation and link validation; `bash tools/check.sh` continues to pass with
native acceptance covered and **unchanged test counts**, because no behavior
changes. Had either count moved, this change would be doing something it claims not
to. Resource budget: CPU only, no GPU workloads; the device inventory was read once
through `nvidia-smi` for the hardware table below, which creates no CUDA context and
needs no lease.

Scope decided before implementation: C6's backlog line bundles two distinct
contracts, and CONTRIBUTING.md mandates one complete vertical slice, so they are
separated. SPEC-0010 owns heterogeneous computation itself — device selection,
residency, batching, transfer timing, arithmetic width, lease ownership, fallback,
cancellation, reset recovery and equivalence — and the batched integer schedule
evaluator that is its first workload. SPEC-0011 owns the GPU linear-programming
backend, which needs a capability concept on the solve contract that nothing in C1
through C8 required. Both are C6; neither is complete without the other, and the
first can be accepted, implemented and measured while the second is still a draft.

Why two decision records: they authorize different things. ADR-0009 amends
ADR-0003's single-unsafe-boundary rule, which is a workspace-wide structural change
and the same blocker C3, C8 and C9 each recorded rather than crossed. ADR-0010
decides that an approximate first-order solution never carries mathematical
authority, which is a numerical-authority decision that would still be needed if the
device were a CPU. Bundling them would let approval of the second imply approval of
the first.

The development host was observed with three Blackwell devices, compute capability
12.0, under driver 580.105.08 and CUDA 13.0.88: two GeForce RTX 5090 with 32,607 MiB
each and one RTX PRO 6000 Blackwell Server Edition with 97,887 MiB. This is recorded
because four properties of that compute capability are load-bearing in SPEC-0010's
requirements rather than incidental to them, and a reader checking the requirements
on sm_100 hardware would find different numbers: FP64 runs at one sixty-fourth of
FP32; INT32 and FP32 share one execution pipeline, so integer code runs at the full
lane rate; a thread block may address at most 99 KB of shared memory; and thread
block clusters are accepted by the assembler while `cluster.sync` degenerates to a
no-op, which is a silent-failure mode rather than a missing feature.

Three decisions inverted what the roadmap paragraph assumed, and each is recorded in
the contract that made it rather than only here. The first workload is integer
because of that FP64 ratio and that shared pipeline, which also means its CPU/GPU
equivalence is an exact identity at tolerance zero rather than an agreement within a
tolerance — the strongest form of the agreement evidence Stage 4 asks for, available
only because the arithmetic is integer. The same ratio does *not* disqualify GPU
linear programming, which is the opposite of what a peak-throughput reading suggests:
a sparse matrix-vector product is bounded by memory bandwidth at this intensity, with
roughly fivefold headroom before the FP64 rate could bind, so first-order methods are
viable here and factorizing ones are not. And "approximate results remain candidates
or warm starts until justified bounds exist" is met by constructing the justification
rather than by deferring it, because the justification is short and deferring it would
have left the backend's value impossible to evaluate except on throughput.

Two prerequisites were found while reading the code and are recorded in
[known failures](known-failures.md) rather than absorbed. The flow-shop heuristics
evaluate every insertion position by cloning the sequence and re-running the whole
recurrence, which is Theta(n^3 m) where Taillard's head/tail acceleration is
Theta(n^2 m); that was the right choice for C5, which forbids performance claims, and
it becomes a strawman the moment a device is measured against it, so Stage 4's entry
condition requires it be tuned first. And the frozen C5 subset is 20 jobs by 5
machines, roughly 1.3e4 integer operations for a full construction, so a crossover
measured only there would report that the CPU wins and would have established
nothing about where the crossover lies.

One correction was made during drafting and is worth recording because it nearly
shipped. An early draft claimed the contract needed no schema version, on the grounds
that a `device` field already existed. It does — in `run-config-v1`, which is the
benchmark manifest's configuration, not the search configuration a run record embeds.
A device recorded only in provenance would describe a run that `optimizer verify`
could not repeat, because SPEC-0005 verification reads only the record's embedded
configuration. SPEC-0010 requirements 40 and 41 therefore accept the version cascade
this actually costs: `search-config-v3`, `search-record-v3` and `run-record-v2`. The
solve configuration stays at version 1, because SPEC-0006 requirement 6 permits one
lease holder across device selections, so a search cannot use two devices and a
per-solve device would be a configuration able to express something the lease forbids.

Evidence (2026-09-13): `bash tools/check.sh` passed with the pinned HiGHS 1.11.0
library linked and **zero test skips**, exit 0, in 29 seconds. Rust tests remain 251
and Python tests remain 60, which is the acceptance gate for a contract with no
behavior: had either moved, this change would be doing something it claims not to.
Documentation moved from 51 to 55 pages, which is the four new contract documents and
nothing else. `cargo deny` reports advisories, bans, licenses and sources ok with no
lockfile change, because no crate was added; `optimizer-cuda-sys` and its `libc`
dependency arrive with the implementation, not with the contract.

Expected changes: docs/specifications/SPEC-0010-heterogeneous-computation.md,
docs/specifications/SPEC-0011-gpu-lp-backend.md,
docs/decisions/ADR-0009-cuda-driver-boundary.md,
docs/decisions/ADR-0010-certified-gpu-lp.md, state/backlog.yaml, AGENTS.md,
state/known-failures.md, implementation-plan.md, wiki/status.md, README.md,
docs/architecture/overview.md, docs/architecture/testing.md, docs/operations/gpu.md,
cuda/schedule_eval/README.md, the forward references in SPEC-0006 and SPEC-0009, and
this record. No CHANGELOG.md entry: the changelog records user-visible changes and an
accepted contract with zero behavior is not one, matching the C2, C5 and C8
specification commits.

Also corrected here rather than left to be decoded: SPEC-0006, `docs/operations/gpu.md`
and `cuda/schedule_eval/README.md` deferred kernel work to a milestone named M5, which
the roadmap later renamed C6. Nothing else in the repository uses that name, so those
references pointed at a milestone a reader could not look up.

Follow-up: SPEC-0010's implementation phases, beginning with the tuned CPU baseline
that Stage 4's entry condition requires before any intervention is measured.

## Local Track B Integration (2026-09-12)

Objective: verify the Track B node-path branch from a clean checkout, integrate it
into local main, and delete the feature branch after confirming its commits are
retained.

Status: complete; clean-checkout verification, fast-forward integration and
feature-branch cleanup finished.

Acceptance gate: the complete gate passes in an independent clone with nothing
prebuilt; fast-forward integration preserves the reviewed tip e8fcd7b; the feature
branch is deleted and the worktree is clean. Resource budget: CPU only, no GPU
workloads.

Evidence (2026-09-12): the branch was cloned with `--no-hardlinks` and no `target/`
directory present, and `bash tools/check.sh` passed there in 2 minutes 3 seconds
with **zero test skips**, building the pinned HiGHS 1.11.0 library inside the clone
and running 251 Rust and 60 Python tests. main fast-forwarded from 5beccfd to
e8fcd7b with no conflicts and no history rewriting; `git diff e8fcd7b main` is
empty, `git merge-base --is-ancestor` confirms the reviewed tip is retained, and
`git branch -d` removed the fully merged branch. The bootstrap smoke was rerun on
the integrated revision, recording e8fcd7b with `dirty: false`.

`Cargo.lock` and `Cargo.toml` are untouched by the whole branch. No crate was
added and no dependency edge changed, which is why this integration did not need
the stronger justification the C4 and C8 clean-checkout runs did — it was run
anyway, because `Model::rebound` is new public API and the branch rewrote a path
every search takes.

One item was found and fixed before integration rather than carried onto main.
SPEC-0001 gained requirement 2a in 5fe8ba3, but its review marker still named
9e6dc86 — a GitHub synchronization record that never touched the file — so the
specification claimed review at a revision predating a normative requirement it
now contains. This is the same staleness 95c1d81 and f0af453 corrected for C8 and
C5. Worth recording is how nearly it was missed: an audit comparing every marker
against its file's last-change commit reported all eighteen specifications and
ADRs as stale, which is a useless answer, because the commit that sets a marker is
itself a change to the file and no correct marker can ever match. The check was
discarded and the one real case identified by reading the history instead.

No remote refs were changed. main is now 13 commits ahead of origin/main and
remains unpushed pending the maintainer's authorization; the publication state is
recorded in [known failures](known-failures.md).

Follow-up: C6, heterogeneous computation and GPU feasibility, is the next
dependency-ready capability and still has no accepted specification. Write one
before introducing any public GPU or backend-selection API. The two deferred
per-node items — the constraint clone in `node::relaxation` and cross-node `Highs`
instance reuse — are recorded in [known failures](known-failures.md) with the
measurement each would need.

## Track B: Node-Path Measurement and Waste Removal (2026-09-12)

Objective: make solver timing measurable, then remove work the branch-and-bound
node path does and discards, without changing any conclusion.

Status: complete; the harness, all five removals and the multi-node gate fixture
are in place and gated. Every item this track set out to do is done, and the two
it declined are recorded below with their reasons.

Acceptance gate: every compared field and node counter is identical before and
after each change, asserted by the harness rather than by eye; every diagnostic
whose text is touched is pinned byte-exactly by a test written against unmodified
code; and `bash tools/check.sh` passes with native acceptance covered after each
commit. Resource budget: CPU only, no GPU workloads.

There was no way to measure a solver change before this. `benches/` held a
placeholder and `tools/benchmark_smoke.py` times `optimizer hello`. The bottleneck
ranking recorded in the plan was therefore static analysis, and the first task was
to replace it with numbers.

The unit of work is a fixed node budget with `time_limit_ms` null, over ta001 to
ta003 from the frozen Taillard set. A time limit would couple the outcome to host
speed, so before and after would explore different trees — the comparison would be
meaningless and the ten fields SPEC-0005 requirement 11 compares would
legitimately move. A node budget holds the work constant, and every run terminates
at the limit and claims nothing.

Measured, minimum of three runs after a warmup, release build, same host:

| change | ta001 | ta002 | ta003 |
| --- | --- | --- | --- |
| baseline | 8028.9 ms | 4186.1 ms | 5369.7 ms |
| basis extracted only on request | -5.8% | -10.4% | -8.9% |
| evaluation diagnostics built lazily | -11.5% | -22.5% | -17.3% |
| structural diagnostics built lazily | -1.0% | -3.5% | -2.4% |
| candidate borrowed when already canonical | -1.3% | -2.3% | -1.8% |
| node relaxation rebounded, not rebuilt | -0.3% | -0.7% | -0.4% |
| **cumulative** | **-18.8%** | **-35.0%** | **-28.1%** |
| *noise floor, identical binary* | *0.1%* | *0.2%* | *0.1%* |

The noise floor is in that table on purpose. The last row of real work is
-0.3% to -0.7% against a repeat-measurement spread of 0.1% to 0.2%, so it is
roughly two to three times noise and no more. Reporting it alone would overstate
it; reporting it beside the floor lets a reader judge it. The first three items
are large enough that the distinction does not arise.

What the numbers are not: they are a development diagnostic, not evidence. The
tool records `"claim": "none"`, defines no threshold, and is comparable only
against another run of itself on the same host. Nothing here is a benchmark result
and no performance property is claimed of the engine.

The largest single item was pure waste. Node relaxations are always continuous, so
the backend extracted an LP basis on every node; extraction computes the model's
canonical fingerprint, which serializes the entire model with
`serde_json::to_string_pretty`. The encoded ta001 model is 567,565 bytes, so a
256-node search serialized and discarded roughly 145 MB — to build a value
`Backend::solve` dropped on the next line and that SPEC-0003 requirement 23
forbids reusing anyway.

The second was diagnostics nobody reads. `checked` took `&str`, so `expression`
formatted about four `String`s per matrix nonzero on the success path and
`check_bound` two to three per call. At 5,175 nonzeros and two to three
evaluations per node that is tens of thousands of allocations per node for text a
valid model never produces. `Model::new`'s per-nonzero context had the same shape
and is on the same path, because `node::relaxation` rebuilds and revalidates a
model per node.

The last two were the smallest and are worth recording for what they cost rather
than for what they saved. `Candidate::canonical` cloned and re-sorted a candidate
a backend had just built by iterating the model's own sorted variables; it now
returns `Cow` and borrows when the input is already canonical. `node::relaxation`
went through `Model::new`, which re-sorted and revalidated every row and the
objective once per node for data the node did not touch; it now goes through
`Model::rebound`, which validates the supplied bounds and refuses any variable
list that is not the original's IDs.

That refusal is the whole basis for skipping the row checks, and it is stated as
SPEC-0001 requirement 2a rather than left implicit in code. The skipped checks
decide two things — coefficients are finite, and every term names a variable the
model has — and the first is carried from a document that already passed while the
second is exactly what the ID requirement preserves. This follows how SPEC-0003
requirement 12a and SPEC-0004 requirement 9a were recorded when implementation
found a rule the contract had not stated. No ADR: the change is strictly narrowing
and reverses nothing accepted.

Method worth keeping: characterization first. Eleven tests pinning the byte-exact
text of every diagnostic these commits touch were written and passed against
unmodified code before any of it moved, and the two candidate-canonicalization
contracts were written the same way, against the clone-always implementation. Three
of the eleven were wrong on the first attempt in an instructive way — the fixtures
aimed at a constraint-level message and hit the variable-level one, because
variables are checked first. Discovering that from a failing characterization test
is the cheap version of discovering it from a changed error message in production.

Every behavior change here was also verified by reinstating the defect rather than
by assertion alone. An unconditional canonical fast path fails the signed-zero
contract with bits 9223372036854775808 against 0 and takes three pre-existing
contracts with it; disabling `rebound`'s ID refusal fails the refusal contract.

Two traps avoided rather than survived. `checked` returns `zero(value)`, not
`value`, and that negative-zero normalization is observable through
`VariableCheck.value` and therefore every serialized validation report; a lazy
rewrite that returned the raw product would have changed committed records. The
same trap reappeared in the candidate fast path, where borrowing a candidate
holding `-0.0` would publish a different number than the owned path does, which is
why the fast path tests for negative zero and not merely for sorted-and-distinct.
And the harness compares conclusions itself and fails outright if any moved, so a
timing win accompanied by a counter change is reported as a bug rather than a
speedup.

A blind spot found while closing the track, and the reason the last commit is a
test rather than a removal: both committed run records reported `nodes_explored:
1`. `tools/verify_committed_record.py` is the only check that re-executes a record
against a later build, and it had therefore never descended past the root node —
while every change on this branch was on the per-node path. A generated 5x3
instance exploring 37 nodes, pruning 23 by bound and proving optimality now closes
that. Its counters are asserted against the committed record rather than the
verdict, which does not carry them, so swapping in a single-node record fails
loudly instead of passing quietly.

Not attempted, and why: reusing the `Highs` object across nodes is legal under
requirement 23, which forbids reusing a *basis* rather than the instance, and is
the obvious next item — deferred pending the measurement that now exists. The
constraint and objective clone in `node::relaxation` also remains and is now
likely the dominant per-node cost, since `rebound` removed the validation beside
it but not the copy; eliminating it needs shared ownership inside `ModelDocument`,
which is a public type change with a wide ripple and belongs behind its own
measurement. Cross-node warm start and any parallelism remain out of scope; both
are forbidden by accepted contracts (SPEC-0003 requirement 23, SPEC-0002
requirement 5) and need their own decision records.

Evidence (2026-09-12): `bash tools/check.sh` passed after each of the three
commits with the pinned HiGHS 1.11.0 library linked and **zero test skips**, exit
0. Rust tests rose from 247 to 251 — two candidate-canonicalization contracts and
two `rebound` contracts — while Python tests remain 60 and documentation 51 pages.
The last commit adds a gate step and fixtures rather than contracts, so it moves
neither count, which is the expected result for what it claims to do.

Follow-up: Track B is closed. C6, heterogeneous computation and GPU feasibility,
is the next dependency-ready capability and still has no accepted specification;
write one before introducing any public GPU or backend-selection API. The two
deferred per-node items above are recorded in
[known failures](known-failures.md) rather than carried as intentions.

## Local Track A Integration (2026-09-12)

Objective: verify the C8 follow-up branch from a clean checkout, integrate it into
local main, and delete the feature branch after confirming its commits are
retained.

Status: complete; clean-checkout verification, fast-forward integration and
feature-branch cleanup finished.

Acceptance gate: the complete gate passes in an independent clone with nothing
prebuilt; fast-forward integration preserves the reviewed tip 8cddb44; the feature
branch is deleted and the worktree is clean. Resource budget: CPU only, no GPU
workloads.

Evidence (2026-09-12): the branch was cloned with `--no-hardlinks` and no `target/`
directory present, and `bash tools/check.sh` passed there in 1 minute 33 seconds
with **zero test skips**, building the pinned HiGHS 1.11.0 library inside the clone
and running 234 Rust and 60 Python tests. main fast-forwarded from dfdc245 to
8cddb44 with no conflicts and no history rewriting; `git diff 8cddb44 main` is
empty, `git merge-base --is-ancestor` confirms the reviewed tip is retained, and
`git branch -d` removed the fully merged branch. The bootstrap smoke was rerun on
the integrated revision, recording 8cddb44 with `dirty: false`.

One process note worth recording rather than hiding: the first commit on this
branch used `git add -A` and captured all of Track A under a message describing
only the review-marker fix. It was split into two honest commits before anything
was integrated. The branch was local and unpushed, so no shared history was
rewritten.

Publication state changed outside this work. The maintainer pushed the work
through `dfdc245` to origin, so every milestone up to and including C8 is now
published. Records dated before that push describe main as unpushed pending
authorization; they were accurate when written and are left as written rather than
backdated. [Known failures](known-failures.md) now carries the current state. The
two Track A commits are local and unpushed, and remain so pending the maintainer's
own push.

Follow-up: Track B, the measurement harness and the behaviour-preserving waste
removal on the per-node path, is next. C6 still has no accepted specification.

## C8 Follow-Up Items (2026-09-12)

Objective: close the three items the C8 integration record left open — SPEC-0009
requirement 14's overstated wording, requirement 20's possibly-unreachable
verification branch, and the stale C5 review markers.

Status: complete; the full gate passes with native acceptance covered.

Acceptance gate: requirement 14 is narrowed to what the implementation can
actually guarantee; requirement 20's branch is either reached by a test or
recorded as unreachable with a decision; the C5 markers name the implementing
revision; and `bash tools/check.sh` passes with native acceptance covered.
Resource budget: CPU only, no GPU workloads.

Requirement 20's branch is reachable, and the earlier doubt came from testing it
the wrong way round. Restamping the *registry* is refused by the declaration check
first, because the extension still reports the version it always did — the existing
test's own comment says so. The rule the requirement describes runs the other
direction: a record naming a version the current build no longer declares, which is
what happens when a record outlives the build that produced it and the extension's
version has since moved. A new contract restates the version in the record's
extension summary, leaves the registry alone so resolution succeeds, and reaches
the comparison. Disabling the branch makes it fail, so it is not vacuous. Nothing
was deleted.

That diagnosis found a second defect, in the acceptance gate itself.
`tools/verify_committed_record.py` restamped the registry and then asserted only
that `9.9.9` appeared in stderr. Resolution's declaration-mismatch message contains
that string too, so the check passed on the wrong error and never reached
requirement 20 — while its comment claimed to "isolate the version refusal". The
gate now covers both rules separately, each asserting the message its own rule
produces, and the requirement 20 case is checked across a commit boundary as
SPEC-0009's acceptance section says it is. Verified by disabling the branch: the
gate step now fails where it previously passed. This is the same class of defect
the C8 clean-checkout run found — a check passing for a reason other than the one
it names — and it is worth recording that it was found by pulling on a thread
about a *different* requirement.

Requirement 14 was wrong as written rather than under-implemented. It claimed
resolution never constructs a refused extension, but `Extension::declare` is the
authority a declaration mismatch compares against and the provider is what supplies
the role, so both mismatches are necessarily decided after construction. The rule is
now split: requirement 14 governs invocation and holds everywhere; requirement 14a
governs construction and names the refusals decided before it — a gpu hardware
requirement, an unsatisfied data requirement, an unpermitted experimental entry and
a failed promotion check are all decided before the provider is consulted, while an
unprovided identity consults the provider but constructs nothing. The
implementation did not change, and the acceptance mapping now says which refusals
can be asserted against a construction counter and why the others cannot.

Evidence (2026-09-12): the complete `bash tools/check.sh` gate passed with the
pinned HiGHS 1.11.0 library linked and **zero skip messages**, exit 0. Rust tests
rose from 233 to 234, the requirement 20 contract. Python tests remain 60 and
documentation 51 pages.

Follow-up: C6 remains the next capability and still has no accepted specification.
The remaining thin spots in SPEC-0009's acceptance mapping — requirement 20's
nondeterministic-record case, requirement 21's positive diagnostic case,
requirement 22's forfeited registry-backed record, `optimizer search --registry`
with a non-empty policy, and the document-level parse cases — stay recorded in
[known failures](known-failures.md); each needs a fixture this build does not have.

## Local C8 Integration (2026-09-12)

Objective: verify the feat/extension-registry branch from a clean checkout,
integrate it into local main, and delete the feature branch after confirming its
commits are retained.

Status: complete; clean-checkout verification, fast-forward integration and
feature-branch cleanup finished.

Acceptance gate: the complete gate passes in an independent clone with nothing
prebuilt; fast-forward integration preserves the reviewed tip 7757af6; the feature
branch is deleted and the worktree is clean. Resource budget: CPU only, no GPU
workloads.

Evidence (2026-09-12): the branch was cloned with `--no-hardlinks` and no `target/`
directory present, and `bash tools/check.sh` passed there in 2 minutes 2 seconds
with **zero test skips**. That run built the pinned HiGHS 1.11.0 library from the
checksum-verified upstream archive inside the clone, producing `libhighs.a` at
10,186,956 bytes, ran 233 Rust and 60 Python tests, re-executed the committed run
records against the freshly built binary, validated 51 documentation pages, and
passed cargo-deny, artifact validation and bootstrap smoke.

This clean-checkout pass is the acceptance evidence for the integration, and it was
not a formality. The first attempt **failed**, at
`a_registry_does_not_change_a_search_that_names_no_extension`, and the cause was a
record identifier derived from measured elapsed time rather than anything the
registry does. Every warm-tree gate run during C8 had passed because both searches
finished in the same millisecond. That defect, its fix and the reasoning are
recorded above under the C8 verification follow-up. C8 adds a crate, a dependency
edge and a lockfile change, which is the case the C4 record identifies as the one
where a clean checkout earns its cost; this time it earned it for a different
reason than a stale lockfile.

main was fast-forwarded from 08ed424 to 7757af6 without conflicts or history
rewriting, so the integrated tree is byte-identical to the verified revision, which
`git diff 7757af6 main` confirms as empty. `git merge-base --is-ancestor` confirmed
the reviewed tip is retained, and `git branch -d` removed the fully merged
feat/extension-registry branch, which refuses a branch whose commits are not
reachable. The worktree is clean and the bootstrap smoke was rerun on the integrated
revision, recording 7757af6 with `dirty: false` for clean revision-bound provenance.

The branch held five commits: d48ce11 specifying the registry, 6cf6d5e implementing
it, 95c1d81 correcting the two review markers to name the implementing revision,
bb13f67 narrowing the requirement 17 contract when the clean checkout failed, and
7757af6 fixing the identifier derivation and restoring that contract to a whole
record comparison. bb13f67 is partly superseded by 7757af6 and was kept rather than
rewritten, because the intermediate state is what motivated the fix and shared
history is not rewritten.

No remote refs were changed. main is now 5 commits ahead of origin/main and remains
unpushed pending separate authorization; the origin remote and its outstanding
protection settings are recorded in [known failures](known-failures.md).

Follow-up: C6, heterogeneous computation and GPU feasibility, is the next
dependency-ready task and has no accepted specification. Write one before
introducing any public GPU or backend-selection API. Two items recorded during C8
are worth picking up with it or before it: SPEC-0009 requirement 14's "MUST NOT
construct" is narrower in practice than it reads and wants a wording correction, and
the requirement 20 version comparison at verification may be unreachable and should
be diagnosed rather than deleted on inspection. SPEC-0008 and ADR-0007 also still
name 5157786, the C5 specification commit, rather than its implementing commit
08ed424, which is the same marker staleness 95c1d81 fixed for C8.

## C8 Verification Follow-up: Clock-Derived Record Identifier (2026-09-12)

Objective: remove measured elapsed time from a run record's identifier, and specify
what the identifier is so the derivation cannot regress.

Status: complete; the full gate passes with native acceptance covered, and the
clean-checkout verification that found the defect now passes.

Acceptance gate: two runs of the same model and configuration produce the same
identifier; a changed configuration and a changed model each produce a different
one; the SPEC-0009 requirement 17 contract compares whole records again with only
elapsed time normalized; the contract fails with the old derivation reinstated; and
`bash tools/check.sh` passes with native acceptance covered. Resource budget: CPU
only, no GPU workloads.

How it was found, because the method is the point: every gate run during C8 used a
warm `target/` and passed. The clean-checkout verification, run before integrating
the branch, failed at
`a_registry_does_not_change_a_search_that_names_no_extension`. The registry was not
the cause. `record_id` was built as `run-{model_id}-{elapsed_ms}`, both searches
finished in 0 ms on the warm tree so their identifiers matched, and in the
independent clone one took 0 ms and the other 1 ms. The contract had been failing
on the clock since it was written and passing by luck.

The defect is older than C8. `search.rs` and `schedule.rs` have derived the
identifier this way since C4 and C5 respectively; the C8 contract was simply the
first thing to compare two whole records produced by separate invocations. A record
identifier that moves with the clock makes a record's identity a property of how
busy the machine was, which SPEC-0005 requirement 12 already excludes from meaning,
and it collides for unrelated searches that happen to take equally long.

What was decided rather than assumed: the identifier now derives from the SHA-256
digests of the input documents the record already carries. Two runs of the same
model and configuration therefore share an identifier, and that is the intended
reading rather than a residual collision — the identifier names the inputs a record
describes, and whether two such runs agree is what `optimizer verify` exists to
answer. `revision` and `model_fingerprint` stay separate fields, so the identifier
does not duplicate the build or the model dimension. The rule is now SPEC-0005
requirement 1a, added rather than left implicit, matching how SPEC-0003 requirement
12a and SPEC-0004 requirement 9a were recorded when implementation found a rule the
contract had not stated.

Why this needed no record version and no ADR: `record_id` is not among the ten
fields requirement 11 compares, so agreement is untouched and SPEC-0005's rule that
a change to the compared fields is breaking does not apply. The field, its type and
its schema constraint are unchanged, no exit code or stderr category moved, and the
committed example records carry hand-written identifiers rather than generated
ones, so none of them changed. The schema gains a description only.

Evidence (2026-09-12): the complete `bash tools/check.sh` gate passed with the
pinned HiGHS 1.11.0 library linked and **zero skip messages**, exit 0. Rust tests
rose from 232 to 233, the new identifier contract. Python tests remain 60 and
documentation 51 pages. The fix is verified by reinstating the defect rather than by
assertion alone: with `run-{model_id}-{elapsed_ms}` restored the new contract fails
at the changed-configuration assertion, and with the fix it passes. Restoring the
requirement 17 contract to a whole-record comparison is the second check, since it
now compares `record_id` like every other field.

## C8 Extension Registry Implementation (2026-09-12)

Objective: implement C8 under the accepted SPEC-0009 and ADR-0008: the registry
document and its strict parser, resolution with each refusal path in its own
category, the reusable conformance suite and its record, the CLI provider table and
`registry` subcommands, registry integration in `search`, `verify` and
`schedule solve`, the two JSON Schemas with committed examples, and a gate step
re-executing a committed registry-backed scheduling record.

Status: complete; the specification preceded the implementation, and the full gate
passes with native acceptance covered.

Acceptance gate: each resolution refusal is asserted separately in its own
`ErrorKind` category; a promoted entry is refused when its conformance record is
absent, tampered with, failing or naming another version; a scheduling run
registering the NEH producer writes a record that verifies by re-execution, both in
Rust and across a commit boundary in the gate; a registry supplied to a search
naming no extension changes nothing; the conformance suite runs and its committed
record regenerates; and `bash tools/check.sh` passes with native acceptance
covered. Resource budget: CPU only, no GPU workloads.

Evidence (2026-09-12): the complete `bash tools/check.sh` gate passed with the
pinned HiGHS 1.11.0 library linked and **zero skip messages**, exit 0, with no
native-uncovered warning. Rust tests rose from 191 to 232 and Python tests from 45
to 60. Documentation rose from 48 to 51 pages: SPEC-0009, ADR-0008 and the
register-an-extension tutorial. No checks were waived; the RustSec advisory fetch
recovered through the cached database as already recorded.

`Cargo.lock` changed only by adding the new optimizer-registry crate and local
dependency edges. No external package version changed and no new external
dependency was introduced. The registry crate depends on the published core,
extension and executive APIs and on no crate supplying a concrete extension, so the
provider seam is enforced by the build rather than asserted: the concrete table
lives in optimizer-cli.

Correctness evidence, stated as what was actually checked:

- Every refusal path is asserted in its own `ErrorKind` category: an unprovided
  identity; a declaration disagreeing with its entry on version, category, host
  contract version, problem class, determinism and limits, each individually; a
  provider returning the wrong role; an authority not implied by the category; the
  transformation category; an unmet data requirement; a gpu hardware requirement;
  an absent required identity; a declared conflicting pair; a promoted entry whose
  record is absent, tampered with, failing, or names another extension or version;
  and an experimental entry without permission.
- Refusal is total. A two-entry registry in which one entry is refused refuses the
  whole set, and the CLI writes no record for such a run.
- The refusals decided before construction are asserted against the provider's own
  construction counter, so neither can pass because nothing was ever built.
- A scheduling run registering the NEH producer through a registry writes a record
  that verifies by re-execution and exits 0. The gate re-executes such a record
  committed at an earlier revision, which is the property no in-process test can
  establish.
- A registry whose entry names a different producer version is refused at
  verification as unsupported rather than reported as divergence, so the verifier
  does not blame a record for a property of its own inputs.
- An experimental entry is refused without `--allow-experimental` and, with it,
  the written record carries a warning naming it.

Findings during implementation, each recorded rather than patched silently:

The conformance suite had no test at all. `conformance::run` and
`optimizer registry check` had exactly one caller between them, the production code
path, so requirements 23 to 25 had no evidence and the committed
`examples/conformance-record-v1.json` was a frozen artifact that was internally
consistent and correctly checksummed but never re-derived. That is the specific
failure the suite exists to prevent: `examples/extension-registry-v1.json` promotes
`flow-shop-neh` by citing that file's SHA-256, so a producer that regressed would
have kept citing a passing record while every check still agreed with it. New CLI
contracts now regenerate the record through `registry check` and compare it byte for
byte, and the assertion was shown to fail by perturbing the committed file. The
suite's own invariance comparison is unit-tested against each of the six fields it
compares, because SPEC-0004's containment means no extension reachable through the
host can move them — a broken comparison would otherwise be indistinguishable from
a conforming extension.

`entry_order_does_not_affect_resolution` was vacuous. Its adviser entry recorded an
identity its declaration did not match, so both orders were refused on the first
policy and the test asserted only that two identical errors were identical; it
passed with both identity sorts deleted. It now resolves two entries successfully in
both orders and asserts the identity and role sequences the host receives, and it
was shown to fail with the sort removed. The refusal-determinism case it used to
cover is kept as a separate test, because a test that only ever observes refusals
cannot see the ordering it claims to check.

Requirement 17 had no test. An empty extension policy with a registry supplied must
still take the extension-free entry point, which is the compatibility claim the
whole slice rests on, and it was asserted only in a code comment. A run surface
contract now compares the two records field by field apart from elapsed time.

`docs/architecture/testing.md` claimed that every refusal test asserts the
extension's own construction or invocation counter. Two did, and the invocation
counter was written and never read. The claim is now accurate, the dead
instrumentation is removed, and the reason the declaration-mismatch paths cannot
assert it is stated: resolution has to construct the extension and call `declare`
to discover the disagreement, which means requirement 14's "MUST NOT construct" is
narrower in practice than it reads. That narrowing is recorded in
[known failures](known-failures.md) as a specification correction to make, not a
code change to sneak in.

Recorded and not closed, because each needs a decision rather than a patch:
requirement 20's nondeterministic-record refusal has no fixture that can produce
one; requirement 20's version comparison at verification may be unreachable, since
resolution has already equated the declaration with the entry, and the branch is
left in place rather than deleted on inspection alone; requirement 21's positive
diagnostic case, requirement 22's forfeited registry-backed record, and
`optimizer search --registry` with a non-empty policy are all untested, the last
because both provided extensions are flow-shop producers that cannot be built from
a bare model. All are in [known failures](known-failures.md).

Scope boundary held: no schema version changed anywhere, no existing document
gained or lost a field, and the compared fields stay the ten SPEC-0005 fixed. The
committed C4 example record still re-executes and verifies inside the gate. An
extension summary difference is a diagnostic note that does not change an exit code,
matching the existing environment-difference rule.

What is deliberately not claimed: no performance, runtime or solution-quality
result. Promotion means the contract conformance suite passed, never that the
extension improves a search, which stays C7's question. The conformance record
carries no timing field, and a test asserts its absence so one cannot arrive
quietly.

Follow-up: C6, heterogeneous computation and GPU feasibility, is the next
dependency-ready task and has no accepted specification; write one before any
public GPU or backend-selection API. C9 and C10 are also unblocked now that C8 is
complete, and both keep their recorded blockers.

## C8 Extension Registry Specification (2026-09-12)

Objective: write and accept the C8 contract before any public registry API exists,
as required by AGENTS.md, CONTRIBUTING.md and the Stage 3 scope. No C8 behavior is
implemented by this change.

Status: complete; SPEC-0009 and ADR-0008 are accepted and the project records that
reference C8 are synchronized.

Acceptance gate: the specification uses numbered observable MUST/MUST NOT
requirements with an acceptance-test mapping, states its exclusions, and passes
documentation and link validation; `bash tools/check.sh` continues to pass with
native acceptance covered and **unchanged test counts**, because no behavior
changes. Had either count moved, this change would be doing something it claims not
to. Resource budget: CPU only, no GPU workloads.

Why C8 and not C6: Stage 4's entry condition is that Stage 3 provides reproducible
workflows, and C8 is Stage 3's last open item. It is also the seam two recorded
known-failures point at, so it blocks rather than merely precedes: the registry does
not exist, and a C5 scheduling run performed with the NEH producer is not verifiable
by re-execution at all. C6's dependencies are met, but starting it would leave
Stage 3's reproducibility claim partial.

Scope decided before implementation: the registry alone. C8's backlog line bundled
three deliverables and CONTRIBUTING.md mandates one complete vertical slice, so the
Python SDK becomes C9 with its pyo3/ADR-0003 blocker unchanged and the comparative
experiment runner becomes C10. Existing references to "C8's registry" stay accurate
because C8 keeps the registry.

Two contract decisions worth recording, because both are the kind a later
implementation could get quietly wrong:

The registry resolves; it does not load. An entry names an extension the build
already provides through a caller-owned `Provider` seam, which is the same pattern
as `&dyn Backend` and `&[Registration]`. Dynamic native loading needs a second
unsafe boundary ADR-0003 prohibits, so it stays deferred; the registry now makes
that absence more visible rather than closing it.

No document version changes and agreement is untouched. An extension is identified
in a record by the `extension_id` and `version` its `ExtensionSummary` already
embeds verbatim, so a record naming an extension is re-resolvable without a new
field. Adding the registry to the compared fields would change what agreement means
for every existing record, which SPEC-0005 reserves for a new record version plus an
ADR. A resolved-version mismatch and a nondeterministic summary are therefore
refused as *unsupported* rather than reported as divergence, which is the same
distinction the C5 implementation drew when it turned a misleading divergence into a
refusal.

Expected changes: docs/specifications/SPEC-0009-extension-registry.md,
docs/decisions/ADR-0008-registry-resolution.md, state/backlog.yaml, AGENTS.md,
state/known-failures.md, implementation-plan.md, wiki/status.md, the forward
references in SPEC-0004, SPEC-0005 and SPEC-0008, and this record. No CHANGELOG.md
entry: the changelog records user-visible changes and an accepted contract with zero
behavior is not one, matching the C2 and C5 specification commits.

Follow-up: C8 implementation is dependency-ready under SPEC-0009. It requires the
optimizer-registry crate with the strict registry document, resolution with each
refusal path in its own category, the reusable conformance suite over a fixed grid,
the CLI provider table and subcommands, registry integration in `search`, `verify`
and `schedule solve`, the two JSON Schemas with committed examples, and a gate step
re-executing a committed registry-backed scheduling record so the closed gap is
established across a commit boundary rather than within one process.

## C5 Flow-Shop Scheduling Implementation (2026-09-11)

Objective: implement C5 under the accepted SPEC-0008 and ADR-0007: flow-shop
instances, the makespan recurrence, the positional encoding, deterministic NEH and
insertion producers, a scheduling command surface, and a frozen generated Taillard
development subset.

Status: complete; the specification preceded the implementation, and the full gate
passes with native acceptance covered.

Acceptance gate: the optimum the executive proves on an encoded model equals the
minimum found by exhaustive permutation enumeration over a fixed grid; the recurrence
agrees with an independently written oracle; the generator reproduces Taillard's
published verification instance exactly; a producer whose proposals are refused
leaves the outcome, proven optimum, dual bound, forfeiture state and both prune
counters unchanged; a scheduling run writes a verifiable run record; and
`bash tools/check.sh` passes with native acceptance covered. Resource budget: CPU
only, no GPU workloads.

Evidence (2026-09-11): the complete `bash tools/check.sh` gate passed with the
pinned HiGHS 1.11.0 library linked and **zero skip messages**, exit 0 in 16 seconds
on a warm build directory, with no native-uncovered warning. Rust tests rose from
159 to 191 and Python tests from 39 to 45. Documentation remains 48 pages, because
SPEC-0008 and ADR-0007 were added by the specification commit. The
`AI_OPTIMIZER_SKIP_NATIVE=1` configuration also passed with all 191 tests and its
uncovered-acceptance warning. No checks were waived; the RustSec advisory fetch
recovered through the cached database as already recorded.

`Cargo.lock` changed only by adding local dependency edges and the new
optimizer-schedule-examples crate. No external package version changed and no new
external dependency was introduced: the Lehmer generator is Taillard's own published
algorithm rather than a general-purpose RNG crate, which is a correctness
requirement and not a dependency preference.

Correctness evidence, stated as what was actually checked:

- Over a fixed grid of tiny instances with no randomness, the executive's proven
  optimum on the encoded model equals the minimum from exhaustive enumeration of
  every permutation, and the decoded winner re-evaluates through the recurrence to
  that same value. Three independent views must agree, so neither the encoding nor
  the recurrence can be wrong alone without failing. The grid sizes are asserted so
  they cannot silently shrink.
- The recurrence agrees with a separately written oracle over 5,232
  instance-permutation pairs. The independence is architectural rather than
  asserted: `evaluate` imports neither `encode` nor `heuristic`, and the test oracle
  is a second implementation in the test file.
- The generator reproduces Taillard's published `ta001` matrix exactly from seed
  873654221, checked in Rust against the published matrix and independently in
  Python against a second implementation of the generator. Both a wrong seed and a
  transposed loop order are shown to disagree, so the check can fail.
- Every one of the ten frozen instances regenerates from its manifest-recorded seed
  and parameters to the committed bytes, and its committed checksum is verified.
- A producer whose every proposal is refused leaves the outcome, proven optimum,
  dual bound, forfeiture state and both prune counters identical to the
  producer-free run, with the refusal recorded as rejected rather than absorbed.
- Every scheduling test that depends on a producer asserts the producer's own
  proposal counter first, so none can pass because the producer was never consulted.
- Decoding refuses a fractional assignment, a position selecting two jobs, a
  position selecting none, one job filling two positions, a candidate naming another
  model, and a candidate missing a variable. None is rounded or repaired.
- The end-to-end surface was exercised on the built binary: a 5-job, 3-machine
  instance reported `proven_optimal` with objective 372, matching independent
  brute-force enumeration of all 120 permutations, and its record verified.

Two findings during implementation, both recorded rather than patched silently:

An early test asserted that an *honest* producer left both prune counters unchanged.
It failed, correctly: `nodes_pruned_bound` went from 0 to 1 because an accepted
incumbent legitimately prunes more by bound, which is the entire purpose of a
candidate producer. SPEC-0008 requirement 20 was already scoped to a refused or
absent proposal, so the contract was right and the test was wrong. A
`RefusedProducer` was added to test the invariance claim for what it actually says,
and the honest producer is now asserted against requirement 19's promise instead.
C3's identically worded rule is consistent, because it was established with hostile
extensions whose proposals are all refused. The specification's acceptance section
now records this rather than leaving the scope looking arbitrary.

`optimizer verify` reported a *divergence* for a record produced with the producer
registered, naming a node-count difference. That diagnosis was misleading:
verification re-executes through the extension-free entry point, so it reproduced a
search the record does not describe and the counters differed for that reason alone.
SPEC-0005 requirement 14 already refuses such a configuration on the search path, so
the same rule now applies to verification and the record is refused as unsupported
instead. The consequence is real and is recorded in
[known failures](known-failures.md): a scheduling run performed with the producer is
not verifiable by re-execution today, and the seam is C8's registry.

Scope boundary held: no schema version changed anywhere, no new record type was
introduced, and no existing document gained or lost a field. `RunRecord`,
`SearchRecord`, `Model` and `optimizer verify` are untouched apart from the
verification refusal above, which is why the committed C4 example record still
re-executes and verifies inside the gate.

What is deliberately not claimed: no performance, runtime or solution-quality
result. Proven optimality is asserted only where exhaustive enumeration is the
oracle; a node-limited run over `ta001` is asserted to report its limit rather than
an optimum, and its incumbent is asserted feasible through the recurrence. No
best-known bound is committed, because a committed bound is an acceptance threshold.
The positional encoding's weak relaxation and the suboptimality of permutation
schedules beyond three machines are both recorded in
[known failures](known-failures.md).

Follow-up: C6 (heterogeneous backend and GPU feasibility) now has its dependencies
met, and C8 (registry, SDK and comparative runner) remains unblocked. Both need
their specifications written before any public API.

## C5 Flow-Shop Scheduling Specification (2026-09-11)

Objective: write and accept the C5 contract before any public scheduling API
exists, as required by AGENTS.md, CONTRIBUTING.md and the Stage 3 scope. No C5
behavior is implemented by this change.

Status: complete; SPEC-0008 and ADR-0007 are accepted and the project records that
reference C5 are synchronized.

Acceptance gate: the specification uses numbered observable MUST/MUST NOT
requirements with an acceptance-test mapping, states its exclusions, and passes
documentation and link validation; `bash tools/check.sh` continues to pass with
native acceptance covered and unchanged test counts, because no behavior changes.
Resource budget: CPU only, four Cargo workers, no GPU workloads.

Evidence (2026-09-11): the complete `bash tools/check.sh` gate passed with the
pinned HiGHS 1.11.0 library linked and **zero skip messages**, exit 0 and no
native-uncovered warning. Rust tests remain 159 and Python tests remain 39, which
is the expected result for a contract with no behavior: had either count moved,
this change would have been doing something it claims not to. Documentation rose
from 46 to 48 pages, SPEC-0008 and ADR-0007, with internal links and anchors
validated. The RustSec advisory fetch failed and recovered through the cached
database, the condition already recorded in [known failures](known-failures.md).
No checks were waived.

The diff is documentation plus one doc comment. `Cargo.lock`, `Cargo.toml`,
`schemas/`, `tools/` and `examples/` are untouched, and the only change under
`crates/` replaces the stale placeholder comment in optimizer-schedule that claimed
its specification was unassigned. No CHANGELOG.md entry accompanies this change:
the changelog records user-visible changes, and an accepted contract with zero
behavior is not one, matching the C2 specification commit. C5 enters the changelog
when its behavior ships.

Three claims in these documents were verified before being written down rather than
reasoned about, because each is the kind a later implementation could get quietly
wrong. Taillard's generator, reimplemented from the OR-Library transcription of the
1993 EJOR paper, reproduces his published ta001 matrix exactly from seed 873654221.
The positional encoding's optimum equals the makespan recurrence for a fixed
permutation, and its minimum over all permutations equals brute-force enumeration,
over 300 randomly generated instances. And permutation schedules are genuinely
suboptimal for the general flow shop beyond three machines: on a 3-job, 4-machine
instance the best permutation schedule costs 50 while the best general schedule
costs 47, which is why SPEC-0008 states the permutation restriction is part of the
problem rather than an approximation. The exhaustive-oracle bound was also measured:
enumerating 8 jobs is 40,320 permutations in roughly 130 ms, so the fixed grid in
the acceptance tests is affordable at n ≤ 8.

Resolved while writing: the first gate run failed rustdoc with an unresolved
intra-doc link, because the new module comment linked to `optimizer_core` while
optimizer-schedule still declares no dependencies. Adding that dependency edge
belongs to the implementation commit, not to a spec-only change, so the comment now
uses plain backticks. Worth recording because the failure was the workspace's
warnings-as-errors rustdoc correctly catching a documentation claim that referenced
something not yet in scope.

Noted and not changed: `state/backlog.yaml` retains one `status: ready`, which is
now C5's own and is correct. The benchmark protocol gained a paragraph stating when
a generated suite satisfies its freezing rule without download tooling, because the
rule as written required download tooling and ADR-0007 deliberately takes the other
route; leaving the two in apparent conflict would have made the protocol read as
overridden rather than extended.

Follow-up: C5 implementation is now dependency-ready under SPEC-0008. It requires
the instance document and its strict parser, the recurrence evaluator kept
independent of the encoding, the Lehmer generator with the pinned published seeds,
the positional adapter, the NEH and insertion producers in their own crate so the
independence evidence comes from the workspace build, a CLI surface, the frozen
manifest with committed instances and checksums, and the exhaustive permutation
grid that is the slice's load-bearing assertion.

Expected changes: docs/specifications/SPEC-0008-flow-shop.md,
docs/decisions/ADR-0007-flow-shop-encoding.md, state/backlog.yaml,
docs/benchmarks/protocol.md, implementation-plan.md, docs/architecture/overview.md,
docs/architecture/testing.md, README.md, wiki/status.md, AGENTS.md, the stale
placeholder doc comment in optimizer-schedule, and this record.

Two decisions are settled before implementation because both are the kind a later
implementation could get quietly wrong, and both were verified rather than
assumed.

The positional encoding is exactly linear. Makespan is not linear in a raw
permutation, but the positional formulation with binary job-position assignment
and continuous completion times needs no big-M constant. Checked over 300 random
instances: the encoded optimum for a fixed permutation equals the makespan
recurrence, and the minimum over all permutations equals brute-force enumeration.
The consequence is that C5 reuses `Model`, `Model::evaluate`,
`optimizer_solver::search`, `RunRecord` and `optimizer verify` unchanged, with no
new record type and no schema version bump.

The frozen Taillard subset is generated from published seeds rather than
downloaded. Taillard's documented Lehmer generator reproduces his published ta001
matrix exactly from seed 873654221, checked against the OR-Library transcription
of the EJOR paper. The canonical instance host timed out from this environment, so
generating from pinned seeds removes a network dependency from the gate instead of
adding one. `schemas/benchmark-manifest-v1.schema.json` already carries the shape
this needs: `instances[].generator` accepts a name, seed and parameters, so no
schema change is required.

What C5 must not claim: the positional encoding's LP relaxation is weak and a
20x5 Taillard instance is 400 binaries, so the executive will not prove optimality
at that size. Proven-optimal assertions are therefore confined to tiny instances
where exhaustive permutation enumeration is the independent oracle, and the frozen
subset carries feasibility, determinism and validated-incumbent assertions only.
Best-known upper bounds are deliberately not committed, because recording one
would create an acceptance threshold that the benchmark protocol says requires its
own ADR and experiment record.

Also in scope: `state/backlog.yaml` still names C4 as the current and next-ready
milestone and marks it `ready` while every other record in the repository says C4
is complete. It is the only file carrying that staleness. The benchmark protocol's
planned-suites table also still dates the two flow-shop suites in the retired
M-numbering.

## Local C4 Integration (2026-09-11)

Objective: verify the feat/run-surface branch from a clean checkout, integrate it
into local main, and delete the feature branch after confirming its commits are
retained.

Status: complete; clean-checkout verification, fast-forward integration and
feature-branch cleanup finished.

Acceptance gate: the complete gate passes in an independent clone with nothing
prebuilt; fast-forward integration preserves the reviewed tip 6725d93; the feature
branch is deleted and the worktree is clean. Resource budget: CPU only, no GPU
workloads.

Evidence (2026-09-11): the branch was cloned to /tmp/c4-final with
`--no-hardlinks` and no `target/` directory present, and `bash tools/check.sh`
passed there in 1 minute 56 seconds with zero skip messages. That run built the
pinned HiGHS 1.11.0 library from the checksum-verified upstream archive inside the
clone, ran 159 Rust and 39 Python tests, re-executed the committed run record
against the freshly built binary, validated 46 documentation pages, and passed
cargo-deny, artifact validation and bootstrap smoke.

Two stale claims were found and fixed before integration rather than carried onto
main. AGENTS.md still stated that C3 was the current scope and had no accepted
specification; it is the first file an agent reads, so a stale scope there
misdirects work rather than merely aging. And the three review markers named
692e19f, the parent the documents were written against, rather than the
implementing revision whose content was reviewed.

main was fast-forwarded from 692e19f to 6725d93 without conflicts or history
rewriting, so the integrated tree is byte-identical to the verified revision.
`git merge-base --is-ancestor` confirmed the reviewed tip is retained, and
`git branch -d` removed the fully merged feat/run-surface branch.

No remote refs were changed. main is now 5 commits ahead of origin/main and
remains unpushed pending separate authorization.

Follow-up: C5, the flow-shop scheduling vertical slice, is dependency-ready.
Write its specification before introducing any public scheduling API. C8, the
local registry, SDK and comparative experiment runner, is also unblocked; the SDK
needs an ADR amending ADR-0003 before any binding code.

## C4 Follow-up: Gated Re-execution and Engine Diagnostics (2026-09-11)

Objective: close three gaps found reviewing the C4 slice — a gate that never
re-executed a committed record, a divergence that could not distinguish a changed
engine from a wrong result, and a non-native build recording a backend version it
never called.

Status: complete; the full gate passes with native acceptance covered, and the
non-native configuration passes separately.

Acceptance gate: the committed example record re-executes against the current
build inside `bash tools/check.sh`, with both refusal directions asserted there
too; a record naming a different revision or compiler still verifies while
reporting the difference; a divergence carries that difference as a note without
changing its exit code; a build linking no native library records `unavailable`
rather than the pinned version, shown by a test that fails when the old code is
reinstated. Resource budget: CPU only, no GPU workloads.

Scope boundary: consulting engine identity as an *explanation* is within
SPEC-0005 as accepted, because requirement 11 fixes the ten compared fields and
requirement 13 forbids strengthening a claim; neither constrains diagnostic text.
Deciding that a version mismatch makes divergence *tolerable* would change the
meaning of agreement, which SPEC-0005's compatibility section says requires a new
record version and an ADR. That remains open and is recorded, not implemented.

Evidence (2026-09-11): the complete gate passed with the pinned library linked and
zero skip messages. Rust tests rose from 156 to 159: two environment-difference
contracts in optimizer-experiment and one CLI contract asserting the diagnostic
does not decide agreement. Python tests remain 39 and documentation 46 pages. The
new `tools/verify_committed_record.py` step reports
`committed run record re-executed and verified: passed`.

`AI_OPTIMIZER_SKIP_NATIVE=1 bash tools/check.sh` also passed with all 159 tests,
still printing its uncovered-acceptance warning, and correctly skipping the
committed-record step because a build with no library cannot solve at all.

The backend-version fix is verified by reinstating the defect rather than by
assertion alone: with `PINNED_VERSION` restored on the pre-cancelled path, the
non-native test fails at backend.rs:172; with the fix, it passes. The same test
runs in both configurations, so the native path is covered by the same assertion.
`interrupted_record` was the reachable path, because a pre-cancelled solve returns
a record without touching the library.

Why the gate step exists: every Rust re-execution test produces its record moments
earlier in the same process against the same binary, so none of them exercised the
property SPEC-0005 actually claims, that a record outlives its author. The gate now
re-runs a record committed at an earlier revision, and asserts the fingerprint
refusal and a counter divergence there as well, so the passing case is not the
only thing checked.

Noted: the example record's own provenance differs from any current checkout by
construction, since it carries the all-zero revision. That made it the natural
fixture for the diagnostic — verifying it now reports `environment_differs: true`
while still agreeing and exiting 0, which is exactly the separation between
explanation and decision that this change is about.

## C4 Agent-Independent Run Surface (2026-09-11)

Objective: implement the first C4 slice under a new SPEC-0005: expose the C2
executive and C3 extension host through the CLI, wrap each search in a
provenance-bearing run record, and add a verification command that re-runs a
search from its record alone and fails on disagreement.

Status: complete; the specification preceded the implementation, and the full
gate passes with native acceptance covered.

Acceptance gate: a search performed through the CLI writes a schema-valid run
record carrying source revision, dirty state, hardware, toolchain, backend
identity and version, the canonical model fingerprint and hashed inputs; that
record is re-executable by `optimizer verify` using only its embedded
configuration and the model it names; verification detects a mutated outcome,
objective, dual bound, forfeiture flag and each node counter individually, and
rejects a model whose fingerprint changed while its `model_id` did not;
elapsed time alone never fails verification; and `bash tools/check.sh` passes
with native acceptance covered. Resource budget: CPU only, four Cargo workers,
no GPU workloads.

Scope boundary, decided before implementation: the backlog's C4 line bundles
four deliverables and CONTRIBUTING.md mandates one complete vertical slice. This
slice delivers the CLI run surface and pinned reproducible runs. The local
registry and the Python SDK are deferred to their own specifications and gates
and are recorded in [known failures](known-failures.md) rather than dropped
silently. The SDK deferral has a technical basis: pyo3 expands to unsafe code,
the workspace forbids it, and ADR-0003 permits unsafe only inside
optimizer-highs, so an SDK needs an amending decision record.

Expected changes: new SPEC-0005 and ADR-0006; `crates/optimizer-experiment`
gains its first types and dependencies; new `schemas/run-record-v1.schema.json`
and `schemas/search-record-v2.schema.json`; `crates/optimizer-cli` gains
`search` and `verify` over new optimizer-solver and optimizer-experiment
dependencies; new tests in optimizer-cli, optimizer-experiment and
tests/integration; `examples/run-record-v1.json`;
`tools/validate_artifacts.py`; README.md, CHANGELOG.md,
docs/architecture/{overview,testing}.md, a new run-and-verify tutorial,
docs/operations/build.md, wiki/{status,glossary}.md, schemas/README.md,
cuda/schedule_eval/README.md, implementation-plan.md, state/backlog.yaml,
state/known-failures.md and this record.

Evidence (2026-09-11): the complete `bash tools/check.sh` gate passed with the
pinned HiGHS 1.11.0 library built and linked, with **zero skip messages**, in 20
seconds on a warm build directory: format, warnings-as-errors Clippy over all
targets, 156 Rust tests, workspace build, warnings-as-errors rustdoc, cargo-deny
(advisories, bans, licenses, sources all ok), artifact validation, 39 Python
tests, 46-page documentation and link validation, and bootstrap smoke. No checks
were waived.

Rust tests rose from 132 to 156: 11 run surface CLI contracts in optimizer-cli,
11 run record contracts in optimizer-experiment, and 2 SHA-256 unit tests.
Python tests rose from 20 to 39: 12 run record and search record schema
contracts plus 2 checksum-agreement tests, counted with subtests as unittest
reports them. Documentation pages rose from 43 to 46: SPEC-0005, ADR-0006 and
the run-and-verify tutorial.

Cargo.lock changed only by adding local dependency edges: optimizer-cli on
optimizer-experiment and optimizer-solver, and optimizer-experiment on
optimizer-core, optimizer-solver, serde and serde_json. No external package
version changed, and no new external dependency was introduced.

Reproducibility evidence, stated as what was actually checked rather than as a
property claimed in prose:

- `optimizer search` over examples/model-v1.json reported
  `outcome: proven_optimal`, `objective: 2.5`, `dual_bound: 2.5`, `forfeited:
  false` and exit 0, matching the C1 solve of the same model exactly. The record
  carried a 40-hex revision, the model fingerprint `fnv1a64:cc63f58b64d1c205`,
  and a SHA-256 for each of the two input documents.
- `optimizer verify` on that record re-ran the search and agreed, exit 0, naming
  all ten compared fields in its verdict.
- Verification was shown to be able to fail, in both directions it must. A model
  whose objective coefficient changed from 2.0 to 2.5 while keeping
  `model_id: tiny-mixed` was refused before any search ran:
  `document: model fingerprint mismatch`, exit 2. A record whose objective was
  edited to 1.5 was refused after re-running:
  `divergence: numerical: objective: recorded 1.5, reproduced 2.5`, exit 2.
- Each of the ten compared fields is asserted to fail when it alone is mutated,
  and the list of mutated field names is asserted equal to
  `RunRecord::compared_fields()`, so a field cannot be dropped from the
  comparison without a test failing.
- A record differing only in `elapsed_ms` by 987 seconds still verified with exit
  0, which fixes elapsed time as diagnostic rather than contractual.
- A node-limited search wrote its record, reported `outcome: node_limit` and exit
  1, and that record verified as still limited. A forfeited search that verifies
  is asserted to remain forfeited and to fail `proves_completion`.

Why the SHA-256 is implemented rather than taken from a crate: `sha2` and its
dependencies would add six external packages under `deny.toml`'s
`multiple-versions = "deny"` policy for one well-specified function. It is
implemented in safe Rust and checked against the FIPS 180-4 published vectors,
including the three padding edge cases at 55, 56 and 64 bytes and the
one-million-character vector, then independently against Python's `hashlib` over
the committed example documents and over a freshly generated record. Agreement
between the two implementations is verified rather than assumed.

Both normative authorities accept the same documents. The new schemas give C2 and
C3 records their first schema coverage, and `RunRecord::from_json` validates the
embedded search record's version on the parse path, so the divergence that
produced commit 6516a6f cannot recur here.

Resolved during implementation: an early assertion that a record with absent
measurements contains no `null` at all was wrong and was narrowed. Search
configuration serializes an absent budget as an explicit `null` meaning
unlimited, which is SPEC-0003's stated convention; the omit-rather-than-null rule
governs measurements. The test now asserts the three measurements are absent and
that `node_limit` is still explicitly null beside them.

Noted and not changed: the example record is generated from a real search and
then rewritten with the all-zero revision and example hardware, matching how
examples/experiment-result.json marks itself as a shape rather than evidence. Its
input hashes are the real ones and are verified against the committed files by
both the validator and a Python test.

Scope split recorded in the backlog: C4's original line covered four
deliverables. C4 is now the run surface and the registry, SDK and comparative
runner are backlog item C8, which depends on C4. C5, C6 and C7 keep their
dependency on C4, which remains meaningful because the run surface is what they
build on. The four deferrals are recorded in
[known failures](known-failures.md) with their blockers.

Clean-checkout verification, which is the stronger C1 and C3 standard and the
case that matters here because this change adds four crate dependency edges where
a stale lockfile or a missing manifest entry would otherwise hide behind a
populated `target/`: the branch was cloned to /tmp/c4-verify with
`--no-hardlinks` and no `target/` directory present, and
`bash tools/check.sh` passed there in 1 minute 36 seconds. That run built the
pinned HiGHS 1.11.0 library from the checksum-verified upstream archive inside
the clone and ran the same 156 Rust and 39 Python tests. The only lines matching
"skip" were CMake's own `Check for working CXX compiler - skipped` probes, not
test skips, so native acceptance was genuinely covered rather than inherited from
a warm build directory.

On the clean committed tree the run surface produces evidence-grade provenance:
`optimizer search` recorded revision c0eac20 with `dirty: false`, and
`optimizer verify` reported `agreement: true` with `evidence: true` and exit 0.
The dirty mid-implementation runs reported `evidence: false`, which is the
requirement 5 rule working rather than a defect.

No remote refs were changed and nothing was pushed; main remains unpushed pending
separate authorization. The branch feat/run-surface holds two commits, 8775da1
specifying the surface and c0eac20 implementing it.

## Local C3 Integration (2026-09-09)

Objective: verify the reviewed feat/extension-runtime branch from a clean
checkout, integrate it into local main, and delete the feature branch after
confirming its commits are retained.

Status: complete; clean-checkout verification, fast-forward integration and
feature-branch cleanup finished.

Acceptance gate: the complete gate passes in an independent clone with nothing
prebuilt; fast-forward integration preserves the reviewed tip 6516a6f; the
feature branch is deleted and the worktree is clean. Resource budget: CPU only,
four Cargo workers, no GPU workloads.

Evidence (2026-09-09): the branch was cloned to /tmp/c3-verify with no `target/`
directory present, and `bash tools/check.sh` passed there in 1 minute 44 seconds
with **zero skip messages**, so native acceptance was genuinely covered rather
than inherited from a warm build directory. That run built the pinned HiGHS
1.11.0 library from the checksum-verified upstream archive inside the clone,
producing both `libhighs.a` (10.2 MB) and the standalone reference executable
(5.0 MB). It ran 132 Rust tests and 20 Python tests, validated 43 documentation
pages, and passed cargo-deny, artifact validation and bootstrap smoke.

The clean clone also solved examples/model-v1.json to `termination: optimal`,
`objective: 2.5`, `backend_version: 1.11.0` with an independently validated
feasible incumbent and exit 0, matching the workspace result exactly.

This clean-checkout pass is the acceptance evidence for the integration. It was
run because C3 adds two crates and a new dev-dependency edge, which is exactly
the case where a stale lockfile or a missing manifest entry hides behind a
populated `target/`. The C2 integration relied on its pre-integration gate pass
instead; this record restores the stronger C1 standard.

main was fast-forwarded from b934dbd to 6516a6f without conflicts or history
rewriting, so the integrated tree is byte-identical to the verified revision.
`git merge-base --is-ancestor` confirmed the reviewed tip is retained on main,
`git rev-parse` confirmed main is exactly the verified revision, and
`git branch -d` removed the fully merged feat/extension-runtime branch. The
worktree is clean and the bootstrap smoke was rerun on the integrated revision
for clean revision-bound provenance.

The RustSec advisory-database fetch failed in the clean clone and recovered
through the cached database, as recorded in [known failures](known-failures.md).
Bans, licenses and sources were checked normally. No checks were waived.

No remote refs were changed. main is now 3 commits ahead of origin/main and
remains unpushed pending separate authorization; the origin remote and its
outstanding protection settings are recorded in
[known failures](known-failures.md).

Follow-up: C4, the agent-independent SDK, CLI, experiment workspace and local
registry, is dependency-ready. Write its specification before introducing any
public SDK or registry API.

## C3 Review Follow-up: Test Provenance and Nested Versions (2026-09-09)

Objective: resolve three problems found reviewing the C3 commit — a history that
made four mandatory test repairs indistinguishable from weakened ones, a
replacement test helper that asserted on serializer whitespace, and Rust record
parsers laxer than the JSON Schemas about nested document versions.

Status: complete; the branch is three commits and the full gate passes with
native acceptance covered.

Acceptance gate: the test repair compiles and passes on its own at search
schema version 1, proving it is not a consequence of the version bump; the
repaired assertions are shown to fail when the helper is sabotaged, so none is
vacuous; a record with a wrong nested version is rejected by both
`from_json` and `tools/validate_artifacts.py`; and `bash tools/check.sh` passes
with native acceptance covered. Resource budget: CPU only, four Cargo workers,
no GPU workloads.

Expected changes: the branch history; `crates/optimizer-core/src/{lib,solve}.rs`;
`crates/optimizer-solver/src/search.rs`; contract tests in optimizer-core,
optimizer-solver and optimizer-extension-examples; SPEC-0002 requirement 11,
SPEC-0003 requirement 22, SPEC-0004 requirement 23 and their acceptance
mappings; CHANGELOG.md and this record.

Evidence (2026-09-09): the branch is `b934dbd` → `9a2eda5` (test repair) →
`a85da69` (C3) → this commit. `git diff c3-pre-split a85da69` touches only the
test helper, confirming the split preserved the reviewed C3 content byte for
byte elsewhere; the pre-split tip is retained as tag `c3-pre-split`. The repair
commit's 22 contracts pass at version 1 with no extension field present, which
is what establishes that the repair was independent of the feature rather than
produced by it. Sabotaging `retarget_version` to a no-op makes both version
tests fail, so neither is vacuous.

The complete `bash tools/check.sh` gate passed with the native library built and
linked, with **zero skip messages**. Rust tests rose from 130 to 132: one nested
version contract in optimizer-core and one in optimizer-solver, plus extension
document coverage folded into the existing round-trip test. Cargo.lock changed
only by adding a `serde_json` dev-dependency edge for
optimizer-extension-examples; no external package version changed.

Why the parser change needed no ADR: `schemas/solve-record-v1.schema.json`
already pins the nested candidate's `schema_version` to `const 1` and pins
`options` by `$ref`, and those schemas are normative under SPEC-0007. The Rust
parsers checked only their own top-level version, so the two enforcement paths
disagreed and `tools/validate_artifacts.py` rejected documents the Rust parser
accepted. This change brings code into line with an accepted contract rather
than deciding anything new, and it is strictly narrowing: no document valid
under both paths becomes invalid. Verified by parsing one fixture with a wrong
nested version through both paths and confirming both reject it.

`Candidate::canonical` is deliberately not called on the parse path. It also
sorts and range-checks values, and parsing a record must reject a wrong version
without silently rewriting the document it was handed.

Resolved during implementation: the acceptance suite needed `serde_json` as a
dev-dependency to mutate a parsed document by field path. It is test-only, so
the examples crate's runtime dependencies remain optimizer-core and
optimizer-extension alone, and the independence evidence is unaffected.

Noted and not changed: `crates/optimizer-core/tests/solve.rs` still replaces
every `"schema_version": 1` occurrence in one assertion, which passes only
because the top-level check fires first. It is not wrong today and its
assertion is the top-level rule, so it is left alone; the new nested-version
contract beside it covers what the replacement cannot distinguish.

Follow-up: C4, the agent-independent SDK, CLI, experiment workspace and local
registry, is dependency-ready. Write its specification before introducing any
public SDK or registry API.

## C3 Extension Runtime and Authority Model (2026-09-09)

Objective: implement C3 under a new SPEC-0004: an extension runtime with a
declared authority model, candidate producers and search advisers, whose actions
the core validates and whose failures are recorded rather than absorbed.

Status: complete; the specification preceded the implementation, and the full
gate passes with native acceptance covered.

Acceptance gate: independently authored extensions build and run against the
published APIs with no engine-internal change; invalid candidates, invalid
advice, incompatible versions, panics and budget abuse each produce a typed
record entry; the proven optimum and the proof claim are identical with and
without extensions, including adversarial ones; and `bash tools/check.sh` passes
with native acceptance covered. Resource budget: CPU only, four Cargo workers,
no GPU workloads.

Expected changes: new SPEC-0004 and ADR-0005; new crates optimizer-extension and
optimizer-extension-examples; optimizer-solver contracts, executive and hooks;
`SEARCH_SCHEMA_VERSION` 1 to 2; the C2 search and native executive tests;
SPEC-0003 compatibility and exclusion clauses; implementation-plan.md, README.md,
docs/architecture/{overview,testing}.md, wiki/{status,glossary}.md, CHANGELOG.md,
state/backlog.yaml, state/known-failures.md and this record.

Evidence (2026-09-09): the complete `bash tools/check.sh` gate passed with the
native library built and linked, with **zero skip messages**: format,
warnings-as-errors Clippy, 130 Rust tests, workspace build, warnings-as-errors
rustdoc, cargo-deny (advisories/bans/licenses/sources), artifact validation, 20
Python tests, 43-page documentation/link validation and bootstrap smoke. Rust
tests rose from 84 to 130: 27 new extension runtime contracts, 18 new
independent-extension acceptance contracts, and 1 new native end-to-end
contract. No checks were waived.

The RustSec advisory-database fetch failed on the final run and recovered
through the cached database, as recorded in
[known failures](known-failures.md). Bans, licenses and sources are offline and
were checked normally; the advisory check ran against the cache rather than a
fresh fetch.

Cargo.lock changed only by adding local dependency edges for
optimizer-extension (optimizer-core, serde, serde_json),
optimizer-extension-examples (optimizer-core, optimizer-extension, and
optimizer-solver as a dev-dependency), the optimizer-solver dependency on
optimizer-extension, and optimizer-highs dev-dependencies on both new crates.
No external package version changed.

Correctness evidence, stated as what was actually checked:

- Three honest extensions and three hostile ones covering 17 distinct
  misbehavior modes (7 bad proposals, 4 bad actions, 6 unadmittable
  declarations) live in optimizer-extension-examples, which depends on the
  published extension and core APIs and takes optimizer-solver only as a
  dev-dependency. That the
  workspace builds is the evidence that a third-party extension needs no
  engine-internal change; it is not an assertion in prose.
- Over a fixed 25-model grid covering both senses, integer and binary domains,
  three capacities, two coefficient settings and a proven-infeasible case, every
  hostile extension leaves the outcome, the
  proven optimum, the dual bound, the forfeiture state and both prune counters
  identical to the extension-free run, which itself agrees with brute-force
  enumeration of the whole assignment space. These comparisons use unlimited
  node and time budgets deliberately: a hostile adviser spending a node budget
  on unpromising nodes legitimately changes which outcome a *budgeted* search
  reaches, so a budgeted assertion would be flaky by design rather than a real
  correctness check.
- An empty extension policy reproduces the extension-free record exactly, apart
  from measured elapsed time. That is the direct check that C3 did not perturb
  C2, and all 22 C2 contracts still pass unchanged in substance.
- Refusals are typed and recorded: infeasible, out-of-bounds, wrong-model,
  incomplete and nonfinite candidates; advice naming a nonexistent node, an
  unknown variable or an integral variable; both directions of host-contract
  mismatch; a refused transformation category; an unclaimed problem class;
  contained panics in `propose`, `advise` and even `declare`; and exhausted
  invocation and proposal budgets. A refused extension is never invoked at all,
  which is asserted against a call counter the extension itself maintains.
- A producer's claimed objective is never read. The out-of-bounds producer
  offers a candidate with an enormous objective and the record still reports the
  true optimum from independent recomputation.
- Recorded diagnostics stay bounded: 10,000 distinct rejections leave the
  counter exact at 10,000 and the retained messages capped at 8.
- The native end-to-end test drives the real executive over pinned HiGHS with a
  lying producer, a ghost-node adviser and a panicking adviser registered
  simultaneously, and still proves the optimum independent enumeration finds.

Resolved during implementation:

- The first acceptance run showed a search adviser being consulted for a
  continuous model, which requirement 20 forbids. Root cause: the node-selection
  hook ran whenever the frontier was non-empty, including when it held exactly
  one node and there was no choice to make. Fixed by not consulting an adviser
  for a decision with one possible answer, and recorded as SPEC-0004
  requirement 9a rather than patched silently. Consulting there could only
  manufacture rejections describing the hook rather than the extension.
- Three acceptance tests initially asserted against models whose LP relaxations
  happen to be integral, so no branching occurred and no adviser was ever
  consulted; they were passing or failing for reasons unrelated to their names.
  They now use a model with a genuinely fractional relaxation and assert
  `nodes_explored > 1` first, so a future change that removes the branching
  cannot make them vacuous.
- Three C2 record tests needed repair rather than renumbering. Two mutated "the
  first `schema_version` in the JSON", which at version 2 is the nested
  candidate's or is absent entirely, so they would have parsed successfully and
  panicked on `unwrap_err`. A third hand-wrote a complete configuration object
  plus an unknown field; with a new required field it would have been rejected
  for the *missing* field while still passing, silently ceasing to test
  unknown-field rejection. All three now target the document's own version or
  build their base from a serialized valid configuration.

Deferred and recorded rather than hidden: the extension host is in-process, so
containment covers panics but not a process abort, stack exhaustion or a memory
fault, and no per-extension memory budget is enforced. Process isolation and the
versioned C boundary for dynamically loaded native components are specified as
deferred and need their own decision record, because a second unsafe boundary
would amend ADR-0003. No CLI subcommand exposes extensions yet, no JSON Schema
covers search or extension records, and no performance claim is made: C3
establishes safety only, and whether advisers improve search is C7's question.

Follow-up: C4, the agent-independent SDK, CLI, experiment workspace and local
registry, is dependency-ready. Write its specification before introducing any
public SDK or registry API.

Contract decisions worth recording, because they are the ones a later
implementation could get quietly wrong:

- No extension path may reach forfeiture, a search-loop break, or an `Err`
  return from `search`. An adversarial extension must not be able to deny a
  proof the engine would otherwise complete. C2 forfeits when a *backend*
  misbehaves because its bounds become untrustworthy; a bad extension candidate
  implies nothing about bounds, so it is a recorded rejection and a disable.
- A proposed candidate is validated by `Model::evaluate` against the original
  model, and the record's objective is the recomputed one. A producer's claimed
  objective is never read.
- An advised branching variable must lie in the recomputed fractional set. This
  is a termination requirement, not a preference: branching on an integral
  variable yields two children that do not tighten the box, which is the same
  hazard SPEC-0003 requirement 12a exists to prevent.
- Extension budgets are counted in invocations and proposals, never wall clock,
  so the search path cannot depend on machine speed and requirement 21's replay
  guarantee survives.
- The `backend` category is not introduced: `optimizer_core::Backend` is already
  public and replaceable under SPEC-0002, and declaring the category only to
  refuse it would read as a regression of an accepted contract.
- `transformation` is refused at declaration time, so no code path for it
  exists until its validity has its own contract.

## Local C2 Integration (2026-09-09)

Objective: integrate the reviewed feat/solver-executive branch into local main
and delete the feature branch after confirming its commits are retained.

Status: complete; fast-forward integration and feature-branch cleanup finished.

Acceptance gate: fast-forward integration preserves the reviewed tip 5a74184;
the feature branch is deleted and the worktree is clean. Resource budget: CPU
only, no GPU workloads.

Evidence (2026-09-09): main fast-forwarded from c742064 to 5a74184 without
conflicts or history rewriting, so the integrated tree is byte-identical to the
revision whose complete gate pass is recorded below. `git merge-base
--is-ancestor` confirmed the reviewed tip is retained on main, and `git branch
-d` removed the fully merged feat/solver-executive branch. The worktree is clean
and the bootstrap smoke was rerun on the integrated revision for clean
provenance.

No remote refs were changed. main remains unpushed pending separate
authorization; the origin remote and its outstanding protection settings are
recorded in [known failures](known-failures.md).

## C2 Owned Solver Executive Implementation (2026-09-09)

Objective: implement C2 under SPEC-0003: an owned branch-and-bound executive in
optimizer-solver that consumes the C1 backend contract as a relaxation service
and owns proof completion.

Status: complete; executive, contract documents, node representation and
acceptance tests are in place and the full gate passes with native acceptance
covered.

Acceptance gate: exhaustive tiny-model search compared against independent
enumeration, termination semantics, budgets, cancellation, proof completion, and
`bash tools/check.sh`. CPU only, four Cargo workers, no GPU workloads.

Expected changes: optimizer-solver runtime and tests, an end-to-end test in
optimizer-highs, SPEC-0003 implementation/test links, project records, changelog
and this task record.

Evidence (2026-09-09): the complete `bash tools/check.sh` gate passed with the
native library built and linked, with **zero skip messages**: format,
warnings-as-errors Clippy, 84 Rust tests, workspace build, warnings-as-errors
rustdoc, cargo-deny (advisories/bans/licenses/sources, fetched successfully this
run without the cached-database fallback), artifact validation, 20 Python tests,
41-page documentation/link validation and bootstrap smoke. Rust tests rose from
58 to 84: 22 new search contracts and 4 new native end-to-end contracts. No
checks were waived.

Cargo.lock changed only by adding local dependency edges for optimizer-solver
(optimizer-core, serde, serde_json) and the optimizer-highs dev-dependency on
optimizer-solver. No external package version changed.

Correctness evidence, stated as what was actually checked:

- 192 tiny discrete models over a fixed coefficient, bound and row-limit grid,
  both objective senses, integer and binary domains, agree with brute-force
  enumeration of the entire assignment space on the proven optimum and on proven
  infeasibility. The grid is fixed with no randomness, so a failure reproduces.
- Every non-optimal relaxation termination (time, iteration and node limits,
  interruption, feasible-without-proof, numerical failure, backend failure,
  unsupported) forfeits the proof claim and prunes nothing by bound.
- The executive runs entirely on test backends, which is what demonstrates
  backend neutrality; the end-to-end test over pinned HiGHS lives in
  optimizer-highs so optimizer-solver keeps that guarantee. Both agree with
  independent enumeration.

Resolved during implementation:

- The first test run did not terminate. A backend that returns the same
  fractional solution regardless of node bounds caused the executive to
  regenerate an identical child forever. Root cause: the executive trusted the
  relaxation solution to lie inside the node it asked about. Fixed by checking
  every relaxation solution against its own node before branching, which makes
  termination independent of backend correctness. Recorded as SPEC-0003
  requirement 12a rather than fixed silently.
- A record test asserted no `null` anywhere in the serialized record. That
  conflated two rules: absent *measurements* are omitted, while an absent
  *budget* stays an explicit null meaning unlimited, matching the C1
  configuration convention. The assertion now targets measurements by name.

Deferred and recorded rather than hidden: checkpoint restart is specified in
shape and deliberately unimplemented; no CLI subcommand exposes search yet; no
performance claim is made and no comparison against another solver was run.
Cross-node basis reuse remains Stage 5 reoptimization work.

Follow-up: C3, the extension runtime and authority model, is dependency-ready.
Write its specification before introducing any public extension API.

## C2 Solver Executive Specification (2026-09-09)

Objective: write and accept the C2 contract before any owned search API exists,
as required by AGENTS.md and the Stage 2 entry condition. No C2 behavior is
implemented by this change.

Status: complete; SPEC-0003 and ADR-0004 are accepted and the project records
that reference C2 are synchronized.

Acceptance gate: the specification uses numbered observable MUST/MUST NOT
requirements with an acceptance-test mapping, states its exclusions, and passes
documentation/link validation; `bash tools/check.sh` continues to pass with
native acceptance covered and unchanged test counts, because no behavior changed.
Resource budget: CPU only, four Cargo workers, no GPU workloads.

Expected changes: docs/specifications/SPEC-0003-solver-executive.md,
docs/decisions/ADR-0004-owned-search.md, state/backlog.yaml, README.md,
implementation-plan.md, docs/architecture/overview.md, wiki/status.md, the two
stale placeholder doc comments in optimizer-solver and optimizer-schedule, and
this record.

Contract decisions worth recording, because they are the ones a later
implementation could get quietly wrong:

- A relaxation objective is admitted as a dual bound only when that relaxation
  reported `Termination::Optimal`. Any limit, interruption or failure leaves the
  node bound unavailable, forbids pruning that node by bound, and permanently
  forfeits the search's proof claim, recorded as `forfeited` in the record. This
  is what stops a timeout inside a child solve from silently discarding an
  optimal solution.
- `SearchOutcome` is a new type rather than a reuse of `Termination`. The two
  express different claims: one relaxation solve versus an exhausted node tree.
- The executive consumes the C1 `Backend` trait and must not depend on
  optimizer-highs, so the pruning and forfeiture rules are testable against a
  stub backend without the native library.
- `Tolerances.integrality` governs both incumbent acceptance and the decision to
  branch, so the two cannot disagree.
- Checkpoints are specified in shape only; restart is deliberately not part of C2
  and needs its own acceptance evidence.

Numbering: no spec-numbering convention exists in the repository, so SPEC-0003
and ADR-0004 take the next free sequential numbers. Two placeholder doc comments
referenced the retired M0-M6 scheme and dangled at nonexistent specifications;
optimizer-schedule's stale "SPEC-0003" claim would have collided with this
specification and now names C5 with an unassigned number.

No CHANGELOG.md entry accompanies this change: the changelog records user-visible
changes, and an accepted contract with zero behavior is not one. C2 enters the
changelog when its behavior ships.

Follow-up: C2 implementation is now dependency-ready under SPEC-0003. It requires
a stub-backend test crate for the bound-validity and forfeiture rules plus
exhaustive tiny-model comparison against independent enumeration.

## Local C1 Integration (2026-09-09)

Objective: verify the reviewed feat/highs-backend branch from a clean checkout,
integrate it into local main, and delete the feature branch after confirming its
commits are retained.

Status: complete; clean-checkout verification, fast-forward integration and
feature-branch cleanup finished.

Acceptance gate: the complete gate passes in an independent clone with nothing
prebuilt; fast-forward integration preserves the reviewed tip c8bb6f3; the
feature branch is deleted and the worktree is clean. Resource budget: CPU only,
four Cargo workers, no GPU workloads.

Evidence (2026-09-09): the branch was cloned to /tmp/c1-verify with no populated
target/native, and `bash tools/check.sh` passed there in 1 minute 43 seconds.
That run built the pinned HiGHS 1.11.0 library from the checksum-verified
upstream archive, produced both libhighs.a and the standalone executable, and ran
58 Rust and 20 Python tests with **zero skip messages**, so native acceptance was
genuinely covered rather than bypassed. The clean clone also solved
examples/model-v1.json to `termination: optimal`, `objective: 2.5`,
`backend_version: 1.11.0` with an independently validated feasible incumbent and
exit 0, and wrote a smoke record bound to revision c8bb6f3 with `dirty: false`.

This clean-checkout pass is the acceptance evidence for the integration. main was
fast-forwarded from 9b42b62 to c8bb6f3 without conflicts or history rewriting, so
the integrated tree is byte-identical to the verified revision.
`git merge-base --is-ancestor` confirmed the reviewed tip is retained on main, and
`git branch -d` removed the fully merged feat/highs-backend branch. No remote refs
were changed; main remains 9 commits ahead of origin/main and unpushed, pending a
separate authorization to push.

The advisory database fetch failed again during the clean-clone run and recovered
through the cached database, as recorded in
[known failures](known-failures.md). No checks were waived.

Follow-up: C2, the owned solver executive, is dependency-ready. Its specification
is now accepted as SPEC-0003; see the C2 record at the top of this file. No C2
behavior existed at the time of this integration.

## C1 Backend-Neutral Solve Contract and HiGHS Adapter (2026-09-09)

Objective: implement C1 under SPEC-0002: backend-neutral solve/session types,
HiGHS adapter boundary, strict solve configuration and structured records.

Status: complete; contract, native adapter, solve CLI, schemas and acceptance
tests are in place and the full gate passes with native acceptance covered.

Acceptance gate: core and adapter contract tests, strict CLI solve flow,
status/cancellation/limits/warm-start behavior, reproducible records, and
`bash tools/check.sh`. CPU-only; native HiGHS setup uses the pinned 1.11.0
source and at most four build workers.

Expected changes: optimizer-core, optimizer-highs, optimizer-cli, experiment
schemas, specifications, changelog, tests, and task state. No GPU workload.

Evidence (2026-09-09): the complete `bash tools/check.sh` gate passed with the
native library built and linked: format, warnings-as-errors Clippy, 58 Rust
tests, workspace build, warnings-as-errors rustdoc, cargo-deny
(advisories/bans/licenses/sources), artifact schema/provenance, 20 Python tests,
38-page documentation/link validation and bootstrap smoke. No checks were waived.

Native provisioning and FFI: `tools/setup_highs.sh` builds the pinned static CPU
library under `target/native/highs-1.11.0/install` from the checksum-verified
upstream archive. A hand-written private FFI module links it; no `highs-sys`
dependency is introduced. `Highs_version()` reports 1.11.0 and the compile-time
assertion confirms a 4-byte `HighsInt`, matching the pinned `HIGHSINT64=OFF`.

Differential acceptance: the standalone executable, built from the same source,
is driven as a separate process over generated LP files and agrees with the
adapter on status and objective for LP, objective-offset, equality, ranged, MILP
and infeasible cases. Disagreement fails the test rather than deferring to the
adapter. The reference is run in a sandbox directory with its log redirected, so
native output cannot litter the tree.

Correctness contracts verified: all 18 native model statuses map explicitly with
no catch-all arm; extracted candidates are re-validated through SPEC-0001 before
publication and a validation failure becomes a numerical failure rather than an
optimality claim; a pre-cancelled solve returns interrupted without creating
native state; limits and interruptions never satisfy `proves_completion`; binary
bounds intersect [0,1] regardless of declared bounds; coefficients below the
native small-matrix threshold are rejected instead of being silently dropped; a
basis is bound to a canonical-model fingerprint, so changed data under an
unchanged `model_id` is rejected.

Resolved review findings during implementation:

- The workspace `unsafe_code = "forbid"` made ADR-0003's native boundary
  unimplementable: `forbid` cannot be relaxed by an inner crate
  (`E0453 overruled by previous forbid`). optimizer-highs now declares its own
  `[lints.rust]` block with `unsafe_op_in_unsafe_fn` denied.
- `serde_json` serializes a nonfinite `f64` as `null`, which is indistinguishable
  from an absent field, so SPEC-0002's absent-not-null rule cannot rely on a
  serializer error. Records omit absent measurements and reject nonfinite ones
  explicitly as numerical failures.
- The stub adapter's pre-cancellation path required a provisioned library, which
  contradicted requirement 6. The check now precedes native dispatch and is
  answered identically with or without the library. Found by running the gate
  with the library deliberately absent.
- A no-op `.max()` in bound conversion and an unfulfilled lint expectation were
  caught by Clippy and removed.

Deferred and recorded rather than hidden: sanitizer runs over repeated native
lifecycles are not yet in the gate; presolve, scaling and reoptimization remain
Stage 5 work; owned search remains C2.

## Roadmap redesign (2026-09-09)

Objective: replace the narrow M0-M6 implementation sequence with the
architecture-driven C1-C7 capability roadmap in implementation-plan.md.

Status: complete; plan and backlog metadata synchronized.

Acceptance gate: roadmap is decision-complete, preserves M0/M1 evidence, keeps
HiGHS as the first replaceable backend, defines executive/extension/SDK/GPU
gates, and bash tools/check.sh reaches the required gate.

Evidence: implementation-plan.md, state/backlog.yaml, README.md, and CHANGELOG.md
now describe C1-C7 and the next dependency-ready task is C1. `git diff --check`
passes. `bash tools/check.sh` reaches preflight but cannot start Cargo because
the environment cannot create its sandbox namespace; no Rust checks were waived.

## M2 Backend Contract and Implementation (2026-09-09)

Objective: implement the approved M2-M6 plan sequentially, starting with the
HiGHS backend contract, safe lifecycle, validated solving and reproducible records.

Status: superseded; see the C1 record at the top of this file. The M2-M6 sequence
was replaced by the evidence-staged roadmap, and this objective was delivered as
C1 under the same SPEC-0002 and ADR-0003 contracts.

Acceptance gate: accepted SPEC-0002 and supporting ADR; standalone HiGHS
differential LP/MILP tests, explicit statuses, cancellation/limits, warm starts,
lifecycle sanitizers, structured records, and bash tools/check.sh. Inspect and
fix review findings before committing.

Expected changes: optimizer-highs, core solve contracts, CLI, experiment schemas,
native build/validation tooling, tests, specifications, ADRs and project state.
Resource budget: CPU only, at most four workers, bounded deterministic
tests and benchmark batches of at most 30 minutes. GPU work will use one shared
host GPU lease at a time. Existing M0/M1 defaults remain unchanged.

Follow-up order under the current roadmap: C2 owned executive, C3 extension
runtime, C4 SDK/registry, C5 flow shop, C6 GPU feasibility, C7 adaptive research.
No remote publication is included.

## Local M1 Integration (2026-09-08)

Objective: merge the reviewed feat/model-validation branch into local main and
delete the feature branch after confirming its commits are retained.

Status: complete; local integration and feature-branch cleanup finished.

Acceptance gate: fast-forward integration preserves reviewed commit 27b1b3a;
bash tools/check.sh passes on main; the merged feature branch is deleted and the
worktree is clean after recording evidence. Expected changes: local Git refs and
this task record. Resource budget: CPU only, four Cargo workers, no GPU workloads.

Evidence (2026-09-08): main fast-forwarded from 9e6dc86 to reviewed tip 27b1b3a
without conflicts or history rewriting. git merge-base --is-ancestor confirmed
the reviewed tip is retained on main, and git branch -d removed the fully merged
feat/model-validation branch. No remote refs were changed.

The unchanged runtime passed the complete acceptance gate before integration,
as recorded below. Two post-merge attempts passed format, Clippy, all 29 Rust
tests, workspace build and rustdoc, then stopped because the RustSec advisory
database could not be fetched. These attempts do not constitute a new full-gate
pass; the successful pre-integration gate remains the full acceptance evidence.
The only additional tracked change is this integration record, validated with
the documentation/link builder and git diff --check before committing.

## Repeated Branch Review (2026-09-08)

Objective: review the complete feature branch against main, fix any substantiated
findings, and repeat until the final review has no unresolved actionable findings.

Status: complete.

Acceptance gate: inspect every changed runtime path and the SPEC-0001/ADR-0002
contracts, verify relevant regression coverage, and run bash tools/check.sh.

Expected changes: this review record and any bounded fixes supported by reproduced
failures. Resource budget: CPU only, at most four Cargo workers, deterministic
tests, no GPU workloads. Review base: local main at 9e6dc86; starting HEAD: 58df6bb.

Current finding: model validate panics with exit 101 when a model/candidate path
contains non-UTF-8 bytes because main uses env::args. Preserve native paths with
args_os and report malformed non-path text as an argument error. Expected fix:
CLI parsing, Unix path/error regression tests, specification and release notes.
Follow-up finding: incomplete/unknown model commands returned bare usage without
the required argument category. Add a categorized dispatch error and regression.

Evidence (2026-09-08): both new regressions failed before their fixes and pass
afterward. Native model/candidate filenames retain their OS representation;
non-UTF-8 command, flag and tolerance text returns an argument error with exit 2.
Incomplete and unknown model commands now return the same error category.
Unix regressions cover real non-UTF-8 filenames, successful reports and missing
files. Specifications, tutorial, changelog and regression instructions agree.

The final complete bash tools/check.sh gate passed: format, warnings-as-errors
Clippy, 29 Rust tests, workspace build, rustdoc, cargo-deny, artifact validation,
8 Python tests, 36-page documentation/link validation and bootstrap smoke.
Temporary RustSec advisory-fetch failures recovered; no checks were waived.
Cargo preflight checks also passed for missing Cargo (exit 127 with a diagnostic)
and the rustup-only PATH fallback to the pinned Rust 1.93.1 toolchain.

Final review against local main at 9e6dc86534de2efa414205752ca58d7584976052
found no unresolved actionable findings. Coverage included strict JSON parsing,
canonical model construction, candidate coverage, arithmetic and tolerance
contracts, report output, CLI errors, dependencies, specifications and fixtures.
The existing independent dense oracle covers 18,522 evaluations and the f64
round-trip suite covers 968 values. Resource use remained CPU-only with four
Cargo workers; scope remains M1. Commit after acceptance, then rerun bootstrap
smoke to record the clean committed revision.

## M1 Review Contract Fixes (2026-09-08)

Objective: reject alternate JSON representations for all model/candidate input
types and return categorized CLI I/O errors when report output fails.

Status: complete.

Acceptance gate: regressions for positional records, object-wrapped enums,
and failed stdout writes; full bash tools/check.sh under SPEC-0001 and ADR-0002.

Expected changes: optimizer-core document parsing, optimizer-cli report output,
contract tests, minimized fixtures, specification clarifications, changelog,
and this task record. Resource budget: CPU only, four Cargo build workers,
bounded deterministic tests, no GPU workloads.

Evidence (2026-09-08): new regressions reproduced accepted alternate JSON forms
and exit 101 on failed stdout before their fixes. Public record types and tagged
bounds now reject positional arrays; domain/objective enums require strings.
Direct and nested parsing tests pass, preserving unknown/duplicate-field rejection
and f64 round trips. CLI tests verify categorized io errors and exit 2 for /dev/full
and closed pipes in structural and candidate modes. Output writes and flushes
are fallible; the specification clarifies that delivered bytes cannot be retracted.

The complete bash tools/check.sh gate passed: format, warnings-as-errors Clippy,
26 Rust tests, workspace build, rustdoc, cargo-deny, artifact validation, 8 Python
tests, 36-page documentation/link validation, and bootstrap smoke. No checks were
waived. Rust 1.93.1, four Cargo workers, and CPU-only simulations were used.
Minimized JSON fixtures and reproduction instructions are in tests/regression/.
Both review findings are resolved; no dependency or numerical-policy changes.

## Commit and Branch Review (2026-09-08)

Objective: validate and commit the pending acceptance-script diagnostic change,
then review the complete feature branch against local main in PR style.

Status: complete; committed as 4981aef and reviewed against local main.

Acceptance gate: run bash tools/check.sh before committing; inspect the complete
main-to-branch diff against SPEC-0001 and ADR-0002 and report actionable findings.

Expected changes: the pending tools/check.sh change and this task record.
Resource budget: CPU only, at most four Cargo build workers; no GPU workloads.

Evidence (2026-09-08): the complete bash tools/check.sh gate passed with Rust
1.93.1 and four Cargo workers: format, Clippy, 22 Rust tests, workspace build,
rustdoc, cargo-deny, artifact validation, 8 Python tests, 36-page documentation
build/link validation, and bootstrap smoke. No checks were waived. Review found
alternate JSON representations and panicking stdout writes, resolved by the M1
review contract fixes above. The comparison base was local main
at 9e6dc86534de2efa414205752ca58d7584976052 (also origin/main locally).

## Current diagnostic fix (2026-09-08)

Objective: make the acceptance gate locate the repository-pinned Rust toolchain and report executor failures clearly.

Status: complete.

Acceptance gate: shell syntax and toolchain preflight behavior pass; existing Rust gate remains unchanged after Cargo is resolved.

Evidence (2026-09-08): `bash -n tools/check.sh` passed. With Cargo absent, the gate exits 127 with an actionable diagnostic instead of an opaque `command not found`; with the pinned toolchain bin directory available, the existing Rust checks remain the executed gate.

Expected changes: tools/check.sh and this task record.

Resource budget: CPU only; no GPU workloads.


Objective: implement M1 core models, candidate validation, versioned JSON, and CLI.

Status: complete.

Acceptance gate: accepted SPEC-0001 and ADR-0002; independent property/exhaustive
model tests, serialization and numerical boundary tests, CLI contracts, and
the complete bash tools/check.sh gate. Commit locally after acceptance.

Expected changes: optimizer-core, optimizer-cli, model fixtures/examples,
specification and ADR, current scope/status documentation, changelog, task state.
Resource budget: CPU only, at most four Cargo build workers, bounded deterministic
tests; no GPU workloads. Existing smoke seeds and configuration remain unchanged.

Evidence (2026-09-08): accepted SPEC-0001 and ADR-0002 preceded implementation.
The complete bash tools/check.sh gate passed after the final runtime/test edits:
format, warnings-as-errors Clippy, 22 Rust tests, workspace build, warnings-as-errors
rustdoc, cargo-deny advisories/bans/licenses/sources, artifact schema/provenance,
8 Python artifact tests, 36-page documentation/link build, and bootstrap smoke.
No checks were waived. The 14 new Rust contracts include 18,522 independent dense
oracle evaluations, generated model ordering properties, 968 finite f64 values
round-tripped through both model and candidate JSON, numerical/domain boundaries,
edge-model fixtures, CLI exit/report behavior, and exact 16 MiB file boundaries.

Resolved regression: Serde internally tagged unit variants accepted an unknown
field on infinite bounds. Strict bound deserialization now rejects the minimized
fixture in tests/regression/infinite-bound-extra-field.json; its contract test passes.

Environment: Rust 1.93.1 and cargo-deny 0.19.0 under /tmp/ai-optimizer-cargo,
RUSTUP_HOME=/tmp/ai-optimizer-rustup, Python tooling /tmp/ai-optimizer-venv,
CARGO_BUILD_JOBS=4. Core contracts completed in 0.17 s and CLI model contracts in
0.78 s in the final gate. Work was CPU-only; lease tests used temporary locks and
simulated jobs. Cargo.lock only adds local core/CLI dependency edges; no external
package versions changed. Serde JSON's float_roundtrip feature preserves f64 input.

Provenance: the precommit gate's smoke honestly records a dirty working tree.
The local feature commit is followed by a smoke rerun for clean revision-bound
provenance at artifacts/bootstrap-smoke.json. This remains CLI startup evidence,
not solver or GPU performance. No push or hosting changes are part of M1.

Follow-up: M2 is dependency-ready. Write SPEC-0002-backend-contract.md before
implementing HiGHS lifecycle, status mapping, cancellation, limits and solve records.
No M2 behavior is implemented here.

## Previous Repository Synchronization

Objective: synchronize the project to https://github.com/liuyumou/OptForge.git.

Status: complete.

Acceptance gate: origin points to the requested repository; main is pushed with
upstream tracking; the remote main revision matches local HEAD; the worktree is
clean. Preserve existing history and validate updated documentation.

Expected changes: Git remote/tracking configuration and repository hosting/task
records. Resource budget: bounded CPU checks and Git operations; no GPU work.

Evidence: the original main history was pushed successfully and main now tracks
origin/main. The complete tools/check.sh gate passed, including 8 Rust tests,
8 artifact tests, dependency policy, documentation, and smoke validation. Hosting
records identify the remote. The synchronization includes this documentation
update; remote revision equality and clean worktree are checked after its push.

## M0 Bootstrap Evidence

Objective: implement M0 from implementation-plan.md.

Status: complete.

Acceptance gate: pinned Rust workspace builds; format, Clippy, tests, dependency
policy, rustdoc, documentation links/build, schemas, and benchmark smoke pass.
GPU discovery must report available UUIDs or an explicit unavailable state.
Simulated jobs must serialize and release ownership after cancellation or exit.

Expected changes: repository bootstrap, crates, tools, schemas, CI, documentation,
examples, benchmark fixtures, and task state. Preserve both original plans.

Resource budget: CPU-only builds and bounded tests; GPU discovery only, no kernels.
One developer, one bounded milestone. M1-M6 remain dependency-ordered backlog.

Evidence before initial commit: Rust workspace build, format, warnings-as-errors
Clippy, 8 Rust unit/integration tests, rustdoc, cargo-deny (advisories, bans,
licenses, sources), 8 Python artifact tests, schema/provenance validation, shell
syntax, and a 33-page documentation/link build passed. Discovery returned all
three expected physical GPU UUIDs without launching kernels.

Clean-checkout acceptance: the complete tools/check.sh gate passed on revision
a628c0c8605dd2434cdf7fd775fae85e96423a31 in an independent local clone at
/tmp/ai-optimizer-m0-verification. It rebuilt every crate and generated a validated
measured smoke record with dirty=false. No acceptance checks were waived.

Verified lease cases: competing-process timeout and serialization, normal release,
SIGINT while waiting, SIGTERM while holding, SIGKILL recovery, and interoperability
with the shell runner's flock primitive. All were CPU simulations. Inventory
reported two RTX 5090 devices and one RTX PRO 6000 by their expected UUIDs.

Artifacts: the clean-clone record is at
/tmp/ai-optimizer-m0-verification/artifacts/bootstrap-smoke.json. The workspace
runner can reproduce artifacts/bootstrap-smoke.json. Records measure CLI startup
only; no solver or GPU performance result is claimed.

Environment: Rust 1.93.1 and cargo-deny 0.19.0 were installed under
/tmp/ai-optimizer-cargo with RUSTUP_HOME=/tmp/ai-optimizer-rustup. Documentation
and schema tooling use /tmp/ai-optimizer-venv. Hosting workflows are configured
but were not run on GitHub; remote protection and GPU-runner provisioning remain
external setup, as documented in state/known-failures.md.

Follow-up: M1 is dependency-ready. Write SPEC-0001-model-and-validation.md, then
implement the original-model numerical authority boundary and its independent
property/exhaustive tests. No M1 behavior has been implemented as part of M0.

## Toolchain recovery (2026-09-09)

The pinned Rust toolchain was present under `/tmp/ai-optimizer-cargo` and
`/tmp/ai-optimizer-rustup` but absent from the default PATH. `tools/check.sh`
now discovers those locations and sets `RUSTUP_HOME` automatically, and the
search order is overridable through `AI_OPTIMIZER_CARGO_HOME` rather than being
hardcoded to one machine's layout.

Superseded detail: this record previously stated that the gate stopped at
artifact validation for a missing Python `jsonschema`. That diagnosis is stale.
`jsonschema` is present and artifact validation passes; the missing module was
`Markdown`, which `tools/requirements.txt` already pins. The gate now checks both
imports as a precondition, so this class of failure is reported in seconds rather
than after several minutes of compilation. C1 native HiGHS and solve CLI
implementation are now complete; see the C1 record at the top of this file.
