"""Explicit CUDA provisioning, never called by workspace cargo builds."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'artifacts/gpup-fp4-gpu-pilot-v1'

def main():
    out=BASE/'build-v3';out.mkdir(exist_ok=False)
    source=ROOT/'research/lp-fp4-gpu-pilot/cuda/pilot_v3.cu'
    (out/'pilot.cu').write_bytes(source.read_bytes())
    commands=[]
    for mode,suffix in [('--cubin','cubin'),('--ptx','ptx')]:
        cmd=['/usr/local/cuda/bin/nvcc',mode,'-arch=sm_120a','-O3','-lineinfo','-fmad=false','-ftz=false','-Xptxas=-v',str(source),'-o',str(out/f'pilot.{suffix}')]
        result=subprocess.run(cmd,capture_output=True,text=True,timeout=300)
        (out/f'{suffix}.stdout').write_text(result.stdout);(out/f'{suffix}.stderr').write_text(result.stderr)
        result.check_returncode();commands.append(cmd)
    sass=subprocess.check_output(['/usr/local/cuda/bin/cuobjdump','--dump-sass',str(out/'pilot.cubin')],text=True,timeout=30)
    (out/'pilot.sass').write_text(sass)
    log=(out/'cubin.stderr').read_text();registers=list(map(int,re.findall(r'Used (\d+) registers',log)))
    spills=[list(map(int,p)) for p in re.findall(r'(\d+) bytes spill stores, (\d+) bytes spill loads',log)]
    if len(registers)!=6 or max(registers)>255 or any(any(pair) for pair in spills):raise ValueError('register/spill admission')
    ptx=(out/'pilot.ptx').read_text()
    if 'kind::f8f6f4.f32.e2m1.e2m1.f32' not in ptx or 'E2M1' not in sass:raise ValueError('actual FP4 image evidence absent')
    (out/'receipt.json').write_text(json.dumps(dict(commands=commands,registers=registers,spills=spills,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),image_sha256=hashlib.sha256((out/'pilot.cubin').read_bytes()).hexdigest()),indent=2)+'\n')
    print(log)

if __name__=='__main__':main()
