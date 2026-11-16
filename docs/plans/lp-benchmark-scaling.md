# LP benchmark scale survey and proposed evaluation

Status: benchmark research and prospective design, 2026-11-17; no scaling runs.
Scope: broadly useful single-solve LP acceleration through low-bit arithmetic,
including FP4, under [SPEC-0045](../specifications/SPEC-0045-general-lowbit-lp.md).
The [latest implementation results](../benchmarks/lp-general-overhead.md) remain
unchanged. This plan does not freeze a confirmation or enlarge resource limits.

## What established collections actually contain

The following statistics were calculated from the publishers' metadata, retrieved
on 2026-11-17. They describe the listed original problems, not presolved matrices.
The [compact inventory](lp-benchmark-scale-inventory.json) records source URLs,
retrieved-byte hashes, counting conventions, statistics and representative rows.
No model archives were downloaded and no solver was executed for this survey.

| Collection / explicitly surveyed subset | Listed instances | Median nonzeros | Largest listed nonzero count | Role |
| --- | ---: | ---: | ---: | --- |
| [NETLIB main numeric summary table](https://netlib.org/lp/data/readme) | 96 | 5,187 | 151,120 | Historical small controls |
| [NETLIB Kennington supplement](https://netlib.org/lp/data/kennington/readme) | 16 | 153,853 | 1,630,758 | Larger historical sparse controls |
| [MIPLIB 2017 benchmark set](https://miplib.zib.de/set_benchmark.html) | 240 | 110,248 | 27,329,900 | Diverse LP relaxations |
| [Mittelmann LPfeas, disclosed main dimension table](https://plato.asu.edu/ftp/lpfeas.html) | 49 | 1,955,388 | 93,001,800 | Modern large public LP anchors |
| [PDLP large-scale collection, paper v2 Table 2](https://arxiv.org/html/2501.07018v2#S6.T2) | 11 | 500,049,700 | 6,337,834,450 | Extreme-scale reference and generator families |

These are different populations, not a pooled benchmark. NETLIB's main table
includes the objective row and objective coefficients and excludes slack/surplus
columns. The 96 count means numeric rows in that table, not every NETLIB archive
or generator. MIPLIB is a mixed-integer collection: our proposed inputs are its
continuous relaxations, preserving objective, rows and bounds while removing
integrality. MIP difficulty labels and integer optima are not LP reference results.
Relax the original MPS before LP-valid presolve; the library's MIP-presolved
models may contain reductions that are invalid for the original LP relaxation.
Published MIPLIB summary counts may be rounded; imported matrix counts must be
measured from the pinned input bytes.

Mittelmann's current main roster has 65 entries, but 16 are undisclosed; the
statistics above cover only the 49 published dimension rows and exclude its
separate extreme-scale addendum. Of those 49, 38 exceed one million nonzeros and
11 exceed ten million. Its table conventions differ from MIPLIB, so similarly
named entries must not be treated as identical input versions.
LPfeas targets a primal-dual feasible point; its reported runtimes likewise do
not establish performance at our original-model certificate criteria.

Representative scale anchors, using the counts as published:

| Collection | Instance | Rows / constraints | Columns / variables | Nonzeros |
| --- | --- | ---: | ---: | ---: |
| Kennington | OSA-60 | 10,281 | 232,966 | 1,630,758 |
| Mittelmann | pds-100 | 156,244 | 505,360 | 1,390,539 |
| Mittelmann | scpm1 | 5,000 | 500,000 | 6,250,000 |
| Mittelmann | a2864 | 22,117 | 200,787 | 20,078,717 |
| MIPLIB relaxation | square47 | 61,591 | 95,030 | 27,329,900 |
| Mittelmann | dlr2 | 7,132,926 | 38,868,107 | 78,091,589 |
| Mittelmann | Dual2_5000 | 30,000,600 | 33,050,602 | 93,001,800 |
| PDLP | heat-source-easy | 15,625,000 | 31,628,008 | 125,000,000 |
| PDLP | tsp-gaia-100m | 162,934,799 | 1,184,557,727 | 6,337,834,450 |

The PDLP paper evaluates its largest collection with a 1% optimality gap and
primal/dual feasibility errors below 1e-8. Those results do not imply our strict
1e-7/1e-9 certificate targets will have similar solve times. Its
[public generator repository](https://github.com/ohinder/large-scale-LP-test-problems)
provides configurable supply-chain, heat-source, production-inventory and matching
families; its full large-instance generation instructions require at least 512 GB
RAM. Reuse the formulations and smaller parameter settings before attempting the
published full sizes. Pin generator commits, licenses, dependencies and seeds.

## Consequences for this project

Our six enlarged general-development fixtures contain 212,918 to 567,673 original
matrix nonzeros. In particular, irregular65537 has 567,673, dense_blocks16385 has
371,121 and dense1025 has 524,800. Thus large variable counts have not yet exposed
the modern multi-million-nonzero regime. These counts come from the existing
[compact results](../benchmarks/lp-general-overhead-results.json); they are not a
claim about all earlier, differently scoped experiments.

The next evaluation should span realistic large sparse LPs and controlled scale
families. Increasing density alone would miss vector-size, sparse-index, irregular
row, certificate and convergence costs. Existing small and medium cases remain
part of the population. A larger suite must retain low tile coverage and numerical
difficulty, even if FP4 does not help there.

## Proposed scale ladder

M below means one million actual original-A nonzeros, not stored padded entries.
Targets are approximate for application generators; record actual dimensions and
nonzeros. This is a development design, not a promise that each target fits the
present machine or that every family reaches every rung.

| Stage | Target nonzeros | Purpose | Execution condition |
| --- | --- | --- | --- |
| Continuity | Existing roster plus about 0.25 M and 1 M | Connect to prior results and retain small-case costs | Existing admission, with complete resource preflight |
| Main scaling | 4 M, 16 M, 64 M | Cover and exceed much of the public LP/MIPLIB scale | Per-instance dimension, numerical-domain and total-memory admission |
| Large public scale | 128 M, 256 M, 512 M | Cross the main Mittelmann maximum and enter PDLP scale | Extend/admit dimensions, storage and execution resources first |
| Frontier design | 1 B, 2 B, 8 B | Reach and exceed the surveyed 6.34 B public reference | New capacity/indexing architecture and explicit resources; no current execution commitment |

Do not silently replace a sparse family that exceeds a dimension limit with a
denser matrix. Retain its unsupported cell and the required engineering work.
The 8 B target exceeds the largest instance in the surveyed PDLP collection;
it is not a claim to exceed every published or proprietary LP experiment.

## Population and construction

1. **Public originals.** Build an inventory from the named collections before
   measuring candidate performance. Include the table's anchors and stratify the
   wider inventory by nonzero count, aspect ratio, row/column degree distribution,
   coefficient range and application/source group. Include tall and wide cases
   such as MIPLIB's neos-3402454-bohle and supportcase19. Retain inaccessible,
   unsupported and memory-limited entries explicitly. Public examples inspected
   here are development anchors, not unseen confirmation instances.
2. **Application-derived scaling.** Use parameterized multicommodity flow,
   production/inventory, PDE/heat-source recovery and matching/allocation models.
   Increase commodities, time horizons, spatial grids or population sizes with
   real coupling through capacities, transitions or balancing constraints.
   Use at least three independently seeded instances per feasible family/scale
   in initial development, subject to a frozen total-cost reservation.
3. **Controlled structural scaling.** Extend the six current families with
   independently controlled nonzeros, dimensions and row-length distributions.
   Include approximate aspect ratios 1:16, 1:1 and 16:1 at matched nonzero counts;
   local and long-range coupling; and low, intermediate and high tile coverage.
   Use these as targeted contrasts rather than a prohibitively large full cross
   product. Dense cases remain one stratum, not the eligibility definition.
4. **Numerical stress.** Include ordinary binary64 coefficients beyond simple
   powers of two or the old generator's short coefficient palette, wide coefficient
   ranges, active bounds, inequalities, degeneracy and near dependence. Vary
   scale separately from difficulty where possible. Construction witnesses can
   validate generated data, but never enter solver inputs or provide warm starts.

Do not inflate scale by copying independent small LPs along a block diagonal or
repeating identical tensor tiles. Such repetitions may be labeled microbenchmarks,
but they do not count as independent large-LP evidence. Record connectivity and
cross-block coupling. Related seeds, permutations, rescalings and sizes belong to
one source family for splitting and uncertainty; they do not create independent
application families. Charge any general reordering/packing in every relevant
complete solve and give equally applicable preprocessing to the controls.

## Measurements and comparisons

Keep native FP64 and FP32 controls with the same shared implementation improvements.
Use actual FP4 Tensor Cores with the general precision policy under development;
FP4x1/x2 ablations can diagnose representation costs. Compare established solvers
such as HiGHS and PDLP as separate references, binding versions, algorithms,
thread counts, hardware, presolve and termination criteria. External-solver status
does not replace our independent original-model certificate.

Measure two distinct endpoints:

- Equal-work execution: products, projection/encoding, launch gaps, reference
  work, bytes transferred, allocated buffers, tile padding and physical arithmetic
  expansion. Use matched update counts and report whether trajectories differ.
  A fast product alone is not certified-solve superiority.
- Fresh-process time to strict certified output at both 1e-7 and 1e-9: parsing,
  preparation, transfers, iterations, original-model assessments, promotions,
  rejected work, recovery and checking. Retain the complete teardown/lifecycle
  cost as well. Reserve independent serial verification and evidence handling;
  report these separately when outside the timed solver endpoint.

Plot size against time, successful certification, iteration count, assessment
share and accepted FP4 work share. Report absolute savings as well as ratios.
Original, transformed/presolved and padded matrix sizes stay separate. A useful
secondary accuracy curve may reproduce a published looser target, but it is
labeled separately and never substituted for the strict endpoints.

Use interleaved, balanced timing repeats; start with four per development cell
only after resource preflight. Repeats estimate timing noise, not problem diversity.
Report all statuses and a budget-based success/time profile alongside jointly
certified paired timings. Do not pool only the cases where both solvers succeed.
Distinguish operational missingness, unsupported inputs and numerical limits.

Confirmation remains a later freeze under SPEC-0045: choose the broad estimand,
family weights, practical improvement, per-stratum coverage/nonregression and
tail criteria, meaningful accepted FP4 contribution, familywise error control and
power from development evidence before inspecting holdout results. Preserve
unfavorable strata; do not inherit a uniform 10 ms floor or claim a broad win
solely from the largest favorable cases. No confirmation thresholds are changed
by this survey.

## Capacity and implementation prerequisites

The current [operator](../../research/lp-general-lowbit/src/operator.rs) admits at
most 1,048,576 rows or columns and 67,108,864 nonzeros. Thus even a sparse public
case with a few million coefficients can exceed the dimension domain. Larger
domains require reviewed reduction/range bounds, checked index arithmetic,
recovery, certificate and device admission; editing those constants is insufficient.
The 8 B target also exceeds 32-bit total-nonzero offsets.

Keep the present 16 GiB sampled host-RSS and 12 GiB owned-device-buffer limits
for any work within the existing allocation. Preflight the full resident and
transient representation: original model, CSR/CSC, FP64 references/state,
indices/maps, FP32 controls, FP4 components/scales, packed tiles, residuals,
checkpoints, checker processes, parsing and generation. FP4 coefficient payload
is only one term and FP4x2 is not four bits of total storage per coefficient.

For scale perspective, two FP64 coefficient arrays alone cost 16 bytes/nonzero:
64 M needs 0.954 GiB, 256 M needs 3.815 GiB, 1 B needs 14.901 GiB and 8 B needs
119.209 GiB. These are lower bounds on that representation, excluding indices,
vectors, tiles and all host copies, not fit estimates. In the current fast
executor, the conservative allocation formula additionally includes
`8 * nnz + 64 * tiles + 320 * (rows + columns + 1)` bytes beyond operator and
packed storage. A small nonzero count with tens of millions of variables can
therefore still exceed the device budget. See
[buffer accounting](../../research/lp-general-lowbit/src/fast_device.rs).

Use streaming generation/import and bounded temporary storage for scale work;
do not instantiate millions of Python term dictionaries merely to serialize them.
First estimate all native/FP32/FP4 and checker memory requirements without
materializing a large model. Treat out-of-core or multi-device execution, if
needed later, as a separately admitted architecture with all transfer costs.
Do not assume those changes or larger hardware are already available.

## Next execution sequence

1. Pin public input/generator sources and licenses, implement metadata inspection
   and total-memory estimates, and freeze the first development roster by structure
   and size. Keep the 22 existing models in coverage and mark prior inspected
   cases as development. Download only the inputs selected by this inventory.
2. Resolve importer, representation, general convergence and assessment-cost
   limits on small representatives; admit changed code before scale measurements.
3. Start at 1 M and 4 M, then 16 M and 64 M where each family's dimensions and
   memory fit. Account for all lanes, tiers, repetitions, original checking and
   teardown in each reservation; do not reuse the undersized prior group budget.
4. Use those observations to size a complete prospective reservation for larger
   public anchors and 128 M-plus generators. If a family exceeds capacity, retain
   the limitation and design the necessary extension rather than dropping it.
5. Freeze independent confirmation only after the broad candidate and all required
   capacity, correctness and resource checks are ready. Keep large inputs and
   raw evidence local; track compact manifests, generator bindings and results.

This survey adds a scale design and metadata evidence. It changes no solver,
numerical admission, historical result, public default or existing allocation.
