# AI Optimizer

A Rust-first research project for mathematical optimization and scheduling with
selective GPU acceleration. The current release is **M0: repository bootstrap**.
It builds and tests project tooling; it does not solve optimization models.

## Quick start

Supported development platform: Linux x86-64. CPU checks require Rust (installed
through rustup), Python 3.11+, Git, and util-linux `flock`. NVIDIA drivers are
optional for discovery. CUDA and HiGHS are not build dependencies at M0.

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r tools/requirements.txt
cargo install cargo-deny --version 0.19.0 --locked
cargo build --workspace --locked
cargo run -p optimizer-cli -- hello
cargo run -p optimizer-cli -- gpu discover --dry-run
bash tools/check.sh
```

The hello command prints `hello workspace`. Discovery prints JSON with
`status: available` and devices sorted by UUID, or `status: unavailable` and a
diagnostic. It never creates a CUDA context. Checks include a bounded process
smoke measurement whose artifact is written to `artifacts/bootstrap-smoke.json`.
A Git commit is required for that measured record.

## Project navigation

- [Current status and milestones](wiki/status.md)
- [Contributor and autonomous workflow](CONTRIBUTING.md)
- [Architecture and ownership](docs/architecture/overview.md)
- [Bootstrap specification](docs/specifications/SPEC-0000-bootstrap.md)
- [GPU discovery and lease contract](docs/specifications/SPEC-0006-gpu-lease.md)
- [Artifact contract](docs/specifications/SPEC-0007-artifacts.md)
- [Build and verification](docs/operations/build.md)
- [GPU operations](docs/operations/gpu.md)
- [First experiment tutorial](docs/tutorials/first-experiment.md)
- [Benchmark policy](docs/benchmarks/protocol.md)
- [Glossary](wiki/glossary.md)
- [Backlog](state/backlog.yaml) and [active task](state/active-task.md)
- [Changelog](CHANGELOG.md)

The source [implementation plan](implementation-plan.md) defines M0 and the
later M1-M6 roadmap. The [research plan](ai-native-optimizer-plan.md) provides
long-term direction. Their unvalidated research claims are hypotheses.

## Layout

`crates/` contains the Rust workspace. Only the CLI, GPU discovery/ownership,
and embedded artifact schemas have runtime or public content. Numerical crates
reserve ownership boundaries with module documentation and no solver APIs.
`schemas/`, `examples/`, `tests/`, and `tools/` provide executable contracts.
`docs/` is authoritative; `wiki/` provides navigation. Python SDK, native HiGHS
integration, CUDA kernels, and performance suites are deferred.

## License

Project code and small generated fixtures use the [MIT license](LICENSE).
External datasets and native dependencies need their own license records before
introduction. No third-party benchmark dataset is bundled.
