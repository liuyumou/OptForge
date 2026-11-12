"""Explicit versioned build; never triggered by workspace Cargo builds."""
import argparse
import re
import subprocess
from lp_fp4_fast_common import ROOT, BASE, put, ref, require

def main():
    p=argparse.ArgumentParser();p.add_argument('version');args=p.parse_args()
    out=BASE/('build-'+args.version);out.mkdir(exist_ok=False)
    source=ROOT/'research/lp-fp4-fast/cuda/fast.cu'
    (out/'fast.cu').write_bytes(source.read_bytes())
    commands=[]
    for mode,suffix in [('--cubin','cubin'),('--ptx','ptx')]:
        cmd=['/usr/local/cuda/bin/nvcc',mode,'-arch=sm_120a','-O3','-lineinfo','-fmad=false','-ftz=false','-Xptxas=-v',str(source),'-o',str(out/f'fast.{suffix}')]
        result=subprocess.run(cmd,capture_output=True,text=True,timeout=300)
        (out/f'{suffix}.stdout').write_text(result.stdout);(out/f'{suffix}.stderr').write_text(result.stderr)
        result.check_returncode();commands.append(cmd)
    sass=subprocess.check_output(['/usr/local/cuda/bin/cuobjdump','--dump-sass',str(out/'fast.cubin')],text=True,timeout=30)
    (out/'fast.sass').write_text(sass)
    log=(out/'cubin.stderr').read_text();registers=list(map(int,re.findall(r'Used (\d+) registers',log)))
    spills=[list(map(int,p)) for p in re.findall(r'(\d+) bytes spill stores, (\d+) bytes spill loads',log)]
    require(len(registers)==56 and max(registers)<=255 and not any(any(p) for p in spills),'register/spill admission')
    require('kind::f8f6f4.f32.e2m1.e2m1.f32' in (out/'fast.ptx').read_text() and 'E2M1' in sass,'actual FP4 instructions')
    put(out/'receipt.json',dict(commands=commands,registers=registers,spills=spills,source=ref(source),reference=ref(ROOT/'research/lp-fp4-gpu-pilot/cuda/pilot_v3.cu'),image=ref(out/'fast.cubin')))
    print(log)

if __name__=='__main__':main()
