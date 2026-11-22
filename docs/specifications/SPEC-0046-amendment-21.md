# SPEC-0046 amendment 21: bounded image-v4 comparison analysis

Before any image-v4 capacity cell starts, separately reserve the existing complete
numerical transcript comparison. That comparison expands retained endpoint arrays
into Python values and therefore needs explicit host and CPU accounting in
addition to each solve and each independent original-model check. Each new v3/v4
cohort comparison runs with 32 GiB sampled host RSS, unchanged 4 GiB physical
headroom and a 600-second wall reservation in reporting. Its numerical comparison
and output format stay unchanged. No old comparison is repeated or reconstructed.

The final compact report compares the already independently checked endpoint
content-addressed manifests without expanding another set of Python vectors.
This supplementary identity check does not replace the original scalar checker,
intermediate checks or complete paired transcript comparison. Source-bound results,
failed reservations, strict certificate criteria and all global limits remain.
