# SPEC-0046 amendment 3: prospective operational readmission

The first 128 M image-v2 capacity cell stops during host preparation with no
response and no observed CUDA context. The retained final reason is
`cleanup_incomplete`; its last trace has an observation interruption. The original
guardian's final cleanup reason supersedes its earlier trigger, so the exact
initiating cause is not reconstructed. The full 1920 CPU / 480 GPU-second
reservation remains charged, and this scientific cell is never repeated.

Subsequent read-only observations find every recorded process identity gone and
the pinned GPU idle. A separate source-bound cleanup disposition preserves the
original false cleanup receipt and active journal entry. It admits only CPU
admission/reporting/cleanup until fresh operational GPU admission passes. No
historical supervision is reconstructed. A prospective GPU admission job requires
fresh CPU resource-contract acceptance. Later development requires its successful
source-bound settlement, empty cleanup and no overrun.

The complete storage scan now uses directory-entry metadata and one file stat
instead of repeated path construction and metadata calls. It still traverses every
owned file, counts hardlinks once and excludes symlinks. There is no disk-usage
cache or change to the one-second supervisor, every 100 ms advisory, storage
ceiling, placement, GPU ownership requirement, numerical image or total allocation.

After readmission, execute only the never-started coupled 128 M cell from the
original freeze, retaining the missing irregular cell. Later 256 M, 512 M and 1 B
inputs remain distinct, prospectively frozen development stages. Every measured
endpoint still receives independent original-model checking.
