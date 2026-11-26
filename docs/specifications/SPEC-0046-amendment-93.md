# SPEC-0046 amendment 93: activate approved asynchronous storage supervision

Status: explicitly approved, 2026-11-23. Owner: resource supervision.
Last reviewed commit: 8035ee7. The user answers the concrete amendment 92 proposal:
"I approve it. Go ahead." This authorizes requirements 3-5 of
[amendment 92](SPEC-0046-amendment-92.md), including the longer storage detection
latency. Its earlier approval-pending status remains historical.

Implement explicit `--storage-policy async-v1`: complete preflight within 60 s,
one asynchronous scanner after a five-second interval, 60 s scan deadline,
90 s maximum age of the last completed observation, owned scanner cleanup, and
mandatory final full inventory within 60 s. Reserve 75 s within the existing
outer job allowance for final inventory/settlement; minimum outer allowance is
120 s. Timeout/error/malformed/stale/over-limit results refuse, never pass from
cached counts. Preserve started/completed timestamps and final dispositions.

RAM/process/GPU observations retain their one-second hard limits and 100 ms
advisories. Legacy requests keep the synchronous runtime policy. No cap, ownership
rule, certificate criterion, failed charge or historical outcome changes.

CPU36 passed for the preflight-only source version. Use fresh CPU37 for the
asynchronous source version, followed by fresh sustained idle and still-unattempted
GPU28. Add source-bound readmission plans for historical cleanup dispositions;
preserve their original receipts and exact exception approval chain. Include the
new storage module among critical resource-source bindings. Numerical candidate
acceptance follows these operational gates; do not rerun scientific cells.

Acceptance must cover delayed successful scanners while sampling continues,
timeouts/stale/malformed/over-limit failures, owned-child termination and no
restart during cleanup, mandatory final verification, unchanged legacy behavior,
original supervisor tests and the complete billion harness. All jobs use the
remaining amendment 91 envelope and original phase caps; no new allowance.
