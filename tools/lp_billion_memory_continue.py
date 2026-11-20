"""Admit borrowed host storage and measure only fresh image-v4 capacity cells."""
import argparse
import time
from lp_billion_common import BASE,load,put,ref,resolve,require
from lp_billion_prepare_continue import completed,job
from lp_billion_idle import Nvml
from lp_billion_availability import idle,stable,observe,proof


def observation(identity):
    sensor=Nvml();samples=[];start=time.monotonic();ready=False
    try:
        for i in range(8):
            if i:
                target=start+60*i
                while time.monotonic()<target:time.sleep(min(1,target-time.monotonic()))
            sample=sensor.sample();path=BASE/'availability/operational-gpu-v10'/(str(sample['start_ns'])+'.json')
            put(path,sample);samples.append(ref(path))
            ready=stable([load(resolve(p)) for p in samples],time.monotonic_ns())
            print(dict(sample=i,idle=idle(sample),used_gib=sample['used']/2**30,utilization=sample['utilization'],ready=ready),flush=True)
            if ready:break
        put(BASE/identity/'result.json',dict(status='observed_idle' if ready else 'idle_gate_not_met',
            samples=samples,source=ref(__file__),cuda_context_created=False,device_mutations=False))
    finally:sensor.close()


def main():
    job('operational-cpu-v10',120,['bash','-c',
        'set -e\npython3 -B -m unittest discover -s tests/integration -p "test_lp_confirmation*supervisor.py"\n'
        'python3 -B -m unittest discover -s tests/integration -p "test_lp_billion*.py"'])
    job('seal-memory-v1',30,['python3','-B','tools/lp_billion_admit.py','seal','--version','4'])
    # Retain a read-only monitor across observation and admission, without device
    # changes or a CUDA context. Every GPU reservation still passes quiet().
    sensor=Nvml()
    try:
        if not completed('operational-gpu-v10'):
            job('memory-idle-v1',480,['python3','-B',__file__,'--observe','memory-idle-v1'],phase='reporting',host=8)
            if load(BASE/'memory-idle-v1/result.json')['status']!='observed_idle':return 75
            observe('operational-gpu-v10')
            proof('operational-gpu-v10')
            job('operational-gpu-v10',120,['python3','-B','tools/lp_billion_admit.py','gpu','--id','operational-gpu-v10','--version','2'],gpu=True)
        from lp_billion_admit import gate_identity
        for kind in ['gpu','memcheck','racecheck','initcheck','synccheck']:
            identity=gate_identity(kind,4)
            command=['python3','-B','tools/lp_billion_admit.py','gpu','--id',identity,'--version','4']
            if kind!='gpu':command+=['--sanitizer',kind]
            job(identity,600 if kind=='racecheck' else 240 if kind=='gpu' else 120,command,
                gpu=True,host=32 if kind=='racecheck' else 16)
        from lp_billion_campaign import freeze
        from lp_billion_ladder import execute
        from lp_billion_results import summarize,compare
        for tag,seconds,host in [('64m',600,32),('256m',900,32),('512m',1800,40)]:
            before=BASE/('ladder-'+tag+'-v3/freeze.json');previous=load(before)['cells']
            identity='ladder-'+tag+'-v4';manifest=BASE/identity/'freeze.json'
            if not manifest.exists():
                models=[resolve(c['model_result']) for c in previous]
                walls={load(p)['family']:c['request']['settings']['wall_ms'] for p,c in zip(models,previous)}
                reserves={load(p)['family']:c['seconds'] for p,c in zip(models,previous)}
                freeze(identity,models,['fp4x2'],100,walls,reserves,ladder=True,version=4)
            remaining=[i for i,c in enumerate(load(manifest)['cells']) if c['status']=='pending' and not completed(c['id'])]
            execute(manifest,remaining)
            job('audit-'+tag+'-v4',seconds,['python3','-B','tools/lp_billion_results.py','audit',str(manifest)],phase='reporting',host=host)
            summary=BASE/identity/'summary.json'
            if not summary.exists():summarize(manifest,summary)
            paired=BASE/('paired-'+tag+'-v3-v4.json')
            if not paired.exists():compare(before,manifest,paired)
        return 0
    finally:sensor.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--observe');a=parser.parse_args()
    if a.observe:observation(a.observe)
    else:raise SystemExit(main())
