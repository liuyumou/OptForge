# SPEC-0046 amendment 25: exact packing allocation refinement

Retain all six image-v5 CPU packing pairs and their exact outputs. The five
zero-tile cases improve, but the actual-FP4 coupled case regresses from 3.858 to
3.994 seconds. These are single paired stage measurements, not full preparation
or solve results. Preserve this regression and every original source/charge.

Image-v6 refines the same isolated packer: reuse each tile's owned value buffer
as quantization residual scratch, following the original encoder's exact arithmetic
order, then release it before orientation construction. The original encoder stays
as the independent packing reference. Preallocate exact fragment, exponent, column,
offset and residual lengths using already-verified tile/coverage counts. Packed
values, coefficient order, strict transpose validation and all solve/certificate
arithmetic remain unchanged. Keep the conservative capacity formula unchanged.

Require a fresh full isolated quality build and the complete packed-representation
regressions before sealing image-v6. A new CPU diagnostic build links that library;
freeze six fresh 64 M paired stage cells with the same alternating order, 240-second
cell ceilings, four CPU slots, 20 GiB sampled RSS and 1 GiB storage. Keep complete
source/model/request/executable bindings, all outcomes and supervision. Never repeat
an attempted cell from the first diagnostic cohort. Distinguish stage measurements
from unmeasured full preparation, GPU execution and total solve cost.

Operational plan v14 permits only the six new named CPU development diagnostics
after fresh CPU acceptance while GPU admission remains incomplete. Supersede only
never-started operational GPU v13; preserve failed v11/v12 and their full charges.
Image-v5 GPU admissions and all ten science cells were never started; future fresh
GPU validation and timing cohorts target image-v6 and still require the original
idle-result check, five-minute proof, operational admission, exact preparation and
continuation comparisons, and all four complete sanitizers before science.

No supervisor, timeout, idle/ownership guard, certificate, allocation or phase-cap
change. Public defaults and both CUDA binaries stay exact. Continue container-only
access with no reset, shared-memory clearing or other-job signals.
