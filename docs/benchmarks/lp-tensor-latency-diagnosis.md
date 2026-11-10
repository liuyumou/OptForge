# GPUP-8 Tensor latency diagnosis

Status: CPU-only diagnosis complete; proposed continuation is not accepted.
Owner: numerical backend and experiment tooling.
Last reviewed commit: bootstrap (parent 6521c3a).

The useful Tensor arithmetic now works, but most of the latency deficit is
shared preparation and solver-policy work. Optimizing the MMA kernel alone is
unlikely to complete GPUP-8. The recommended next slice is
[proposed ADR-0044](../decisions/ADR-0044-tensor-cost-continuation.md): repair CPU
admission first, then test one fixed package of preparation, norm and audit
changes, with early refusal before spending the timing reservation.

## Evidence and attribution boundaries

This diagnosis reads the exhausted [ADR-0043 study](lp-tensor-residual-gpup8.md).
The separate [machine receipt](data/tensor-latency/diagnosis.json) binds 72 study
endpoints and their workers/trials by SHA-256, checks the retained report binding,
and verifies the exact settled 17362-event ledger. It does not rerun a solve or
claim fresh numerical verification. The earlier independent verification of all
248 GPUP-8 LP records remains the numerical evidence. No GPU job runs here.

Reproduce the receipt to a new filename, preserving the existing one:

```sh
python3 tools/diagnose_lp_tensor_latency.py \
  --output docs/benchmarks/data/tensor-latency/diagnosis-check.json
```

Worker elapsed time is the primary fresh-process single-solve latency. The
`cost/*` fields are **exclusive** host-thread times: sum a scope and its
descendants once to recover its inclusive cost. `host_preparation`, `solve_loop`,
`context`, and `original_model_assessments` are overlapping envelopes and must
not be added to those costs. Submission/readback scopes include waits; they are
not CUDA-event kernel durations or hardware-utilization measurements.

The existing `tuned-fp64` **timings** use unchanged `optimizer lp-study solve
--backend cuda-lp-tuned`. Its forced **profiles** instead use the research
executable with `layout=original_tuned`. That wrapper still constructs Tensor
metadata and uses its own assessment/evidence path. Its 3.497-second preparation
time on the large model cannot be assigned to the unchanged tuned timing path.
The original profiles remain useful for a limited common-wrapper comparison;
they are not clean end-to-end profiles of the primary control. The new proposal
requires the actual tuned path for both timing and diagnostic controls.

## Measured latency and work

Five fresh-process timings per cell all certify at unchanged 1e-9 tolerances:

| Model | Tuned FP64 | INT8 | FP16 | BF16 | Represented SIMT | Policy-matched FP64 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1024 rows, median seconds | 0.462114 | 0.614776 | 0.625008 | 0.720782 | 0.608621 | 0.597043 |
| 65536 rows, median seconds | 6.331022 | 10.390881 | 10.482344 | 10.739558 | 10.371203 | 10.352774 |

INT8 must reduce its current total latency by 24.83% on the small model or 39.07%
on the large model merely to tie tuned FP64. All six retained adjusted intervals
show slowdowns. The matched-FP64 deficit accounts arithmetically for 88.38% and
99.06% of the corresponding INT8 deficit. This subtraction identifies shared
cost as the main investigation target; different executions and five samples
do not establish a causal allocation of every millisecond.

| Certified solve work | Tensor / represented SIMT / matched FP64 | Unchanged tuned FP64 |
| --- | ---: | ---: |
| Logical updates, both models | 2200 | 1400 |
| Physical updates | 2277, including 77 audits | 1400 |
| Kernel launches | 24508 | 8400 |
| Large-model upload bytes | 277299348 | 63438856 |
| Large-model readback bytes | 161488096 | 7340032 |
| Rejected / replayed updates | 0 / 0 | not a Tensor recovery path |

All thirty Tensor timings have 66 useful windows and no native promotion. Failed
arithmetic, replay storms or a fallback solve are therefore not explanations
for these timing results.

## Why the shared path is expensive

**The norm restriction changes the trajectory.** `quant::Operator::new` doubles
each absolute coefficient enclosure when constructing induced row/column norm
bounds. Tensor execution then restricts the engine step to `0.9 / norm`. On
1024 rows the step is 0.405030 versus the unrestricted engine's 2.445488; on
65536 rows it is 0.394898 versus 2.379194. The latter values are recorded by the
original-tuned wrapper; true tuned timings independently record 1400 updates.
The restriction is about sixfold, not merely a different product instruction.
All component and matched trajectories certify at 2200 updates. A tighter
**proved** bound is a plausible way to reduce that amplification. The evidence
does not isolate the step from audit adoption and reduction-order differences,
and simply copying tuned's estimated step would remove the accepted safety bound.

**Preparation repeats substantial generic work.** Tensor construction first
builds a full quantization operator, then builds additional error arrays, sparse
group indices, a tile map, dense integers and represented coefficients. Even the
matched-FP64 control pays these costs. The large INT8 2000-update profile contains
1.320577 seconds in the exclusive packing/metadata subtree: 0.959711 in generic
quantization and 0.360867 in the Tensor layer. Host preparation totals 3.469498
seconds and includes another 0.773036 seconds of norm/step estimation. These
are one-profile observations, not medians or fully removable costs. Fresh
preparation remains part of the endpoint; session reuse cannot supply this gain.

**Audits return work to the CPU every 32 updates.** On the large INT8 profile,
70 host audits cost 1.280538 seconds, including 1.247751 seconds of original FP64
arithmetic. Each passing audit adopts that reference update. The full reference
must be preserved; its location and data movement can be optimized only with
an independently proved equivalent implementation. The 200-update restart,
weight and host-certification boundaries are separate and remain mandatory.

**Assessment cost is amplified by the extra updates.** The same profile spends
2.771474 seconds in original-model assessments and 0.749079 seconds in the
controller-assessment subtree. In full INT8 solve timings, median original-model
assessment time is 3.097706 seconds. Those costs must not be added to `solve_loop`
again. Reducing work to reach certification addresses repeated checks without
weakening or delaying certification. No assessment-cadence change is proposed.

**Dispatch and transfers matter, but are not the largest large-model cost.**
The kernel path submits eleven kernels per update plus four per window, compared
with six per update in tuned FP64. It uploads state at every audit window and
downloads both the endpoint and its pre-audit state. At 2000 updates, INT8 has
22280 launches and 146807360 readback bytes; the original-tuned wrapper has 12020
launches and 10485840 bytes. The INT8 device-window subtree costs 0.456819 seconds,
versus 0.418990 for matched FP64 and 0.139589 for the tuned wrapper. Eliminating
even that entire INT8 subtree would leave roughly 9.4655 seconds in the measured
2000-update worker. This is a scope-based illustration, not a predicted
time-to-certificate or a bound on pure kernel speedup.

## Why Tensor instructions do not yet provide an arithmetic advantage

The 56-bit representation uses eight 7-bit components for INT8/FP16 and fourteen
4-bit components for BF16. Each selected scalar product expands into 64 or 196
component cross-products, followed by exact 128-bit reconstruction. The source
executes 16/32/112 warp-level MMA instructions per 32x32 tile and orientation
for INT8/FP16/BF16, respectively. BF16 pads fourteen vector components to sixteen
lanes of component columns, explaining additional work beyond the 196 pairs.
This is single-RHS exact component work, not a conventional dense low-precision
matrix multiply whose peak throughput can be applied directly.

Dynamic packing recomputes the same 32-entry block maximum in each lane. Residual
corrections also remain necessary: on the large full timing trajectory they are
19.19% of selected products; on the small trajectory, 18.13%. `tn_product` scans
all selected coefficient entries to count work and apply nonzero residuals,
even when most tails are zero. The native sparse remainder adds more work.
These are real source/counter costs, but there are no separate CUDA-event timings
for packing, MMA, reconstruction and correction, so their exact time shares
remain unknown. BF16's larger component expansion is consistent with its slower
observed timing; it is not established as the sole cause.

## Resource diagnosis and remaining allowance

The previous resource wrapper monitors only its child process tree. It has no
shared aggregate admission lock, token accounting or cumulative CPU reservation.
Four admission workers and a separate four-job Cargo build could therefore run
at once. A peak from either tree cannot certify the aggregate peak. Preserve the
[historical limitation receipt](data/tensor-residual/cpu-concurrency-limitation.json).

The current environment exposes cgroup v2 CPU/memory counters but its control
files are not writable. The enclosing CPU quota is 90 cores and memory limit
is 200 GiB, so that enclosure does not enforce this task's four-worker/8-GiB
limits. [The read-only preflight](data/tensor-latency/resource-preflight.json)
records this. ADR-0044 requires an independently admitted delegated task
enclosure, a shared coordinator, and CPU-only contention/failure tests before
fresh preparation. Configuration of that host capability is a real prerequisite;
the proposal must refuse if it is unavailable. No privileged host change runs
as part of this diagnosis.

| GPUP-8 phase | Original cap, GPU s | Charged | Remaining | Proposed maximum |
| --- | ---: | ---: | ---: | ---: |
| Screening | 1600 | 415.105235119 | 1184.894764881 | 990 |
| Ablations | 550 | 90.046073299 | 459.953926701 | 320 |
| Repeatability / acceptance | 850 | 319.962723857 | 530.037276143 | 496 |
| Total | 3000 | 825.114032275 | 2174.885967725 | **1806** |

No phase transfers or cap increases are needed. The proposed maximum would make
the task 2631.114032275 / 3000 GPU seconds and campaign 23990.699888064 /
25202.574545061, leaving 368.885967725 task GPU seconds unreserved.

Prior conservative CPU accounting is 19134.822845162 / 21600 seconds. Charge this
diagnosis and its acceptance **400 CPU seconds in full**, including a conservative
allowance for small inspection/editing commands. Do not reclaim old reserves or
unrecorded overlap time. This leaves 2065.177154838 CPU seconds. ADR-0044 reserves
at most **2050 CPU seconds**, including compilation, proofs/admission, acceptance,
leased-worker CPU, verification, monitoring and reporting. That leaves only
15.177154838 seconds unreserved. Failure of a CPU gate or an inadequate forecast
must stop work; GPU headroom cannot compensate for CPU exhaustion.

## Recommended decision

Approve only the single staged experiment in proposed ADR-0044. Its most valuable
changes are compact preparation, a tighter conservative operator norm, and an
equivalent device reference audit. Existing Tensor arithmetic, original-model
authority, local tolerances, sticky promotion and whole-window replay remain.
Require CPU resource admission before implementation preparation, numerical CPU
admission before device work, and a predeclared diagnostic go/no-go before all
60 fresh timing cells. Retain all three arithmetic families and the original six
Bonferroni comparisons; do not select a winner from the screening samples or
replace a failed identity. A statistical gain remains uncertain. If the bounded
slice refuses or shows no gain, GPUP-8 remains incomplete.

The historical concurrency failure remains historical. A new clean, source-bound
CPU cohort can establish prospective admission for the revised implementation;
it cannot make the old cohort's resource acceptance pass retroactively.

## Diagnosis acceptance

The separate [acceptance receipt](data/tensor-latency/acceptance.json) records a
stable-source full pinned-native `tools/check.sh` pass: 366 Python tests,
Rust/native/dependency checks, historical replay, 144 documentation pages and
smoke, with zero GPU execution. The gate used 234.500760 measured CPU seconds
and sampled 1650266112 bytes peak process-tree RSS; heavy jobs ran sequentially.
The full 400-second diagnostic reservation is charged conservatively. This
accepts the diagnosis and proposed plan only. ADR-0044 remains unaccepted,
prospective delegated containment remains unavailable, and GPUP-8 incomplete.
The exact 17362-event ledger and 17200/17132 prefixes are unchanged. Historical
numerical/runtime sources, endpoints and reports were not edited. Final edits
only add this acceptance metadata and task-state records.
