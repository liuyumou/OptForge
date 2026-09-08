# Build and Verify

Purpose: reproduce local and CI acceptance. Scope: Linux M0-M1.

Install rustup, Python 3.11+, Git and util-linux. The root toolchain file pins Rust.
Create a Python virtual environment and install tools/requirements.txt, then:

```bash
cargo install cargo-deny --version 0.19.0 --locked
bash tools/check.sh
```

[check.sh](../../tools/check.sh) runs formatting, warnings-as-errors Clippy,
workspace tests and build, warnings-as-errors rustdoc, dependency advisories and
licenses, schema/provenance checks, artifact negative tests, documentation links,
and the benchmark smoke. Run from a committed checkout for measured provenance.
Cargo.lock is committed; use --locked for builds.

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
