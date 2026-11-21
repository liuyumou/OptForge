"""Fresh source-bound operational admission under the revised approved phase caps."""
import argparse,time
from lp_billion_common import BASE,ROOT,put,ref,load,require
from lp_billion_prepare_continue import job
from lp_billion_availability import observe,proof,stable,idle
from lp_billion_idle import Nvml
GPU='operational-gpu-v20'
PYTHON=ROOT/'artifacts/gpup-copt-adapter-env/venv/bin/python'
def observation():
    sensor=Nvml();samples=[];refs=[];start=time.monotonic();ready=False
    try:
        for i in range(8):
            if i:
                target=start+60*i
                while time.monotonic()<target:time.sleep(min(1,target-time.monotonic()))
            s=sensor.sample();p=BASE/'availability'/GPU/(str(s['start_ns'])+'.json');put(p,s)
            samples.append(s);refs.append(ref(p));ready=stable(samples,time.monotonic_ns())
            print(dict(sample=i,idle=idle(s),used_gib=s['used']/2**30,ready=ready),flush=True)
            if ready:break
        put(BASE/'gpu-pack-idle-v2/result.json',dict(status='observed_idle' if ready else 'idle_gate_not_met',samples=refs,source=ref(__file__)))
    finally:sensor.close()
def execute():
    command=['bash','-c',f'set -e\n{PYTHON} -B -m unittest discover -s tests/integration -p "test_lp_confirmation*supervisor.py"\n{PYTHON} -B -m unittest discover -s tests/integration -p "test_lp_billion*.py"']
    job('operational-cpu-v24',180,command,phase='admission')
    job('gpu-pack-idle-v2',480,['python3','-B',__file__,'observation'],phase='reporting',host=8)
    require(load(BASE/'gpu-pack-idle-v2/result.json')['status']=='observed_idle','full fresh idle window')
    observe(GPU);proof(GPU)
    job(GPU,120,[str(PYTHON),'-B',str(ROOT/'tools/lp_billion_admit.py'),'gpu','--id',GPU,'--version','2'],gpu=True)
    job('gpu-pack-quality-v6',480,['bash','tools/lp_general_env.sh','env','CARGO_BUILD_JOBS=1','python3','-B',str(ROOT/'tools/lp_billion_gpu_pack_build.py'),'build','--id','gpu-pack-quality-v6'],phase='native',host=16,disk=3)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['execute','observation']);a=p.parse_args();globals()[a.action]()
