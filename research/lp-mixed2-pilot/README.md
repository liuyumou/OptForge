# MIXED2 prepared attribution and storage pilot

Isolated research implementation of [SPEC-0037](../../docs/specifications/SPEC-0037-mixed2-pilot.md).
The copied DELIVERY4 numerical state machine, original model arithmetic and
independent checker remain exact. `GPUP_MIXED2_PILOT_VARIANT=control|profile`
selects retained native CUDA kernels or bounded diagnostic instrumentation.
Both variants use the same batching, overlap and exact SHA implementation.

`cuda/pilot.cu` includes the retained FP4-ACCEL image source and adds an
instrumented native kernel, FP64/FP32-storage product kernels with the same
FP64 FMA/reduction tree, a conservative upward error guard and a timer probe.
The product microprobe is not integrated into a solver. No default changes.

CPU validation: `bash tools/check_mixed2_pilot_cpu.sh`. CUDA compilation uses
SM120a, `-O3 -lineinfo -fmad=false -ftz=false`; explicit product FMA intrinsics
remain fused while the retained native arithmetic stays separate multiply/add.
The new image requires its own four-sanitizer admission; earlier sanitizer
receipts are not reused. Device execution requires the pinned shared lease.

Source-bound launchers, failures and complete charges are retained under
`artifacts/gpup-mixed2-pilot-v1`. Its allocation closes at delivery; rerunning a
scientific cell or reusing its identities is forbidden. Portable CPU replay:
`python3 -B tools/lp_mixed2_pilot_analysis.py verify`.

[Report and limitations](../../docs/benchmarks/lp-mixed2-pilot.md).
