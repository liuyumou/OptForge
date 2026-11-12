# DELIVERY3 diagnosis: startup first, prepared arithmetic conditional

Further precision work cannot deliver the cold-latency target on this execution
path. Even removing **all** recorded GPU event time from the improved native
control gives only **1.0094x** on the dense cold target. The next recommended task
is [GPUP-DELIVERY4](../plans/lp-delivery4.md): attribute and reduce startup and
lifecycle costs, beginning with the serial host preparation and unresolved outer
latency. MIXED2 remains a plausible prepared-throughput alternative, subject to
actual matrix-only attribution and its numerical contract.

This is an exploratory CPU-only reanalysis of the committed [DELIVERY3
study](lp-delivery3.md), not another experiment or retention decision. The
[reproducible analyzer](../../tools/lp_delivery3_diagnose.py) checks all 39 portable
archive hashes, all 6144 confirmation cells / 12288 solves and the exact original
eight retention decisions. All 11264 certificates and 1024 intentional refusals
remain represented. The [machine record](data/delivery3-diagnosis-v1.json) retains
all family/lane/tier summaries, paired observations, environment associations,
profile summaries and cost bounds. The [diagnosis plan](../plans/lp-delivery3-diagnosis.md)
defines scope and separate accounting. To reproduce from a checkout, run
`python3 tools/lp_delivery3_diagnose.py --output /tmp/delivery3-diagnosis-reproduced.json`
with a new output filename; the command reads committed archives and refuses to
overwrite an existing output. It needs no scientific binaries or device.

## 1. Cold execution is overwhelmingly outside the GPU event interval

The table uses arithmetic means of per-record additive components for strict
1e-9 dense512, with the selected overlap-only cold configuration. Each lane has
32 fresh processes. GPU event time is subtracted from the enclosing iteration
timer before summation. These means explain costs; they do not replace the
study's median-of-block-ratios retention estimand.

| Complete-path component | Native ms | FP4 ms |
| --- | ---: | ---: |
| Session setup | 371.183 | 371.759 |
| Prepare/reset | 11.033 | 14.420 |
| GPU event interval | 5.423 | 4.500 |
| Iteration outside GPU events | 5.292 | 4.713 |
| Original-A audit | 0.796 | 0.805 |
| Independent checker phase | 6.905 | 6.986 |
| Export | 0.149 | 0.481 |
| In-solve coordination | 0.895 | 0.908 |
| Outside both setup and solve | 113.843 | 112.105 |
| **Complete cold delivery** | **515.519** | **516.677** |

Setup plus the outer remainder account for approximately **94%** of complete
cold time. The outer remainder includes process/runtime entry, result construction
and serialization, EOF/exit, owned-resource destruction, parent collection and
durable writes. It is **not** a measured CUDA teardown interval or PCIe transfer.
Its 112–114 ms warrants instrumentation before attributing a cause.

The [timer boundaries](../../research/lp-delivery3/src/main.rs) and
[EOF transport](../../tools/lp_delivery2_transport.py) establish these inclusions.
`solve_ns` ends before the response JSON is assembled. Prepared `setup_ns` is
repeated metadata, not a per-solve cost; it is never added to prepared solve time.

## 2. Existing startup spans identify a serial host prerequisite

The separate instrumented cohort has only two fresh blocks per configuration.
For strict dense512 native cold execution, mean spans are:

| Startup span | Control ms | Overlap ms |
| --- | ---: | ---: |
| Host model read/preparation | 124.697 | 125.876 |
| Early checker spawn | 0.001 | 0.368 |
| CUDA context/module/stream | 237.031 | 247.061 |
| Checker spawn or final join | 207.360 | 0.009 |
| Device-image read/hash binding | 8.941 | 8.201 |

Overlap successfully hides checker readiness behind CUDA setup. However,
`Data::new` still completes **before either operation begins**. Its source includes
JSON decoding, original LP construction, row scaling, dense representation,
norms/initial state and original-byte hashing. The retained spans cannot separate
those costs. Moving or reducing this approximately 125 ms serial prerequisite is
a better cold hypothesis than faster inner arithmetic; its full duration is not
a guaranteed saving because concurrency changes contention and failure handling.

The independent checker itself takes about 201 ms to become ready in this
profile: 8.397 ms reading the model, 118.879 ms constructing its model/checking
plans, and **73.820 ms after preparation**. The last interval includes reading and
hashing its executable, hashing original model bytes for readiness, formatting
and sending readiness. Calling the entire 201 ms "model parsing" would be wrong.
This interval is already hidden in the overlap route, so speeding it alone need
not shorten the critical path. Parent and child startup spans overlap and must
not be summed.

These are source-supported attribution targets, not new measured optimizations.
See [host preparation](../../research/lp-fp4-accel/src/model.rs) and
[checker startup](../../research/lp-delivery3/src/transport.rs).

## 3. Prepared time has several comparable costs

The selected batching-only strict dense512 route has 32 independent sessions
and three fresh reset/certificate solves per session. The following means use
all 96 solves per lane, including slow observations:

| Complete-path component | Native ms | FP4 ms |
| --- | ---: | ---: |
| GPU event interval | 5.417 | 4.484 |
| Iteration outside GPU events | 4.840 | 4.462 |
| Independent checker phase | 5.191 | 5.157 |
| Prepare/reset | 0.730 | 0.705 |
| Original-A audit | 0.729 | 0.725 |
| Export | 0.144 | 0.448 |
| In-solve coordination | 1.566 | 1.509 |
| Outside solve timer | 1.642 | 1.940 |
| **Complete prepared solve** | **20.259** | **19.431** |

Against matched control means, native saves 1.975 ms, of which 1.356 ms comes
from the checker phase and 0.255 ms from outside-solve delivery. FP4 saves
2.167 ms, of which 1.252 ms comes from checking and 0.327 ms from outside-solve
delivery. GPU event means are essentially unchanged. These paired-cohort mean
changes support delivery attribution but are not a new FP4-versus-native
significance claim. Both strict dense512 lanes still take 200 updates.

## 4. Batching has already removed most request-writing cost

In the two-block instrumented strict dense512 prepared cohort, native request
build/encode/write/flush falls **1.803 -> 0.081 ms**; FP4 falls
**1.656 -> 0.081 ms**. In the batched profiles, the independent child assessment
still takes **4.979 ms native / 4.659 ms FP4**, including its exact mathematics,
endpoint hashing and result construction. Child decode is about 0.19 ms, child
response send about 0.007 ms, and parent response binding about 0.12 ms.

Parent wait/read includes overlapping child work. It must not be added to the
child duration. Child assessment was slower in these batched diagnostic samples
than in control, despite unchanged mathematics; two blocks cannot establish that
batching causes slower checking. The broader uninstrumented cohort confirms a
net checker-phase reduction. Further pipe batching alone is unlikely to provide
another multi-millisecond saving; exact checker work is now the larger measured
part of that phase.

## 5. Iteration variability is concentrated outside GPU events

Across the 96 selected strict dense512 prepared solves:

| Recorded span | Native min / median / max ms | FP4 min / median / max ms |
| --- | ---: | ---: |
| GPU event interval | 5.346 / 5.418 / 5.705 | 4.449 / 4.485 / 4.623 |
| Iteration outside events | 0.159 / 5.558 / 27.027 | 0.154 / 5.265 / 9.940 |
| Checker phase | 4.063 / 4.869 / 7.287 | 3.852 / 4.853 / 6.946 |

The outer iteration remainder is much more variable than the event interval.
Its descriptive correlation with total time is 0.972 native / 0.963 FP4;
this is partly a part-whole correlation and does not identify a cause.

[Device source](../../research/lp-fp4-accel/src/device.rs) shows a synchronous
report reset before the start event and report download/synchronization after
the end event, plus event-query/report bookkeeping. These are candidates within
the remainder. The event interval itself encloses per-update launch sequences
and can include stream/host-submission gaps; it is not pure matrix arithmetic.
The [copy boundary](../../crates/optimizer-cuda-sys/src/lib.rs) synchronizes to
keep borrowed host buffers alive. Eliminating a wait without changing ownership
would violate that contract. A future profile should separate copy, synchronize,
launch and bookkeeping costs before proposing a safe scheduling change.

## 6. The arithmetic cost case depends on lifecycle and workload

For every selected native record, transform total time `T` to
`T - A + w*A/s + O`, where `A` is the whole recorded GPU event interval. The table
assumes unchanged updates/certificates (`w=1`) and zero added overhead (`O=0`).
Transform each solve first, then take the prepared session median, the equal-
weight dense128/256/512 geometric mean within each block and the median of 32
blocks. These are **optimistic forecasts**, not measured gains or confidence
intervals. Actual MIXED2 affects only a subset of `A`.

| Lifecycle / tier | Entire GPU event 2x faster | 4x faster | Entire event removed |
| --- | ---: | ---: | ---: |
| Cold / 1e-7 | 1.00468x | 1.00703x | 1.00940x |
| Cold / 1e-9 | 1.00468x | 1.00704x | 1.00940x |
| Prepared / 1e-7 | 1.15945x | 1.25990x | 1.37943x |
| Prepared / 1e-9 | 1.15163x | 1.24617x | 1.35770x |

The cold cost case fails decisively under these assumptions. A 2x speedup of the
*entire* event interval could support a prepared dense gain, but the median
extra-cost allowance before losing 1.10x is only **0.471 / 0.555 / 0.795 ms** for
strict dense128/256/512 respectively. Conversion, guards, recovery or extra
updates consume this allowance. Matrix-only speedup could be materially smaller.

Six small bounded families also fail the strict prepared 1.10x ideal event-removal
bound: coupled equality/inequality, fixed active bounds, ill-scaled coupled,
irregular tail and ranged one-sided yield only **1.085–1.089x**. This argues for
an explicitly scoped prepared dense hypothesis, with all other families retained
as coverage/regression guards. It does not justify dropping unfavorable families
from an existing experiment.

## 7. Three prepared solves do not amortize session costs

Strict dense512 batching-only setup plus teardown averages **715.091 ms native /
720.364 ms FP4**. The primary prepared metric intentionally excludes both. Adding
those measured costs back and dividing over the three measured solves gives
**258.623 / 259.552 ms per solve**, versus 20.259 / 19.431 ms for the solve-only
means. This still excludes the runner's numerical comparison, result reread/hash
and coordination work: another 97.728 / 101.662 ms per three-solve batch, retained
separately in the machine record.

Holding measured solve means and session overhead fixed, amortization over 10
solves forecasts 91.768 / 91.467 ms, and over 100 solves forecasts
27.410 / 26.634 ms. Those larger batches were **not run**; sustained throughput,
resource lifetime and later-solve behavior remain unmeasured. Prepared batching
uses the sequential-startup configuration selected before confirmation; no
unconfirmed overlap-plus-batching dispatcher is substituted into these forecasts.

First-solve behavior does not support a universal warmup penalty. Within each
selected session, first minus the mean of solves two and three has median
**-0.486 ms native / -0.317 ms FP4**; corresponding means are -0.555 / +0.193 ms.
The distributions include both signs. No first solve is dropped, and later solves
retain fresh reset/checking rather than warm iterates or old certificates.

## 8. Unresolved guards remain uncertain; no single cause is established

All original simultaneous intervals and decisions reproduce exactly. The nine
unresolved family guards exceed the permitted excess-cost boundary in **6–9 of
32 blocks**. With the frozen upper endpoint at sorted rank 27, six or more
positive observations suffice to keep that endpoint positive. This explains the
classification mechanically; it does not show the allowance or correction was
inappropriate, or that those observations should be removed.

All nine unresolved guards have favorable median control/candidate ratios in
both pair-order groups, each containing 16 blocks. Ordering therefore does not
expose an obvious consistent reversal, but neither group establishes safety.
At strict dense512, prepared paired control/candidate total-time correlations
are 0.903 native / 0.816 FP4, consistent with shared block variation. Prepared
ratio medians shift from 1.069 to 1.103 native and 1.076 to 1.092 FP4 between
first and second halves; cold paired medians are comparatively stable near
1.39–1.40. These are post hoc descriptions, not a drift-adjusted estimate.

The full record retains every block and every order, time, load, temperature,
clock, memory and utilization association. Across the nine unresolved guards,
start-utilization correlations with log ratios range approximately -0.440 to
+0.010, and end-utilization correlations range -0.235 to +0.238. Their inconsistent
sizes, coarse block-boundary sampling, shared device and many exploratory
comparisons do not identify GPU contention as the cause. No p-value, new
qualification or independence claim is derived from these associations.

DELIVERY2's earlier prepared slowdown remains unexplained, and its failed gate
is unchanged. DELIVERY3's four modest prepared benefit results remain insufficient
or inconclusive; this diagnosis does not promote them to retention passes.

## Next task and durable findings

[GPUP-DELIVERY4](../plans/lp-delivery4.md) is the recommended next task for the
existing cold-latency priority. Start with CPU attribution of host model/LP
construction and readiness hashing, then an independently admitted lifecycle
profile for process entry/output, checker shutdown, buffer/module/context teardown
and durable collection. Evaluate safe startup concurrency only after preserving
input admission, independent checking, exact provenance and bounded cleanup.
Choose one concrete optimization from those measurements before a new frozen
confirmation; do not rerun DELIVERY3 until a threshold is crossed.

MIXED2 remains ready for its separate CPU numerical contract and matrix-only
prepared cost attribution. No mixed-precision device allocation follows from
these optimistic full-event bounds. The variable iteration remainder is another
specific prepared-path measurement target. Neither target releases TENSOR2,
GPUP-8 completion or GPUP-9.

The user's standing instruction to record useful diagnostic findings is retained
in [AGENTS.md](../../AGENTS.md). Future diagnoses should record supported,
negative and inconclusive findings with evidence, limitations and task implications.

## Validation and accounting

The analyzer validates timer closure for all records, including zero-update
intentional refusals; keeps all 32 blocks, both lanes and tiers; checks adjacent
pairs and exact 16/16 counterbalance; and reproduces the original decisions.
Six focused tests cover nested timers, prepared setup exclusion, zero-update
refusals, malformed timers, added work/overhead and undefined constant correlation.
The composite repository CPU/native gate and final preservation checks are recorded in
[acceptance](data/delivery3-diagnosis-acceptance-v1.json).

The first analyzer attempt incorrectly assumed every refusal had an iteration
timer. Its `KeyError`, source snapshot and full **480 CPU-second** reservation
remain retained; the corrected analysis treats missing iteration time as zero
and verifies the GPU counter is also zero. No scientific cell was retried.
Subsequent added variability/overhead summaries preserve the prior analysis output.
The full native launcher then passed Rust, 669 Python tests and committed-record
replay but failed documentation validation on a new handoff's relative link.
Its full **3600 CPU-second** reservation remains charged. After correcting only
the links, the documentation/smoke tail is run separately; this is reported as
composite full coverage, not a passing status for the failed original launcher.
A first final-verification attempt then encountered an undeclared YAML import in
the acceptance helper; its source/log and full **480 CPU-second** reservation
also remain charged. The corrected helper validates the retained backlog's
explicit one-line task format with the standard library and rejects other syntax.
This packaging failure changes neither analysis results nor software test outcomes.
A second verifier attempt counted only the 637 direct workspace Rust tests and
missed the additional buffered-transport Rust test invoked during Python acceptance;
its full **240 CPU-second** reservation is retained. Final acceptance records
637 workspace plus one buffered-transport test (638 total) explicitly. A third verifier completed the substantive checks but hit the immutable writer
when publishing over a pending documentation-link receipt; its full **240 CPU
seconds** are retained. Final publication preserves the pending draft and permits
only a pending-to-final transition; existing successful receipts cannot be
replaced. These five failed reservations total **5040 CPU seconds**; none is a
scientific cell failure.

The separate allocation is closed at **5784.673587084 / 8000 CPU seconds**, with
**zero GPU**. This includes 512 preparation, 128 closing administration and all
5040 CPU seconds of failed reservations. All supervisor cleanup is empty; 1756
historical tracked files, older handoffs and all prior backlog entries remain
exact. Final charges, full failed reservations, source versions,
receipts and empty cleanup are in [accounting](data/delivery3-diagnosis-accounting-v1.json).
No historical allocation was reopened. Software acceptance runs its ordinary
CPU/native correctness and replay checks; there was no new scientific solver,
checker or device study. Public defaults and historical numerical sources stay exact.
