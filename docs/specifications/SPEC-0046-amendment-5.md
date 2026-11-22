# SPEC-0046 amendment 5: GPU preparation with original-model certificates

The user explicitly requests moving scaling, norm estimation, step-size estimation
and other suitable preparation work to the GPU, while preserving strict certificate
checks. Continue the billion-nonzero objective and preserve every existing capacity
observation, including the missing 128 M cell. Complete already-started generation
and the image-v2 capacity baseline before changing the final cohort implementation.

An opt-in image-v3 may use a separate FP64 preparation CUDA module for Ruiz maxima,
Pock-Chambolle sums, scaled coefficient construction, power-iteration products,
vector norms, normalization and step calculation. Preserve the original arithmetic
order with explicit rounded operations and the original 1024-leaf reduction tree.
Special cases outside the admitted exact GPU domain use the original host
preparation, with an explicit recorded fallback. No construction witness or
endpoint answer is used. The fast-image-v10 solve CUDA module remains unchanged.

Original CSR/CSC and certificate authority remain on the CPU. Independent scalar
checking and every strict feasibility/gap guard remain unchanged. GPU preparation
has no mathematical authority. Its device buffers are checked and released before
the solve device allocation; complete memory accounting includes both stages and
host download transients. Count upload, download, context lifetime and teardown in
preparation and complete process time. The existing `host_preparation` cost key
continues to denote the complete pre-solve preparation interval; additional phase
fields explicitly identify GPU work.

Admission requires bitwise scales, coefficients, objective/bounds and step-size
comparisons, zero/rectangular/tail/extreme/fallback cases, exact full continuations,
forced recovery/cancellation and all four sanitizers. Keep public sources/defaults
and historical images exact. Source-bound operational admission covers the added
CUDA source and preparation module before new scientific work.

After admission, compare a new six-family 64 M fixed-work cohort and the two 256 M
and 512 M capacity inputs against their retained image-v2 observations. Keep all
regressions and require exact non-timing transcripts for equal-work ratios. These
are new implementation cohorts, not retries. Final one-billion-nonzero native,
FP32 and FP4x2 solves use one common admitted preparation implementation; their
complete limits and allocation are frozen only after capacity observations.

Totals, phase ceilings from amendment 4, four slots, physical memory/storage
limits, pinned idle-only GPU, one-second supervision and all 100 ms advisories
remain unchanged. No public adoption, publication or confirmation is released.
