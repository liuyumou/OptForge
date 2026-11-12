"""SPEC-0033 same-executable delivery comparison; immutable arithmetic/evidence."""
import argparse
import os
from pathlib import Path
import time
import lp_fp4_accel_run as transport
from lp_delivery2_transport import deliver
from lp_delivery2_common import ROOT,BASE,put,ref,load,require
from lp_delivery2_cpu import BINARY

PARENT=ROOT/'artifacts/gpup-fp4-accel-v1/study-v1'
ORIGINAL=ROOT/'research/lp-fp4-accel/target/release/lp-fp4-accel'
LANES=('nativefast','gridfp4x2')
TIERS=('certified-1e-7','certified-1e-9')


def canonical(value):
    if isinstance(value,dict):
        return {k:canonical(v) for k,v in value.items() if k not in ('checker_binary_sha256','gpu_us')}
    if isinstance(value,list):return [canonical(v) for v in value]
    return value


def numerical(result):
    return canonical({k:result[k] for k in ('endpoint','certificate','audits','checkpoint','events','physical','logical',
        'attempted','status','certified','terminal','final_lane','representation','row_scale','shift','image_sha256','model_sha256')})


def bits(value):
    import struct
    if isinstance(value,float):return ('binary64',struct.pack('!d',value).hex())
    if isinstance(value,dict):return {k:bits(v) for k,v in value.items()}
    if isinstance(value,list):return [bits(v) for v in value]
    return value


def delivery_mode(mode):
    if mode=='original':os.environ['GPUP_DELIVERY2_CONTROL']='1'
    else:os.environ.pop('GPUP_DELIVERY2_CONTROL',None)


def matches(result,old,binary):
    require(result['checker_binary_sha256']==binary['sha256'],'wrong independent checker executable')
    require(result['certificate']['checker_binary_sha256']==binary['sha256'],'wrong terminal checker binding')
    require(all(a['certificate']['checker_binary_sha256']==binary['sha256'] for a in result['audits']),'wrong audit checker binding')
    require(bits(numerical(result))==bits(numerical(old)),'changed endpoint, certificate, audit, work, recovery or checkpoint')
    require(sum(result['costs_ns'].values())==result['solve_ns'],'nonexclusive phase accounting')


def freeze(directory,smoke=False):
    out=Path(directory);out.mkdir(parents=True,exist_ok=False)
    parent=load(PARENT/'manifest.json')
    require(ref(ORIGINAL)==parent['binary'],'changed baseline binary')
    require(load(BASE/'resources/cpu-acceptance-v1.settlement.json')['status']=='passed','CPU software admission')
    require(load(BASE/'resources/native-gate-v2.settlement.json')['status']=='passed','full native admission')
    require(load(BASE/'resources/software-tail-v1.settlement.json')['status']=='passed','delivery failure regression')
    cpu_manifest=load(BASE/'cpu-v1/manifest.json')
    require(ref(BINARY)==cpu_manifest['binary'],'CPU-admitted binary changed')
    profile=load(BASE/'cpu-v1/result.json')
    require(profile['status']=='passed' and profile['endpoints']==102,'CPU endpoint admission')
    cells=[];families=list(parent['models'])
    if smoke:families=['coupled-equality','dense-generic-512','ill-scaled-generic-128','infinite-bound-refusal']
    for lifecycle in (('prepared',) if smoke else ('prepared','cold')):
        for family in families:
            for tier in TIERS:
                for repetition in range(1 if smoke else 5):
                    for checker in (('original','optimized') if repetition%2==0 else ('optimized','original')):
                        for lane in (LANES if repetition%2==0 else LANES[::-1]):
                            ident=f'{lifecycle}-{family}-{tier}-{repetition}-{checker}-{lane}'
                            old=next(c for c in parent['cells'] if c['lifecycle']==lifecycle and c['family']==family and c['tier']==tier and c['repetition']==repetition and c['lane']==lane)
                            cells.append(dict(id=ident,lifecycle=lifecycle,family=family,tier=tier,repetition=repetition,checker=checker,lane=lane,original_result=ref(PARENT/(old['id']+'.json'))))
    sources=[ref(p) for p in sorted((ROOT/'research/lp-delivery2/src').glob('*.rs'))]
    sources+=[ref(p) for p in sorted((ROOT/'tools').glob('lp_delivery2*.py'))]
    sources+=[ref(p) for p in sorted((ROOT/'research/lp-delivery2').glob('Cargo.*'))]
    sources += [ref(ROOT/'docs/specifications/SPEC-0033-delivery2.md'),ref(ROOT/'docs/decisions/ADR-0065-delivery2.md')]
    sources += [ref(p) for p in sorted((ROOT/'research/lp-fp4-checker/src').glob('*.rs'))]
    put(out/'manifest.json',dict(kind='gpup-delivery2-v1',smoke=smoke,parent=ref(PARENT/'manifest.json'),
        cpu_admission=ref(BASE/'cpu-v1/result.json'),image=parent['image'],models=parent['models'],settings=parent['settings'],
        binaries=dict(original=ref(BINARY),optimized=ref(BINARY)),sources=sources,cells=cells,automatic_retry=False))
    print(dict(frozen=len(cells),directory=str(out)),flush=True)


def execute(directory):
    out=Path(directory);m=load(out/'manifest.json');parent=load(ROOT/m['parent']['path'])
    for binding in [m['parent'],m['cpu_admission'],m['image'],*m['models'].values(),*m['binaries'].values(),*m['sources'],*parent['sources']]:
        require(ref(ROOT/binding['path'])==binding,'changed frozen source/input')
    if not m['smoke']:
        require(load(BASE/'smoke-v1/result.json')['status']=='complete','device/transport admission incomplete')
        require(load(BASE/'lifecycle-v1/result.json')['status']=='passed','lifecycle admission incomplete')
        require(load(BASE/'resources/device-acceptance-v1.settlement.json')['status']=='passed','device reservation not settled')
    require('GPUP_CHECKER_ORIGINAL' not in os.environ,'unexpected checker override')
    require(not (out/'STARTED.json').exists(),'cohort already started');put(out/'STARTED.json',dict(manifest=ref(out/'manifest.json')))
    rows=[];setups=[];teardowns=[];services={};active_family=None;cell=None
    def close_services():
        for mode,service in services.items():
            before=time.monotonic_ns();service.close()
            teardowns.append(dict(family=active_family,checker=mode,ns=time.monotonic_ns()-before))
    try:
        for cell in m['cells']:
            if cell['family']!=active_family or cell['lifecycle']=='cold':
                close_services()
                services={};active_family=cell['family']
            binary=m['binaries'][cell['checker']];dest=out/(cell['id']+'.json');delivery_mode(cell['checker'])
            if cell['lifecycle']=='prepared':
                if cell['checker'] not in services:
                    transport.BINARY=ROOT/binary['path'];start=time.monotonic_ns()
                    service=transport.Service(ROOT/m['image']['path'],ROOT/m['models'][cell['family']]['path'],out/(cell['family']+'-'+cell['checker']+'.log'))
                    ready=time.monotonic_ns()-start;prep=[]
                    for lane in LANES:
                        t=time.monotonic_ns();value=service.call('prepare',lane=lane);prep.append(dict(lane=lane,ns=time.monotonic_ns()-t,result=value))
                    setups.append(dict(family=cell['family'],checker=cell['checker'],ready_ns=ready,prepare=prep,total_ns=time.monotonic_ns()-start))
                    services[cell['checker']]=service
                result,elapsed=services[cell['checker']].solve_to_file(dest,lane=cell['lane'],tier=cell['tier'],**m['settings'])
            else:
                request=out/(cell['id']+'.request.json');put(request,dict(op='solve',lane=cell['lane'],tier=cell['tier'],**m['settings']))
                elapsed=deliver([str(ROOT/binary['path']),'once',str(ROOT/m['image']['path']),str(ROOT/m['models'][cell['family']]['path']),str(request)],dest,out/(cell['id']+'.stderr'),35)
                result=load(dest)
            require(ref(ROOT/cell['original_result']['path'])==cell['original_result'],'changed old cell')
            matches(result,load(ROOT/cell['original_result']['path']),binary)
            require(elapsed>=result['solve_ns'],'invalid complete boundary')
            rows.append(dict(**cell,complete_ns=elapsed,solve_ns=result['solve_ns'],setup_ns=result['setup_ns'],costs_ns=result['costs_ns'],
                gpu_us=result['gpu_us'],physical=result['physical'],certified=result['certified'],status=result['status'],result=ref(dest)))
            if len(rows)%40==0:print(dict(completed=len(rows),planned=len(m['cells'])),flush=True)
        close_services()
        services={}
    except Exception as exc:
        put(out/'partial.json',dict(status='failed',error=str(exc),failed_cell=cell,rows=rows,setups=setups,teardowns=teardowns,unexecuted=[c for c in m['cells'] if c['id'] not in {r['id'] for r in rows} and c['id']!=cell['id']]))
        raise
    finally:
        for service in services.values():
            service.close()
    put(out/'result.json',dict(status='complete',manifest=ref(out/'manifest.json'),rows=rows,setups=setups,teardowns=teardowns,
        exact_all_audits_endpoints_certificates_recoveries_checkpoints_and_physical_work=True))
    print(dict(completed=len(rows),certified=sum(r['certified'] for r in rows)),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','run']);p.add_argument('directory');p.add_argument('--smoke',action='store_true');a=p.parse_args()
    if a.action=='freeze':freeze(a.directory,a.smoke)
    else:execute(a.directory)
