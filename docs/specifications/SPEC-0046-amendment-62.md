# SPEC-0046 amendment 62: retained seal interruption and independent artifact audit

GPU-pack-quality-v7 passes complete native acceptance with end-of-build source
bindings, and the full resource harness passes 97 tests. GPU-pack-seal-v1 writes
the five files and binding.json, then supervision records lost_coordinator_heartbeat
with empty cleanup and no overrun. Preserve its full 120 CPU-second charge and all
outputs; the heartbeat cause is unproven. No GPU candidate has run.

Do not repeat the failed seal or rewrite its files. A separate read-only seal audit
must compare every retained artifact to the admitted v7 build output, both old
CUDA modules, the binding document and all frozen numerical sources. Only a passed
supervised audit admits these existing artifacts for subsequent GPU validation.
Use the existing four-slot placement helper to reserve one of the admitted CPUs
for the coordinator/guardian during that audit; no affinity escapes the four
approved CPUs and no heartbeat, observation or cleanup criterion changes.
The failed resource receipt remains failed. No scientific cell is retried.
