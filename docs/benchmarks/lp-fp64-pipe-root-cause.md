# Why FP32 Components Were Slower: The FP64 Pipe

Status: investigation record, 2026-09-19; acted on by
[ADR-0022](../decisions/ADR-0022-fp64-pipe-execution-and-tolerance-tiers.md) (GPUP-5C).
The [GPUP-5B report](lp-exact-components-gpup5b.md) and its archived evidence are
unchanged. Every number here is an **uncharged diagnostic**: standalone
microbenchmarks compiled from the unchanged research source, run under the shared
host lease on the study device for under one minute total, outside the campaign
ledger. GPUP-5C repeats the microbenchmarks as charged acceptance work from
committed source in cuda/diagnostics and reports those numbers separately.

## Findings

1. **The cost is the FP64 pipe, not Tensor Cores or bandwidth.** On the RTX 5090
   (GB202, sm_120) FP64 add/multiply, `DSETP` compares and 64-bit `F2F` conversions
   issue at one sixty-fourth of the FP32 rate, as NVIDIA's
   [RTX Blackwell whitepaper](https://images.nvidia.com/aem-dam/Solutions/geforce/blackwell/nvidia-rtx-blackwell-gpu-architecture.pdf)
   states. No project kernel uses a Tensor Core instruction. The three-component
   cross-product kernel spends about 140 FP64-pipe instructions per nonzero, 126 of
   them in the `compensated()` helper that protects 18 cheap FP32 partials with seven
   dependent FP64 adds each. Bit width of the components is irrelevant to this cost.
2. **The research FP64 control also pays.** Its `checked()`/`multiply()` guards
   compile to about a dozen `DSETP` compares per nonzero, so `research_native64` is
   2.4x slower than tuned `spmv_warp32` at scale with identical results.
3. **The twelve development instances are launch-bound.** Every SpMV variant except
   the component kernels takes about 4.1 us per launch on irregular-2048 and
   dense_block-1024, against a 2.1 us floor for an eight-row launch. Precision cannot
   change kernel time on this corpus.
4. **Even ideal FP32 arithmetic caps near 1.7-2.6x** on the sparse kernel at scale,
   because SpMV is byte-bound; the gain comes from halving bytes, not from the 64x
   FLOP ratio. That ratio only bites when FP64 work is *added*.
5. **Certified solve time is elsewhere.** On the archived irregular-2048 research
   profile: context creation 208.7 ms, kernels and synchronization 34.2 ms,
   host certification 28.8 ms, preconditioning 26.3 ms, research preparation
   18.6 ms, controller 15.3 ms, of a 512 ms solve. Six launches per proposal with
   a synchronization every 64 steps cost 12.4 us per proposal on 2048-element
   vectors versus 5.0 us for a CUDA graph and 4.9 us for a persistent kernel.

## Static instruction evidence

Compiled with the provisioning flags (`nvcc -std=c++17 -arch=sm_120 -O3 -lineinfo
-fmad=false -ftz=false`), inner sparse loop, non-`NOP` SASS per kernel:

| Kernel | FP64-pipe | 64-bit F2F | FP32 | memory | other |
| --- | ---: | ---: | ---: | ---: | ---: |
| tuned spmv_warp32 (unrolled 2) | 32 | 0 | 0 | 51 | 67 |
| research_native64 (unrolled 4) | 64 | 0 | 0 | 24 | 91 |
| research_native32 | 28 | 4 | 4 | 12 | 47 |
| research_factored64 | 48 | 0 | 0 | 16 | 59 |
| research_components3_native | 27 | 9 | 4 | 6 | 47 |
| research_components2_cross | 71 | 14 | 12 | 7 | 39 |
| research_components3_cross | 140 | 23 | 22 | 9 | 37 |

Per nonzero: tuned 2 FP64-pipe instructions (`DMUL`, `DADD`); research native
about 16 (arithmetic plus `DSETP.NEU/NE/EQU` guard compares and selects);
three-component cross-products 163 (140 FP64 plus 23 conversions). Registers are
34-40 per thread with no spills in every kernel. Hardware counters remain
unavailable: Nsight Compute returns `ERR_NVGPUCTRPERM` for the standalone binary
as well, because the driver runs with `RmProfilingAdminOnly` and the container
lacks the capability, so pipe attribution rests on counts plus timing.

## Microbenchmark timing

Standalone harness including `cuda/lp_pdhg_research/lp_pdhg_research.cu` verbatim;
same 256-thread, eight-rows-per-block geometry as the executor; 400 launches
(x1) or 50 launches (x64) after warm-up; CUDA events on one stream. The x64 cases
tile the CSR pattern 64 times block-diagonally. Scaled coefficients are drawn with
non-dyadic row/column factors so they are not FP32-exact. Microseconds per launch:

| Kernel | irregular-2048 | dense_block-1024 | irregular x64 (131072 rows) | dense_block x64 (65536 rows) |
| --- | ---: | ---: | ---: | ---: |
| FP64 warp-per-row (tuned arithmetic) | 4.10 | 4.10 | 39.0 | 26.7 |
| research_native64 | 4.10 | 4.10 | 94.3 | 90.1 |
| research_native32 | 4.10 | 4.10 | 94.2 | 90.1 |
| research_components3_native | 8.14 | 6.15 | 232.7 | 209.0 |
| research_components3_cross | 20.49 | 20.47 | 876.4 | 858.5 |
| research_components2_cross | 12.35 | 12.29 | 486.2 | 465.0 |
| cross3 with plain FP64 adds (no compensation) | 8.20 | 8.20 | 278.8 | 268.0 |
| cross3 truncated, x pre-split (incl. split launch) | 8.20 | 8.19 | 147.4 | 134.8 |
| double-float FP32 pair, x pre-split (incl. split launch) | 6.12 | 6.03 | 30.8 | 18.5 |
| FP64 with integer-pipe guards | 4.10 | 4.09 | 38.9 | 30.8 |
| FP32 storage, FP64 products, no guards | 4.09 | 4.10 | 43.1 | 30.7 |
| all-FP32 (storage, operands, FMA, accumulate) | 4.10 | 2.05 | 22.6 | 10.3 |
| eight-row launch floor | 2.08 | 2.06 | | |

Interpretation. The cross-product kernel moves twice the bytes of FP64 and takes
22x longer at x64; bandwidth cannot produce that ratio, while an FP64-pipe
throughput estimate lands within about 1.5x with dependent-add latency covering
the rest. Removing compensation alone gives 3.1x; pre-splitting the vector and
dropping the six negligible cross terms gives another 1.9x; only removing FP64
from the loop entirely (double-float) beats FP64. Integer-pipe guards make the
guarded FP64 kernel identical in cost to tuned. Maximum relative errors against a
long-double reference: FP64 variants 1e-13 to 1e-11, double-float 1.3e-12 at x1
and 2.4e-10 at x64 on nearly cancelling row sums (per-operation error about
3.6e-15), all-FP32 2e-4 to 3e-3.

## Launch structure

2048-element vector kernels, 64 iterations of six launches, one synchronization
per 64 iterations, 50 repetitions:

| Structure | us per iteration |
| --- | ---: |
| six stream launches, synchronize per 64 | 12.36 |
| one CUDA graph of 384 nodes | 5.02 |
| persistent cooperative kernel, six grid barriers per iteration, 8 blocks | 4.98 |
| same, 170 blocks | 4.86 |

The archived 21 us per proposal for research native FP64 is consistent with six
launches at about 3.5 us each. Fusing sparse products with their vector updates,
as the tuned executor already does, reaches two launches per proposal without any
new driver-API symbol; graphs and cooperative launch would need new boundary
wrappers under ADR-0009 and are not pursued.

## Assessment of alternatives raised

- **Relaxing 1e-9.** Row 805 of irregular-2048 violates its original allowance by
  3.1e-7 against 9e-9 under FP32 storage; relative tiers of 1e-6 or 1e-4 would
  admit it. cuOpt's PDLP defaults are 1e-4 for all six absolute/relative
  primal/dual/gap tolerances
  ([settings](https://docs.nvidia.com/cuopt/user-guide/latest/lp-qp-milp-settings.html),
  [source](https://github.com/NVIDIA/cuopt/blob/main/cpp/src/math_optimization/solver_settings.cu)),
  relative to global norms of b and c, whereas this project's relative allowance
  is per row and its dual bound is certified outward on the original model at any
  tier. The GPUP-5 COPT controls were run at the project's 1e-9, so that comparison
  was matched. ADR-0022 adds explicit tiers rather than changing the default.
- **Mixed decompositions (2xFP32+BF16, FP8 slices).** Not worthwhile here.
  Component count and width never drove the cost; any FP64 recombination pays the
  1/64 rate, and BF16/FP8 parts convert to FP32 before multiplying. A BF16 third
  component saves two bytes per nonzero and nothing else. FP8 slicing needs about
  14 E4M3 slices for 53 bits and roughly 100 Tensor Core products per scalar,
  which pays only for dense GEMM; these matrices average 18-33 nonzeros per row.
- **Custom kernels.** Yes: integer-pipe guards (free), fused two-launch schedule
  (halves launch cost), double-float sparse products (1.3-1.4x over FP64 at
  scale, loses at study size to its extra split unless fused). All three are
  GPUP-5C modes.
- **Context creation** at 208 ms is the largest single cost and outside all
  arithmetic; repeated-solve context reuse remains a separate objective in the
  [candidate register](../plans/lp-precision-candidates.md).

## Provenance

Investigation host: the GPUP-5B study device GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48,
driver 580.105.08, CUDA 13.0.88, all three visible devices sm_120. The archived
research cubin SHA-256 3116cc29ca171aa65f7331b45f39c92288085230e2ce36e0f5ddebb5e8c6a418
was disassembled; the microbenchmark recompiled the same source. Microbenchmark
sources are committed as cuda/diagnostics/fp64_pipe_bench.cu and
cuda/diagnostics/launch_overhead.cu; their charged GPUP-5C acceptance runs are
reported in the GPUP-5C report. No solver, protocol, seed, tolerance, artifact or
ledger changed during this investigation.
