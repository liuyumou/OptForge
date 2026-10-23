#!/usr/bin/env bash
# ADR-0043 compile/instruction admission only; never executes a GPU job.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 - <<'PY'
import hashlib,json,re,subprocess
from pathlib import Path
source=Path('cuda/lp_pdhg_tensor_residual/lp_pdhg_tensor_residual.cu');image=Path('target/native/cuda/lp_pdhg_tensor_residual.cubin');out=Path('artifacts/gpup-tensor-residual-v1/build');out.mkdir(parents=True,exist_ok=True)
flags=['-arch=sm_120','-O3','-lineinfo','-fmad=false','-ftz=false','-Xptxas=-v']
cmd=['/usr/local/cuda/bin/nvcc','--cubin',*flags,'-o',str(image),str(source)]
r=subprocess.run(cmd,capture_output=True,text=True,timeout=300)
(out/'compile.stdout').write_text(r.stdout);(out/'compile.stderr').write_text(r.stderr);r.check_returncode()
registers=list(map(int,re.findall(r'Used (\d+) registers',r.stderr)));spills=re.findall(r'(\d+) bytes spill stores, (\d+) bytes spill loads',r.stderr)
if not registers or max(registers)>128 or not spills or any(a!='0' or b!='0' for a,b in spills):raise ValueError('Tensor register/spill admission failed')
ptx=subprocess.check_output(['/usr/local/cuda/bin/nvcc','--ptx',*flags,'-o','-',str(source)],text=True)
sass=subprocess.check_output(['/usr/local/cuda/bin/cuobjdump','--dump-sass',str(image)],text=True)
resources=subprocess.check_output(['/usr/local/cuda/bin/cuobjdump','--dump-resource-usage',str(image)],text=True)
for name in ['tn_int8','tn_fp16','tn_bf16']:
 body=sass.split('Function : '+name,1)[1].split('Function :',1)[0]
 if not re.search(r'\b[HI]MMA',body):raise ValueError('missing Tensor instruction '+name)
if re.search(r'\b(?:fma\.|\w+\.ftz\.)',ptx):raise ValueError('unauthorized contraction/FTZ')
for name,text in [('tensor.ptx',ptx),('tensor.sass',sass),('tensor.resources',resources)]: (out/name).write_text(text)
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
files=[source,Path('cuda/lp_pdhg_tensor_residual/fragment_layout.h'),Path('cuda/lp_pdhg_quant_resident/lp_pdhg_quant_resident.cu'),Path('cuda/lp_pdhg_tuned/lp_pdhg_tuned.cu'),Path('cuda/lp_pdhg/lp_pdhg.cu')]
result=dict(status='passed',gpu_seconds=0,command=cmd,sources={str(p):h(p) for p in files},image_sha256=h(image),max_registers=max(registers),spill_bytes=0,nvcc_version=subprocess.check_output(['/usr/local/cuda/bin/nvcc','--version'],text=True),ptx_sha256=h(out/'tensor.ptx'),sass_sha256=h(out/'tensor.sass'))
image.with_suffix('.build.json').write_text(json.dumps(result,indent=2)+'\n')
Path('docs/benchmarks/data/tensor-residual').mkdir(parents=True,exist_ok=True)
Path('docs/benchmarks/data/tensor-residual/instruction-admission.json').write_text(json.dumps(result,indent=2)+'\n')
print('Tensor image passes: max registers',max(registers),'zero spills; INT8/FP16/BF16 MMA instructions present')
PY
