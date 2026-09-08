# Tests

Rust unit tests live beside implementation. CLI process tests live in
[optimizer-cli/tests](../crates/optimizer-cli/tests/cli.rs) so cargo test discovers
them. Cross-language artifact integration tests live in
[integration](integration/test_artifacts.py). See the
[test strategy](../docs/architecture/testing.md) for contracts and future coverage.
