# Compact LP Study Evidence

Purpose: write smaller independently verifiable LP study artifacts under
[SPEC-0015](../specifications/SPEC-0015-compact-lp-evidence.md). Scope: study-only
single solves, verification, replay and conversion; ordinary solve output stays compatible.

After a normal build, run a host solve without any device:

```bash
optimizer lp-study solve --model examples/lp-model-v1.json \
  --config examples/solve-config-v1.json --backend host-lp \
  --lp-settings examples/lp-settings-v1.json \
  --lp-evidence compact.endpoint.json --evidence-format compact-v1
optimizer lp-study verify --model examples/lp-model-v1.json \
  --evidence compact.endpoint.json
optimizer lp-study transcode --model examples/lp-model-v1.json \
  --evidence compact.endpoint.json --output restored.endpoint.json \
  --evidence-format legacy
```

Compact solve prints only the assessment JSON to stdout. The endpoint retains the
original candidate, dual witness, row IDs, method/settings, executed identity and
payload hash. Its validation digest binds the omitted detailed validation report.
Verification recomputes that report from the exact original model and then invokes
the existing independent verifier, including conservative dual certification.

`--evidence-format legacy` is the study solve default. Ordinary `optimizer solve`
does not accept this flag. Existing LP endpoint versions 1–5 remain readable.
Replay defaults to the input format and optionally accepts the same explicit format
flag. The model and evidence each use the ordinary 16 MiB input bound by default;
`--model-byte-limit 134217728` explicitly permits study solve/verify/replay/transcode
inputs up to 128 MiB. It does not increase the worker's output cap.

New compact/transcode destinations and their `.partial` siblings must not exist.
Failed writes retain partial files; publication cannot overwrite another writer's
output. Conversion verifies first and performs no solve. A converted limited,
interrupted or numerically rejected result retains that outcome and is not a new
performance sample. Separate ordinary model files remain necessary for verification.

The codec does not extend research-specific, batch/session or external COPT formats.
GPU replay requires the shared host lease and the recorded execution code image;
compact formatting does not change those requirements. See
[GPU operations](../operations/gpu.md) and [ADR-0027](../decisions/ADR-0027-compact-lp-evidence.md)
for the bounded comparison and preserved resource authority.
