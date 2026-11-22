"""Readmit cleared non-overrun cleanup; execute only untouched frozen assessment/control cells."""
import argparse,time,subprocess
from lp_billion_common import BASE,ROOT,load,put,ref,resolve,require,NS,CPU_CAPS,GPU_CAPS,disk_bytes,DISK_LIMIT
from lp_billion_budget import accounting,run as reserve,cleared
from lp_billion_prepare_continue import job,completed
from lp_confirmation2_supervisor import same_process
from lp_billion_availability import stable,idle,observe,proof
from lp_billion_idle import Nvml
PYTHON=ROOT/'artifacts/gpup-copt-adapter-env/venv/bin/python'
FAILED='gpu-control-1b-v1-1-v11'
CPU='operational-cpu-v29';GPU='operational-gpu-v23'
PROTOCOL=ROOT/'docs/specifications/SPEC-0046-amendment-72.md'
MANIFEST=BASE/'gpu-control-1b-v1/freeze.json'


def plan():
    path=BASE/'resources'/(FAILED+'.settlement.json');s=load(path)
    require(not s['overrun'] and not s['cleanup_empty'] and s['status']=='refused','exact non-overrun cleanup failure')
    resource=load(resolve(s['resource']));journal=BASE/'resources'/(FAILED+'.cpu-journal.json')
    identities={}
    def collect(v):
        if isinstance(v,dict):
            if 'pid' in v and 'start_ticks' in v:identities[(v['pid'],v['start_ticks'])]=v
            for x in v.values():collect(x)
        elif isinstance(v,list):
            for x in v:collect(x)
    collect(resource);collect(load(journal))
    require(identities and not any(same_process(v) for v in identities.values()),'every exact retained owned identity gone')
    disposition=BASE/'resources'/(FAILED+'.cleanup-disposition.json')
    put(disposition,dict(status='cleanup_verified',settlement=ref(path),resource=s['resource'],journal=ref(journal),
        identities=list(identities.values()),signals_sent=False,admission_job=GPU,cpu_admission_job=CPU,protocol=ref(PROTOCOL),source=ref(__file__)))
    put(BASE/'operational-readmissions/v53.json',dict(status='prospective',cleanup_disposition=ref(disposition),
        admission_job=GPU,cpu_admission_job=CPU,protocol=ref(PROTOCOL),previous_plan=ref(BASE/'operational-readmissions/v52.json'),availability_window_seconds=300))
    f=load(MANIFEST);todo=[c for c in f['cells'] if c['status']=='pending' and not (BASE/'resources'/(c['id']+'.reservation.json')).exists()]
    require([c['family'] for c in todo]==['tall','coupled_blocks','ill_scaled','degenerate'],'only four never-attempted scientific cells')
    cpu,gpu=accounting()
    require(cpu['admission']+3120*NS<=CPU_CAPS['admission']*NS and gpu['admission']+120*NS<=GPU_CAPS['admission']*NS,'whole fresh operational admission')
    require(cpu['development']+4*sum(c['seconds'] for c in todo)*NS<=CPU_CAPS['development']*NS and gpu['development']+sum(c['seconds'] for c in todo)*NS<=GPU_CAPS['development']*NS,'whole untouched solve tail')
    require(cpu['reporting']+(240+4*sum(c['audit_seconds'] for c in todo)+2400)*NS<=CPU_CAPS['reporting']*NS,'whole idle/audit/final reporting reserve')
    require(disk_bytes()+(sum(__import__('math').ceil(c['memory']['endpoint_bytes_upper']/(1<<30))+1 for c in todo)+8)*(1<<30)<=DISK_LIMIT,'remaining storage')
    put(BASE/'gpu-control-untouched-tail-v1/plan.json',dict(status='frozen_untouched_tail',manifest=ref(MANIFEST),source=ref(__file__),protocol=ref(PROTOCOL),
        cleanup=ref(disposition),readmission=ref(BASE/'operational-readmissions/v53.json'),never_started=[c['id'] for c in todo],failed_not_retried=FAILED))
    print(dict(owned_identities_gone=len(identities),never_started=[c['id'] for c in todo]),flush=True)


def observation():
    out=BASE/'gpu-control-tail-idle-v1';out.mkdir(exist_ok=False)
    sensor=Nvml();samples=[];start=time.monotonic();ready=False
    try:
        for i in range(8):
            if i:
                target=start+60*i
                while time.monotonic()<target:time.sleep(min(1,target-time.monotonic()))
            s=sensor.sample();p=BASE/'availability'/GPU/(str(s['start_ns'])+'.json');put(p,s);samples.append(ref(p))
            ready=stable([load(resolve(p)) for p in samples],time.monotonic_ns())
            print(dict(sample=i,idle=idle(s),used_gib=s['used']/2**30,ready=ready),flush=True)
            if ready:break
        put(out/'result.json',dict(status='observed_idle' if ready else 'idle_gate_not_met',samples=samples,source=ref(__file__)))
    finally:sensor.close()


def execute():
    plan=load(BASE/'gpu-control-untouched-tail-v1/plan.json');resolve(plan['source']);resolve(plan['manifest'])
    command=load(BASE/'resources/operational-cpu-v28.reservation.json')['command']
    job(CPU,180,command,phase='admission')
    job('gpu-control-tail-idle-v1',480,[str(PYTHON),'-B',str(ROOT/'tools/lp_mixed2_reuse_place.py'),str(PYTHON),'-B',__file__,'observation'],phase='admission',host=8)
    require(load(BASE/'gpu-control-tail-idle-v1/result.json')['status']=='observed_idle','fresh complete idle window')
    observe(GPU);proof(GPU)
    job(GPU,120,['python3','-B',str(ROOT/'tools/lp_billion_admit.py'),'gpu','--id',GPU,'--version','2'],gpu=True)
    import math
    f=load(MANIFEST)
    for index,c in enumerate(f['cells']):
        if c['status']!='pending':continue
        previous=BASE/'resources'/(c['id']+'.reservation.json')
        audit=c['id']+'-full-audit'
        if previous.exists():
            if c['id']!=FAILED:
                require(completed(c['id']) and completed(audit),'previous successful cell and audit retained')
                continue
            cleared(previous.with_name(c['id']+'.settlement.json'),True,'development','gpu-control-untouched-tail')
        else:
            require(c['id'] in plan['never_started'],'frozen never-attempted cell only')
            m=c['memory']
            s=reserve(c['id'],'development',c['seconds'],True,[str(PYTHON),'-B',str(resolve(f['source'])),'worker','--manifest',str(MANIFEST),'--index',str(index)],m['host_gib'],m['device_gib'],math.ceil(m['endpoint_bytes_upper']/(1<<30))+1)
            print(dict(cell=c['id'],settlement=s),flush=True);require(s['cleanup_empty'] and not s['overrun'],'cleanup/overrun stops continuation')
        require(not (BASE/'resources'/(audit+'.reservation.json')).exists(),'audit is never-started')
        missing=c['id']==FAILED
        command=[str(PYTHON),'-B',str(resolve(f['audit'])),str(MANIFEST),str(index)]
        if missing:command=[str(PYTHON),'-B',str(ROOT/'tools/lp_mixed2_reuse_place.py'),*command]
        s=reserve(audit,'reporting',60 if missing else c['audit_seconds'],False,command,8 if missing else c['audit_host_gib'],0,1 if missing else math.ceil(8*load(resolve(c['model_result']))['rows']/(1<<30))+1)
        print(dict(audit=audit,settlement=s),flush=True);require(s['status']=='passed','independent audit or missing-endpoint record passed')
    put(MANIFEST.parent/'completed.json',dict(status='all_supported_cells_attempted_and_available_endpoints_audited',freeze=ref(MANIFEST),tail=ref(BASE/'gpu-control-untouched-tail-v1/plan.json')))
    put(BASE/'gpu-control-untouched-tail-v1/completed.json',dict(status='complete',plan=ref(BASE/'gpu-control-untouched-tail-v1/plan.json'),completion=ref(MANIFEST.parent/'completed.json')))
    from lp_billion_gpu_control_continue import measure
    measure()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['plan','observation','execute']);a=p.parse_args();globals()[a.action]()
