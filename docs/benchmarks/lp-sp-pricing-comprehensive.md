# Certified LP solver implementation and performance

The implementation solves canonical linear programs of the form `maximize cᵀx subject to Ax≤b`, with free variables, using numerical proposals followed by independent exact optimality certificates. Dense and sparse square or wide problems use CPU factorization; eligible rectangular and tall problems use resident FP64 GPU projection. The certificate proves feasibility and zero gap on the original model.

The fresh three-seed scaled-tall evaluation produces **6/6 timely certified candidate solutions**, with lower median complete cost than COPT GPU in **0/2 families**. Complete cost includes model encoding, cold preparation, solving, endpoint construction and independent certification. The other matrix shapes retain their stated measurements and receive separate preservation checks.

The results concern the stated synthetic dyadic problems and solver configurations. This practical hybrid includes bounded pricing components and certified presolve; it does not establish a completed literal strongly polynomial implementation or general superiority over COPT.

## Final implementation

The solver is motivated by [Strongly Polynomial Linear Programming](https://github.com/openai/math/blob/main/preprints/Strongly-polynomial-linear-programming-November-24-2026/paper.pdf). Reference modules implement paired-cone price queries, compressed calibration and witness recovery. The practical pricing fallback uses input-height calibration, bounded expert populations and query counts, and exact restricted-cone recovery. These bounded choices do not inherit the paper’s strongly polynomial guarantee. The factor-recovery paths described below can establish an optimum directly and are the paths exercised by the successful large-case comparisons.

The numerical entry point is `tools/lp_sp_pricing_pipeline_lazy_run.py --wide-backend cpu --inverse-backend cpu`. Its output is a proposal, not a trusted certificate. `tools/lp_sp_pricing_final_endpoint.py` applies the common endpoint policy, and the checker selected by certificate type determines acceptance. All vendor endpoints receive the same construction policy and checker.

| Matrix case | Numerical work | Certificate |
| --- | --- | --- |
| Dense square | LAPACK LU reused for primal and transposed dual solves | Explicit exact endpoint when recoverable; otherwise implicit primal recovery within its dimension limit |
| Sparse square and irregular | Sparse LU and transposed solve | Explicit original-model certificate; sparse fill controls factor cost |
| Full-row-rank wide | Form AAᵀ with dense BLAS or sparse products; reuse a factor for b and Ac; recover x with Aᵀ | Implicit full-row primal plus an exact nonnegative dual |
| Mixed rectangular and tall | Resident Cholesky factor of AᵀA; batched FP64 projection; power-of-two row balancing where applicable | Exact active primal and implicit dual correction |
| Outside supported recovery domains | Existing bounded exact geometry, pricing and auxiliary-search path | Independent certificate required; a resource limit is not a mathematical LP outcome |

Wide proposals require m≤4096 and mn≤2²⁷. Rectangular/tall projection requires n≤4096 and mn≤2²⁷. Large sparse-square factorization follows its existing sparse path. Unsupported rank, coefficient range or reconstruction can make recovery inconclusive even when the LP has an optimum.

### Rectangular and tall GPU projection

Each iteration solves `Gx=Aᵀ(b−s−u)+c/ρ`, where `G=AᵀA`, then projects the slack and updates the scaled multiplier. G is factored in place; its Cholesky factor, A and the iteration state stay on GPU. Checkpoints occur every 100 updates. The penalty uses the documented norm scale multiplied by 16, and the update ceiling is 6000.

Rows with a large norm spread are balanced by powers of two before numerical projection. The dual is mapped back to the original coordinates, and every certificate is checked against the original A, b and c. On the supported dyadic test range these scalings are exact; the final proof never relies on transformed-model residuals alone.

For mixed rectangular cases, a promising checkpoint triggers exact primal recovery and a screened dual correction. An early stop requires a complete exact check, followed by a separate cold independent check of the published certificate. Ordinary unscaled tall cases retain the stringent numerical stopping rule.

Scaled tall cases use a bounded correction pipeline. One worker receives an immutable primal/dual snapshot while the main thread continues GPU projection in batches of 100 updates. The worker decodes the original dyadic model once, recovers an exactly feasible primal, and lazily constructs one active-basis inverse proposal. Later snapshots reuse that inverse while its rows remain exactly active and have positive dual-base entries. A changed active set invalidates the cache; a failed inverse construction can try the alternate basis. Negative corrections are screened using sparse products and matrix-vector multiplication, without refactoring at every checkpoint.

The worker runs the unchanged independent exact check when a correction is promising. The solver accepts only the checked snapshot, even if GPU projection has advanced further. There is at most one pending correction and one resident cached inverse. A failed pending check at numerical termination is followed by a check of the latest snapshot. Worker shutdown, speculative GPU updates, failed trials and every inverse allocation are included in complete time.

The selected configuration constructs the cached inverse on CPU while GPU projection continues. A cuSOLVER inverse option is implemented and independently validated. Its summed complete development cost was 3.97% lower across the two tested sizes, below the predefined 5% threshold for selecting that backend; the reported holdouts therefore use CPU construction. This is a limited configuration choice, not a claim that CPU inversion is universally faster.

The correction worker can use three BLAS threads alongside the main projection thread, within four CPU slots. The thread setting is scoped and restored. CUDA inverse construction uses the existing library path; no simultaneous-kernel throughput or transfer overlap is inferred from host timing. Other shapes delegate to the same numerical and certificate paths as before.

### Exact host work

Certificate construction decodes the IEEE significand and exponent to find the shared dyadic exponent, then converts the matrix once. It avoids a succession of full-array rescalings. The cached inverse is reused for correction refinement across eligible snapshots; no floating proposal is itself an acceptance decision.

The implicit-dual checker validates canonical CSR and scans every original nonzero. It computes exact sparse integer products using signed limbs. Before each product, a bound on the sum of absolute terms proves that all multiplications and partial sums stay below 2⁶². Limb results are combined with unbounded Python integers. Inputs outside those bounds use the arbitrary-integer fallback. The CPU inverse enclosure remains independent of the constructor.

Dedicated implicit-dual construction and checking processes can use four BLAS threads, with no simultaneous integer-scan worker pool. The implicit-primal checker uses three integer workers while the parent computes the enclosure. Explicit certificates retain their original checker. These paths fit the four allocated CPU slots.

### Memory and concurrency

The GPU projection stores roughly mn+n² FP64 matrix entries plus vectors and library workspaces; its current implementation densifies A. At 16000×4000, those matrix terms occupy about 0.596 GiB. Sparse-wide CPU recovery retains sparse normal factors, but its certificate still contains a dense m×m inverse proposal. Scaled-tall correction adds at most one n×n cached host inverse, plus bounded snapshot vectors. These quadratic objects limit supported dimensions even when the input is sparse.

Recovery avoids a full rational null-space basis. The pricing fallback retains lazy CPU tableau construction, tiled products and checks, bounded synchronized auxiliary batches, reusable allocations and transfer/compute overlap. These mechanisms bound workspace and share GPU work when searches are needed; accepted factor-recovery paths bypass those searches. The reported fast paths use FP64 proposals, not a claim of packed low-precision tensor-core throughput.

## Certificate definitions

For a wide system, choose m columns J and let B=A[:,J]. The certificate defines `x=x₀+E_Jδ`, where `Bδ=b−Ax₀`. An independent enclosure proving ‖I−RB‖∞<1 establishes nonsingularity and therefore exact primal feasibility. A full integer scan proves `Aᵀy=c` and `y≥0`; all rows are active at the defined primal, giving zero gap. The corrected primal need not have short dyadic coordinates.

For a rectangular/tall system, the checker proves that a recovered dyadic primal is feasible and that the dual base y₀ is supported only on exactly active rows. With B formed from n selected active rows, it defines `y=y₀+E_Jδ` by `Bᵀδ=c−Aᵀy₀`. Exact stationarity residuals and the independent inverse-norm enclosure bound δ. A correction no larger than the selected positive dual margin proves dual nonnegativity and zero gap.

Inverse enclosures assume standard IEEE FP64 BLAS roundoff and require nearest CPU rounding. Raw numerical status, the original conservative 1e-9 endpoint audit and exact reconstructed certificates are separate quantities. A missing finite raw bound is not proof of a wrong numerical optimum. All performance ratios below use timely independently accepted exact certificates.

## Evaluation method

Measurements were made on November 26, 2026 with an Intel Xeon Platinum 8457C and NVIDIA RTX PRO 6000 Blackwell Server Edition, using COPT 8.0.6. Reservations use four CPU slots and a 32 GiB sampled aggregate host envelope. Candidate proposal BLAS normally uses one thread; the scaled-tall worker uses three while projection continues. Dedicated cold implicit-dual construction/checking and COPT use up to four. GPU ownership, memory and idle admission checks remain enforced.

COPT GPU uses LpMethod=6, GPUMode=1, Presolve=0, Crossover=0 and PDLPTol=1e-9, with installed default Scaling and Dualize. COPT CPU uses its automatic method, GPUMode=0 and installed default presolve/scaling. Both use FeasTol=DualTol=1e-9, MatrixTol=0 and MemLimit=12000. These are specified configurations rather than unrestricted claims about COPT’s best achievable settings.

Each solver has a 60-second native allowance and a 90-second process ceiling. Construction and independent proof have 90- and 120-second process ceilings. Complete cost includes shared original-model generation/encoding, cold solver process, raw audit, common construction and cold proof. Import, conversion, allocations, transfers, CUDA/library initialization and teardown are included. COPT preparation, including opaque work inside SolveLp, is included. Construction-witness validation and experiment supervision are research overhead outside solver timings.

Inputs are signed dyadic synthetic models with independently checked planted feasible and complementary witnesses withheld from solvers. Mixed cases have 20% inactive rows at the planted optimum; another optimum can have a different active set. Scaled families apply row factors from 2⁻⁴ through 2⁴. The short-dyadic planted witnesses favor these reconstruction paths. The objective is bounded, while the feasible region need not be. Million scale means original nonzeros, not millions of variables.

There is one cold run per solver and seed, three independent holdout seeds per scaled-tall family and no cache flushing. Candidate/GPU order rotates; COPT CPU runs in a separate CPU-only group. Fresh scaled-tall seeds are 129101, 129123 and 129149; CPU preservation seeds are 129201, 129223 and 129249. The holdout study contains 54 solver attempts on 21 models: six scaled-tall models against the reference candidate and COPT GPU/CPU, plus fifteen paired CPU preservation models. Three separate unscaled GPU preservation models add six attempts. Those GPU preservation cases precede the holdouts and are reported as such.

Other-shape measurements below use preserved numerical and certificate paths. Each candidate/COPT pair uses the same original model and common certificate policy. Timings from different cohorts are not combined into one speed ratio. GPU preparation, CPU correction work, all failed attempts within a solve, worker drain and final certification are charged. Construction-witness validation and experiment supervision remain outside solver comparisons.

## Fresh scaled-tall comparisons

Cells show timely certified count / attempted count, followed by median [minimum, maximum] complete seconds. A dash means no eligible certified time. Native deadlines remain unsuccessful even if later reconstruction can prove an endpoint.

| Family | Shape; nonzeros | Candidate | COPT GPU | COPT CPU auto |
| --- | --- | ---: | ---: | ---: |
| mixed-scaled-tall-1m | 4,000 × 1,000; 1,000,000 | 3/3; 2.770 [2.721, 2.979] | 3/3; 2.431 [2.371, 2.578] | 0/3; — |
| mixed-scaled-tall-4m | 8,000 × 2,000; 4,000,000 | 3/3; 5.408 [5.295, 5.450] | 3/3; 4.446 [4.403, 4.504] | 0/3; — |

| Family | Eligible GPU pairs / 3 | Median COPT GPU / candidate | Eligible CPU pairs / 3 | Median COPT CPU / candidate |
| --- | ---: | ---: | ---: | ---: |
| mixed-scaled-tall-1m | 3/3 | 0.872× | 0/3 | — |
| mixed-scaled-tall-4m | 3/3 | 0.816× | 0/3 | — |

## Unscaled rectangular and tall cases

These retained three-seed measurements exercise the preserved numerical path. Fresh preservation comparisons below test the new dispatch.

| Family | Shape; nonzeros | Candidate | COPT GPU | COPT CPU auto |
| --- | --- | ---: | ---: | ---: |
| mixed-rectangular-1p5m | 1,500 × 1,000; 1,500,000 | 3/3; 2.493 [2.351, 2.552] | 3/3; 2.802 [2.751, 2.893] | 3/3; 13.659 [13.568, 16.272] |
| mixed-tall-1m | 4,000 × 1,000; 1,000,000 | 3/3; 2.216 [2.216, 2.269] | 3/3; 2.369 [2.316, 2.416] | 1/3; 52.094 [52.094, 52.094] |
| mixed-tall-4m | 8,000 × 2,000; 4,000,000 | 3/3; 3.742 [3.737, 3.789] | 3/3; 4.438 [4.388, 4.493] | 0/3; — |
| mixed-tall-16m | 16,000 × 4,000; 16,000,000 | 3/3; 11.579 [11.069, 11.665] | 3/3; 14.765 [14.522, 15.022] | 0/3; — |

## Other matrix shapes

These retained measurements exercise the preserved square/wide paths. Acceptance counts include deadlines and failed exact recovery; unsuccessful cases are not silently removed.

| Family | Shape; nonzeros | Candidate | COPT GPU | COPT CPU auto |
| --- | --- | ---: | ---: | ---: |
| dense-wide-1m | 500 × 2,000; 1,000,000 | 3/3; 1.527 [1.519, 1.568] | 3/3; 2.469 [2.468, 2.528] | 0/3; — |
| dense-wide-4m | 1,000 × 4,000; 4,000,000 | 3/3; 3.281 [3.239, 3.292] | 3/3; 4.782 [4.683, 4.941] | 0/3; — |
| sparse-wide-1m | 2,000 × 8,000; 1,000,000 | 3/3; 3.268 [3.229, 3.320] | 3/3; 3.819 [3.769, 3.829] | 0/3; — |
| mixed-square-1m | 1,000 × 1,000; 1,000,000 | 3/3; 1.875 [1.874, 1.935] | 3/3; 2.786 [2.726, 2.826] | 3/3; 5.229 [5.130, 5.290] |
| dense-square-4m | 2,000 × 2,000; 4,000,000 | 3/3; 5.186 [5.037, 5.485] | 1/3; 63.701 [63.701, 63.701] | 3/3; 35.161 [31.118, 35.203] |
| banded-square-4m | 16,000 × 16,000; 4,000,000 | 3/3; 8.691 [8.632, 8.795] | 0/3; — | 0/3; — |
| irregular-square-1m | 4,000 × 4,000; 1,000,000 | 3/3; 6.480 [5.913, 6.516] | 2/3; 16.250 [14.875, 17.625] | 0/3; — |
| scaled-square-1m | 8,000 × 8,000; 1,000,000 | 3/3; 2.727 [2.678, 2.732] | 1/3; 23.552 [23.552, 23.552] | 0/3; — |

## Cost diagnosis

The following phase medians describe the final scaled-tall pipeline. Independent medians need not sum to median complete time. Solver-process time includes imports, setup and worker shutdown; it is not kernel-active GPU time.

| Family and lane | Encoding s | Solver process s | Raw audit s | Construction s | Independent proof s |
| --- | ---: | ---: | ---: | ---: | ---: |
| mixed-scaled-tall-1m / Candidate | 0.049 | 1.816 | 0.074 | 0.415 | 0.416 |
| mixed-scaled-tall-1m / COPT GPU | 0.049 | 1.316 | 0.074 | 0.576 | 0.417 |
| mixed-scaled-tall-4m / Candidate | 0.222 | 3.623 | 0.224 | 0.416 | 0.917 |
| mixed-scaled-tall-4m / COPT GPU | 0.222 | 2.117 | 0.225 | 1.066 | 0.817 |

| Candidate family | Median total updates | Certificate snapshot update | Inverses built | Correction worker s | Worker/advance overlap s |
| --- | ---: | ---: | ---: | ---: | ---: |
| mixed-scaled-tall-1m | 1300 | 1300 | 1 | 0.180 | 0.086 |
| mixed-scaled-tall-4m | 2100 | 1900 | 1 | 0.969 | 0.602 |

Overlap is the intersection of correction-worker wall intervals with host-observed GPU advance calls. It is not a measurement of simultaneous GPU kernels, and worker time must not be added to complete time.

The repeated work is reduced by reusing an inverse across snapshots and screening with sparse products and matrix-vector multiplication. The remaining host cost includes exact primal recovery, full original-model integer scans and the CPU inverse enclosure. The final cold proof is still mandatory. Overlap can advance the GPU beyond the snapshot that ultimately certifies; those extra updates are charged.

mixed-scaled-tall-1m: candidate 2.770 versus COPT GPU 2.431 complete seconds; COPT retains the lower median cost.
mixed-scaled-tall-4m: candidate 5.408 versus COPT GPU 4.446 complete seconds; COPT retains the lower median cost.

For unscaled tall cases, inverse construction and the independent dense enclosure remain cubic CPU work as the column dimension grows. Input handling and exact scans scale with original nonzeros. Wide recovery avoids rational geometry and market search through an implicit full-row certificate, while sparse factor fill and the dense inverse proposal remain possible limits.

## Validation and practical limits

All **18/18 preservation pairs** retain exact acceptance. The fifteen CPU pairs cover dense-wide, sparse-wide, mixed-square, dense-square and irregular-square cases. Their explicit certificates match exactly where present. Three separate GPU pairs cover mixed rectangular, unscaled 4M tall and unscaled 16M tall; all retain identical numerical endpoints and iteration counts. The largest family median current/reference complete-time ratio is 1.091×, within the predefined 1.10 limit.

The 16M GPU preservation pair records a 9.1% complete-time increase. Both cold solver processes take 3.569 seconds; the difference is in the common, unchanged construction and proof processes. This single-pair timing variation is retained and is not evidence of identical end-to-end timing. Other numerical paths and exact acceptance are preserved.

The full regression suite contains 156 tests. Tests cover exponent decoding, signed integer products beyond 64 bits, malformed CSR, altered certificates, cache invalidation, scoped thread restoration, bounded overlap and stale-snapshot shutdown. Twelve CPU/GPU continuation comparisons run concurrently with GPU inverse proposals and pass independent inverse enclosures. The existing CUDA sources and exact checker are unchanged, with their source-bound sanitizer evidence retained.

Every included comparison verifies original input hashes, source/proof bindings and complete nonzero counts. Native status, raw 1e-9 audit and exact reconstructed acceptance remain separate. Every development outcome, deadline and failure remains in the evidence.

Recovery requires a suitable rank profile and a recoverable exact primal or dual representation. Normal equations can be ill-conditioned, sparse factors can fill, and the inverse certificate imposes a quadratic storage and cubic work cost. The experiments do not establish large-scale behavior on arbitrary real-world, infeasible, unbounded or highly degenerate LPs. Three seeds support these measured comparisons, not a universal performance guarantee.

[Complete comparison data](lp-sp-pricing-pipeline-comparison.csv), [settings, proofs and source bindings](lp-sp-pricing-pipeline-results.json), and the [settled validation checkpoint](lp-sp-pricing-pipeline-checkpoint.json) provide the reproducible evidence.

## Billion-nonzero evaluation scope

The [billion-nonzero first-pass report](lp-sp-pricing-billion-first-pass.md) records CPU-validated dense-wide, mixed-active tall and near-dense square inputs with exactly one billion original nonzeros. GPU admission and all candidate/COPT solves are deferred at the user’s request. These input checks do not establish solver performance or extend the smaller-scale speed ratios above.
