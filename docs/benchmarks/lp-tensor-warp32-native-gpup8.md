# GPUP-8 warp32 correction: CPU acceptance and native stop

The corrected compiler launch passes. The isolated image uses at most 88
registers and zero spills, preserves the required Tensor instructions and
rounding, and leaves historical numerical bodies/images unchanged.
Independent actual-host/kernel-body comparison passes 592 bit/refusal cases.
The complete eight-model CPU cohort retains 48 cells and independently verifies
24 endpoints. All twelve required dense-model configurations complete useful
400-update trajectories. Ten new launcher/harness regressions pass.

The full native gate stops at a redundant i32 cast in the new device-test
fixture. Its full 1200-CPU-second reservation remains charged and cleanup is
verified empty. The cast is removed in a separate one-line correction, with
the old source archived. Numerical sources, compiled image and CPU evidence
are unchanged. No full native pass or device acceptance is claimed.

At the native stop CPU consumption is 31950.822722026 / 35900 seconds; later
CPU-only refusal delivery/accounting is charged separately. No new GPU work
ran. GPUP-8 remains at 863.208464546 / 3000 GPU seconds, campaign consumption
at 22222.794320335 / 25202.574545061, and the exact 17366-event ledger prefix
remains preserved. GPUP-8 is incomplete; numerical and latency criteria remain
unchanged. No bootstrap rerun, host access or container configuration change.

The [bounded recovery proposal](../plans/lp-tensor-warp32-native-recovery.md)
requests 1200 native and 40 reporting CPU seconds from unspent workers, keeping
the 6100 allocation, 35900 ceiling and 790-GPU-second cap. It authorizes no work
until accepted. The tighter worker envelope can refuse study admission before
timings; no subset result can complete GPUP-8. No local numerical commit,
GPUP-9 work, publication or merge follows the failed gate.


Final CPU-only delivery acceptance passes formatting, 155 documentation pages,
repository CPU smoke and diff hygiene; no full native or numerical/device gate
is inferred. Final CPU accounting is 31980.332668818 / 35900, with
12.490053208 reporting CPU seconds unspent before any proposed transfer.
The separate native-final-cpu-accounting-v1.json receipt retains every charge.
No new GPU work or resource bootstrap ran; all project cleanup is verified empty.
