# Billion-nonzero first pass

No candidate-versus-COPT performance conclusion is available from this pass yet. The GPU scale-admission command has not completed, and no scientific candidate or COPT solve has started. Input construction and independent feasibility/optimality checks are CPU preparation, not solver results.

The six-family roster below uses at least one billion original nonzeros per model. A separate exactly-billion near-dense square alternative is also retained. Rectangular certificate bases have order 4,000. Sparse-wide has 25% density and irregular-square 62.5%; this roster does not establish behavior on extremely sparse million-by-million square LPs.

| Family | Rows × columns | Original NNZ | Input status | Candidate / COPT |
| --- | ---: | ---: | --- | --- |
| dense-wide-1b | 4,000 × 250,000 | 1,000,000,000 | passed | Not started / not started |
| sparse-wide-1b | 4,000 × 1,000,000 | 1,000,000,000 | not_generated | Not started / not started |
| mixed-tall-1b | 1,000,000 × 4,000 | 1,000,000,000 | passed | Not started / not started |
| scaled-mixed-tall-1b | 1,000,000 × 4,000 | 1,000,000,000 | not_generated | Not started / not started |
| dense-square-1b | 31,623 × 31,623 | 1,000,014,129 | input_not_admitted | Not started / not started |
| irregular-square-1b | 40,000 × 40,000 | 1,000,000,000 | not_generated | Not started / not started |
| near-dense-square-1b | 32,000 × 32,000 | 1,000,000,000 | passed | Not started / not started |

## Measured input preparation

| Family | Generation and encoding (s) | Cold exact check (s) | Completed raw 1e-9 check (s) | All preparation (s) |
| --- | ---: | ---: | ---: | ---: |
| dense-wide-1b | 57.576 | 54.789 | 99.347 | 303.102 |
| mixed-tall-1b | 54.485 | 172.219 | 71.508 | 298.734 |
| dense-square-1b | 52.221 | 94.059 | 0.002 | 146.727 |
| near-dense-square-1b | 53.550 | 87.473 | 92.539 | 233.943 |

The dense-wide total includes its original raw-audit timeout and the successful supplemental check; neither cost is dropped. The original dense-square has 1,000,014,129 nonzeros and is rejected at manifest validation by the strict checker; its very short raw-check time is a domain rejection, not a numerical assessment. The separate 32,000 by 32,000 alternative has exactly one billion nonzeros at 97.65625% density and uses fresh seed 131181. The tall construction checks returned accepting results, but their parent reservation lost its coordinator during finalization. A fresh supervised read-only seal verifies the completed proof contents and known-owned-process cleanup. The original reservation remains failed with its full charge.

## Implementation and acceptance

The additive scale path uses bounded CSR generation and loading, exact integer products with explicit overflow bounds, implicit rectangular certificates, and a proposed GPU square LU with two solves from one factorization. Existing admitted million-scale paths and numerical defaults are unchanged. The large GPU paths are compiled but remain unadmitted until differential checks, the large-offset capacity probe, and all four compute-sanitizer tools pass.

A CPU-only validation diagnostic on 1,000,000 rows and 16,000,000 entries measured 4.69× (int32 offsets) and 5.24× (uint64 offsets) speedups from casting row offsets once before the unchanged blockwise canonical scan. Twenty-four malformed/valid differential cases agree; eight exact-proof tests also pass with the optimized scan. These are component timings, not billion-scale end-to-end solver speedups.

The core CPU admission passes 18 input/numerical tests. Two additional harness contracts verify preparation-inclusive timing and exclusion when a cold proof is missing. No GPU quality or sanitizer success is claimed.

## Comparison protocol and availability

Both lanes use the same original model and strict 1e-9 raw checker. Complete cost is the sum of original generation, all construction checks including failed attempts, the cold solver process (input/import/transfers/solve/export), raw audit, common endpoint construction, and cold independent exact proof. Queue delay between separately reserved phases is excluded. GPU solve and CPU audit reservations are separate. Ratios require timely completion, raw acceptance, and the cold exact certificate for both lanes.

The native allowance is 180 seconds and the solver-process allowance 240 seconds. Candidate native timing includes its input preparation; COPT reports its native solve separately, while its import remains in process and complete costs. Assessment has 450 seconds per cell, including up to 240 for the raw check and 90 for common reconstruction. The larger assessment envelope was frozen before any solver attempt, after the first billion-input check exceeded 90 seconds.

COPT is configured for GPU PDLP with Presolve=0, Crossover=0, four CPU threads, strict 1e-9 settings, installed-default Scaling/Dualize, and a disclosed 96,000 MB memory parameter. Hard limits remain 128 GiB owned host memory and 80 GiB owned GPU memory.

A GPU admission reservation failed before the quality command started; its full 600 GPU / 2,400 CPU-second charge remains. Later read-only observations show about 74.9 GiB device memory used without process attribution in this container. Utilization initially read 100% and later zero. This exceeds the fixed 2 GiB unattributed-memory allowance and does not grant admission. No owner is inferred, and no unrelated workload is signalled.

The user asked to finish CPU preparation and save GPU runs for later. No monitor or automatic GPU continuation remains active. Resume only after a new user request and fresh availability/ownership admission, preserving every prior attempt and charge. The user approved cumulative caps of 240,000 CPU and 37,200 GPU seconds. The resumption uses a fresh two-hour wall envelope without changing those totals. All failures retain their full charges. Admitted private input objects remain available for untouched solver attempts. The over-limit square matrix objects were deleted after their exact proof and manifest-rejection disposition; its small arrays, hashes, proofs and failures remain. Historical objects and previous comparison results are preserved. Remaining family inputs will be generated one at a time on resumption to respect rolling storage headroom.

The first pass targets six synthetic dyadic families with one fresh seed each. Million-by-million sparse square, mixed-active square or rectangular bases above order 4,096, scaled sparse-square, and the COPT CPU-auto lane are outside this admission envelope. The candidate remains a practical certificate-first method, not a completed strongly polynomial implementation of the paper.

The [comprehensive report](lp-sp-pricing-comprehensive.md) retains the completed smaller-scale comparisons. The [prospective roster](../plans/lp-sp-pricing-billion-first-pass.md) records the original proposal; immutable execution manifests and receipts record the subsequent approval and enlarged audit allowances.
