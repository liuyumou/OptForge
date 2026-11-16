# Actual FP4 Tensor Core LP development

Status: opt-in implementation admitted; broad low-bit performance remains an
engineering objective. No confirmation or public adoption is claimed.
Contract: [SPEC-0045](../specifications/SPEC-0045-general-lowbit-lp.md).
Earlier evidence: [general development](lp-general-lowbit.md).

## Implementation and precision policy

The new `gpu-tensor` backend executes actual normal-E2M1 Tensor Core instructions
on the NVIDIA RTX PRO 6000 Blackwell Server Edition, pinned UUID
`GPU-6721b13a-30f9-83ec-dace-ba2d9738556f`. The retained SM120a cubin disassembles to
`QMMA.16832.F32.E2M1.E2M1`. This is distinct from the previous FP4-storage/FP32-SIMT
prototype. Ordinary single solves remain the primary performance endpoint.

Canonical 32-by-32 sparse blocks are eligible at 128 nonzeros; unselected entries
remain sparse. There is no whole-matrix densification or family-specific routing.
The transpose represents exactly the same quantized coefficients. One through
four FP4 components feed FP32 accumulation and FP64 solver state. The principal
candidate uses four components: sixteen logical coefficient bits per orientation,
plus scale/index/error metadata and retained original FP64 data. It is actual FP4
arithmetic, but is not a four-bit-total-storage claim.

The old global maximum guard and permanent promotion after a local refusal are
replaced by tile-local coefficient and vector error bounds. Each output that
fails its local budget is recomputed from its complete original FP64 row before
projection. Other rows retain FP4 eligibility. Actual tensor nonzeros, original
row replacements, reference products and globally rejected attempts are reported
separately; an accepted FP4-labelled update can still contain corrected rows.
Nonfinite state and global progress failures restore the complete checkpoint.
Final original-model certificates remain mandatory and unchanged.

Original-A anchors refresh at the 100-update control boundary; Tensor Cores
multiply increments from those FP64 anchors. Reference, subtraction, representation,
accumulation and final-addition errors are included. Control feedback and strict
certificate assessment have independent cadences. Direct products remain an
ablation. The native and actual FP32-storage controls share the controller,
preconditioner, check schedule and original certificate authority.

Implemented performance changes include compact nibble fragments expanded only
into registers, linear sparse block discovery, cached kernel handles, one-warp
Tensor Core blocks, cached control merit for identical state/weight, and reuse of
an already accepted final assessment. Expanded fragments and four-warp blocks
remain matched ablations. Operators with no eligible tiles select native
explicitly, omit unused packing, and contribute zero FP4 work.

## Evaluation contract

The admitted candidate is `tensor-image-v6`, binary SHA-256
`4bfc6356c9d16afe584cbc1573b46428e3a7fc042bb8930ba64d7767eac9105b`, cubin SHA-256
`417a2a53b2127a553f13efcd89b1de3bfe762cbc37bd0699965b3cfd43eac9b1`.
`tensor-admission-v4.json` binds its retained sources, CPU/device checks, original
serial certificates, four sanitizers and prospective operational readmission.

The 22-model development roster includes six generated families at multiple
sizes, afiro, adlittle, israel and 25fv47, dimensions up to 65537, and a dense
1025-column case. All were previously development inputs; no holdout was viewed.
The 154-cell ablation crosses seven implementations at strict 1e-9 with a
500-physical-update/10-second limit. The 132-cell full-solve comparison crosses
native, FP32 and four-component FP4 at 1e-7 and 1e-9, with 20000 physical updates
and a 30-second internal solver deadline. Final checking, serialization and
process exit can extend complete elapsed time beyond that deadline. Checks occur every 500 accepted updates and at the
end. Order alternates by model/tier. Every cell has a fresh process and context.

Complete time covers process startup, input handling, preparation, packing,
device setup, iterations, internal original-model checking, teardown and response
serialization. Independent external serial replay and evidence writing are
validation costs outside that endpoint, retained in resource charges. Execution
cost includes encoding, product, projection and launch costs; it is not a pure
MMA timing. Residual control, counter reads and other unassigned work remain in
complete cost. Fresh processes do not imply flushed caches.

One observation per model/format/tier is descriptive. Only jointly certified,
fully supervised cells enter solve-time ratios; all planned cells remain in the
coverage denominator. Faster unsuccessful attempts are not faster solves.
No simultaneous confidence or adoption criterion is applied retrospectively.

## Results and diagnosis

Both final campaigns complete: 154/154 ablation cells and 132/132 full-solve
cells have complete supervision. The separately failed first campaign retains
2/68 responses and no qualified timings. Its 66 missing cells remain explicit.
[Compact results](lp-general-tensor-results.json) retain every planned cell,
status, complete cost, work count and certified pair.

| Full-solve lane | Certified model/tier cases | Faster than native among jointly certified pairs | Median native/lane time |
| --- | ---: | ---: | ---: |
| Native | 20/44 | — | 1.000x |
| FP32 | 20/44 | 6/20 | 0.933x |
| FP4, four components | 20/44 | 3/20 | 0.892x |
| FP4 subset with actual accepted Tensor Core work | 14 certified cases | 0/14 | 0.816x |

The FP4 configuration is faster than FP32 in 7/20 jointly certified pairs, with
a median FP32/FP4 ratio of 0.923x. These are descriptive observations, not tests
of superiority. All three configurations leave 24/44 cases uncertified under
the iteration/deadline limits. The broad convergence problem persists.

The new guard policy does sustain actual low-bit work: four-component FP4 retains
99.999832% of attempted tensor nonzeros in accepted control intervals, contributing
25.3910% of all accepted product nonzeros across the full roster,
including uncertified development solves. Only 82490
accepted row-replacement nonzeros remain. Native sparse remainder, zero-tile
models, original reference products and global rollback costs are additional;
none count as useful FP4 work. The contribution is substantial but not a speedup.

The fixed-work ablation helps distinguish policy effects. Anchored two-component
FP4 retains 31.1831% of attempted tensor nonzeros; direct four-component FP4 retains
52.2184%; anchored four-component FP4 retains 100% over these 500-update cells.
Their all-product FP4 shares are 12.4155%, 20.7906% and 39.8147%, respectively.
No cell certifies within this short diagnostic limit. Compact versus expanded
fragments and one versus four warps preserve all 44 matched numerical transcripts
exactly. Fragment storage is halved, but one noisy observation per shape does
not establish a latency advantage for either layout or launch choice.

The dense 1025-column case makes the remaining execution cost concrete:

| Strict 1e-9, 2000 updates | Native | FP32 | FP4, four components |
| --- | ---: | ---: | ---: |
| Complete solve | 916.2 ms | 997.5 ms | 1429.2 ms |
| Host preparation | 137.7 ms | 137.8 ms | 301.7 ms |
| Iteration execution | 93.2 ms | 165.4 ms | 449.9 ms |
| Internal assessment/control | 221.5 ms | 231.6 ms | 227.7 ms |

All three certify with the same accepted iteration count. Almost all products
in this FP4 solve use Tensor Cores; fallback does not explain its regression.
FP4 adds vector encoding, component reconstruction, local error calculations and
six kernel launches per update versus two for native. Four matrix components
and four vector components require sixteen component-pair sums; half of the
MMA's eight output columns are unused. This single-vector mapping cannot inherit
the hardware's advertised matrix-matrix throughput automatically. These known
costs and the measured execution regression motivate optimization; the current
phase timings do not separately identify each kernel's causal contribution.

Setup variation also matters. At adlittle/1e-7 the native complete observation
is 13449.1 ms versus 1195.9 ms for the FP4-labelled configuration. Device setup
accounts for 12532.1 versus 244.8 ms; iteration execution is 339.8 versus 340.4 ms.
The FP4-labelled run selects native and performs zero tensor work. Retain this
apparent 11.25x configuration ratio, but do not attribute it to FP4. The ablation's
large degenerate direct-mode outlier similarly performs no tensor work; its cost
is concentrated in preparation/setup. No scheduler, cache or device cause is
established. All observations remain in the compact record.

The next optimization must address both general convergence and low-bit cost.
Priorities are reducing encoding/guard/launch overhead, evaluating lower component
counts with inexpensive local refinement, and adding strong FP16/BF16 Tensor Core
controls. Arbitrary sparse operators need useful low-bit execution rather than
permanent native routing. Blocked inner linear algebra or preconditioning inside
a **single LP solve** is worth evaluating alongside SpMV; multiple-solve batching
is not a substitute for the project objective. Keep the broad model roster,
strict original certificates, native/FP32 controls and full costs. No confirmation
is frozen, no broad value gate is passed, and the project is not narrowed to the
subset that happens to contain dense tiles.

## Admission and preserved failures

The final CPU candidate passes 15 isolated Rust and 10 Python contracts. Device
admission retains 582 product/solve responses, with 21888 independent product
outputs, original serial checking of every solve assessment, forced recovery,
cancellation, both transpose directions, zero-tile routing and positive strict
certificates. Each of memcheck, racecheck, initcheck and synccheck passes 126
responses / 3828 product outputs, including solver execution. Compact/expanded
fragments, one/four-warp launches and one through four components are covered.

The unchanged supervisor passes its 39-contract suite and a fresh supervised
CPU workload. Hash-bound readmission releases prospective work only; it does not
explain or repair the earlier missing supervisor receipt or its 39 missing cells.
The one-second hard supervision bound and all 100 ms advisories remain unchanged.
Sampled RSS is not a hard peak enclosure.

Two earlier tensor CPU candidates failed Clippy and retain 960 CPU seconds each.
The first tensor development campaign failed in evidence writing: its second
response encountered an immutable `partial.json` filename. Both raw responses,
all 68 planned cells, source versions, and the full 720 CPU / 180 GPU-second
reservation remain. It has no qualified performance comparisons and was not
retried. Later campaigns use append-only partial records and a separately admitted
candidate. Earlier admitted versions and every sanitizer receipt remain local.
An initial reporting attempt assumed newer response fields in the first failed
campaign; its KeyError and full 480 CPU-second charge remain. Corrected analysis
preserves those historical fields as absent, without changing response bytes.

## Evidence and reproduction

Large inputs, raw responses, executable images, failed versions and resource
receipts remain under local `artifacts/gpup-general-v1`. The portable Tensor Core
delta bundle retains the new evidence without copying the entire old scientific
bundle. Exact-byte verification and independent original serial replay run from
an extracted root. Only compact results and validation receipts are committed.
Use fresh identities under `tools/lp_general_budget.py`; never reuse an old cell.

Reproduction tools are `lp_general_tensor_cpu.sh`, `lp_general_tensor.py`,
`lp_general_tensor_admit.py`, `lp_general_tensor_bench.py`,
`lp_general_tensor_analyze.py` and `lp_general_tensor_portable.py` in `tools/`.
Public defaults remain unchanged. Local admission is not production availability
or a general performance guarantee.


## Delivery acceptance and allocation

Final native acceptance passes 638 repository Rust / 820 Python tests, native
replay, dependency checks, documentation and smoke. The isolated candidate passes
15 Rust / 10 Python contracts. All numerical, device, helper and test source bytes
match the retained final native snapshot; numerical source also matches the
admitted image. [Validation receipt](lp-general-tensor-validation.json) binds the
checks, source comparisons, failures, charges and portable replay.

Portable delta replay verifies 39385 files and all 288 retained scientific
responses / 3767 assessments, including the two responses in the failed first
campaign. Offline identical-witness/tier/proof/result deduplication uses 2638
independent serial assessments; the solver itself does not memoize endpoints.
All 66 first-campaign missing cells and the earlier general pilot's separate
39 missing cells remain missing. All 43430 earlier archived scientific files
remain exact. The local delta has 45 compressed parts, 1438837023 bytes in total;
these are evidence artifacts, not Git blobs. Original models, raw response bytes,
all failed versions and full charges remain retained.

The independent allocation stays open under its unchanged 240000 CPU / 30000 GPU
ceiling and phase caps. Four new failed development/reporting reservations retain
3120 CPU / 180 GPU seconds; every settled job has empty cleanup. The one-second
supervisor and 100 ms advisories are unchanged. No confirmation, public-default
change or publication is implied. Commit locally only.

Open allocation checkpoint: 61348.495516364 CPU / 5583.955075437 GPU seconds.
