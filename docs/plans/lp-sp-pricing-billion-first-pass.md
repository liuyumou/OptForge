# Billion-nonzero first pass

Status: CPU preparation; GPU budget extension and scale admission pending.
No new billion-scale solve has run. This is a prospective protocol, not a result.

The user selected a two-hour first pass across representative families. Each
scientific model below contains at least one billion original nonzeros. Filled
basis entries, replicated independent problems and aggregate batch work do not
count toward that size.

| Family | Rows | Columns | Original NNZ | Density | Proposed route |
| --- | ---: | ---: | ---: | ---: | --- |
| Dense wide | 4,000 | 250,000 | 1,000,000,000 | 100% | GPU row Gram, implicit primal recovery |
| Sparse wide | 4,000 | 1,000,000 | 1,000,000,000 | 25% | GPU row Gram, implicit primal recovery |
| Mixed-active tall | 1,000,000 | 4,000 | 1,000,000,000 | 25% | GPU projection, cached implicit dual correction |
| Scaled mixed-active tall | 1,000,000 | 4,000 | 1,000,000,000 | 25% | Equilibrated projection and pipelined correction |
| Dense square | 31,623 | 31,623 | 1,000,014,129 | 100% | GPU LU, explicit exact certificate |
| Irregular square | 40,000 | 40,000 | 1,000,000,000 | 62.5% | GPU LU, explicit exact certificate |

These shapes deliberately keep rectangular certificate bases at order 4,000.
The sparse-wide and irregular-square densities must accompany results; they do
not establish performance on extremely sparse, million-by-million square LPs.
Mixed-active square and rectangular models with both dimensions above 4,096,
scaled sparse-square, and million-by-million sparse-square remain visible as
outside the admitted first-pass scope. The COPT CPU-auto lane is omitted from
this two-hour pass.

The stream generator uses signed dyadic coefficients, power-of-two row scaling
where specified, and 20% inactive rows in mixed cases. Its b and c construction
uses checked int64 bounds and exactly representable FP64 values. Construction
witnesses remain separate and must pass an independent original-model check
before either solver starts. One fresh seed per family is fixed in the executable
protocol. These are synthetic feasible bounded cases, not a broad industrial
workload or a completed implementation of the paper's strongly polynomial
algorithm.

## Required scale admission

Existing admitted rectangular CUDA entry limits stop at 2^27 dense entries.
The proposed shapes need up to four billion dense entries, including offsets
beyond signed int32. The entry-limit extension must be additive, with explicit
64-bit size checks and boundary diagnostics. The order-4,096 certificate limit
stays unchanged. Large square cases require a separate GPU LU proposal with two
solves from one factorization, runtime workspace checks, and an explicit exact
certificate; a 40,000-order inverse is not proposed.

The wide and explicit independent checks need bounded integer products over all
original nonzeros. Numerical proposals never accept certificates. Before any
scientific cell, require CPU scalar differential tests, GPU differential and
malformed-input checks, all four compute-sanitizer tools, and a capacity ladder.
A failed admission stays a failed admission; it must not be reported as a solver
result. Existing admitted sources, public defaults, and previous results remain
unchanged. The old billion-study drivers and identities must never be repeated.

The analytical forecasts include dense host copies, CSR and loader copies,
integer encoding, inverse objects and runtime allowance. They are planning
estimates, not measured peaks. The largest rectangular GPU matrix is 32 GB.
COPT's internal workspace is opaque: its capacity requires measurement under the
unchanged resource guard. Increase its prospective memory parameter from 12,000
to 96,000 MB for this roster, retaining the 128 GiB aggregate host and 80 GiB
owned-device hard limits. Every capacity refusal stays visible.

## Timing and comparison

The two-hour execution window begins with the first guarded preparation after
explicit approval of the GPU extension. Target 600 seconds for scale admission,
900 seconds per family for six paired families, 300 seconds for reporting, and
900 seconds of contingency. These are outer envelopes, not guarantees of six
completed pairs. Reserve cleanup and reporting time first; do not start a family
when its complete allowance no longer fits. Keep any unstarted slot visible.

Each lane requests 180 native seconds with a 240-second process allowance and
120 seconds for complete assessment. The assessment allowance covers the raw
original-model check, common endpoint reconstruction and cold independent proof.
If input/import time exhausts the outer window, record that failure explicitly.
Do not retry a started cell or hide a startup timeout. Rotate candidate/COPT order
by family. No cache flushing or statistical significance is claimed from one pair.

Complete cost includes common original generation and encoding, input hashing,
GPU preparation and transfers, solver/import time, endpoint export, raw 1e-9
audit, common reconstruction, and independent exact or rigorous implicit proof.
Record raw acceptance and reconstructed acceptance separately. A solver's optimal
status does not establish certification. Report speed ratios only for jointly
timely certified pairs. Preserve every endpoint, missing response, failed proof,
phase time and sampled memory peak in the compact evidence.

COPT uses the installed default Scaling and Dualize, GPU PDLP, Presolve=0,
Crossover=0, four CPU threads, and the existing strict 1e-9 settings. The memory
parameter change is disclosed. No claim about concurrent auxiliary-search
throughput follows from these factor-presolve/projection measurements.

## Storage and budget

Generate and audit one family at a time in a fresh private object store, using
bounded blocks of at most 2^20 nonzeros. Retain small manifests, source bindings,
proofs, failures and receipts. Delete only that family's newly owned large blobs
after all claims are audited and cleanup is recorded. Historical shared objects
are excluded. Full raw replay after pruning requires deterministic regeneration.

The settled [pipeline checkpoint](../benchmarks/lp-sp-pricing-pipeline-checkpoint.json)
records 179,062.584 CPU seconds and 29,965.476 GPU seconds against the existing
240,000 / 30,000 totals. Only 34.524 GPU seconds remain; the guard requires at
least 120 seconds for a GPU reservation. The existing allocation cannot run this
pass. The pending proposal adds **7,200 GPU seconds**, raising the cumulative
GPU cap to **37,200**, while keeping the CPU cap at **240,000**. It does not
activate that increase or infer approval from the wall-time preference.

Prospective phase caps are CPU reference/admission/development/confirmation/
billion/reporting = 4,000/32,000/20,000/126,000/32,000/26,000, and GPU =
0/4,877/3,416/22,307/6,600/0. Every prior charge remains. Four CPU slots, physical
headroom, the 30-second idle proof, ownership checks and all supervision rules
remain unchanged. CPU preparation uses the already approved allocation.

The implementation of this proposal is in
[the protocol](../../tools/lp_sp_pricing_billion_plan.py),
[the streaming generator](../../tools/lp_sp_pricing_billion_input.py), and
[its exact-oracle tests](../../tests/integration/test_lp_sp_pricing_billion_input.py).
The proposal has no solver-launch, approval, or deletion action.
