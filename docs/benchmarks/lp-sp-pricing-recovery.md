# Wide and mixed-active LP recovery: implementation and COPT comparisons

Date: November 26, 2026. This opt-in update addresses the wide and mixed-active failures in the [preceding report](lp-sp-pricing-comprehensive.md), while retaining the successful square and irregular numerical paths. All certified times below include model encoding, cold preparation, solving, endpoint recovery and independent certification.

The primary study contains **57 fresh solver attempts on 21 models**: fifteen focus models against COPT GPU and CPU, plus six paired old/new regression models. A second cohort adds **45 fresh attempts on fifteen further models** using a faster common exact checker. The second cohort supplies 12/15 timely, supervised candidate certificates and 15/30 eligible exact candidate–COPT pairs. A separately frozen mixed-square supplement adds nine attempts on three new models, for 111 attempts on 39 models. A final rectangular refinement adds sixteen attempts on five models: **127 comparison attempts on 44 models** in total, plus the separately reported development experiments. All attempted cells, native statuses, failed certificates and deadlines remain visible.

Across the second cohort’s eligible matched exact GPU comparisons, the candidate has the lower median complete cost in 3/4 families. The per-family tables retain the direction and sample count of every comparison, including cases that favor COPT. The six old/new square and irregular regression models retain identical accepted explicit certificates.

The practical improvement comes from recognizing a full-row-rank feasibility problem and representing its primal implicitly. It bypasses pricing when an independently checkable optimum is available. It does not speed up the paper’s literal recursive algorithm or establish strongly polynomial complexity. The performance conclusions apply to these synthetic cases and specified configurations.

## Diagnosis

Dense-wide previously spent a median 54.285 seconds in recorded exact geometry before its deadline. The numerical primal was generally not a short dyadic vector, so the earlier reconstruction failed even when a factor solve could describe a valid optimum. Building an implicit null-space representation after rational elimination did not remove that earlier elimination cost.

For the three retained, supervised sparse-wide follow-up inputs, the exact CPU market consumed 7.281, 7.327 and 7.324 seconds and returned `native_market_2`. The native source maps that code to its scan cap. The Python work total near two million is incomplete for this failure: the C++ scan metrics are copied back only on a successful return. The earlier cap was approximately 200 million remaining counted scans, not two million. Geometry/expert construction also consumed about 4.23 seconds. These earlier runs did not certify, so their durations are diagnostics rather than certified speedup denominators.

Mixed-active square cases exposed a different reconstruction limitation. With nonsingular square A, solving Ax=b makes every inequality active and feasible, even when the generated optimum had inactive inequalities. The resulting x may have non-dyadic rational coordinates. If the corresponding exact dual is nonnegative, this all-active point is optimal; rejecting it solely because x cannot be rounded to a short dyadic representation is unnecessary.

## Factorized recovery and exact acceptance

For m ≤ n, select m columns J and define B=A[:,J]. The certificate stores a dyadic primal base x₀, an exact dyadic dual y, the column indices J, and a floating inverse proposal R. It defines the actual primal by

`x = x₀ + E_J δ`, where `B δ = b − A x₀`.

An independent CPU enclosure proves ‖I−RB‖∞<1 and hence that B is nonsingular. Therefore the defined x satisfies **every original row equality Ax=b**, without explicitly materializing its rational coordinates or an n×(n−m) null-space basis. The enclosure assumes standard IEEE FP64 BLAS roundoff and rejects non-nearest CPU rounding. A full original-CSR scan with arbitrary-precision integers proves y≥0 and Aᵀy=c. Primal feasibility, dual feasibility and zero gap then follow exactly. The corrected primal can differ from the numerical endpoint; its implicit definition is the certified output. Raw floating-endpoint acceptance remains a separate, unchanged 1e-9 tier.

The first sparse-wide development bases used structural matching. Two certificates were correctly rejected because the matched numerical basis was ill-conditioned. The final constructor first tries two evenly distributed column selections, checks their inverse enclosures, and then retains structural matching as a checked fallback. The final independent checker recomputes the enclosure. No rank or stability decision is taken from the sparsity pattern alone. The rejected development outcomes and original sources remain retained.

| Input | Final proposal path | Avoided work / limitation |
| --- | --- | --- |
| Dense-wide | Dense CPU BLAS forms AAᵀ; one Cholesky factor solves the two right-hand sides b and Ac; Aᵀ maps the primal back | No rational geometry or market search on accepted recovery; normal equations can be inconclusive |
| Sparse-wide | Sparse AAᵀ and sparse LU, reused for both right-hand sides | No pricing queries or market scans on accepted recovery; sparse factor fill remains shape-dependent |
| Mixed-active square after old presolve rejects | CPU LU solves primal and transposed dual systems, followed by implicit primal recovery | Removes the short-dyadic-primal requirement; exact dual recovery remains bounded |
| Mixed-active rectangular, n < m < 2n | Existing resident FP64 GPU projection extended to the previously unsupported dispatch interval | Avoids rational elimination; retains the bounded preceding CPU presolve and exact postprocessor |
| Successful square/irregular presolve and existing tall dispatch | Original numerical entry point and original success path | No numerical algorithm change; measured regression controls below |

A separate CUDA implementation forms the wide row-Gram matrix with cuBLAS, factors it with cuSOLVER and solves both right-hand sides together. It passes CPU/GPU differential checks and memcheck, racecheck, initcheck and synccheck. Cold complete development timings favor CPU recovery at the tested sizes, so the frozen wide configuration uses `--wide-backend cpu`. The GPU option remains available and is measured explicitly; moving an operation to GPU is not treated as an end-to-end improvement by itself. Mixed-active rectangular recovery uses GPU projection.

The primary and second-cohort entry point is `tools/lp_sp_pricing_recovery_run_fast.py --wide-backend cpu`. Common endpoint recovery is `tools/lp_sp_pricing_recovery_endpoint_balanced.py`. Existing square/irregular successes still use their original exact factor presolve; only a rejected presolve enters new recovery. Public defaults and all retained numerical/resource sources are unchanged. New implementations and admissions are additive.

The wide dense proposal stores O(mn+m²) floating matrix entries. Its certificate has an m² inverse proposal and O(m+n) vectors/indices, rather than a full rational null-space basis. Sparse proposals retain sparse factors but the current certificate still has a dense m×m inverse proposal. The row dimension is capped at 4096, and the proposal shape at mn≤2^27. These are nonzero-scale experiments, not claims about millions of variables.

## Backend selection and faster host checking

The backend rule was fixed before holdouts: choose GPU only if its cold complete development cost improved by at least 10%. Each development comparison used a separate solver process and the same certificate pipeline; these single-pair measurements are configuration choices, not a broad performance claim. The CPU dense comparison uses dense BLAS rather than sparse multiplication.

| Development family | CPU proposal region s | GPU proposal region s | CPU complete s | GPU complete s | Selected |
| --- | ---: | ---: | ---: | ---: | --- |
| dense-wide-1m | 0.039 | 0.555 | 1.878 | 2.529 | cpu |
| dense-wide-4m | 0.194 | 0.598 | 4.869 | 5.319 | cpu |
| sparse-wide-1m | 0.425 | 0.735 | 3.721 | 4.222 | cpu |

The proposal region includes conversion and factor setup; its GPU measurement also includes cold CUDA/library initialization, allocations, transfers and teardown. It is not kernel-active time. At these dimensions, the complete GPU region costs more than the efficient CPU region, while both pay the same independent CPU certificate work.


The final checker overlaps three disjoint exact integer dual scans with the parent’s CPU inverse enclosure. Integer partial sums are combined exactly. All original matrix entries are still checked. The nonsingular correction definition already guarantees Ax=b, so recomputing A x₀ only to display its residual is unnecessary for acceptance and is omitted in the parallel path. Small checks retain the serial implementation.

The following cold checker-only measurements recheck retained development certificates; they do not repeat LP solves or replace earlier recorded timings. The final cohort below measures the complete updated pipeline on new models.

| Certificate | Serial cold check s | Parallel cold check s | Serial / parallel |
| --- | ---: | ---: | ---: |
| dense-wide-1m | 0.815 | 0.415 | 1.966× |
| dense-wide-4m | 2.417 | 0.865 | 2.794× |
| sparse-wide-1m | 1.216 | 0.765 | 1.588× |

## Experimental protocol

Hardware is the same Intel Xeon Platinum 8457C and NVIDIA RTX PRO 6000 Blackwell Server Edition used previously. COPT is 8.0.6. Each reservation has four CPU slots and a 32 GiB aggregate sampled host envelope; candidate BLAS uses one thread and COPT uses four. Exact parallel checks use three worker processes plus the parent. GPU ownership, physical headroom, idle observations and memory limits remain enforced.

Every solver requests a 60-second native allowance and a 90-second process ceiling. Reconstruction and proof have 90- and 120-second process ceilings. COPT GPU uses LpMethod=6, GPUMode=1, Presolve=0, Crossover=0 and PDLPTol=1e-9, with installed default Scaling and Dualize. COPT CPU uses its automatic method with GPUMode=0 and installed default presolve/scaling. Both vendor lanes use FeasTol=DualTol=1e-9, MatrixTol=0, MemLimit=12000 and Threads=4. These are specified experimental configurations, not an unrestricted claim about vendor defaults.

Complete time is common model generation/encoding plus cold solver process, raw audit, common endpoint recovery and cold independent proof. Solver time includes validation, matrix conversion, native import, library/CUDA setup, preparation, optimization, extraction and teardown. In particular, **COPT preparation is included**, including opaque work inside SolveLp. Construction-witness checks, idle admission and experiment supervision are excluded from solver comparisons and included in resource accounting.

Native optimal status, raw 1e-9 endpoint acceptance and exact reconstruction are distinct. An exact-time ratio requires both reservations to pass, both native attempts to be timely, and both endpoints to pass the same independent exact policy. A native optimal return without an exact certificate is not counted as a certified solve; a deadline never becomes a timely solve through later reconstruction. All denominators retain unsuccessful and missing slots.

Primary seeds are 126101, 126123 and 126149; regression seeds are 126201, 126223 and 126249. The final checker cohort uses 126401, 126423 and 126449; the separate mixed-square supplement uses 126901, 126923 and 126949. Candidate/GPU order rotates; CPU controls run in separate groups with alternating CPU/GPU group order. There is one cold timing per seed and no cache flush. Ranges describe these samples and are not confidence intervals.

Inputs are signed dyadic synthetic LPs with independently checked planted witnesses kept outside solver inputs. Wide inputs have all rows active at the planted optimum; mixed inputs have 20% inactive rows there. Their exact short-dyadic duals favor the bounded reconstruction strategy. “Mixed-active” describes the generated optimum, not a guarantee that every optimum has the same active set.

| Family | Rows × columns | Original nonzeros |
| --- | ---: | ---: |
| dense-wide-1m | 500 × 2,000 | 1,000,000 |
| dense-wide-4m | 1,000 × 4,000 | 4,000,000 |
| sparse-wide-1m | 2,000 × 8,000 | 1,000,000 |
| mixed-square-1m | 1,000 × 1,000 | 1,000,000 |
| mixed-rectangular-1p5m | 1,500 × 1,000 | 1,500,000 |

## Primary cohort with serial implicit-primal checker

Each cell is accepted count / 3 followed by median [minimum, maximum] complete seconds over accepted, timely endpoints. Read durations with their counts; missing entries are not zero runtime.

| Family | Candidate | COPT GPU | COPT CPU auto |
| --- | ---: | ---: | ---: |
| dense-wide-1m | 3/3; 1.874 [1.874, 1.884] | 3/3; 2.826 [2.826, 2.836] | 0/3; — |
| dense-wide-4m | 3/3; 4.863 [4.820, 4.865] | 3/3; 6.317 [6.273, 6.566] | 0/3; — |
| sparse-wide-1m | 3/3; 3.677 [3.675, 3.738] | 3/3; 4.276 [4.228, 4.288] | 0/3; — |
| mixed-square-1m | 3/3; 2.323 [2.275, 2.373] | 3/3; 3.226 [3.224, 3.274] | 3/3; 5.579 [5.478, 5.678] |
| mixed-rectangular-1p5m | 3/3; 4.200 [4.150, 4.351] | 3/3; 3.249 [3.213, 3.348] | 3/3; 14.263 [13.466, 14.568] |

| Family | Eligible GPU pairs / 3; median COPT / candidate | Eligible CPU pairs / 3; median COPT / candidate |
| --- | ---: | ---: |
| dense-wide-1m | 3/3; 1.508× | 0/3; — |
| dense-wide-4m | 3/3; 1.301× | 0/3; — |
| sparse-wide-1m | 3/3; 1.150× | 0/3; — |
| mixed-square-1m | 3/3; 1.388× | 3/3; 2.408× |
| mixed-rectangular-1p5m | 3/3; 0.773× | 3/3; 3.348× |

## Final cohort with parallel implicit-primal checker

Each cell is accepted count / 3 followed by median [minimum, maximum] complete seconds over accepted, timely endpoints. Read durations with their counts; missing entries are not zero runtime.

| Family | Candidate | COPT GPU | COPT CPU auto |
| --- | ---: | ---: | ---: |
| dense-wide-1m | 3/3; 1.527 [1.519, 1.568] | 3/3; 2.469 [2.468, 2.528] | 0/3; — |
| dense-wide-4m | 3/3; 3.281 [3.239, 3.292] | 3/3; 4.782 [4.683, 4.941] | 0/3; — |
| sparse-wide-1m | 3/3; 3.268 [3.229, 3.320] | 3/3; 3.819 [3.769, 3.829] | 0/3; — |
| mixed-square-1m | 0/3; — | 0/3; — | 3/3; 5.070 [5.070, 5.171] |
| mixed-rectangular-1p5m | 3/3; 4.336 [4.189, 4.337] | 3/3; 3.235 [3.189, 3.286] | 3/3; 14.414 [13.000, 14.955] |

| Family | Eligible GPU pairs / 3; median COPT / candidate | Eligible CPU pairs / 3; median COPT / candidate |
| --- | ---: | ---: |
| dense-wide-1m | 3/3; 1.625× | 0/3; — |
| dense-wide-4m | 3/3; 1.453× | 0/3; — |
| sparse-wide-1m | 3/3; 1.154× | 0/3; — |
| mixed-square-1m | 0/3; — | 0/3; — |
| mixed-rectangular-1p5m | 3/3; 0.758× | 3/3; 3.323× |

## Failed finalization and separate mixed-square supplement

The final mixed-square GPU group wrote all six numerical results and accepting proofs, then supervision failed during finalization with `coordinator_lost`. All six timings are excluded, and the full 600 CPU / 150 GPU seconds remain charged. Cleanup was empty and no overrun occurred. A separately supervised read-only seal verifies the original sources, completed results and absence of all recorded owned identities; it neither recomputes nor regrades the failed group. The preceding failure trigger is unknown. A bounded exit wait now observes an actual completed owned inventory cycle before returning; an inventory race is a hypothesis, not an established cause.

Only the two untouched rectangular groups continued. The following separately frozen new mixed-square seeds provide fresh timing coverage with the same solver, vendor settings and parallel checker. They do not replace the failed slots or repair their timing eligibility.

| Supplement family | Candidate | COPT GPU | COPT CPU auto |
| --- | ---: | ---: | ---: |
| mixed-square-1m | 3/3; 1.875 [1.874, 1.935] | 3/3; 2.786 [2.726, 2.826] | 3/3; 5.229 [5.130, 5.290] |

COPT GPU supplement: 3/3 eligible pairs; median COPT / candidate 1.454×.

COPT CPU auto supplement: 3/3 eligible pairs; median COPT / candidate 2.737×.

## Square and irregular regression controls

These paired runs use identical new inputs and the old versus new candidate. Their explicit certificates must match exactly. The final parallel checker affects only implicit-primal certificates and is not invoked on these explicit-success paths; the numerical candidate and common postprocessor are identical across the two new focus cohorts.

| Family | Old complete median [range] s | New complete median [range] s | Median new / old complete | Median new / old native | Identical accepted certificates |
| --- | ---: | ---: | ---: | ---: | ---: |
| dense-square-4m | 4.912 [4.817, 4.921] | 4.863 [4.818, 4.921] | 1.000× | 0.942× | 3/3 |
| irregular-square-1m | 6.532 [6.519, 6.620] | 6.520 [6.233, 6.622] | 1.000× | 0.995× | 3/3 |

## Direct rectangular GPU refinement

The initial mixed rectangular path spent about 0.67 seconds in an unsuccessful CPU LSMR presolve before GPU projection. A final opt-in dispatcher skips that work only for n<m<2n within the existing dimension limits. Every other shape delegates to the preceding implementation. The CUDA kernel, stopping threshold, exact postprocessor and independent proof are unchanged.

The first refinement development wrapper failed after its baseline solve because it tried to recreate the common harness’s existing result file. Its baseline timing is excluded and the full 600 CPU / 150 GPU-second charge remains. The other four planned configurations never started. An additive wrapper writes configuration metadata separately, verifies cleanup and prior sources, and uses a new development seed. A prospective transfer moves 150 unused GPU admission seconds into development within unchanged totals and the original deadline.

A prospectively bounded development experiment uses one new input (seed 127021), with the preceding candidate and four direct GPU penalty multipliers. Selection requires a timely exact certificate and at least a 10% complete-cost reduction versus the preceding candidate; all alternatives remain in the table. These development timings select a configuration, not a general performance claim.

| Development configuration | Exact accepted | GPU updates | Proposal region s | Complete s |
| --- | ---: | ---: | ---: | ---: |
| candidate-before | True | 1900 | 1.437 | 4.304 |
| candidate-rho-16 | True | 1900 | 1.438 | 3.554 |
| candidate-rho-64 | True | 2100 | 1.520 | 3.654 |
| candidate-rho-256 | True | 2500 | 1.703 | 3.865 |
| candidate-rho-1024 | True | 3000 | 1.943 | 4.105 |

The frozen choice is rho multiplier **16**. The measured final entry point is `tools/lp_sp_pricing_rectangular_run.py --wide-backend cpu --rho-multiplier 16`. This remains opt-in; retained public defaults and earlier studies are unchanged.

After the nine GPU-group slots completed successfully, the driver detected that its planned CPU reservation identity was already used by the admission job. It stopped before launching any CPU/control cell. A separately supervised continuation verifies the original completed GPU group and sources, and runs only the two untouched groups under fresh reservation names. The original driver is never rerun.

Holdout seeds 127301, 127323 and 127349 compare preceding/new candidates and both COPT lanes. All complete times include the same original encoding, cold preparation, raw audit, common endpoint recovery and independent proof. These new measurements are separate from the preceding rectangular cohorts.

| Rectangular holdout lane | Exact accepted / 3 | Complete median [range] s |
| --- | ---: | ---: |
| Preceding candidate | 3/3 | 4.146 [4.056, 4.195] |
| Candidate | 3/3 | 3.455 [3.445, 3.695] |
| COPT GPU | 3/3 | 3.269 [3.255, 3.344] |
| COPT CPU auto | 3/3 | 14.260 [14.020, 14.362] |

Old/new exact pairs: 3/3; median preceding / new 1.174×.

COPT GPU exact pairs: 3/3; median COPT / new 0.946×.

COPT CPU auto exact pairs: 3/3; median COPT / new 4.057×.

Two additional square/irregular controls (seeds 127401 and 127403) check the final dispatcher on new inputs. These are one pair per family, supplementary to the three primary pairs per family; they are not a statistical latency guarantee.

| Final dispatcher control | New / preceding complete | Identical accepted certificate |
| --- | ---: | ---: |
| dense-square-4m | 1.000× | True |
| irregular-square-1m | 0.978× | True |

Both families pass the prespecified no-lost-certificate, identical-certificate and ≤10% median complete-time regression checks. This supports preservation on the measured cases; it is not a universal latency guarantee. Existing tall and larger sparse-square dispatch remains unchanged by source construction.

## Second-cohort phase costs and unsuccessful slots

Phase medians below describe the second cohort and include all supervision-eligible returned attempts, including deadlines; they diagnose cost and are not themselves certified speedup ratios. Independent phase medians need not sum to the median complete cost.

| Family and lane | Encoding s | Solver process s | Raw audit s | Reconstruction s | Independent proof s |
| --- | ---: | ---: | ---: | ---: | ---: |
| dense-wide-1m / Candidate | 0.048 | 0.364 | 0.075 | 0.615 | 0.416 |
| dense-wide-1m / COPT GPU | 0.048 | 1.316 | 0.074 | 0.615 | 0.416 |
| dense-wide-1m / COPT CPU auto | 0.048 | 60.601 | 0.000 | 0.000 | 0.000 |
| dense-wide-4m / Candidate | 0.207 | 0.615 | 0.225 | 1.317 | 0.878 |
| dense-wide-4m / COPT GPU | 0.207 | 2.067 | 0.225 | 1.317 | 0.867 |
| dense-wide-4m / COPT CPU auto | 0.207 | 60.810 | 0.000 | 0.000 | 0.000 |
| sparse-wide-1m / Candidate | 0.046 | 0.765 | 0.074 | 1.567 | 0.767 |
| sparse-wide-1m / COPT GPU | 0.046 | 1.316 | 0.074 | 1.567 | 0.767 |
| sparse-wide-1m / COPT CPU auto | 0.046 | 61.747 | 0.000 | 0.000 | 0.000 |
| mixed-square-1m / Candidate | — | — | — | — | — |
| mixed-square-1m / COPT GPU | — | — | — | — | — |
| mixed-square-1m / COPT CPU auto | 0.045 | 3.669 | 0.074 | 0.816 | 0.466 |
| mixed-rectangular-1p5m / Candidate | 0.064 | 2.567 | 0.075 | 0.916 | 0.665 |
| mixed-rectangular-1p5m / COPT GPU | 0.064 | 1.566 | 0.075 | 0.866 | 0.617 |
| mixed-rectangular-1p5m / COPT CPU auto | 0.064 | 12.782 | 0.075 | 0.866 | 0.616 |

| Second-cohort lane | Native optima | Raw accepted | Exact accepted | Timings excluded |
| --- | ---: | ---: | ---: | ---: |
| Candidate | 0/15 | 0/15 | 12/15 | 3 |
| COPT GPU | 12/15 | 0/15 | 12/15 | 3 |
| COPT CPU auto | 6/15 | 0/15 | 6/15 | 0 |

The candidate labels new factor endpoints as numerical proposals pending the common proof, so its native-optimal count is not an acceptance criterion.

| Second-cohort lane | Unsuccessful exact disposition | Count |
| --- | --- | ---: |
| Candidate | numerical_proposal: supervision failed; timing excluded | 3 |
| COPT GPU | native optimum: supervision failed; timing excluded | 3 |
| COPT CPU auto | interrupted: no accepted exact certificate | 6 |
| COPT CPU auto | time limit: no accepted exact certificate | 3 |

## Validation, limits and reproducibility

The new proof is tested against independent Fraction Gaussian elimination, including an explicitly non-dyadic primal. Corrupted duals, singular/invalid bases, invalid inverses, noncanonical CSR and nonfinite inputs are rejected. Serial and parallel original-model checks agree on small exact cases, and the large checker profile independently accepts each retained development certificate. The final full regression suite contains 137 tests. The new CUDA kernel has four complete sanitizer passes and CPU/GPU numerical comparisons.

The report hash-checks every retained reference and all new original input arrays, verifies every accepted proof’s original-model binding and full nonzero count, and checks the old/new explicit certificates. All prior failed reservations and scientific rejections remain retained and charged. The first sparse-wide development certificates were rejected; their results are not regraded by the later balanced-basis success.

Remaining restrictions matter: recovery requires full row rank and a reconstructible nonnegative exact dyadic dual; normal equations may be ill-conditioned; the dense inverse certificate limits row dimension; and sparse normal factors can fill. The initial mixed rectangular recovery pays for bounded CPU LSMR before GPU projection; the final refinement described above removes it only in that rectangular interval. Both use the earlier implicit-dual proof. The new synthetic inputs do not establish behavior on arbitrary real-world, infeasible, unbounded or strongly degenerate LPs.

The outcomes establish targeted practical improvements and measured regression preservation. They do not establish general superiority over COPT or a complete strongly polynomial implementation. Historical failed candidate solves are not used as speedup denominators, and cohorts with different seeds/checkers are not pooled into a single speed ratio.

[All comparison slots](lp-sp-pricing-recovery-comparison.csv), [structured evidence](lp-sp-pricing-recovery-results.json), and the [settled checkpoint](lp-sp-pricing-recovery-checkpoint.json) retain individual settings, costs, proofs and supervision. The unchanged cumulative ceilings are 240000 CPU and 30000 GPU seconds, including all preceding work and full failed charges. The current follow-up uses a fresh two-hour envelope; the checkpoint records actual elapsed time and absence of active owned work.
