# Bounded matrix quantization: GPUP-7

Status: bounded research evaluation under accepted ADR-0040. No supported preset.

Retained 104 of 104 planned attempts; independently verified 34 endpoints and certified 33/96 timing cells.

| Configuration | Verified timings | Certified timings |
| --- | ---: | ---: |
| fp16-uniform | 3 / 12 | 3 / 12 |
| fp16-selective | 3 / 12 | 3 / 12 |
| e4m3-uniform | 3 / 12 | 3 / 12 |
| e4m3-selective | 3 / 12 | 3 / 12 |
| e5m2-uniform | 3 / 12 | 3 / 12 |
| e5m2-selective | 3 / 12 | 3 / 12 |
| matched-fp64 | 3 / 12 | 3 / 12 |
| tuned-fp64 | 12 / 12 | 12 / 12 |

All candidates retain FP64 masters and fresh original-model host certification at
1e-9. Local 1e-7 product/audit budgets grant no final-accuracy authority.
Original-unit guards, metadata scans, host FP64 updates, transfers, audits and
sticky promotion/replay are included in fresh-process latency. Low work and
promoted masks remain explicit in the [machine-readable report](data/quant/report.json).
A solve that succeeds after native promotion is not evidence of a low-precision
convergence or throughput benefit. Initial host-only successes are also separate.

The eight-model CPU admission and independent integer/Fraction format/product
oracle precede device execution; numerical refusals remain in
[CPU admission](data/quant/cpu-admission.json). Failed, interrupted and missing
endpoints remain unsuccessful timings. Partial profiles cannot enter comparisons.
All eight diagnostic cells remain visible. None reaches its complete requested
2000 charged-update horizon: seven paths time out; tuned FP64 certifies early
at 1400 updates. No full-horizon profile comparison follows. CPU-only reader
review excludes incomplete horizons and CPU fallback from GPU timing claims,
with unchanged numerical results and charges. The original report is retained.
The fixed comparison includes uniform/selective binary16, CUDA E4M3/E5M2,
matched FP64 with the same conservative step/audits and unchanged tuned FP64.

Full pinned-native, ordinary device, new product/controller differentials,
18 fixed-work endpoint/replay pairs and four scoped sanitizers precede the study.
Exact sources, executable/image identities, raw outputs and all outcomes are
retained under artifacts/gpup-quant-v1; historical evidence remains separate.

Task GPU charge: 1382.959456122 / 3600 seconds.
Cumulative charge: 21113.899268966 / 25202.574545061 seconds.
Ledger: 17036 events, SHA-256
861c90d8d82a20ff9655173742db37a5047d315e8cc4c983e0d6b2e6fa09bb97.

No vector FP16/FP8 quantization, Tensor Core or combined-policy conclusion follows.
GPUP-8 needs its own conditional admission contract; unused allowance reserves nothing.

Final pinned-native acceptance passes 329 Python tests, Rust/native/dependency
checks, historical replay, 134 documentation pages and smoke, with zero GPU work.
See [native acceptance](data/quant/native-acceptance.json),
[device and sanitizer acceptance](data/quant/device-acceptance.json),
[fresh verification of all 182 retained endpoints](data/quant/retained-verification.json)
and [final source receipts](data/quant/final-source.json). Only documentation and
acceptance receipts record the final gate afterward; measured runtime bodies,
executables, images, requests and ledger remain exact.
