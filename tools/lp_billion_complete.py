"""Guarded continuation of the authorized full billion comparison."""
import argparse
import time
from lp_billion_common import BASE,put,load,ref,resolve,require
from lp_billion_availability import idle,stable,observe,proof
from lp_billion_idle import Nvml
from lp_billion_prepare_continue import job,completed


def observation():
    identity='complete-idle-v1';sensor=Nvml();samples=[];start=time.monotonic();ready=False
    try:
        for i in range(8):
            if i:
                target=start+60*i
                while time.monotonic()<target:time.sleep(min(1,target-time.monotonic()))
            s=sensor.sample();p=BASE/'availability/operational-gpu-v16'/(str(s['start_ns'])+'.json');put(p,s);samples.append(ref(p))
            ready=stable([load(resolve(p)) for p in samples],time.monotonic_ns())
            print(dict(sample=i,idle=idle(s),used_gib=s['used']/2**30,ready=ready),flush=True)
            if ready:break
        put(BASE/identity/'result.json',dict(status='observed_idle' if ready else 'idle_gate_not_met',samples=samples,
            cuda_context_created=False,source=ref(__file__)))
    finally:sensor.close()


def device_admission():
    require(completed('operational-cpu-v18'),'current operational CPU gate')
    sensor=Nvml()
    try:
        require(load(BASE/'complete-idle-v1/result.json')['status']=='observed_idle','complete observed idle window')
        if not completed('operational-gpu-v16'):
            observe('operational-gpu-v16');proof('operational-gpu-v16')
            job('operational-gpu-v16',120,['python3','-B','tools/lp_billion_admit.py','gpu','--id','operational-gpu-v16','--version','2'],gpu=True)
        from lp_billion_admit import gate_identity
        for kind in ['gpu','memcheck','racecheck','initcheck','synccheck']:
            identity=gate_identity(kind,9);cmd=['python3','-B','tools/lp_billion_admit.py','gpu','--id',identity,'--version','9']
            if kind!='gpu':cmd+=['--sanitizer',kind]
            job(identity,600 if kind=='racecheck' else 240 if kind=='gpu' else 120,cmd,gpu=True,host=64 if kind=='racecheck' else 16)
    finally:sensor.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['observation','device_admission']);a=p.parse_args();globals()[a.action]()
