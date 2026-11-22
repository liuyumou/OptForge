# SPEC-0046 amendment 53: retain CPU admission failure; correct interpreter

Operational CPU v22 passes 75 supervisor tests but fails three billion harness
imports because the default Python lacks SciPy. Preserve its full 720 CPU-second
charge, source snapshot, raw output and empty cleanup. No GPU work starts.
Fresh operational CPU v23 uses the already installed COPT-adapter Python, which
contains SciPy and NumPy. GPU v19 remains unattempted and requires passed v23 plus
the unchanged fresh idle window. Additive cleanup plans bind these same gates.
No resource cap, arithmetic, certificate or scientific-cell criterion changes.
