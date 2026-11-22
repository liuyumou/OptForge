# SPEC-0046 amendment 76: compact-source readmission and untouched tail

Source compaction passes with every archived member independently hashed before
loose removal. Direct old-large-data deletion also passes, retaining all 1609
chunks needed by the four untouched billion inputs. Preserve both cleanup receipts,
the original failed wide cell and all prior charges. The old raw-data replay limit
is intentional and authorized by the user, as specified in amendment 75.

Future reservations now share immutable source objects instead of copying every
source file. Each reservation keeps its own manifest and exact original/retained
size and SHA-256 references. Atomic creation and byte comparison reject corrupted
or conflicting objects. Three tests cover exact reuse, changed versions and
corruption rejection. Add the helper to exact resource-source gate bindings.

Operational CPU v29 and GPU v23 prospectively admit the changed budget/retention
sources. Append new operational plans for all four retained false-cleanup
dispositions, preserving every previous plan. The source-store format does not
change numerical Rust/CUDA, the native inventory, complete file traversal,
0.9-second counter timeout, one-second heartbeat guard, sampling advisories,
original certificate arithmetic, allocation totals or phase caps.

A fresh untouched-tail-v2 plan replaces only the uncompleted bookkeeping plan;
its original v1 source and partial cleanup/readmission records remain. The wide
cell is never repeated. After fresh CPU acceptance, a complete new idle window
and GPU acceptance, record its missing endpoint and run only tall, coupled_blocks,
ill_scaled and degenerate under their original frozen requests. Retain the
completed 64 M cohort and irregular solve/audits unchanged. Remove remaining large
objects only after all dependent audits finish, using a fresh protected-set plan.
