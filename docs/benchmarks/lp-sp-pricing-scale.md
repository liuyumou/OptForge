# Larger-scale LP evaluation and certificate assurance

Thirteen fresh models contain 4–16 million nonzeros each. The primary roster has two independent seeds across five families and three solver lanes, for thirty slots with 120 native / 150 process seconds per solver. A separately frozen third seed covers three families with 300 native / 360 process seconds, adding nine slots. All thirty-nine slots, deadlines and missing endpoints remain visible.

See the [complete results](lp-sp-pricing-scale-results.json), [all thirty-nine cells](lp-sp-pricing-scale-comparison.csv), [settled checkpoint](lp-sp-pricing-scale-checkpoint.json), and [preceding million-scale diagnosis](lp-sp-pricing-geometry.md).

## Outcomes

| Native allowance | Lane | Returned / slots | Vendor numerical optima | Strict accepted | Independent exact accepted | Timely exact with eligible timing |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 120 s | candidate | 10/10 | — | 8 | 8 | 4 |
| 120 s | copt-gpu | 10/10 | 3 | 0 | 0 | 0 |
| 120 s | copt-auto | 10/10 | 2 | 0 | 0 | 0 |
| 300 s | candidate | 3/3 | — | 2 | 2 | 2 |
| 300 s | copt-gpu | 3/3 | 1 | 0 | 0 | 0 |
| 300 s | copt-auto | 3/3 | 0 | 0 | 0 | 0 |

A vendor numerical optimum, unchanged original-model 1e-9 acceptance, and independent exact rational acceptance are distinct outcomes. In free-variable models, a small nonzero dual residual can prevent a finite rigorous dual bound. Rejection by a stronger certificate check does not establish that a numerical optimum is wrong.

## Workload and controls

Recorded hardware is Intel(R) Xeon(R) Platinum 8457C and NVIDIA RTX PRO 6000 Blackwell Server Edition; the installed vendor is COPT 8.0.6. The supervisor permits four CPU slots. Candidate BLAS is limited to one thread and COPT is configured for four threads.

| Family | Rows × columns | Nonzeros per input | Structure |
| --- | ---: | ---: | --- |
| dense-4m | 2000 × 2000 | 4,000,000 | all rows active |
| dense-16m | 4000 × 4000 | 16,000,000 | all rows active |
| sparse-4m | 16000 × 16000 | 4,000,000 | all rows active |
| sparse-scaled-10m | 40000 × 40000 | 10,000,000 | row scaling 2^-4 to 2^4 |
| mixed-tall-4m | 8000 × 2000 | 4,000,000 | 20% inactive rows |

Seeds 122301 and 122357 are separate inputs, not repeated timings of the same input. Matrices have signed short-dyadic coefficients, nonuniform planted primal coordinates and dual weights, and a cyclic sparse pattern where applicable. Construction witnesses pass the original strict checker and are never passed to the solvers. Eight inputs are square and all-active; two are rectangular with inactive inequalities. This structure can favor exact reconstruction.

The longer-window supplement uses fresh seed 122419 for dense-16m, sparse-scaled-10m and mixed-tall-4m. It was added after some primary outcomes were visible, to allow longer completion attempts on the larger dense/sparse and rectangular families. Candidate code and vendor settings remain unchanged. It repeats no attempted LP. Its 300-second results remain a separate cohort; medians and claims are not pooled across different deadlines.

The candidate uses the new guarded certificate boundary with the previously admitted numerical code. Its exact-certified factor presolve runs on CPU; a successful presolve does not initialize CUDA. Unsuccessful presolve proceeds to the existing GPU-capable geometry/pricing path under unchanged operation, fill and arithmetic limits. This is an opt-in practical candidate, not evidence that the full paper algorithm is implemented or strongly polynomial.

COPT GPU uses the retained scale-off GPU-PDLP configuration: LpMethod=6, Presolve=0, Scaling=0, Crossover=0, PDLPTol=1e-12. COPT auto uses automatic CPU LP-method selection and the installed default presolve, scaling, dualization and crossover. Both are configured for four CPU threads, unchanged original coefficients, MatrixTol=0 and 1e-9 primal/dual tolerances. Exact returned parameters and defaults are retained. Candidate/GPU-COPT order alternates across families and seeds; CPU-auto runs in separate groups. Candidate BLAS remains single-threaded under the existing supervisor. No settings were retuned after new outcomes were observed.

## Complete timings

Operational complete time includes common model encoding, cold process startup, input/hash checks, CSR conversion, factorization or GPU preparation, solving, internal certificate work, endpoint writing, teardown, and the unchanged cold strict audit. Fully audited time additionally includes a separate cold arbitrary-precision certificate process. COPT internal GPU setup remains within its opaque solve call. Resource admission, idle observations and settlement are charged separately; corruption challenges are additional research validation and excluded from both timings.

Times for unsuccessful cells are time to their recorded disposition, not certified solution times. There is one cold process per input/lane, without cache flushing. The model encoding measurement is shared consistently across all three lanes for that input.

The second candidate/GPU group wrote all ten process results and its completion marker, but final resource supervision failed with `coordinator_lost`. Its full 6240 CPU / 1560 GPU-second charge remains, with empty cleanup and no recorded overrun. A separately supervised read-only seal verifies retained records and recorded process absence; it does not regrade supervision. The preceding cause is unknown. All ten timings remain descriptive and are excluded from timely certified counts and every raw/reconstructed speedup ratio. Their mathematical certificates still require the complete independent audits. The separate second-seed automatic-CPU controls are unaffected.

| Family | Seed | Allowance s | Lane | Result | Native s | Operational complete s | Fully audited s | Timely strict / exact |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- |
| dense-4m | 122301 | 120 | candidate | certificate_returned | 0.673 | 1.669 | 3.737 | True / True |
| dense-4m | 122301 | 120 | copt-gpu | interrupted | 120.036 | 121.153 | 121.153 | False / False |
| dense-4m | 122301 | 120 | copt-auto | numerical optimum | 26.082 | 27.307 | 29.526 | False / False |
| dense-16m | 122301 | 120 | copt-gpu | interrupted | 120.051 | 123.112 | 123.112 | False / False |
| dense-16m | 122301 | 120 | candidate | certificate_returned | 5.573 | 8.688 | 17.915 | True / True |
| dense-16m | 122301 | 120 | copt-auto | time limit | 121.701 | 124.543 | 124.543 | False / False |
| sparse-4m | 122301 | 120 | candidate | certificate_returned | 4.244 | 5.376 | 7.644 | True / True |
| sparse-4m | 122301 | 120 | copt-gpu | interrupted | 120.035 | 121.093 | 121.094 | False / False |
| sparse-4m | 122301 | 120 | copt-auto | time limit | 121.291 | 122.328 | 122.328 | False / False |
| sparse-scaled-10m | 122301 | 120 | copt-gpu | interrupted | 120.046 | 122.141 | 122.141 | False / False |
| sparse-scaled-10m | 122301 | 120 | candidate | certificate_returned | 14.175 | 16.504 | 22.877 | True / True |
| sparse-scaled-10m | 122301 | 120 | copt-auto | time limit | 122.611 | 124.523 | 124.523 | False / False |
| mixed-tall-4m | 122301 | 120 | candidate | resource_limit | 120.572 | 121.393 | 121.394 | False / False |
| mixed-tall-4m | 122301 | 120 | copt-gpu | numerical optimum | 0.933 | 2.211 | 4.679 | False / False |
| mixed-tall-4m | 122301 | 120 | copt-auto | time limit | 129.870 | 130.931 | 130.931 | False / False |
| dense-4m | 122357 | 120 | copt-gpu | numerical optimum | 44.629 | 45.957 | 48.175 | False / False |
| dense-4m | 122357 | 120 | candidate | certificate_returned | 0.656 | 1.600 | 3.718 | False / False |
| dense-4m | 122357 | 120 | copt-auto | numerical optimum | 26.501 | 27.789 | 30.007 | False / False |
| dense-16m | 122357 | 120 | candidate | certificate_returned | 5.637 | 8.675 | 17.752 | False / False |
| dense-16m | 122357 | 120 | copt-gpu | interrupted | 120.046 | 123.000 | 123.000 | False / False |
| dense-16m | 122357 | 120 | copt-auto | time limit | 122.766 | 125.832 | 125.832 | False / False |
| sparse-4m | 122357 | 120 | copt-gpu | interrupted | 120.035 | 121.155 | 121.155 | False / False |
| sparse-4m | 122357 | 120 | candidate | certificate_returned | 4.271 | 5.436 | 7.704 | False / False |
| sparse-4m | 122357 | 120 | copt-auto | time limit | 123.221 | 124.245 | 124.245 | False / False |
| sparse-scaled-10m | 122357 | 120 | candidate | certificate_returned | 14.210 | 16.635 | 22.959 | False / False |
| sparse-scaled-10m | 122357 | 120 | copt-gpu | interrupted | 120.039 | 122.022 | 122.022 | False / False |
| sparse-scaled-10m | 122357 | 120 | copt-auto | time limit | 123.116 | 125.056 | 125.056 | False / False |
| mixed-tall-4m | 122357 | 120 | copt-gpu | numerical optimum | 0.808 | 2.056 | 4.524 | False / False |
| mixed-tall-4m | 122357 | 120 | candidate | resource_limit | 120.573 | 121.394 | 121.394 | False / False |
| mixed-tall-4m | 122357 | 120 | copt-auto | time limit | 124.047 | 125.058 | 125.058 | False / False |
| dense-16m | 122419 | 300 | candidate | certificate_returned | 5.798 | 8.992 | 18.020 | True / True |
| dense-16m | 122419 | 300 | copt-gpu | interrupted | 300.058 | 303.201 | 303.201 | False / False |
| dense-16m | 122419 | 300 | copt-auto | time limit | 302.619 | 305.583 | 305.583 | False / False |
| sparse-scaled-10m | 122419 | 300 | copt-gpu | interrupted | 300.043 | 301.975 | 301.975 | False / False |
| sparse-scaled-10m | 122419 | 300 | candidate | certificate_returned | 14.217 | 16.556 | 22.929 | True / True |
| sparse-scaled-10m | 122419 | 300 | copt-auto | time limit | 305.580 | 307.470 | 307.470 | False / False |
| mixed-tall-4m | 122419 | 300 | candidate | resource_limit | 300.686 | 301.526 | 301.527 | False / False |
| mixed-tall-4m | 122419 | 300 | copt-gpu | numerical optimum | 2.321 | 3.649 | 6.067 | False / False |
| mixed-tall-4m | 122419 | 300 | copt-auto | time limit | 301.086 | 302.103 | 302.103 | False / False |

There are 0/26 jointly timely strict pairs and 0/26 jointly timely exact pairs in the raw-endpoint comparison. Ratios are retained only at their corresponding common acceptance tier; failures and time limits do not become speedup ratios.

## Common endpoint reconstruction

Raw COPT endpoints and the candidate do not use the same certificate representation. A separately frozen, post-hoc diagnostic therefore applies the candidate's same bounded dyadic quantization ladder (exponents 0–24, integer bound 2^40) to every available endpoint from all lanes. Floating screens only reject proposals; the guarded exact checker, unchanged strict checker and independent arbitrary-precision checker must all accept. No factorization, LP solve or planted witness is used. Missing endpoints remain unsuccessful. Original results are preserved.

This alternative complete pipeline retains original model encoding and cold solver-process time, then adds a cold reconstruction process and fresh strict/exact audits. It replaces the raw endpoint audit in the pipeline cost; all actual research work, including both audit pathways, remains charged in resource accounting. The same extra work is charged to candidate and vendor outputs. Reconstruction is bounded by 60 work / 90 process seconds. Its 32 valid perturbed-endpoint tests and 32 negative-dual tests pass before use.

See [all reconstruction outcomes](lp-sp-pricing-scale-reconstruction.csv). This tier measures COPT plus shared certificate reconstruction, not native COPT certification, and was specified after first-seed raw audit outcomes were visible.

| Family | Seed | COPT lane | Both timely exact after reconstruction | COPT / candidate operational | COPT / candidate fully audited |
| --- | ---: | --- | --- | ---: | ---: |
| dense-4m | 122301 | copt-gpu | False | — | — |
| dense-4m | 122301 | copt-auto | True | 10.605× | 6.426× |
| dense-16m | 122301 | copt-gpu | False | — | — |
| dense-16m | 122301 | copt-auto | False | — | — |
| sparse-4m | 122301 | copt-gpu | False | — | — |
| sparse-4m | 122301 | copt-auto | False | — | — |
| sparse-scaled-10m | 122301 | copt-gpu | False | — | — |
| sparse-scaled-10m | 122301 | copt-auto | False | — | — |
| mixed-tall-4m | 122301 | copt-gpu | False | — | — |
| mixed-tall-4m | 122301 | copt-auto | False | — | — |
| dense-4m | 122357 | copt-gpu | False | — | — |
| dense-4m | 122357 | copt-auto | False | — | — |
| dense-16m | 122357 | copt-gpu | False | — | — |
| dense-16m | 122357 | copt-auto | False | — | — |
| sparse-4m | 122357 | copt-gpu | False | — | — |
| sparse-4m | 122357 | copt-auto | False | — | — |
| sparse-scaled-10m | 122357 | copt-gpu | False | — | — |
| sparse-scaled-10m | 122357 | copt-auto | False | — | — |
| mixed-tall-4m | 122357 | copt-gpu | False | — | — |
| mixed-tall-4m | 122357 | copt-auto | False | — | — |
| dense-16m | 122419 | copt-gpu | False | — | — |
| dense-16m | 122419 | copt-auto | False | — | — |
| sparse-scaled-10m | 122419 | copt-gpu | False | — | — |
| sparse-scaled-10m | 122419 | copt-auto | False | — | — |
| mixed-tall-4m | 122419 | copt-gpu | False | — | — |
| mixed-tall-4m | 122419 | copt-auto | False | — | — |

Common reconstruction accepts 10 candidate, 1 GPU-COPT and 2 automatic-CPU COPT endpoints. The excluded supervision group remains excluded from all ratios.

On dense-4m seed 122301, the candidate and copt-auto complete the common fully audited pipeline in 4.753 and 30.542 seconds, respectively (6.426×). This is a single eligible same-input pair on a synthetic all-active square LP; it is not broad solver or GPU superiority.


## Certificate reliability

The additional checker decodes original binary64 coefficients using `float.as_integer_ratio`, decodes rational endpoints independently, and traverses the entire original CSR with Python arbitrary-precision integer arithmetic. It checks every primal inequality, every dual equation, dual nonnegativity and exact zero gap. It also checks that published floating endpoints match the rational proof. It shares neither the native signed-128 arithmetic kernel nor solver acceptance reductions, and it does not use a planted witness. Original content chunks are hash-verified when read.

Admission compares 128 randomized mixed-active valid cases with two independent oracles and rejects 384 deliberately invalid certificates. Boundary tests cover large cancellation, range/exponent limits, non-dyadic rational proofs, modified immutable chunks, forged integer caches and a one-ULP disagreement between published and rational endpoints.

The tests exposed an unsigned-narrowing issue in the old direct helper: uint64(2^64-1) could become signed -1 before its range check. The new opt-in boundary checks original-dtype ranges before conversion and verifies cached integers against the original coefficients. Previous actual solver proposals were bounded signed integers; old sources, receipts and timings remain unchanged.

Every one of the 8 accepted candidate endpoints in the primary cohort also receives two deliberately invalid large-model challenges. Both native and independent checkers reject all 16 challenges. The objective mutation receives a complete original-matrix traversal; the negative-dual mutation is rejected by the sign condition. The supplement receives the same full independent endpoint proof, but is outside that earlier frozen corruption-challenge roster. No solver is rerun and immutable inputs are not changed.

Exact proof validity is deterministic for the represented input. Broader tests and an independent arithmetic implementation improve confidence in the software; they do not turn a certificate into a statistical claim. The proof is about the stored coefficients, not unknown real-world data before rounding.

## Scope and resource settlement

The two-hour wall deadline and phase transfer were recorded before model generation. Existing total ceilings remain 240000 CPU / 30000 GPU seconds. Four CPU slots, physical host/GPU/storage caps, ownership checks, idle admission and all original failure charges remain in force. The compact checkpoint records actual settled charges, final tests/documentation and the absence of owned processes. No historical scientific cell is repeated.

This is a larger synthetic capacity and certificate evaluation. It does not establish broad LP or GPU superiority. Fast CPU factor presolve, expensive rectangular exact geometry, and unsuccessful vendor endpoints must be interpreted separately. Two seeds do not characterize timing variance or a broad workload distribution. Candidate process high-water memory is retained; no matched COPT process-memory comparison is claimed.
