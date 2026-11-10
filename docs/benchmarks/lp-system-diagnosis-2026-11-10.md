# GPU LP system diagnosis and solver comparison

Status: read-only diagnosis of retained evidence, 2026-11-10; no new solver run.
Owner: numerical backend and experiment tooling.
Reviewed source: `396bd0e2ea095f1d038dfa862bb31f29a61e0d68`.
Decision: [ADR-0047](../decisions/ADR-0047-certified-performance-roadmap.md).
Next work: [current roadmap](../plans/gpu-lp-precision-roadmap.md#current-plan-2026-11-10).

The project has implemented substantial low-precision arithmetic and independent
validation, but has not demonstrated a supported low-precision solver that beats
its tuned FP64 baseline in certified single-solve latency. In the latest GPUP-8
profiles, reconstructing accurate products and updating expanded vectors cost
much more than the Tensor main product. Improving Tensor throughput alone cannot
remove that bottleneck. The next investment should establish a fair external
baseline and reduce total execution cost, then test a simpler mixed-precision
method with explicit recovery. Exact expansion remains a reference and a bounded
research alternative, rather than the assumed fast path.

## What is actually implemented

The [latest recovery report](lp-tensor-expanded-recovery-gpup8.md) supersedes earlier
GPUP-8 failure descriptions as the current disposition. Earlier failures remain
valid historical evidence.

| Area | Current state | What remains unproved |
| --- | --- | --- |
| Scalar arithmetic | Corrected 7376-case independent proof; conversions, splits, component products and projections pass | General solver speed from primitive correctness |
| Expanded solver | Separate CPU and CUDA research executors; accepted native, model and device gates | Production integration and a competitive total solve |
| Device acceptance | All six jobs pass, including four sanitizers; twelve fixed-work/replay pairs accounted for, with twenty newly verified changed endpoints | Performance on the unfinished study cells |
| Profiles | Six small-model profiles finish; first large BF16 profile times out at the unchanged 18-second deadline | Nine unexecuted profiles and all sixty timings |
| GPUP-8 / GPUP-9 | GPUP-8 incomplete; scientific stages closed; GPUP-9 gated | Full forecast, certified gain and supported precision recipe |

The timeout is not evidence of a numerical error. The partial profiles are also
not a complete gain forecast or a replacement for primary timing acceptance.
CPU accounting remains **59603.097503214 / 77640 seconds**; GPUP-8 GPU accounting
is **1410.959187474 / 3000 seconds**. Campaign GPU consumption is
**22770.545043263 / 25202.574545061 seconds**. The 17438-event ledger, original
prefix, failed charges and unused timing allocations remain as recorded in the
[final accounting](data/tensor-expanded/recovery-final-accounting-v1.json).

[ADR-0046](../decisions/ADR-0046-expanded-audit-window-state.md) keeps Expansion64
working state private within windows of at most 32 updates. Penultimate vectors
are canonicalized to FP64, both candidate and reference use that same input,
and a successful audit adopts the FP64 reference endpoint. Controller and fresh
assessment boundaries remain at 200 updates. Expansion does not persist across
windows. The research executor is a separate workspace under
`research/lp-tensor-expanded-device`, not the default search backend.

## Latest measured bottleneck

The following values come from the retained dense-block 1024-row, seed-0,
2000-update profile endpoints. The [extracted metrics and source hashes](data/system-diagnosis-2026-11-10.json)
make this table traceable without running the profiles again. All five research
configurations first certify at update 1400.

| Profile | Preparation, seconds | Execution through final assessment, seconds |
| --- | ---: | ---: |
| Expanded component SIMT | 0.526 | 5.771 |
| Expanded FP16 Tensor | 0.477 | 5.777 |
| Expanded INT8 Tensor | 0.546 | 5.833 |
| Expanded BF16 Tensor | 0.534 | 5.849 |
| Matched FP64 | 0.533 | 0.807 |

These are instrumented fixed-horizon observations, including preparation. They
exclude part of the outer producer lifecycle and are not fresh-process primary
timing medians. The matched FP64 control shares research overhead and is not the
unchanged tuned baseline. The near equality of SIMT and Tensor totals is strong
evidence that the main-product instruction family is not the dominant cost here.

For expanded INT8, CUDA events attribute **3.906 seconds to reconstruction**,
**0.844 seconds to primal plus dual updates**, **0.0677 seconds to the Tensor
main product**, and **0.0062 seconds to reference audit**. Reconstruction is about
67% of the 5.833-second execution envelope. Even eliminating the main-product
event time entirely gives only an illustrative **1.012x** envelope improvement
if every other cost stays fixed. This is an Amdahl-style cost bound, not a speed
forecast for a changed implementation. The first-certificate prefix alone is
4.060 seconds for INT8, before the required remaining producer costs.

Host and device measurements overlap. The host profile records 8700
`resident_solve_loop/device_to_host` calls occupying 4.877 seconds, largely while
waiting for submitted work. This is not another 4.877 seconds of PCIe transfer
to add to the CUDA events. There are 11616 recorded synchronization calls across
the expanded profile, versus 1074 in its matched FP64 control. Instrumentation
and synchronization can affect timings; there is no hardware-counter evidence
here establishing bandwidth saturation, occupancy, cache behavior or Tensor
utilization. Those require a new, separately admitted profile.

### Why reconstruction is expensive

The [reconstruction kernel](../../cuda/lp_pdhg_tensor_expanded/expanded_reconstruct.cu)
assigns one thread per output and traverses its groups and stored entries
serially. Eligible entries still load and test vector residuals; nonzero residuals
take expanded multiply and add operations. Sparse or promoted terms follow the
accurate path as well. This preserves the declared reduction semantics but leaves
substantial scalar work outside the Tensor product.

The [expanded arithmetic helper](../../cuda/lp_pdhg_tensor_expanded/expanded_fast.h)
forms up to nine FP32 digit products, their error terms and wide integer
accumulation; the full-range fallback uses compact integer arithmetic. Even
`xr_add` invokes that generic construction through multiplication by one.
Avoiding FP64 arithmetic instructions does not make this equivalent in cost to
one native FP32 operation. Expansion64 uses 16 bytes per coordinate before scratch,
versus eight for a native FP64 value. For the declared 56-bit matrix and 64-bit
vector main parts, INT8/FP16 require 80 component pairs and BF16 requires 224.
The INT8 profile counts 10.486 billion component products for 131.072 million
eligible logical coefficient products, plus padding and residual work.

The [device controller](../../research/lp-tensor-expanded-device/src/device.rs)
also uploads four coefficients and reads status four times per update. Its
[CUDA buffer boundary](../../research/lp-tensor-expanded-device/cuda-sys/src/lib.rs)
synchronizes copies. These are concrete opportunities for device-resident control
and fewer host observations, subject to preserving refusal, rollback and
cancellation semantics. Removing host reads cannot by itself remove the dominant
expanded arithmetic work.

### What older diagnoses do and do not explain

The [earlier Tensor latency diagnosis](lp-tensor-latency-diagnosis.md) identified
step-size restriction and extra iterations. Its 2200-versus-1400 comparison must
not be applied to the current expanded profiles: these first certify at 1400.
The current problem is principally expensive work per update and preparation.

Convergence still matters outside this small dense case. In the
[convergence study](lp-convergence.md), FP32 proposals on irregular-32768 were
about 10.1% cheaper, but 40464 proposals failed to certify, while precision-FP64
certified at 1600 and tuned FP64 at 1400. A cheaper proposal is useful only if
the number of proposals, recovery and certification costs remain competitive.

## Bottlenecks across the whole system

| Priority | Evidence and implication | Design response |
| --- | --- | --- |
| 1: accurate reconstruction and state updates | Dominant in current expanded profiles; many component and residual operations | Do not extend exact emulation by default; require a whole-solve cost case before another Tensor implementation |
| 2: synchronization and host control | Per-update coefficients/status, thousands of synchronous copies | Prototype bounded device-resident blocks with sticky error flags and explicit safe boundaries |
| 3: setup, conversion and final checks | Context creation, layout/preconditioning, artifact work and original-model assessment are charged | Report cold, warm and core times separately; optimize immutable setup and checker implementation without dropping checks |
| 4: convergence and recovery | FP32 and quantization can stall or reject useful work | Measure time to a common certificate; use residual-driven precision escalation and a native fallback |
| 5: workload fit | The initial Tensor study found eligible dense tiles in only two of eight model families | Dispatch by measured structure and precision requirements; retain sparse SIMT and CPU alternatives |
| 6: algorithm and integration coverage | Research PDHG is not a complete commercial LP/MIP portfolio or the search relaxation path | Establish external baselines, then add separately verified presolve/postsolve and integration work where evidence warrants it |

Several apparent next ideas have already been tried:

- [Repeated-solve sessions](lp-repeated-solve-throughput.md) exist. Their small-model
  batching gains are throughput results and cannot be used as cold single-solve wins.
- [Residual refinement](lp-refinement-gpup-refine.md) exists with FP64 outer updates
  and GPU products. Only 30/96 timings certify; all nine successful new-method
  timings certify at the initial host point with zero inner updates. A new proposal
  must establish useful nonzero work and address these refusals.
- [Assessment scheduling](lp-assessment-scheduling-gpup-assess.md) produced a scoped
  1.0272x FP64 irregular-model gain. It did not eliminate the required controller
  assessments or establish a general recipe.
- [Resident quantization](lp-quant-resident-gpup7r.md) did not admit a useful
  quantized window. Residency alone does not fix overconservative guards or
  insufficient numerical progress.

The ordinary search CLI constructs a HiGHS relaxation backend in
[search.rs](../../crates/optimizer-cli/src/search.rs). The
[executive](../../crates/optimizer-solver/src/executive.rs) calls relaxation solves
without a warm start. GPUP-8 results therefore do not currently accelerate that
branch-and-bound path. LP kernel improvements, repeated LP throughput and full
MILP performance need separate acceptance endpoints.

## Comparison with available solvers

This is a capability comparison, not a new benchmark ranking. Vendor documentation
was checked on 2026-11-10; the installed COPT release was read locally.

| System | Relevant design | Consequence for this project |
| --- | --- | --- |
| AI Optimizer | Independently checked original-model certificates; PDHG research, explicit arithmetic/replay contracts and precision experiments | Strong validation foundation; limited demonstrated workload coverage, expensive exact emulation, no supported precision preset |
| NVIDIA cuOpt 26.10 | GPU PDLP and barrier, CPU simplex and concurrent options; presolve and crossover; explicit single/double/mixed PDLP modes | First external GPU baseline; compare forced PDLP and portfolio modes separately |
| COPT 8.0.6 | Local commercial LP/MIP implementation, CPU/GPU methods including PDLP and barrier, presolve and postsolve | Available comparator; separate native solver time from adapter/model-building and external-check costs |
| Gurobi 13 | Broad commercial solver portfolio; documentation now includes GPU PDHG | Documentation-only reference for now; absence must not block cuOpt/COPT work |

cuOpt's documented mixed mode uses FP32 matrix storage with FP64 vectors and
computation, retaining FP64 matrices for full checks at restart. This is a useful
simple comparison design, but it is not a claim of FP16/BF16 Tensor acceleration
or an overall halving of memory. Mode parameters should be explicit; default
solver tolerances differ and do not establish the project's original-unit
certificate. See [cuOpt features](https://docs.nvidia.com/cuopt/user-guide/latest/convex-features.html)
and [precision and tolerance settings](https://docs.nvidia.com/cuopt/user-guide/latest/convex-settings.html).

Gurobi 13 documents PDHG selection through `Method=6`, with GPU execution via
`PDHGGPU=1` and a GPU-enabled installation. No local Gurobi installation, license
or benchmark is claimed. See the [Gurobi 13 changes](https://docs.gurobi.com/projects/optimizer/en/current/reference/releasenotes/changes.html).
For COPT, local `/root/copt80/release-notes.txt` identifies 8.0.6, CUDA 13 support
and GPU barrier improvements. The local headers and existing COPT adapter are
the executable version authority; the [COPT parameter reference](https://guide.coap.online/copt/en-doc/parameter.html)
is supplementary. No proprietary arithmetic internals are inferred.

### Existing COPT evidence

The common-checker convergence study reports these historical primary medians
(seconds, three repetitions, original 1e-9 criterion):

| Model | Tuned project FP64 | COPT CPU PDLP | COPT GPU PDLP |
| --- | ---: | ---: | ---: |
| small-4 | 0.4141 | 0.2672 | 0.7226 |
| irregular 32768 | 2.6467 | 3.5685 | 3.8078 |
| dense-block 65536 | 6.4145 | 9.2406 | 8.9383 |

The small-4 row is a different model from the 1024-row GPUP-8 profiles above.
These particular adapter and resource settings are not a general solver ranking.
The [larger COPT comparison](lp-copt-comparison.md) retained 1140 attempts,
948 verified endpoints and only 402/816 certified primary timings. In a dense
profile, COPT's native LP solve was about 1.242 seconds inside an 8.832-second
full path. Adapter construction and independent checking can reverse the apparent
ordering. Single-CPU affinity also limits what those results say about commercial
parallel portfolios. The new comparison must disclose both an equal-resource
cohort and any separately budgeted vendor-recommended settings.

## Design conclusion and limits

Modern GPU low-precision peak throughput is primarily attractive when enough
matrix work can be reused. A single sparse LP iteration usually performs matrix-
vector products, not a large matrix-matrix product. NVIDIA's
[matrix performance guide](https://docs.nvidia.com/deeplearning/performance/dl-performance-matrix-multiplication/index.html)
explains that matrix-vector operations have low arithmetic intensity. Expanding
one product into many digit products does not create free useful throughput.
Batching related right-hand sides may improve reuse, but it changes the endpoint
to throughput and requires its own workload and report.

The selected direction is consequently: comparable cuOpt/COPT baselines; lean
resident execution; simple mixed precision with reliable original-model checks
and escalation; selective Tensor work only where structure and measured total
cost support it. Separate [ADR-0047](../decisions/ADR-0047-certified-performance-roadmap.md)
and [roadmap tasks](../plans/gpu-lp-precision-roadmap.md#current-plan-2026-11-10)
record the alternatives, dependencies, deliverables and decision gates.

No fresh profile, endpoint verification, performance trial or scientific budget
transfer was made for this diagnosis. It cannot establish current cuOpt speed,
general superiority over a commercial solver, or behavior on unseen large models.
The optional [cuOpt setup](../operations/cuopt.md) records installation separately
from device and solver acceptance.
