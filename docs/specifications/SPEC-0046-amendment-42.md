# SPEC-0046 amendment 42: retain COPT timeout admission

COPT full admission v1 passes 21 fixtures, then the GPU ill-scaled fixture
returns native status 8 (time limit), no solution, and actual GPU PDLP evidence.
The harness incorrectly requires an endpoint from every generated fixture.
Retain all raw outputs, the failed reservation's full 960 CPU / 240 GPU seconds,
and empty cleanup. This is an admission failure, not a scientific timing.

Fresh admission v2 permits an absent endpoint only for a documented native
non-optimal terminal outcome; every returned endpoint still receives the exact
original-model 1e-9 check. Geometry fixtures still require strict certification,
and infeasible/unbounded/deadline fixtures keep their separate assertions.
No solver parameter, tolerance, arithmetic or supervisor changes. The scientific
adapter now requires the fresh v2 receipt; its sole source change is that gate ID.
Retain the earlier source-bound v1 admission and failed source snapshot.

Before any capacity cell is attempted, set each 64 M reservation to 100 seconds
for its fixed 30-second solve plus input, endpoint transport and strict final
check. Retain 240/360 seconds at 256/512 M. Freeze each complete capacity stage
against the remaining unchanged allocation, preserving any refusal. No attempted
scientific capacity cell is repeated.
