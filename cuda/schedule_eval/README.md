# CUDA Schedule Evaluation

Reserved for the C6 batched schedule evaluator. No kernel is compiled or launched
yet.

The contract this directory was waiting for is
[SPEC-0010](../../docs/specifications/SPEC-0010-heterogeneous-computation.md),
which accepts layout, arithmetic width, limits, CPU equivalence, fallback, timing
and recovery, and
[ADR-0009](../../docs/decisions/ADR-0009-cuda-driver-boundary.md), which
authorizes the driver boundary these kernels are reached through. Two of those
decisions shape every file that will land here: arithmetic is `u32`, because
compute capability 12.0 allows a thread block at most 99 KB of shared memory and
a `u64` head/tail table would not fit; and no kernel may depend on thread block
clusters, because that capability accepts the directive while `cluster.sync`
degenerates to a no-op.

Kernels are compiled out of tracked source by `tools/setup_cuda.sh`, never by
`cargo build`. All compilation and sanitizer work belongs on the serialized
labeled GPU runner.
