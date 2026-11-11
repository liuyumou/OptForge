"""One explicitly diagnostic Nsight Compute replay; not a timing cell."""
import subprocess
from lp_fp4_fast_common import BASE, put, ref, require
from lp_fp4_fast_experiment import BINARY
from lp_fp4_fast_prepare import request


def main():
    d=BASE/'counters-v1';d.mkdir(exist_ok=False)
    put(d/'input.json',request(512,4,8))
    cmd=['/usr/local/cuda/bin/ncu','--target-processes','all','--kernel-name','regex:fast_4_8_3','--launch-skip','2','--launch-count','1','--section','SpeedOfLight','--section','WarpStateStats','--section','LaunchStats','--section','Occupancy','--clock-control','none','--export',str(d/'profile'),'--csv',str(BINARY),str(d/'input.json'),str(BASE/'build-v1/fast.cubin'),str(d/'output.json')]
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=150)
    (d/'stdout').write_text(p.stdout);(d/'stderr').write_text(p.stderr)
    put(d/'attempt.json',dict(command=cmd,returncode=p.returncode,stdout=ref(d/'stdout'),stderr=ref(d/'stderr')))
    print(p.stdout[-6000:]);print(p.stderr)
    require(p.returncode==0,'Nsight diagnostic unavailable')

if __name__=='__main__':main()
