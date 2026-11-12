# ADR-0068: measure and reduce cold lifecycle costs

Status: accepted for the user's DELIVERY4 implementation request (2026-11-12)

[DELIVERY3 diagnosis](../benchmarks/lp-delivery3-diagnosis.md) bounds cold arithmetic-
only gain at about 1.0094x and identifies serial host preparation plus a large
unclassified outer remainder. Implement [SPEC-0035](../specifications/SPEC-0035-delivery4.md)
in a separate research package, measuring CPU startup first and device lifecycle
only after exact CPU admission. Preserve original input admission, numerical
order, independent checking and complete EOF/durability/cleanup costs.

Select one evidence-supported startup/lifecycle optimization and a new bounded
pilot before freezing a cold-only confirmation against the strong DELIVERY3
overlap control. Keep prospective scoped 1.10x benefit and material-regression
guards; all old results and allocations remain exact. Prepared and mixed-precision
work stay separate. Report negative and inconclusive results as well as gains.
The new independent resource ceiling is specified in SPEC-0035; no public preset,
push, publication or GPUP-9 release follows.
