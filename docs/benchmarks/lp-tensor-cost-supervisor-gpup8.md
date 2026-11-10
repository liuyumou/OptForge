# GPUP-8 in-container supervisor: first bootstrap refusal

Status: bootstrap refused, 2026-10-23; GPUP-8 remains incomplete.

The user explicitly accepts revised [ADR-0044](../decisions/ADR-0044-tensor-cost-continuation.md),
14300 additional CPU seconds and reallocation of 1700. The approved prospective
allocation is 16000 CPU seconds under a 35900-second cumulative ceiling. The
existing numerical, device, study and latency completion gates remain unchanged.
No host access, namespace entry, cluster mutation or cgroup remount is performed.

## Implementation and first attempt

The new `tools/lp_cpu_admission.py` implements a project-wide admission lock,
durable stage reservations, inherited four-CPU affinity, a ready/release launch
handshake, process/thread discovery, a subreaper coordinator and independent
guardian, sampled RSS and conservative four-times-wall CPU charging. Its current
source is an implementation awaiting real acceptance, not an admitted controller.
The independent `tools/lp_cpu_bootstrap.py` contains entry, nested-session orphan,
coordinator-death, stale-journal and competing-lock witnesses.

The first outer supervisor attempt writes its reservation and forks the
coordinator, then fails because this Python 3.11.14 build does not expose
`os.pidfd_open`. The coordinator also reaches that missing API before its launch
function. **No workload command is released**; the independent bootstrap
witnesses, numerical preparation, compiler/native gate and all device work remain
unrun. No CPU resource-compliance pass follows from the attempted implementation.

The [refusal receipt](data/tensor-cost/supervisor-bootstrap-refusal.json) binds the
captured exception and frozen failed source. Preserve
`artifacts/gpup-tensor-cost-v1/bootstrap-failed-source`, including the original
unsettled journal, and `bootstrap-launch.stderr`. The recorded guardian exited;
inspection found no remaining supervisor/bootstrap process. Both failing branches
precede workload launch. The recovered journal settles the full 100-CPU-second
bootstrap reservation and remains failed, so another launch cannot silently begin.

## Portability repair and its limits

Current source adds a portable pidfd wrapper using the normal Linux syscall on
the supported x86_64/aarch64 ABIs when Python's optional wrapper is absent. The
container kernel/seccomp policy still applies; a denial is propagated. Unknown
architectures refuse. A capability check now occurs before creating children,
and failure acquiring a child pidfd triggers descendant cleanup while preserving
the active reservation for explicit failure settlement.

Four mocked source-only regressions pass: use the Python wrapper when available,
fall back when the binding is absent, refuse an unsupported ABI and propagate a
kernel-policy denial. They create no workload and invoke no real pidfd syscall.
They do not establish runtime capability, real guardian cleanup, sampling or
resource admission. The repaired source does not replace the failed source.
No full pinned-native or real supervisor acceptance pass is claimed.

ADR-0044 requires that bootstrap failure retain a refusal and states that
“there is no automatic retry.” One corrected bootstrap using 100 CPU seconds
from the existing implementation stage is therefore pending explicit user
authorization. The necessary source repair is concrete; no new budget, GPU
reservation or host access is requested. Until then, the failed journal blocks
resumption. A second attempt must retain the first evidence and use separate
sources, receipts and explicit authorization rather than clearing the refusal.

## Accounting and preservation

Charge 100 CPU seconds for the incomplete bootstrap observation. A separate
[refusal-delivery reservation](data/tensor-cost/supervisor-refusal-delivery-reservation.json)
reserves and conservatively charges 100 CPU seconds from reporting for recovery,
source-only regressions, static checks and this report. Complete admitted aggregate
accounting is unavailable; neither charge claims otherwise.

Conservative cumulative CPU accounting becomes **20099.822845162 / 35900
seconds**. Remaining stage allocations are implementation 1900, proofs/admission
2600, native acceptance 2200, worker/verification 8400, reporting 300 and margin
400, totaling 15800 CPU seconds; overall headroom is 15800.177154838. No historical
charge is reclaimed and no implicit stage transfer occurs.

GPU charge and reservations for this implementation are **zero**. Task/campaign
GPU consumption remains 825.114032275 / 22184.699888064 seconds. The ledger remains
17362 events, SHA-256
`e1766490f8de2affa14f4f950afed18be7f69531c3c28eedfd74539fcc0d9db5`, preserving
both earlier prefixes. All measured sources, images, workers, reports and old
receipts remain exact. Neither a supported preset nor GPUP-9 progression follows.
Full acceptance and local commit remain gated.
