# General LP scale development with COPT

Status: development measurements complete under [SPEC-0045](../specifications/SPEC-0045-general-lowbit-lp.md),
2026-11-17. The objective remains a broadly useful single-solve LP solver whose
performance improves through low-bit arithmetic, including actual FP4 Tensor
Cores. This continuation implements the first stages of the
[public-benchmark scale design](../plans/lp-benchmark-scaling.md). It does not
freeze confirmation, alter historical criteria or change public solver defaults.

Compact transport and exact shared host improvements are delivered. Scaling to
16 million nonzeros exposes up to a 5.332x median FP4 execution-phase advantage
on the coupled family, with complete costs near parity. Preparation,
original-model control/checking, response transport and sparse FP4 coverage
remain the main engineering targets. Broad FP4 superiority remains unestablished.

## Population and original input

The connected structural population has six families, three seeds and targets
of one million and four million original matrix nonzeros: irregular, wide,
tall, coupled blocks, ill-scaled and degenerate. The generator uses ordinary
binary64 coefficients, active bounds, inequalities and independently sampled
long-range links. Wide and tall use 1:4 and 4:1 row-to-column aspect ratios.
Its exact construction witnesses are retained separately and
never enter solver inputs. All 36 lower-scale generated models have one bipartite
connected component. These are structural experiments, not six independent
application families.

An earlier generator produced disconnected wide models. Those inputs and their
diagnostic pilots remain retained under version 1. Version 2 adds a connected
backbone and global links; full scale studies use version 2. No old input or
observation is overwritten.

| Public original / continuous relaxation | Rows | Columns | Matrix nonzeros |
| --- | ---: | ---: | ---: |
| MIPLIB square31 | 19,435 | 28,860 | 3,937,200 |
| Mittelmann scpm1 | 5,000 | 500,000 | 6,250,000 |
| Mittelmann pds-100 | 156,243 | 505,360 | 1,086,785 |

PDS-100's published 1,390,539 count includes its 303,754 objective coefficients;
the extra published row is the objective row. The two conventions must not be
confused. Public inputs are compared through COPT and an independent HiGHS MPS
reader before integrality is removed. Coefficients, CSR structure, bounds,
objective sense and offset must agree exactly. No MIP presolve is used.

`LPCSRA01` transports original CSR data without quantization or giant JSON model
objects. Both readers check exact length, dimension/index domains, ordering,
bounds and finite coefficients. Numerical domains remain at most 2^20 rows or
columns and 2^26 matrix entries. Larger ladder stages retain explicit dimension,
host/device-memory and per-file capacity prerequisites. This delivery does not
claim execution of the 64 M–8 B design stages or the application-generator work.
The prospective 16 M extension applies the same capacity checks to all six
families and three seeds. Tall and coupled blocks fit: six generated models and
30 solver lanes. The other twelve model records retain their capacity refusals
and all sixty unexecuted lanes. This subset is selected by capacity before
solver outcomes; it cannot establish broad 16 M coverage.

## Shared implementation improvements

The opt-in host reduction removes padded zero work while preserving the original
1024-leaf reduction tree, signed zeros and exceptional behavior. Up to four host
workers process independent output rows. The same products accelerate spectral
preparation through an isolated engine adapter, including exact step sizes above
one. An earlier implementation redundantly repeated preparation when its step
exceeded one; its slower version and pilot remain retained.

The exact checker is prepared lazily after the first failed assessment when more
checks remain. It reuses previously admitted immutable coefficient geometry;
endpoint answers are never cached. The certificate criteria, assessment cadence,
FP64 state and original-model authority remain unchanged. Native, FP32 and FP4
receive these shared improvements. The public core numerical sources remain
byte-identical.

Automatic scheduling selects split products when either orientation averages
more than four tiles per output group, otherwise retaining the combined schedule.
This uses matrix structure rather than model names. Each choice preserves its
explicit schedule's arithmetic. Combined and split reductions can round
differently, so admission compares the candidate to the corresponding schedule.
The device image remains `fast-image-v10`; no new Tensor Core instruction claim
or hardware-counter measurement is made here.
FP4x2 represents a coefficient with two normal-E2M1 components: eight logical
coefficient bits plus scales, indices and retained original data. It is not a
four-bit-total-storage claim. Accepted FP4 work excludes sparse fallback work.

## Baseline and measurement contract

COPT 8.0.6 is loaded from a pinned local environment whose native libraries match
the authorized `/root/copt80` installation. CPU auto uses four threads, automatic
LP method and crossover. GPU PDLP uses the pinned GPU, method 6 and no crossover;
logs establish whether GPU execution actually occurred. Both have a 30-second
solver limit, MatrixTol=0 and explicit feasibility/duality tolerances. Import,
environment, conversion, solve and teardown times remain separate. COPT's
reported arithmetic precision is not inferred from its GPU use.
The retained execution logs identify an Intel Xeon Platinum 8457C host and an
NVIDIA RTX PRO 6000 Blackwell Server Edition GPU (compute capability 12.0).
The main scale research image uses Rust's default x86-64 target; a subsequent
explicit x86-64-v4 build is a separately identified prospective experiment.
Four CPU slots and one pinned shared GPU
lease apply to both lanes; the machine's full core count is not the allocation.
The limits have different boundaries: COPT's TimeLimit applies inside solveLP;
our 30-second wall budget also includes internal preparation and checking after
input parsing. Complete measured costs include the surrounding work for both.
Coverage counts are conditional on these declared limits, not unlimited solver
capability or identical iteration budgets.
In particular, a 20,000-update exit before 30 seconds is an iteration-limit
result, not evidence that the model cannot certify within 30 seconds. Larger
time-budget studies need bounded streaming of intermediate evidence so their
storage allowance does not impose an artificial iteration ceiling.

The initial COPT GPU configuration uses PDLPTol=1e-9. Some of its optimal-status
endpoints fail our componentwise original-model feasibility check even when
their objective gaps are small. An additional uniform PDLPTol=1e-12 configuration
is applied across the final scale roster. The original configuration and every
time limit, absent solution and failed certificate remain visible. COPT status
alone is never treated as our certificate.

PDS reveals a limitation of that certificate implementation. COPT CPU's retained
endpoint passes original-model feasibility and has an exact rational objective
gap of only 3.510081114654895e-11 relative to the retained certified bound. The
outward floating-point objective enclosure has a gap upper bound of
9.5367431640625e-6, well below the approximately 10.928 relative upper allowance,
but its lower endpoint crosses the separate absolute -1e-9 guard. That causes
rejection. At this objective magnitude, one binary64 ULP is about 1.907e-6.
The [exact retained-endpoint diagnosis](lp-general-scale-gap-diagnosis.json)
therefore identifies enclosure width, rather than a large true objective gap, as
the CPU rejection mechanism. COPT GPU's endpoint separately fails componentwise
feasibility. Historical outcomes remain unchanged; neither optimality statuses
nor an offline diagnosis replace the frozen checks or missing timing receipts.
Future certificate work should refine an uncertain objective enclosure exactly
before rejecting, while retaining the strict original-model requirements. The
current pass count alone understates this CPU baseline's numerical quality.

Scale development uses strict 1e-9 certificates, at most 20,000 updates, checks
every 500 updates and original-A control every 100 updates. The historical broad
roster retains all 22 models and both 1e-7/1e-9 tiers. Lane order rotates and
reverses deterministically. The final matched host pilot uses a 1,000-update cap and
250-update checks to exercise checker reuse; earlier 500-update pilots have their
own frozen identities. Early certificates can stop the final pilot; matched
attribution requires equal actual work and exact transcripts. Bounded-work
measurements are not general certified-solve gains.

The primary measured envelope starts a fresh solver process and ends after a
fresh independent final original-model check. Our current research response
includes intermediate trajectories, so their serialization and transport are
included; COPT returns a final endpoint. This asymmetry is explicit and must not
be mistaken for an intrinsic solver arithmetic cost. Final campaigns separate
archive compression and historical endpoint audit time. Earlier pilot v1 and
interrupted v2 include historical audit in complete cost; compare versions only
within the same frozen campaign. No latency ratio is a success unless both lanes
certify with complete supervision; zero-FP4 work earns no FP4 credit.
The `execution` partition is host elapsed time around device advancement and
endpoint transfer, not a sum of kernel-only event times. `assessment` includes
original-A merit/control, certificate work, continuation/reset and checker
release. Cost attribution uses those measured boundaries; it does not assign
the entire assessment partition to certificate arithmetic alone.

For the four-million-nonzero cohort, historical endpoint audits use separate CPU
reservations after releasing the GPU lease. A comparison remains ineligible
until both its scientific reservation and all required audit reservations pass.
The fresh final certificate stays in the primary path. This changes resource
scheduling, not certificate criteria or the set of retained intermediate checks.

## Development results

The [compact results](lp-general-scale-results.json) retain every pilot, broad,
1 M/public and 4 M observation, including failed groups and missing cells. Full
certificates and response bindings remain in the referenced local evidence.
The [model index](lp-general-scale-models.json) maps compact cell indices to the
frozen family, original input and available size/seed metadata for every cohort.

Matched host pilots establish shared implementation gains. The corrected exact
host preparation has a 1.338x median complete-cost ratio across 32 equal-work,
exact-transcript pairs against its contemporaneous control. The later lazy
checker has a 1.053x median across 28 fully supervised equal-work pairs. These
are different development comparisons, with different controls and work caps;
their ratios must not be multiplied. Both native and FP4 receive the improvements.
The final pilot's refused last group is excluded from these timing summaries.

The complete historical broad roster retains 132/132 cells: native, FP32 and
FP4x2 each certify 20/44 model/tier cases. Across the fourteen jointly certified
cases with actual FP4 work, the median native/FP4 complete-cost ratio is 0.971
and FP32/FP4 is 0.969; FP4 is faster in four and six pairs respectively. Including
the six zero-FP4 jointly certified cases gives 0.985 and 0.984. FP4 contributes
24.131% of accepted product nonzeros across its broad lane. This establishes
coverage and useful arithmetic participation, but not broad complete-solve value.

On the 1 M structural population, our lanes certify 14/18 and COPT GPU with the
uniform tighter setting certifies 15/18. COPT CPU auto reaches its declared limit
without a certificate on all eighteen. COPT CPU and GPU both certify square31
and scpm1, while our lanes do not certify those public cases under their declared
caps. PDS's numerical and measurement qualifications are recorded above and below.
Public instances are reported individually, not folded into a favorable synthetic
family average.

The complete 4 M cohort retains 90/90 measurements and all eighteen history
audits. Native, FP32 and FP4x2 each certify 12/18; COPT GPU certifies 15/18 and
COPT CPU auto 0/18 under the declared limits. Native, FP32, FP4x2 and COPT GPU
certify all wide, tall, coupled and degenerate cases; COPT GPU additionally
certifies all three irregular cases. No lane certifies the ill-scaled family.
Across the twelve jointly certified FP4/native cases, the median complete-cost
ratio is 0.971; against FP32 it is 0.979. The three cases with actual FP4 work
have medians of 0.999 and 1.000 respectively. The other fifteen generated models
have no eligible tensor tiles. Both coverage and these near-parity costs matter:
the larger full roster does not establish an FP4 complete-solve advantage.
FP4 supplies 4.110% of accepted product nonzeros across the full 4 M lane;
uncertified, long-running sparse cases remain in that denominator.
The ill-scaled failures have substantial residual error: for example, the first
4 M native endpoint fails primal feasibility and has a gap upper bound of about
97.03 at an objective near -28,010. This is distinct from the tiny exact-gap PDS
enclosure issue; improving certificate arithmetic alone would not solve it.

For the first 1 M coupled instance, FP4 execution is 39.79 ms versus 127.01 ms
native and 106.42 ms FP32, with 75% accepted FP4 product work. Complete measured
times are 1.458, 1.399 and 1.420 seconds respectively; COPT GPU takes 1.992 seconds
and also certifies. The solver beats this COPT configuration on that case, but
the FP4 arithmetic does not produce an incremental complete-cost win over our
native/FP32 controls.

At 4 M, the first irregular instance has no eligible FP4 tiles. Our lanes reach
20,000 updates without certifying in approximately 33 seconds including transport
and the final check. GPU execution accounts for 3.3–3.8 seconds and assessment
about 18 seconds. COPT GPU certifies in 12.83 seconds, including an 8.01-second
solve. The FP4-configured fallback's timing is not evidence for FP4. On the first
4 M coupled case, actual FP4 execution falls to 109.91 ms versus native 426.43 ms,
but FP4 takes 3,000 rather than 2,500 updates and complete cost is 5.502 versus
5.270 seconds. Larger products expose real arithmetic savings and still leave
assessment, preparation, transport and convergence decisive.

The [16 M extension](lp-general-scale-frontier-results.json) completes all 30
admitted measurements and six independent history audits. Native, FP32, FP4x2
and COPT GPU each certify 6/6; COPT CPU auto certifies 0/6 under its limit. All six
generated inputs have one connected component. Twelve additional model records
and sixty unexecuted lanes retain their capacity refusals. Across the six
supported models the native/FP4 complete-cost median is 0.972. Across the three
coupled models with actual FP4 work it is 1.008, versus 0.994 for FP32/FP4. These
small, mixed differences on a capacity-selected subset do not establish broad
superiority. The subset's 53.571% accepted FP4 work share cannot be interpreted as
improved coverage of the excluded sparse families.

The paired medians below use the three coupled seeds at each size; ratios above
one favor FP4. They summarize complete measured execution at each lane's actual
iteration count, not a fixed-work kernel microbenchmark.

| Original nonzeros | Native/FP4 execution | FP32/FP4 execution | Native/FP4 complete cost | FP32/FP4 complete cost |
| --- | ---: | ---: | ---: | ---: |
| 1 M | 3.192 | 2.675 | 0.981 | 0.974 |
| 4 M | 4.675 | 3.880 | 0.999 | 1.000 |
| 16 M | 5.332 | 4.419 | 1.008 | 0.994 |

On the first 16 M coupled seed, native and FP4 both take 2,500 updates. Execution
falls from 1.657 to 0.310 seconds, but complete time is 21.395 versus 21.826
seconds. On the first tall seed, device execution is below one second while
complete time is 28–30 seconds; that case has no FP4 tiles. The measured scaling
therefore strengthens the diagnosis of surrounding costs and limited sparse
coverage, rather than proving that size alone establishes FP4 superiority.

The first 16 M coupled pair makes the cancellation concrete. Native execution
is only 7.7% of its complete cost. FP4 saves 1.346 seconds in that partition,
while its measured host preparation is 1.256 seconds longer. The source adds
canonical tensor packing on the FP4 path; these phase observations motivate
isolating and accelerating that preparation, rather than attributing the entire
difference to a hardware effect. Assessment and independent checking then remain
large shared costs.

| Measured seconds, first 16 M coupled seed | Native | FP4x2 |
| --- | ---: | ---: |
| Host preparation | 5.731 | 6.987 |
| Device execution and endpoint transfer | 1.657 | 0.310 |
| Assessment/control/reset | 6.811 | 7.064 |
| Fresh independent final check | 4.321 | 4.504 |
| Complete measured primary path | 21.395 | 21.826 |

The listed components are selected partitions, not an exhaustive sum: input,
setup, response construction/transport, parsing and teardown also remain in the
primary path. Shared-host variation remains relevant to small pair differences.

## Host build target follow-up

Inspection of the retained Cargo fingerprint found that the main scale image
uses the default x86-64 target. A source-identical x86-64-v4 build receives fresh
CPU/GPU/sanitizer admission and a [separate matched pilot](lp-general-scale-target-results.json).
All six connected 1 M families and square31/scpm1 are retained, with native,
FP32 and FP4x2, both builds and two repetitions: 96/96 cells. All 48 paired
transcripts agree exactly at equal work. Both builds get a 1,000-update cap,
250-update certificate cadence and 30-second wall limit; early certificates
can stop before the cap. This follow-up avoids the earlier scpm1 pilot's unequal
work under a 10-second deadline.

The default-target/v4 complete-cost medians are 1.0154 for native, 1.0033 for
FP32 and 1.0112 for FP4x2; the overall paired median is 1.0080. Of 48 pairs, 38
favor v4, with individual ratios spanning 0.9483–1.0765. These small descriptive
effects on a shared host do not establish a broad deployment benefit. The
experiment isolates the host build configuration, not any individual SIMD
instruction or FP4 arithmetic. The v4 image remains available as an opt-in
research build; portable Cargo targets and public defaults stay unchanged. The
1 M/4 M/16 M full-solve results above remain those of the default-target image.

## Evidence, failures and limits

Every campaign freezes inputs, binaries, lane order and its retained runner.
Responses exceeding 32 MiB are stored as bounded gzip chunks with exact raw-byte
and per-chunk hashes. The 512 MiB per-file supervisor ceiling is unchanged.
Large matrices, trajectories, source snapshots and content-addressed archives
stay local. Only compact findings and source are tracked.

The initial scale cohort retains 120/126 completed cells. Its final PDS group
stopped after the old JSON evidence reader rejected a 415,164,920-byte response;
that raw response and all six missing cell receipts remain visible. A separate
pilot stopped after its working harness changed following freeze; its 12 results
and 84 missing cells remain. Later campaigns execute frozen runner copies.
These cells are not retried. Corrected implementations have new prospective
cohorts, with all old observations and full failed reservation charges preserved.
The final 1,000-update-cap pilot retains 95/96 cell records after its last public
group exhausted its reservation. All timings in that group are ineligible.
Deadline-induced unequal-work pairs are reported separately from exact matched
trajectories; they cannot establish an isolated implementation speedup.

The final main cohort retains 100/105 cell records. Its PDS native solve and
fresh final check completed, but the repeated historical proof stream reached
the 512 MiB file ceiling before the cell receipt was written. A later CPU-only
audit verifies all 41 retained endpoints; it does not reconstruct the missing
timing or turn the failed reservation into a pass. A continuation of never-started
lanes then retained the PDS FP32 response and final check but failed because a
deferred-audit row referenced a deliberately absent inline audit file. That
measurement also remains missing. A second tail completes the three remaining
unstarted lanes and their separate audit. Across these distinct attempt
identities, 103 of the original 105 planned measurements have complete receipts;
the other two retain raw numerical endpoints. Neither attempted cell is rerun.

The corrected audit writer chunks exact JSONL bytes and drops repeated proof
objects only from transient parsed Python results. The complete proof stream is
still retained. Its admission includes the large PDS trajectory and an eight-lane
complete deferred-workflow smoke test. The PDS audit's execution is bound by its
reservation source snapshot; its disposition also records a closing working-file
hash after unrelated tail edits. Those are different provenance observations,
and the later hash is not presented as the executed source.

Other retained failures include missing configuration fields during development,
a COPT GPU admission time limit without a solution, an attempted PDS expansion
above the inherited file limit, a missing imported-test symbol, and the original
automatic-schedule comparison against the wrong explicit reduction schedule.
All source versions, logs, refusals and full charges remain in the ledger.

The first 16 M preparation also fails because the base Python lacks SciPy, after
writing one complete tall input and witness but before any solver launch. Its
full 2,400 CPU-second charge and exact partial output remain. A new preparation
identity uses the pinned SciPy environment, reuses that exact input and witness,
and generates the remaining five admitted models. All six pass the connectivity
check; no solver cell is repeated. Input manifest version 3 records this lineage.

Four CPU slots, 16 GiB sampled RSS, 12 GiB owned device buffers, the pinned shared
lease, one-second supervision and all 100 ms advisories remain. Sampled RSS and
COPT's reported memory are not hard peak-memory enclosures. Shared-host/device
variation limits small descriptive ratios. No confirmation or general FP4
superiority is inferred from fixed-work gains or native fallback.
The owned-buffer counter covers our executor. COPT uses its 12,000 MB `MemLimit`
setting and reports `MemPeak`; its opaque device allocations are not independently
enumerated by our counter. The comparison does not claim such an enclosure.

## Validation and next general improvements

Native acceptance passes 638 repository Rust tests and 827 Python tests (the
initial full gate passed 826 Python tests; the final complete Python run includes
the added exact JSONL stream contract). The isolated package passes 37 Rust tests.
Final CPU admission includes 24 input-equivalence comparisons, 32 host probes and
60 cached-certificate comparisons. The main image and source-identical host-target
image each preserve 60 complete GPU continuations against the matching explicit
old schedule; memcheck, racecheck, initcheck and synccheck each pass 20 cases on
each image. Sixteen malformed native-input
cases refuse before solving. Imported checker sources, unchanged public numerical
sources and the unchanged device image are bound separately.

The next engineering priorities remain general single solves:

1. Move repeated original-A control work onto an efficient original-precision GPU
   path and reduce exact-check preparation and traversal costs. Add a bounded
   exact refinement when enclosure width alone makes the gap decision uncertain,
   as demonstrated by PDS. Preserve strict fresh final certificates and
   independently admit each changed reduction tree and decision implementation.
2. Stream intermediate evidence with bounded resident memory and deduplicate
   immutable proof geometry. This removes the current trajectory transport cost
   and permits a time-budget comparison without an artificial storage-driven
   update cap. Retain every endpoint and full failure history.
3. Improve convergence on irregular and ill-scaled LPs, with the same improvements
   available to native, FP32 and FP4 controls. Report accuracy and work to solution
   alongside iteration cost; a cheaper update that requires more updates can lose.
4. Extend low-bit execution to broadly sparse matrices where the current tensor
   packing finds no eligible tiles, and reduce reference/packing/launch overhead
   on matrices that do use FP4. Keep zero-FP4 cases, all structural families and
   public anchors in coverage. Increasing size alone cannot fix absent FP4 work.

These are remaining requirements for the broad performance objective, not a
recommendation to narrow the project to a favorable dense or prepared workflow.
Fresh processes do not imply flushed caches. Installed COPT's results are a
concrete external reference under the stated limits, not a precision attribution
or a claim about every COPT algorithm and configuration.

Reproduction uses `tools/lp_general_scale_cpu.sh`, the scale admission tools,
`lp_general_scale_bench.py freeze/campaign`, `lp_general_scale_report.py` and
`lp_general_scale_portable.py archive/replay`, each under a fresh applicable
`lp_general_budget.py` reservation. Never reuse a reservation or scientific cell
identity. Preserve exact original sources, failures and missingness.

## Delivery validation

The [compact validation receipt](lp-general-scale-validation.json) binds final
source, native/device admission, resource settlements and portable replay. The
local delta archive verifies 92,050 files and preserves 221,275 earlier
scientific file bindings exactly. Its 10,749,532,394 compressed bytes stay
local in 139 bounded parts. Exact chunk validation covers
104 streams / 13,695,765,344 raw bytes. Only compact findings and source enter Git.

Extracted-root original-model replay passes 897 retained campaign responses,
707 research admission responses and 11 COPT admission responses,
with 10,457 assessments / 4,407 distinct serial witnesses.
It preserves 4 raw-only responses and the explicit missing-cell ledger;
checking those bytes does not repair missing measurements or supervision.

All eleven failed scale reservations retain their full 12,000 CPU / 1,830 GPU
seconds and original sources. All settled scale cleanup is empty, no scale
reservation overruns, and no reservation remains active. The independent
240,000 CPU / 30,000 GPU-second allocation stays open at
181311.318401148 CPU / 23462.140788896 GPU seconds. Final documentation and
resource receipts are additive to the retained scientific archive snapshot.
This delivery is committed locally only; no confirmation, public adoption or
publication is released.
