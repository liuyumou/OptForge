# SPEC-0046 amendment 92: separate storage latency from safety sampling

Status: preflight revision authorized; asynchronous runtime proposal pending
explicit approval, 2026-11-23. Owner: resource supervision.
Last reviewed commit: 8035ee7. The user asks whether the time limit is reasonable
and explicitly requests revision if it is not. This supersedes amendment 91's
unchanged preflight inventory timeout requirement. Automatic approval review
rejected applying the broader asynchronous runtime policy without explicit
approval of its longer storage-observation age. Requirements 3-5 below are a
concrete proposal, not active behavior.

The old 0.9-second full-tree storage scan executes synchronously inside a
one-second process/GPU safety sample. Repeated preflight refusals and a measured
0.912 s wall / 0.066 s child CPU interval show that its margin does not accommodate
the observed filesystem/scheduling waits. Increasing only that timeout would
still block safety sampling and is insufficient. A complete authorized scan then
took 22.649875027 s wall and 1.028264 s child CPU over 98,195 files / 8,281,396,955
bytes. This supports a 60-second preflight cap; the initial 10-second runtime
proposal was also too short and is superseded below.

1. Keep the legacy policy available for historical requests; never rewrite old
   results, failures, budgets, frozen drivers or admission records.
2. The new explicit `async-v1` storage policy MUST complete a full preflight
   inventory within 60 seconds before releasing a workload. It MUST verify the
   original native executable/source binding, exact byte ceiling, complete disk
   reservation and physical headroom. No timeout may supply an estimated count.
3. Proposed runtime policy: start an owned asynchronous full inventory after at
   least five seconds since the previous completion, with at most one scanner.
   A scan MUST finish within 60 seconds; the last valid completed scan MUST be
   at most 90 seconds old.
   Malformed output, an over-limit count, scan failure, timeout or stale data
   MUST fail closed. Storage detection latency changes explicitly; process/RAM/
   GPU safety observations MUST retain their one-second hard bounds and 100 ms
   advisories. Never wait for a storage traversal inside those observations.
4. Stop/reap the owned scanner when descendant cleanup begins, without starting
   replacement scans during cleanup. Continue process/RAM/GPU sampling. After
   supervised cleanup, the launcher MUST complete another full inventory within
   60 seconds before accepting settlement. Final storage failure retains the
   full failed reservation even if process supervision passed.
5. Reserve 75 seconds of the existing outer job allowance for final storage
   verification/settlement, reducing the supervisor's inner allowance accordingly.
   New-policy jobs MUST reserve at least 120 seconds. Include final inventory time
   in settlement charging; do not increase any CPU/GPU/phase or memory/storage cap.
6. Retain scan timestamps, original bytes and validation dispositions. Exact
   original-model certification, public defaults and numerical settings remain.
7. Retain the prior resource source versions, add source-bound CPU36/GPU28
   readmission plans and require fresh idle proof before device work. CPU
   bootstrap/read-only reporting may run through the new policy to validate it.
8. Test slow successful scans without blocking safety observations, stalled and
   stale scans, malformed/nonzero exits, over-limit counts, ownership cleanup,
   initial/final failures and legacy policy compatibility. Run existing supervisor
   and billion harness acceptance before device release.

The 60-second scan / 90-second freshness limits are bounded engineering
allowances, not a measured
percentile guarantee. Record complete observed scan timings during admission and
report whether these allowances fit. A failing new scan still blocks execution.
The scope remains within amendment 91's existing phase envelope; no new scientific
attempt, GPU allowance or exception for an overrun is created.

Current implementation changes only `preflight_disk_bytes()` and the launcher's
preflight call. `disk_bytes()` used by runtime supervision retains its original
0.9-second timeout. The one-second sampling path is untouched. Do not launch a
job expecting the preflight change alone to fix runtime storage stalls. The
asynchronous module/launcher/cleanup changes were rejected atomically and are
not present. Explicit approval of requirements 3-5 is required to continue that
part; numerical optimization authorization remains in effect.
