# LP precision study operations

Purpose: reproduce the bounded LP-only study under accepted SPEC-0013 and
[ADR-0014](../decisions/ADR-0014-lp-baseline-protocol.md). Owner: experiment tooling.
Status: GPUP-2 complete; see the [baseline evidence](lp-baseline-gpup2.md).

## Prepare and validate

```bash
cargo build --workspace --locked
python3 tools/lp_generate.py
bash tools/check.sh
cargo build --release --workspace --locked
python3 tools/benchmark_lp.py --dry-run
```

The materializer recreates ignored artifacts/lp-inputs-v1 and verifies every byte
against the three committed manifests. It does not run validation/held-out solves.
Do not use --freeze to change this campaign: changed choices require a new decision
and experiment identity. All 32 models fit the unchanged 16 MiB input limit.
Generated scheduling models reuse the Rust encoder with only integrality relaxed;
the existing inspected Taillard cases remain development diagnostics.
Generator sha256-counter-lp-v1 fixes the remaining parameters in tools/lp_generate.py:
irregular row width is 4 + draw(29), dense rows contain their 32-column block plus
column (i + 32) modulo n, and scaling coefficient (i, j) is multiplied by
2 ** (((i + j) modulo 41) - 20). The original model and recomputed objective/row
bounds retain that transformation, which is not an equivalent solve rescaling.
Sizes, partition/family seed, generator identity, model and witness hashes determine
each frozen case; both sizes remain in the same partition group.

## Inspect one independent endpoint

```bash
target/release/optimizer solve --backend host-lp \
  --model examples/lp-model-v1.json --config examples/solve-config-v1.json \
  --lp-settings examples/lp-settings-v1.json --lp-evidence /tmp/lp-endpoint.json
target/release/optimizer lp-study verify \
  --model examples/lp-model-v1.json --evidence /tmp/lp-endpoint.json
```

The ordinary solve JSON remains version 2. The separate endpoint sidecar carries
an untrusted dual in canonical row order and a fresh original-model assessment.
The checker reconstructs feasibility, objective, certificate and conservative gap;
it does not trust a native status or best_bound diagnostic. HiGHS native LP
best_bound can be unrelated to the certified endpoint; both retain their original
meanings. Limits/interruption never become successful completion after the fact.
Original-model feasibility retains the tolerance-based SPEC-0001 contract.

## Run and resume the development study

```bash
python3 tools/benchmark_lp.py --output artifacts/gpup-baseline-v1
python3 tools/lp_report.py --input artifacts/gpup-baseline-v1
```

A matching full-native gate receipt is required. Use the same output directory to
resume; prior attempts are not repeated. The authoritative ledger lives in
artifacts/lp-campaign-ledgers/gpup-baseline-v1 and binds one output directory;
changing --output cannot reset the budget. A portable ledger snapshot accompanies
the raw trial bundle. The runner freezes source/binary/device
identity across resume and archives the exact dirty source as source.tar, alongside
execution.json and its hash. Raw trials preserve manifests/configuration hashes,
code-object/native archive identity, toolchains, device and thermal/process context.
The report checks its input references and ledger coverage. The source archive
allows reconstruction even when the measured tree had not yet been committed.

Each solve is a fresh foreground process. Primary timing includes file input,
setup, context creation, data transfers, solver work, independent host checks,
evidence serialization and teardown. The separate verifier is also run before a
trial is accepted; its additional host cost is reported separately. Profiles run
separately and never enter primary timing ratios. Their synchronized phase clocks
add no synchronization to primary executions. Uninstrumented startup/output and
teardown are still charged in primary elapsed time, not represented as zero.

The runner names only the approved RTX 5090 UUID and pauses for competing compute
processes/nonzero GPU utilization or unavailable activity telemetry. Every GPU job
uses tools/gpu_job.sh's supervised form and the same host-wide flock as ordinary
jobs. A supervisor retains ownership and its deadline if the outer coordinator
exits. Queue wait is separate from leased wall time. No device substitution.

Ten seconds trigger SIGINT; two further seconds permit cleanup before SIGKILL.
Signal intents are persisted before delivery/escalation. The Linux supervisor
adopts orphaned process-group children and reaps them before releasing the lease.
An additional one-second reservation covers supervisor setup/lease teardown, so
one job reserves 13 seconds. Charge any unexpected overrun fully and stop. CPU
work is pinned to one allowed core. An 8 GiB process-tree RSS watchdog samples at
10 ms; it is not hard isolation and may double-count shared pages. LP device
buffer accounting includes all invariant and working allocations, with one-element
empty buffers, and enforces 8 GiB. Driver/context memory is separate telemetry.
Output files are bounded at 32 MiB each; virtual address space is not an RSS limit.

Reserve and fsync before execution. Flush/fsync each settlement. Exclusive
campaign ownership rejects concurrent writers. After interruption, unresolved
reservations are charged in full; a torn last write is preserved as evidence.
Malformed complete events block resume. An unfinished intent remains a failed
attempt, never a resurrected success. GPU study spending is capped at 900 seconds
of the 1,800-second baseline phase, inside the unchanged 28,800-second campaign.
Acceptance jobs are separately budgeted and recorded in active-task state.
The original baseline consumed 173.148261443 GPU seconds. The subsequent
[diagnosis](lp-gpu-slowdown-diagnosis.md) added 20.994604580 seconds, bringing
cumulative study consumption to 194.142866023 seconds. Preserve its ledger
and raw bundle; future configuration/source changes need a recorded migration
that carries forward spending, not a fresh budget.

## Read the report

Report paired per-instance medians and 95% percentile bootstrap intervals, with
10,000 paired resamples and seed 17002. Only mutually certified original-backend
pairs enter ratios. Full coverage, failures, timeouts, missing trials and fallback
execution remain alongside them. Three repeats are preliminary variability
measurements, not finalist evidence or cross-problem generalization. A profile
may expose setup/host-check costs even when no solver closes the requested gap.

The existing host uses adaptive restart/weight control while the GPU uses fixed
anchors/weight. These are distinct baseline implementations, not an algorithmically
matched acceleration claim. GPUP-3/4 supplies the matched/tuned control. Neither a
fast kernel nor this baseline report selects a mixed-precision recipe.

## Device acceptance and compatibility

```bash
bash tools/gpu_job.sh GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48 \
  bash tools/lp_gpu_check.sh
```

This runs all three regular device suites, all four sanitizers on the two added
study_observation tests, and actual CLI device/fallback verification. It refuses
missing sanitizers and device skips. It does not claim the broad historical
sanitizer suite was run; the older atomic negative-control racecheck limitation
remains separately recorded. Ordinary builds and the CPU gate require no device
or CUDA toolkit.

The five new LP schema names are separate from existing SPEC-0007 records. There
is no migration from a smoke result into an LP trial. Existing readers retain
their meanings; unsupported future LP versions are rejected. Synthetic schema
examples explicitly name their lack of measurement evidence.

## Matched FP64 follow-up

[ADR-0016](../decisions/ADR-0016-matched-fp64.md) freezes the next bounded study.
Tooling now reuses one strictly checked schema snapshot per process; restart the
process to observe schema edits. GPU admission waits up to 300 seconds for zero
utilization and no compute processes before reservation, with 250 ms polling.
Unavailable telemetry pauses with a retained activity sidecar. Version-2 workers
recheck under the shared lease for at most three seconds; GPU jobs reserve 16
seconds and charge all leased time. A blocked leased attempt is retained and never
silently retried. No device is substituted. Existing frozen artifacts stay intact.
