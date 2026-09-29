# COPT Bulk Adapter: GPUP-COPT-ADAPTER

The isolated bulk adapter preserves the model and independently certified outcomes,
but is slower in every certified comparison cell. The dense-65536 GPU PDLP median
increases from 8.983 to 11.070 seconds. Native bulk loading is cheaper; fresh CSC
preparation and sparse dependency import outweigh that saving. No preset or default
is selected. This is one measured adapter implementation, not a claim that every
possible use of COPT's bulk API must be slower. The faster existing scalar wrapper
remains the ordinary COPT path; the bulk worker is opt-in and runtime solver
defaults are unchanged.

[SPEC-0019](../specifications/SPEC-0019-copt-bulk-adapter.md) and
[ADR-0031](../decisions/ADR-0031-copt-bulk-adapter.md) were accepted before behavior.
The [strict protocol](../../benchmarks/configs/lp-copt-adapter-v1.json) fixes
`gpup-copt-adapter-v1`, four development models, three methods, two adapters,
three timing repetitions and twelve separate profiles. All **84/84 attempts verify**
with both archived baseline and current Rust certifiers. **42/72 timings** and
**10/12 profiles** certify. Verification of an interrupted or rejected outcome does
not make it a successful timing.

## Interface and controls

`copt-scalar-v1` invokes the historical scalar worker unchanged. `copt-bulk-v1`
uses a separate worker with binary64 CSC arrays, COPT `loadMatrix`, explicit sense
and offset setters and original ID names. Duplicate terms are rejected before any
sparse conversion; nonzero coefficients at or below MatrixTol and invalid finite
bounds retain their guards. Continuous domains, ranged bounds and canonical order
remain. Witness and endpoint v2, original-model certification and native parameters
are unchanged. No project runtime or kernel is modified.

Both fresh controls use a new isolated Python 3.11 environment with NumPy 2.3.4,
SciPy 1.16.3 and the original COPT 8.0.6 library/binding hashes. The historical
environment and measurements remain untouched. The scalar path does not import
SciPy; the new dependency's cold import is included in the bulk endpoint. Trial
identity binds the adapter, source, complete dependency manifest, command, model,
request, witness, endpoint, logs, costs and worker receipts. Missing dependencies
never trigger another adapter. COPT license files are not copied or archived.

All processes use seed 17 in the recorded solve contract, one solver thread and
1e-9 tolerances. COPT lacks a matching hard PDLP iteration/seed control; aggregate
native counts above 50000 remain work-limited and are not project physical updates.
Fresh-process launch through certified output is the primary endpoint, including
imports and teardown. The small-model deadline is 10 seconds and extension deadline
30 seconds, plus two seconds for cleanup; the input/output/host limits remain
128 MiB / 32 MiB per file / 8 GiB. GPU claims require the shared lease and an
execution log, not discovery alone. Native logs identify the target as an NVIDIA
GeForce RTX 5090 with CUDA capability 12.0 and report CUDA 13.0; the protocol binds
its UUID. Detailed per-trial driver/thermal telemetry was not sampled and remains
explicitly unavailable. Lease admission retains observed competing activity. No
retrospective thermal or driver measurement is substituted for those missing fields.

## Latency and coverage

Medians below are seconds, using certified fresh processes only. Ratios are the
median of paired scalar/bulk ratios; values below one favor scalar. Intervals use
10000 paired bootstrap resamples, seed 17002, 95% confidence. Three development
repetitions do not establish a supported general recipe. Ordering uses seed 17001.

| Model | Method | Certified scalar, bulk | Scalar median s | Bulk median s | Scalar/bulk [95% interval] |
| --- | --- | --- | ---: | ---: | --- |
| small-4 | CPU-default | 3/3, 3/3 | 0.2674 | 0.3384 | 0.7806 [0.7765, 0.8000] |
| small-4 | CPU-PDLP | 3/3, 3/3 | 0.2628 | 0.3352 | 0.7746 [0.7668, 0.7873] |
| small-4 | GPU-PDLP | 3/3, 3/3 | 0.7291 | 0.8653 | 0.8507 [0.7851, 0.8665] |
| irregular-32768 | CPU-default | 0/3, 0/3 | unavailable | unavailable | unavailable |
| irregular-32768 | CPU-PDLP | 3/3, 3/3 | 3.5723 | 4.1986 | 0.8503 [0.8499, 0.8545] |
| irregular-32768 | GPU-PDLP | 3/3, 3/3 | 3.8240 | 4.4225 | 0.8589 [0.8562, 0.8688] |
| dense_block-65536 | CPU-default | 0/3, 0/3 | unavailable | unavailable | unavailable |
| dense_block-65536 | CPU-PDLP | 3/3, 3/3 | 9.2697 | 11.3988 | 0.8142 [0.8121, 0.8270] |
| dense_block-65536 | GPU-PDLP | 3/3, 3/3 | 8.9825 | 11.0700 | 0.8097 [0.8060, 0.8217] |
| mixed-65536 | CPU-default | 0/3, 0/3 | unavailable | unavailable | unavailable |
| mixed-65536 | CPU-PDLP | 0/3, 0/3 | unavailable | unavailable | unavailable |
| mixed-65536 | GPU-PDLP | 0/3, 0/3 | unavailable | unavailable | unavailable |

All 18 primary CPU-default extension attempts reach the process deadline and retain
verifiable interrupted endpoints. All 12 primary mixed-65536 PDLP attempts complete
but fail original-model certification. Profiles add two interrupted dense CPU-default
attempts. No attempt is missing, retried, erased or used to fill a historical cell.
There is no certified paired speed ratio for any of these incomplete cells.

## Component diagnosis and agreement

The dense-65536 rows below are separate single profiles, in seconds. Native loading
includes objective/name restoration. These disjoint construction scopes are compared
with the solve and certification envelopes; nested certifier CPU costs are not added
again. A zero in the sparse columns means that operation is absent from the scalar
path, not that an unavailable measurement was imputed.

| Method | Adapter | SciPy import s | CSC preparation s | Native construction s | solveLP s | Host certification s |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| CPU-PDLP | copt-scalar-v1 | 0.0000 | 0.0000 | 1.6848 | 1.6819 | 1.9438 |
| CPU-PDLP | copt-bulk-v1 | 0.0649 | 2.4981 | 0.9944 | 1.6839 | 1.9435 |
| GPU-PDLP | copt-scalar-v1 | 0.0000 | 0.0000 | 1.6846 | 1.2606 | 1.9387 |
| GPU-PDLP | copt-bulk-v1 | 0.0655 | 2.6968 | 0.9999 | 1.2374 | 1.9411 |

For GPU PDLP, native construction falls from 1.685 to 1.000 seconds, but CSC
preparation adds 2.697 seconds and sparse import adds 0.066 seconds. Native solve
and fresh host certification are similar. The small CPU PDLP profile adds about
64 ms of sparse import to an operation whose native solve takes about 0.5 ms.
The pure builder performs structural validation, a further coefficient-guard scan,
column-bucket construction and array preparation; its work is charged in the table.
The common earlier import guard is retained too. The study does not separate every
suboperation within CSC preparation or claim these costs are unavoidable. No
post-result optimization or additional candidate is substituted for this version.

All **27/36** matching timing pairs include every certified pair and all mixed PDLP
rejections. The remaining nine pairs are exactly the interrupted CPU-default cells.
Their native work differs: for dense-65536, scalar reports about 44302–44308 native
iterations and 24.80–24.88 solve seconds; bulk reports 43444–43475 iterations and
22.78–22.85 solve seconds. This is consistent with added construction consuming
more of the same process deadline; the internal COPT iteration phases remain opaque.
No equal-work or numerical-equivalence claim is made for these nine pairs.

**10/12** profile-to-first-timing comparisons match numerical state and work;
the two exceptions are the interrupted dense CPU-default profiles. Profile wall
ratios to the corresponding certified timing median range from 0.9303 to 1.0228.
These single diagnostic samples are not pooled with timing repetitions and do not
establish a general profiling-overhead distribution. Binary64 comparisons exclude
clocks and native memory reports, while retaining objectives, bounds, assessments,
primal/dual vectors, status and all native iteration counters.

## Acceptance, resources and reproduction

Full pinned-native acceptance passes 514 Rust tests, 205 Python integration tests,
committed-record replay, 113 documentation pages and smoke; both pre-study and
final full gates pass. Nine new dependency-free
contracts also pass in a source-only checkout without COPT or campaign artifacts.
Real CPU readback matches all twelve scalar/bulk min/max representations, including
empty dimensions. All 24 min/max method/adapter/profile endpoints certify with both
verifiers; numerical state and work match in all six four-endpoint groups. Existing
supervisor tests exercise deadlines and cleanup; new fault tests cover native
interrupt delivery, missing dependencies, command/artifact substitution and recovered
reservations. The initial schema-enum and readback API failures are retained with
passing corrections. No failed GPU acceptance or retried study identity occurred.
Unchanged project CUDA code retains its earlier sanitizer receipts; the historical
racecheck, large-session and mixed-model limitations are not closed by this task.

Task charge is **171.904859644 GPU seconds**: timing 142.395630328/900,
profiles 22.026636414/200 and acceptance 7.482592902/400; combined cap 1500.
Cumulative consumption is **15804.186067059 / 18002.574545061 seconds**, with no new
allowance or borrowing. The **15776-event** ledger SHA-256 is
`2b99b615dc77da07fb078e1cefc188d2131db5ca671fe9b86f989a6d660606f0`. Its 15606-event prefix remains
`ad3d84354f0b74ae62fcc019ee4dcbf29b0a3251d066f1e0f2df11ccb107230b`; all earlier prefixes,
phase caps and the original output binding remain intact. Four build jobs and a
four-CPU-hour cap apply. [Resource receipts](data/copt-adapter/adapter-resources.json)
record metered child CPU separately from ledger CPU reservations; small source-edit
and catalog operations are outside that meter.

The frozen source, executables and raw results remain under
`artifacts/gpup-copt-adapter-baseline`, `artifacts/gpup-copt-adapter-v1` and
`artifacts/gpup-copt-adapter-acceptance`; optional dependency files are under
`artifacts/gpup-copt-adapter-env`. The original source revision is
`8fdec89451c07ffea46a3d8630aa184b14e072c5`. Reproduction requires the existing pinned
COPT installation and original optional environment, the pinned native HiGHS build,
and authorized remaining ledger headroom. From the repository root:

```bash
python3 -B tools/setup_copt_adapter.py
bash tools/check.sh
cargo build --release --workspace --all-features --locked
python3 -B tools/benchmark_lp_copt_adapter.py --dry-run
python3 -B tools/benchmark_lp_copt_adapter.py --prepare
# Acceptance and study invocation are frozen in retained request/CPU receipts.
# Admitted study identities cannot be rerun; the runner skips them.
python3 -B tools/report_lp_copt_adapter.py
python3 -B tools/export_lp_copt_adapter.py
```

Use the archived source/schema snapshot to reverify the measured execution. The
reporter rechecks all endpoint assessments with both binaries; it verifies request,
filename, dependency, source and ledger identity and never repairs the ledger.
[Summary](data/copt-adapter/adapter-summary.json),
[all trials](data/copt-adapter/adapter-trials.csv),
[profiles](data/copt-adapter/adapter-profiles.json),
[source/ledger audit](data/copt-adapter/adapter-source-ledger-audit.json) and
[artifact catalog](data/copt-adapter/adapter-provenance.json) retain the evidence.
The next bounded task is GPUP-CONVERGENCE; it is not started here.

## Integration review

Self-review reproduced and corrected interrupted-coordinator recovery: retained
partial files now receive exact artifact bindings, surviving worker observations
are restored, and a recovered reservation keeps its full charge. Recovered trials
remain process failures even when a completed worker receipt survives; they cannot
enter successful latency samples. A crash after settlement retains its actual
charge. CPU regression tests cover both accounting paths and reject substitution
or promotion of interrupted trials.

The [review correction manifest](data/copt-adapter/adapter-review-corrections.json)
binds the measured and reviewed bytes of the three changed coordinator/report/export
files. Both solver workers, the CSC builder, frozen protocol, schemas, native
binaries, all measured results and the GPU ledger remain byte-identical. The
source audit declares these CPU corrections separately from the measured version.
