# FP4x2 verified input and strict proof costs

The new CPU paths reduce verified input time by **1.56–1.97x**, certificate
time against the previous four-worker workspace by **1.39–1.59x**, and complete
cold checking against the original serial checker by **2.08–2.56x** on four
fresh synthetic shapes. Every measured model and certificate matches its
original reference. These are input/checker measurements, not complete PDLP
solver speedups. GPU integration and solver default promotion remain pending.

This continuation starts from `7647a3d`, follows
[amendment 96](../specifications/SPEC-0046-amendment-96.md), and extends the
[component diagnosis](lp-fp4x2-pipeline.md). All 472 protected PR #30/shared/CUDA
interface sources and all original CUDA kernels remain unchanged. The original
scalar certificate implementation and frozen independent checker images remain
the reference authority. No historical scientific LP or driver is repeated.

## Why these phases cost so much

At one billion nonzeros, original coefficients and their 32-bit indices alone
occupy 12 GB in CSR, before row offsets, IDs, bounds or the objective. CSC holds
another 12 GB. Input loading reads content objects, checks their exact SHA-256
hashes and lengths, decodes them, validates the original sparse structure, counts
column entries and scatters the original data into its ordered transpose.
Several full memory passes and a large, irregular scatter are involved.

The original loader processes chunks serially and the original transpose scatter
uses one thread. Those serial dependencies are implementation choices. By
contrast, SHA-256 identity, array shapes, finite coefficients, sorted unique
indices/IDs, legal bounds and the original coefficient bits are required by the
input contract. Removing those checks would change what input is trusted.

Strict certification is much more work than an approximate matrix product:
each nonzero contributes a binary64 outward enclosure; exactness checks decide
whether rounding requires neighboring floats; reductions maintain lower, upper
and rounded values through the prescribed tree. Feasibility separately traverses
the original rows and bounds. The reference cold checker does this serially.
The optimized in-solve workspace already uses up to four workers, so the two
certificate baselines must not be confused.

The reported **cold final proof includes input reload, hashing and reconstruction**
as well as proof arithmetic and process teardown. It does not mean that all
132.358 seconds in the retained coupled billion run were spent on arithmetic.
The solver and independent checker establish their own original-input identity.
That separate cold audit is required by the current evaluation protocol, not by
each mathematical PDLP update. It cannot be removed from reported complete cost.
Both existing and accelerated checker commands already load a model once and
accept a stream of distinct endpoints; no extra reload is needed within a session.
The audit harness already deduplicates identical endpoints exactly.

## Necessary work and removable cost

| Work | Treatment |
| --- | --- |
| Read original bytes and verify each content digest | Keep. Parallelize independent chunks; do not trust a previous process's cache or weaken SHA-256. |
| Decode and validate shapes, IDs, sparse order, finite values and bounds | Keep. Decode directly into final disjoint slices; preserve every validation and the first chunk-order refusal. |
| Construct ordered CSC for column products | Keep the representation. Partition complete columns by work and scatter from sorted CSR rows concurrently, using binary searches to visit only each worker's entries. No floating-point atomics, sorting changes or second matrix-sized staging copy. |
| Wide integer product exactness comparison | Skip only when a significand bit-length bound proves the product cannot be represented exactly. Remaining products fit in 54 bits and use a bounded 64-bit comparison. Preserve underflow, overflow, signed-zero and adjacent-float behavior. |
| General checked reduction at every node | Use the existing tested vector reduction only for at most 2048 enclosure terms in its proven normal range. Preserve all tree edges and padding. Use the original general reduction everywhere else. |
| Repeated certificate allocations | Reuse the previous solve-local workspace. No per-nonzero decomposition cache is added. Recompute all products, bounds and decisions for every endpoint. |
| Independent original-model acceptance | Keep strict 1e-9 feasibility, dual-bound and gap checks. The original scalar command remains available; frozen audit images and historical receipts are untouched. |

Input parallelism uses at most four CPU workers. Large chunk decoding retains at
most four raw 32 MiB buffers alongside final decoded arrays: a bounded additional
96 MiB versus serial loading, rather than another complete decoded array. Each
loading, construction and assessment stage joins before the next worker team
starts. GPU-overlapped assessment still reserves three proof workers plus its
caller. Memory and phase limits are unchanged.

The new switches are explicit:

```sh
billion solve MODEL STORE CUBIN --parallel-input
billion assess-fast MODEL STORE --parallel-input
```

`fast.exact_certificate=true` selects the new exact product/reduction path inside
FP4x2 PDLP and includes reusable workspace. The original `assess` command remains
serial and authoritative. `assess-fast` is a separate original-model CPU checker;
it never creates a CUDA context. See the
[executor options](../../research/lp-billion-lowbit/README.md).

## Correctness before timing

Final source-bound gate `fp4x2-io-quality-v4` passes formatting, **84 Rust tests**,
Clippy with warnings denied, and release builds. It includes:

- **248,841 exact product comparisons** against the original outward operation,
  covering exponent/significand boundaries, random bit patterns, subnormals,
  infinities, NaNs, overflow and both signed zeros.
- **2,160 new full-certificate comparisons** against the original scalar checker
  at one, three and four workers, in addition to the previous 2,160 comparisons.
  Bounds, allowances, unadjusted results, repair counts and first refusals match.
- Parallel transpose comparisons at 1,048,576 nonzeros, including skewed columns,
  subnormal values, signed zeros and malformed indices/coefficients. Smaller and
  empty model roundtrips compare both construction paths.
- Concurrent chunk corruption/truncation checks, exact decoded bits and ordered
  failure reporting. Cold command comparisons include an accepting empty model
  and a nontrivial endpoint. False GPU acceptance still requires original CPU
  confirmation and is rejected.

The final benchmark then checks all original model arrays and returned proof
values, including certificate bits against the original scalar arithmetic,
before retaining any performance conclusion. None of its 144 cold-process
responses differs from its corresponding original proof.

## Measurements

`fp4x2-io-measure-v1` uses four fresh shapes with **16,777,216 nonzeros**, three
fresh seeds each and three rotated repetitions per seed. Input comparisons
separately enable chunk parallelism, transpose parallelism and both. Certificate
comparisons use the previous and new workspaces with four workers. Cold process
comparisons separately enable accelerated input, the accelerated checker and both.
Reported ratios are medians of the three seed medians of paired old/new times.

| Shape | Input: chunks only | Input: transpose only | Input: both | Certificate: old/new, 4 workers | Complete cold check: original/new |
| --- | ---: | ---: | ---: | ---: | ---: |
| Short columns | 1.152x | 1.557x | 1.968x | 1.391x | 2.563x |
| Balanced | 1.141x | 1.552x | 1.925x | 1.441x | 2.484x |
| Long columns | 1.194x | 1.216x | 1.561x | 1.585x | 2.385x |
| Uneven columns | 1.193x | 1.283x | 1.603x | 1.493x | 2.077x |

For the short-column case, median input time changes from approximately
893 to 460 ms: CSR reading/hashing/decoding changes from 360 to 248 ms, while
validated construction changes from 528 to 200 ms. Complete cold checking changes
from approximately 1693 to 661 ms. These measurements show that both construction
and proof execution matter; faster hashing alone would not achieve the combined
gain. Aggregate time ratios need not equal ratios of separately aggregated times.

Every shape/seed median improves in the combined paths. All individual samples,
including any local variability or regressions, remain in
[compact evidence](lp-fp4x2-io-proof-results.json). The complete cold checker gains
include changing the reference's serial execution to four workers, while the
certificate column compares equal worker counts. They are different comparisons.

Processes are cold but OS page caches are **not flushed**. Synthetic construction
and checker input are retained as separate costs; generation is outside the
checking stopwatch. These four patterns are not the full six-family scientific
roster and do not establish billion-scale, GPU, deadline/recovery or full-solver
performance. Sampled aggregate RSS peaks at 1,206,620,160 bytes within the 16 GiB
reservation; it is not an exact peak or a per-mode memory nonregression result.
All new large synthetic objects are deleted only after their exact comparisons;
small manifests, hashes, sources, logs, results and failures remain. Raw replay
requires regeneration from the retained generator and seeds.

## What can move to the GPU

Original primal feasibility and control reductions already have GPU paths. The
current CUDA code preserves original row order and uses explicit rounded binary64
operations; every accepting diagnostic still receives original CPU confirmation.

A GPU dual proof is feasible as a separate implementation: compute original
column products and three-component enclosures, reduce them through exactly the
same tree, preserve subnormals and signed-zero padding, and report the same first
refusal. Ordinary approximate FP4/FP32 products or an unordered sparse reduction
cannot replace these checks while preserving current certificate semantics.
The new bounded integer classification is suitable for such a future port, but
it has only CPU validation here.

There is also a concrete memory/transfer cost. Current GPU feasibility stores
original CSR values, while solver/preparation CSC values are scaled. A direct
GPU dual implementation needs original CSC coefficients, or an exactly verified
mapping to original CSR, plus bounded proof scratch. A separate billion-element
FP64 coefficient array alone is 8 GB. Recovering original coefficients by dividing
scaled values would not preserve original bits. Admission must count this memory,
uploads, launches, fallback and final independent checks in complete cost.

GPU transpose construction would additionally need stable original ordering and
host results for the independent checker. GPU hashing still needs verified file
bytes transferred to the device and cannot omit the original content identity.
Neither operation becomes free by moving it, especially while the device is
occupied. The tested CPU paths are usable without borrowing GPU capacity.

A fresh, supervised read-only observation finds approximately **74.9 GiB allocated**
on the pinned GPU and fails the existing idle rule, despite zero instantaneous
sampled utilization. It grants no GPU admission. No GPU job, sustained-idle monitor
or other-workload intervention occurs. A GPU proof implementation still requires
fresh idle admission, exact continuations, independent checks and all sanitizers.
The older five-option GPU test matrix does not cover the new certificate/input
options and must be extended before any device admission.

## Resource accounting and defaults

Before final reporting, this continuation consumes **4150.387673008 CPU seconds**
and **zero GPU seconds**, within the existing 570000/68000 totals and unchanged
phase caps. The second quality gate stops at an import-formatting check, before
numerical tests or measurement, and retains its full **1440 CPU-second** failure
charge. Every completed reservation has empty cleanup and no overrun. Native
headroom was below the minimum reservation, so fresh correctness gates use the
existing CPU admission phase as specified prospectively; no old charge is moved.

Final reporting verifies the existing source-only FP4x2 policy tests and all
documentation links, seals `image-fp4x2-io-v1` as **CPU_quality_only**, and retains
its reservation separately until settlement. Only its generated HTML is removed.
The compact evidence includes all actual preceding charges and the final reserve.

CPU input/checker acceleration is demonstrated on the stated fixtures and is
available through the explicit commands above. GPU solver integration, the full
family roster and complete PDLP cost remain unmeasured, so solver defaults stay
unchanged. Historical scientific complete costs and the original cold-audit
requirement are not regraded using these new CPU results.
