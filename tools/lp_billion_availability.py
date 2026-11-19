"""Read-only availability observations before the next operational GPU admission."""
import argparse
import time
from lp_billion_common import BASE, load, put, ref, require
from lp_billion_idle import Nvml, validate_gpu


def idle(sample):
    try:
        validate_gpu(sample,set())
        return sample['utilization']==0 and not sample['processes']
    except (ValueError,KeyError):
        return False


def stable(samples, now):
    recent=[]
    for sample in reversed(samples):
        if not idle(sample):
            break
        if recent and recent[-1]['start_ns']-sample['end_ns']>90_000_000_000:
            break
        recent.append(sample)
    return (len(recent)>=6 and 0<=now-recent[0]['end_ns']<=90_000_000_000
            and recent[0]['start_ns']-recent[-1]['end_ns']>=300_000_000_000)


def observe(identity):
    out=BASE/'availability'/identity
    sensor=Nvml()
    try:
        sample=sensor.sample()
    finally:
        sensor.close()
    put(out/(str(sample['start_ns'])+'.json'),sample)
    samples=[load(p) for p in sorted(out.glob('*.json'),key=lambda p:int(p.stem))]
    print(dict(idle=idle(sample),used_gib=sample['used']/2**30,
               utilization=sample['utilization'],stable_five_minutes=stable(samples,time.monotonic_ns())),flush=True)


def proof(identity):
    paths=sorted((BASE/'availability'/identity).glob('*.json'),key=lambda p:int(p.stem))
    require(stable([load(p) for p in paths],time.monotonic_ns()),'five-minute idle observations required')
    put(BASE/'availability'/(identity+'.json'),dict(status='observed_idle',samples=[ref(p) for p in paths],
        required_span_seconds=300,max_observation_gap_seconds=90,
        limitation='Sampled availability does not reserve the device or guarantee later idleness.'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['observe','proof']);p.add_argument('--id',required=True);a=p.parse_args()
    require(a.id and '/' not in a.id and a.id not in ['.','..'],'availability identity')
    (observe if a.action=='observe' else proof)(a.id)
