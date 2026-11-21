# SPEC-0046 amendment 54: opt-in canonical GPU packing and capacity

Image-v10 adds a separate pack.cubin compiled with FP64 contraction and flush to
zero disabled. Integer structural counting and fixed per-tile FP64 encoding
produce both canonical fragment orientations; no floating atomic sum or solver
arithmetic changes. Host work constructs sorted tile metadata and exact offsets.
All original CSR/CSC indices, finite coefficient domains and bitwise transpose
identity are checked before packing or the no-eligible early return. A bounded
4096-entry structural hash overflow explicitly selects the exact host packer.
No fragment, residual, coverage or encoding buffer is allocated for zero eligible
tiles. GPU coefficient validation replaces the redundant host coefficient scan
only in this opt-in array-executor path. Other paths and defaults remain intact.

GPU output returns to canonical host Packed, then uses the unchanged device
initializer; this first candidate still includes those transfers in measured
packing and setup cost. Metadata/downloads, context setup and teardown remain in
complete time. The proposal does not claim device-resident packing reuse.

Capacity formula 7 retains every formula-6 stage and adds resident originals,
engine values, final Packed, 32 bytes per axis, 96 bytes per tile and 64 MiB
scratch for GPU packing host work, plus the unchanged 8 GiB internal allowance
and 4 GiB physical headroom. The device bound retains both original orientations,
both residual orientations, all fragments/exponents, metadata, coverage, tile
keys/coordinates and padding. It matches the conservative Rust pre-allocation
check and takes the maximum with existing preparation/solve bounds. Both fragment
indices and the 80 GiB device ceiling are checked before tile metadata allocation.
The bounded hash fallback retains the original formula-6 host-packing allowance.

Admission compares all canonical packed fields and residual FP64 bits, covers
rounding neighbors, exponents, all component counts and fragment layouts, partial
and empty axes, no eligible tiles, hash overflow and malformed inputs. Compare
60 exact solve continuations including checkpoint recovery/cancellation, then run
all four complete sanitizers on packing and twenty solve continuations each.
Unchanged original-model independent checking is required for every assessment.
No performance claim or timing cohort is admitted by source availability alone.
