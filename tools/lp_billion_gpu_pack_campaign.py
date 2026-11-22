"""New source-bound FP4 packing cohorts; all prior scientific attempts remain intact."""
import argparse,copy,json,math,resource,time
from pathlib import Path
from lp_billion_common import BASE,ROOT,put,load,ref,resolve,require,CPU_CAPS,GPU_CAPS,NS,DISK_LIMIT,disk_bytes
from lp_billion_budget import accounting,run
from lp_billion_prepare_continue import completed
from lp_billion_owned_process import execute as child
from lp_billion_campaign import endpoint_bytes
from lp_billion_gpu_pack_capacity import capacity
PYTHON=ROOT/'artifacts/gpup-copt-adapter-env/venv/bin/python'
AUDIT=ROOT/'tools/lp_billion_full_audit_v2.py'

def freeze(scale):
    manifest=BASE/f'gpu-pack-{scale}-v1/freeze.json';require(not manifest.exists(),'fresh packing cohort')
    for job in ['operational-cpu-v26','operational-gpu-v21','gpu-pack-contracts-v1','gpu-pack-seal-audit-v1',
                'gpu-pack-gpu-v1','gpu-pack-memcheck-v1','gpu-pack-racecheck-v1','gpu-pack-initcheck-v1','gpu-pack-synccheck-v1']:
        require(completed(job),'complete GPU packing admission '+job)
    image=load(BASE/'image-v10/binding.json')
    for item in image['files'].values():resolve(item)
    for item in load(resolve(image['source_manifest']))['sources']:
        if item['original']['path'].endswith(('.rs','.cu')) or Path(item['original']['path']).name.startswith('Cargo.'):
            resolve(item['original']);resolve(item['retained'])
    source=load(BASE/('ladder-64m-v3/freeze.json' if scale=='64m' else 'full-billion-v1/freeze.json'))
    previous=[c for c in source['cells'] if c['lane']=='fp4x2'];require(len(previous)==6,'all six families')
    cells=[]
    for i,old in enumerate(previous):
        model=load(resolve(old['model_result']));variants=(['v9','v10'] if i%2==0 else ['v10','v9']) if scale=='64m' else ['v10']
        for version in variants:
            c=copy.deepcopy(old);c.update(id=f'gpu-pack-{scale}-v1-{i}-{version}',family=model['family'],version=version,lane='fp4x2',
                image=ref(BASE/('image-'+version)/'binding.json'),memory=capacity(model),seconds=120 if scale=='64m' else old['seconds'],
                audit_seconds=120 if scale=='64m' else old['audit_seconds'],audit_host_gib=16 if scale=='64m' else old['audit_host_gib'])
            c['status']='pending' if c['memory']['admitted'] else 'unsupported_capacity'
            c['memory']['endpoint_bytes_upper']=endpoint_bytes(model,100 if scale=='64m' else 1000)
            c['request']['profile']=True
            if version=='v10':c['request']['fast']['gpu_packing']=True
            if scale=='64m':c['request']['settings'].update(iteration_limit=100,wall_ms=60000)
            require(not (BASE/'resources'/(c['id']+'.reservation.json')).exists(),'never-attempted cell')
            cells.append(c)
    active=[c for c in cells if c['status']=='pending'];cpu,gpu=accounting()
    seconds=sum(c['seconds'] for c in active);audits=sum(c['audit_seconds'] for c in active)
    require(cpu['development']+4*seconds*NS<=CPU_CAPS['development']*NS,'whole solve CPU reservation')
    require(gpu['development']+seconds*NS<=GPU_CAPS['development']*NS,'whole solve GPU reservation')
    require(cpu['reporting']+(4*audits+1200)*NS<=CPU_CAPS['reporting']*NS,'whole strict audit and completion CPU reservation')
    require(disk_bytes()+sum(c['memory']['endpoint_bytes_upper'] for c in active)+(4<<30)<=DISK_LIMIT,'whole storage including repaired witnesses')
    put(manifest,dict(status='frozen_development',scale=scale,cells=cells,source=ref(__file__),audit=ref(AUDIT),
        child=ref(ROOT/'tools/lp_billion_owned_process.py'),capacity=ref(ROOT/'tools/lp_billion_gpu_pack_capacity.py'),
        checker=ref(BASE/'image-v1/executor'),candidate_image=ref(BASE/'image-v10/binding.json'),
        protocol=ref(ROOT/'docs/specifications/SPEC-0046-amendment-54.md'),allocation=ref(BASE/'approved-packing-transfer-v2.json'),
        historical_control=ref(BASE/'full-billion-v1/freeze.json') if scale=='1b' else None,
        reservation=dict(solve_cpu_seconds=4*seconds,solve_gpu_seconds=seconds,audit_cpu_seconds=4*audits),
        claim='All six families; fresh rotated paired 64 M cells; billion comparison to retained v9 is descriptive historical timing.'))
    print(dict(frozen=str(manifest),cells=len(cells),gpu_seconds=seconds),flush=True)

def worker(manifest,index):
    f=load(manifest);c=f['cells'][index]
    for key in ['source','audit','child','capacity']:resolve(f[key])
    require(c['status']=='pending','capacity-admitted cell');out=BASE/c['id'];out.mkdir(exist_ok=False)
    binding=load(resolve(c['image']));exe=resolve(binding['executor']);cuda=resolve(binding['cuda']);resolve(binding['preparation'])
    if c['version']=='v10':resolve(binding['packing'])
    put(out/'request.json',c['request']);prior=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    process=child([str(exe),'solve',str(resolve(c['model'])),str(BASE),str(cuda)],out/'stdout.jsonl',out/'stderr',c['seconds']-30,json.dumps(c['request'])+'\n')
    process['child_rusage_hwm_bytes']=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss*1024
    process['child_rusage_scope_is_single_solver']=prior==0;put(out/'process.json',process)
    require(not process['timed_out'] and process['returncode']==0,'retained owned child interruption; never retry cell')
    start=time.monotonic_ns();r=json.loads((out/'stdout.jsonl').read_text());response=out/'response.json';put(response,r)
    from lp_billion_admit import validate_timings
    validate_timings(r,True);m=c['memory']
    require(r['model_sha256']==c['model']['sha256'] and r['nonzeros']==load(resolve(c['model_result']))['nonzeros'],'original model identity')
    require(max(r['device_bytes_upper'],r['gpu_preparation'].get('allocated_bytes',0),r.get('gpu_packing',{}).get('allocated_bytes_upper',0))<=m['device_bytes'],'complete device bound')
    require(sum(r['attempted'])==r['physical'] and sum(r['accepted'])==r['logical'],'full work accounting')
    require(all(x['restored_exact'] for x in r['recoveries']),'exact checkpoint recovery')
    from lp_billion_portable import arrays
    chunks={x['sha256']:x['bytes'] for a in arrays(r) for x in a['chunks']}
    require(sum(chunks.values())<=m['endpoint_bytes_upper'],'endpoint and repaired witness storage')
    if c['version']=='v10':
        require(r['gpu_packing']['backend']=='gpu','GPU packing actually executed')
        require(r['gpu_packing']['eligible_tiles']==load(resolve(c['model_result']))['canonical_tiles'],'canonical eligible tiles')
    measured=dict(status='measured',cell=c['id'],freeze=ref(manifest),response=ref(response),process_ns=process['elapsed_ns'],
        response_transport_ns=time.monotonic_ns()-start,solver_status=r['status'],certified=r['certified'],
        solver_child_hwm_bytes=process['child_rusage_hwm_bytes'] if prior==0 else None)
    measured['fresh_process_ns']=measured['process_ns']+measured['response_transport_ns']
    from lp_billion_timing import process_ledger
    measured['process_cost_ledger']=process_ledger(r,measured);put(out/'result.json',measured)
    print(dict(cell=c['id'],process_seconds=measured['fresh_process_ns']/NS,packing_seconds=r['preparation_detail_ns']['packing']/NS,logical=r['logical'],certified=r['certified']),flush=True)

def execute(manifest):
    f=load(manifest)
    for key in ['source','audit','child','capacity']:resolve(f[key])
    for index,c in enumerate(f['cells']):
        if c['status']!='pending':print(dict(cell=c['id'],status=c['status']),flush=True);continue
        r=BASE/'resources'/(c['id']+'.reservation.json')
        if not r.exists():
            m=c['memory'];s=run(c['id'],'development',c['seconds'],True,[str(PYTHON),'-B',__file__,'worker','--manifest',str(manifest),'--index',str(index)],m['host_gib'],m['device_gib'],math.ceil(m['endpoint_bytes_upper']/(1<<30))+1)
            print(dict(cell=c['id'],settlement=s),flush=True)
        else:s=load(r.with_name(c['id']+'.settlement.json'))
        require(s['cleanup_empty'] and not s['overrun'],'cleanup/overrun stops continuation')
        audit=c['id']+'-full-audit'
        if (BASE/'resources'/(audit+'.reservation.json')).exists():require(completed(audit),'failed audit retained');continue
        command=[str(PYTHON),'-B',str(AUDIT),str(manifest),str(index)]
        if c['audit_host_gib']<=16:command=[str(PYTHON),'-B',str(ROOT/'tools/lp_mixed2_reuse_place.py'),*command]
        s=run(audit,'reporting',c['audit_seconds'],False,command,c['audit_host_gib'],0,math.ceil(8*load(resolve(c['model_result']))['rows']/(1<<30))+1)
        print(dict(audit=audit,settlement=s),flush=True);require(s['status']=='passed','strict independent audit')
    put(manifest.parent/'completed.json',dict(status='all_admitted_cells_attempted_and_available_endpoints_audited',freeze=ref(manifest)))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','worker','execute']);p.add_argument('--scale',choices=['64m','1b']);p.add_argument('--manifest',type=Path);p.add_argument('--index',type=int);a=p.parse_args()
    if a.action=='freeze':freeze(a.scale)
    elif a.action=='worker':worker(a.manifest,a.index)
    else:execute(a.manifest)
