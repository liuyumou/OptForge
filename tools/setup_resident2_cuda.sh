#!/usr/bin/env bash
# SPEC-0024 provisioning only; never called by ordinary cargo builds.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 - <<'PY'
import hashlib,json,re,subprocess
from pathlib import Path
s=Path('cuda/lp_pdhg_resident2/lp_pdhg_resident2.cu');d=Path('target/native/cuda');d.mkdir(parents=True,exist_ok=True)
cmd=['/usr/local/cuda/bin/nvcc','--cubin','-arch=sm_120','-O3','-lineinfo','-fmad=false','-ftz=false','-Xptxas=-v','-o',str(d/'lp_pdhg_resident2.cubin'),str(s)]
r=subprocess.run(cmd,capture_output=True,text=True,timeout=300)
(d/'lp_pdhg_resident2.compile.stdout').write_text(r.stdout);(d/'lp_pdhg_resident2.compile.stderr').write_text(r.stderr);r.check_returncode()
registers=[int(n) for n in re.findall(r'Used (\d+) registers',r.stderr)]
spills=re.findall(r'(\d+) bytes spill stores, (\d+) bytes spill loads',r.stderr)
if not registers or max(registers)>128 or not spills or any(a!='0' or b!='0' for a,b in spills):raise ValueError('resident register/spill admission')
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(d/'lp_pdhg_resident2.build.json').write_text(json.dumps(dict(command=cmd,source_sha256=h(s),included_sources={str(p):h(p) for p in [Path('cuda/lp_pdhg_tuned/lp_pdhg_tuned.cu'),Path('cuda/lp_pdhg/lp_pdhg.cu')]},image_sha256=h(d/'lp_pdhg_resident2.cubin'),registers=registers,spills=spills,nvcc_version=subprocess.check_output(['/usr/local/cuda/bin/nvcc','--version'],text=True)),indent=2)+'\n')
print(r.stderr)
PY
