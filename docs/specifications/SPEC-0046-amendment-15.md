# SPEC-0046 amendment 15: preserve the prospective cohort identity

Before any image-v3 scientific freeze, source review finds that the loop binding
failed admission receipts reuses the function's `identity` parameter. That would
give future cell identifiers an interrupted admission's name instead of their
cohort's name. No image-v3 scientific cohort has been frozen or executed.

Rename only that loop variable and add a regression assertion covering the exact
cohort-qualified cell identifiers. Fresh `preparation-harness-cpu-v5` acceptance
must pass before the continuation or any image-v3 freeze. Every failed receipt
remains bound. This changes no numerical code, result, attempted scientific cell,
resource ceiling, strict certificate or supervision/idle gate.
