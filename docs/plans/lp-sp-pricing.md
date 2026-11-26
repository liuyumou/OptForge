# Strongly polynomial pricing: implementation and evaluation

Date: 2026-11-25. Source: [the November 24 paper](https://github.com/openai/math/blob/main/preprints/Strongly-polynomial-linear-programming-November-24-2026/paper.pdf).

## Implementation status

The isolated [research implementation](../../research/lp-sp-pricing/README.md)
connects the full reference structure and provides an optimized practical path.
The frozen held-out confirmation is complete: 246 attempts and six capacity
refusals across 252 slots. The
[measurement report](../benchmarks/lp-sp-pricing.md) records its final outcomes.

| Planned component | Implemented behavior | Validation boundary |
| --- | --- | --- |
| Exact arithmetic and geometry | Rational elimination, Newton minors, slack/orthogonal spaces | Independent scalar, rank and determinant tests |
| Online compression | Exact affine sign access, symbolic large logs, common scales/LLL, restart invalidation | Explicit-rational differential tests; oversized products refuse |
| Compressed calibration | Ordered cofactors, common compressed proxies, rational exponential approximation | Component calibration tests; literal parameters refuse before oversized allocation |
| Implicit experts | At most five guesses, difference cells, counts/moments, ancestor wealth stacks | Enumeration oracle on small cells; no enumeration in implementation |
| Reference market | Rounded rational ellipsoid, integer feasibility gap, lexicographic recovery on proved vertex grids | Feasibility, rational optimum and actual grouped-market tests |
| Recursive search and recovery | Literal branching/depth, recursive investment, sequential coordinate restrictions from original data | Controller/circuit tests; no complete literal run validated |
| Practical markets | Integer utility arithmetic, exact signed-network flow dual and lexicographic prices | Exact flow checks, independent cut-LP comparisons, ASan/UBSan |
| Practical auxiliaries | Persistent GMP tableau, target early exit, exact negative dual certificates | Python exact differential oracle, original-model checks, ASan/UBSan |
| GPU search | Shared dense/CSR products, both signed slots, widths 1/8/32/64, precision escalation | 224 configurations and all four CUDA sanitizers |
| Adaptive pool | 4096 initial extras, at most three epochs and 65536 extras, 1024 queries | Deterministic prefix expansion; explicit new wealth epoch |
| End-to-end comparison | Frozen 28-model, three-lane, three-repetition campaign | Separate original-model strict audits; all 252 slots retained; recovery ordering deviation below |
| Billion originals | Dense and connected sparse capacity forecasts | Both unsupported before generation; no auxiliary substituted for an original LP |

Implementation presence is distinct from validation of a complete literal paper
execution. No practical or empirical strongly polynomial guarantee is claimed.
The reference mode preserves the paper constants; certified acceleration checks
GPU proposals and falls back to the reference oracle.

## Exact acceptance

Canonical input is exact `max c*x`, `A*x <= b`, with free variables.
Feasibility, recession and homogenized strict primal–dual feasibility produce
original-model witnesses. Practical support recovery may return as soon as an
exact witness exists. Reference recovery performs sequential restrictions to
isolate a circuit, rebuilding each trial from the original selected subspace.

Auxiliary labels use `-epsilon <= xi*B <= 2` and a coefficient box. A positive
label needs an exact witness at least 1/4. A negative label needs an exact upper
bound below 1/4, or an opposite-slot witness with proved isotropic separation.
Equality belongs to the positive case. Calibration epochs prevent stale proofs
from surviving a compression restart.

For a GPU dual proposal u, the exact upper bound is:

```text
H * ||c - B*u||_1 + sum_j support_[-epsilon,2](u_j)
```

Every final certificate is independently checked on the original LP. The
historical 1e-9 checker is a separate, explicitly run tier; it does not replace
exact-rational acceptance. All project intermediate assessments are also audited.

## Performance work

Profiling identified expert evaluation and Fraction arithmetic as the original
CPU market bottleneck. Common integer denominators and the exact flow dual remove
that cost. Native GMP auxiliaries/elimination, shared objective bases, exact
target exits, sparse proof products and an analytic calibration-error bound address
the next bottleneck. The original Python and cut-LP paths remain differential
oracles. A native 128-bit capacity limit is an explicit resource limit.

GPU matrix upload is shared across each batch. Target states are independent,
including the two signed slots, while recursive outer proposals retain their
sequential wealth dependencies. FP32 and FP4 components generate proposals.
Uploads/accumulation are FP64; FP4 is simulated E2M1 on CUDA cores with unpacked
storage. Tensor-core throughput, packed storage savings and arbitrary-precision
GPU arithmetic are not claimed.

On the separate-seed 21-case ladder, CPU and GPU each certify 14 cases.
Capped complete development costs are 88.3 and 114.7 seconds respectively.
The prespecified rule selects CPU before examining held-out results.

## Frozen evaluation

Seven families: dense, irregular, wide, tall, coupled, ill-scaled and degenerate.
Each has 16- and 64-variable cases at seeds 38101 and 38102. Tall has eight times
as many rows as columns, wide has half as many, and the others have twice as many.
Construction witnesses are stored separately and never supplied to solvers.

Three rotated repetitions compare practical pricing, retained image-v11 and the
previously selected COPT scale-off configuration. Native windows are 10/30
seconds and process windows are 30/60 seconds. The portable baseline input must
represent every original rational coefficient exactly in FP64. Every source,
binary, model, setting and roster identity is frozen before execution.

Seven family solve reservations amortize the idle observation while retaining
fresh per-cell processes. Independent audits use separate CPU reservations.
Complete cost includes common model encoding, process startup/preparation/solve,
output and mandatory independent endpoint audits. Idle observation and resource
finalization are excluded from comparable cost and retained in allocation charges.
All refusals, deadlines, missing responses, late certificates and unmatched
certificates remain visible. Only jointly timely accepted pairs receive ratios.
Three rotations and unflushed caches limit generalization.

Six solve reservations failed at output-directory creation before any LP in
those families started. Their full 40320 CPU / 10080 GPU seconds remain charged.
The corrected continuation freezes only untouched cells and precreates its output
parent. CPU-selected candidates run in CPU-only reservations; GPU baselines run
in bounded chunks which stop before another full process/cleanup window cannot
fit. Inputs, numerical sources, repetition identities and native/process windows
stay exact. This changes cross-lane interleaving for those six families, which
must be disclosed and limits the timing comparisons to descriptive results.
The degenerate family retains the original rotated order. A failed recovery
chunk stops continuation immediately.

The final strict timely counts are candidate 6, image-v11 3 and COPT 0.
The sole jointly certified model has three repetitions; the candidate's complete
cost is about 1.31 times image-v11's. The experiment does not establish broad
end-to-end superiority. Vendor optimal statuses and strict-checker rejection
reasons remain visible; an unmatched certificate receives no speed ratio.

Original billion models are dense 32000 by 31250 and sparse 1000000 by 1000000
with degree 1000. Both have one billion original nonzeros. The mixed optimality
basis and transpose forecast about 804 GB and 800 TB in FP64 alone. Explicit
rational geometry fails capacity before generation; no billion solve is attempted.

## Resources and preservation

The independent allocation remains 240000 CPU / 30000 GPU seconds.

| Phase | CPU seconds | GPU seconds |
| --- | ---: | ---: |
| Reference and native | 36000 | 0 |
| Admission | 24000 | 4000 |
| Development | 30000 | 6000 |
| Confirmation | 60000 | 12000 |
| Billion | 60000 | 8000 |
| Reporting and cleanup | 30000 | 0 |

Four CPU slots, 128 GiB aggregate owned host memory, 80 GiB owned device memory,
physical headroom, storage limits and exact ownership supervision remain.
The user's high-priority authorization prospectively sets a fresh 30-second idle
window for this study. Historical idle proofs and frozen sources remain exact.

Each reservation has immutable source snapshots, logs and a settlement. Every
failure keeps its full charge. Unresolved cleanup or overrun closes admission.
The earlier incomplete batch cell and every failed adapter/component admission
remain in the evidence. Existing project numerical sources, public defaults and
historical scientific identities are unchanged. No old billion driver is rerun.

## Lean GPU follow-up

The user's request to remove unnecessary candidate components authorizes an
opt-in FP64 proposal path with reusable state, fused CUDA kernels, active-target
compaction, staged exact acceptance, compact native GMP decisions and early
handoff to the existing exact CPU auxiliary solver. The original source/binary
archive remains bound by `gpu-optimization-baseline-v1/binding.json`.
Full final original-model certificates and the independent strict checker remain.
Software component precision modes and full intermediate witness traces are
removed from this candidate's execution path.

Development first compares fixed auxiliary step counts across dense/CSR layouts,
widths and implementations. Separate seed 73011 development selects the step
policy by timely exact certificates and then capped cost. A fresh seed 88371
confirmation freezes eight original models, three lanes (CPU, archived GPU,
lean GPU), two rotated repetitions, ten-second native and twenty-second process
windows, and complete cold-process plus independent audit timing. CPU and lean
GPU share compact trace output. All forty-eight slots and both exact/strict
acceptance tiers remain visible. Ratios require joint timely certification.

The source-bound admission covers 64 configurations and 1,680 exact differential
proposals, continued/inactive states and both CUDA kernel paths under four
sanitizers. Native GMP full and compact paths are compared to the independent
Python checker and run under ASan/UBSan. Three failed GPU admission reservations
retain full charges; v3's failed cleanup remains unchanged with an additive proof
that all seven exact recorded identities exited and a source-bound CPU readmission.
The allocation, phase caps, physical headroom, ownership checks and 30-second idle
window remain unchanged. No original scientific identity is repeated.

The [follow-up report](../benchmarks/lp-sp-pricing-gpu.md) records the final
configuration, all outcomes and limitations separately from the historical study.

## Preparation, interval checking and synchronized search follow-up

The user requests removing remaining preparation/checking overhead and advancing
auxiliary searches together. `wave-baseline-v1/baseline.json` retains the prior
candidate, tools, binaries and checkpoint. A three-rotation diagnostic separates
CUDA first-use initialization from warm matrix preparation and compares the old
sm_75 build with explicit sm_120 static/shared-runtime builds. COPT's internal
GPU initialization remains part of its opaque solve timer.

The new opt-in path overlaps initialization with CPU geometry, retains one
solve-scoped device arena, shares coefficient loads across four right-hand sides,
and uses common iteration checkpoints for all signed targets. Rigorous interval
decisions avoid unnecessary GMP products and string conversion, with GMP fallback
for uncertainty. Exact final acceptance and the independent 1e-9 checker remain.

Development retains 120 fixed-work cells and separate 21-model step-policy
ladders. Selection precedes a new seed-99173 comparison: seven families, four
lanes (CPU, preceding lean GPU, synchronized wave GPU, retained COPT scale-off
GPU-PDLP), and two cyclic rotations. Every lane receives ten native seconds and
fifteen process seconds. All 56 cold-process outcomes and mandatory independent
audits remain, with ratios only for jointly timely certified endpoints.

Numerical admission checks 54 GPU configurations and 2,464 proposals, independent
scalar equations, continued/inactive states, all four CUDA sanitizers, interval
edge cases and 128 native ASan/UBSan cases. The first GPU admission retains its
full charge after a supervised process-disappearance error. An additive local
process-mapper fix handles ProcessLookupError consistently with FileNotFoundError,
with a fresh source-bound CPU gate; foreign ownership and other sampling errors
still fail. Shared resource-critical files, phase caps and physical limits stay
exact. Only unfinished sanitizer work continues under a fresh identity.

The [new report](../benchmarks/lp-sp-pricing-wave.md) and its settled checkpoint
record final timings, all failures and the remaining limits separately.

The completed wave cohort reveals a remaining first-query initialization wait.
A subsequent Python-only policy uses the existing exact CPU oracle for queries
while the GPU future is pending, and dispatches to the unchanged admitted wave
backend once ready. It propagates failed initialization and joins/releases an
unused session at teardown. New CPU contracts cover all four paths; all numerical
CUDA/interval/GMP bindings remain exact.

Seven cold seed-73011 development pairs select the opportunistic policy with
six certificates in each lane and 23.358 versus 22.302 capped process seconds.
A new seed 111359 freezes seven families, CPU/wave/opportunistic lanes and two
rotations: 42 additional cold cells with the same ten/fifteen-second windows.
All original-model audits and complete costs remain. This is a separate fresh
confirmation after policy development, not a regrading of the preceding cohort.
The [policy report](../benchmarks/lp-sp-pricing-wave-policy.md) retains its results
and links the direct COPT comparison without inferring a transitive speedup.

Final verification completes 67 tests and 400 documentation pages, then its
resource finalization fails with `coordinator_lost`. Both completed verification
records, empty cleanup, the original failure and the full 960 CPU-second charge
remain. The preceding cause is not established by the retained evidence.
`tools/lp_sp_pricing_wave_finish.py` seals the completed records, exact source
copies, output hashes and absent process identities in a fresh CPU-only reporting
reservation. It performs no numerical recomputation or scientific retry. The
[finalization receipt](../benchmarks/lp-sp-pricing-wave-finalization.json) binds
that separate audit and both settled checkpoints without regrading the failure.

## Million-scale experiments

The user requests million-scale experiments. Fresh seed 121951 defines three
original LPs with exactly one million nonzeros: 1000×1000 dense, 4000×1000 tall
with 250 entries per row, and 8000×8000 sparse with 125 entries per row. Exact
dyadic planted certificates are checked independently before freezing; solvers
never receive those witnesses. The unchanged candidate geometry guards are
tested prospectively by dimensions and retain unsupported rows. COPT scale-off
GPU PDLP receives two cold repetitions per model with 30-second native and
45-second process limits, followed by the unchanged strict endpoint checker.

The separate auxiliary cohort has 108 cold processes: three matrices with one
million coefficient positions, dense/CSR storage, 64/256/1000 distinct objectives,
lean/wave kernels, and three alternating repetitions at 128 FP64 steps. Two
dense matrices have one million nonzeros; the sparse matrix has only 16000.
All returned matched states receive a whole-state differential audit, with
independent CPU equations on twelve selected states and exact interval/GMP
checks on four proposals from each wave cell. Kernel time, cold auxiliary
process time and complete original-LP time remain separate.

Only new experiment tools and tests are added. Admitted numerical sources and
limits remain exact. The prospective outer reservations are development 1300
GPU seconds for auxiliary processes and 1200 CPU-only wall seconds for their
audit; confirmation 360 GPU seconds for six COPT attempts and 120 CPU-only wall
seconds for endpoint audits. Preparation and final reporting use separate
CPU-only reservations. Every phase stays within the existing 240000 CPU /
30000 GPU-second allocation, with four slots, 16 GiB requested host memory and
the existing physical, ownership and 30-second idle requirements. No historical
scientific identity is repeated. The frozen manifest is `million-v1/freeze.json`.

All 108 auxiliary runs and six COPT original-LP attempts complete with passing
supervision; their separate audits also pass. The 54 whole-state auxiliary pairs
are bitwise identical, and all 216 sampled proposal checks have equal GMP and
interval label coverage. Final verification completes 72 tests and 401 pages,
but its resource finalization records `coordinator_lost`, empty cleanup and full
720 CPU seconds. The preceding cause remains unestablished. A separate CPU-only
read-only seal retains that failure and verifies the completed records and
original source copies without repeating scientific work. The
[finalization receipt](../benchmarks/lp-sp-pricing-million-finalization.json)
binds that seal to the settled checkpoint.

## Compact geometry and bounded GPU execution

The user explicitly requests lazy exact fallback construction, tiled products
and checks, bounded synchronized auxiliary batches, and factorized/implicit
bases. The new opt-in `compact_*` path keeps all prior numerical sources and
scientific records exact. It stores sparse RREF rows and references to their
nonpivot factors, generates the orthogonal complement `[-R^T I]` on demand,
and preserves exact half-integral-price calibration using sparse elimination.
Original feasibility/recession/optimality reductions are sparse row generators;
original certificates are still checked independently. There is no strongly
polynomial complexity claim for this practical variant.

CPU constraints/tableaus are constructed only after unresolved GPU labels.
Their original million-cell admission remains. Sparse elimination instead
checks actual fill, with a two-million-entry/four-GiB per-factor envelope and
the original operation/bit/deadline checks. Four slots and the supervised
aggregate 16-GiB experiment reservation remain authoritative; representation
estimates are not hard aggregate process-memory measurements.

GPU execution retains at most 64 searches, with 32 selected prospectively,
and at most 256 MiB of numerical state. A bounded 64-MiB tile cache is optional;
larger matrices use two pinned upload slots and explicit copy/compute events.
Host coefficient and sparse-check caches each have 32-MiB limits, with bounded
temporary tile buffers. A single producer prepares the next tile, while one
host checker may overlap the next GPU batch. No unbounded future queue or
parallel exact tableau is introduced. Streamed rigorous interval tests fall
back to exact rational products on uncertainty; only proved labels are merged.

CPU differential tests cover implicit complements, exact calibration, sparse
fill refusal, unchanged original-model certificates and zero fallback allocation
when GPU labels suffice. Native ASan/UBSan covers 64 cases; source-bound GPU
admission covers cached/streamed dense/CSR products, independent scalar states,
24 configurations, 116 exact proposals, pipeline equivalence and all four CUDA
sanitizers. The first CPU development reservation retains its full 960-second
charge for a test import-path error. Earlier successful compact admissions and
their source copies/binaries remain when sparse packing/check-cache reuse is
improved; final experiments require the final admission.

Prospective evaluation: eighteen cold auxiliary cells compare wave, compact
serial/pipelined execution and forced streaming where admitted. Fixtures include
two million-position matrices and an implicit 128-million-position paired space;
the latter stores only 4000 positive-factor entries. A 1100-second development
GPU reservation covers every auxiliary process window plus admission/cleanup.
Three formerly unsupported original million-nonzero candidate cells then receive
20 native / 30 process seconds under a separate 180-second development GPU
reservation. Old COPT solves are not repeated. Finally, seed 122011 supplies
three fresh small original models and 24 cold runs, four lanes and two rotations,
under a 420-second confirmation GPU reservation with 10/15-second windows.
Every returned original endpoint receives independent exact/strict auditing.
Resource limits, phase caps, strict 1e-9 authority, failed charges and the fresh
30-second idle requirement remain unchanged.

## Native exact geometry and fresh COPT comparison

The user requests diagnosis and acceleration of exact CPU geometry, followed by
fresh million-scale comparisons including all preparation. Fresh seed-122101
profiles isolate the first slack-space row reduction, with roughly eighteen
million Python calls per eight-second instrumented attempt. No calibration or
auxiliary query is reached. The new opt-in `geometry_fast` path uses native
sparse GMP elimination and bounded exact integer endpoint checking. Numerical
LAPACK/SuperLU/LSMR factor solves propose dyadic endpoints; only exact original
primal/dual/gap checks permit an early return. Such presolve completion is
reported separately from execution of the paper's pricing construction.

A separate CUDA kernel computes exact modular rank over the prime 65521. Full
column rank proves the rational space is full when all denominators are
invertible. An incomplete modular rank supplies no negative rational conclusion
and falls back to GMP. Matrix allocation is bounded to one GiB; this is a
separate geometry workspace, within the unchanged 80-GiB device and 16-GiB
sampled experiment host limits. Existing compact numerical state/cache limits,
CPU fallback limits, exact scalar limits and all historical sources stay exact.

CPU differential tests, native ASan/UBSan and all four CUDA sanitizers precede
performance measurements. The first CPU admission retains its full 720 CPU-second
charge for an unavailable optional thread-control import. The implementation
instead inherits the supervisor's unchanged single-thread BLAS configuration.
No dependency or shared resource-source change is required.

Development separately measures completed exact RREF comparisons, large modular
rank proofs and certificate proposals on seed 122127. Fresh confirmation uses
seed 122141 and three million-nonzero models with nonuniform dyadic primal and
dual construction witnesses; witnesses are never supplied to either solver.
One rotated cold attempt per model/lane gives six candidate/COPT cells, each
with 30 native / 45 process seconds. The 330-second GPU reservation fits the
remaining confirmation cap. This is a small synthetic cohort with no repeated
timing estimate. Model encoding, cold startup, import/conversion, factorization,
GPU preparation if used, solve, proof, output, teardown and independent endpoint
checking are all included in complete cost. Development, rank diagnostics and
reporting use fresh reservations; all phase caps and failures remain exact.

A separate prospective supplement adds automatic-method CPU COPT on the same
three frozen models, with the same 30/45-second windows and complete-cost
definition. It was added after the primary roster was frozen and its first
candidate timing was visible, to avoid limiting the comparison to the retained
GPU-PDLP configuration. Candidate sources and configuration are not changed or
repeated. Default method/presolve/scaling/dualization/crossover values are recorded;
only resource controls, original-coefficient handling and common strict tolerances
are set. The three-cell CPU-only reservation is 180 seconds within the existing
confirmation CPU cap, followed by the unchanged independent endpoint audit.

## Larger two-seed evaluation and independent certificate assurance

The user requests larger and more numerous experiments, permits longer solver
deadlines and additional time budget, and asks for completion within two hours.
`scale-allocation-v1.json` prospectively transfers unused large-scale allowance
to confirmation: CPU confirmation/billion become 84000/36000 seconds and GPU
confirmation/billion become 17000/3000 seconds. Total ceilings stay at
240000 CPU / 30000 GPU seconds. The existing wrapper, ownership/supervision
sources, physical caps, 30-second GPU idle window and every historical failure
remain exact. The new allocation adapter checks its approval/source bindings
and a fixed wall deadline of 2026-11-26 02:12:58 UTC (10:12:58 Asia/Shanghai).

The solver's previous arithmetic remains frozen. A new opt-in certificate
boundary validates integer ranges before narrowing and cached coefficients
against the original model. An adversarial direct-call test exposes unsigned
wraparound in the old helper; solver-produced endpoints were bounded signed
integers and historical results remain independently verified. The new boundary
rejects that input and forged integer caches without weakening acceptance.

The new independent original-model verifier uses `float.as_integer_ratio`,
Python arbitrary-precision integers, a complete CSR traversal, exact dual
equations and exact gap equality. It neither calls the native proof library nor
uses planted witnesses. It also checks that published floating endpoints match
their rational certificates. Admission covers 128 random mixed-active valid
models against two independent oracles, 384 corrupted proofs, unsigned/range
edges, exact cancellation, non-dyadic certificates, corrupt content objects
and mismatched published endpoints. Existing native/GPU numerical admissions
remain exact; only the new CPU certificate boundary and verifier need admission.

The frozen fresh roster has five families and two independent seeds: dense
2000×2000 (4M NNZ), dense 4000×4000 (16M), sparse 16000×16000 degree250 (4M),
row-scaled sparse 40000×40000 degree250 (10M), and mixed-active tall 8000×2000
degree500 (4M). Signed coefficients, nonuniform primal/dual values and inactive
constraints extend the preceding all-active positive-coefficient cohort. Eight
square cases remain synthetic all-active LPs; two tall cases have 20% inactive
rows. There is one cold timing per independent input/solver, not repeated timing
of one seed. Candidate, retained GPU-PDLP COPT and automatic CPU COPT give thirty
cells. Each receives 120 native seconds and 150 process seconds. Native arithmetic,
fill and state caps remain unchanged; longer time does not waive other limits.

Two sequential GPU groups reserve 1560 seconds each; the two separate automatic
CPU groups reserve 810 seconds each. Each group uses four slots and 32 GiB sampled
host memory, within the unchanged 128-GiB global cap. Endpoint audits and reporting
reserve their own CPU time. Both the unchanged strict 1e-9 checker and the new
complete independent exact checker evaluate every available endpoint. Complete
cost includes generation/encoding, cold process startup, all preparation, solve,
internal proof, output/teardown and both external audits. Operational complete
cost excluding the additional research oracle is also reported separately.
The launch envelope preserves ten minutes for audits/reporting and records any
unattempted wall-budget slots explicitly. No historical scientific cell repeats.

An additional frozen challenge protocol selects every independently accepted new
candidate endpoint. It changes one objective coefficient by 2^-16 and separately
sets one dual multiplier negative. The guarded native checker and arbitrary-
precision checker must reject both. The objective mutation traverses the entire
matrix. These are in-memory proof challenges, with no changed immutable input or
repeated LP solve; their costs are separate from comparison timings.

After the first GPU group and first automatic-CPU result were visible, a separate
longer-window supplement was declared for dense-16m, sparse-scaled-10m and
mixed-tall-4m, using fresh seed 122419. All three lanes get 300 native / 360
process seconds on those new inputs. The same solver sources, settings, exact
checks and resource guards apply. Its nine slots are separate from the original
thirty; unequal-window cohorts are not pooled for timing claims. The supplement
must fit the same two-hour deadline, including endpoint audits and settlement.

A separate post-hoc certificate-format diagnostic was declared after the first
seed's raw endpoint audits. It applies the candidate's same bounded dyadic
reconstruction policy to every available endpoint from all lanes in both
cohorts. It performs no factorization, LP reexecution or planted-witness lookup.
Both independent checkers must accept any reconstructed certificate. Cold
reconstruction and fresh audits are charged equally to both candidate and vendor
pipelines; raw outcomes remain unchanged, and all 39 slots stay visible. Its
64 small positive/negative tests precede execution. Results are explicitly COPT
plus reconstruction, rather than native COPT exact certification.

The second candidate/GPU group writes all ten process responses and completion
marker, then receives `coordinator_lost` during final supervision. Its original
refusal, full 6240 CPU / 1560 GPU-second charge, empty cleanup and no-overrun
receipt remain unchanged. A fresh CPU-only read-only seal verifies retained
records and recorded identity absence without recomputing any LP. All ten
timings are excluded from certified counts/ratios, including the reconstruction
tier. Endpoint certificates still undergo the full independent audits. The
preceding cause remains unknown; no resource source is changed or retried.

