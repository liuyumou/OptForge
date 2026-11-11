"""Versioned integration image build; does not create a device context."""
import argparse,re,subprocess
from lp_fp4_accel_common import ROOT,BASE,put,ref,require

def main():
 p=argparse.ArgumentParser();p.add_argument('version');a=p.parse_args()
 out=BASE/('build-'+a.version);out.mkdir(exist_ok=False)
 src=ROOT/'research/lp-fp4-accel/cuda/accel.cu'
 for path in src.parent.glob('*'): (out/path.name).write_bytes(path.read_bytes())
 commands=[]
 for mode,suffix in [('--cubin','cubin'),('--ptx','ptx')]:
  cmd=['/usr/local/cuda/bin/nvcc',mode,'-arch=sm_120a','-O3','-lineinfo','-fmad=false','-ftz=false','-Xptxas=-v',str(src),'-o',str(out/f'accel.{suffix}')]
  r=subprocess.run(cmd,capture_output=True,text=True,timeout=300)
  (out/f'{suffix}.stdout').write_text(r.stdout);(out/f'{suffix}.stderr').write_text(r.stderr);r.check_returncode();commands.append(cmd)
 sass=subprocess.check_output(['/usr/local/cuda/bin/cuobjdump','--dump-sass',str(out/'accel.cubin')],text=True,timeout=30)
 (out/'accel.sass').write_text(sass)
 require('E2M1' in sass and 'kind::f8f6f4.f32.e2m1.e2m1.f32' in (out/'accel.ptx').read_text(),'actual FP4 instruction missing')
 log=(out/'cubin.stderr').read_text();spills=re.findall(r'(\d+) bytes spill stores, (\d+) bytes spill loads',log)
 put(out/'receipt.json',dict(commands=commands,source=ref(src),helpers=ref(src.parent/'helpers.cuh'),image=ref(out/'accel.cubin'),registers=list(map(int,re.findall(r'Used (\d+) registers',log))),spills=spills))
 print(log)
if __name__=='__main__':main()
