"""Finish the untouched three-cell tail with prospectively smaller host stops."""
import argparse
import copy
import math
import time
from pathlib import Path
from lp_billion_common import BASE, ROOT, NS, CPU_CAPS, GPU_CAPS, load, put, ref, resolve, require
from lp_billion_budget import accounting, run
from lp_billion_prepare_continue import completed, job
from lp_billion_readmission import CPU, GPU
from lp_billion_copt_fair_run import PYTHON, cleanup
import lp_billion_copt_fair_native_tail as previous

MANIFEST=BASE/'copt-fair-headroom-tail-v1/freeze.json'
CONTRACTS='copt-fair-headroom-contracts-v1'
IDLE='copt-fair-headroom-idle-v1'
PRUNE='copt-fair-ill-scaled-endpoint-prune-v1'
PROTOCOL=ROOT/'docs/specifications/SPEC-0046-amendment-88.md'
CELL='copt-fair-1b-v1-ill_scaled-project'


def available():
    return int(next(v.split()[1] for v in Path('/proc/meminfo').read_text().splitlines() if v.startswith('MemAvailable:')))*1024


def smaller(cell):
    value=copy.deepcopy(cell)
    require(value['status']=='pending' and value['lane']=='copt-gpu-pdlp' and value['family'] in ['ill_scaled','degenerate'],'only untouched vendor declarations')
    m=value['memory'];require(m['admitted'] and m['host_gib']==128 and m['host_bytes']==128<<30,'original admitted host reservation')
    require(m['empirical_host_peak_with_allowance']<=112<<30,'retain at least eight GiB beyond the already padded forecast')
    m.update(host_gib=120,host_bytes=120<<30,previous_host_gib=128,host_reservation_protocol=ref(PROTOCOL))
    return value


def plan():
    cpu=dict(admission=960,development=36000,reporting=34000,cleanup=720);gpu=dict(development=8100);c,g=accounting()
    require(all(c[k]+v*NS<=CPU_CAPS[k]*NS for k,v in cpu.items()),'whole remaining CPU reservation')
    require(all(g[k]+v*NS<=GPU_CAPS[k]*NS for k,v in gpu.items()),'whole remaining GPU reservation')
    return dict(cpu=cpu,gpu=gpu,remaining_after_cpu_seconds={k:CPU_CAPS[k]-c[k]/NS-v for k,v in cpu.items()},
                remaining_after_gpu_seconds={k:GPU_CAPS[k]-g[k]/NS-v for k,v in gpu.items()})


def removable(documents, protected):
    from lp_billion_portable import arrays
    excluded={c['sha256'] for d in protected for a in arrays(d) for c in a['chunks']}
    chunks={c['sha256']:c['bytes'] for d in documents for a in arrays(d) for c in a['chunks']}
    return {sha:size for sha,size in chunks.items() if sha not in excluded and size>=8<<20}


def prune():
    require(completed(CELL+'-full-audit'),'every project endpoint is independently audited')
    f=load(previous.MANIFEST);response=BASE/CELL/'response.json';proof=BASE/(CELL+'-full-audit/result.json');audit=load(proof)
    require(audit['status']=='passed' and audit['response']==ref(response),'exact completed proof binding')
    models={c['model_result']['path']:c['model_result'] for c in f['cells']};protected=[]
    for item in models.values():
        result=load(resolve(item));protected.extend([load(resolve(result['model'])),load(resolve(result['construction']))])
    documents=[load(response),load(BASE/(CELL+'-full-audit/requests.json'))]
    deleted=[];root=BASE/'objects'
    for sha,size in removable(documents,protected).items():
        require(len(sha)==64 and all(c in '0123456789abcdef' for c in sha),'owned content-addressed endpoint')
        path=root/(sha+'.bin')
        if not path.exists():continue
        require(not path.is_symlink() and path.resolve().parent==root.resolve() and path.stat().st_size==size,'exact obsolete endpoint object')
        path.unlink();deleted.append(dict(sha256=sha,bytes=size))
    put(BASE/(PRUNE+'.json'),dict(status='audited_endpoint_objects_deleted',deleted=deleted,released_bytes=sum(c['bytes'] for c in deleted),
        preserved_models=list(models.values()),audit=ref(proof),source=ref(__file__),protocol=ref(PROTOCOL),replay_requires_regeneration=True))
    print(dict(released_gib=sum(c['bytes'] for c in deleted)/(1<<30),host_available_gib=available()/(1<<30)),flush=True)


def freeze():
    require(completed(CPU) and completed(GPU) and completed(CONTRACTS) and completed(PRUNE),'operational, harness and completed audit cleanup')
    require(not MANIFEST.exists(),'fresh three-cell effective manifest');f=load(previous.MANIFEST);resolve(f['resumption_source'])
    tail=[c['id'] for c in f['cells'] if c['status']=='pending' and not (BASE/'resources'/(c['id']+'.reservation.json')).exists()]
    require(tail==['copt-fair-1b-v1-ill_scaled-copt','copt-fair-1b-v1-degenerate-copt','copt-fair-1b-v1-degenerate-project'],'exact untouched three-cell tail')
    value=copy.deepcopy(f);value['cells']=[smaller(c) if c['id'] in tail and c['lane']=='copt-gpu-pdlp' else c for c in value['cells']]
    for before,after in zip(f['cells'],value['cells']):
        require({k:v for k,v in before.items() if k!='memory'}=={k:v for k,v in after.items() if k!='memory'},'every native request, allowance and model remains exact')
    for item in load(BASE/'gpu-control-settled-checkpoint-v1.json')['numerical_bindings']:resolve(item)
    value.update(previous_effective_freeze=ref(previous.MANIFEST),resumption_source=ref(__file__),host_reservation_protocol=ref(PROTOCOL),
        remaining_three=tail,reservation=plan(),contracts=ref(BASE/'resources'/(CONTRACTS+'.settlement.json')),
        endpoint_cleanup=ref(BASE/(PRUNE+'.json')),completed_project_audit=ref(BASE/(CELL+'-full-audit/result.json')))
    put(MANIFEST,value);print(dict(remaining=tail,reservation=value['reservation']),flush=True)


def observation():
    from lp_billion_availability import observe,stable,proof
    out=BASE/IDLE;out.mkdir(exist_ok=False);start=time.monotonic();ready=False;host=[]
    for i in range(8):
        while time.monotonic()<start+i*60:time.sleep(min(1,start+i*60-time.monotonic()))
        observe(IDLE);host.append(dict(monotonic_ns=time.monotonic_ns(),available_bytes=available()))
        paths=sorted((BASE/'availability'/IDLE).glob('*.json'),key=lambda p:int(p.stem))
        ready=stable([load(p) for p in paths],time.monotonic_ns()) and host[-1]['available_bytes']>=124<<30
        if ready:proof(IDLE);break
    put(out/'result.json',dict(status='capacity_and_idle_passed' if ready else 'capacity_or_idle_not_met',host_samples=host,
        required_host_available_bytes=124<<30,gpu_samples=[ref(p) for p in paths],source=ref(__file__)))


def execute():
    require(all(completed(i) for i in [CPU,GPU,CONTRACTS,PRUNE,IDLE]),'all exact operational and fresh capacity gates')
    require(load(BASE/IDLE/'result.json')['status']=='capacity_and_idle_passed','current host and sustained GPU idle admission')
    f=load(MANIFEST);resolve(f['resumption_source']);plan()
    require(not (MANIFEST.parent/'completed.json').exists(),'never repeat completed tail')
    for identity in f['remaining_three']:require(not (BASE/'resources'/(identity+'.reservation.json')).exists(),'never repeat an attempted LP')
    for family in ['ill_scaled','degenerate']:
        if family=='degenerate':job('copt-fair-regenerate-1b-degenerate-v1',900,[str(PYTHON),'-B',str(ROOT/'tools/lp_billion_copt_fair_native_tail.py'),'regenerate','--family',family],phase='development',host=32,disk=40)
        for i,c in enumerate(f['cells']):
            if c['id'] not in f['remaining_three'] or c['family']!=family:continue
            m=c['memory'];disk=c.get('disk_gib',math.ceil(m.get('endpoint_bytes_upper',0)/(1<<30))+1)
            s=run(c['id'],'development',2700,True,[str(PYTHON),'-B',str(resolve(f['source'])),'worker','--manifest',str(MANIFEST),'--index',str(i)],m['host_gib'],m['device_gib'],disk)
            print(dict(cell=c['id'],settlement=s),flush=True);require(s['cleanup_empty'] and not s['overrun'],'cleanup/overrun stops the tail')
            name=c['id']+'-full-audit';a=run(name,'reporting',c['audit_seconds'],False,[str(PYTHON),'-B',str(resolve(f['audit'])),str(MANIFEST),str(i)],64,0,math.ceil(8*load(resolve(c['model_result']))['rows']/(1<<30))+1)
            print(dict(audit=name,settlement=a),flush=True);require(a['status']=='passed','complete strict proof coverage')
        job('copt-fair-prune-1b-'+family+'-v1',60,[str(PYTHON),'-B',str(ROOT/'tools/lp_mixed2_reuse_place.py'),str(PYTHON),'-B',str(ROOT/'tools/lp_billion_copt_fair_run.py'),'cleanup','--scale','1b','--family',family],phase='cleanup',host=8)
    put(MANIFEST.parent/'completed.json',dict(status='all_remaining_cells_attempted_and_audited',manifest=ref(MANIFEST)))
    put(previous.MANIFEST.parent/'completed.json',dict(status='all_four_cells_attempted_and_audited',effective_freeze=ref(MANIFEST)))
    put(previous.ORIGINAL.parent/'completed.json',dict(status='all_admitted_cells_attempted_and_audited',original_freeze=ref(previous.ORIGINAL),effective_freeze=ref(MANIFEST)))
    job('copt-fair-complete-report-v1',180,[str(PYTHON),'-B',str(ROOT/'tools/lp_mixed2_reuse_place.py'),str(PYTHON),'-B',__file__,'report'],phase='reporting',host=8)


def report():
    # Reuse the exact admitted reporting logic with the explicitly bound effective
    # manifest. This changes no numerical worker, endpoint or proof classification.
    previous.MANIFEST=MANIFEST
    previous.report()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prune','freeze','observation','execute','report']);a=p.parse_args();globals()[a.action]()
