"""Run the explicitly approved fresh operational recovery, without repeating science."""
import argparse,time
from lp_billion_common import BASE,put,load,ref,require
from lp_billion_availability import stable,idle,observe,proof
from lp_billion_idle import Nvml
from lp_billion_prepare_continue import job,completed

def observation():
    out=BASE/'recovery-idle-v1';out.mkdir(exist_ok=False)
    sensor=Nvml();samples=[];start=time.monotonic();ready=False
    try:
        for i in range(8):
            if i:
                target=start+60*i
                while time.monotonic()<target:time.sleep(min(1,target-time.monotonic()))
            sample=sensor.sample();path=BASE/'availability/operational-gpu-v17'/(str(sample['start_ns'])+'.json');put(path,sample);samples.append(ref(path))
            ready=stable([load(BASE/p['path']) for p in samples],time.monotonic_ns())
            print(dict(sample=i,idle=idle(sample),used_gib=sample['used']/2**30,ready=ready),flush=True)
            if ready:break
        put(out/'result.json',dict(status='observed_idle' if ready else 'idle_gate_not_met',samples=samples,source=ref(__file__)))
    finally:sensor.close()

def run():
    require(completed('operational-cpu-v20'),'fresh CPU recovery admission')
    sensor=Nvml()
    try:
        job('recovery-idle-v1',480,['python3','-B',__file__,'observation'],host=8)
        require(load(BASE/'recovery-idle-v1/result.json')['status']=='observed_idle','full idle observation required')
        observe('operational-gpu-v17');proof('operational-gpu-v17')
        job('operational-gpu-v17',180,['python3','-B','tools/lp_billion_admit.py','gpu','--id','operational-gpu-v17','--version','2'],gpu=True)
    finally:sensor.close()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['observation','run']);a=p.parse_args();globals()[a.action]()
