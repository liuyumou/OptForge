# Build and Verify

Purpose: reproduce local and CI acceptance. Scope: Linux, M0-M1 and C1 through C4.

Install rustup, Python 3.11+, Git and util-linux. Solving additionally requires
CMake and a C++ compiler for the pinned HiGHS build. The root toolchain file pins
Rust. Create a Python virtual environment and install tools/requirements.txt, then:

```bash
cargo install cargo-deny --version 0.19.0 --locked
bash tools/setup_highs.sh
bash tools/check.sh
```

[check.sh](../../tools/check.sh) runs shell syntax and whitespace checks, a Python
dependency preflight, the pinned native HiGHS build, formatting,
warnings-as-errors Clippy, workspace tests and build, warnings-as-errors rustdoc,
dependency advisories and licenses, schema/provenance checks, artifact negative
tests, re-execution of the committed run record, documentation links, and the
benchmark smoke. Run from a committed checkout
for measured provenance. Cargo.lock is committed; use --locked for builds.

[setup_highs.sh](../../tools/setup_highs.sh) downloads the checksum-verified
HiGHS 1.11.0 source and builds a static CPU library under `target/native`, outside
tracked source. Set `AI_OPTIMIZER_HIGHS_DIR` to use an existing install prefix.
Set `AI_OPTIMIZER_SKIP_NATIVE=1` to run the gate without the native library; that
run prints a warning and is not a complete acceptance pass. Set
`AI_OPTIMIZER_CARGO_HOME` to point the gate at a specific Cargo installation.

`python3 tools/build_docs.py` writes a static book under book/.
`cargo doc --workspace --no-deps --locked` writes public API docs under target/doc/.
The docs workflow archives both. Python is tooling only; no SDK is implemented.
Nextest is optional when CI capacity warrants it; cargo test is the required gate.

## Troubleshooting

Missing NVIDIA tooling is an explicit unavailable discovery result and does not
fail CPU CI. Toolchain/download failures require network access to the official
Rust distribution and crates.io; record failures rather than skipping gates.
Dependency advisories require diagnosis or a narrowly documented policy change.
No advisories are ignored by default. See [known failures](../../state/known-failures.md).
