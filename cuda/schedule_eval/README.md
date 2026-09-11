# CUDA Schedule Evaluation

Reserved for M5 kernels and their narrow CUDA C++ host boundary. No kernel is
compiled or launched in M0. Introduce implementation only after the C6
heterogeneous-computation specification accepts layout, arithmetic width, limits,
CPU equivalence, fallback, timing, and recovery.
All future compilation/sanitizer work belongs on the serialized labeled GPU runner.
