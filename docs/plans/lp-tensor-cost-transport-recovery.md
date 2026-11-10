# GPUP-8 supervisor transport recovery

Status: accepted by explicit user approval, 2026-10-23. Table figures describe the transfer before recovery setup; every subsequent charge is additional within these caps.

The first full native command passed Rust/native and dependency checks. Its
Python suite completed 401 tests with one failure: the historical PR source
reader does not yet recognize this continuation's module/example registrations.
Documentation and smoke checks did not run. Separately, the coordinator's final
observation packet exceeded the guardian's 65536-byte receive buffer. The packet
was truncated, leaving no valid final resource receipt. The misleading
`refused_before_launch` label must not be read as evidence that the command never
ran. All three recorded supervisor/entry identities exited. No GPU work ran.

Preserve the raw log, original unsettled journal and separate
[refusal receipt](../benchmarks/data/tensor-cost/native-transport-refusal.json).
Charge the full 2200 native CPU seconds because result accounting is incomplete.
All reporting funds are also charged. Current cumulative CPU upper accounting
is 25507.557917574 / 35900 seconds. Do not restart the failed journal.

The prepared source repair stores the bounded completion result atomically on
disk and sends only its length and SHA-256 over the control socket. The guardian
checks size, hash and file binding; a truncated or malformed control frame follows
normal cleanup and full-reservation settlement. Four added tests cover a result
larger than 64 KiB, actual packet truncation, changed contents and invalid sizes.
These tests are prepared, not run. Earlier supervisor sources and admission
receipts remain exact and do not admit the repaired source.

The prepared historical reader follows each separate source bridge while checking
every frozen predecessor hash. A generator requires committed predecessor bytes
to match their historical receipt and rejects edits to historical Rust bodies.
The new bridge and all repaired-source resource acceptance remain unrun.

Proposed transfers use existing funds; no cumulative increase is requested:

| CPU stage | Current cap | Charged | Proposed cap | Remaining after transfer |
| --- | ---: | ---: | ---: | ---: |
| Implementation | 2000 | 1449.059638324 | 1600 | 150.940361676 |
| Independent proofs | 2600 | 1558.675434088 | 1600 | 41.324565912 |
| Native acceptance | 2200 | 2200 | 3800 | 1600 |
| Device workers/verification | 8400 | 0 | 7800 | 7800 |
| Reporting | 400 | 400 | 800 | 400 |
| Termination margin | 400 | 0 | 400 | 400 |
| Total | 16000 | 5607.735072412 | 16000 | 10392.264927588 |

This transfers 1000 proof and 600 worker seconds to native acceptance, and 400
implementation seconds to reporting. The 7800 worker seconds retain 7224 for
four-times-wall accounting of the entire 1806-second GPU package and 576 for
unleased verification/coordination. Each phase still requires a prospective
reservation; an insufficient remaining reservation stops the study.

On approval: archive the exact accepted ADR before its resource-table amendment;
carry every charge into a separate recovery journal; admit the repaired supervisor
with all 26 resource tests, without rerunning the bootstrap; generate and check
the registration bridge; run one new full native gate; then freeze and follow
the existing device acceptance, profile/forecast and conditional timing gates.
Implementation work must fit the remaining 150.940361676 seconds. A failed gate
stops, with no automatic retry or implicit transfer.

The four-CPU mask, one-phase ownership, 6-GiB sampled RSS stop, PID/start-time
cleanup, device UUID, GPU caps, numerical contracts and latency criteria stay
unchanged. Work stays inside the shared container. No host/cluster/container
configuration changes or signals to unrelated processes are authorized. GPUP-8
remains incomplete; GPUP-9 remains gated.
