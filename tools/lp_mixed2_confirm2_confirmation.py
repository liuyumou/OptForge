"""Prospective independent confirmation; immutable complete session blocks."""
import argparse
import math
import os
import random
import subprocess
import time
from lp_mixed2_confirm2_common import BASE, PRIOR, BINARY, IMAGE, ROOT, DEVICE, load, put, ref, require
from lp_mixed2_reuse_study import execute_session
from lp_mixed2_fp4_analysis import interval

FREEZE=BASE/'confirmation-freeze.json'
TIERS=['certified-1e-7','certified-1e-9']
FAMILIES=['dense-generic-1024','dense-generic-2048','dense-coupled-1024','dense-coupled-2048']


def roster(blocks=32, seed=410074):
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
    paths+=[ROOT/'tools'/f'lp_mixed2_confirm2_{n}.py' for n in ('confirmation','common','budget','analysis','admit','serial','validate','run','diagnose')]
    paths+=[ROOT/'tools'/f'lp_mixed2_reuse_{n}.py' for n in ('study','transport','place','analysis','common')]
    paths+=[ROOT/'tools/lp_confirmation2_supervisor.py',ROOT/'tools/lp_cpu_admission.py',
        ROOT/'tools/lp_baseline_common.py',ROOT/'tools/lp_mixed2_reuse_admit.py',
        ROOT/'tools/lp_mixed2_confirm_native_place.py',ROOT/'tools/lp_mixed2_confirm_cargo.py',
        ROOT/'tests/integration/test_lp_confirmation2_supervisor.py',
        ROOT/'tools/lp_mixed2_fp4_cpu.py',ROOT/'tools/lp_mixed2_fp4_analysis.py',ROOT/'tools/lp_delivery2_transport.py',
        ROOT/'docs/specifications/SPEC-0041-mixed2-confirm2.md',ROOT/'docs/decisions/ADR-0074-mixed2-confirm2.md']
    return [ref(p) for p in sorted(paths)]


def freeze():
    require(not FREEZE.exists(),'already frozen')
    admissions=[]
    for name in ['supervisor-contracts-v1','policy-admission-v2','native-v1','same-image-smoke-v1','resource-pilot-v1','resource-pilot2-v1','resource-pilot3-v1','serial-admission-v1','analysis-admission-v1']:
        p=BASE/'resources'/(name+'.settlement.json')
        require(load(p)['status']=='passed','admission failed: '+name);admissions.append(ref(p))
        reservation=load(BASE/'resources'/(name+'.reservation.json'))
        resource=load(ROOT/load(p)['resource']['path'])
        require(reservation['supervisor']==ref(ROOT/'tools/lp_confirmation2_supervisor.py') and
                reservation['max_gap_ns']==1000000000 and not reservation['diagnostic_trace'],
                'admission supervision policy or source mismatch')
        require(resource['guardian_cleanup']['empty'] and resource['result']['cleanup']['empty'],
                'admission cleanup incomplete')
    for name,count in [('same-image-smoke',64),('resource-pilot',512),('resource-pilot2',512),('resource-pilot3',512)]:
        result=load(BASE/(name+'-v1')/'result.json')
        require(result['status']=='passed' and len(result['sessions'])==16 and
                result['exact_historical_comparisons']==count,'pilot coverage incomplete')
    previous=load(PRIOR/'confirmation-freeze.json')
    require(previous['binary']==ref(BINARY) and previous['image']==ref(IMAGE),'numerical identity changed')
    for item in previous['admissions']:
        require(ref(ROOT/item['path'])==item,'historical admission changed')
    admissions.extend(previous['admissions'])
    admissions.extend(ref(BASE/p) for p in ['same-image-smoke-v1/result.json','resource-pilot-v1/result.json','resource-pilot2-v1/result.json','resource-pilot3-v1/result.json',
        'serial-admission-v1/result.json','analysis-admission-v1.json'])
    models=load(PRIOR/'models/manifest.json');ci=interval(list(range(32)),.05/16);k=ci['rank']
    power={str(p):sum(math.comb(32,i)*p**i*(1-p)**(32-i) for i in range(33-k,33)) for p in (.75,.8,.85,.9,.95)}
    put(FREEZE,dict(schema_version=1,blocks=32,count=32,block_reserve_seconds=300,seed=410074,cells=roster(),
        binary=ref(BINARY),image=ref(IMAGE),sources=bindings(),admissions=admissions,
        models=ref(PRIOR/'models/manifest.json'),groups=models['groups'],diagnosis=ref(BASE/'supervisor-admission-v2.json'),
        worker_cpus=3,supervisor_cpus=4,max_gap_ns=1000000000,advisory_gap_ns=100000000,
        primary='complete 32-request changing-model session including all setup, cache, switching, durable results and teardown',
        statistics=dict(comparisons=16,alpha=.05/16,rank=k,coverage=ci['coverage'],positive_blocks_needed=33-k,sign_power=power),
        value=dict(speedup_lower_above=1.,saved_ms_lower_above=10.,provisional_comparison=1.10),
        limitations=['constructed four-scenario cyclic streams','shared GPU and temporal independence assumption',
          'scope selected using prior study, independent prospective sessions','one-second sampled-resource bound does not enclose sub-sample RSS peaks', '100 ms exceedances are retained without censoring timing', 'CPU phase observations do not establish the historical stall cause'],
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
    require(os.environ.get('MIXED2_REUSE_TELEMETRY')!='1','scientific control tracing is disabled')
    require(os.environ.get('MIXED2_CONFIRM2_TRACE')!='1' and not os.environ.get('MIXED2_CONFIRM2_SCAN_DELAY_MS'),'diagnostic tracing and injection are disabled')
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
