# Coupled FP4 integration research executor

Implements [SPEC-0030](../../docs/specifications/SPEC-0030-fp4-integration.md).
This separate executable supports bounded coupled LP state up to 128 coordinates
per direction. It does not change the public solver or its default tolerances.

The CUDA service uses actual E2M1 Tensor instructions, local FP32 pairs and packed
persistent component state. The host controller applies the operational recovery
policy and audits the original matrix by 200 accepted updates. Independent CPU
checking retains the original-model bound, feasibility and gap mathematics.
Select `certified-1e-7` or `certified-1e-9` explicitly.

Build and test without a GPU:

```sh
cargo test --release --locked --manifest-path research/lp-fp4-integrate/Cargo.toml
cargo build --release --locked --manifest-path research/lp-fp4-integrate/Cargo.toml
python3 -B -m unittest discover -s tests/integration -p test_lp_fp4_integrate.py
```

`check MODEL ENDPOINT TIER OUTPUT` performs a fresh independent check;
`check-service MODEL TIER` checks multiple endpoints in a separate CPU process.
Both receive the original model and endpoint only. `serve IMAGE MODEL` requires
the pinned GPU lease and accepts bounded JSON commands on standard input.

A generation identifies a checkpoint within a solve. A solve identity isolates
fresh prepared solves. Precision changes must restore first and preserve exact
represented state. `finish` destroys per-solve buffers and advances the solve
identity; it preserves lifetime physical accounting. Cancellation is terminal.

The integration tools record every model, source image, attempted update,
checkpoint, refusal, certificate and cost. Cold timings include process startup
and exit; prepared timings report context/checker startup separately. GPU event
timing is a separate metric. Instructions for reproducing a study are in the
specification; a closed allocation does not authorize rerunning its cells.
