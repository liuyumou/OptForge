# Optional cuOpt environment

Status: cuOpt 26.10.0 installed and import-checked on 2026-11-10;
device and solver acceptance not run.
Owner: experiment tooling.
Reviewed project commit: `396bd0e2ea095f1d038dfa862bb31f29a61e0d68`.
Decision: [ADR-0047](../decisions/ADR-0047-certified-performance-roadmap.md).
Evidence: [installation receipt](../benchmarks/data/cuopt-setup-2026-11-10.json).

The optional environment is at
`artifacts/cuopt-26.10.0-cu13/venv` under the repository root. It contains the
Python LP bindings and cuOpt libraries. It occupies approximately 4.7 GiB,
including GPU dependencies. The project environment, system packages, drivers,
local COPT installation and historical experiment environments are unchanged.

The host has Python 3.11.14, Linux x86-64 and NVIDIA driver 580.105.08, with
Blackwell compute capability 12.0 devices. This meets the documented CUDA 13
driver minimum; package imports do not establish actual GPU compatibility.
The resolver selected CUDA 13.5 runtime packages, recorded in the lock. A later
admitted device smoke must verify the complete installed stack, including any
JIT/driver requirements. See NVIDIA's [system requirements](https://docs.nvidia.com/cuopt/user-guide/latest/system-requirements.html)
and [installation guide](https://docs.nvidia.com/cuopt/user-guide/latest/install.html).

## Use and reproduce the installation

From the repository root, use the isolated interpreter directly:

```bash
CUDA_VISIBLE_DEVICES='' artifacts/cuopt-26.10.0-cu13/venv/bin/python -m pip check
CUDA_VISIBLE_DEVICES='' artifacts/cuopt-26.10.0-cu13/venv/bin/python -c \
  'import cuopt; from cuopt import linear_programming; print(cuopt.__version__)'
```

Both checks passed: no broken requirements, and the `cuopt` and
`cuopt.linear_programming` imports succeeded at version 26.10.0. GPUs were hidden;
no model or solver was constructed. There is no performance or numerical result.

The initial installation used `cuopt-cu13==26.10.0`, binary wheels only, PyPI
and NVIDIA's package index, in a new virtual environment. Its full dependency
resolution is pinned with wheel hashes in
[cuopt-requirements-cu13.lock](../../tools/cuopt-requirements-cu13.lock).
To reproduce it in a **new** CPython 3.11 Linux x86-64 environment:

```bash
python3 -m venv artifacts/cuopt-reproduction/venv
CUDA_VISIBLE_DEVICES='' timeout 900 artifacts/cuopt-reproduction/venv/bin/python -m pip install \
  --only-binary=:all: --require-hashes \
  --index-url https://pypi.org/simple --extra-index-url https://pypi.nvidia.com \
  --timeout 20 --retries 2 \
  -r tools/cuopt-requirements-cu13.lock
```

The lock is specific to the resolved platform and Python version; it is not added
to the project's ordinary `tools/requirements.txt`. Installation logs, pip's
download report and `freeze.txt` remain under the ignored
`artifacts/cuopt-26.10.0-cu13` directory. The tracked receipt records their hashes,
package versions and wheel origins. Do not silently update an environment after
using it for a frozen experiment; create another identity for dependency changes.

## Next acceptance step

`GPUP-BASELINE-SPEC` must define the common-checker comparison contract and resource
package before solver measurements. The subsequent adapter must export actual
primal and dual information, preserve original-model mappings and record precision,
algorithm, presolve and crossover settings. GPU jobs must use the shared lease
and accepted resource controls in [GPU operations](gpu.md). Setup/import success
does not bypass those gates.

Local COPT 8.0.6 remains available under `/root/copt80`; its existing
[setup helper](../../tools/setup_copt.py) is unchanged. Gurobi is unavailable and
is not installed or required. The [current roadmap](../plans/gpu-lp-precision-roadmap.md#current-plan-2026-11-10)
keeps all three availability states explicit.
