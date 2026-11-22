# SPEC-0046 amendment 22: indexed preparation without discarded residual arrays

The user requests further preparation-time reduction. Image-v5 introduces an
isolated proposal packer that appends canonical tiles in the same sorted order,
uses direct tile indices during orientation construction and reuses touched-column
scratch. It shares the original encoder and preserves all packed coefficient bits,
fragments, exponents, coverage and residual order. For zero eligible tiles it
retains complete original-transpose validation and then returns no packed operator
without building the residual copies that the caller would immediately discard.
Legacy packing APIs and public defaults remain unchanged.

CPU regressions compare the complete packed representation to the retained original
packer across component counts, layouts, rectangular tails and parallel thresholds.
They check that transpose corruption still refuses even when no tile qualifies.
New timing-only preparation partitions expose engine, operator, packing and control
initialization; their sum must equal the existing complete preparation interval.
Input time remains separately visible and included in complete process cost.

Require full isolated tests, format, Clippy, release/CUDA build, source-bound image
sealing, fresh operational CPU/GPU admission, exact preparation and continuation
comparisons, and all four complete sanitizer suites before science. Use the existing
phase caps and 240000 CPU / 30000 GPU totals; no transfer or physical-limit change.
Operational v11 follows a fresh five-minute idle window and binds these sources.
Preparation and solve CUDA, original-model certificates, control100/certificate500,
all historical failures and full charges remain unchanged. Stay container-only.

Run only fresh image-v5 cells against all six 64 M and both 256/512 M image-v4
capacity controls at their existing 100-update settings. Preserve every outcome
and regression, with independent final/intermediate checking and supervised paired
comparisons. Keep the conservative borrowed-storage capacity formula unchanged;
no new memory allowance reduction is inferred from eliminated transient work.
The eighteen billion-scale cells remain unfrozen pending complete physical and
solve/audit/storage admission. No attempted scientific cell is repeated.

Reporting correction: amendment 21 described paired analysis as expanding endpoint
arrays into Python values. The retained lp_billion_results.canonical already compares
content-addressed manifests, so that description was incorrect. Its extra resource
supervision and all actual receipts remain valid and unchanged. Distinguish that
bounded campaign comparator from the small-fixture admission unpacker.
