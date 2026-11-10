# External LP baseline: protocol and resource proposal

Status: GPUP-BASELINE-SPEC CPU contract complete; execution package proposed only.
Owner: experiment tooling and numerical backend.
Reviewed commit: 396bd0e2ea095f1d038dfa862bb31f29a61e0d68.
Normative contract: [SPEC-0022](../specifications/SPEC-0022-external-lp-baseline.md).
Machine proposal: [lp-external-baseline-proposal-v1.json](../../benchmarks/configs/lp-external-baseline-proposal-v1.json).
Design authority: [ADR-0047](../decisions/ADR-0047-certified-performance-roadmap.md).

The first comparison will establish how much time each solver spends delivering
an independently certified answer. It will not select a supported precision recipe.
The protocol fixes a development screening grid and admission sequence, while
keeping resource approval and actual execution separate. No solver runs, GPU
reservations or historical budget transfers were made for this specification.

## Configuration decisions

Use ten lanes on one pinned RTX PRO 6000 Blackwell Server Edition and four allowed
logical CPU IDs, selected in ascending order and frozen before execution. Set all
native thread controls to four, including BLAS/OpenMP where applicable; CPU affinity
bounds aggregate concurrency. Four CPUs accommodate the concurrent solvers, and
this is a new cohort, not a direct extension of historical one-CPU timings. If the
chosen device or required resource controls are unavailable, stop admission.

| Lane | Method and explicit choices | Purpose |
| --- | --- | --- |
| project-tuned-fp64 | Retained tuned CUDA PDHG, native FP64, original scaling/controller | Primary project reference |
| project-precision-fp64 | Same retained execution with explicit FP64 precision path | Expose precision-framework cost |
| highs-cpu | Pinned HiGHS 1.11.0, native LP defaults except declared resources/tolerances | CPU backend control required by SPEC-0013 |
| cuopt-pdlp-double | `method=1`, `pdlp_precision=1`, `pdlp_solver_mode=4`, presolve/crossover off | Forced GPU PDLP double control |
| cuopt-pdlp-mixed | Same, `pdlp_precision=2` | Vendor mixed-storage comparison |
| cuopt-pdlp-single | Same, `pdlp_precision=0` | Strict-quality single-precision coverage and cost |
| copt-cpu-pdlp | `LpMethod=6`, `GPUMode=0`, `Presolve=0`, `Crossover=0` | Forced CPU PDLP |
| copt-gpu-pdlp | Same, `GPUMode=1`, masked `GPUDevice=0` | Forced GPU PDLP; arithmetic remains opaque |
| cuopt-concurrent | `method=0`, PDLP double/Stable3, PSLP `presolve=2`, crossover on | Quality-adjusted portfolio row; record actual winner |
| copt-cpu-default | `LpMethod=-1`, `GPUMode=0`, `Presolve=-1`, `Scaling=-1`, `Crossover=1` | Quality-adjusted CPU portfolio row |

All native solve limits are 40 seconds in screening and 20 seconds in admission;
the outer supervisor limits below include additional extraction, certification
and cleanup time. Project and cuOpt work limit is 50000 updates/iterations where
supported; COPT has no matching hard PDLP work/seed control, so wall limit is the
common resource limit. Report native iteration units separately; do not equate
them to project physical updates or reject COPT after solving solely for exceeding
another algorithm's work count. Project/cuOpt seed is 17 where supported. HiGHS
uses the pinned backend's supported controls; native defaults and unsupported
controls must be captured during admission, not guessed from another solver.

cuOpt's six absolute/relative primal, dual and gap tolerances are explicitly 1e-9.
COPT uses `FeasTol=DualTol=1e-9`, plus `PDLPTol=1e-9` for PDLP. These settings
express intent, not numerical equivalence: the original-model checker remains
decisive. Concurrent barrier/simplex subsolver tolerances not exposed under the
same parameter names are recorded as defaults; the portfolio row may consequently
fail the strict checker. There is no hidden re-solve or stricter second attempt.
The proposal makes no lower-quality, FP16/BF16 Tensor or Gurobi lane.

Forced PDLP disables vendor presolve and crossover to isolate that algorithm's
path. Internal scaling and algorithm designs still differ, so the experiment is
not a claim of identical iterations. Portfolio rows explicitly permit presolve
and crossover and must be reported separately. cuOpt mixed is a documented matrix
storage/compute mode, not inferred Tensor execution. See the
[vendor settings reference](https://docs.nvidia.com/cuopt/user-guide/latest/convex-settings.html).

## Implementable adapter and checker path

The [API inspection receipt](data/baseline-spec-api-inspection-v1.json) binds the
local files inspected. cuOpt 26.10.0 provides `DataModel.set_csr_constraint_matrix`,
native row/variable lower and upper bounds, `set_maximize`, objective offset,
and solution getters for primal, dual, reduced costs, status and `get_solved_by`.
Use binary64 host arrays and native ranged rows. CSC-to-CSR permutation is provided
by the CPU contract tool; it performs no coefficient arithmetic. Exact API upload
and readback, objective sense and postsolve-sign behavior still require admission.

COPT 8.0.6 provides `loadMatrix`, `setObjSense`, `setObjConst`, `getValues` and
`getDuals`. The existing bulk adapter experiment found slower total latency than
the scalar adapter, so retain the scalar construction as the initial COPT timing
lane. Use bulk import as a separately identified acceptance/readback diagnostic,
not an assumed improvement or a silently substituted timing implementation.
Do not change the historical workers. Preserve COPT's coefficient/infinity guards:
finite values at or beyond its infinity sentinel or nonzero coefficients that
the configured import threshold may discard are unsupported. No matrix rounding
is allowed to manufacture common coverage.

For min-normalized objective sigma*(c*x+offset), row dual y is in original units,
positive on a lower side and negative on an upper side. Compute reduced cost from
the original matrix, never from the solver-reported reduced-cost vector. The
existing COPT exporter multiplies native row duals by sigma. Admit cuOpt's mapping
using independently constructed min/max, offset, equality and ranged-row cases;
do not assume its scaling/postsolve conventions from API spelling alone.

The existing Rust `external-certify` v1/v2 path is COPT-specific. GPUP-BASELINE must
add a new solver-neutral reader/bridge, reuse original-model feasibility,
`certify` and `assess_gap`, and leave old formats intact. Missing original duals
are an export limitation and an uncertified result, not an invitation to rerun
another solver. Infeasible/unbounded native statuses are retained without a proof
claim because this version has no independent ray/Farkas verifier.

## Model and acceptance coverage

The proposal binds eight existing development models by original byte hashes and
source manifests: small-4, irregular-2048, dense-block-1024, scaling-256,
scheduling-20x5, irregular-32768, dense-block-65536 and mixed-65536. Groups and
licenses are preserved. Historical models remain development evidence; the
held-out manifest is neither read nor repurposed.

Before vendor execution, new CPU fixtures must cover min/max offsets, free/fixed
variables, equality/ranged/one-sided/empty rows, empty columns, duplicate and
unknown IDs, tiny coefficients, sentinel collisions, signed zero, missing duals,
postsolve mappings, infeasible/unbounded status, timeout, cancellation, dependency
failure, false GPU claims and mismatched source/receipt hashes. Analytic optimal
solutions for tiny fixtures are authored independently of vendor output.

Two admitted solver suites per lane end with irregular-2048 and dense-block-1024.
Each suite includes the new tiny readback/sign-mapping cases before its nontrivial
model; all native calls share that job's cumulative 20-second solve allowance and
30-second outer reservation. These are admission suites, not primary timings;
no extra unbudgeted GPU jobs are implied by the tiny cases.
Require fresh independent certificates and actual nonzero iteration work in each
forced PDLP lane, plus source-bound GPU execution evidence in its GPU subset.
Portfolio/presolve-only solutions may count as portfolio success, with work
recorded honestly. API/sign/checker failures close dependent execution. A vendor
that is unavailable or cannot export required witnesses keeps explicit unavailable
rows; it cannot be replaced by a different method under the same lane ID.

Real sparse datasets and a larger degenerate corpus remain required for broader
competitiveness claims, but are not silently added to this bounded generated
screen. A follow-up manifest must name the original source/license, download and
converted hashes, importer, group split and unsupported constructs before it runs.
Warm sessions, hardware-counter profiles, other CPU resource cohorts, lower-quality
tiers and at-least-ten-repetition finalist/holdout evaluation are also deferred.

## Timing and analysis

Primary elapsed nanoseconds begin immediately before fresh worker launch and end
after worker exit, durable endpoint and independent checker receipt. Model import,
native license/context initialization, solve, extraction, check, serialization and
teardown all count. Record queue/lease wait separately. A timeout or late receipt
cannot become a successful primary timing even if an endpoint survives cleanup.

The grid is 8 models x 10 lanes x 3 repetitions = **240 screening cells**, including
168 GPU-requested cells. Freeze all identities before release. Within each
model/repetition block, order lane IDs by SHA-256 of
`17110 + NUL + model_id + NUL + repetition + NUL + lane_id`; use UTF-8 decimal
integers and lane ID as tie-breaker. Blocks sort by model ID then repetition.
This is stable across Python versions and independent of input array ordering.

Report planned/attempted/certified/GPU-confirmed counts per model and lane, every
unavailable/refused/failed/timeout cell, full costs and optional native solver time.
For each candidate against tuned FP64, report paired ratios only for jointly
certified repetitions alongside the full denominator. Bootstrap the paired log
ratios with 10000 resamples, seed 17111, percentile 95% intervals, per model.
Three repetitions give limited uncertainty information, not a supported recipe.
Do not pool only favorable certified pairs into a global superiority claim.
Coverage loss prevents a broad speed claim; incomplete admission/screening stays
incomplete. No speedup threshold is a requirement to finish this baseline study.

## Two-phase resource proposal

This is a proposal, not an allocation. The machine document fixes
`execution_authorized=false` and selected UUID null. A future accepted run manifest
must bind the exact GPU, allowed four-CPU set, source/binaries, environment,
controller/LP settings, all effective native defaults, supervisor and execution
authority before its first reservation. Model hashes alone do not make it runnable.
The old GPUP-8 journal, charges and completion criteria stay unchanged.

| Phase | Jobs / limit including cleanup | CPU reservation, seconds | GPU reservation, seconds |
| --- | --- | ---: | ---: |
| A software: new adapters/checker bridge and focused native acceptance | Bounded CPU-only stage | 2400 | 0 |
| A hardware/lease and installed stack admission | 2 GPU jobs x 30 s | 240 | 60 |
| A adapter acceptance | 10 lanes x 2 models x 30 s; 14 GPU jobs | 2400 | 420 |
| A reporting | CPU-only | 600 | 0 |
| A restricted cleanup margin | Termination only | 400 | 0 |
| **A total: admission only** | **No comparison timings** | **6040** | **480** |
| B screening | 240 jobs x 60 s; 168 GPU jobs | 57600 | 10080 |
| B reporting and restricted cleanup | 600 + 400 CPU s | 1000 | 0 |
| **B total: conditional screening** | **Requires A pass and separate release** | **58600** | **10080** |
| **Combined maximum** | **No automatic transfer between phases** | **64640** | **10560** |

The four-times-wall policy reserves 4*30=120 CPU seconds for each acceptance job
and 4*60=240 for each screening job. Acceptance native solve limit is 20 seconds,
worker deadline 28 seconds and cleanup at most two more; screening uses 40 seconds
native, 58 seconds worker and two cleanup. The remaining worker time must cover
conversion, extraction and certification; it is not an extra allowance. Stop on
resource refusal instead of reducing a deadline mid-study. Full failed/unsettled
reservations remain charged; actual overrun is charged and stops later releases.

Proposed aggregate limits: 16 GiB host process-tree RSS, 12 GiB device allocation,
one owned job at a time, 128 MiB original JSON input, bounded 16 MiB stdout and
16 MiB stderr per job. Reuse the accepted cooperative in-container supervisor
semantics and shared GPU lease. Its sampled memory policy is not a hard cgroup
memory guarantee. Before release, demonstrate process-tree accounting, affinity,
termination, log limits and peak/device memory observation for these new workers;
do not claim that installing a package establishes resource acceptance. Hidden
GPU allocations beyond the admitted observation/control capability refuse release.
No host, container, driver or supervisor redesign is included in this proposal.

The previous campaign has only **2432.029501798 GPU seconds** remaining under its
current ceiling. Phase A fits arithmetically, but still needs an explicit new task
allocation; none is transferred here. Both phases together would exceed that
headroom by **8127.970498202 GPU seconds**. If accounted under the same cumulative
CPU ceiling, they would exceed its headroom by **46603.097503214 CPU seconds**.
Consequently the complete screen needs an explicit resource amendment or a new
separately authorized campaign before B can be released. No completed historical
check, profile or trial is rerun by this specification. New controls must have new
study identities and their own acceptance when execution is authorized.

## Delivery and next task

The CPU validator admits the proposal and original artifact bindings; canonical
and endpoint fixtures exercise the new schemas and semantic checks. The
[acceptance receipt](data/baseline-spec-acceptance-v1.json) records only new CPU
contract tests, documentation and preservation checks. It is not solver evidence.

GPUP-BASELINE-SPEC is complete when these checks pass. GPUP-BASELINE is the next
implementation slice: build the separate adapters/checker bridge and prepare
the exact phase-A run manifest. Its numerical execution remains gated on resource
and protocol release. GPUP-8 stays incomplete; GPUP-9 stays gated.
