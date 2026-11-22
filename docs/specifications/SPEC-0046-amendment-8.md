# SPEC-0046 amendment 8: CPU input construction while the GPU is unavailable

The GPU ownership refusal does not prevent CPU-only construction of the six
already-authorized billion-nonzero originals. Prospectively admit only the six
named `generate-1b-{family}-v1` jobs after fresh CPU operational acceptance. Each
uses the unchanged admitted streaming generator, fixed seed 861119 plus family
index, and the admitted original scalar construction checker. The wrapper verifies
the generator and checker bindings before allowing this limited exception.

Each job has its own 1800-second wall reservation, four CPU slots and no GPU access.
Declare 112 GiB host RSS for wide, 80 GiB for irregular/tall/ill-scaled/degenerate,
and 64 GiB for coupled; reserve 30 GiB additional storage per family. Live physical
headroom, aggregate storage, the original supervisor and all advisories still
apply. Every failed or incomplete generation retains its complete charge and
sources. A later request may consume an already-generated immutable input but may
not repeat an attempted scientific cell.

Operational plan v7 binds this exception and the stronger ownership guard. Its
fresh CPU tests supersede v6 CPU acceptance for prospective execution. GPU
admission v7 supersedes the never-started v5/v6 GPU jobs; all GPU science remains
blocked until the device has demonstrably returned to idle and readmission passes.
Only input generation and scalar construction checking are exempted from this
GPU-specific prerequisite. The final solve cohort and new GPU preparation module
still require their separate full admissions. Totals and phase ceilings do not
change, and the general scientific allocation remains untouched.
