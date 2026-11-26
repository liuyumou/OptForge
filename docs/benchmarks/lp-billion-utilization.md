# GPU utilization and retained-memory diagnosis

Date: 2026-11-23. The diagnosis uses retained image-v11 project responses and
the final COPT comparison. The subsequent authorized candidate is opt-in;
original images and pre-change numerical sources remain retained exactly.

## Findings

The solver alternates GPU advancement with synchronous CPU work. Its device
matrices, iterates and scratch remain allocated during that work. This explains
why busy GPU intervals can alternate with low/zero utilization while memory stays
high. The evidence identifies substantial opportunities to shorten these waits;
it does not timestamp the user's particular utilization samples.

NVIDIA defines GPU utilization as the fraction of a sampling period containing
kernel execution. It does not measure achieved bandwidth, occupancy, useful
iterations or Tensor Core efficiency. An allocation can persist with no kernel
executing, and short bursts can produce very different adjacent samples. See
[NVIDIA's metric definition](https://docs.nvidia.com/deploy/nvidia-smi/).

Latest project responses in the final COPT comparison:

| Family | GPU advancement host interval (s) | Strict assessments (s) | Checkpoints (s) | Witness output (s) | Upload + download (s) |
| --- | ---: | ---: | ---: | ---: | ---: |
| irregular | 488.200 | 459.063 | 67.300 | 66.462 | 85.376 |
| tall | 64.619 | 88.131 | 9.375 | 12.259 | 10.054 |
| ill-scaled | 692.313 | 703.532 | 101.424 | 124.220 | 124.646 |

These are exclusive host elapsed intervals. Advancement includes submission and
synchronization; certification includes GPU feasibility and CPU dual/gap work.
Neither column is kernel-active time or an observed utilization percentage.
Tall's original complete-cost timing remains excluded. Missing wide, coupled
and degenerate project responses cannot provide phase attribution.

The [solver](../../research/lp-billion-lowbit/src/billion.rs) downloads an endpoint
at each 100-update control boundary, performs control, and uploads state before
the next window. Every 500 updates, and at the last window, it assesses the
original model and writes witnesses. A checkpoint clones the rollback state
before a window. These operations serialize progress, with buffers kept resident.
Moving control to the GPU has already reduced its cost substantially; it has
not eliminated CPU certification, checkpoint copying or witness I/O.

The [assessor](../../research/lp-billion-lowbit/src/array_assessment.rs) calls GPU
feasibility, then the authoritative CPU dual enclosure and gap check. Potential
acceptance also requires original CPU feasibility and identical objective bits.
The [bounded checker](../../research/lp-billion-lowbit/src/bounded_certificate.rs)
still traverses the original sparse matrix with outward interval arithmetic.
Four CPU workers partition columns by count, which need not balance nonzeros.
Uneven work is a source-level possibility; no worker imbalance measurement was
retained, so it is not claimed as the measured cause of these timings.

Device allocation happens before initial control and remains until after final
assessment. Intermediate witness writes also retain it. Final endpoint output
occurs after device teardown. Input hashing/loading happens before the solve
creates device buffers, and the separate independent final checker runs after
the solve. Those two expensive phases reduce experiment-wide GPU duty time but
cannot explain residency of this solver's main buffers. They must not be
described as an allocation leak.

For scale, the earlier coupled billion run spent 8.190 s advancing, 67.101 s in
strict assessments, 100.017 s loading/validating input and 132.358 s in the
independent final check (371.999 s complete). These figures belong to the earlier
1000-update cohort, not the missing coupled project response in the latest fair
comparison. See the [retained control report](lp-billion.md#gpu-assessment-and-control-with-strict-cpu-acceptance).

COPT is separate: the retained irregular run reached GPU PDLP only around 1060 s
into supervised activity. Its native solve interval includes opaque vendor
preparation. The original failing billion attempts never logged GPU PDLP startup.
This supports a long startup explanation, but not an attribution to GPU OOM,
an import bug, thermal throttling or a particular internal vendor phase.

## Concrete optimization order

1. Reduce exact CPU certification cost. Preserve original outward arithmetic,
   reduction order, first-refusal behavior and strict 1e-9 authority. A bounded
   candidate is to partition independent column work by cumulative nonzeros,
   retain each column's arithmetic unchanged, and concatenate results in original
   order. Establish worker balance with CPU timing before selecting it. Reuse
   worker scratch where exact arithmetic permits. This targets repeated long-run
   stalls; the gain remains unmeasured.
2. Remove redundant final assessment only when the exact endpoint is unchanged.
   All six 64 M v11 runs and four uncertified earlier billion v11 runs have an
   extra assessment of the same final primal/dual content descriptors and the
   same certificate. Certified tall already reuses its certificate. The latest
   irregular and ill-scaled deadline runs have different final endpoints after
   rollback: reuse there would be wrong. A solve-local cache must bind the exact
   state version (physical/logical iterations plus restoration generation),
   immutable model and tolerance; preserve repaired-dual evidence and deadline
   status. Do not cache across solves or remove the independent final proof.
3. Shorten CPU-only tails that retain device allocations. Split final GPU
   feasibility from the remaining CPU proof and release buffers after their last
   use, while retaining all required proof inputs. This reduces memory residence;
   it does not by itself increase useful GPU execution. Do not free/reallocate
   matrices at every intermediate certificate boundary.
4. Measure checkpoint copying and durable witness writes before designing bounded
   overlap. Any overlap must retain snapshot ownership, deadline rollback,
   write-error propagation, completed witnesses and the aggregate memory cap.
   Unbounded background work or overlapping independent solves is not admitted.

CUDA graphs or further kernel tuning address only the advancement interval and
cannot remove these CPU waits. Increasing check intervals, dropping proofs,
weakening tolerances or running dummy kernels would not meet the objective.

The success measure is lower complete time to the same strictly certified result,
with phase-attributed GPU duty time and allocation lifetime as supporting metrics.
High sampled utilization alone is insufficient. A future admitted trace should
align phase boundaries, kernel activity and owned memory on a common timeline;
the retained aggregate profiles cannot retrospectively provide that trace.

## Reproduction and admission boundary

The new [offline reader](../../tools/lp_billion_utilization_report.py) verifies
response source hashes and exact phase coverage, preserves missing/vendor rows,
and checks final endpoint/certificate identity without loading deleted large
vectors. Its JSON leaves utilization, kernel-active time and duplicate-call
duration unknown. No savings are inferred by dividing aggregate assessment time.

Run through a fresh CPU reporting reservation:

```sh
python -B tools/lp_billion_utilization_report.py docs/benchmarks/lp-billion-utilization-results.json
```

The command creates its output exclusively; it never overwrites retained evidence.
The [focused tests](../../tests/integration/test_lp_billion_utilization_report.py)
cover rollback, changed dual/certificate, already-reused certificates, missing
responses, opaque vendor phases, corrupt coverage and false kernel-time claims.

The current [handoff](../../AGENTS.md) requires existing numerical bindings to
remain exact, and [amendment 90](../specifications/SPEC-0046-amendment-90.md)
requires fresh CPU36/GPU28 and availability checks for future development.
Amendments 91-93 subsequently authorize and admit the new versioned scope.
CPU37 and GPU28 now pass for the asynchronous resource sources. No old scientific
LP or driver is repeated. The original diagnosis itself launched no GPU work.

Historical preflight status: two fresh reporting launch identities, `utilization-diagnosis-v1`
and `utilization-diagnosis-v2`, stopped at the unchanged 0.9-second native storage
inventory preflight. Neither created a reservation or started its test/report
command. Reporting v3 subsequently passes over 24 retained rows and identifies
ten duplicate candidates; the original refusal receipts remain retained.

## Authorized candidate and GPU certification assessment (2026-11-23)

The original 0.9-second inventory timeout was unreasonable for the observed cold
filesystem: a complete scan took 22.650 s wall / 1.028 s child CPU across 98,195
files. [Amendment 92](../specifications/SPEC-0046-amendment-92.md) admits a
60-second preflight. After an initial automatic approval refusal, the user
explicitly approved the asynchronous runtime policy in
[amendment 93](../specifications/SPEC-0046-amendment-93.md).

New jobs can select `--storage-policy async-v1`: one background inventory after
a five-second interval, a 60-second scan deadline, maximum completed-observation
age of 90 seconds, and a mandatory final full scan. Failures retain full charges.
The existing outer allowance includes a 75-second finalization reserve; the
minimum outer allowance is 120 seconds. RAM/process/GPU sampling retains its
one-second hard limit and 100 ms advisories; legacy runtime requests are unchanged.
CPU37 passes 75 original supervisor and 156 billion harness tests. Its maximum
sample gap/work is 16.008/10.949 ms. Sustained idle and GPU28's sixty exact
continuations pass; all these jobs have complete cleanup and no overrun.

Subsequent validation: the 60-second preflight path passes in 0.354 s with warm
filesystem metadata. CPU36 passes 75 supervisor and 145 billion harness tests
using unchanged runtime sampling, with maximum sample gap/work 0.3105/0.3054 s.
Reporting v3 passes over 24 retained rows and identifies the ten duplicate
assessment candidates; 391 documentation pages and local links pass. Both jobs
have empty cleanup, no overrun and zero GPU charge. This validates the preflight
revision and reporting for that earlier source version.

The user subsequently authorizes the optimization scope. [Amendment 91](../specifications/SPEC-0046-amendment-91.md)
opens a versioned, off-by-default candidate while preserving all historical
images and their original sources. No further authorization is needed to execute
this scope once its operational guards pass.

The first candidate is implemented in
[scratch_certificate.rs](../../research/lp-billion-lowbit/src/scratch_certificate.rs).
Set `fast.certificate_scratch=true` only on the original-array solver to select it.
The default still uses the original bounded checker; the legacy solver explicitly
rejects the new option. Each worker reuses a product vector across columns, and
each reduction compacts its original 1024-leaf tree in place. This removes the
per-column reduction copies and allocations without changing enclosure primitives,
column ordering, first-refusal behavior or the authoritative acceptance check.
The buffers are local to one certificate and do not cache results between endpoints.
Worker scratch retains capacity for its largest visited column until that worker
finishes; future capacity admission must account for all four such buffers plus
row/column terms and repaired multipliers. There is no whole-matrix checker graph.

Regression cases cover the original 640 full-certificate comparisons, exact
signed-zero/subnormal/overflow behavior, a reduction exceeding 1024 squared
entries, scratch reuse after refusal, first-column error ordering, false device
feasibility and explicit option/default behavior. Native quality now passes 69
tests, formatting, Clippy and the release build. Image-v12 contains the new
executor and exact copies of the five other image-v11 files, including all CUDA
modules. CPU measurements use six alternating-order pairs per matrix shape.

`fast.final_assessment_reuse=true` independently enables conservative final reuse.
It reuses an existing certificate only for an iteration-limit endpoint with the
same solve-local physical/logical iteration and restoration generation. Model
and tolerance are immutable within the solve. Restart changes anchors and weight,
not the assessed vectors; a native regression checks those endpoint bits.
Cancellation, deadline and numerical-failure tails recompute. The certificate's
repaired-dual evidence is retained, and independent final checking is unchanged.
Both options default to false and are rejected by the legacy interface.

The first CPU36 preflight stopped at the unchanged 0.9-second inventory timeout before
creating a reservation. A subsequent diagnostic of that same bounded preflight
records 0.912 s wall time and 0.066 s child user+system CPU. Storage latency or
scheduling delay is consistent with this gap; the measurement does not separate
them. Subsequent revisions and acceptance are described above; the old refusal
remains exact. All receipts are retained under `utilization-optimization-v1`
and the new resource identities in the evidence tree.

## Candidate measurements and disposition

All 240 continuations pass exact comparison against image-v11: sixty fixtures
cover four formats, recovery/cancellation and all four combinations of the two
new options. The original scalar checker independently validates 520 returned
endpoint claims. The native suite passes 69 tests; the operational suites pass
75 supervisor / 156 harness tests and sixty GPU continuations. All reservations
pass with complete cleanup and no overrun. All 306 original numerical bindings
are accounted for: 299 unchanged, seven scoped integration files with exact
originals retained. All six original image-v11 files remain exact.

The CPU-only certificate microbenchmark uses about one million nonzeros in each
of three shapes and six alternating-order pairs. Median paired reference/candidate
ratios are 1.222 (short columns), 1.061 (balanced), and 1.032 (long columns).
Every bound, rounded value, allowance and repair count matches exactly.

Fresh 4,194,304-nonzero FP32 pairs use 1000 updates, control100/certificate500,
strict original-model 1e-9 checks and a 30-second native allowance. All three
pairs have exactly matching numerical continuations. Each of the six responses
receives two distinct independent proofs covering its final and intermediate
claims. Tall certifies in both variants; irregular and coupled remain uncertified
iteration-limit results.

| Family | Strict assessment, reference → candidate (s) | Calls | Complete time, reference → candidate (s) |
| --- | ---: | ---: | ---: |
| irregular | 0.473 → 0.239 | 3 → 2 | 2.807 → 2.196 |
| tall | 0.231 → 0.208 | 2 → 2 | 1.946 → 2.090 |
| coupled | 0.256 → 0.164 | 3 → 2 | 1.916 → 1.697 |

Complete time includes fresh-process original input/CSR-to-CSC construction and
the cold independent final proof; shared model generation and additional offline
proofs are separate. These are single rotated pairs, with unflushed caches and a
shared content-addressed witness store. The second writer can reuse files:
irregular witness output takes 0.418/0.027 s (reference first), while tall takes
0.017/0.112 s (candidate first). This confounds complete-time ratios. The 7.4%
tall regression and all uncertified outcomes remain visible. No general
certified-solve speedup or measured GPU-utilization increase is established.

Keep both optimizations opt-in. They shorten exact CPU checking and remove a
proven duplicate call without changing GPU advancement or proof authority.
Earlier device release, checkpoint overlap and a GPU certificate screen remain
separate future work. The [compact validation and measurements](lp-billion-utilization-optimization-results.json)
bind the complete evidence; the [original diagnostic JSON](lp-billion-utilization-results.json)
remains unchanged. No historical scientific cell or driver was repeated.

Final reporting passes 392 documentation pages/local links. The
[settled receipt](lp-billion-utilization-checkpoint.json) records 3881.803214088
CPU / 285.322280343 GPU seconds for this scope, within amendment 91 and every
original phase cap. All 1852 recorded owned identities from the scope are absent;
no reservation or monitor remains active. All 68 existing failed reservations
and their charges remain intact; every new reservation in this scope passed.

## GPU certification assessment

GPU-assisted certification is a worthwhile next research direction. Its parallel
column products and enclosure reductions could replace long CPU intervals. CUDA
supports explicit FP64 rounding directions and controls for FMA contraction,
which can support an interval implementation, but do not automatically reproduce
our CPU tree or its refusal semantics. See [NVIDIA's floating-point documentation](https://docs.nvidia.com/cuda/floating-point/index.html).
Atomically accumulating a dot product or substituting a plain FP64 residual does
not establish our conservative bound.

The architectural constraint is independent authority, not a claim that GPUs
cannot perform rigorous arithmetic. Under [ADR-0010](../decisions/ADR-0010-certified-gpu-lp.md),
an erroneous GPU computation must not certify itself. A useful hybrid would run
device screening and tentative diagnostics, then recompute the original CPU proof
before accepting a bound or declaring success. Screening failures must remain
unverified diagnostics and cannot be published as authoritative infeasibility.
Periodic CPU checks and a mandatory final CPU check would also protect against a
bad screen suppressing progress indefinitely.

Merely adding GPU dual/gap calculations while retaining every existing CPU
certificate would duplicate work. Avoiding those CPU calls would change the
current certificate500 and intermediate-evidence contract, so that protocol change
is not part of the scratch candidate. A future separately specified hybrid must
preserve strict final CPU authority, retain tentative versus certified status,
measure device memory and FP64/interval throughput, and include the final proof
in complete timing. The GPU is not automatically the faster location for the
integer exactness checks and branches in this particular enclosure implementation.
