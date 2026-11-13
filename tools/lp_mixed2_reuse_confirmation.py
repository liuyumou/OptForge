"""Prospective independent confirmation; immutable complete session blocks."""
import argparse
import math
import random
import subprocess
import time
from lp_mixed2_reuse_common import BASE, BINARY, IMAGE, ROOT, DEVICE, load, put, ref, require
from lp_mixed2_reuse_study import execute_session
from lp_mixed2_fp4_analysis import interval

FREEZE=BASE/'confirmation-freeze.json'
TIERS=['certified-1e-7','certified-1e-9']
FAMILIES=['dense-generic-1024','dense-generic-2048','dense-coupled-1024','dense-coupled-2048']


def roster(blocks=32, seed=390072):
    require(blocks>0 and blocks%2==0,'balanced even block count')
    rng=random.Random(seed); pairs=[(f,t) for f in FAMILIES for t in TIERS]
    orders={p:rng.sample([0]*(blocks//2)+[1]*(blocks//2),blocks) for p in pairs}
    cells=[]
    for block in range(blocks):
        shuffled=pairs.copy();rng.shuffle(shuffled)
        for family,tier in shuffled:
            lanes=['native','fp4x2']
            if orders[family,tier][block]:lanes.reverse()
            for position,lane in enumerate(lanes):
                cells.append(dict(id=f'b{block:02d}-{family}-{tier}-{lane}',block=block,
                                  family=family,tier=tier,lane=lane,position=position))
    return cells


def bindings():
    paths=list((ROOT/'research/lp-mixed2-reuse/src').glob('*.rs'))
    paths+=list((ROOT/'research/lp-mixed2-reuse').glob('Cargo.*'))
    paths+=[ROOT/'tools'/f'lp_mixed2_reuse_{n}.py' for n in
            ('confirmation','common','study','transport','place','budget','analysis')]
    paths+=[ROOT/'tools/lp_cpu_admission.py',ROOT/'tools/lp_mixed2_fp4_cpu.py',ROOT/'tools/lp_mixed2_fp4_analysis.py',
            ROOT/'tools/lp_delivery2_transport.py',ROOT/'docs/specifications/SPEC-0039-mixed2-reuse.md',
            ROOT/'docs/decisions/ADR-0072-mixed2-reuse.md']
    return [ref(p) for p in sorted(paths)]


def freeze():
    require(not FREEZE.exists(),'already frozen')
    admissions=[]
    for name in ['native-v2','build-v2','device-v2','scenario-large-v2','scenario-invalid-v2','scenario-recovery-v2','serial-admission-v3','processes-v2','resource-pilot-v1','analysis-admission-v1']+[
            n+'-v2' for n in ('memcheck','racecheck','initcheck','synccheck')]+[
            'scenario-'+n+'-v3' for n in ('memcheck','racecheck','initcheck','synccheck')]:
        p=BASE/'resources'/(name+'.settlement.json')
        require(load(p)['status']=='passed','admission failed: '+name);admissions.append(ref(p))
    require(load(BASE/'cpu-v2/result.json')['status']=='passed' and load(BASE/'cpu-v2/manifest.json')['binary']==ref(BINARY),'current CPU binary')
    admissions.extend([ref(BASE/'cpu-v2/result.json'),ref(BASE/'cpu-v2/manifest.json')])
    diagnosis=load(BASE/'reliability-v1.json')
    require(diagnosis['proceed_research_confirmation'],'reliability disposition not admitted')
    models=load(BASE/'models/manifest.json');ci=interval(list(range(32)),.05/16);k=ci['rank']
    # Probability that the simultaneous lower bound exceeds a threshold when an
    # independent block exceeds it with probability p. This is sign-consistency
    # planning, not a fitted Gaussian power claim or an independence guarantee.
    power={str(p):sum(math.comb(32,i)*p**i*(1-p)**(32-i) for i in range(33-k,33))
           for p in (.75,.8,.85,.9,.95)}
    put(FREEZE,dict(schema_version=1,blocks=32,count=32,block_reserve_seconds=200,seed=390072,cells=roster(),
        binary=ref(BINARY),image=ref(IMAGE),sources=bindings(),admissions=admissions,
        models=ref(BASE/'models/manifest.json'),groups=models['groups'],diagnosis=ref(BASE/'reliability-v1.json'),
        worker_cpus=3,supervisor_cpus=4,max_gap_ns=100000000,
        primary='complete 32-request changing-model session including all setup, cache, switching, durable results and teardown',
        statistics=dict(comparisons=16,alpha=.05/16,rank=k,coverage=ci['coverage'],
                        positive_blocks_needed=33-k,sign_power=power),
        value=dict(speedup_lower_above=1.,saved_ms_lower_above=10.,provisional_comparison=1.10),
        limitations=['constructed four-scenario cyclic streams','shared GPU and temporal independence assumption',
                    'scope selected using prior study, tested on independent prospective sessions',
                    'historical sanitizer exit and heartbeat cause not necessarily resolved'],
        no_retry=True,default_change=False))


def environment_snapshot():
    fields='uuid,driver_version,temperature.gpu,power.draw,clocks.sm,memory.used,utilization.gpu'
    try:
        result=subprocess.run(['nvidia-smi','--id='+DEVICE,'--query-gpu='+fields,'--format=csv'],
                              capture_output=True,text=True,timeout=5)
        return dict(time_ns=time.time_ns(),monotonic_ns=time.monotonic_ns(),fields=fields,
                    returncode=result.returncode,stdout=result.stdout,stderr=result.stderr)
    except (OSError,subprocess.TimeoutExpired) as error:
        # Optional coarse diagnostics never select or discard a scientific cell.
        return dict(time_ns=time.time_ns(),error=repr(error))


def block(index):
    f=load(FREEZE);require(type(index) is int and 0<=index<f['blocks'],'block index')
    require(f['sources']==bindings() and f['binary']==ref(BINARY) and f['image']==ref(IMAGE),'frozen code changed')
    for item in [f['models'],f['diagnosis'],*f['admissions'],*[p for ps in f['groups'].values() for p in ps]]:
        require(ref(ROOT/item['path'])==item,'frozen input changed')
    out=BASE/f'confirmation-b{index:02d}';out.mkdir(exist_ok=False)
    put(out/'manifest.json',dict(freeze=ref(FREEZE),block=index,environment=environment_snapshot()));rows=[];models=load(ROOT/f['models']['path'])
    try:
        for cell in (c for c in f['cells'] if c['block']==index):
            rows.append(execute_session(out,cell,models,count=f['count']))
    except BaseException as error:
        put(out/'FAILED.json',dict(error=repr(error),completed=len(rows)));raise
    put(out/'result.json',dict(status='complete',block=index,sessions=rows,environment=environment_snapshot()))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','block']);p.add_argument('--index',type=int)
    a=p.parse_args();freeze() if a.action=='freeze' else block(a.index)
