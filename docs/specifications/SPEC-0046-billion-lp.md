# SPEC-0046: Billion-nonzero LP development on the Pro6000

The user explicitly authorizes a separate 240000 CPU-second / 30000 GPU-second
allocation, 128 GiB sampled aggregate host RSS, 80 GiB owned GPU buffers and
400 GiB of owned storage under `/storage/ai-optimizer-billion-v1`. Four CPU slots,
the pinned GPU lease, the original one-second supervisor and every 100 ms advisory
remain. The target is a full LP with one billion original matrix nonzeros, not
one billion arithmetic operations or copies of independent small problems.

The additional condition is **only while the Pro6000 is idle**. Bind GPU UUID
`GPU-6721b13a-30f9-83ec-dace-ba2d9738556f`; require no compute/graphics/MPS processes
and zero observed utilization before each GPU reservation. Continuously check
ownership during execution. Unknown ownership, failed telemetry or a foreign
process stops only our process family. Never stop another user's work. Keep the
interruption and full charge; do not repeat an attempted scientific cell.

CPU phase ceilings are implementation 30000, native 12000, admission 36000,
development 120000, reporting 36000 and cleanup 6000 seconds. GPU ceilings are
admission 6000 and development 24000 seconds. Reserve 512 implementation CPU
seconds for initial preparation and 128 cleanup CPU seconds for closing
administration. Successful jobs charge four times supervised elapsed wall time;
failed jobs retain their entire reservation and sources. Whole-cohort time,
host/device memory, disk and live physical headroom must pass before launch.
No capacity transfer from or modification to the earlier general ledger occurs.

## Implementation and admission

Use an isolated derivative of scale-image-v14, preserving public sources,
historical images and the fast-image-v10 CUDA image. Direct canonical sparse
array construction, streaming generation and chunked binary endpoint evidence
must avoid per-term document copies and retained JSON vectors. Preserve original
coefficient bits, objective/bounds, reduction order, checkpoint recovery and strict
original-model certificate criteria. Construction witnesses never enter solves.
Large dimensions and physical tile/index arithmetic need explicit range checks;
raising old constants alone is not admission. Actual device buffers must have
checked allocation accounting below 80 GiB. All individual evidence files remain
below 512 MiB; chunked original arrays and endpoint objects are content addressed.

Admit exact input/geometry and certificate equivalence on small representatives,
including noncontiguous IDs, both objective senses, empty/rectangular axes,
signed zero, subnormals, overflow/refusal and cancellation/recovery. Compare
complete numerical trajectories with the prior executor and independently check
all final/intermediate endpoints. Fresh device and four scoped sanitizer suites
precede scientific measurements. Validate the operational extension and preserve
the unchanged supervisor's contract suite. An unmappable GPU PID is a refusal.

## Prospective experiment

The ladder is 64 M, 128 M, 256 M, 512 M and 1 B original nonzeros. Keep irregular,
wide, tall, coupled, ill-scaled and degenerate structural families, independently
generated coefficients and explicit connectivity. Keep all historical public and
lower-scale coverage; retain every unsupported capacity cell. Do not infer broad
value from a subset that fits. Native, FP32 and actual FP4x2 use the same shared
preparation and strict 1e-9 certificate policy. Retain 100-update control and
500-update certificates. Initial development uses one seed per family, one rotated
timing repetition and at most 5000 updates; this is not confirmation.

Freeze each complete cohort's exact inputs, binaries, order, solve limits and
reservations after lower-scale capacity observations. No model is admitted merely
because a coarse estimate fits. Input/endpoint storage lower bounds are not full
peak allowances. Include transient preparation, verification, metadata and source
objects. Use directly portable content-addressed evidence to avoid a second
full-size archive copy within the 400 GiB ceiling.

Report complete fresh-process time: generation/preparation where applicable,
parsing, packing, transfers, execution, control/certification, response transport,
independent final checking and owned teardown. Report separate offline audits.
Retain failed, missing, deadline and uncertified results; no retries or historical
regrading. Report actual accepted FP4 work and original versus padded storage.
Publish no default change, confirmation or external result. Commit compact
implementation/protocol/results locally; retain large evidence on approved storage.
