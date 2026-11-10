# GPUP-8 cost continuation: CPU resource admission refusal

Status: CPU resource admission refused, 2026-10-23; GPUP-8 remains incomplete.
Owner: numerical backend and experiment tooling.
Last reviewed commit: bootstrap (parent 345df9c).

The user explicitly accepted [ADR-0044](../decisions/ADR-0044-tensor-cost-continuation.md)
and directed CPU resource admission first. The read-only admission preflight
cannot obtain the required delegated task enclosure in the current environment.
The accepted decision requires: “If delegation is unavailable, retain a CPU
admission refusal and stop before preparation/device reservations.” This report
records that disposition. The optimization package and new GPU study have not
started; no latency-gain claim or GPUP-9 progression follows.

## Admission evidence

The separate [preflight receipt](data/tensor-cost/cpu-admission.json) binds the
accepted ADR and preflight source by SHA-256. It retains these observations:

- The sole visible cgroup v2 mount is `/sys/fs/cgroup`, mounted read-only.
  There are no visible delegated child groups. Membership is `0::/`, a shared
  namespace root containing unrelated processes.
- CPU quota is `9000000 100000` (90 cores), and the effective cpuset is `0-95`.
  Neither enforces the task's four-core constraint.
- The enclosing memory limit and swap limit are each 214748364800 bytes
  (200 GiB), exceeding the required 8-GiB memory/no-swap limits.
- Membership, limits, freeze and kill controls are not writable. Aggregate
  counters are readable but belong to the shared root, not this continuation.
  They cannot establish task resource usage or certify the historical overlap.
- System and user systemd manager probes fail. The system manager reports that
  PID 1 is not systemd; the user bus is unavailable. No systemd/DBus manager or
  host/container management socket is exposed in the checked locations.

An initial interactive discovery read attempted to read write-only `cgroup.kill`
and received EINVAL. It launched no workload. The retained preflight handles
write-only controls by checking existence and access only; a regression verifies
that it never reads the kill control. The corrected capability probe is not a
study retry: no numerical source cohort, study cell or GPU identity was attempted.

The preflight acquires a project-wide CPU admission lock for its observation.
That lock does not implement the complete coordinator or create hard resource
containment. Even a synthetic snapshot with suitable controls only produces
`capability_ready_not_admitted`; it never authorizes preparation or device work.
The full coordinator, failure cleanup and aggregate resource tests remain
unimplemented because their delegated-host prerequisite is absent. No per-tree
sampler, affinity-only limit or permissive root quota substitutes for admission.

## Bounded work and accounting

The [CPU reservation receipt](data/tensor-cost/cpu-reservations.json) reserves
250 seconds for the admission/bootstrap stage and preserves the later mandatory
stage reservations within ADR-0044's 2050-second cap. Capability discovery and
simulated refusal checks necessarily precede an admitted task enclosure; they
do not claim enforced aggregate resource compliance. Because complete task
aggregate accounting is unavailable, charge the full 250-second admission
reservation and the full 100-second reporting/delivery reservation, **350 CPU
seconds total**. Do not reclaim any prior conservative reserve.

Conservative cumulative GPUP-8 CPU accounting is therefore
**19884.822845162 / 21600 seconds**, leaving 1715.177154838 seconds under the
original ceiling. Of ADR-0044's accepted 2050-second cap, 1700 seconds are
unspent. Those numbers do not authorize a retry or another experiment.

**GPU consumption and reservations for ADR-0044 are both zero.** GPUP-8 GPU
consumption remains 825.114032275 / 3000 seconds; cumulative campaign consumption
remains 22184.699888064 / 25202.574545061. No GPU lease, preparation, compiler,
numeric proof/admission cohort, device acceptance or timing/profile cell runs.
Every historical source, image, worker, endpoint and report is retained.

The GPU ledger remains 17362 events with SHA-256
`e1766490f8de2affa14f4f950afed18be7f69531c3c28eedfd74539fcc0d9db5`.
The exact 17200-event and 17132-event prefixes remain unchanged. The historical
ADR-0043 admission/build overlap remains **not certified**.

## Verification and next prerequisite

Seven CPU-only bootstrap counterexamples pass: read-only mounts and shared roots
refuse despite writable-looking file metadata; capability availability never
grants workload admission; unlimited/malformed/oversized limits refuse; missing
aggregate counters and memory events refuse; membership/freeze/kill permissions
are required; write-only controls are not read; and old receipts cannot be
overwritten. These use temporary simulated controls and launch no admitted work.
They are not substitutes for the coordinator's required real containment tests.

Documentation/link validation and whitespace checks cover the refusal record.
The full pinned-native gate cannot start after failed resource admission under
ADR-0044; no new full-gate pass is claimed, and the new changes remain uncommitted.
The earlier 366-test/144-page diagnosis acceptance remains historical and exact.
The separate [delivery receipt](data/tensor-cost/acceptance.json) distinguishes
bootstrap validation from unrun native, numerical and device gates.

Further execution requires a host-provided delegated cgroup v2 task subtree
with writable membership/limits/freeze/kill controls, at most four effective
CPUs and four cores of quota, memory limited to 8 GiB, swap disabled, and complete
aggregate CPU/memory peak/event telemetry. The host must make that subtree
available to this executor before a reviewed continuation can pass admission.
The current executor cannot provision it through an exposed manager. No further
approval of ADR-0044 itself is needed; its execution prerequisite remains unmet.
