# SPEC-0046 amendment 51: proposed GPU packing development

The user requests GPU FP4 packing, skipping packing when no tile is eligible,
additional preparation improvements and preparation/complete solve measurements
with unchanged strict original-model certificates. This proposal retains total
320000 CPU / 35000 GPU seconds and every existing failed charge. It is not yet an
applied phase-cap change.

Proposed CPU phase caps: implementation6000/native18000/admission52000/
development151000/reporting92000/cleanup1000. Proposed GPU phase caps:
admission7000/development28000. Four slots, 128 GiB sampled aggregate host RSS,
80 GiB owned GPU, 400 GiB owned storage, four GiB physical host headroom, all idle
and ownership checks, and the container-only restriction remain unchanged.

The settled starting checkpoint is 235329.259157332 CPU / 26771.899422302 GPU
seconds. The transfer leaves 84670.740842668 CPU / 8228.100577698 GPU seconds;
GPU admission has 1618.465895699 seconds and development 6609.634681999 seconds.
No increase in total time, memory or storage is proposed.

The opt-in candidate must preserve canonical packed bits in both orientations,
strict original-model 1e-9 certificates, control100/certificate500, original solve
CUDA, all historical sources and all attempted scientific cells. New GPU kernels
require bitwise CPU comparisons, exact solve continuations and all four complete
sanitizers before performance measurements. Unchanged preparation and solve
kernels retain their existing independent admissions, with new integration checks.

The prospective scientific scope is a new six-family paired 64 M preparation and
fixed-work complete-cost cohort, then six new FP4-request billion-NNZ solves with
the same 1000-update / 600-second solver settings as the retained image-v9 cohort.
All six families remain visible, including zero-eligible fallbacks. Existing
image-v9 billion timings are a descriptive historical comparison, not a new
randomized paired experiment. Deadline/update differences, regressions and failed
certificates remain explicit. Full original-model independent final/intermediate
proofs and potential repaired witnesses are reserved before each cohort freeze.

The six billion solve reservations total 6100 GPU / 24400 CPU seconds; independent
audits reserve 5450 wall / 21800 CPU seconds. Admission, the small cohort and
completion must fit the remaining allocation before billion freeze; unsupported
cells are retained if capacity cannot be admitted. No attempted cell is retried.
Exact small-cohort ceilings and measured capacity formulas are frozen only after
candidate correctness and capacity admission. Stage settlement can return unused
reservation capacity but cannot erase failures or justify exceeding any cap.

Applying the transfer requires a supplemental approval and new source-bound
operational readmission. The original approved COPT overrun exception remains
restricted to its original immutable settlement; every other overrun still closes
execution. Preserve the original approval and add a separate transfer record.
No public adoption or publication is authorized; commit locally only.
