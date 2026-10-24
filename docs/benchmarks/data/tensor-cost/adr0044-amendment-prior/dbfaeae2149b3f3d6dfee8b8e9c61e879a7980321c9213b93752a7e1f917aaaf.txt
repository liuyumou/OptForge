# GPUP-8 continuation under the Kubernetes container constraint

Status: documentation-only revision, 2026-10-23; execution remains resource-blocked.
Scope: the user's confirmed Kubernetes executor and prohibition on escaping this
container. This revision does not amend accepted numerical or resource contracts.

## Feasibility and revised next step

The user clarified that the executor runs under Kubernetes and that escaping
this container is prohibited. Withdraw the host provisioning route from the
current task. Do not enter host namespaces, invoke privileged helpers, remount
the cgroup hierarchy, request a privileged replacement, use host sockets or
mutate the cluster through its API. No such operation was performed for this
revision. Ordinary repository reads and edits stay inside the existing container.

The retained [admission receipt](../benchmarks/data/tensor-cost/cpu-admission.json)
shows a read-only cgroup v2 mount, no delegated child and shared 90-core/200-GiB
limits. Those controls cannot enforce a private four-CPU/8-GiB task enclosure.
The unavailable host interface is an environmental prerequisite, not a numerical
implementation defect that additional GPU time can repair.

[ADR-0044](../decisions/ADR-0044-tensor-cost-continuation.md) requires a delegated
enclosure, complete aggregate accounting and verified cleanup before preparation.
Its required disposition is to retain the refusal and stop. CPU affinity, thread
environment variables, a lock, per-process rlimits and sampled process trees can
support cooperative limits, but do not establish the accepted aggregate memory,
descendant containment, accounting and orphan-cleanup guarantees. This plan does
not silently substitute them or certify historical resource compliance.

The revised sequence is:

1. Close this bounded documentation-only revision and retain the current refusal.
   Do not rerun the preflight, start a new implementation cohort or reserve a GPU.
2. Keep the compact-preparation, certified-norm and equivalent-audit package as
   unexecuted design work. Its arithmetic, certification and latency criteria
   remain unchanged. GPUP-8 remains incomplete; GPUP-9 does not start.
3. Any future in-container execution proposal must first specify a demonstrably
   implementable resource contract and an explicit CPU stage allocation. There
   is currently no demonstrated replacement that meets ADR-0044's guarantees in
   this container. A cooperative-monitor proposal would explicitly weaken that
   contract and needs a separate accepted decision; it cannot be called an
   equivalent implementation. No such weakening is accepted by this revision.
4. Only after an accepted resource amendment, its implementation and real failure
   tests could numerical preparation and the unchanged device gates become ready.
   No new study identity, retry or automatic transfer follows from unused time.

## Remaining resources and the GPU offer

The preserved [bootstrap settlement](../benchmarks/data/tensor-cost/cpu-settlement.json)
charges the entire 250-CPU-second admission stage and 100-second reporting stage.
It leaves 1700 CPU seconds in ADR-0044: 550 proofs/admission, 550 native acceptance,
550 worker CPU/verification and 50 supervisor margin. Admission and reporting
each have zero remaining stage allocation. The ADR explicitly forbids implicit
borrowing. Its existing approval remains valid, but provisioning alone would not
fund another admission stage; the earlier host-prerequisite handoff was incomplete
on this point. Old conservative charges are not reclaimed.

This separate, user-requested documentation revision conservatively charges 10
CPU seconds from the previously unallocated 15.177154838 seconds under the original
21600-second ceiling. It performs repository reads/edits and static preservation
checks only, with no admitted-work or aggregate-resource certification claim.
Revised conservative CPU accounting is **19894.822845162 / 21600 seconds**:
1705.177154838 seconds remain overall, including the unchanged 1700 seconds in
ADR-0044 and 5.177154838 unallocated seconds. This planning charge does not grant
another execution phase. Its separate receipt must not replace the old settlement.

The user offered another **3600 GPU seconds**. Keep that offer unreserved: GPU
capacity is not the current blocker, and neither a phase allocation nor amended
cumulative ceilings are established here. In particular, simply adding 3600 to
the existing 25202.574545061 campaign ceiling would produce 28802.574545061 and
exceed the independent 28800-second ceiling. A future allocation must reconcile
both cumulative and phase limits rather than silently raising either.

Current GPUP-8 GPU charge remains **825.114032275 / 3000 seconds**, leaving
2174.885967725. ADR-0044's existing maximum of 1806 GPU seconds already fits:
990 screening, 320 ablations and 496 repeatability, each within its remaining
phase allocation. No additional GPU allowance is needed for that frozen package.
Campaign consumption remains **22184.699888064 / 25202.574545061 seconds**.

## Evidence boundary

Preserve the accepted ADR and all measured sources, images, workers, reports and
receipts. This plan is a later constraint record, not a rewrite of the measured
refusal or its acceptance. The GPU ledger remains 17362 events, SHA-256
`e1766490f8de2affa14f4f950afed18be7f69531c3c28eedfd74539fcc0d9db5`, including its
exact 17200/17132-event prefixes. No compiler, native gate, numerical cohort,
device test, profile or timing runs in this revision. Static preservation checks
do not imply a full acceptance pass, and local commit remains gated.
