"""CPU-only implementation compilation of the isolated packing CUDA module."""
import subprocess
from lp_billion_common import BASE,ROOT,put,ref,require
out=BASE/'gpu-pack-cuda-compile-v1';out.mkdir(exist_ok=False)
cmd=['/usr/local/cuda/bin/nvcc','-std=c++17','-O3','-lineinfo','-fmad=false','-ftz=false','-arch=sm_120a','--ptxas-options=-v','--cubin',str(ROOT/'research/lp-billion-lowbit/cuda/pack.cu'),'-o',str(out/'pack.cubin')]
p=subprocess.run(cmd,text=True,capture_output=True,timeout=45)
(out/'stdout').write_text(p.stdout);(out/'stderr').write_text(p.stderr)
require(p.returncode==0,'packing CUDA implementation compile: '+p.stderr)
put(out/'result.json',dict(status='passed',command=cmd,cuda=ref(out/'pack.cubin'),source=ref(ROOT/'research/lp-billion-lowbit/cuda/pack.cu'),gpu_executed=False))
print(dict(status='compiled',gpu_executed=False),flush=True)
