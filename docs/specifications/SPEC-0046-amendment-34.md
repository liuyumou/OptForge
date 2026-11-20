# SPEC-0046 amendment 34: native parameter typing and serialized CPU compilation

Retain `copt-native-cpu-v1`, sources, the first original model and conversion,
stdout/stderr, empty cleanup and full 480 CPU / zero GPU seconds. The native C API
rejects `MemLimit` through the integer setter before import or solve. Unlike the
previous high-level Python binding, the C interface requires the documented double
setter. Bind the supported parameter names to their native types and roundtrip every
value. Fresh native CPU admission v2 checks the corrected adapter; no scientific
cell or completed solve is repeated.

The second timing build's coordinator retains a 1.269-second sampling pass and
32 sampled threads. Both failed build attempts keep their sources and full charges.
After the independent CPU contracts pass, prospectively serialize Cargo compilation
with `CARGO_BUILD_JOBS=1` for fresh timing quality v3 while retaining existing
three-plus-one CPU placement, all tests, Clippy, release flags and CUDA compilation.
This reduces concurrent compiler work within the four-slot allowance; it does not
change arithmetic, sampling cadence, failure accounting or any guard. GPU admission
and billion-scale capacity remain separate and incomplete.
