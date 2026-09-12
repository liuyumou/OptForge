# Microbenchmarks

There is deliberately no criterion harness here. Solver timing lives in
[`tools/benchmark_search.py`](../tools/benchmark_search.py), outside the
acceptance gate, and this note records why so the choice is not silently
re-litigated.

`tools/check.sh` runs `cargo clippy --workspace --all-targets`, which compiles
bench targets on every gate run, and `cargo deny --locked check`, which turns
every transitive dependency into a policy obligation and a lockfile change.
Criterion would put both on the critical path of a gate that currently finishes
in about ninety seconds, in exchange for a measurement run by hand. Criterion
also measures functions, while the protocol requires end-to-end timing including
transfers; driving the built binary gets that by construction, and a
microbenchmark of an inner loop would be easy to make look good without
answering the question.

A criterion harness becomes the right tool when a specification states a
measurable algorithmic contract that a function-level measurement can check. M0's
process smoke never was one, and neither is a node-path diagnostic.
