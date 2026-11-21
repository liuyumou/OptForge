# SPEC-0046 amendment 43: COPT capacity interruption and proposed readmission

Status: recovery proposal; no authority to resume resource execution is supplied
by this document. The existing budget guard remains unchanged and closed.

The 64 M degenerate COPT GPU capacity cell exhausts its 100-second reservation
while the vendor is initializing GPU PDLP. The log has no returned endpoint or
iteration result. The receipt records 400.620150944 CPU / 100 GPU seconds,
overrun=true and cleanup_empty=false. Retain that receipt, all sources and logs;
exclude the timing and never repeat the attempted cell. Subsequent read-only
PID/start-time inspection finds every recorded owned process gone. A separate
cleanup verification is supplemental and does not rewrite the failed receipt.

The 100-second capacity reservation was too small for this vendor path; neither
its 30-second requested solver limit nor its soft memory limit is a hard process
bound. No performance or capacity success is inferred from the partial result.
Two prior coupled 64 M COPT cells finish, both at a time limit without an endpoint.
Their real GPU execution, peak memory and complete costs remain recorded.

Proposed recovery requires explicit user authorization for both the allocation
extension and this particular overrun readmission. Preserve the actual overrun
charge and every failed reservation. The proposal raises only cumulative time to
320000 CPU / 35000 GPU seconds; physical limits, four slots, container restriction,
strict certificates, one-second supervision, every 100 ms advisory and idle /
ownership guards remain unchanged. Proposed CPU phase caps are implementation
2000, native 14000, admission 45000, development 148000, reporting 110000 and cleanup
1000 seconds. Proposed GPU caps are admission 9000 and development 26000 seconds.

A source-bound exception, if authorized, must apply only to this exact settlement
hash and its verified dead PID/start-time identities. It must require fresh CPU
supervisor/resource tests, a fresh five-minute idle window and fresh operational
GPU readmission before allowing GPU scientific work. Every future overrun must
still close execution. Never generalize this disposition to other failures or
change the original supervisor/ownership implementation.

Preserve the 64 M capacity freeze and every attempted cell. Only the nine
never-started capacity cells may move to a separately frozen tail with 300-second
process reservations and the same 30-second vendor solver limit. The interrupted
degenerate GPU capacity result stays explicitly unsupported; do not invent a
successful capacity measurement. Complete the retained 256/512 M prospective
ladder before any supported COPT billion lane is admitted. Unsupported lanes must
remain visible in the full roster. Project billion lanes use admitted image-v9.

The reviewable full-roster time worksheet is
`/storage/ai-optimizer-billion-v1/full-reservation-proposal-v1.json`. It plans a
common 600-second solver wall, 100-update control, 500-update certification, and
at least 500 permitted updates, retaining every larger-ceiling rejection. Final
freeze remains contingent on observed capacity and whole solve/check/audit/storage
admission. No billion scientific cell has been attempted.
