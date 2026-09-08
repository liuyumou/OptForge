# Known Failures and Limitations

No known implementation failure has been accepted as a waived gate.

## Source planning references

The preserved ai-native-optimizer-plan.md references optimizer-survey.md and
llm-or-survey.md from another session; neither is present. Reproduction:
inspect its Background links. Next diagnostic step: recover those source surveys
if research work needs them. The maintained documentation book excludes the two
original planning inputs from recursive link validation.

## External configuration

The origin remote is https://github.com/liuyumou/OptForge.git. Protected main,
labeled GPU runner provisioning, and artifact retention still require hosting
administration. Next step: configure these settings separately from Git syncing.

## Deferred hardware evidence

M0 queries inventory only. CUDA sanitizer, kernel equivalence, HiGHS differential,
and numerical correctness tests remain gated on M1-M5 implementation.
