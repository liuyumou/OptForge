# General sparse low-bit LP research executor

The [preparation/control continuation](../../docs/benchmarks/lp-general-prep-control.md)
adds exact gathered host products, scoped worker/buffer reuse and parallel
canonical FP4 packing in scale-image-v12. Scale-image-v14 adds checked indexed
preparation in an isolated host derivative; all public source files stay exact.
Default control remains every 100 updates. The separately evaluated 500-update
setting in v12 changes trajectories and regresses the certified-solve median.
The final indexed comparison reduces preparation by about 6.8% at lower scale
and 5.2% on the limited 16 M extension; certified complete-time medians improve
about 2.4% and 1.6%. All 150 measurements are retained. Broad FP4 complete-time
superiority remains unestablished.
Public solver defaults and the fast-image-v10 CUDA image remain unchanged.

The [host-cost continuation](../../docs/benchmarks/lp-general-host-cost.md)
optimizes the existing opt-in `host_certificates` path. Original host products,
control decisions and spectral preparation are preserved. Historical
scale-image-v6 remains the matched control; public solver defaults are unchanged.

See [SPEC-0045](../../docs/specifications/SPEC-0045-general-lowbit-lp.md).
This isolated candidate targets fresh single solves of general LPs. It does not
change public solver defaults and has no broad performance claim yet.

The original sparse CUDA kernel uses packed FP4 coefficients with FP32 SIMT
increments and FP64 references/state. It is not a Tensor Core kernel. Native
FP64 and FP32 controls share geometry, controller and original-model checking.
Both matrix orientations refer to a canonical represented operator. Every
rejected attempt remains in physical work and complete cost.

Ordinary Cargo builds need no CUDA toolkit. The GPU image is explicitly compiled
and admitted under the independent budget and unchanged shared-device lease.
All numerical jobs use `tools/lp_general_budget.py`; CPU and device admission
tools retain source-bound responses and original serial certificates. Diagnostic
`gpu-fixed` bypasses the local value limit only for bounded arithmetic admission;
it cannot return a solver certificate or be used for performance claims.

JSONL commands are `cpu`, `operator`, `assess`, `gpu`, `gpu-probe`, and `gpu-fixed`.
GPU commands also require an explicitly supplied cubin. Every request includes
validated settings. `gpu` creates and destroys its owned context for each solve.
The product admission command alone caches a context across diagnostic requests.

`tighten` emits an equivalent model and original-row implication proof;
`assess-proven` checks an external endpoint using the same proved bounds and
limited dual-repair proposals as the solver. Original `assess` remains available
for diagnosing the unextended checker. Every actual certificate dual is retained
separately from the numerical continuation state. Independent exact-rational
proof verification precedes unchanged serial checking of equivalent bounds and
original primal feasibility. These shared improvements do not establish FP4 value.

Generated models, raw responses, binary images and portable evidence bundles stay
under the ignored local `artifacts/gpup-general-v1` directory. Commit source,
protocol, compact results and reproduction instructions; do not commit build
targets or large generated matrices. Retain all scientific inputs and failures.

The initial 128-cell pilot is complete. The extended 176-cell pilot stopped with
137 retained responses after a missing supervisor receipt; 136 have complete
resource receipts and 39 planned cells are missing. Numerical admission does not
establish performance: FP4 supplies only about 0.48% of accepted updates in the
retained extended results. See the [development report](../../docs/benchmarks/lp-general-lowbit.md)
and its compact result record for all outcomes and continuing engineering work.
The interruption disposition permits CPU work; new GPU/scientific execution
requires operational readmission. Neither existing cell identities nor failed
resource reservations may be reused.

`tools/lp_general_portable.py archive --id NAME` creates a local evidence bundle;
`replay --id NAME` checks its exact bytes and independently reassesses every
retained endpoint from an extracted root. Use a fresh budget job identity and
the reporting phase for each command. Replay retains the missing-cell ledger
and does not turn missing supervision into a successful experiment. The archive
receipt gives its hash, compressed size and retained file count.


## Actual FP4 Tensor Core backend

`gpu-tensor MODEL CUBIN` is a separate opt-in backend. `tensor-operator MODEL`
emits its canonical sparse-block packing and `gpu-tensor-probe MODEL CUBIN`
admits products only. The SM120 image uses actual E2M1 MMA with FP32 accumulation
and FP64 state. `fp4x1` through `fp4x4` select one through four components;
`fp4x4` means sixteen logical coefficient bits per orientation, plus metadata
and original FP64 data, not four-bit total storage.

A request has `settings` and optional `tensor` objects. Tensor controls are
`min_tile_nnz` (default 128 of 1024), `control_interval` (100), `incremental`
(true), `compact_fragments` (true), and `tensor_warps` (1, alternatively 4).
The component count follows `settings.format`. The same settings support native
and real FP32-storage controls. Local original-row replacements preserve global
FP4 eligibility; actual tensor nonzeros and corrected nonzeros are counted
separately. Zero-tile models explicitly select native and contribute no FP4 work.
Global progress/nonfinite failures still restore a complete checkpoint.

Control feedback is separate from strict original-model certificate assessment.
Periodic original-A references allow the Tensor Core path to quantize increments.
Direct products, expanded fragments and four-warp launches remain diagnostic
ablations. Every fresh solve pays its own preparation, context and teardown.
Public defaults are unchanged; development observations do not imply adoption.

`tools/lp_general_tensor_cpu.sh` builds and checks a candidate; the tensor
admission tool covers independent rational products, original serial certificates,
restoration and all four sanitizers. A hash-bound composite admission precedes
`tools/lp_general_tensor_bench.py freeze` / `campaign`. These commands must run
within the existing budget/supervisor protocol; old identities cannot be reused.
`tools/lp_general_tensor_portable.py` archives and independently replays a local
**delta** bundle, keeping the original large evidence bundle separate. Only
compact results and validation receipts belong in Git.

## Specialized search-proposal backend

`gpu-fast MODEL CUBIN` uses the separately compiled `cuda/fast.cu` image.
`gpu-fast-probe` emits independently checked proposal products with
`enclosed: false`; these values have no certificate authority. FP64 state,
original-operator control/reference work, rollback and strict original-model
certification remain in the solve. The sparse remainder uses FP32; cases with
no eligible tiles explicitly select FP32 and contribute no FP4 work.

The optional `fast` object has `combined` (true), `fused_encode` (true),
`adaptive_rows` (true), and `lanes` (0). Combined FP4 assigns a CTA to 32 outputs,
integrating product, projection and encoding. Short remainder rows use eight
lanes; groups containing a row with more than 64 entries use full warps.
Disabling `adaptive_rows` forces full-warp reduction. Setting
`combined: false` selects the split half-tile implementation. `lanes` selects
1/4/8/32 lanes for native, FP32 and split FP4, with zero choosing from average
work per output; combined FP4 uses its own short/long-row policy. Disabling
encoding fusion provides a matched arithmetic ablation. The original
`gpu-tensor` local-bound backend remains available.

FP32 and FP4 remainder products reuse a cached FP32 vector difference, formed
once per vector element at each reset or projection. This preserves their
product arithmetic while removing repeated FP64 subtraction and conversion
from the per-nonzero loop. The native control keeps its FP64 products.

Use `tools/lp_general_fast_cpu.sh`, the fast arithmetic/boundary admission tools,
four sanitizers and `lp_general_fast_admit.py` before a frozen fast benchmark.
Every numerical command still requires a fresh budget reservation and applicable
GPU lease. `lp_general_fast_profile.py` brackets each timeline with uninstrumented
transcript checks. `lp_general_fast_portable.py` stores identical source snapshots
as one content-addressed object and independently replays the extracted evidence.
For this backend, reserve archive construction in reporting and the independent
CPU numerical replay in admission, within the unchanged phase ceilings.
Large evidence remains local. See the [redesign report](../../docs/benchmarks/lp-general-fast.md).

The [FP4 surrounding-work continuation](../../docs/benchmarks/lp-general-overhead.md)
coalesces projection and encoding while preserving complete numerical transcripts.
Its matched old/new comparison retains native/FP32 controls and the full LP roster.

## Compact scale inputs and exact host work

`MODEL` may also be an `LPCSRA01` compact original-model file. It stores canonical
CSR, original IDs, sparse objective, bounds and binary64 coefficients without
quantization. The 64-byte little-endian header and array order are documented in
`src/input.rs` and `tools/lp_general_scale_io.py`. Both readers validate dimensions,
exact length, positions, ordering and bounds. The numerical dimension/nonzero
limits remain unchanged; compact transport does not increase device capacity.

Additional opt-in `fast` settings are `host_reductions` and
`host_preparation`, both false by default. The former removes unused zero-padding
work from the original host reduction tree and uses up to four workers. It
preserves tree order, including signed-zero behavior. The latter applies those
same products to the original spectral estimate. An isolated adapter reuses
public geometry preparation and retains the exact computed step, including
steps above one. Original core sources stay unchanged. Neither option changes certificate arithmetic or permits
an approximate progress test to issue a certificate.

`host_certificates` lazily prepares the already admitted exact checker after the
first failed assessment when more work remains. It caches immutable coefficient
geometry, never endpoint answers. A solve that certifies at its first check pays
no cache setup. `auto_schedule` selects split products when either orientation
has more than four tiles per output group on average. This is a structural rule,
without model-name dispatch. It preserves the arithmetic of the chosen explicit
schedule; split and combined reduction orders can differ. Both options default
to false. The strict original-model certificate and check cadence are unchanged.

`assess`, `assess-proven` and the admission-only `assess-fast` reuse immutable
model geometry across a batch of independent endpoint requests. A fresh final
checker process still pays its own preparation. `assess-fast` checks reuse of the
cached arithmetic against the original serial authority.

`tools/lp_general_scale_models.py` generates coupled structural models at bounded
nonzero targets. Construction witnesses remain separate from solver input.
`lp_general_scale_public.py` compares COPT and HiGHS MPS imports before emitting a
continuous model; no MIP presolve is applied. `lp_general_scale_copt.py` loads the
same compact model through COPT's bulk matrix API, retaining CPU auto and actual
GPU PDLP as separate external baselines. Its pinned local environment must match
the libraries in `/root/copt80`. A COPT status is not our certificate authority.
`lp_general_scale_bench.py` freezes source-bound development cells, runs fresh
processes and checks every retained endpoint in a separate CPU process using the
unchanged original serial certificate routines. Baseline-specific stopping
criteria, time limits, conversion and independent-checking costs remain visible.
The additional `copt-gpu-tight` lane uses PDLPTol=1e-12 uniformly, retaining the
same strict 1e-9 external certificate and 30-second solver limit.

Frozen campaigns execute their retained runner copy. Large responses are stored
as bounded gzip chunks with exact raw-byte and per-chunk hashes; the supervisor's
512 MiB file ceiling stays unchanged. `lp_general_scale_portable.py` archives a
content-addressed local delta and replays original-model certificates from an
extracted root. Numerical replay and packaging use fresh reporting reservations.
The current research response includes intermediate trajectories; its complete
process time therefore includes their serialization and transport. Archive
compression and historical endpoint replay are separately timed. These costs
must remain explicit when comparing against COPT's final-only response.
The four-million-nonzero campaign releases its GPU lease before independent
history audits in separate CPU reservations. Its final independent certificate
remains in the timed path. All history audits must pass before timings qualify;
the deferred work and its charges are retained in additive audit receipts.

Run structural inventory and frontier preparation with the pinned
`artifacts/gpup-copt-adapter-env/venv/bin/python`, which supplies SciPy. The base
research Python has NumPy but does not supply SciPy. `freeze --model-version N`
selects the explicit original-input manifest version; it does not modify models.
The 16 M frontier retains unsupported families and may reuse exact complete
inputs from a failed preparation, with its failed receipt and generator source
bound separately. No solver cell is retried by that preparation continuation.

The main scaling image uses the default Rust x86-64 target. The source-identical
`scale-image-v7` experiment is built with `RUSTFLAGS=-C target-cpu=x86-64-v4` on
the admitted host; its compiler fingerprints and exact-response/sanitizer
admission are retained. `lp_general_scale_target.py` freezes a separate matched
host-build pilot. Both builds use identical requests and the same CUDA image;
any measured difference is a host-build effect, not an FP4-specific improvement.
This does not change Cargo's portable default target or public solver defaults.
