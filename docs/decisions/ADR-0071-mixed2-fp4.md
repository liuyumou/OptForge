# ADR-0071: FP4 tensor increments with FP64 authority

Status: accepted through the user's implementation and GPU-study authorization,
2026-11-13. Implementation: [SPEC-0038](../specifications/SPEC-0038-mixed2-fp4.md).

The FP32-storage pilot found no useful product win and a costly dense conservative
guard. Actual FP4 tensor arithmetic has a more plausible larger-dense opportunity.
Retain FP64 persistent state and original-A references, and move guard work to
precomputed matrix summaries plus small vector summaries. Original-model progress,
transactional recovery and independent final certificates remain mandatory.
Measure larger 1024/2048 dense models and complete prepared costs against a strong
matched native control. Optimize under versioned development before fresh frozen
confirmation. No universal performance promise, public preset, historical regrade,
or assumption that component acceleration implies complete-solver acceleration.
