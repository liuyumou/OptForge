"""Resume admitted preparation stages; failed reservations and scientific cells never repeat."""
from lp_billion_common import BASE,load,resolve,require
from lp_billion_budget import run


def completed(identity):
    reservation=BASE/'resources'/(identity+'.reservation.json')
    if not reservation.exists():
        return False
    settled=reservation.with_name(identity+'.settlement.json')
    require(settled.exists(),'unsettled reservation: '+identity)
    result=load(settled)
    require(result['status']=='passed' and result['cleanup_empty'] and not result['overrun'],
            'retain failed reservation; fresh explicit admission is required: '+identity)
    return True


def job(identity,seconds,command,gpu=False,phase='admission',host=16,disk=2):
    if completed(identity):
        print(dict(job=identity,status='already_passed'),flush=True)
        return
    result=run(identity,phase,seconds,gpu,command,host,2 if gpu else 0,disk)
    print(dict(job=identity,settlement=result),flush=True)
    require(result['status']=='passed','job stopped; retain outcome without retry')


def main():
    job('preparation-harness-cpu-v2',120,
        ['python3','-B','-m','unittest','discover','-s','tests/integration','-p','test_lp_billion*.py'])
    if not completed('operational-gpu-v8'):
        from lp_billion_availability import observe,proof,stable
        import time
        observe('operational-gpu-v8')
        paths=sorted((BASE/'availability/operational-gpu-v8').glob('*.json'),key=lambda p:int(p.stem))
        if not stable([load(p) for p in paths],time.monotonic_ns()):
            print(dict(status='waiting_for_gpu',required_idle_seconds=300),flush=True)
            return 75
        proof_path=BASE/'availability/operational-gpu-v8.json'
        if not proof_path.exists():
            proof('operational-gpu-v8')
        job('operational-gpu-v8',120,['python3','-B','tools/lp_billion_admit.py','gpu','--id','operational-gpu-v8','--version','2'],gpu=True)
    job('seal-prepare-v3',30,['python3','-B','tools/lp_billion_admit.py','seal','--version','3'])
    job('array-gpu-v3',240,['python3','-B','tools/lp_billion_admit.py','gpu','--id','array-gpu-v3','--version','3'],gpu=True)
    for sanitizer in ['memcheck','racecheck','initcheck','synccheck']:
        identity='array-'+sanitizer+'-v3'
        job(identity,240,['python3','-B','tools/lp_billion_admit.py','gpu','--id',identity,'--version','3','--sanitizer',sanitizer],gpu=True)
    from lp_billion_campaign import freeze
    from lp_billion_ladder import execute
    from lp_billion_results import summarize,compare
    for tag,seconds,host in [('64m',600,32),('256m',900,64),('512m',1800,64)]:
        before=BASE/('ladder-'+tag+'-v2/freeze.json')
        previous=load(before)['cells']
        identity='ladder-'+tag+'-v3';manifest=BASE/identity/'freeze.json'
        if not manifest.exists():
            models=[resolve(c['model_result']) for c in previous]
            walls={load(p)['family']:c['request']['settings']['wall_ms'] for p,c in zip(models,previous)}
            reserves={load(p)['family']:c['seconds'] for p,c in zip(models,previous)}
            freeze(identity,models,['fp4x2'],100,walls,reserves,ladder=True,version=3)
        remaining=[i for i,c in enumerate(load(manifest)['cells']) if c['status']=='pending' and not completed(c['id'])]
        execute(manifest,remaining)
        job('audit-'+tag+'-v3',seconds,['python3','-B','tools/lp_billion_results.py','audit',str(manifest)],phase='reporting',host=host)
        summary=BASE/identity/'summary.json'
        if not summary.exists():summarize(manifest,summary)
        paired=BASE/('paired-'+tag+'-v2-v3.json')
        if not paired.exists():compare(before,manifest,paired)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
