# Why the GPU LP Baseline Is Slow

Purpose: explain measured solver and study overhead. Owner: numerical backend and
experiment tooling. Status: completed diagnostic follow-up, 2026-09-15.
Protocol: [ADR-0015](../decisions/ADR-0015-lp-baseline-diagnosis.md), supplementing
the unchanged [GPUP-2 baseline](lp-baseline-gpup2.md).

## Conclusion

The main obstacles are poor convergence with the GPU's fixed controller, expensive
repeated host certification, and fresh-process GPU setup. The Python harness adds
substantial overhead outside the reported solve timings. Transfers are a small
measured cost on these instances. These observations do not establish that changing
precision would solve the current problems.

Seven new, independently checked GPU jobs used 20.994604580 leased GPU seconds.
The same release solver and LP code object were used as in the baseline. Three
ordinary profiles confirmed its timings; four 200-iteration runs isolated tracing
overhead and produced two CUDA activity traces. CPU component measurements and
50,000-step differential replays used the original recorded models and endpoints.
No solver, numerical target, controller, kernel or frozen baseline trial changed.

## 1. The fixed controller converges too slowly

The existing GPU backend holds its initial anchors and primal weight fixed, with
Halpern coefficient k/(k+1). The host backend restarts its anchors and adjusts its
weight. This is an algorithmic difference, not just a different execution device.

The CPU diagnostic calls the existing Engine::step_once with weight 1 and applies
the GPU's fixed-anchor update. On irregular-256 and scaling-64, after 50,000 steps,
**every primal and dual binary64 bit matches the archived GPU endpoint**. This
checks the long trajectory's endpoint on two nontrivial cases and reproduces the
failure to reach feasibility. It does not prove every model/kernel path correct.

For irregular-256:

| Fixed-control iteration | Largest row violation | Rejected row bounds |
| ---: | ---: | ---: |
| 200 | 0.805909 | 197 |
| 1,000 | 0.161672 | 197 |
| 1,200 | 0.134749 | 197 |
| 5,000 | 0.032361 | 197 |
| 10,000 | 0.016182 | 197 |
| 50,000 | 0.003237 | 197 |

The last violation remains about 198,983 times its recorded allowance. Its decrease
is consistent with approximately 1/k convergence over these checkpoints, not a
roundoff-sized plateau. The certified lower bound is already close to 216 at
1,000 iterations, but the primal is infeasible. At 50,000 iterations its reported
objective is 215.673809; treating that as a feasible optimum would be incorrect.
The ordinary host controller certifies this instance at 1,200 iterations.

The scaling-64 replay also matches every GPU bit and remains infeasible at 50,000;
the ordinary host certifies it at 3,200. These tests identify the combined controller
difference; they do not separately quantify restart versus weight contributions.
GPUP-3 should establish the shared resumable FP64 controller before device/precision
comparisons. Implementation locations: [GPU iteration](../../crates/optimizer-lp-cuda/src/backend.rs)
and [host control](../../crates/optimizer-lp/src/pdhg.rs).

## 2. Host certification dominates larger solves

The new ordinary profile for irregular-2048 took **9.276 seconds**:

| Measured phase | Seconds | Share of complete process |
| --- | ---: | ---: |
| Host checks | 7.369 | 79.4% |
| Kernel submission, execution and synchronization | 1.235 | 13.3% |
| Device setup | 0.443 | 4.8% |
| Working allocation, upload and readback combined | 0.019 | 0.2% |

The remaining time includes preparation, final independent checks, serialization
and teardown. The original profile measured 7.300 seconds in host checks, so the
new result confirms the same bottleneck.

CPU-only microbenchmarks separate existing operations. Each number below is the
median of three blocks, each containing 20 calls on an archived endpoint:

| Instance | One certificate ms | One candidate evaluation ms | One conservative gap ms |
| --- | ---: | ---: | ---: |
| small-4 | 0.061 | 0.001 | 0.012 |
| irregular-256 | 3.287 | 0.119 | 0.016 |
| irregular-2048 | 26.455 | 1.223 | 0.085 |
| dense_block-1024 | 13.644 | 0.866 | 0.055 |

A 50,000-iteration GPU run checks every 200 steps, then checks its final candidate
again: 251 backend checks, plus the separate final evidence assessment. For
irregular-2048, 251 times the isolated certificate/evaluation costs predicts
6.947 seconds, close to the measured 7.300–7.369 seconds. The isolated endpoint
assessment itself takes 32.094 ms. Timing variation, candidate construction and
other small operations account for the remaining difference; the measurements are
not a same-process allocation of every nanosecond.

### Why each certificate is expensive

[Certification](../../crates/optimizer-lp/src/certify.rs) uses an outward enclosure
for each column sum. The shared [reduction](../../crates/optimizer-lp/src/reduce.rs)
pads every nonempty segment to 1,024 entries and executes all 1,023 combine steps.
Each [enclosure addition](../../crates/optimizer-lp/src/outward.rs) performs checked
outward arithmetic for both interval endpoints, even for padded zero entries.

Irregular-2048 has 36,645 nonzeros, about 17.9 per column. Its column reductions
nevertheless execute 2,095,104 enclosure combines per certificate, over 525 million
across 251 checks. This is a large structural amplification of sparse work. An
ordinary-f64 diagnostic on exact dyadic inputs also shows nearly constant padded
reduction cost: approximately 230 ns for 4, 18 or 32 values, and 264 ns for 1,024.
A sequential sum of 18 values takes about 4 ns. That is evidence about wasted
padding work, not a measured certificate-optimization speedup or permission to
change the reduction order.

The controller multiplies this cost: irregular-256's GPU runs 250 interval checks,
whereas its adaptive host run closes at the sixth. Full certification on already
infeasible candidates is another possible cost to examine. Every published bound
and success claim must still receive conservative host certification; the GPUP-1
exact-rational regressions remain mandatory for any optimization.

## 3. Startup and launch costs matter; copies are small

For small-4, the new ordinary profile took 477.841 ms, with 386.564 ms in device
setup and only 3.219 ms in the kernel/synchronization phase. Its 200-iteration
untraced companion took 462.714 ms. This case starts at a constructed optimum,
so it mainly measures process/device overhead rather than useful convergence.

Nsight Systems traces independently counted all expected operations:

| 200-iteration trace | small-4 | irregular-2048 |
| --- | ---: | ---: |
| Kernel launches | 1,200 | 1,200 |
| Sum of GPU kernel durations | 1.683 ms | 3.784 ms |
| Span from first kernel start to last kernel end | 3.930 ms | 5.347 ms |
| Sum of GPU copy durations, 17 copies | 0.005 ms | 0.031 ms |
| CPU cuLaunchKernel durations, summed | 3.622 ms | 3.756 ms |
| Stream synchronizations | 21 | 21 |
| Allocations / frees | 20 / 20 | 20 / 20 |

CPU submission and GPU execution overlap: their durations must not be added as
independent phases. Kernel gaps occupy 57.2% and 29.2% of the respective spans;
submission/scheduling and chunk synchronization contribute to those gaps. The
traces do not individually attribute each gap.

Each step issues two matrix-vector products, primal/dual updates and two Halpern
updates. At 50,000 iterations this is 300,000 launches. The driver boundary also
constructs two small host vectors per launch, implying 600,000 small allocations
at that limit. This is a source-derived count, not a separate allocator profile.
The GPU SpMV kernels stage a full 1,024-element reduction with block barriers,
even for short rows/columns. In the irregular trace, each SpMV takes about 7.1 µs;
the four vector-update launches together contribute about 4.6 µs per iteration.
The data do not establish that these kernels are bandwidth-bound. The idealized
bandwidth argument in the kernel source omits substantial padded reduction work;
actual bandwidth/occupancy counters were not collected.

The traces contain cuCtxCreate durations of 135–145 ms and cuCtxDestroy durations
of 65–66 ms. These instrumented API times are parts of startup/teardown, not the
complete setup phase. Tracing increased measured device setup from 356–366 ms to
601–621 ms, and the profiler process took 3.86–4.06 seconds including collection
and failed automatic export. Use the ordinary profiles for untraced latency.
The already-recorded traces were subsequently decoded offline, without GPU reruns.

Reallocating nine working buffers every 200 steps is unnecessary repeated work to
investigate, but its measured allocation/upload/readback cost is small here. The
largest currently demonstrated opportunities precede transfer optimization.

## 4. The study harness is also slow

The three recorded baseline invocations consumed 542.872 seconds of wall time:
173.148 seconds in leased GPU jobs, 202.667 seconds in CPU jobs, 24.459 seconds in
additional standalone verification, and **142.598 seconds outside those categories**.
This remainder includes orchestration, schema validation, telemetry, source/ledger
handling and output. It excludes pauses between invocations and separately executed
report generation; it must not all be labeled schema time.

[validator()](../../tools/validate_artifacts.py) loads and checks every schema afresh
on every call. Direct measurements, three repetitions:

| Validation | Existing path median | Reuse already checked validator median |
| --- | ---: | ---: |
| One ledger event | 118.862 ms | 0.052 ms |
| Irregular-2048 endpoint | 172.842 ms | 53.811 ms |

Both paths reject an added unknown field. A cProfile sample places essentially
all fresh ledger validation time under schema construction/check_schema, not the
event itself. Reuse here is a diagnostic counterfactual; the production runner was
not changed. There are five fresh validations per ordinary trial, plus campaign,
ledger replay and report validations. Replaying 288 historical ledger events alone
implies about 34 seconds of redundant schema setup at the observed cost.

The activity guard also mistakes a nonzero recent utilization sample for evidence
of competing activity. NVIDIA's installed help defines utilization over a past
sampling window of 1/6–1 second, rather than current ownership. The first short
job recorded 0% before and 1% after, then the guard paused; a later check returned
0%. Four diagnostic invocations paused and resumed, without repeating jobs. This
is consistent with detecting our own recently finished work; telemetry does not
exclude every brief external activity. A future fix should distinguish active
processes from stale utilization and wait for quiet telemetry while preserving
the shared lease and competing-work checks. Rebuilding the whole ledger on each
such restart makes these conservative pauses especially expensive.

These harness costs affect campaign/report/resume wall time. They are outside the
fresh optimizer-process timing and do not explain the solver's 9.276-second latency.

## Priorities and limits

1. Establish the GPUP-3 shared controller, then compare convergence fairly.
2. Reduce redundant schema construction and avoid full-run restarts for stale
   utilization samples in a separate bounded tooling fix.
3. Profile and optimize host certification's padded work and check scheduling,
   retaining conservative authority and independent exact-rational acceptance.
4. Then assess launch/fusion, sparse reduction and residency improvements under
   GPUP-4. Preserve fresh-process startup costs in the single-solve objective.

The supplementary profiles have one sample each, with no new confidence intervals
or winner claims. CPU call-stack sampling was unavailable because perf_event_open
is denied; component timings, source inspection and cProfile supplied the host
attribution. GPU bandwidth/occupancy remain unmeasured. This diagnosis does not
implement a precision recipe or change existing defaults.

## Evidence, accounting and reproduction

Raw evidence remains ignored under artifacts/gpup2-diagnosis-v1. diagnosis.json
contains measurements, replay checkpoints and trace summaries; artifact-hashes.json
indexes source, results, witnesses, traces and logs. Its source snapshot records
base revision 978c98cfa1c323da23845c315b651f2396dbc114 plus the diagnostic edits.
Postprocessing/report tooling was completed afterward. The release solver and
code-object hashes exactly match the baseline.

| Artifact | SHA-256 |
| --- | --- |
| diagnosis.json | `0c79e7bb322df44fdcaa7cc8679d0a6c7347138d721562822638eb44b570a7cb` |
| artifact-hashes.json | `37bd268489e44f2d34919eb0ff5f2aea5d42426f7af67eff651c57ad6415169e` |
| cumulative ledger.jsonl | `9a1bed26e90ad69bc641355c68ca6edff055268a3971f948df69cc89abeb254f` |
| measured source.tar | `8547a15c59524e52817aea7b38d0972785743da56b39930624aea184fb70d848` |

Additional GPU study consumption was **20.994604580 seconds** of the 120-second
diagnostic allowance, including trace/export failures. Cumulative study consumption
is **194.142866023 seconds** within the original 900-second Slice 2 allowance,
1,800-second baseline phase and 28,800-second campaign total. The original baseline
ledger prefix and summary hash remain unchanged. No new GPU acceptance workload
was needed: runtime/kernels were unchanged and every diagnostic endpoint verified.

```bash
cargo build --release -p optimizer-experiment --example lp_diagnose --locked
# CPU costs; use replay with irregular-256 or scaling-64 to compare GPU bits.
target/release/examples/lp_diagnose cost \
  artifacts/lp-inputs-v1/gpup-development-irregular-2048.json \
  artifacts/gpup-baseline-v1/profile-gpup-development-irregular-2048-0-cuda-lp.endpoint.json
python3 tools/diagnose_lp.py
bash tools/check.sh
# Only unattempted frozen diagnostics can launch; preserve the existing ledger.
python3 tools/diagnose_lp.py --gpu
python3 tools/analyze_lp_diagnosis.py
```

The completed local bundle is for analysis; a true resume with pending jobs must
use the archived diagnostic source identity. Later source changes are refused
before launch and cannot silently replace completed measurements.

The installed Nsight Systems 2025.3 importer initially lacked libdw.so.1. The
Ubuntu libdw1 0.186-1ubuntu0.1 package was downloaded and extracted privately under
/tmp/gpup2-nsys-libs; no system library or project dependency was changed. For each
saved trace, run the installed QdstrmImporter with --input-file TRACE.qdstrm and
--output-file TRACE.nsys-rep, then nsys export --type=sqlite --output=TRACE.sqlite
TRACE.nsys-rep. Supply LD_LIBRARY_PATH=/tmp/gpup2-nsys-libs/root/usr/lib/x86_64-linux-gnu.
trace-import.json records the importer/package hashes. This offline recovery used
no GPU time. Completed diagnostics must not be rerun to replace their evidence.
