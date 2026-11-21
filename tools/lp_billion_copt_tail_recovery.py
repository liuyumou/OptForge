"""Readmit cleared non-overrun cleanup; execute only untouched frozen COPT cells."""
import argparse,time,subprocess
from lp_billion_common import BASE,ROOT,load,put,ref,resolve,require,NS,CPU_CAPS,GPU_CAPS,disk_bytes,DISK_LIMIT
from lp_billion_budget import accounting,run as reserve,cleared
from lp_billion_prepare_continue import job,completed
from lp_confirmation2_supervisor import same_process
from lp_billion_availability import stable,idle,observe,proof
from lp_billion_idle import Nvml
PYTHON=ROOT/'artifacts/gpup-copt-adapter-env/venv/bin/python'
FAILED='copt-nopresolve-1b-v1-2'
CPU='operational-cpu-v21';GPU='operational-gpu-v18'
PROTOCOL=ROOT/'docs/specifications/SPEC-0046-amendment-50.md'
MANIFEST=BASE/'copt-nopresolve-1b-v1/freeze.json'


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
    put(BASE/'operational-readmissions/v31.json',dict(status='prospective',cleanup_disposition=ref(disposition),
        admission_job=GPU,cpu_admission_job=CPU,protocol=ref(PROTOCOL),previous_plan=ref(BASE/'operational-readmissions/v30.json'),availability_window_seconds=300))
    f=load(MANIFEST);todo=[c for c in f['cells'] if c['status']=='pending' and not (BASE/'resources'/(c['id']+'.reservation.json')).exists()]
    require([c['family'] for c in todo]==['ill_scaled','degenerate'],'only two never-attempted scientific cells')
    cpu,gpu=accounting()
    require(cpu['admission']+1440*NS<=CPU_CAPS['admission']*NS and gpu['admission']+180*NS<=GPU_CAPS['admission']*NS,'whole fresh operational admission')
    require(cpu['development']+4*sum(c['seconds'] for c in todo)*NS<=CPU_CAPS['development']*NS and gpu['development']+sum(c['seconds'] for c in todo)*NS<=GPU_CAPS['development']*NS,'whole untouched solve tail')
    require(cpu['reporting']+(1920+4*sum(c['audit_seconds'] for c in f['cells'] if c['status']=='pending')+2400)*NS<=CPU_CAPS['reporting']*NS,'whole idle/audit/final reporting reserve')
    require(disk_bytes()+(sum(c['disk_gib'] for c in todo)+8)*(1<<30)<=DISK_LIMIT,'remaining storage')
    put(BASE/'copt-nopresolve-1b-tail-v1/plan.json',dict(status='frozen_untouched_tail',manifest=ref(MANIFEST),source=ref(__file__),protocol=ref(PROTOCOL),
        cleanup=ref(disposition),readmission=ref(BASE/'operational-readmissions/v31.json'),never_started=[c['id'] for c in todo],failed_not_retried=FAILED))
    print(dict(owned_identities_gone=len(identities),never_started=[c['id'] for c in todo]),flush=True)


def observation():
    out=BASE/'copt-tail-idle-v1';out.mkdir(exist_ok=False)
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
    plan=load(BASE/'copt-nopresolve-1b-tail-v1/plan.json');resolve(plan['source']);resolve(plan['manifest'])
    command=load(BASE/'resources/operational-cpu-v20.reservation.json')['command']
    job(CPU,180,command,phase='admission')
    job('copt-tail-idle-v1',480,['python3','-B',__file__,'observation'],phase='reporting',host=8)
    require(load(BASE/'copt-tail-idle-v1/result.json')['status']=='observed_idle','fresh complete idle window')
    observe(GPU);proof(GPU)
    job(GPU,180,['python3','-B',str(ROOT/'tools/lp_billion_admit.py'),'gpu','--id',GPU,'--version','2'],gpu=True)
    f=load(MANIFEST)
    for index,c in enumerate(f['cells']):
        if c['status']!='pending':continue
        previous=BASE/'resources'/(c['id']+'.reservation.json')
        if previous.exists():
            require(c['id']==FAILED,'no other original cell may be repeated')
            cleared(previous.with_name(c['id']+'.settlement.json'),True,'development','copt-untouched-tail')
        else:
            require(c['id'] in plan['never_started'],'frozen never-attempted cell only')
            s=reserve(c['id'],'development',c['seconds'],True,[str(PYTHON),'-B',str(resolve(f['source'])),'worker','--manifest',str(MANIFEST),'--index',str(index)],128,80,c['disk_gib'])
            print(dict(cell=c['id'],settlement=s),flush=True);require(s['cleanup_empty'] and not s['overrun'],'cleanup/overrun stops continuation')
        audit=c['id']+'-full-audit'
        require(not (BASE/'resources'/(audit+'.reservation.json')).exists(),'audit is never-started')
        s=reserve(audit,'reporting',c['audit_seconds'],False,[str(PYTHON),'-B',str(resolve(f['audit'])),str(MANIFEST),str(index)],64,0,c['disk_gib'])
        print(dict(audit=audit,settlement=s),flush=True);require(s['status']=='passed','independent audit passed')
    put(MANIFEST.parent/'completed.json',dict(status='all_supported_cells_attempted_and_available_endpoints_audited',freeze=ref(MANIFEST),tail=ref(BASE/'copt-nopresolve-1b-tail-v1/plan.json')))
    put(BASE/'copt-nopresolve-1b-tail-v1/completed.json',dict(status='complete',plan=ref(BASE/'copt-nopresolve-1b-tail-v1/plan.json'),completion=ref(MANIFEST.parent/'completed.json')))
    job('full-billion-delivery-v1',120,[str(PYTHON),'-B',str(ROOT/'tools/lp_billion_full_delivery.py')],phase='reporting',host=8)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['plan','observation','execute']);a=p.parse_args();globals()[a.action]()
