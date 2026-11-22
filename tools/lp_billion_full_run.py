"""Full original-billion roster, immutable freeze, one attempt and strict audits."""
import argparse,math,resource,time
from pathlib import Path
from lp_billion_common import BASE,ROOT,put,load,ref,resolve,require,CPU_CAPS,GPU_CAPS,NS,DISK_LIMIT,disk_bytes
from lp_billion_budget import accounting,run
from lp_billion_prepare_continue import completed
from lp_billion_full_plan import FAMILIES,LANES,SOLVE,COPT,FINAL,EXTRA
from lp_billion_campaign import endpoint_bytes
from lp_billion_memory_bounds_final import bounded_capacity
from lp_billion_owned_process import execute as child
from lp_general_oracle import settings
PYTHON=ROOT/'artifacts/gpup-copt-adapter-env/venv/bin/python'
MANIFEST=BASE/'full-billion-v1/freeze.json'

def candidates(models,capacity,used_cpu,used_gpu,storage):
    plans=[]
    for updates in range(500,5001,500):
        cells=[]
        for i,family in enumerate(FAMILIES):
            model=models[family];order=LANES[i%len(LANES):]+LANES[:i%len(LANES)]
            for lane in order:
                project=lane in LANES[:3];memory=bounded_capacity(model,lane) if project else capacity[family][lane]
                supported=memory['admitted'];seconds=SOLVE[family] if project else COPT[family]+300
                if project and updates>500:
                    seconds=max(seconds,{'irregular':1000,'wide':1250,'tall':1000,'coupled_blocks':850,'ill_scaled':1000,'degenerate':1000}[family])
                audit=FINAL[family]+math.ceil(updates/500)*EXTRA[family] if project else FINAL[family]
                memory=dict(memory,endpoint_bytes_upper=endpoint_bytes(model,updates) if project else 8*(model['columns']+2*model['rows']))
                cell=dict(id=f'full-billion-v1-{i}-{lane}',family=family,lane=lane,status='pending' if supported else 'unsupported_capacity',
                    model=model['model'],model_result=ref(BASE/f'models-1b-{family}-v1/result.json'),memory=memory,seconds=seconds,audit_seconds=audit,
                    audit_host_gib=math.ceil((bounded_capacity(model,'native')['stage_live_bytes']['independent_final_check']+(8<<30))/(1<<30)),
                    common_solver_wall_seconds=600,memory_mb=48000.)
                if project:cell['request']=dict(settings={**settings(lane),'iteration_limit':updates,'check_interval':500,'wall_ms':600000},
                    tensor=dict(control_interval=100,min_tile_nnz=128),fast=dict(host_reductions=True,host_preparation=True,host_certificates=True,auto_schedule=True,gpu_preparation=True),profile=True)
                cells.append(cell)
        live=[c for c in cells if c['status']=='pending']
        solve=4*sum(c['seconds'] for c in live);audit=4*sum(c['audit_seconds'] for c in live);gpu=sum(c['seconds'] for c in live if c['lane']!='copt-cpu-auto')
        space=storage+sum(c['memory']['endpoint_bytes_upper'] for c in live)+(8<<30)
        rejected=[]
        if used_cpu['development']+solve*NS>CPU_CAPS['development']*NS:rejected.append('whole solve CPU')
        if used_cpu['reporting']+(audit+1200)*NS>CPU_CAPS['reporting']*NS:rejected.append('whole strict audit CPU plus final reporting')
        if used_gpu['development']+gpu*NS>GPU_CAPS['development']*NS:rejected.append('whole GPU')
        if space>DISK_LIMIT:rejected.append('whole storage including repaired witnesses')
        plans.append(dict(iterations=updates,cells=cells,solve_cpu_seconds=solve,audit_cpu_seconds=audit,gpu_seconds=gpu,storage_bytes=space,rejected_by=rejected))
    return plans

def freeze():
    require(not MANIFEST.exists(),'fresh full-billion scientific freeze')
    for name in ['operational-cpu-v20','operational-gpu-v17','copt-tail-contracts-v1','full-run-contracts-v1','bounded-copy-gpu-v1','copt-full-admission-v2',
                 'bounded-memory-gpu-v1','bounded-memory-memcheck-v1','bounded-memory-racecheck-v1','bounded-memory-initcheck-v1','bounded-memory-synccheck-v1']:
        require(completed(name),'complete source-specific admission '+name)
    require(load(BASE/'full-run-acceptance-v1.json')['current_full_run']==ref(__file__),'current full-run source acceptance')
    require(load(BASE/'full-audit-admission-v2/result.json')['checker_source']==ref(ROOT/'tools/lp_billion_full_audit_v2.py'),'current streaming checker admission')
    capacity_path=BASE/'copt-capacity-readiness-v1.json';capacity=load(capacity_path)
    require(capacity['status']=='complete_capacity_dispositions','full COPT capacity dispositions')
    for proof in capacity['evidence']:resolve(proof)
    models={f:load(BASE/f'models-1b-{f}-v1/result.json') for f in FAMILIES}
    construction=[]
    for f,m in models.items():
        require(m['status']=='generated' and m['nonzeros']==1_000_000_000,'one billion ORIGINAL nonzeros in every family')
        p=resolve(m['model']).parent/'construction-check.json';q=load(p)
        require(q['accepted'] and q['model']==m['model'],'strict original construction check');construction.append(ref(p))
    cpu,gpu=accounting();plans=candidates(models,capacity['capacity'],cpu,gpu,disk_bytes());eligible=[p for p in plans if not p['rejected_by']]
    require(eligible,'no full-cohort solve/audit/storage reservation fits')
    chosen=eligible[-1]
    require(len(chosen['cells'])==30 and len({(c['family'],c['lane']) for c in chosen['cells']})==30,'full six by five roster')
    for c in chosen['cells']:require(not (BASE/'resources'/(c['id']+'.reservation.json')).exists(),'no attempted billion cell may repeat')
    binding=load(BASE/'image-v9/binding.json')
    for key in ['executor','cuda','preparation']:resolve(binding[key])
    for item in load(resolve(binding['source_manifest']))['sources']:
        name=item['original']['path']
        if name.endswith(('.rs','.cu')) or Path(name).name.startswith('Cargo.'):resolve(item['original'])
    from lp_billion_copt_run import installation
    put(MANIFEST,dict(status='frozen_development',cells=chosen['cells'],iterations=chosen['iterations'],common_solver_wall_seconds=600,
        image=ref(BASE/'image-v9/binding.json'),checker=ref(BASE/'image-v1/executor'),construction=construction,
        source=ref(__file__),audit=ref(ROOT/'tools/lp_billion_full_audit_v2.py'),child=ref(ROOT/'tools/lp_billion_owned_process.py'),
        copt_adapter=ref(ROOT/'tools/lp_billion_copt_run.py'),installation=installation(),capacity=ref(capacity_path),
        allocation=ref(BASE/'approved-recovery-v1.json'),protocol=ref(ROOT/'docs/specifications/SPEC-0046-amendment-46.md'),
        candidates=[{k:v for k,v in p.items() if k!='cells'} for p in plans],
        claim='One fresh-process attempt per supported cell. All capacity refusals retained. No confirmation or public adoption.'))
    print(dict(freeze=str(MANIFEST),iterations=chosen['iterations'],supported=sum(c['status']=='pending' for c in chosen['cells']),cells=30),flush=True)

def worker(index):
    f=load(MANIFEST);c=f['cells'][index];require(c['status']=='pending','capacity refusal is not executable')
    for key in ['source','audit','child']:resolve(f[key])
    project=c['lane'] in LANES[:3];out=BASE/c['id'];out.mkdir(exist_ok=False);response_path=out/'response.json'
    prior_child_hwm=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    if project:
        import json
        binding=load(resolve(f['image']));executor=resolve(binding['executor']);cuda=resolve(binding['cuda']);resolve(binding['preparation'])
        put(out/'request.json',c['request'])
        process=child([str(executor),'solve',str(resolve(c['model'])),str(BASE),str(cuda)],out/'stdout.jsonl',out/'stderr',c['seconds']-30,json.dumps(c['request'])+'\n')
    else:
        from lp_billion_copt_run import installation
        require(f['installation']==installation(),'installed COPT binding');resolve(f['copt_adapter'])
        process=child([str(PYTHON),'-B',str(ROOT/'tools/lp_billion_copt_run.py'),str(resolve(c['model'])),str(response_path),
            '--wall-seconds','600','--memory-mb',str(c['memory_mb']),*(['--gpu'] if c['lane']=='copt-gpu-pdlp' else [])],out/'stdout',out/'stderr',c['seconds']-30)
    process['child_rusage_hwm_bytes']=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss*1024
    process['child_rusage_scope_is_single_solver']=prior_child_hwm==0
    put(out/'process.json',process)
    require(not process['timed_out'] and process['returncode']==0,'retained owned child interruption; never retry scientific cell')
    start=time.monotonic_ns()
    if project:
        import json
        r=json.loads((out/'stdout.jsonl').read_text());put(response_path,r)
        from lp_billion_admit import validate_timings
        validate_timings(r,True)
        require(r['device_bytes_upper']<=c['memory']['device_bytes'] and r.get('gpu_preparation',{}).get('allocated_bytes',0)<=c['memory']['device_bytes'],'device/preparation allocation bound')
        require(sum(r['attempted'])==r['physical'] and sum(r['accepted'])==r['logical'],'complete work accounting')
        require(all(x['restored_exact'] for x in r['recoveries']),'strict checkpoint recovery')
        from lp_billion_portable import arrays
        chunks={x['sha256']:x['bytes'] for a in arrays(r) for x in a['chunks']}
        require(sum(chunks.values())<=c['memory']['endpoint_bytes_upper'],'all endpoints and repaired dual witnesses fit')
    else:r=load(response_path)
    require(r['model_sha256']==c['model']['sha256'] and r['nonzeros']==1_000_000_000,'full original billion matrix identity')
    measured=dict(status='measured',cell=c['id'],response=ref(response_path),freeze=ref(MANIFEST),process_ns=process['elapsed_ns'],
        response_transport_ns=time.monotonic_ns()-start,solver_status=r['status'],certified=r.get('certified'),
        solver_child_hwm_bytes=process['child_rusage_hwm_bytes'] if process['child_rusage_scope_is_single_solver'] else None)
    measured['fresh_process_ns']=measured['process_ns']+measured['response_transport_ns']
    if project:
        from lp_billion_timing import process_ledger
        measured['process_cost_ledger']=process_ledger(r,measured)
    else:
        require(r['profile']['total_ns']<=measured['process_ns'],'vendor full process coverage')
        costs=dict(r['profile']['exclusive_ns'],process_imports_serialization_cleanup=measured['process_ns']-r['profile']['total_ns'],response_transport=measured['response_transport_ns'])
        require(sum(costs.values())==measured['fresh_process_ns'],'vendor exact outer coverage')
        measured['process_cost_ledger']=dict(total_ns=measured['fresh_process_ns'],exclusive_ns=costs)
    put(out/'result.json',measured)
    print(dict(cell=c['id'],seconds=measured['fresh_process_ns']/NS,status=r['status'],logical=r.get('logical'),certified=r.get('certified'),gpu_confirmed=r.get('gpu_confirmed')),flush=True)

def execute():
    f=load(MANIFEST);[resolve(f[k]) for k in ['source','audit','child']]
    from lp_billion_idle import Nvml
    sensor=Nvml()
    try:
        for i,c in enumerate(f['cells']):
            if c['status']!='pending':print(dict(cell=c['id'],status=c['status']),flush=True);continue
            p=BASE/'resources'/(c['id']+'.reservation.json')
            if not p.exists():
                m=c['memory'];gpu=c['lane']!='copt-cpu-auto'
                s=run(c['id'],'development',c['seconds'],gpu,[str(PYTHON),'-B',__file__,'worker','--index',str(i)],m['host_gib'],m['device_gib'] if gpu else 0,math.ceil(m['endpoint_bytes_upper']/(1<<30))+1)
                print(dict(cell=c['id'],settlement=s),flush=True)
            else:s=load(p.with_name(c['id']+'.settlement.json'));print(dict(cell=c['id'],status='retained_attempt_no_repeat'),flush=True)
            require(s['cleanup_empty'] and not s['overrun'],'cleanup/overrun stops scientific continuation')
            check_id=c['id']+'-full-audit';p=BASE/'resources'/(check_id+'.reservation.json')
            if p.exists():require(completed(check_id),'failed audit is retained, never silently repeated');continue
            s=run(check_id,'reporting',c['audit_seconds'],False,[str(PYTHON),'-B',str(ROOT/'tools/lp_billion_full_audit_v2.py'),str(MANIFEST),str(i)],c['audit_host_gib'],0,math.ceil(8*load(resolve(c['model_result']))['rows']/(1<<30))+1)
            print(dict(audit=check_id,settlement=s),flush=True);require(s['status']=='passed','strict independent audit stopped')
        put(MANIFEST.parent/'completed.json',dict(status='all_supported_cells_attempted_and_available_endpoints_audited',freeze=ref(MANIFEST)))
    finally:sensor.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','worker','execute']);p.add_argument('--index',type=int);a=p.parse_args()
    if a.action=='worker':worker(a.index)
    else:globals()[a.action]()
