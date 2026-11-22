# SPEC-0046 amendment 67: proposed assessment/control continuation allocation

The user requests GPU assessment/control optimization with unchanged strict 1e-9
certificates and total-time measurements at one billion original matrix nonzeros.
This is a prospective proposal; it does not change the approved caps or guards.
The previous settled checkpoint is 280670.141791928 CPU / 31576.271121081 GPU
seconds, with no active reservation. Every old failure and charge remains.

Proposed total ceilings are 370000 CPU / 44000 GPU seconds (increases of 50000
CPU / 9000 GPU). Proposed exact CPU phase caps are implementation 10000, native
26000, admission 58000, development 162000, reporting 113000 and cleanup 1000.
Proposed GPU phase caps are admission 10000 and development 34000.

The prospective full reservation is 75000 CPU / 9220 GPU seconds:

| Phase | CPU seconds | GPU seconds | Scope |
| --- | ---: | ---: | --- |
| Implementation | 1600 | 0 | Protocol, capacity and source/evidence tools |
| Native | 3200 | 0 | Isolated Rust/CUDA build and numerical CPU acceptance |
| Admission | 10080 | 1680 | Fresh operational CPU/idle/GPU gates; bitwise diagnostics; exact continuations; all four complete sanitizers |
| Development | 30160 | 7540 | Twelve rotated paired 64 M cells (120 s each), then six new billion cells with the retained 6100-second aggregate process reservation |
| Reporting | 29560 | 0 | All independent final/intermediate audits, phase tables, source/cleanup/documentation verification |
| Cleanup | 400 | 0 | Final administration and owned-process evidence |

Admission GPU reservations are 120 s operational, 240 s diagnostic/continuation,
240 s memcheck, 600 s racecheck, 240 s initcheck and 240 s synccheck. Their 6720
CPU seconds plus 720 CPU gate, 480 contracts, 240 sealing and 1920 idle-observation
CPU seconds total 10080. Reporting reserves 5760 CPU for small audits, 21800 for
billion audits and 2000 for completion. Full prospective CPU usage is therefore
355670.141791928 and GPU usage 40796.271121081, below the proposed totals and
within every proposed phase cap. Unused margin is not permission to exceed caps.

The existing GPU remainder is only 3423.728878919 seconds, which cannot reserve
this 9220-second plan. The exact-cap approval chain in lp_billion_readmission.py
requires explicit authorization before applying the proposed extension. Work
that fits current approved phases may continue while the question is pending.

Retain four CPU slots, 128 GiB sampled aggregate host RSS, 80 GiB owned GPU,
400 GiB owned storage, physical headroom, one-second supervision, all 100 ms
advisories, the pinned idle-only Pro6000 lease and container-only execution.
No host escape, reset, other-job signals, owner inference or shared-memory clearing.
Keep control100/certificate500, the 1000-update ceiling, 600-second requested
solver allowance, strict original-model 1e-9 criteria and independent CPU audits.
Compare all six families; retain regressions, deadlines and unsupported capacity.
Never retry an attempted scientific cell or failed reservation identity. Public
defaults remain unchanged; commit locally only. The earlier general allocation
remains separate and unchanged.
