#!/usr/bin/env bash
# Provision only the isolated ADR-0037 image. Ordinary Cargo builds never call nvcc.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 - <<'PYBUILD'
import hashlib,json,subprocess
from pathlib import Path
source=Path('cuda/lp_pdhg_refine/lp_pdhg_refine.cu')
out=Path('target/native/cuda');out.mkdir(parents=True,exist_ok=True)
command=['/usr/local/cuda/bin/nvcc','--cubin','-arch=sm_120','-O3','-lineinfo','-fmad=false','-ftz=false','-Xptxas=-v','-o',str(out/'lp_pdhg_refine.cubin'),str(source)]
result=subprocess.run(command,capture_output=True,text=True,timeout=300)
(out/'lp_pdhg_refine.compile.stdout').write_text(result.stdout)
(out/'lp_pdhg_refine.compile.stderr').write_text(result.stderr)
result.check_returncode()
if '0 bytes spill stores, 0 bytes spill loads' not in result.stderr:raise ValueError('refinement compiler spill gate')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
receipt=dict(command=command,source_sha256=sha(source),image_sha256=sha(out/'lp_pdhg_refine.cubin'),stdout_sha256=sha(out/'lp_pdhg_refine.compile.stdout'),stderr_sha256=sha(out/'lp_pdhg_refine.compile.stderr'),nvcc_version=subprocess.check_output(['/usr/local/cuda/bin/nvcc','--version'],text=True))
(out/'lp_pdhg_refine.build.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(result.stderr)
PYBUILD
