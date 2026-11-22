# SPEC-0046 amendment 36: bounded preparation storage and upload lifetimes

The user requests reducing required peak memory. The isolated image-v9 candidate
replaces retained dense FP4 tiles, coefficient coverage flags and half-tile lists
with two ordered sparse passes, bounded tile scratch and direct final-array writes.
The previous image-v8 packing routine remains byte-identical as a CPU diagnostic
reference. Preserve all final packed bytes, canonical transpose validation,
component counts, original FP64 model, iteration arithmetic and strict certificates.

Add a checked offset-copy operation in the existing CUDA ownership boundary and
use bounded FP32 conversion chunks for proposal uploads. Original whole-buffer
copy behavior and numerical CUDA binaries remain unchanged. The new operation
must reject element/byte/address overflows and finish each borrowed-host copy before
returning. Allocate/upload device state before creating host control scratch, then
release host packed arrays after synchronous upload. Retain their exact logical
metadata for reporting and scheduling. Include all lifetime and transfer overhead
in exclusive and aggregate timing; unchanged deadlines cover the full process.

Require CPU exact representation comparisons, transfer-boundary tests, formatting,
Clippy, release/CUDA compilation and source-bound image sealing. New GPU operational,
continuation and all four sanitizer admissions remain mandatory before full solves.
No current GPU admission is inferred from CPU evidence. Public defaults, strict
original-model 1e-9 criteria, control100/certificate500 and all ownership/supervision
limits remain. No changes to certificate arithmetic are proposed in this stage.

Prospectively measure fresh, separate-process CPU preparation runs for both the
retained reference and candidate on all six 64 M inputs and coupled 256 M. Compare
complete packed-array hashes and dimensions without retaining two packed results
in one process. Record input/engine/packing/process costs, exact live-buffer bounds
and sampled RSS, including regressions. A single candidate-only billion-nonzero
coupled CPU preparation may run only if its derived full reservation and physical
headroom fit; this is not a full LP solve and has no paired billion speedup claim.
Freeze every diagnostic cell before execution with solve=False and CUDA=False;
never retry any attempted cell. Existing failed reservations and charges remain.

Refine capacity prospectively from the new allocations and lifetime maxima, with
explicit preparation/upload/solve/independent-check bounds and the original 8 GiB
internal allowance plus 4 GiB physical headroom. A smaller derived reservation
must come from removed allocations, not a changed guard. Keep the full thirty-cell
billion comparison unfrozen until all project and COPT admissions and complete
reservations fit. Existing phase caps and 240000 CPU / 30000 GPU totals remain;
new CPU-only development identities require source-bound operational plans for
both historical cleanup dispositions. All work remains container-only, local and
non-published, with no reset, shared-memory clearing or other-job signals.
