# SPEC-0046 amendment 61: expanded exponent fixtures and final source sealing

Operational GPU v20 passes sixty exact continuations. Native quality-v6 passes
all tests, formatting, Clippy, release and CUDA compilation, charging 317.864206368
CPU seconds with empty cleanup. Its standalone packing fixture was expanded while
that build was active, so its original source snapshot no longer binds that one
file. Retain v6 and its exact charge, but exclude it from candidate sealing. No
solver or packing-kernel source changed during that build and no GPU candidate ran.

The expanded fixture adds eight whole-batch comparisons around powers of two and
six, including subnormal values, the -48 exponent clamp and the coefficient-domain
boundary, across all component counts and both fragment layouts. Admission now
requires 81 complete bitwise packing comparisons and six malformed-input rejections.
Fresh native quality-v7 freezes these exact sources. The build harness additionally
checks every numerical source against its retained snapshot before declaring
success. No source is edited during that fresh build. All resource caps, strict
certificates, unchanged numerical CUDA modules and scientific scope remain intact.
