# SPEC-0046 amendment 70: retained formatting failure and fresh quality build

Operational CPU v28 and GPU v22 pass, including a fresh six-minute uninterrupted
idle observation at the 0.750 GiB baseline. GPU-control-quality-v1 fails its first
formatting check before compilation. Preserve its sources, diagnostics, empty
cleanup and full 2400 CPU / zero GPU-second charge. No scientific cell has run.

Apply cargo fmt and prospectively reserve fresh quality-v2 for 600 seconds, one
build worker and the same complete isolated tests, Clippy, release and CUDA build.
The native phase has 5235.597137432 CPU seconds remaining before this reservation;
2400 fits the unchanged 26000 phase cap. All total caps, approvals, original
certificates, operational sources and physical guards remain unchanged. No failed
reservation or scientific cell is repeated. Candidate sealing must bind quality-v2.
