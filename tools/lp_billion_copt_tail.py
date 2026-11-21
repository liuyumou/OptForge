"""Never-attempted COPT capacity cells with separate strict checks and child margins."""
import argparse,copy,math,time
from pathlib import Path
from lp_billion_common import BASE,ROOT,put,load,ref,resolve,require,CPU_CAPS,GPU_CAPS,NS
from lp_billion_budget import accounting,run
from lp_billion_owned_process import execute as child
from lp_billion_prepare_continue import completed
PYTHON=ROOT/'artifacts/gpup-copt-adapter-env/venv/bin/python'

def unattempted(cells,attempted):
    require(len({c['id'] for c in cells})==len(cells),'unique capacity cell identities')
    return [copy.deepcopy(c) for c in cells if c['id'] not in attempted]

def freeze(tag):
    require(completed('operational-cpu-v20') and completed('operational-gpu-v17'),'fresh operational capacity gates')
    require(completed('copt-tail-contracts-v1'),'fresh capacity-tail contracts')
    require(completed('copt-full-admission-v2'),'native COPT admission')
    old=None
    if tag=='64m':
        old=BASE/'copt-capacity-64m-v1/freeze.json';source=load(old)
        attempted={c['id'] for c in source['cells'] if (BASE/'resources'/(c['id']+'.reservation.json')).exists()}
        require(len(attempted)==3,'retain all three original capacity attempts')
        cells=unattempted(source['cells'],attempted)
        for c in cells:c['seconds']=300
    else:
        paths=sorted(BASE.glob(f'models-{tag}-*-v1/result.json'));require(len(paths)==2,'full capacity family roster')
        cells=[]
        for i,p in enumerate(paths):
            m=load(p);lanes=['copt-cpu-auto','copt-gpu-pdlp'] if i%2==0 else ['copt-gpu-pdlp','copt-cpu-auto']
            if tag=='512m':lanes=['copt-gpu-pdlp']
            for lane in lanes:
                cells.append(dict(id=f'copt-capacity-{tag}-v2-{i}-{lane}',model=m['model'],model_result=ref(p),family=m['family'],lane=lane,
                    wall_seconds=60 if tag=='256m' else 120,seconds=240 if tag=='256m' else 360,host_gib=128,
                    device_gib=80 if lane=='copt-gpu-pdlp' else 0,memory_mb=48000.,disk_gib=3))
    for c in cells:
        require(not (BASE/'resources'/(c['id']+'.reservation.json')).exists(),'attempted cell cannot be in tail')
        c['check_seconds']=90 if tag=='64m' else 180 if tag=='256m' else 300
    cpu,gpu=accounting()
    require(cpu['admission']+4*sum(c['seconds'] for c in cells)*NS<=CPU_CAPS['admission']*NS,'whole capacity stage CPU reserve')
    require(cpu['reporting']+4*sum(c['check_seconds'] for c in cells)*NS<=CPU_CAPS['reporting']*NS,'whole capacity final-check reserve')
    require(gpu['admission']+sum(c['seconds'] for c in cells if c['device_gib'])*NS<=GPU_CAPS['admission']*NS,'whole capacity GPU reserve')
    from lp_billion_copt_run import installation
    path=BASE/f'copt-capacity-{tag}-tail-v1/freeze.json'
    put(path,dict(status='frozen_capacity_admission_only',cells=cells,prior_freeze=ref(old) if old else None,
        source=ref(__file__),adapter=ref(ROOT/'tools/lp_billion_copt_run.py'),installation=installation(),checker=ref(BASE/'image-v1/executor'),
        audit=ref(ROOT/'tools/lp_billion_full_audit.py'),child=ref(ROOT/'tools/lp_billion_owned_process.py'),protocol=ref(ROOT/'docs/specifications/SPEC-0046-amendment-45.md')))
    print(dict(freeze=str(path),never_attempted_cells=len(cells)),flush=True)

def worker(manifest,index):
    f=load(manifest);c=f['cells'][index]
    from lp_billion_copt_run import installation
    require(f['source']==ref(__file__) and f['adapter']==ref(ROOT/'tools/lp_billion_copt_run.py') and f['installation']==installation(),'capacity source/library binding')
    resolve(f['child']);out=BASE/c['id'];out.mkdir(exist_ok=False);response=out/'response.json'
    result=child([str(PYTHON),'-B',str(ROOT/'tools/lp_billion_copt_run.py'),str(resolve(c['model'])),str(response),'--wall-seconds',str(c['wall_seconds']),
                  '--memory-mb',str(c['memory_mb']),'--admission',*(['--gpu'] if c['device_gib'] else [])],out/'stdout',out/'stderr',c['seconds']-30)
    put(out/'process.json',result)
    require(not result['timed_out'] and result['returncode']==0,'retained COPT child interruption; never retry')
    start=time.monotonic_ns();r=load(response)
    require(r['model_sha256']==c['model']['sha256'] and r['nonzeros']==load(resolve(c['model_result']))['nonzeros'],'capacity original model')
    process_ns=result['elapsed_ns'];require(process_ns>=r['profile']['total_ns'],'capacity process interval')
    measured=dict(status='measured',cell=c['id'],response=ref(response),freeze=ref(manifest),process_ns=process_ns,
        response_transport_ns=time.monotonic_ns()-start,solver_status=r['status'],certified=None,
        gpu_confirmed=r['gpu_confirmed'],has_solution=r['has_solution'],host_memory=r['host_memory'])
    measured['fresh_process_ns']=measured['process_ns']+measured['response_transport_ns'];put(out/'result.json',measured)
    print(dict(cell=c['id'],gpu_confirmed=r['gpu_confirmed'],status=r['status'],has_solution=r['has_solution'],seconds=measured['fresh_process_ns']/NS),flush=True)

def execute(tag):
    path=BASE/f'copt-capacity-{tag}-tail-v1/freeze.json';f=load(path);resolve(f['source']);resolve(f['audit'])
    for i,c in enumerate(f['cells']):
        reservation=BASE/'resources'/(c['id']+'.reservation.json')
        if reservation.exists():
            s=load(reservation.with_name(c['id']+'.settlement.json'))
            require(s['cleanup_empty'] and not s['overrun'],'failed cleanup/overrun stops capacity continuation')
            print(dict(cell=c['id'],status='retained_attempt_no_repeat'),flush=True)
        else:
            s=run(c['id'],'admission',c['seconds'],bool(c['device_gib']),[str(PYTHON),'-B',__file__,'worker','--manifest',str(path),'--index',str(i)],c['host_gib'],c['device_gib'],c['disk_gib'])
            print(dict(cell=c['id'],settlement=s),flush=True)
            require(s['cleanup_empty'] and not s['overrun'],'failed cleanup/overrun stops capacity continuation')
        response=BASE/c['id']/'response.json'
        if not response.exists() or not load(response)['has_solution']:continue
        check_id=c['id']+'-full-audit'
        if (BASE/'resources'/(check_id+'.reservation.json')).exists():
            require(completed(check_id),'retained failed audit requires explicit fresh disposition');continue
        check=run(check_id,'reporting',c['check_seconds'],False,[str(PYTHON),'-B',str(ROOT/'tools/lp_billion_full_audit.py'),str(path),str(i)],64,0,1)
        print(dict(check=check_id,settlement=check),flush=True);require(check['status']=='passed','strict capacity audit stopped')
    put(path.parent/'completed.json',dict(status='all_tail_cells_attempted',freeze=ref(path)))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','execute','worker']);p.add_argument('--tag',choices=['64m','256m','512m']);p.add_argument('--manifest',type=Path);p.add_argument('--index',type=int);a=p.parse_args()
    if a.action=='worker':worker(a.manifest,a.index)
    else:globals()[a.action](a.tag)
