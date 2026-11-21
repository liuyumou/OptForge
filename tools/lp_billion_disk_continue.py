"""Operational readmission of exact native inventory, then untouched packing cohorts."""
import argparse,time
from lp_billion_common import BASE,ROOT,put,ref,load,require
from lp_billion_prepare_continue import job,completed
from lp_billion_availability import observe,proof,stable,idle
from lp_billion_idle import Nvml
GPU='operational-gpu-v21'
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
        put(BASE/'gpu-pack-idle-v3/result.json',dict(status='observed_idle' if ready else 'idle_gate_not_met',samples=refs,source=ref(__file__)))
    finally:sensor.close()
def execute():
    require(completed('operational-cpu-v26'),'fresh native-inventory operational CPU acceptance')
    job('gpu-pack-idle-v3',480,['python3','-B',str(ROOT/'tools/lp_mixed2_reuse_place.py'),'python3','-B',__file__,'observation'],phase='reporting',host=8)
    require(load(BASE/'gpu-pack-idle-v3/result.json')['status']=='observed_idle','full fresh idle window')
    observe(GPU);proof(GPU)
    job(GPU,120,[str(PYTHON),'-B',str(ROOT/'tools/lp_billion_admit.py'),'gpu','--id',GPU,'--version','2'],gpu=True)
    from lp_billion_gpu_pack_continue import measure
    measure()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['execute','observation']);a=p.parse_args();globals()[a.action]()
