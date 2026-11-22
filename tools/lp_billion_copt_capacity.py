"""Prospective COPT capacity ladder with original-model checks and no cell repeats."""
import argparse,json,math,subprocess,time
from pathlib import Path
from lp_billion_common import BASE,ROOT,put,load,ref,resolve,require,CPU_CAPS,GPU_CAPS,NS
from lp_billion_budget import accounting
from lp_billion_prepare_continue import job
from lp_billion_copt_run import installation
from lp_general_oracle import settings
PYTHON=ROOT/'artifacts/gpup-copt-adapter-env/venv/bin/python'


def freeze(tag):
    paths=sorted(BASE.glob(f'models-{tag}-*-v1/result.json'))
    require(len(paths)==(6 if tag=='64m' else 2),'complete capacity family roster')
    cells=[]
    for i,p in enumerate(paths):
        m=load(p)
        lanes=['copt-cpu-auto','copt-gpu-pdlp'] if i%2==0 else ['copt-gpu-pdlp','copt-cpu-auto']
        if tag=='512m':lanes=['copt-gpu-pdlp']
        for lane in lanes:
            cells.append(dict(id=f'copt-capacity-{tag}-v1-{i}-{lane}',model=m['model'],model_result=ref(p),family=m['family'],lane=lane,
                wall_seconds=30 if tag=='64m' else 60 if tag=='256m' else 120,
                seconds=100 if tag=='64m' else 240 if tag=='256m' else 360,host_gib=128,device_gib=80 if lane=='copt-gpu-pdlp' else 0,
                memory_mb=48000.,disk_gib=3))
    cpu,gpu=accounting();planned=sum(c['seconds'] for c in cells)
    require(cpu['admission']+4*planned*NS<=CPU_CAPS['admission']*NS,'complete current COPT admission stage CPU reserve')
    require(gpu['admission']+sum(c['seconds'] for c in cells if c['device_gib'])*NS<=GPU_CAPS['admission']*NS,'COPT admission stage GPU reserve')
    put(BASE/f'copt-capacity-{tag}-v1/freeze.json',dict(status='frozen_capacity_admission_only',cells=cells,
        adapter=ref(ROOT/'tools/lp_billion_copt_run.py'),source=ref(__file__),installation=installation(),
        protocol=ref(ROOT/'docs/specifications/SPEC-0046-amendment-40.md'),strict_original_tolerance=1e-9))


def worker(tag,index):
    freeze_path=BASE/f'copt-capacity-{tag}-v1/freeze.json';f=load(freeze_path);c=f['cells'][index]
    require(f['adapter']==ref(ROOT/'tools/lp_billion_copt_run.py') and f['installation']==installation(),'capacity source/library binding')
    out=BASE/c['id'];out.mkdir(exist_ok=False);response=out/'response.json'
    start=time.monotonic_ns();p=subprocess.run([str(PYTHON),'-B',str(ROOT/'tools/lp_billion_copt_run.py'),str(resolve(c['model'])),str(response),
        '--wall-seconds',str(c['wall_seconds']),'--memory-mb',str(c['memory_mb']),'--admission',*(['--gpu'] if c['device_gib'] else [])],text=True,capture_output=True)
    process_ns=time.monotonic_ns()-start;(out/'stdout').write_text(p.stdout);(out/'stderr').write_text(p.stderr)
    require(p.returncode==0,'capacity COPT process '+p.stderr[-2000:]);r=load(response)
    require(r['model_sha256']==c['model']['sha256'] and r['nonzeros']==load(resolve(c['model_result']))['nonzeros'],'capacity original model')
    proof=None;check_ns=0
    if r['has_solution']:
        request=dict(settings=settings('native'),endpoint=r['endpoint']);put(out/'check-request.json',request)
        start=time.monotonic_ns();p=subprocess.run([str(BASE/'image-v1/executor'),'assess',str(resolve(c['model'])),str(BASE)],input=json.dumps(request)+'\n',text=True,capture_output=True)
        check_ns=time.monotonic_ns()-start;(out/'check-stdout').write_text(p.stdout);(out/'check-stderr').write_text(p.stderr)
        require(p.returncode==0,'capacity strict checking '+p.stderr[-2000:]);proof=json.loads(p.stdout)
        require(proof['model_sha256']==c['model']['sha256'],'strict original model binding');put(out/'check.json',proof)
    require(r['profile']['total_ns']<=process_ns,'capacity cost intervals')
    costs=dict(r['profile']['exclusive_ns'],process_imports_serialization_cleanup=process_ns-r['profile']['total_ns'],independent_final_check=check_ns)
    require(sum(costs.values())==process_ns+check_ns,'capacity complete cost coverage')
    put(out/'result.json',dict(status='passed',response=ref(response),freeze=ref(freeze_path),strict_certified=bool(proof and proof['accepted']),
        check=ref(out/'check.json') if proof else None,process_ns=process_ns,final_check_ns=check_ns,complete_ns=process_ns+check_ns,exclusive_ns=costs,
        gpu_confirmed=r['gpu_confirmed'],has_solution=r['has_solution'],vendor_status=r['status'],host_memory=r['host_memory']))
    print(dict(cell=c['id'],gpu_confirmed=r['gpu_confirmed'],strict_accepted=bool(proof and proof['accepted']),seconds=(process_ns+check_ns)/1e9),flush=True)


def execute(tag):
    path=BASE/f'copt-capacity-{tag}-v1/freeze.json'
    require(path.exists(),'prospective capacity freeze')
    for i,c in enumerate(load(path)['cells']):
        require(not (BASE/'resources'/(c['id']+'.reservation.json')).exists(),'attempted capacity cell cannot repeat')
        # Use budget.run directly to preserve the full 80 GiB vendor allowance.
        from lp_billion_budget import run
        result=run(c['id'],'admission',c['seconds'],bool(c['device_gib']),[str(PYTHON),'-B',__file__,'worker','--tag',tag,'--index',str(i)],c['host_gib'],c['device_gib'],c['disk_gib'])
        print(dict(cell=c['id'],settlement=result),flush=True);require(result['status']=='passed','retain capacity interruption without retry')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','worker','execute']);p.add_argument('--tag',choices=['64m','256m','512m'],required=True);p.add_argument('--index',type=int);a=p.parse_args()
    if a.action=='worker':worker(a.tag,a.index)
    else:globals()[a.action](a.tag)
