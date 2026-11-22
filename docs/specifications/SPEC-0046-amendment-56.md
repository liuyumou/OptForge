# SPEC-0046 amendment 56: preserve compile failure and correct guard placement

GPU-pack-quality-v2 reaches the compiler but rejects a pre-allocation guard placed
in the residual-download method instead of the top-level packing method. Preserve
its full 1920 CPU-second charge, source snapshot and empty cleanup. Move the guard
to immediately before tile metadata allocation; its bounds remain unchanged.
Skip reads of unused allocation padding for empty residual arrays. No GPU
candidate or scientific timing has run. Fresh quality-v3 performs complete native
isolated Rust tests, formatting, Clippy, release and CUDA compilation in the native
acceptance phase within its already approved cap. All failed receipts remain;
there is no cap change, scientific-cell retry or certificate change.
