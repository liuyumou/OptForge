# SPEC-0046 amendment 78: COPT startup investigation

The user asks to investigate COPT's missing billion-scale solutions and obtain a
fair comparison on the same original models with strict 1e-9 external checks.
The completed cohorts and every failed attempt remain immutable. New diagnostics
use distinct configurations and identities; no completed driver is rerun.

Retained billion logs enter COPT_SolveLp after importing the model, then show no
GPU PDLP startup or iteration messages. Each attempt's sampled owned GPU peak is
only 0.537109375 GiB. Smaller retained runs show substantial time before iteration
zero, including time-limit endpoints at zero iterations. This identifies startup
as a target, not a proven internal cause. The former adapter saved all phase costs
only after teardown, losing them on interruption.

Add a separate adapter reusing the admitted input/import/dual-mapping helpers.
Flush a single small phase journal at every stage, including entry/return of the
opaque vendor call and teardown. A deadline thread calls COPT_Interrupt only on
its own live problem and joins before the problem is freed. The outer directly
owned-child cutoff and all physical/resource guards remain. Retain missing and
late endpoints; late results cannot win an equal-budget comparison.

Prospectively compare four configurations: Presolve=0 with otherwise automatic
scaling/dualization; additionally Scaling=0; additionally Dualize=0; and both off.
Keep MatrixTol=0, FeasTol=DualTol=1e-9, PDLPTol=1e-12, four threads, GPU PDLP and
no crossover. These controls are documented in the installed header and the
[official parameters](https://guide.coap.online/copt/en-doc/parameter.html).
The [C API](https://guide.coap.online/copt/en-doc/capiref.html#copt-interrupt)
documents interruption of the current problem. Test deadline ownership/races
and exact min/max imports before performance diagnostics.

The initial investigation fits the current phase caps: 120 seconds CPU-only
admission contracts; 300 seconds GPU small admission; 420 seconds CPU-only idle
observation; 300 seconds CPU-only regeneration of the three 64 M inputs; twelve
150-second GPU diagnostic cells and twelve 90-second independent audits; and
240 seconds CPU-only reporting. The shared strict checker and original images
are unchanged. A fresh sustained idle observation precedes GPU work. Run under
the existing supervisor, 128 GiB host / 80 GiB GPU / 400 GiB storage limits, fixed
headroom, ownership checks and one-second cadence. Do not change resource sources.

Regenerate only required deleted inputs with the original generator/seed and
require byte-identical model manifests and chunk hashes before use. Construction
witnesses never enter solves. Keep small results, logs and failures; delete new
large arrays after their dependent audits. Freeze the complete further capacity
and fair-comparison reservation only after these diagnostics identify a viable
configuration. Current remaining time cannot cover an unrestricted twelve-cell
billion comparison; any necessary allocation extension needs explicit approval.
