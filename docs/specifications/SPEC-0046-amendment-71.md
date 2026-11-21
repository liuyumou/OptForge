# SPEC-0046 amendment 71: diagnostic settings construction and fresh quality

Quality-v2 passes formatting, then compilation rejects LpSettings::default in the
new diagnostic because this repository exposes LpSettings::published instead.
Use published(100,100) with the diagnostic's explicit zero scaling/power settings.
Solver arithmetic is unchanged by this diagnostic-only correction. Preserve the
failed sources, full 2400 CPU / zero GPU charge and empty cleanup.

Fresh quality-v3 reserves 300 seconds / 1200 CPU seconds, using one build worker
and the same format, complete Rust tests, Clippy, release and CUDA compilation.
Previously compiled library artifacts remain available; no acceptance stage is
omitted. The 2835.597137432 native CPU seconds remaining cover this reservation.
Bind candidate sealing and subsequent reports to quality-v3. All approved phase
caps, resource checks, strict certificates and no-repeat requirements remain.
