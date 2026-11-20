# SPEC-0046 amendment 38: retain the packed-bound refusal and finish only unstarted diagnostics

The coupled 64 M candidate diagnostic completes and retains its raw preparation
response, but its worker refuses finalization because the prospective packed-array
bound omitted the two terminal residual-offset entries (eight bytes total).
Preserve that failed reservation, all raw values, sources, complete 960 CPU-second
charge and empty cleanup. Exclude its performance timing; do not retry it. This
is a capacity-accounting bug, not an observed numerical mismatch. An unstarted
reference response may still be compared offline with its retained packed hash.

The exact final-array formula now includes all four terminal offsets across
half-tile and residual orientations. Include the explicit CPU construction clone,
Pock term lists/capacities and spectral scratch required by amendment 37. The
corrected coupled one-billion requirement is 64 GiB host plus unchanged 4 GiB
physical headroom, compared with the earlier 72 GiB declaration. The preliminary
60 GiB estimate remains superseded. Numerical sources and diagnostic executable
remain identical to image-v9; no solver or certificate arithmetic changes.

Freeze a tail disposition containing only the original eight never-attempted
cells. Keep the original fifteen-cell manifest and all seven attempts intact.
Use the corrected 64 GiB reserve for the never-started billion CPU preparation,
and retain 20/32 GiB for the remaining 64/256 M cells. Fresh operational CPU v17
must pass the original supervisor tests and all 42 resource/evidence/timing/memory
tests. New plans bind the tail and corrected sources for both old cleanup
dispositions. GPU operational v16 and all device/sanitizer gates remain pending.
No allocation cap, strict criterion, GPU guard or publication status changes.
