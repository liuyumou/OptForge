# GPUP-DELIVERY2

Isolated delivery variant of the exact FP4 checker executor. Numerical modules
are imported from retained sources; public solver defaults are unchanged.
See [SPEC-0033](../../docs/specifications/SPEC-0033-delivery2.md).

The default batches checker pipe writes and overlaps independent original-model
checker preparation with CUDA setup. `GPUP_DELIVERY2_CONTROL=1` selects retained
sequential setup and unbuffered requests in the same executable.

CPU acceptance: `bash tools/check_delivery2_cpu.sh`, with the pinned Rust toolchain
and Python dependencies from `tools/requirements.txt`. The full repository gate
is `bash tools/check.sh`. Source-bound process replay is separately supervised
by `tools/lp_delivery2_cpu.py` when retained model artifacts are provisioned.
GPU execution requires the pinned shared lease and separate supervised allocation.
