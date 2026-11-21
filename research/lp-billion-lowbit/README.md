# Isolated billion-nonzero LP executor

This opt-in derivative of `lp-general-lowbit` is governed by
[SPEC-0046](../../docs/specifications/SPEC-0046-billion-lp.md). It retains the
admitted fast-image-v10 CUDA image. Public solver sources and defaults are
unchanged. Admission and experimental status are recorded separately from source
availability; the presence of this crate is not a performance claim.

The `billion` binary consumes a small original-model manifest plus content-addressed
32 MiB chunks. The manifest fixes dimensions, original nonzeros, objective sense
and offset, identities, bounds, canonical CSR and sparse objective arrays. The
reader verifies every chunk, validates canonical positions and builds the exact
transpose directly. It avoids a per-term model document and compression triples.

Preparation retains the original arithmetic tree with bounded per-line scratch.
Control retains the 100-update cadence, full checkpoint recovery and bitwise state
comparison; the already-owned checkpoint supplies the restoration reference.
The GPU wrapper counts each device buffer and checks physical fragment and launch
indices before creating a CUDA context. Raised dimensions alone do not admit a run.

Feasibility follows original canonical term order. Image-v1 uses the original
serial dual certificate; image-v2 computes its independent terms with bounded
workers and keeps their canonical final reduction. Scalar external checking and
gap assessment use the unchanged original implementation. The array path uses the
supplied original bounds directly; it does not apply optional implied-bound
strengthening. Endpoint vectors and any repaired dual witness are immutable binary64
chunks. The response references every intermediate and final endpoint.

Commands take `MODEL STORE`; `solve` additionally takes the admitted CUDA image.
`convert` converts a small original document or historical compact input into a
manifest, `inspect` validates its geometry, `assess` independently checks endpoint
references, and `solve` reads one JSON request per line. The legacy interface is
retained for admission comparisons. Build output belongs on approved experiment
storage through `CARGO_TARGET_DIR`, not the capacity-constrained checkout.

The optional `fast.gpu_preparation: true` request uses a separately built
`prepare.cubin` next to the solve image. It moves Ruiz and Pock-Chambolle scaling,
scaled CSR/CSC coefficients, spectral power iterations, vector norms and step
calculation to FP64 CUDA kernels. Explicit rounded operations preserve the
original reduction tree; no floating-point atomics are used. Upload, download,
context creation and teardown count toward complete preparation cost. Preparation
buffers are released before the solve device is allocated.

The exact GPU domain has at most 1024 nonzeros per original row or column and
Pock-Chambolle alpha 0 or 1. Empty geometry, longer lines, other exponents and
invalid intermediate values retain explicit host fallback. Bounds and objective
are constructed from the downloaded scales on the host. Original CSR/CSC,
strict feasibility and dual-gap certification, and independent scalar checking
remain authoritative on the CPU. The flag defaults to false.

`prepare-check MODEL STORE PREPARE_CUBIN` compares every scale, scaled coefficient,
objective/bound value and step-size bit against the admitted host implementation.
Preparation device admission, sanitizers and timing results are recorded in the
[billion-scale report](../../docs/benchmarks/lp-billion.md). Source availability
alone does not admit a particular image or establish a measured speedup.


The independent opt-in flags `fast.gpu_control: true` and
`fast.gpu_feasibility: true` load `control.cubin` next to the solve image. Control
uses the resident scaled CSR/CSC and existing vector scratch for exact-tree
projected residuals and restart movement norms. Lines longer than 1024 terms
retain CPU residual evaluation. Scalar square roots and the log/exp weight
recurrence remain on the CPU, with unchanged control cadence and recovery.

GPU feasibility evaluates original coefficients and bounds in original row order.
It borrows CSR indices and uploads original values and bounds with bounded host
scratch. Its additional live device allocation is checked together with the solve
buffers before allocation. The CPU dual-bound enclosure and gap arithmetic remain
unchanged. Every potentially accepting GPU feasibility result must also pass the
original CPU feasibility check with identical objective bits before certificate
acceptance. Independent final/intermediate audits remain required by the campaign.
Both flags default to false; neither changes the strict original-model 1e-9 criteria.

`control_check TENSOR_CUBIN` is a separate admission diagnostic for exact residuals,
movement norms, original feasibility, long-line fallback and invalid inputs.
The admission and campaign tools retain immutable images, complete sanitizers,
resource supervision and all failed or uncertified outcomes. Performance claims
must come from completed, independently audited cohorts in the benchmark report.
