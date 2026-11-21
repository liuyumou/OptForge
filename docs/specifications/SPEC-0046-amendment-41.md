# SPEC-0046 amendment 41: retain compiler-path admission failure

`complete-harness-v1` passes all 45 Python contracts, then stops before compiling
the standalone chunk-copy diagnostic because `rustc` is absent from the current
PATH. Preserve the reservation, copied library, source snapshot, empty cleanup and
full 480 CPU / zero GPU seconds. No device or scientific cell starts.

The existing container toolchain is
`/root/.rustup/toolchains/1.93.1-x86_64-unknown-linux-gnu/bin/rustc`.
Use that explicit compiler for a fresh `bounded-copy-build-v2` and supervised
`complete-harness-v2`. Bind its executable hash; install nothing and change no
solver/library arithmetic. Retain the first incomplete build directory. All
remaining named GPU admissions are still unattempted and keep their identities.
