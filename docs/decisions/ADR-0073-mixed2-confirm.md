# ADR-0073: Correct supervision before independent confirmation

Status: accepted through the user's explicit request to complete confirmation.
Implementation: [SPEC-0040](../specifications/SPEC-0040-mixed2-confirm.md).

The two older incomplete cohorts remain exact. Repeating missing historical cells
would not repair their frozen coverage. Use a new allocation and independent
cohort after demonstrating a supervision correction with fault injection and
source-bound CPU/device admission. Distinguish delayed guardian observation from
an actual 100 ms sampling/freshness violation; do not merely enlarge the timeout.
Keep numerical sources, original-model authority and all complete delivery costs.
A completed measurement does not imply that FP4 beats native or merits adoption.
