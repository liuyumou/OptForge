# SPEC-0046 amendment 33: bind the existing COPT Python environment

Retain `timing-copt-contracts-v1`, its sources, complete 180 CPU / zero GPU-second
charge and empty cleanup. The default Python lacks SciPy, so unittest import fails
before any contract or COPT solve runs. The installed COPT validation environment
at `artifacts/gpup-copt-adapter-env/venv/bin/python` already supplies the sparse-array
dependencies used by earlier accepted comparisons. Use that existing interpreter
for fresh timing/COPT contracts v2 and native COPT CPU admission v1; record its
NumPy/SciPy/Python versions and retain all subprocess output. No dependency is
installed, numerical result repeated, failed receipt replaced or limit changed.
