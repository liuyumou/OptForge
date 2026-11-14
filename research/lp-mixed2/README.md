# MIXED2 CPU reference

Isolated CPU contract for FP32 matrix storage and FP64 state/arithmetic. This is
not a GPU solver or certificate authority. See ../../docs/specifications/SPEC-0036-mixed2.md.

`bash tools/check_mixed2_cpu.sh` checks the package and independent rational oracle.
`python3 tools/lp_mixed2_cost.py --verify` reproduces the committed cost admission.
No toolkit or device is required. Original model/checker/defaults are unchanged.
