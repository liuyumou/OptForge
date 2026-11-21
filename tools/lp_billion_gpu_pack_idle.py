"""Container-only read-only five-minute availability window for GPU packing."""
import time
from lp_billion_common import BASE,put,ref
from lp_billion_idle import Nvml
from lp_billion_availability import stable,idle

def observe(identity='operational-gpu-v19'):
    sensor=Nvml();samples=[];refs=[];start=time.monotonic();ready=False
    try:
        for i in range(8):
            if i:
                target=start+60*i
                while time.monotonic()<target:time.sleep(min(1,target-time.monotonic()))
            s=sensor.sample();p=BASE/'availability'/identity/(str(s['start_ns'])+'.json');put(p,s)
            samples.append(s);refs.append(ref(p));ready=stable(samples,time.monotonic_ns())
            print(dict(sample=i,idle=idle(s),used_gib=s['used']/2**30,ready=ready),flush=True)
            if ready:break
        put(BASE/'gpu-pack-idle-v1/result.json',dict(status='observed_idle' if ready else 'idle_gate_not_met',samples=refs,source=ref(__file__)))
    finally:sensor.close()
if __name__=='__main__':observe()
