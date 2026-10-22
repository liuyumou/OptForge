#!/usr/bin/env bash
# Explicit provisioning only; ordinary builds never invoke nvcc.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 - <<'PY'
import hashlib,json,re,subprocess
from pathlib import Path
s=Path('cuda/lp_pdhg_quant/lp_pdhg_quant.cu');d=Path('target/native/cuda');d.mkdir(parents=True,exist_ok=True)
cmd=['/usr/local/cuda/bin/nvcc','--cubin','-arch=sm_120','-O3','-lineinfo','-fmad=false','-ftz=false','-Xptxas=-v','-o',str(d/'lp_pdhg_quant.cubin'),str(s)]
r=subprocess.run(cmd,capture_output=True,text=True,timeout=300)
(d/'lp_pdhg_quant.compile.stdout').write_text(r.stdout);(d/'lp_pdhg_quant.compile.stderr').write_text(r.stderr);r.check_returncode()
registers=[int(n) for n in re.findall(r'Used (\d+) registers',r.stderr)]
if not registers or max(registers)>128 or '0 bytes spill stores, 0 bytes spill loads' not in r.stderr:raise ValueError('quant resource admission')
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(d/'lp_pdhg_quant.build.json').write_text(json.dumps(dict(command=cmd,source_sha256=h(s),image_sha256=h(d/'lp_pdhg_quant.cubin'),registers=registers,nvcc_version=subprocess.check_output(['/usr/local/cuda/bin/nvcc','--version'],text=True)),indent=2)+'\n')
print(r.stderr)
PY
